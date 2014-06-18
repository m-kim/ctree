"""
Parses the python AST below, transforms it to C, JITs it, and runs it.
"""

import logging

logging.basicConfig(level=20)

import numpy as np

from ctree.frontend import get_ast
from ctree.c.nodes import *
from ctree.c.types import *
from ctree.dotgen import to_dot
from ctree.transformations import *
from ctree.jit import LazySpecializedFunction
from ctree.types import get_ctree_type

# ---------------------------------------------------------------------------
# Specializer code


class OpTranslator(LazySpecializedFunction):
    def args_to_subconfig(self, args):
        """
        Analyze arguments and return a 'subconfig', a hashable object
        that classifies them. Arguments with identical subconfigs
        might be processed by the same generated code.
        """
        A = args[0]
        return {
            'A_len': len(A),
            'A_dtype': A.dtype,
            'A_ndim': A.ndim,
            'A_shape': A.shape,
        }

    def transform(self, py_ast, program_config):
        """
        Convert the Python AST to a C AST according to the directions
        given in program_config.
        """
        arg_config, tuner_config = program_config
        len_A   = arg_config['A_len']
        A_dtype = arg_config['A_dtype']
        A_ndim  = arg_config['A_ndim']
        A_shape = arg_config['A_shape']

        inner_type = get_ctree_type(A_dtype)
        array_type = NdPointer(A_dtype, A_ndim, A_shape)
        apply_one_typesig = FuncType(inner_type, [inner_type])

        tree = CFile("generated", [
            py_ast.body[0],
            FunctionDecl(Void(), "apply_all",
                         params=[SymbolRef("A", array_type),SymbolRef("B", array_type)],
                         defn=[
                             For(Assign(SymbolRef("i", Int()), Constant(0)),
                                 Lt(SymbolRef("i"), Constant(len_A)),
                                 PostInc(SymbolRef("i")),
                                 [
                                     Assign(ArrayRef(SymbolRef("B"), SymbolRef("i")),
                                            FunctionCall(SymbolRef("apply"), [ArrayRef(SymbolRef("A"),
                                                                                       SymbolRef("i"))])),
                                 ]),
                         ]
            ),
        ])

        tree = PyBasicConversions().visit(tree)

        apply_one = tree.find(FunctionDecl, name="apply")
        apply_one.set_static().set_inline()
        apply_one.set_typesig(apply_one_typesig)

        entry_point_typesig = tree.find(FunctionDecl, name="apply_all").get_type().as_ctype()

        return Project([tree]), entry_point_typesig


class ArrayOp(object):
    """
    A class for managing independent operation on elements
    in numpy arrays.
    """

    def __init__(self):
        """Instantiate translator."""
        self.c_apply_all = OpTranslator(get_ast(self.apply), "apply_all")

    def __call__(self, A, B):
        """Apply the operator to the arguments via a generated function."""
        return self.c_apply_all(A, B)


# ---------------------------------------------------------------------------
# User code

class Doubler(ArrayOp):
    """Double elements of the array."""

    def apply(n):
        return n * 2


def py_doubler(A):
    A *= 2


def main():
    c_doubler = Doubler()

    # doubling doubles
    actual_d = np.ones(12, dtype=np.float64)
    target_d = np.ones(12, dtype=np.float64)
    expected_d = np.ones(12, dtype=np.float64)
    c_doubler(actual_d, target_d)
    py_doubler(expected_d)
    np.testing.assert_array_equal(actual_d, expected_d)

    print("Success.")


if __name__ == '__main__':
    main()
