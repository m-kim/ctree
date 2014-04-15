"""
C preprocessor nodes supported by ctree.
"""

from ctree.nodes import CtreeNode


class CppNode(CtreeNode):
    """Base class for all C Preprocessor nodes in ctree."""

    def codegen(self, indent=0):
        from ctree.cpp.codegen import CppCodeGen

        return CppCodeGen(indent).visit(self)

    def _to_dot(self):
        from ctree.cpp.dotgen import CppDotGen

        return CppDotGen().visit(self)

    def _requires_semicolon(self):
        return False


class CppInclude(CppNode):
    """Represents #include <foo.h>."""

    def __init__(self, target="", angled_brackets=True):
        self.target = target
        self.angled_brackets = angled_brackets


class Comment(CppNode):
    """Represents // foo"""

    def __init__(self, text=""):
        assert "\n" not in text, "Comment only supports single-line comments."
        self.text = text

class CppDefine(CppNode):

    def __init__(self, name=None, params=None, body=None):
        self.name = name
        self.params = params
        self.body = body
        super(CppDefine, self).__init__()
