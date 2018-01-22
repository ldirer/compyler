"""Note our method to go from parsing output to AST expects to find a class in this file for each grammar expression."""

from llvmlite import ir
from typing import Union, List


class AstNode:
    # A set of strings that we can discard after parsing.
    # Ex: in 'var a = 2', we don't need 'var' when building our Assignment node.
    # TODO: obv. that's very fragile design. Mb we could have a global variable for that (not sure it's class specific).
    syntax_strings = {}

    @property
    def children(self):
        # TODO: should be a way to get children. Mb write a first design, see what I need and come back
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

    def __init__(self, statements: List['Statement']):
        self.statements = statements

    @property
    def children(self):
        return self.statements


class Identifier(AstNode):

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f'{self.__class__.__name__}(name={self.name})'


class Expr(AstNode):
    # TODO: the *value* of this class is debatable as well (like Statement)
    # I think it should be an abstract class and Integer, String, etc should inherit from it.

    @property
    def children(self):
        return []


class Integer(Expr):
    def __init__(self, value):
        self.value = int(value)

    def __str__(self):
        return f'{self.__class__.__name__}({self.value})'


class String(Expr):
    syntax_strings = {'"'}

    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return f'{self.__class__.__name__}({self.value})'


class Statement(AstNode):

    syntax_strings = {';'}


class Char(Expr):
    syntax_strings = {"'"}

    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return f'{self.__class__.__name__}({self.value})'


class Assignment(Expr):
    syntax_strings = {'=', ';', ''}

    def __init__(self, identifier: Identifier, value: Expr):
        self.identifier = identifier
        self.value = value

    @property
    def children(self):
        return [self.identifier, self.value]

    def __str__(self):
        return f'{self.__class__.__name__}'


class Declaration(Statement):
    syntax_strings = {'=', ';', ''}

    def __init__(self, type: str, identifier: Identifier, value: Union[Expr, None] = None):
        self.type = type
        self.identifier = identifier
        self.value = value

    @property
    def children(self):
        return [self.identifier] if self.value is None else [self.identifier, self.value]

    def __str__(self):
        return f'{self.__class__.__name__}'


class UnOp(AstNode):
    NOT = '!'
    PLUS = '+'
    COMPLEMENT = '~'
    MINUS = '-'

    def __init__(self, operation, operand):
        self.operation = operation
        self.operand = operand

    @property
    def children(self):
        return [self.operand]


class BinOp(AstNode):
    MULTIPLY = '*'
    ADD = '+'
    SUBSTRACT = '-'
    DIVIDE = '/'
    MODULO = '%'

    GTE = '>='
    LTE = '<='
    GT = '>'
    LT = '<'
    EQ = '=='
    NEQ = '!='

    OPERATORS = [MULTIPLY, ADD, SUBSTRACT, DIVIDE, MODULO, GT, LT, GTE, LTE, EQ, NEQ]

    syntax_strings = {'(', ')'}

    def __init__(self, left, operation, right):
        self.operation = operation
        self.left = left
        self.right = right

    @property
    def children(self):
        return [self.left, self.right]

    def __str__(self):
        return f'{self.__class__.__name__}({self.operation})'



class Function(Statement):
    syntax_strings = {'()', '(', ')', '{', '}'}

    def __init__(self, return_type: str, name: Identifier, body: List[Statement],
                 args: Union['FunctionArgs', None]=None):
        self.return_type = return_type
        self.name = name
        self.args = args if args is not None else FunctionArgs()
        self.body = FunctionBody(body)

    @property
    def children(self):
        return [self.name, self.body, self.args]


class FunctionBody(AstNode):

    def __init__(self, statements: List[Statement]):
        self.statements = statements

    @property
    def children(self):
        return self.statements


class FunctionCall(Expr):
    syntax_strings = {'(', ')', '()'}

    def __init__(self, function_id: Identifier, args: Union['FunctionCallArgs', None]=None):
        self.function_id = function_id
        self.args = args if args is not None else []

    @property
    def children(self):
        return [self.function_id] + self.args


