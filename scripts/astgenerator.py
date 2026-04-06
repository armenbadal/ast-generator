import os
import argparse
class Node:
    def __init__(self, name, slots):
        self.name = name
        self.slots = slots
        self.parent = None
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
        if self._eos():
            return Lexeme(EOF)

        if not self._eof() and self._peek().isalpha():
            start_pos = self.position
            while not self._eos() and self._peek().isalnum():
                self.position += 1
            return Lexeme(IDENTIFIER, self.source[start_pos:self.position])

        if self._see('{'):
            start_pos = self.position
            while not self._eos() and not self._see('}'):
                self.position += 1
            if self._eos():
                raise ValueError(f'Line {self.line}: Unclosed verbatim block. Expected closing brace but reached end of file.')
            self.position += 1
            return Lexeme(VERBATIM, self.source[start_pos+1:self.position-1])

        if self._see('\n'):
            self.position += 1
            self.line += 1
            return Lexeme(NEW_LINE)

        if self._see(' '):
            spaces = ''
            while not self._eos() and self._peek().isspace():
                self.position += 1
                spaces += ' '
            return Lexeme(SPACE, spaces)

        if self._see('['):
            self.position += 1
            return Lexeme(LEFT_BRACKET)

        if self._see(']'):
            self.position += 1
            return Lexeme(RIGHT_BRACKET)

        if self._see(':'):
            self.position += 1
            return Lexeme(COLON)

        if self._see(','):
            self.position += 1
            return Lexeme(COMMA)

        raise ValueError(f'Unexpected character: {self.source[self.position]}')
        
    def _eos(self):
        return self.position >= self.length
    
    def _peek(self):
        return self.source[self.position]

    def _see(self, char):
        return not self._eos() and self.source[self.position] == char


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
            child.parent = head
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
        typ = self.match(IDENTIFIER)
        return (name, prefix + typ)

    def parse_new_lines(self):
        while self.lookahead.token == NEW_LINE:
            self.match(NEW_LINE)


class Generator:
    def __init__(self, ast, directory):
        verbatims, tree = ast
        self.preamble = '\n'.join(verbatims)
        self.tree = tree
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def generate(self):
        self._generate(self.tree)

    def _generate(self, tree: Node):
        self._generate_node(tree)
        if tree.children is not None:
            for ch in tree.children:
                self._generate(ch)

    def _generate_node(self, node: Node):
        code = 'public '

        if node.slots is None:
            code += 'sealed interface '
        else:
            if node.children is None:
                code += 'final class '
            else:
                code += 'sealed abstract class '

        code += node.name

        if node.parent is not None:
            pr = node.parent
            if pr.slots is None:
                code += ' implements '
            else:
                code += ' extends '
            code += node.parent.name

        if node.children is not None:
            code += ' permits '
            code += ', '.join([n.name for n in node.children])

        code += ' {\n'

        if node.slots is not None:
            for nm, tp in node.slots:
                decl = self._slot_declaration(nm, tp)
                code += f'  public {decl};\n'

        if 'final class' in code:
            params = []
            body = ''
            for nm, tp in node.slots:
                decl = self._slot_declaration(nm, tp)
                params.append(decl)
                body += f'    this.{nm} = {nm};\n'

            paramcode = ', '.join(params)
            code += f'\n  public {node.name}({paramcode}) {{\n{body}  }}\n'

        code += '}\n'

        path = os.path.join(self.directory, f'{node.name}.java')
        with open(path, 'w') as f:
            f.write(self.preamble)
            f.write('\n\n')
            if 'List<' in code:
                f.write('import java.util.List;')
                f.write('\n\n')
            f.write(code)

    def _slot_declaration(self, nm, tp):
        if tp.startswith('[]'):
            tp = f'List<{tp[2:]}>'
        return f'{tp} {nm}'



if __name__ == "__main__":
    argp = argparse.ArgumentParser(description='Generate AST Java classes from a definition file')
    argp.add_argument('input', help='path to input AST definition file')
    argp.add_argument('output', help='output directory for generated .java files')
    args = argp.parse_args()

    try:
        with open(args.input, 'r') as f:
            source = f.read()
        ast = Parser(Scanner(source)).parse()
        generator = Generator(ast, args.output)
        generator.generate()
    except FileNotFoundError as e:
        print(f'File not found: {e.filename}')
    except ValueError as e:
        print(e)
