#!/usr/bin/env python3
"""Pure S as an interaction system (no eraser).

Agents (port 0 is principal):
  S            value, principal = output
  S1(x)        value S x,   ports: 0 out, 1 x
  S2(x, y)     value S x y, ports: 0 out, 1 x, 2 y
  A(arg, out)  application, port 0 = function (principal), 1 = argument, 2 = result
  D(o1, o2)    duplicator,  port 0 = input (principal), 1, 2 = copies
Rules (active pair = two principal ports joined):
  A ⋈ S          ->  S1(arg) on out
  A ⋈ S1(x)      ->  S2(x, arg) on out
  A ⋈ S2(x, y)   ->  out := A(A(x, z1), A(y, z2)) with D(z) = (z1, z2)        [the S-step]
  D ⋈ S          ->  S, S
  D ⋈ S1(x)      ->  S1(x1), S1(x2) with D(x) = (x1, x2)
  D ⋈ S2(x, y)   ->  S2(x1, y1), S2(x2, y2) with D(x), D(y)
Every agent consumed is rebuilt or copied: the system never erases.  `run` reduces all active pairs
in parallel rounds; `readback` unfolds sharing into a term."""
import sys
sys.setrecursionlimit(1000000)

class Net:
    def __init__(self):
        self.kind = {}; self.link = {}; self.nid = 0
    def new(self, k):
        self.nid += 1; self.kind[self.nid] = k; return self.nid
    def wire(self, p, q):
        self.link[p] = q; self.link[q] = p
    def delete(self, n):
        del self.kind[n]
        for i in range(3):
            self.link.pop((n, i), None)

def encode(net, t):
    """Return the output port of term t ('S' or (l, r))."""
    if t == 'S':
        n = net.new('S'); return (n, 0)
    a = net.new('A')
    net.wire((a, 0), encode(net, t[0]))
    net.wire((a, 1), encode(net, t[1]))
    return (a, 2)

def build(t):
    net = Net()
    root = net.new('R')
    net.wire((root, 0), encode(net, t))
    return net, root

def active(net):
    out = []
    for n, k in net.kind.items():
        if k == 'A' or k == 'D':
            q = net.link.get((n, 0))
            if q and q[1] == 0 and net.kind[q[0]] in ('S', 'S1', 'S2'):
                out.append((n, q[0]))
    return out

def ext(net, n, i):
    return net.link[(n, i)]

def interact(net, a, v, stats):
    ka, kv = net.kind[a], net.kind[v]
    if ka == 'A':
        arg, out = ext(net, a, 1), ext(net, a, 2)
        if kv == 'S':
            s1 = net.new('S1'); net.delete(a); net.delete(v)
            net.wire((s1, 1), arg); net.wire((s1, 0), out); stats['app'] += 1
        elif kv == 'S1':
            x = ext(net, v, 1); s2 = net.new('S2'); net.delete(a); net.delete(v)
            net.wire((s2, 1), x); net.wire((s2, 2), arg); net.wire((s2, 0), out); stats['app'] += 1
        else:  # S2: the S-step
            x, y = ext(net, v, 1), ext(net, v, 2)
            net.delete(a); net.delete(v)
            d = net.new('D'); a1 = net.new('A'); a2 = net.new('A'); a3 = net.new('A')
            net.wire((d, 0), arg)
            net.wire((a1, 0), x); net.wire((a1, 1), (d, 1))
            net.wire((a2, 0), y); net.wire((a2, 1), (d, 2))
            net.wire((a3, 0), (a1, 2)); net.wire((a3, 1), (a2, 2)); net.wire((a3, 2), out)
            stats['sstep'] += 1
    else:  # D
        o1, o2 = ext(net, a, 1), ext(net, a, 2)
        stats['dup'] += 1
        if kv == 'S':
            net.delete(a); net.delete(v)
            s, t = net.new('S'), net.new('S'); net.wire((s, 0), o1); net.wire((t, 0), o2)
        elif kv == 'S1':
            x = ext(net, v, 1); net.delete(a); net.delete(v)
            d = net.new('D'); p, q = net.new('S1'), net.new('S1')
            net.wire((d, 0), x); net.wire((p, 1), (d, 1)); net.wire((q, 1), (d, 2))
            net.wire((p, 0), o1); net.wire((q, 0), o2)
        else:
            x, y = ext(net, v, 1), ext(net, v, 2); net.delete(a); net.delete(v)
            dx, dy = net.new('D'), net.new('D'); p, q = net.new('S2'), net.new('S2')
            net.wire((dx, 0), x); net.wire((dy, 0), y)
            net.wire((p, 1), (dx, 1)); net.wire((q, 1), (dx, 2))
            net.wire((p, 2), (dy, 1)); net.wire((q, 2), (dy, 2))
            net.wire((p, 0), o1); net.wire((q, 0), o2)

def run(net, max_rounds=100000, max_nodes=2_000_000):
    stats = {'app': 0, 'sstep': 0, 'dup': 0, 'rounds': 0, 'maxnodes': len(net.kind), 'normal': False}
    while stats['rounds'] < max_rounds:
        pairs = active(net)
        if not pairs: stats['normal'] = True; break
        for a, v in pairs: interact(net, a, v, stats)
        stats['rounds'] += 1
        stats['maxnodes'] = max(stats['maxnodes'], len(net.kind))
        if len(net.kind) > max_nodes: break
    stats['total'] = stats['app'] + stats['sstep'] + stats['dup']
    return stats

def readback(net, port):
    n, i = port; k = net.kind[n]
    if k == 'S': return 'S'
    if k == 'S1': return ('S', readback(net, net.link[(n, 1)]))
    if k == 'S2': return (('S', readback(net, net.link[(n, 1)])), readback(net, net.link[(n, 2)]))
    if k == 'A' and i == 2: return (readback(net, net.link[(n, 0)]), readback(net, net.link[(n, 1)]))
    if k == 'D' and i in (1, 2): return readback(net, net.link[(n, 0)])
    raise ValueError((k, i))
