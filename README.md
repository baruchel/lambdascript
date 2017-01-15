# lambdascript
A new pure functional language built on the top of Python3.

_Warning: this is an alpha release; the core of the interpreter is working and should give a precise idea of the language, but the provided program parses the `README.md` file (see the very last line of the code). This is because it should be discussed (on a mailing list) how to use the interpreter: as a standalone command line tool? as a module called from pure Python code? should it be turned into an interpreter or rather compile collection of functions to `.pyc` modules?_ In the initial days after the announcement of the project, I will be watching the `#lambdascript` channel on `irc.freenode.net` for discussing about the further evolutions of the project (answers may take a little time however).

Lambdascript is a new languages (main influence being Haskell) intended to use several Python features and take some benefit of all modules written in Python while programming in a functional style. Since all expressions are Python expressions, one hour should be more than enough to understand the specific philosophy of the language.

Once a public version will be released, it should be able to compile very well-written modules to be used in pure Python programs (or even in other Lambdascript programs).

## Philosophy

Main features of the _Lambdascript_ programming language are:

  * strong emphasis on **literate programming** (a full program being a Markdown document structured with titles, well formatted paragraphs explaining each part of an algorithm, mathematical formulae, pictures, etc.);
  * **lexical binding** inside each block of code in the Markdown document in order to prevent bugs in case some names would be redefined;
  * **tail-recursion** support;
  * **currying** of all functions.

It is intended to work either with CPython3 or PyPy3.

## Installing the module

Just type `pip3 install lambdascript` for installing the module. Two functions are provided: `parse_block` (for evaluating a single block) and `parse_document` (for evaluating a whole markdown document).

## Using the interpreter

The best starting point should be to run Python3 (or Pypy3) and type: `import lambdascript` and then `lambdascript.parse_document("README.md")` where the file `README.md` is the current file (which is a valid Lambdascript file). Then read carefully the current document in order to understand what is happening and make some changes in the `README.md` file in order to experiment (or change the last line of the program in order to adapt it to your needs).

Of course, this will be improved now, but the initial goal was rather to make the language work.

## Language specifications

### Lexical binding

A Lambdascript program is logically split into blocks of code in the whole Markdown document containing it. These blocks should be well commented by using all features of Markdown syntax, but it will be seen later that splitting the code into blocks is not only performed for esthetical reasons; it should also follow some logical principles since different decisions in splitting the code are not technically equivalent.

A Lambdascript block of code is a comma-separated collection of declarations. Unlike Python, Lambdascript does not care at all about indentations; furthermore, it does not care either about order of declarations inside a given code block. An example of a simple block of code is:

    f: lambda n: 2*n,
    x: 42,
    g: lambda n: f(n)+x

Since order does not matter, the very same block could be written:

    g: lambda n: f(n)+x
        # where
        ,    f: lambda n: 2*n
        ,    x: 42

Each declaration being made of a label and any Python expression (generally a lambda function).

In the example above, the most important thing is lexical binding: the three objects `f`, `x` and `g` will be mirrored to the global namespace but the binding by itself is performed in a separate protected namespace, meaning that later changing the content of the global variables `x` or `f` will never break the behaviour of the `g` function. This also apply for recursive functions:

    # Factorial function
    fac : lambda n: n*fac(n-1) if n else 1

Of course, dynamic binding is still performed whenever a symbol was (previously) declared outside of the current block of code (either from pure Python code or as Lambdascript code).

### Symbols

Any valid Python name is a Lambdascript valid name but:

  * a symbol beginning with exactly one underscore is lexically bound without being mirrored to the global namespace;
  * a symbol beginning with two underscores has special meaning and can not be used as an arbitrary name when programming;
  * unlike well-written pure Python code, it should be considered better here to use short single-letter names for auxiliary functions (like `f`, `g` or even `φ`) with a very clear explanation of their role in a Markdown paragraph and keep long explicit name for the main function in each block of code (two reasons for this: it is safe to re-use the same short names in different locations since they will be lexically bound and another idea is to follow mathematical usages and better integrate with mathematical equations, if any, in the Markdown document; furthermore, an explicit long name for the main function will allow the reader to locate it more easely).

Since short names are encouraged, Unicode symbols may be used (for instance greek letters), but there was a bug in the current versions of PyPy3, concerning a rather obscure feature used by the Lambdascript interpreter and Unicode symbols are not supported if the interpreter is run with PyPy3 instead of CPython3 (this bug was [reported and fixed](https://bitbucket.org/pypy/pypy/issues/2457) however and next versions of PyPy3 should work fine in this case too).

### Functions and constants

Since the binding between objects declared in the same block will never be broken, Lambdascript objects are all "constants" in some way; but for convenience reason, this word will be used only for non-lambda objects. Thus Lambdascript objects are either functions or constants. In the first example, `x` is a constant, which is very useful for writing the following block:

    area: lambda r: pi * r**2
        # where
        ,    pi: 3.14159

Technically a constant is anything that is not _initially_ declared as a lambda object, even:

    f: (lambda: lambda n: 2*n)()

An important rule is that constants can't be involved in circular dependancy relations, while functions can; thus the following block is perfectly valid:

    f: lambda x: g(x-1)**2 if x else 1,
    g: lambda x: 2*f(x-1) if x else 1

Furthermore, currying or tail-recusion optimization (see below) will not be applied on constants.

### Currying

Currying is applied on all Lambdascript functions:

    add: lambda a,b: a+b,
    inc: add(1),
    __print__: inc(41) # will print 42

### Tail-recursion

When a lambdascript function is tail-recursive, the recursive call is internally turned into a loop (the function is found to be tail-recursive if and only if all self-reference are tail-calls; optimization does not occur if tail-calls are mixed with non-tail-calls or even with non-called references). Thus loops are avoided in Lambdascript:

    fac: lambda n, f: fac(n-1, n*f) if n else f

Of course the previous function could also be written by using an auxiliary function:

    _fac: lambda n, f: _fac(n-1, n*f) if n else f,
    fac: lambda n: _fac(n, 1)

As an extra benefit, the choice of naming `_fac` the function above will prevent this function to be mirrored in the global namespace. (This is the rule for any symbol beginning with exactly _one_ underscore).

### Special symbols

Special symbols will be extended; right now, only one symbol is provided:

  * `__print__` will print the associated expression _after_ the whole block has been parsed and evaluated;

_TODO_

### Mixing pure Python and Lambdascript

Pure Python can be embed in the Markdown document by using _fenced code blocks_ and indicating `python` as the language of the block. A fenced code block can also have `lambdascript` as its language if required.

The following piece of code is a fenced code block containing Python code (and using the previously defined `fac` function):

~~~python
print(fac(5))
~~~
