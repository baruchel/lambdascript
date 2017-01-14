"""
A new pure functional language built on the top of Python3.
"""

__version__ = '0.1 alpha'
# -*- coding: utf-8 -*-

import ast, re

class DuplicateDeclarationError(Exception):
    pass
class CircularReferenceError(Exception):
    pass

def __ast_check_tail_recursive__(node, symbol):
    # count all references of 'symbol' (even if not called)
    # count tail-calls of symbols
    n = sum((isinstance(w, ast.Name) and w.id==symbol)
              for w in ast.walk(node))
    def count(no):
        if isinstance(no, ast.IfExp):
            return count(no.body) + count(no.orelse)
        if (
                isinstance(no, ast.Call)
            and isinstance(no.func, ast.Name)
            and no.func.id == symbol ):
            return 1
        return 0
    return (n>0) and (n==count(node.body))

class __TailRecursiveCall__:
    def __init__(self, args):
        self.run = True
        self.args = args
    def __call__(self, *args):
        self.run = True
        self.args = args

def __make_tail_recursive__(__func):
    def __run_function__(*args):
        __T__ = __TailRecursiveCall__(args)
        while __T__.run:
            __T__.run = False
            __result__ = __func(__T__)(*__T__.args)
        return __result__
    return __run_function__

__make_curry__ = lambda f: (lambda n:
 (lambda f: (lambda x: x(x))(lambda y: f(lambda *args: y(y)(*args))))
        (lambda g: lambda *args: f(*args) if len(args) >= n
                                  else lambda *args2: g(*(args+args2)))
        )(f.__code__.co_argcount)

def parse_block(s, context=globals()):
    """
    s : a (possibly multiline) string containing lambdascript code
    context : the context in which the functions are to be mirrored
    internal : lambdascript global variables
    """
    # A lambdascript cell is like a Python dictionary without enclosing braces
    node = ast.parse('{'+s+'}', mode='eval').body
    # Extraction of names (some of them are reserved symbols
    names, reserved = {}, {}
    nonlambda = []
    for k, v in zip([k.id for k in node.keys], node.values):
        if len(k) >= 2 and k[:2] == "__":
            if k in reserved:
                raise DuplicateDeclarationError(
                        # TODO: find a better sentence
                        "Several uses of the special symbol '%s'"
                        + " in the same environment"
                        % k )
            reserved[k] = v
        else:
            if k in names:
                raise DuplicateDeclarationError(
                        "Several declarations for the symbol '%s'"
                        + " in the same environment"
                        % k )
            names[k] = v
            if not isinstance(v, ast.Lambda):
                nonlambda.append(k)
            else: # TODO
                pass
                # parse content of Lambda in order to find the tail-recursion
                # symbol ...( *args )  with Ellipsis(). See:
                # ast.dump(ast.parse("...(3)", mode='eval'))
                # 'Expression(body=Call(func=Ellipsis(), args=[Num(n=3)], keywords=[], starargs=None, kwargs=None))'
                # On pourra aussi chercher ...[k](3)  pour la continuation
    # Extraction of free variables (but not global ones)
    freevars = {}
    body = [
            ast.Assign(targets=[ast.Name(id=k, ctx=ast.Store())],
                       value=ast.Lambda(args=ast.arguments(
                           args=[], vararg=None, kwonlyargs=[],
                           kw_defaults=[], kwarg=None, defaults=[]),
                       body=ast.Num(n=0)))
            for k in names ]
    c = {} # local context
    for k in names:
        # We append a 'Lambda' in front of the expression in case it isn't a Lambda
        # itself (in order to avoid getting the expression evaluated)
        body.append(ast.Return(
            value=ast.Lambda(args=ast.arguments(
                args=[], varargs=None, kwonlyargs=[],
                kw_defaults=[], kwarg=None, defaults=[]), body=names[k])))
        M = ast.Module(body=[ast.FunctionDef(name='__lambdascript__',
            args=ast.arguments(args=[], vararg=None, kwonlyargs=[],
                kw_defaults=[], kwarg=None, defaults=[]), body=body,
            decorator_list=[], returns=None)])
        M = ast.fix_missing_locations(M)
        exec(compile(M, '<string>', mode='exec'), context, c)
        body.pop()
        freevars[k] = c['__lambdascript__']().__code__.co_freevars
    # An O(n^2) algorithm for checking that non-lambda expressions are not
    # involved in circular dependancies (lambda expressions are allowed to be)
    for k in names:
        if k in nonlambda:
            checked = { k:False for k in names }
            stack = [k]
            while stack:
                i = stack.pop()
                checked[i] = True
                j = freevars[i]
                for e in j:
                    if e==k:
                        raise CircularReferenceError(
        "Symbol '"+k+"' involved in a circular reference relation"
                                )
                    if not checked[e]: stack.append(e)
    # Tail-recursion
    for k in names:
        if k not in nonlambda and __ast_check_tail_recursive__(names[k], k):
            for w in ast.walk(names[k]):
                if isinstance(w, ast.Name) and w.id==k:
                    w.id = k
            names[k] = ast.Lambda(args = ast.arguments(
                args=[ast.arg(arg=k, annotation=None)], vararg=None,
                kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[]),
                body= names[k])
            names[k] = ast.Call(func=ast.Name(id='__make_tail_recursive__',
                ctx = ast.Load()), args=[names[k]],
                 keywords=[], starargs=None, kwargs=None)
    # Curry
    for k in names:
        if k not in nonlambda:
            names[k] = ast.Call(func=ast.Name(id='__make_curry__',
                ctx = ast.Load()), args=[names[k]],
                 keywords=[], starargs=None, kwargs=None)
    # Reference of a lambda in another lambda can now be safely removed
    # from the dictionary 'freevars' because sorting the declarations not
    # care about order between two lambda expressions.
    for k in names:
        if k not in nonlambda:
            freevars[k] = tuple( i for i in freevars[k] if i in nonlambda )
    # Sort the declarations
    D = []
    tmp = list(names)
    while tmp:
        for i in range(len(tmp)):
            e = tmp[i]
            ev = freevars[e]
            if all(i in D for i in ev):
                D.append(tmp.pop(i))
                break
        # for/else: raise # useless after previous check
    # Compile all expressions
    body_outer = []
    body_inner = []
    for k in nonlambda:
        body_inner.append(ast.Nonlocal(names=[k]))
    for k in D:
        if k in nonlambda:
            body_outer.append(ast.Assign(targets=[ast.Name(id=k,
                                                  ctx=ast.Store())],
                                         value=ast.Num(n=0)))
            body_inner.append(ast.Assign(targets=[ast.Name(id=k,
                                                  ctx=ast.Store())],
                                         value=names[k]))
        else:
            body_outer.append(ast.Assign(
                targets=[ast.Name(id=k, ctx=ast.Store())], value=names[k]))
            body_inner.append(ast.Assign(
                targets=[ast.Attribute(value=ast.Name(id=k, ctx=ast.Load()),
                                       attr='__code__', ctx=ast.Store())],
                value=ast.Attribute(value=names[k],
                                       attr='__code__', ctx=ast.Load())))
    body_inner.append(ast.Return(value=ast.Dict(
        keys=[ast.Str(s=k) for k in D],
        values=[ast.Name(id=k, ctx=ast.Load()) for k in D])))
    body_outer.append(ast.FunctionDef(name='__inner__', args=ast.arguments(
                            args=[], vararg=None, kwonlyargs=[],
                            kw_defaults=[], kwarg=None, defaults=[]),
                          body=body_inner, decorator_list=[], returns=None))
    body_outer.append(ast.Return(value=ast.Call(
                               func=ast.Name(id='__inner__', ctx=ast.Load()),
                          args=[], keywords=[], starargs=None, kwargs=None)))
    M = ast.Module(body=[ast.FunctionDef(name='__lambdascript__',
        args=ast.arguments(args=[], vararg=None, kwonlyargs=[],
            kw_defaults=[], kwarg=None, defaults=[]), body=body_outer,
        decorator_list=[], returns=None)])
    M = ast.fix_missing_locations(M)
    exec(compile(M, '<string>', mode='exec'), context, c)
    S = c['__lambdascript__']()
    # mirror all symbols in context (generally globals())
    # don't mirror private symbols
    for k in D:
        if k[0] != '_': context[k] = S[k]
    # Parse special symbols (AFTER)
    for k in reserved:
        if k == "__print__":
            E = ast.Expression(body=reserved[k])
            print(eval(compile(E, '<string>', mode='eval'), context, c))


