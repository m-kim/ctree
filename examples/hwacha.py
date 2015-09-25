import numpy as np
import ctypes as ct
import ast

from ctree.jit import LazySpecializedFunction, ConcreteSpecializedFunction
from ctree.transformations import PyBasicConversions
from ctree.transforms.declaration_filler import DeclarationFiller
from ctree.c.nodes import CFile
import ctree.c.nodes as C
from ctree.nodes import Project


def get_nd_pointer(arg):
    return np.ctypeslib.ndpointer(arg.dtype, arg.ndim, arg.shape)


class HwachaFN(ConcreteSpecializedFunction):
    def finalize(self, entry_point_name, project_node, entry_typesig):
        self._c_function = self._compile(entry_point_name, project_node, entry_typesig)
        return self

    def __call__(self, *args):
        return self._c_function(*args)


class MapTransformer(ast.NodeTransformer):
    def __init__(self, loopvar, param_dict, retval_name):
        self.loopvar = loopvar
        self.param_dict = param_dict
        self.retval_name = retval_name

    def visit_SymbolRef(self, node):
        if node.name in self.param_dict:
            return C.ArrayRef(node, C.SymbolRef(self.loopvar))
        return node

    def visit_Return(self, node):
        node.value = self.visit(node.value)
        return C.Assign(C.ArrayRef(C.SymbolRef(self.retval_name),
                                   C.SymbolRef(self.loopvar)),
                        node.value)


class HwachaTranslator(LazySpecializedFunction):
    def args_to_subconfig(self, args):
        return tuple(get_nd_pointer(arg) for arg in args)

    def transform(self, py_ast, program_cfg):
        arg_cfg, tune_cfg = program_cfg
        tree = PyBasicConversions().visit(py_ast)
        param_dict = {}
        # Annotate arguments
        for param, type in zip(tree.body[0].params, arg_cfg):
            param.type = type()
            param_dict[param.name] = arg_cfg
        tree.body[0].params.append(C.SymbolRef("retval", arg_cfg[0]()))

        length = np.prod(arg_cfg[0]._shape_)
        transformer = MapTransformer("i", param_dict, "retval")
        body = list(map(transformer.visit, tree.body[0].defn))

        tree.body[0].defn = [C.For(
            C.Assign(C.SymbolRef("i", ct.c_int()), C.Constant(0)),
            C.Lt(C.SymbolRef("i"), C.Constant(length)),
            C.PostInc(C.SymbolRef("i")),
            body=body,
            pragma="ivdep"
        )]


        tree = DeclarationFiller().visit(tree)
        return [CFile("generated", [tree])]

    def finalize(self, transform_result, program_config):
        generated = transform_result[0]
        print(generated)
        proj = Project([generated])
        entry_type = ct.CFUNCTYPE(None, *program_config[0])
        return HwachaFN().finalize("apply", proj, entry_type)


def hwacha_map(fn, *args):
    mapfn = HwachaTranslator.from_function(fn, "map")
    retval = np.empty_like(args[0])
    args += (retval, )
    mapfn(*args)
    return retval


CALIBRATE_COLD = 0x7000
CALIBRATE_HOT  = 0xA000

SIZE = (208 * 156)

# Generate a dummy calibration table, just so there's something
# to execute.
cold = np.full(SIZE, CALIBRATE_COLD, np.int32)
hot  = np.full(SIZE, CALIBRATE_HOT, np.int32)

# Generate a dummy input image, again just so there's something
# to execute.
raw  = np.empty(SIZE, np.int32)

for i in range(SIZE):
    scale = (CALIBRATE_HOT - CALIBRATE_COLD)
    percent = (i % 120) - 10
    raw[i] = scale * (percent / 100.0) + CALIBRATE_COLD
    raw[i] = CALIBRATE_COLD + (i % (int)(scale - 2)) + 1

def gold(cold, hot, raw, flat):
    for i in range(208 * 156):
        _max = hot[i]
        _min = cold[i]
        offset = raw[i] - _min
        scale = _max - _min
        foffset = float(offset)
        fscale = float(scale)
        scaled = foffset / fscale
        scaled = 1.0 if scaled > 1.0 else scaled
        scaled = 0.0 if scaled < 0.0 else scaled
        flat[i] = 255 * scaled

def test_map(cold, hot, raw):
    _max = hot
    _min = cold
    offset = raw - _min
    scale = _max - _min
    foffset = float(offset)
    fscale = float(scale)
    scaled = foffset / fscale
    scaled = 1.0 if scaled > 1.0 else scaled
    scaled = 0.0 if scaled < 0.0 else scaled
    return 255 * scaled


flat_gold = np.empty_like(raw)
gold(cold, hot, raw, flat_gold)

flat_test = hwacha_map(test_map, cold, hot, raw)

np.testing.assert_array_equal(flat_gold, flat_test)