class Return(Statement):
    syntax_strings = {'return', ';'}

    def __init__(self, value: Expr):
        self.value = value

    def __str__(self):
        return f'{self.__class__.__name__}({self.value})'

    @property
    def children(self):
        return [self.value]


class FunctionArgs(AstNode):
    syntax_strings = {','}

    def __init__(self, *args: Declaration):
        self.args = args

    @property
    def children(self):
        return self.args


class FunctionCallArgs(AstNode):
    syntax_strings = {','}

    def __init__(self, *args):
        self.args = args

    @property
    def children(self):
        return self.args


def Operator(op_string):
    # Noop because we dont want to create a node for this. It was just to make the grammar clearer.
    return op_string


Operator.syntax_strings = {}


def Type(type_string):
    # Noop because we dont want to create a node for this. It was just to make the grammar clearer.
    return type_string


Type.syntax_strings = {}


def Noop(ast_or_terminal_token):
    return ast_or_terminal_token


Noop.syntax_strings = {'(', ')', ';', ''}

SimpleExpr = Noop
Operator = Noop
UnaryOperator = Noop
Expr2 = Expr


def reduce_to_list(item, items=None):
    """Typically we will have three statements (lines of code basically) in a row, giving us:
    Block line1 [Block line2 [Block line3]]

    And we want a list of statements at the end of the day
    """
    if items is None:
        items = []
    if isinstance(item, list):
        return item + items
    else:
        return [item] + items


reduce_to_list.syntax_strings = {' ', '\n'}  # We really want \s here (any whitespace char).
Block = reduce_to_list


def ast_to_str(ast: AstNode, depth=0):
    """Return a pretty-print representation of an AST"""
    indent = ' ' * 2
    # Each node class is responsible for providing a __str__ function.
    extra_break = '\n' if ast.children else ''
    return indent * depth + str(ast) + extra_break + '\n'.join(
        [ast_to_str(child, depth=depth + 1) for child in ast.children])


class LlvmConverterState:

    def __init__(self):
        self.functions = {}  # A map function name => llvmlite function object
        self.arg_identifiers_to_index = {}
        # TODO: add identifier_to_llvm_value for vars. Make arg_identifiers... consistent with it!
        # We should even have only ONE way of handling functions, args variables and variables.
        # Mb some kind of scope concerns later on though.
        # We dont have the args variables when we're just writing the function declaration though
        self.identifier_to_var = {}


llvm_converter_state = LlvmConverterState()


def function_to_llvm(node: Function, module: ir.Module):
    assert module is not None

    args = to_llvm(node.args, None, module) if node.args is not None else tuple([])
    # Hardcoded type...
    f_type = ir.FunctionType(ir.IntType(64), args)

    # node.name is a Identifier node. So node.name.name. Thumbs up.
    f = ir.Function(module, f_type, node.name.name)
    llvm_converter_state.functions[node.name.name] = f
    # TODO: Does variable declaration in function arguments require a block?... I dont have one until now.
    # I think argument declaration requires
    block = f.append_basic_block(name='entry')
    builder = ir.IRBuilder(block)
    to_llvm(node.body, builder, module)
    return module


def return_to_llvm(node: Return, builder: ir.IRBuilder):
    """This function modifies builder inplace. It's a bit weird as it's not super consistent with other converters."""
    return builder.ret(to_llvm(node.value, builder))


def string_to_llvm(node):
    # TODO: maybe do int arithmetic before.
    pass


def char_to_llvm(node, builder, module):
    # A char in C is just an integer (with 8 bits of storage but we dont care about this)
    return to_llvm(Integer(ord(node.value)), builder, module)


type_to_llvm_type = {'int': ir.IntType(64),
                     'char': ir.IntType(64)   # Not accurate/optimal. Whatever.
                     }

