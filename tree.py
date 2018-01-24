"""Note our method to go from parsing output to AST expects to find a class in this file for each grammar expression."""

from typing import Union, List


class AstNode:
    # A set of strings that we can discard after parsing.
    # Ex: in 'var a = 2', we don't need 'var' when building our Assignment node.
    SYNTAX_STRINGS = {'=', ';', ',', '', '"', "'", '(', ')', '()', '{', '}', '{}', 'return', 'if', 'else', 'for',
                      # I'm not sure anymore why I need whitespace characters here. Removing does break tests though ;).
                      ' ', '\n'}

    @property
    def children(self):
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


class Statement(AstNode):
    pass


class Expr(Statement):
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

    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return f'{self.__class__.__name__}({self.value})'


class Char(Expr):

    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return f'{self.__class__.__name__}({self.value})'


class Assignment(Expr):

    def __init__(self, identifier: Identifier, value: Expr):
        self.identifier = identifier
        self.value = value

    @property
    def children(self):
        return [self.identifier, self.value]

    def __str__(self):
        return f'{self.__class__.__name__}'


class Declaration(Statement):

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

    def __init__(self, return_type: str, name: Identifier, body: List[Statement],
                 args: Union['FunctionArgs', None] = None):
        self.return_type = return_type
        self.name = name
        self.args = args if args is not None else FunctionArgs()
        self.body = BodyBlock(body)

    @property
    def children(self):
        return [self.name, self.body, self.args]


class BodyBlock(AstNode):
    # Name is lame, to avoid conflict with Block defined in the grammar...

    def __init__(self, statements: List[Statement]):
        self.statements = statements

    @property
    def children(self):
        return self.statements


class FunctionCall(Expr):

    def __init__(self, function_id: Identifier, args: Union['FunctionCallArgs', None] = None):
        self.function_id = function_id
        self.args = args

    @property
    def children(self):
        return [self.function_id, self.args]


class Return(Statement):

    def __init__(self, value: Expr):
        self.value = value

    def __str__(self):
        return f'{self.__class__.__name__}({self.value})'

    @property
    def children(self):
        return [self.value]


class If(Statement):

    def __init__(self, condition, if_block, else_block=None):
        self.condition = condition
        self.if_block = if_block
        self.else_block = else_block

    @property
    def children(self):
        return [self.condition, self.if_block] + ([self.else_block] if self.else_block is not None else [])


class FunctionArgs(AstNode):

    def __init__(self, *args: Declaration):
        self.args = args

    @property
    def children(self):
        return self.args


class FunctionCallArgs(AstNode):

    def __init__(self, *args):
        self.args = args

    @property
    def children(self):
        return self.args


class ForLoop(Statement):

    def __init__(self, for_init: Union[Declaration, Assignment], for_condition: Expr, for_increment: Assignment,
                 for_body: BodyBlock):
        self.for_init = for_init
        self.for_condition = for_condition
        self.for_increment = for_increment
        self.for_body = for_body

    @property
    def children(self):
        return [self.for_init, self.for_condition, self.for_increment, self.for_body]


def ControlFlowBody(statement_or_block=None):
    if statement_or_block is None:
        # This is an empty if block with braces.
        return BodyBlock([])
    if isinstance(statement_or_block, Statement):
        return BodyBlock([statement_or_block])
    else:
        return BodyBlock(statement_or_block)


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


def Noop(ast_or_terminal_token):
    return ast_or_terminal_token


# Noop because we dont want to create a node for these. They were just here to make the grammar clearer.
SimpleExpr = Noop
Operator = Noop
UnaryOperator = Noop
Type = Noop
ForInit = Noop

Block = reduce_to_list

# This was created during the Great Battle of Left Recursion and Left Associativity.
Expr2 = Expr


def ast_to_str(ast: AstNode, depth=0):
    """Return a pretty-print representation of an AST"""
    indent = ' ' * 2
    # Each node class is responsible for providing a __str__ function.
    extra_break = '\n' if ast.children else ''
    return indent * depth + str(ast) + extra_break + '\n'.join(
        [ast_to_str(child, depth=depth + 1) for child in ast.children])
