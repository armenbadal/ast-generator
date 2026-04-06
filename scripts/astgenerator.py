import os
import argparse

try:
    import yaml
except ImportError:
    yaml = None

def load_ast_from_yaml(path):
    if yaml is None:
        raise ImportError('PyYAML is required to load YAML input. Install it with "pip install pyyaml".')

    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError('YAML root must be a mapping.')

    preamble = []
    if 'package' in data:
        preamble.append(f'package {data["package"]};')

    if 'preamble' in data:
        raw_preamble = data['preamble']
        if isinstance(raw_preamble, list):
            preamble.extend(raw_preamble)
        elif isinstance(raw_preamble, str):
            preamble.append(raw_preamble)
        else:
            raise ValueError('preamble must be a string or list of strings.')

    definitions = data.get('definitions')
    if definitions is None:
        raise ValueError('YAML must contain top-level "definitions".')
    if not isinstance(definitions, list):
        raise ValueError('definitions must be a list.')

    validated = [validate_definition(defn) for defn in definitions]
    tree = validated[0] if len(validated) == 1 else validated
    return preamble, tree


def validate_definition(defn, parent_name=None):
    if not isinstance(defn, dict):
        raise ValueError('Each definition must be a mapping.')

    name = defn.get('name')
    if not isinstance(name, str):
        raise ValueError('Each node definition must have a string "name".')

    kind = defn.get('type')
    if kind is not None and not isinstance(kind, str):
        raise ValueError(f'type for node "{name}" must be a string if present.')

    slots = None
    if 'slots' in defn:
        raw_slots = defn['slots']
        if raw_slots is None:
            slots = []
        elif not isinstance(raw_slots, list):
            raise ValueError(f'slots for node "{name}" must be a list.')
        else:
            slots = []
            for slot in raw_slots:
                if not isinstance(slot, dict):
                    raise ValueError(f'Each slot for node "{name}" must be a mapping.')
                slot_name = slot.get('name')
                slot_type = slot.get('type')
                if not isinstance(slot_name, str) or not isinstance(slot_type, str):
                    raise ValueError(f'Each slot for node "{name}" must have string name and type.')
                slots.append({'name': slot_name, 'type': slot_type})

    children = None
    if 'children' in defn:
        raw_children = defn['children']
        if not isinstance(raw_children, list):
            raise ValueError(f'children for node "{name}" must be a list.')
        children = [validate_definition(child, name) for child in raw_children]

    node = {
        'name': name,
        'type': kind,
        'slots': slots,
        'children': children,
    }
    return node


class Generator:
    def __init__(self, ast, directory):
        verbatims, tree = ast
        self.preamble = '\n'.join(verbatims)
        self.tree = tree
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def generate(self):
        if isinstance(self.tree, list):
            for node in self.tree:
                self._generate(node, None)
        else:
            self._generate(self.tree, None)

    def _generate(self, node, parent):
        self._generate_node(node, parent)
        if node.get('children') is not None:
            for child in node['children']:
                self._generate(child, node)

    def _generate_node(self, node, parent):
        code = 'public '

        kind = node.get('type')
        kind = kind.lower() if isinstance(kind, str) else None
        if kind == 'interface':
            code += 'sealed interface '
        elif kind == 'abstract class':
            code += 'sealed abstract class '
        elif kind == 'final class' or kind == 'class':
            code += 'final class '
        else:
            if node.get('slots') is None:
                code += 'sealed interface '
            elif node.get('children') is None:
                code += 'final class '
            else:
                code += 'sealed abstract class '

        code += node['name']

        if parent is not None:
            if parent.get('slots') is None:
                code += ' implements '
            else:
                code += ' extends '
            code += parent['name']

        if node.get('children') is not None:
            code += ' permits '
            code += ', '.join([child['name'] for child in node['children']])

        code += ' {\n'

        if node.get('slots') is not None:
            for slot in node['slots']:
                decl = self._slot_declaration(slot['name'], slot['type'])
                code += f'  public {decl};\n'

        if 'final class' in code:
            params = []
            body = ''
            for slot in node.get('slots', []):
                decl = self._slot_declaration(slot['name'], slot['type'])
                params.append(decl)
                body += f'    this.{slot["name"]} = {slot["name"]};\n'

            paramcode = ', '.join(params)
            code += f'\n  public {node["name"]}({paramcode}) {{\n{body}  }}\n'

        code += '}\n'

        path = os.path.join(self.directory, f'{node["name"]}.java')
        with open(path, 'w', encoding='utf-8') as f:
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
    argp = argparse.ArgumentParser(description='Generate AST code from a YAML definition file')
    argp.add_argument('input', help='path to input YAML AST definition file')
    argp.add_argument('output', help='output directory for generated code files')
    args = argp.parse_args()

    try:
        ast = load_ast_from_yaml(args.input)
        generator = Generator(ast, args.output)
        generator.generate()
    except FileNotFoundError as e:
        print(f'File not found: {e.filename}')
    except ImportError as e:
        print(e)
    except ValueError as e:
        print(e)
