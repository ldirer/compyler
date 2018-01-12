from llvmlite import ir

class AstNode:

    # A set of strings that we can discard after parsing.
    # Ex: in 'var a = 2', we don't need 'var' when building our Assignment node.
    # TODO: obv. that's very fragile design. Mb we could have a global variable for that (not sure it's class specific).
    syntax_strings = {}

    @property
    def children(self):
        #TODO: should be a way to get children. Mb write a first design, see what I need and come back
        return []

    def __str__(self):
        """A string for the node alone (without its subtree)"""
        return f'{self.__class__.__name__}'


class Wrap(AstNode):
    """I could have named this `Program` as it just wraps our program (we need a top-level node!)."""

    def __init__(self, content):
        self.content = content

    @property
    def children(self):
        return [self.content]



class Identifier(AstNode):

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f'{self.__class__.__name__}(name={self.name})'


class Value(AstNode):

    def __init__(self, value):
        self.value = value

    @property
    def children(self):
        return [self.value]


class Integer(AstNode):
    def __init__(self, value):
        self.value = int(value)

    def __str__(self):
        return f'{self.__class__.__name__}({self.value})'


class Assignment(AstNode):

    syntax_strings = {'var', '='}

    def __init__(self, identifier: Identifier, value: Value):
        self.identifier = identifier
        self.value = value

    @property
    def children(self):
        return [self.identifier, self.value]

    def __str__(self):
        return f'{self.__class__.__name__}'


class Statement(AstNode):

    def __init__(self, stuff):
        pass


class FunctionDef(AstNode):

    def __init__(self, name: Identifier, body: Statement):
        pass






def ast_to_str(ast: AstNode, depth=0):
    """Return a pretty-print representation of an AST"""
    indent = ' ' * 2
    # Each node class is responsible for providing a __str__ function.
    extra_break = '\n' if ast.children else ''
    return indent * depth + str(ast) + extra_break + '\n'.join([ast_to_str(child, depth=depth+1) for child in ast.children])


def function_to_llvm(node: FunctionDef):
    pass


def ast_to_llvm_ir(ast: AstNode):
    """
    http://llvmlite.pydata.org/en/latest/user-guide/ir/examples.html
    :return: llvm ir code as a string
    """
    # > A module can contain any number of function declarations and definitions, global variables and metadata.
    module = ir.Module(name='generated')
    builder = ir.IRBuilder(block)
    for child in ast.children:
        # This will modify module inplace
        child.to_llvm_ir(module)
    return str(module)


