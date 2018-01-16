# raw strings mean we don't have to escape backslashes.
import re
from typing import List, Dict, Tuple
import pytest

import tree as tree


def split_trim(text, sep=None, max_split=-1):
    # Like split but we remove empty strings and trim whitespaces
    return [t.strip() for t in text.split(sep, max_split) if t]


def read_grammar(description):
    g = {}
    for line in split_trim(description, '\n'):
        # line comments allowed (and blank lines)
        if line.startswith('#') or not line.strip():
            continue
        atom, specs = split_trim(line, sep='=>', max_split=1)
        alternatives = tuple(a.split() for a in split_trim(specs, ' | '))
        g[atom] = alternatives
    return g


class ParseError(Exception):
    pass


def parse(grammar: Dict[str, Tuple[List[str]]], text: str):
    """One thing to remember is that we deal with context-free grammars.
    I think it matters a lot because it means there's no ambiguity when parsing.


    Keep in mind that the tree has *a single root node*. It's important to understand the code.

    """

    if not text:
        return None

    def parse_sequence(seq: List, text: str):
        """We use this to parse things like 'var Identifier = Value' which is effectively a sequence.
        Note the sequence could have a single element, it's not a big deal and makes it more generic.

        """
        result = []
        remainder = text
        for atom in seq:
            tree, remainder = parse_atom(atom, remainder)
            result.append(tree)

        return result, remainder

    def parse_atom(atom, text):
        """
        :param: atom: smt like Assignment. Or a terminal expression, like a regex '[0-9]'
        """
        whitespace = '\s*'
        # We hit a terminal expression - no need to recurse further
        if atom not in grammar:
            # watch out for the sneaky whitespaces ruining the parsing.
            match = re.match(f'{whitespace}({atom})', text)
            if match is not None:
                # match.group(0) would be with the whitespaces
                print(atom, '---', text)
                return match.group(1), text[match.end():]
            else:
                raise ParseError()

        else:
            # onto non-terminal atoms
            for alternative in grammar[atom]:
                try:
                    tree, remainder = parse_sequence(alternative, text)
                except ParseError:
                    continue

                print(atom, '---', text)
                return [atom] + tree, remainder
            # no more alternatives, fail
            raise ParseError(f'No more alternatives, cannot parse {text}')

    return parse_atom('Wrap', text)


def to_ast(token_list) -> tree.AstNode:
    # I think we could integrate this step and not generate a list of tuple-lists of tokens. Dunno if its a good idea.

    class_name, *args = token_list
    cls = getattr(tree, class_name)
    # I dont know what im doing
    setattr(tree, 'Expr', tree.Value)
    # Some elements are lists: these still need parsing.
    ast_args = [to_ast(arg) if isinstance(arg, list) else arg for arg in args
                if not (isinstance(arg, str) and arg in cls.syntax_strings)]
    # Hack. Esp since some 'class_name' refer to functions.
    return cls(*ast_args)