def __markdown_parser(fname):
    in_block = False
    in_fenced = False
    last_empty = True
    re_empty_line = re.compile("^\s*$")
    re_code_line = re.compile("^(    )|\t")
    re_fenced = re.compile("(?P<fenced>[~`]{3,})\s*(?P<lang>[^\s`]+)?")
    block = ""
    fenced = ""
    lang = ""
    ls = 0
    with open(fname, mode='r') as f:
        for n, l in enumerate(f, start=1):
            todo = True
            while todo:
                todo = False
                if in_fenced:
                    if len(l) >= len(fenced) and fenced == l[:len(fenced)]:
                        in_fenced = False
                        in_block = False
                        last_empty = True
                        yield (block, lang, ls, n)
                        lang = ""
                    else: block += l
                elif in_block:
                    if re_code_line.match(l) or re_empty_line.match(l):
                        block += l
                    else:
                        in_block = False
                        yield (block, lang, ls, n-1)
                        lang = ""
                        todo = True
                elif last_empty and re_code_line.match(l):
                    in_block = True
                    last_empty = False
                    lang = "lambdascript"
                    block = l
                    ls = n
                elif len(l) >= 3 and (
                        l[:3] == "~~~" or l[:3] == "```" ):
                    last_empty = False
                    fenced, lang = re_fenced.match(l).groups()
                    if lang == None: lang = "lambdascript"
                    in_block = True
                    in_fenced = True
                    block = ""
                    ls = n
                elif re_empty_line.match(l):
                    last_empty = True
                else:
                    last_empty = False
    if in_block: yield (block, lang, ls, n)


def parse_document(fname, context=globals()):
    for s, lang, ls, le in __markdown_parser(fname):
        try:
            if lang == "python":
                exec(s, context)
            elif lang == "lambdascript":
                parse_block(s, context=context)
        except Exception as e:
            print("Exception encountered during execution"
                    + " of block at lines %d-%d:" % (ls, le))
            raise e

__all__ = ['parse_block', 'parse_document']