def to_llvm(node: AstNode, builder: Union[ir.IRBuilder, None] = None, module: Union[ir.Module, None] = None):
    if isinstance(node, Function):
        return function_to_llvm(node, module)
    if isinstance(node, FunctionBody):
        for statement in node.statements:
            to_llvm(statement, builder, module)
        # Note we dont return anything here! it does not matter, the Function case will return for us.
    if isinstance(node, FunctionArgs):
        # We need the llvmlite version of the declarations to define the function.
        arg_list = []
        for i, arg in enumerate(node.args):
            # arg is a Declaration, but we dont want to handle it like a regular Declaration since it's a function arg.
            # Namely we don't want to allocate memory now, we just want the type of the variable.
            # Also we want to keep the name of the arg here for future Identifier nodes!
            llvm_converter_state.arg_identifiers_to_index[arg.identifier.name] = i
            arg_list.append(type_to_llvm_type[arg.type])
        return tuple(arg_list)
    if isinstance(node, FunctionCall):
        args = [] if not node.args else to_llvm(node.args, builder, module)
        return builder.call(llvm_converter_state.functions[node.function_id.name], args)
    if isinstance(node, FunctionCallArgs):
        arg_list = []
        for arg in node.args:
            arg_list.append(to_llvm(arg, builder, module))
        return arg_list
    if isinstance(node, Declaration):
        variable = builder.alloca(type_to_llvm_type[node.type], name=node.identifier.name)
        llvm_converter_state.identifier_to_var[node.identifier.name] = variable
        if node.value is not None:
            return builder.store(to_llvm(node.value, builder, module), variable)
        else:
            return variable

    if isinstance(node, Assignment):
        return builder.store(to_llvm(node.value, builder, module),
                             llvm_converter_state.identifier_to_var[node.identifier.name])

    if isinstance(node, Integer):
        return integer_to_llvm(node)
    if isinstance(node, Return):
        return return_to_llvm(node, builder)
    if isinstance(node, Char):
        return char_to_llvm(node, builder, module)
    if isinstance(node, BinOp):
        left = to_llvm(node.left, builder, module)
        right = to_llvm(node.right, builder, module)

        operation_to_method = {
            BinOp.ADD: builder.add,
            BinOp.SUBSTRACT: builder.sub,
            BinOp.MULTIPLY: builder.mul,
            # sdiv for signed integer division. I think there's a subtlety here.
            BinOp.DIVIDE: builder.sdiv,
            BinOp.MODULO: builder.srem
        }

        try:
            method = operation_to_method[node.operation]
        except KeyError:
            def compare_and_upcast(left, right):
                return builder.zext(builder.icmp_signed(node.operation, left, right), ir.IntType(64))

            method = compare_and_upcast

        return method(left, right)

    if isinstance(node, UnOp):
        def logical_not(value):
            """!a is 1 if a is 0, else 0."""
            # We need to upcast the IntType(1) that icmp_signed returns so it matches the `main` return type.
            # Or whatever type is required.
            return builder.zext(builder.icmp_signed('==', value, ir.Constant(ir.IntType(64), 0)), ir.IntType(64))

        # +(expr) is a noop --> (expr). This is probably not very accurate.
        operation_to_method = {UnOp.MINUS: builder.neg, UnOp.COMPLEMENT: builder.not_, UnOp.PLUS: lambda v: v,
                               UnOp.NOT: logical_not}

        method = operation_to_method[node.operation]
        value = to_llvm(node.operand, builder, module)
        return method(value)
    if isinstance(node, Wrap):
        module = ir.Module('generated', )
        # I got the triple from compiling a C program on my machine.
        module.triple = "x86_64-unknown-linux-gnu"
        for statement in node.children:
            to_llvm(statement, module=module)
        return module
    if isinstance(node, String):
        return string_to_llvm(node)

    if isinstance(node, Identifier):
        # Here we're just using an identifier 'alone' in an expr (not assigning to it) -> We want to get the value!
        try:
            var = llvm_converter_state.identifier_to_var[node.name]
        except KeyError:
            # This is just for function arguments! Not any variable...
            return builder.function.args[llvm_converter_state.arg_identifiers_to_index[node.name]]

        return builder.load(var)

        # # TODO: I just hardocded that to see the rest of the output.
        # return ir.Constant(ir.IntType(64), 172)


def integer_to_llvm(node: Integer):
    # TODO: mb some kind of optimization on the number of bits. 64 is the safe I-dont-wanna-hear-about-it way.
    i_type = ir.IntType(64)
    return ir.Constant(i_type, node.value)
