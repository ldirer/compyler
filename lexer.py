# raw strings mean we don't have to escape backslashes.
import re
from typing import List, Dict, Tuple
from pprint import pprint

import pytest

letter = r'([a-zA-Z_])'

# variables cant start with a number.
identifier = rf'{letter}({letter}|[0-9])+'
integer = r'[1-9][0-9]*'

equals = r'='


print(identifier)


def split_trim(text, sep=None, max_split=-1):
    # Like split but we remove empty strings and trim whitespaces
    return [t.strip() for t in text.split(sep, max_split) if t]


class Token:

    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                frozenset(self.__dict__.items()) == frozenset(other.__dict__.items()))


# Tokens are also terminal expressions. (TODO: that's really a guess! But I dont want to define an Identifier node in ast...)
class Identifier(Token):

    def __init__(self, name: str):
        self.name = name


class Integer(Token):

    def __init__(self, value: str):
        # Should the lexer already be converting values?
        self.value = int(value)


# TODO: I think we could have metaprogramming help somewhere here to make definitions of tokens/regex clearer.
token_types = [(re.compile(pattern), token_cls)
               for pattern, token_cls in zip([identifier, integer], [Identifier, Integer])]


def lex(source: str) -> List[Token]:
    """For now: single-line source."""
    # I was not entirely sure what the lexer should output... Hints: https://stackoverflow.com/a/2662255/3914041
    source = source.replace('\t', ' ')
    output = []
    for token in split_trim(source, sep=' '):
        for regexp, token_cls in token_types:
            m = regexp.match(token)
            if m is not None and m.group() == token:
                output.append(token_cls(token))
    return output


import tree as tree


# TODO: Identifier is just an intermediate variable. We dont want it to show up in the tokens. Or do we? I think we dont.
# Maybe we could mark them as 'terminal' here with a slightly more sophisticated grammar object
def read_grammar(description):
    g = {}
    for line in split_trim(description, '\n'):
        # line comments allowed (and blank lines)
        if line.startswith('#') or not line.strip():
            continue
        atom, specs = split_trim(line, sep='=>', max_split=1)
        alternatives = tuple(a.split() for a in split_trim(specs, '|'))
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

    def parse_sequence(seq: List, text):
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
            # TODO whitespace here I guess.. YES. SSSNEAKY LITTLE SSPACE.
            match = re.match(f'{whitespace}({atom})', text)
            if match is not None:
                # match.group(0) would be with the whitespaces
                return match.group(1), text[match.end():]
            else:
                raise ParseError()

        else:
            # onto non-terminal atoms
            exceptions = []
            for alternative in grammar[atom]:
                try:
                    tree, remainder = parse_sequence(alternative, text)
                except ParseError as e:
                    exceptions.append(e)
                    continue
                return [atom] + tree, remainder
            # no more alternatives, fail
            raise ParseError(f'No more alternatives, cannot parse {text}')

    return parse_atom('Wrap', text)


def test_identifier():
    re_identifier = re.compile(identifier)
    valid_identifier = 'valid_identifier'
    assert re_identifier.match(valid_identifier).group() == valid_identifier
    invalid_identifier = '9_cant_start_with_number'
    assert re_identifier.match(invalid_identifier) is None


def test_lexer():
    src = 'valid_identifier'
    assert lex(src) == [Identifier('valid_identifier')]


simple_assign = 'var valid_identifier = 42'
invalid_identifier = 'var 911notvalid = 42'
invalid_identifier_big = """
var valid = 13
var ok = 12
var 911notvalid = 42
var validone = 11
var again = 10
"""

def test_parser():
    # TODO: read as raw string vs binary?
    with open('another_grammar', 'r') as f:
        g = read_grammar(f.read())
    pprint(g)
    print('-' * 50)
    token_tree, remainder = parse(g, simple_assign)
    assert remainder == ''
    # assert token_tree == ['Wrap', ['Assignment', 'var', ['Identifier', 'valid_identifier'],
    #                                '=',
    #                                ['Value', ['Integer', '42']]]]

    my_ast = to_ast(token_tree)
    print(tree.ast_to_str(my_ast))
    print('-' * 50)

    with pytest.raises(ParseError):
        parse(g, invalid_identifier)

    # Note we dont necessarily raise an exception when we cant parse. Just when we cant parse *anything*.
    my_ast, remainder = parse(g, invalid_identifier_big)
    assert remainder != ''


def to_ast(token_list):
    # I think we could integrate this step and not generate a list of tuple-lists of tokens. Dunno if its a good idea.

    class_name, *args = token_list
    cls = getattr(tree, class_name)
    # Some elements are lists: these still need parsing.
    ast_args = [to_ast(arg) if isinstance(arg, list) else arg for arg in args
                if not (isinstance(arg, str) and arg in cls.syntax_strings)
                ]
    # Hack. Esp since some 'class_name' refer to functions.
    return cls(*ast_args)



if __name__ == '__main__':
    # test_identifier()
    # test_lexer()
    test_parser()
