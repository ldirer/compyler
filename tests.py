from pprint import pprint

import pytest
from llvmlite import ir

from lexer import read_grammar, parse, to_ast, ParseError

from tree import ast_to_str, Function, function_to_llvm, to_llvm

simple_assign = 'var valid_identifier = 42'
invalid_identifier = 'var 911notvalid = 42'
invalid_identifier_big = """
var valid = 13
var ok = 12
var 911notvalid = 42
var validone = 11
var again = 10
"""

simple_function = """
func fibo () {
    return 42
}"""

assign_string = 'var greetings = "hello"'

# TODO: read as raw string vs binary?
with open('another_grammar', 'r') as f:
    g = read_grammar(f.read())
pprint(g)


def test_parser_assignment():
    token_tree, remainder = parse(g, simple_assign)
    assert remainder == ''
    assert token_tree == ['Wrap', ['Statement', ['Declaration', 'var', ['Identifier', 'valid_identifier'],
                                                 '=',
                                                 ['Expr', ['Integer', '42']]]]]

    # Note we dont necessarily raise an exception when we cant parse. Just when we cant parse *anything*.
    token_tree, remainder = parse(g, invalid_identifier)
    assert remainder != ''

    token_tree, remainder = parse(g, invalid_identifier_big)
    assert remainder != ''

    token_tree, remainder = parse(g, assign_string)
    assert remainder == ''


def test_parser_binop():
    binop = "40 + 2"
    token_tree, remainder = parse(g, binop)
    assert remainder == ''

def test_parser_binop_associativity():
    binop = "60 + 1 - 4"
    token_tree, remainder = parse(g, binop)
    assert remainder == ''

def test_parser_binop_parentheses():
    binop = "(60 + 1) >= 50"
    token_tree, remainder = parse(g, binop)
    assert remainder == ''

def test_parse_and_ast_assignment():
    token_tree, remainder = parse(g, simple_assign)
    # Just check it does not crash for now.
    my_ast = to_ast(token_tree)

    token_tree, remainder = parse(g, assign_string)
    # Just check it does not crash for now.
    my_ast = to_ast(token_tree)

def test_parse_return():
    t_tree, rem = parse(g, 'return 42')
    assert rem == ''


def test_parse_function():
    token_tree, remainder = parse(g, simple_function)
    assert remainder == ''

    my_ast = to_ast(token_tree)

    print(ast_to_str(my_ast))


def test_function_node_to_llvm():
    token_tree, remainder = parse(g, simple_function)

    my_ast = to_ast(token_tree)
    # Let's get the function node
    func_node = None
    for node in my_ast.walk():
        if isinstance(node, Function):
            func_node = node
            break

    module = ir.Module('test')
    ir_code = function_to_llvm(func_node, module)

    expected_ir_code = """define i64 @"fibo"() 
{
entry:
  ret i64 42
}"""
    assert expected_ir_code.strip() in str(ir_code)


def test_simple_module_function_to_llvm():
    token_tree, remainder = parse(g, simple_function)
    my_ast = to_ast(token_tree)

    ir_code = to_llvm(my_ast)

    expected_ir_code = """define i64 @"fibo"() 
{
entry:
  ret i64 42
}"""
    assert expected_ir_code.strip() in str(ir_code)



