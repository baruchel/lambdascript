# -*- coding: utf-8 -*-

import ast

class DuplicateDeclarationError(Exception):
    pass
class CircularReferenceError(Exception):
    pass

def parse(s, context=globals(), internal={}):
    """
    s : a (possibly multiline) string containing lambdascript code
    context : the context in which the functions are to be mirrored
    internal : lambdascript global variables
    """
    # A lambdascript cell is like a Python dictionary without enclosing braces
    node = ast.parse('{'+s+'}', mode='eval').body
    # Check if the blocks is a special block (containing global variables)
    if isinstance(node, ast.Set):
        for k in node.elts:
            if (    not isinstance(k, ast.Compare)
                 or len(k.ops) != 1
                 or not isinstance(k.ops[0], ast.Lt)
                 or len(k.comparators) != 1
                 or not isinstance(k.comparators[0], ast.UnaryOp)
                 or not isinstance(k.comparators[0].op, ast.USub)
            ):
                raise SyntaxError()
            n = k.left.id
            try: # CPython3
                v = k.comparators[0].operand.value
            except: # Pypy3
                v = eval(k.comparators[0].operand.id)
            internal[n] = v
        return
    # Extraction of names (some of them are reserved symbols
    names, reserved = {}, {}
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
    # Reference of a lambda in another lambda can now be safely removed
    # from the dictionary 'freevars' because sorting the declarations not
    # care about order between two lambda expressions.
    freevars2 = dict(freevars)
    for k in names:
        if k not in nonlambda:
            freevars2[k] = tuple( i for i in freevars2[k] if i in nonlambda )
    # Sort the declarations
    D = []
    tmp = list(names)
    while tmp:
        for i in range(len(tmp)):
            e = tmp[i]
            ev = freevars2[e]
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
                targets=[ast.Name(id=k, ctx=ast.Store())],
                value=ast.Lambda(args=ast.arguments(
                            args=[], vararg=None, kwonlyargs=[],
                            kw_defaults=[], kwarg=None, defaults=[]),
                          body=ast.Tuple(elts=[ast.Name(id=i, ctx=ast.Load())
                        for i in freevars[k]], ctx=ast.Load()))))
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
    # TODO special symbols
    # TODO curry
    # TODO continuation
    # TODO tail recursion


parse("""

   enable_curry <- False,
   blabla       <- True

        """)


a = 42
c = 3
b = 5

source = """
        f: lambda n: 2*n + b + 3,
        g2: lambda n: f(n)+1,
        a: f(3),
        h: g2(4)+a
        """
parse(source)

print(f(5), g2(5), a, h, b)
b = 0
print(f(5), g2(5), a, h, b)
