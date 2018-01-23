from lexer import parse_atom, read_grammar

with open('another_grammar', 'r') as f:
    g = read_grammar(f.read())


def test_parse_for():
    src = "for (i = 0; i < 5; i = i + 1) { j = 3 }"
    tree, remainder = parse_atom(g, 'ForLoop', src)
    assert not remainder
