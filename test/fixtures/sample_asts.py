"""
A collection of pre-built ASTs for use in testing.
"""

from ctypes import *
from ctree.c.nodes import *
from ctree.cpp.nodes import *

# ---------------------------------------------------------------------------
# integer identity


def identity(x):
    return x


identity_ast = \
    FunctionDecl(c_int(), "identity", [SymbolRef(SymbolRef("x"), c_int())], [
        Return(SymbolRef("x"))
    ])


# ---------------------------------------------------------------------------
# greatest common divisor

def gcd(a, b):
    if b == 0:
        return a
    else:
        return gcd(b, a % b)


gcd_ast = \
    FunctionDecl(c_int(), "gcd", [SymbolRef("a", c_int()), SymbolRef("b", c_int())], [
        If(Eq(SymbolRef('b'), Constant(0)),
           [Return(SymbolRef('a'))],
           [Return(FunctionCall(SymbolRef('gcd'), [SymbolRef('b'), Mod(SymbolRef('a'),
                                                                       SymbolRef('b'))]))])
    ])


# ---------------------------------------------------------------------------
# naive fibonacci

def fib(n):
    if n < 2:
        return n
    else:
        return fib(n - 1) + fib(n - 2)


fib_ast = \
    FunctionDecl(c_int(), "fib", [SymbolRef("n", c_int())], [
        If(Lt(SymbolRef("n"), Constant(2)),
           [Return(SymbolRef("n"))],
           [Return(Add(FunctionCall(SymbolRef("fib"), [Sub(SymbolRef("n"), Constant(1))]),
                       FunctionCall(SymbolRef("fib"), [Sub(SymbolRef("n"), Constant(2))])))])
    ])


# ---------------------------------------------------------------------------
# a zero-argument function

def get_two():
    return 2


get_two_ast = \
    FunctionDecl(c_long(), "get_two", [], [
        Return(Constant(2))
    ])


# ---------------------------------------------------------------------------
# a function with mixed argument types

def choose(p, a, b):
    if p < 0.5:
        return a
    else:
        return b


choose_ast = \
    FunctionDecl(c_long(), "choose",
                 [SymbolRef("p", c_double()), SymbolRef("a", c_long()), SymbolRef("b", c_long())], [
            If(Lt(SymbolRef("p"), Constant(0.5)), [
                Return(SymbolRef("a")),
            ], [
                   Return(SymbolRef("b")),
               ])
        ])


# ---------------------------------------------------------------------------
# a function that takes a numpy array

import math
import numpy as np

def l2norm(A):
    return math.sqrt(sum(x*x for x in A))

l2norm_ast = CFile("generated", [
    CppInclude("math.h"),
    FunctionDecl(c_double(), "l2norm",
        params=[
            SymbolRef("A", np.ctypeslib.ndpointer(np.float64, 1, 12)()),
            SymbolRef("n", c_int()),
        ],
        defn=[
            SymbolRef("sum", c_double()),
            For(Assign(SymbolRef("i", c_int()), Constant(0)),
                Lt(SymbolRef("i"), SymbolRef("n")),
                PostInc(SymbolRef("i")), [
                AddAssign(SymbolRef("sum"),
                          Mul(ArrayRef(SymbolRef("A"), SymbolRef("i")),
                              ArrayRef(SymbolRef("A"), SymbolRef("i")))),
        ]),
        Return( FunctionCall("sqrt", [SymbolRef("sum")]) ),
    ])
])
