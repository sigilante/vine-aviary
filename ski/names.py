#!/usr/bin/env python3
"""Names the static parts of a term, so that a net copies a name where it would have
copied a structure.

    main, defs = names.name(term, least=2)

Every subterm of a closed term of S, K and I is itself closed, so any of them can be a
definition. A subterm is named when it is an application in argument position (or the
whole term), is in normal form, and has at least `least` leaves. `defs` maps each name to
its term, in which named arguments are again references; `main` is the term so rewritten.

Only normal forms are named, on purpose. A reference is expanded afresh at each use, so
naming a term that still has work in it would repeat the work at every use, and reduction
by need would lose its sharing. A normal form has no work in it to repeat.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from net import ARITY, Ref

BIG = 10 ** 9


def name(term, least=2):
    # Equal subterms get one number (hash-consing), children before parents.
    number, info = {}, []   # info[n] = (leaf or None, f, a, size, normal, head, nargs)
    by_id = {}
    stack = [term]
    while stack:
        t = stack[-1]
        if id(t) in by_id and isinstance(t, tuple):
            stack.pop()
            continue
        if not isinstance(t, tuple):
            stack.pop()
            if t not in number:
                number[t] = len(info)
                info.append((t, None, None, 1, True, t, 0))
            continue
        f, a = t
        fn = by_id.get(id(f)) if isinstance(f, tuple) else number.get(f)
        an = by_id.get(id(a)) if isinstance(a, tuple) else number.get(a)
        if fn is None or an is None:
            if an is None:
                stack.append(a)
            if fn is None:
                stack.append(f)
            continue
        stack.pop()
        key = (fn, an)
        if key not in number:
            _, _, _, fs, fnorm, head, nargs = info[fn]
            _, _, _, asz, anorm, _, _ = info[an]
            under = nargs + 1 < ARITY[head] if isinstance(head, str) else True
            number[key] = len(info)
            info.append((None, fn, an, min(fs + asz, BIG), fnorm and anorm and under, head, nargs + 1))
        by_id[id(t)] = number[key]
    root = by_id[id(term)] if isinstance(term, tuple) else number[term]

    named = lambda n: info[n][0] is None and info[n][4] and info[n][3] >= least
    inline, defs = [None] * len(info), {}
    for n, (leaf, f, a, *_rest) in enumerate(info):
        if leaf is not None:
            inline[n] = leaf
        else:
            inline[n] = (inline[f], Ref(a) if named(a) else inline[a])
    for n in range(len(info)):
        if named(n):
            defs[n] = inline[n]
    main = Ref(root) if named(root) else inline[root]
    # Keep only the definitions the main term can reach.
    keep, todo = {}, [main]
    while todo:
        t = todo.pop()
        if isinstance(t, Ref):
            if t.k not in keep:
                keep[t.k] = defs[t.k]
                todo.append(defs[t.k])
        elif isinstance(t, tuple):
            todo.extend(t)
    return main, keep
