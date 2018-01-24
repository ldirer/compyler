

from tree import Wrap, Function, Return, Integer, Identifier


def test_walk():
    """Test that walking a tree goes through all the nodes."""

    ret = Return(Integer(42))
    function_body = [ret]
    func = Function('int', Identifier('main'), function_body)
    ast = Wrap([func])
    nodes = list(ast.walk())

    # We just test the number of nodes.
    # We could test for order but the order of function identifier and body is not really well-defined.
    assert len(nodes) == 7

