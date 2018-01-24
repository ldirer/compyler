from lexer import parse_atom, read_grammar

with open('C_grammar', 'r') as f:
    g = read_grammar(f.read())

def test_parse_block():
    src = """int main() {

    int j;
return j;
}"""
    tree, remainder = parse_atom(g, 'Wrap', src)
    assert not remainder


def test_parse_comment():

    line_comment = """int main() {
    // This is a line comment. Please ignore it.
    return 0;
    }"""
    tree, remainder = parse_atom(g, 'Wrap', line_comment)
    assert not remainder

    inline_comment = """int main() {
    return 0; // This is an inline comment. You may also ignore it.
    }"""
    tree, remainder = parse_atom(g, 'Wrap', inline_comment)
    assert not remainder

def test_parse_statement():
    src = "int i = 0;"
    tree, remainder = parse_atom(g, 'Statement', src)
    assert not remainder
    src = "int i;"
    tree, remainder = parse_atom(g, 'Statement', src)
    assert not remainder


def test_parse_declaration():
    src = "int i = 0"
    tree, remainder = parse_atom(g, 'Declaration', src)
    assert not remainder
    src = "int i"
    tree, remainder = parse_atom(g, 'Declaration', src)
    assert not remainder


def test_parse_for():
    src = "for (i = 0; i < 5; i = i + 1) { j = 3 }"
    tree, remainder = parse_atom(g, 'ForLoop', src)
    assert not remainder


def test_parse_empty_if():
    src = "if (1) { }"
    tree, remainder = parse_atom(g, 'If', src)
    assert not remainder