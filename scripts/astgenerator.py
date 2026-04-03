
class Slot:
    def __init__(self, name, type):
        self.name = name
        self.type = type

    def __str__(self):
        return f'{self.name}: {self.type}'

class Node:
    def __init__(self, name, slots):
        self.name = name
        self.slots = slots
        self.parent = ''
        self.children = None


# Թոքեններ
IDENTIFIER = 'ID'
LEFT_BRACKET = '['
RIGHT_BRACKET = ']'
COLON = ':'
COMMA = ','
VERBATIM = '@'
NEW_LINE = '↵'
SPACE = '␣'
EOF = 'EOF'

class Lexeme:
    def __init__(self, token, value = None):
        self.token = token
        self.value = self.token if value is None else value

class Scanner:
    def __init__(self, source):
        self.source = source
        self.length = len(source)
        self.position = 0
        self.line = 1

    def next_lexeme(self):
        if self.position >= self.length:
            return Lexeme(EOF)

        current_char = self.source[self.position]

        if current_char.isalpha():
            start_pos = self.position
            while self.position < self.length and self.source[self.position].isalnum():
                self.position += 1
            return Lexeme(IDENTIFIER, self.source[start_pos:self.position])
        if current_char == '@':
            start_pos = self.position
            while self.position < self.length and self.source[self.position] != '\n':
                self.position += 1
            return Lexeme(VERBATIM, self.source[start_pos+1:self.position])
        elif current_char == '\n':
            self.position += 1
            self.line += 1
            return Lexeme(NEW_LINE)
        elif current_char.isspace():
            spaces = ''
            while self.source[self.position].isspace():
                self.position += 1
                spaces += ' '
            return Lexeme(SPACE, spaces)
        elif current_char == '[':
            self.position += 1
            return Lexeme(LEFT_BRACKET)
        elif current_char == ']':
            self.position += 1
            return Lexeme(RIGHT_BRACKET)
        elif current_char == ':':
            self.position += 1
            return Lexeme(COLON)
        elif current_char == ',':
            self.position += 1
            return Lexeme(COMMA)
        else:
            raise ValueError(f'Unexpected character: {current_char}')

class Parser:
    def __init__(self, scanner):
        self.scanner = scanner
        self.lookahead = self.scanner.next_lexeme()

    def match(self, token):
        if self.lookahead.token == token:
            value = self.lookahead.value
            self.lookahead = self.scanner.next_lexeme()
            return value

        raise ValueError(f'Line {self.scanner.line}: Expected token {token}, got {self.lookahead.token}.')

    def has(self, token):
        return self.lookahead.token == token

    def parse(self):
        verbatims = self.parse_verbatims()
        definitions = self.parse_definitions('')
        return (verbatims, definitions)
    
    def parse_verbatims(self):
        verbatims = []
        while self.has(VERBATIM):
            verbatim = self.match(VERBATIM)
            verbatims.append(verbatim)
            self.parse_new_lines()
        return verbatims

    def parse_definitions(self, indent):
        head = self.parse_definition(indent)

        children = []
        while self.has(SPACE) and self.lookahead.value == indent + '  ':
            child = self.parse_definitions(indent + '  ')
            child.parent = head.name
            children.append(child)
        if len(children) != 0:
            head.children = children

        return head

    def parse_definition(self, indent):
        if self.has(SPACE):
            if self.lookahead.value == indent:
                self.match(SPACE)
            else:
                raise ValueError('Expected correct indentation.')

        name = self.match(IDENTIFIER)

        slots = None
        if self.has(LEFT_BRACKET):
            self.match(LEFT_BRACKET)
            slots = self.parse_slots()
            self.match(RIGHT_BRACKET)

        self.parse_new_lines()

        return Node(name, slots)

    def parse_slots(self):
        if self.has(RIGHT_BRACKET):
            return []

        slots = []
        slots.append(self.parse_slot())
        while self.lookahead.token == COMMA:
            self.match(COMMA)
            slots.append(self.parse_slot())
        return slots

    def parse_slot(self):
        name = self.match(IDENTIFIER)
        self.match(COLON)
        prefix = ''
        if self.has(LEFT_BRACKET):
            self.match(LEFT_BRACKET)
            self.match(RIGHT_BRACKET)
            prefix = '[]'
        type = self.match(IDENTIFIER)
        return Slot(name, prefix + type)

    def parse_new_lines(self):
        while self.lookahead.token == NEW_LINE:
            self.match(NEW_LINE)


class Generator:
    def __init__(self, ast, directory):
        self.ast = ast
        self.directory = directory

    def generate(self):
        verbatims, tree = self.ast
        preamble = '\n'.join(verbatims)
        self._generate(tree)

    def _generate(self, tree: Node):
        c = self._generate_node(tree)
        print(c)
        if tree.children is not None:
            for ch in tree.children:
                self._generate(ch)

    def _generate_node(self, node: Node):
        code = 'public '

        if node.children is not None:
            code += 'sealed '
        else:
            code += 'final '

        if node.slots is None:
            code += 'interface '
        else:
            code += 'class '

        code += node.name

        if node.children is not None:
            code += ' permits '
            code += ', '.join([n.name for n in node.children])
        code += ' {\n'

        if node.slots is not None:
            for s in node.slots:
                code += '  public ' + str(s) + ';\n'

        code += '}\n'
        return code



if __name__ == "__main__":
    try:
        with open('examples/ex01.ast', 'r') as f:
            source = f.read()
        scanner = Scanner(source)
        parser = Parser(scanner)
        ast = parser.parse()
        generator = Generator(ast, '.')
        generator.generate()
    except ValueError as e:
        print(e)
