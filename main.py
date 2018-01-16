import click as click

from lexer import parse, read_grammar, to_ast
from tree import to_llvm

with open('another_grammar', 'r') as f:
    g = read_grammar(f.read())


# @click.Parameter()   # nice to get the docs on signature/parameters that click.argument does not give easily.
@click.command()
@click.argument('source-file', type=click.File(), required=True)
def compile(source_file):
    token_list, remainder = parse(g, source_file.read())
    ast = to_ast(token_list)
    print(to_llvm(ast))


if __name__ == '__main__':
    compile()
