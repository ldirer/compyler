"""
I wrote these tests as I was programming to help avoid regressions.

Most of them are 'weak tests' that don't check correctness (just some level of non-brokenness).
"""
from pprint import pprint

from llvmlite import ir

from lexer import read_grammar, parse, to_ast

from tree import ast_to_str, Function, BinOp, UnOp
from llvm_backend import function_to_llvm, to_llvm

simple_assign = 'int valid_identifier = 42;'
invalid_identifier = 'int 911notvalid = 42;'
invalid_identifier_big = """
int valid = 13;
int ok = 12;
int 911notvalid = 42;
int validone = 11;
int again = 10;
"""

simple_function = """
int fibo () {
    return 42;
}"""

multiline_function = """
int sum () {
    int a = 4;
    int b = 2;
    return 1;
}"""

function_declaration_with_args = """
int sum(int a, int b) {
    return a + b;
}"""


function_call = """fibo()"""

# The type is wrong but it should still parse.
assign_string = 'int greetings = "hello";'

# When writing grammar as a string in code, using raw strings mean we don't have to escape backslashes.
with open('C_grammar', 'r') as f:
    g = read_grammar(f.read())
pprint(g)


def test_parser_assignment():
    token_tree, remainder = parse(g, simple_assign)
    assert remainder == ''
    assert token_tree == ['Wrap', ['Block', ['Statement', ['Declaration', ['Type', 'int'], ['Identifier', 'valid_identifier'],
                                                 '=',
                                                 ['Expr', ['Expr2', ['SimpleExpr', ['Integer', '42']]]]], ';']]]

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
    weak_parse_test("60 + 1 - 4")
    weak_parse_test("1 + 2 + 3 + 4 + 5")


def test_parser_binop_parentheses():
    weak_parse_test("(60) > 50")
    weak_parse_test("(60 + 1) >= 50")
    weak_parse_test("((1 + 3) + (60 + 1) * 2) >= 50")


def test_parser_unary():
    weak_parse_test('-1')
    weak_parse_test('+1')
    weak_parse_test('~1')
    weak_parse_test('!1')
    weak_parse_test('~-1')


def test_ast_unary_precedence():

    ast = get_ast('~2 + 3')
    nodes = list(ast.walk())
    assert [n.__class__ for n in nodes if isinstance(n, (UnOp, BinOp))] == [BinOp, UnOp]

    ast = get_ast('~(2 + 3)')
    nodes = list(ast.walk())
    assert [n.__class__ for n in nodes if isinstance(n, (UnOp, BinOp))] == [UnOp, BinOp]


def weak_parse_test(source):
    token_tree, remainder = parse(g, source)
    assert remainder == ''


def test_ast_binop_precedence():
    binop = "(1 + 2) * 3"
    token_tree, remainder = parse(g, binop)
    assert remainder == '', 'Parsing failed, check parser tests.'

    ast = to_ast(token_tree)
    nodes = list(ast.walk())

    expected_order = [BinOp.MULTIPLY, BinOp.ADD]
    assert [node.operation for node in nodes if isinstance(node, BinOp)] == expected_order

    binop_2 = "1 + 2 * 3"
    ast = get_ast(binop_2)
    nodes = list(ast.walk())
    expected_order = [BinOp.ADD, BinOp.MULTIPLY]
    assert [node.operation for node in nodes if isinstance(node, BinOp)] == expected_order

    binop_3 = "1 * 2 + 3"
    ast = get_ast(binop_3)
    nodes = list(ast.walk())
    expected_order = [BinOp.ADD, BinOp.MULTIPLY]
    assert [node.operation for node in nodes if isinstance(node, BinOp)] == expected_order

    binop_3 = "4 / 3 * 2"
    ast = get_ast(binop_3)
    nodes = list(ast.walk())
    expected_order = [BinOp.MULTIPLY, BinOp.DIVIDE]
    assert [node.operation for node in nodes if isinstance(node, BinOp)] == expected_order


def get_ast(source):
    token_tree, remainder = parse(g, source)
    assert remainder == '', 'Parsing failed, check parser tests.'

    return to_ast(token_tree)


def test_parse_and_ast_assignment():
    token_tree, remainder = parse(g, simple_assign)
    # Just check it does not crash for now.
    my_ast = to_ast(token_tree)

    token_tree, remainder = parse(g, assign_string)
    # Just check it does not crash for now.
    my_ast = to_ast(token_tree)


def test_parse_return():
    t_tree, rem = parse(g, 'return 42;')
    assert rem == ''


def test_parse_function():
    # this checks that we can build an ast without crashing (not that it is correct)
    get_ast(simple_function)
    get_ast(multiline_function)


def test_parse_declaration():
    weak_parse_test('int a = 1;')
    weak_parse_test('int a = b = 1;')


def test_parse_function_chained_declaration():
    # Had some trouble with this one
    src = """
    int main() {
    int a = 3;
    int b = a = 4; 
    return (a + b);
}"""
    weak_parse_test(src)

    ast = get_ast(src)
    print(ast_to_str(ast))


def test_parse_function_with_args():
    get_ast(function_declaration_with_args)


def test_parse_function_call():
    get_ast(function_call)


def test_parse_function_call_with_args():
    get_ast("foo(3, 2)")


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


def test_integration_temp():
    code = """int main() {
    return ((3));
    }"""
    ast = get_ast(code)
    ir_code = to_llvm(ast)
    expected_ir_code = """define i64 @"main"() 
{
entry:
  ret i64 3
}"""
    assert expected_ir_code.strip() in str(ir_code)


def test_parse_if():
    src = """int main() {
if (1) return 3; else return 2;
}"""
    ast = get_ast(src)
    ast_to_str(ast)

    src = """int main() { if (1) return 2;}"""
    ast = get_ast(src)
    ast_to_str(ast)


def test_parse_for():
    src = """int main() {
    int i;
    for (i = 0; i < 5; i = i + 1) {
        1;
    }}"""
    ast = get_ast(src)
    ast_to_str(ast)


def test_parse_for_with_without_braces():
    src = """int main() {
    int i;
    for (i = 0; i < 5; i = i + 1) {
        1;
    }}"""
    ast = get_ast(src)
    ast_to_str(ast)

    src_2 = """int main() {
    int i;
    for (i = 0; i < 5; i = i + 1) 
        1;
    }"""

    ast_2 = get_ast(src_2)
    assert ast_to_str(ast_2) == ast_to_str(ast)
