import contextlib
from typing import Union

from llvmlite import ir
from llvmlite.ir import NamedValue

from tree import Function, Return, Integer, AstNode, BodyBlock, FunctionArgs, FunctionCall, \
    FunctionCallArgs, Declaration, Assignment, Char, BinOp, UnOp, Wrap, String, Identifier, If, ForLoop


class CustomBuilder(ir.IRBuilder):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    @contextlib.contextmanager
    def _branch_helper_goto_start(self, bbenter, bbexit, add_terminal=True):
        """
        :param add_terminal: If False do not add a terminal to the bbenter block, even if the user did not provide one.
        I'm using it to be able to set a custom terminal after this context manager has been used.
        :return:
        """
        self.position_at_start(bbenter)
        yield bbexit
        if add_terminal:
            if self.basic_block.terminator is None:
                self.branch(bbexit)

    @contextlib.contextmanager
    def for_loop(self, condition_varname: str):
        """I want a behavior similar to `ir.IRBuilder.if_else`.
        I did not find anything for this!! This is a bit weird even though they might be into 'vectorization' since
        llvmlite is maintained by Numba.

        with build.for_loop() as (condition, incr, loop):
            with condition:
                # The condition code. We need a block here as opposed to when we use a if statement.
            with incr:
                # The increment code
            with loop:
                # Do stuff in for loop body

        :param condition_varname: the variable name that will store the computed condition bool in the condition block.
        We need this so we can pre-write branching.

        This code is heavily inspired by `if_else`.
        """
        bb = self.basic_block
        # We need a for condition block because this condition will run several times (unlike in an if statement)
        bbcond = self.append_basic_block(name=bb.name + '.forcondition')
        bbincr = self.append_basic_block(name=bb.name + '.forincrement')
        bbbody = self.append_basic_block(name=bb.name + '.for')
        bbend = self.append_basic_block(name=bb.name + '.endfor')

        # In the current block we always redirect to the for condition. No questions asked.
        self.branch(bbcond)

        # Same at the end of bbincr
        self.position_at_end(bbincr)
        self.branch(bbcond)

        # At the end of the body we go to incr
        self.position_at_end(bbbody)
        self.branch(bbincr)

        # I think the value yielded by _branch_helper is irrelevant: we won't use it and yielding it does affect state.
        for_cond = self._branch_helper_goto_start(bbcond, bbend, add_terminal=False)
        for_incr = self._branch_helper_goto_start(bbincr, bbend)
        for_body = self._branch_helper_goto_start(bbbody, bbend)
        yield for_cond, for_incr, for_body

        # HACK WARNING.
        # I tried using a NamedValue but llvmlite does a good job of deduplicating names so if we use a name twice it
        # will create 2 different names .

        # condition: jump out of loop when not met.
        self.position_at_end(bbcond)
        condition_value = NamedValue(bbcond, ir.IntType(1), condition_varname)
        # the name will be deduplicated: we don't want that (if var already exists we will get var.1)! We override it.
        condition_value._name = condition_varname
        self.cbranch(condition_value, bbbody, bbend)

        self.position_at_end(bbend)


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
    builder = CustomBuilder(block)
    to_llvm(node.body, builder, module)

    # This is to fix empty blocks: they are not accepted by LLVM IR. Every block is supposed to have a terminator.
    # See http://llvm.org/docs/LangRef.html#terminators
    # For instance `if` creates an extra block and it crashes if there's nothing in it.
    if not builder.block.instructions:
        builder.unreachable()
    return module


def return_to_llvm(node: Return, builder: CustomBuilder):
    """This function modifies builder inplace. It's a bit weird as it's not super consistent with other converters."""
    return builder.ret(to_llvm(node.value, builder))


def string_to_llvm(node):
    # TODO: maybe do int arithmetic before.
    pass


def char_to_llvm(node, builder, module):
    # A char in C is just an integer (with 8 bits of storage but we dont care about this)
    return to_llvm(Integer(ord(node.value)), builder, module)


type_to_llvm_type = {'int': ir.IntType(64),
                     'char': ir.IntType(64)  # Not accurate/optimal. Whatever.
                     }


def to_llvm(node: AstNode, builder: Union[CustomBuilder, None] = None, module: Union[ir.Module, None] = None):
    if isinstance(node, Function):
        return function_to_llvm(node, module)
    if isinstance(node, BodyBlock):
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
            to_llvm(statement, builder, module=module)
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
    if isinstance(node, If):
        # We cant just throw the condition to llvm: it expects a type of i1 (boolean, 1/0).
        # If node.condition is an Integer, we compare to 0 for instance.
        predicate = condition_to_llvm(node.condition, builder, module)
        if node.else_block is None:
            with builder.if_then(predicate) as then:
                to_llvm(node.if_block, builder, module)
        else:
            with builder.if_else(predicate) as (then, otherwise):
                with then:
                    to_llvm(node.if_block, builder, module)
                with otherwise:
                    to_llvm(node.else_block, builder, module)

    if isinstance(node, ForLoop):
        cond_varname = 'forcond'
        to_llvm(node.for_init, builder, module)
        with builder.for_loop(cond_varname) as (condition, incr, loop):
            with condition:
                condition_to_llvm(node.for_condition, builder, module, varname=cond_varname)
            with incr:
                to_llvm(node.for_increment, builder, module)
            with loop:
                to_llvm(node.for_body, builder, module)


def condition_to_llvm(node, builder: CustomBuilder, module, varname=''):
    # Might make sense to do it in the AST instead? It's hard to know the type in the AST though.
    # Works out nicely in the end!
    condition = to_llvm(node, builder, module)

    if isinstance(condition.type, ir.IntType):
        # If it's already a boolean (ir.IntType(1)) we cast it to int64. Compare it to 0. Get a boolean. Great!
        return builder.icmp_signed('!=', to_llvm(node, builder, module), ir.Constant(ir.IntType(64), 0), name=varname)
    else:
        raise NotImplementedError('Lazy developer does not implement what does not crash')


def integer_to_llvm(node: Integer):
    # mb some kind of optimization on the number of bits. 64 is the safe I-dont-wanna-hear-about-it way.
    i_type = ir.IntType(64)
    return ir.Constant(i_type, node.value)