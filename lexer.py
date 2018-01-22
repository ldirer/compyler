# raw strings mean we don't have to escape backslashes.
import re
from typing import List, Dict, Tuple, Union
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

    def parse_sequence(seq: List, text: str, repeat=False) -> Tuple[List, str]:
        """We use this to parse things like 'var Identifier = Expr' which is effectively a sequence.
        Note the sequence could have a single element, it's not a big deal and makes it more generic.
        """
        result = []
        remainder = text

        if repeat:
            # Parse the sequence as many times as we can
            while True:
                try:
                    tree_list, remainder = parse_sequence(seq, remainder, repeat=False)
                except ParseError:
                    break

                result.extend(tree_list)
            return result, remainder


        i = 0
        REPEAT_START = 'REPEAT_START'
        REPEAT_END = 'REPEAT_END'
        while i < len(seq):
            atom = seq[i]
            if atom == REPEAT_START:
                # Get just the sequence to repeat
                repeat_sequence = seq[(i + 1): seq.index(REPEAT_END, i)]
                repeat_result, remainder = parse_sequence(repeat_sequence, remainder, repeat=True)
                result.extend(repeat_result)
                i = seq.index(REPEAT_END, i) + 1
            else:
                tree, remainder = parse_atom(atom, remainder)
                result.append(tree)
                i += 1

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
                # print(atom, '--', text, '--', match.group(1))
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

                # print(atom, '--', text, '--', tree)
                return [atom] + tree, remainder
            # no more alternatives, fail
            raise ParseError(f'No more alternatives, cannot parse {text}')

    return parse_atom('Wrap', text)


def to_ast(token_list) -> tree.AstNode:

    class_name, *args = token_list
    cls = getattr(tree, class_name)
    # I dont know what im doing. HACK
    setattr(tree, 'Expr', tree.Expr)
    setattr(tree, 'Term', tree.Expr)

    # Some elements are lists: these still need parsing.
    ast_args = [[arg] if not isinstance(arg, list) else to_ast(arg)
                for arg in args if not (isinstance(arg, str) and arg in cls.syntax_strings)]

    # This is for specific tricks where we want to modify the structure of the ast (move a child node up for instance)
    # We just flatten here.
    ast_args = [a for arg_list in ast_args for a in arg_list]

    nodes = parse_ast_args(cls, ast_args)
    if cls == tree.Wrap:
        return nodes[0]

    return nodes


def parse_ast_args(cls, ast_args) -> Union[tree.AstNode, List[tree.AstNode]]:

    if cls == tree.Declaration and len(ast_args) >= 3:
        # We deal with chained declarations here (`int a = b = 1;`). We want two separate variable declarations.
        var_type, identifier, expr = ast_args
        if isinstance(expr, tree.Assignment):
            # We should raise an error somehow if there's no previous declaration of the variable here.
            # A good solution would maintain a mapping to the original source code so we can show where the error is.
            # We want to move the assignment node one up so it is **sibling** to this declaration node.
            # Then the declaration should be made with the value of the assigned variable.
            ast_args[2] = tree.Identifier(expr.identifier.name)
            return [expr, *parse_ast_args(cls, ast_args)]

    if cls == tree.Function:
        # Sometimes we don't have function arguments. I don't know how to handle it but here, rearranging args order.
        assert len(ast_args) in {3, 4}
        if len(ast_args) == 4:
            # Swap function args and body so it works with our class' constructor default args.
            ast_args[2], ast_args[3] = ast_args[3], ast_args[2]

    if cls == tree.Expr and any(op in ast_args for op in tree.BinOp.OPERATORS):
        # We want to parse 4 / 3 * 2 with left-associativity. (it should output 2)
        # It means we need to parse the multiplication first
        *left_hand_side, op, right_hand_side = ast_args
        assert op in tree.BinOp.OPERATORS, "Operator should be in second place in the token list"

        if len(left_hand_side) > 1:
            # We need to parse something like 1 + 2 + 3 + 4
            # When making the recursive call we need to use [0] to avoid creatng an additional list.
            left_hand_side = parse_ast_args(cls, left_hand_side)[0]
        else:
            # The left hand side is a single expression, it was already parsed into an ast.
            left_hand_side = left_hand_side[0]

        return [tree.BinOp(left_hand_side, op, right_hand_side)]

    # We 'unnest' the structure - these classes are abstract so we are rly interested in what they contain.
    if cls == tree.Expr:
        assert len(ast_args) == 1
        return ast_args
    if cls == tree.Statement:
        return ast_args

    # Hack. Esp since some 'class_name' refer to functions.
    return [cls(*ast_args)]
