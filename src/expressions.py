"""This code is based on the post from stack overflow:
    https://stackoverflow.com/a/30516254/1735409
   In Debian it requires that you install python3-asteval package
"""
import ast, math

locals =  {key: value for (key,value) in vars(math).items() if key[0] != '_'}
locals.update({"int": int, "abs": abs, "complex": complex, "min": min, "max": max, "pow": pow, "round": round})
# Additionally, we keep the list of our own constants, that should be put
# to packages or header files
defines ={}
# In the next dictionary we keep the original expressions (to be put to comments)
comments={}

def addval(valname,valstr):
    val=exprval(valstr)
    locals[valname]=val
    defines[valname]=val
    comments[valname]=valstr

class Visitor(ast.NodeVisitor):
    def visit(self, node):
        if not isinstance(node, self.whitelist):
            raise ValueError(node)
        return super().visit(node)

    whitelist = (ast.Module, ast.Expr, ast.Load, ast.Expression, ast.Add, ast.Sub, ast.UnaryOp, ast.Num, ast.BinOp,
            ast.Mult, ast.Div, ast.Pow, ast.BitOr, ast.BitAnd, ast.BitXor, ast.USub, ast.UAdd, ast.FloorDiv, ast.Mod,
            ast.LShift, ast.RShift, ast.Invert, ast.Call, ast.Name)


def exprval(expr):
    if any(elem in expr for elem in '\n#') : raise ValueError(expr)
    try:
        node = ast.parse(expr.strip(), mode='eval')
        Visitor().visit(node)
        return eval(compile(node, "<string>", "eval"), {'__builtins__': None}, locals)
    except Exception: raise ValueError(expr)
