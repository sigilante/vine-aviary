#!/usr/bin/env python3
"""Two experiments: (1) terms with large normal forms (Dance of the Starlings §5.4 'monsters'):
interactions and parallel rounds of the net against leftmost-outermost tree steps; (2) terms
without a normal form: run the net for R rounds and report growth and the stability of the
read-back term near the root (top-termination: the root region stops changing)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from snet import build, run, readback

def readcut(net, port, d):
    """Read back to depth d only (sharing is not unfolded below the cut)."""
    if d == 0: return '?'
    n, i = port; k = net.kind[n]
    if k == 'S': return 'S'
    if k == 'S1': return ('S', readcut(net, net.link[(n, 1)], d - 1))
    if k == 'S2': return (('S', readcut(net, net.link[(n, 1)], d - 2)) if d > 1 else '?', readcut(net, net.link[(n, 2)], d - 1))
    if k == 'A' and i == 2: return (readcut(net, net.link[(n, 0)], d - 1), readcut(net, net.link[(n, 1)], d - 1))
    if k == 'D' and i in (1, 2): return readcut(net, net.link[(n, 0)], d)
    raise ValueError((k, i))
from census import lo_nf, size
sys.setrecursionlimit(1000000)
S = 'S'
def app(*xs):
    t = xs[0]
    for x in xs[1:]: t = (t, x)
    return t
A = app(S, S, S); T = app(S, S)
def show(t, d=4):
    if d == 0: return '…'
    if t == 'S': return 'S'
    return '(' + show(t[0], d - 1) + ' ' + show(t[1], d - 1) + ')'
def cut(t, d):
    if d == 0: return '?'
    if t == 'S': return 'S'
    return (cut(t[0], d - 1), cut(t[1], d - 1))
print('(1) large normal forms')
for name, t in [('S A (S S S S S S) S S S', app(S, A, app(S, S, S, S, S, S), S, S, S)),
                ('S T T S S', app(S, T, T, S, S))]:
    nf, steps = lo_nf(t, 200000)
    net, root = build(t); st = run(net, max_rounds=100000, max_nodes=3_000_000)
    ok = st['normal'] and readback(net, net.link[(root, 0)]) == nf
    print(f'  {name}: LO steps {steps}, nf size {size(nf) if nf else None}; net: S-steps {st["sstep"]}, '
          f'dups {st["dup"]}, total {st["total"]}, rounds {st["rounds"]}, breadth {st["total"] / max(1, st["rounds"]):.1f}, '
          f'max nodes {st["maxnodes"]}, read-back = nf: {ok}')
print('(2) no normal form: stability of the read-back near the root')
for name, t in [('A A A', app(A, A, A)), ('S T T (S T T)', app(S, T, T, app(S, T, T))), ('S A A (S A A)', app(S, A, A, app(S, A, A)))]:
    net, root = build(t)
    prev = None; changes = []
    for R in (5, 10, 20, 40, 80):
        st = run(net, max_rounds=R - (0 if prev is None else prevR), max_nodes=400000)
        prevR = R
        c = readcut(net, net.link[(root, 0)], 6)
        changes.append((R, len(net.kind), c == prev))
        prev = c
    print(f'  {name}: (rounds, net nodes, depth-6 read-back unchanged since previous) {changes}')
