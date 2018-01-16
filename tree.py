"""Note our method to go from parsing output to AST expects to find a class in this file for each grammar expression."""

from llvmlite import ir
from typing import Callable, Any, Union


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

    def walk(self):
        """Traverse the ast depth-first and yield the nodes."""
        yield self
        for child in self.children:
            yield from child.walk()


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
    # TODO: the *value* of this class is debatable as well (like Statement)
    # I think it should be an abstract class and Integer, String, etc should inherit from it.

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


class String(AstNode):
    syntax_strings = {'"'}

    def __init__(self, value: str):
        self.value = value

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


class Declaration(AstNode):

    syntax_strings = {'var', '='}

    def __init__(self, identifier: Identifier, value: Union[Value, None]=None):
        self.identifier = identifier
        self.value = value

    @property
    def children(self):
        return [self.identifier] if self.value is None else [self.identifier, self.value]

    def __str__(self):
        return f'{self.__class__.__name__}'

class BinOp(AstNode):

    def __init__(self, operation, left, right):
        self.operation = operation
        self.left = left
        self.right = right

    def children(self):
        return [self.left, self.right]


class Statement(AstNode):
    # TODO: Does this actually add value?? I DONT THINK SO. LAME.
    # Maybe the value it should have is provide a way to have any number of children (lines of code)?

    def __init__(self, stuff):
        self.content = stuff

    @property
    def children(self):
        return [self.content]


class Function(AstNode):

    syntax_strings = {'func', '()', '(', ')', '{', '}'}

    def __init__(self, name: Identifier, body: Statement):
        self.name = name
        self.body = body

    @property
    def children(self):
        return [self.name, self.body]


class Return(AstNode):

    syntax_strings = {'return'}

    def __init__(self, value: Statement):
        self.value = value

    def __str__(self):
        return f'{self.__class__.__name__}({self.value})'

    @property
    def children(self):
        return [self.value]


def ast_to_str(ast: AstNode, depth=0):
    """Return a pretty-print representation of an AST"""
    indent = ' ' * 2
    # Each node class is responsible for providing a __str__ function.
    extra_break = '\n' if ast.children else ''
    return indent * depth + str(ast) + extra_break + '\n'.join([ast_to_str(child, depth=depth+1) for child in ast.children])


def function_to_llvm(node: Function, module: ir.Module):
    assert module is not None
    f_type = ir.FunctionType(ir.IntType(64), tuple([]))
    # node.name is a Identifier node. So node.name.name. Thumbs up.
    f = ir.Function(module, f_type, node.name.name)
    block = f.append_basic_block(name='entry')
    builder = ir.IRBuilder(block)
    to_llvm(node.body, builder, module)
    return module


def statement_to_llvm(node: Statement, builder: ir.IRBuilder, module: ir.Module):
    # TODO: fix this along with the Statement node (mostly nonsense atm).
    return to_llvm(node.content, builder, module)


def return_to_llvm(node: Return, builder: ir.IRBuilder):
    """This function modifies builder inplace. It's a bit weird as it's not super consistent with other converters."""
    builder.ret(to_llvm(node.value, builder))


def value_to_llvm(node: Value):
    return to_llvm(node.value)


def string_to_llvm(node):
    # TODO: maybe do int arithmetic before.
    pass


def to_llvm(node: AstNode, builder: Union[ir.IRBuilder, None]=None, module: Union[ir.Module, None]=None):
    if isinstance(node, Function):
        return function_to_llvm(node, module)
    if isinstance(node, Integer):
        return integer_to_llvm(node)
    if isinstance(node, Return):
        return return_to_llvm(node, builder)
    if isinstance(node, Value):
        return value_to_llvm(node)
    if isinstance(node, Statement):
        return statement_to_llvm(node, builder, module)
    if isinstance(node, Wrap):
        module = ir.Module('generated', )
        # I got the triple from compiling a C program on my machine.
        module.triple = "x86_64-unknown-linux-gnu"
        return to_llvm(node.content, module=module)
    if isinstance(node, String):
        return string_to_llvm(node)


def integer_to_llvm(node: Integer):
    # TODO: mb some kind of optimization on the number of bits. 64 is the safe I-dont-wanna-hear-about-it way.
    i_type = ir.IntType(64)
    return ir.Constant(i_type, node.value)

