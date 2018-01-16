

from tree import AstNode, Wrap, Function, Statement, Return, Integer, Identifier


def test_walk():

    ret = Return(Statement(Integer(42)))
    function_body = Statement(ret)
    func = Function(Identifier('main'), function_body)
    ast = Wrap(func)
    nodes = list(ast.walk())

    # We just test the number of nodes.
    # We could test for order but the order of function identifier and body is not really well-defined.
    assert len(nodes) == 7

