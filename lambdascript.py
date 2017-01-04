# -*- coding: utf-8 -*-

import ast

class DuplicateDeclarationError(Exception):
    pass
class CircularReferenceError(Exception):
    pass

def parse(s, context=globals()):
    # A lambdascript cell is like a Python dictionary without enclosing braces
    node = ast.parse('{'+s+'}', mode='eval').body
    # Extraction of names (some of them are reserved symbols
    # Make a copy of context (generally globals()) and remove variables with
    #    same name (in order to avoid confusion).
    names, reserved, context2 = {}, {}, dict(context)
    nonlambda = []
    for k, v in zip([k.id for k in node.keys], node.values):
        if len(k) >= 2 and k[:2] == "__":
            if k in reserved:
                # TODO: print 's'
                raise DuplicateDeclarationError(
                        # TODO: find a better sentence
                        "Several uses of the special symbol '%s'"
                        + " in the same environment"
                        % k )
            reserved[k] = v
        else:
            if k in names:
                # TODO: print 's'
                raise DuplicateDeclarationError(
                        "Several declarations for the symbol '%s'"
                        + " in the same environment"
                        % k )
            names[k] = v
            if not isinstance(v, ast.Lambda):
                nonlambda.append(k)
            if k in context2:
                del context2[k]
    # Extraction of free variables (but not global ones)
    freevars = {}
    body = [
            ast.Assign(targets=[ast.Name(id=k, ctx=ast.Store())],
                       value=ast.Lambda(args=ast.arguments(
                           args=[], vararg=None, kwonlyargs=[],
                           kw_defaults=[], kwarg=None, defaults=[]),
                       body=ast.Num(n=0)))
            for k in names ]
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
        exec(compile(M, '<string>', mode='exec'), context2)
        body.pop()
        freevars[k] = context2['__lambdascript__']().__code__.co_freevars
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
    print(D)



a = 42

source = """
        f: lambda n: 2*n + b,
        g2: lambda n: f(n)+1,
        a: f(3),
        h: g2(4)+a,
        b:5
        """
parse(source)
