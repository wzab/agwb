""" This is the simplest implemantation of the module "expressions"
It uses the "eval" function that is unsafe.
A better implementation should be available soon.
"""

locals = {}
def exprval(valstr):
    return eval(valstr,None,locals)
def addval(valname,valstr):
    locals[valname]=exprval(valstr)
