
class Slot:
    def __init__(self, name, type):
        self.name = name
        self.type = type

    def __str__(self):
        return f'{self.name}: {self.type}'

class Entity:
    def __init__(self, name):
        self.name = name
        self.kind = ''
        self.slots = []
        self.parent = ''
        self.children = []

    def __str__(self):
        result = f'{self.name}\n'
        result += f'1  {self.kind}\n'
        result += f'2  {self.parent}\n'
        result += f'3  {self.children}\n'
        s = [str(x) for x in self.slots]
        result += f'4  {s}\n'
        return result


# Թոքեններ
IDENTIFIER = 'IDENTIFIER'
LEFT_BRACKET = '['
RIGHT_BRACKET = ']'
EXCLAMATION = '!'
COLON = ':'
COMMA = ','
VERBATIM = '@'
NEW_LINE = '↵'
SPACE = '␣'
EOF = 'EOF'

class Lexeme:
    def __init__(self, token, value):
        self.token = token
        self.value = value

class Scanner:
    def __init__(self, source):
        self.source = source
        self.length = len(source)
        self.position = 0
        self.line = 1

    def next_lexeme(self):
        if self.position >= self.length:
            return Lexeme(EOF, None)

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
        elif current_char == '[':
            self.position += 1
            return Lexeme(LEFT_BRACKET, '[')
        elif current_char == ']':
            self.position += 1
            return Lexeme(RIGHT_BRACKET, ']')
        elif current_char == '!':
            self.position += 1
            return Lexeme(EXCLAMATION, '!')
        elif current_char == ':':
            self.position += 1
            return Lexeme(COLON, ':')
        elif current_char == ',':
            self.position += 1
            return Lexeme(COMMA, ',')
        elif current_char == '\n':
            self.position += 1
            self.line += 1
            return Lexeme(NEW_LINE, '\n')
        elif current_char.isspace():
            self.position += 1
            return Lexeme(SPACE, ' ')
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
        verbatims = []
        while self.has(VERBATIM):
            verbatim = self.match(VERBATIM)
            verbatims.append(verbatim)
            self.parse_new_lines()

        definitions = []
        while self.lookahead.token != EOF:
            definition = self.parse_definition()
            definitions.append(definition)

        return (verbatims, definitions)

    def parse_definition(self):
        indent = self.parse_indent()
        name = self.match(IDENTIFIER)
        marker = ''
        if self.has(EXCLAMATION):
            self.match(EXCLAMATION)
            marker = '!'
        slots = []
        if self.has(LEFT_BRACKET):
            self.match(LEFT_BRACKET)
            slots = self.parse_slots()
            self.match(RIGHT_BRACKET)
        self.parse_new_lines()
        return (indent, name, marker, slots)

    def parse_indent(self):
        count = 0
        while self.lookahead.token == SPACE:
            count += 1
            self.match(SPACE)
        return count

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
        return (name, prefix + type)

    def parse_new_lines(self):
        while self.lookahead.token == NEW_LINE:
            self.match(NEW_LINE)

    def skip_spaces(self):
        while self.lookahead.token == SPACE:
            self.match(SPACE)


class Generator:
    def __init__(self, ast, directory):
        self.ast = ast
        self.directory = directory


class JavaGenerator(Generator):
    def __init__(self, ast, directory):
        super().__init__(ast, directory)

    def generate(self):
        verbatims, definitions = self.ast
        preamble = '\n'.join(verbatims)

        current_indent = -1
        bases = ['Object']
        for definition in definitions:
            indent, name, kind, slots = definition
            entity = Entity(name)

            entity.parent = bases[-1]
            if indent > current_indent:
                bases.append(name)
            elif indent < current_indent:
                bases.pop()
            current_indent = indent

            if kind == '!':
                entity.kind = 'final'
            if len(slots) == 0:
                entity.kind = 'abstract'

            entity.slots = [Slot(n, t) for n, t in slots]

            print(entity)


if __name__ == "__main__":
    try:
        with open('examples/ex01.ast', 'r') as f:
            source = f.read()
        scanner = Scanner(source)
        parser = Parser(scanner)
        result = parser.parse()
        generator = JavaGenerator(result, '.')
        generator.generate()
    except ValueError as e:
        print(e)
