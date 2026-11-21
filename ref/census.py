#!/usr/bin/env python3
"""Census: pure-S interaction nets against tree reduction.
For every S-term of size <= N that normalizes (leftmost-outermost tree reduction within a cap),
run the net in parallel rounds and record total interactions, S-steps, duplications, rounds
(parallel depth), breadth = total / rounds, and check the read-back normal form."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from snet import build, run, readback
sys.setrecursionlimit(1000000)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 9
CAP = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
memo = {}
def terms(n):
    if n in memo: return memo[n]
    out = ['S'] if n == 1 else [(a, b) for k in range(1, n) for a in terms(k) for b in terms(n - k)]
    memo[n] = out; return out
def size(t): return 1 if t == 'S' else size(t[0]) + size(t[1])
def lo_step(t):
    """Leftmost-outermost step, or None if normal."""
    sp = []; h = t
    while h != 'S': sp.append(h[1]); h = h[0]
    sp.reverse()
    if len(sp) >= 3:
        x, y, z = sp[0], sp[1], sp[2]; r = ((x, z), (y, z))
        for a in sp[3:]: r = (r, a)
        return r
    for i, a in enumerate(sp):
        a2 = lo_step(a)
        if a2 is not None:
            r = 'S'
            for j, b in enumerate(sp): r = (r, a2 if j == i else b)
            return r
    return None
def lo_nf(t, cap):
    n = 0
    while n < cap:
        u = lo_step(t)
        if u is None: return t, n
        t = u; n += 1
        if size(t) > 20000: return None, n
    return None, n
def main():
    rows = []; bad = 0; nonnorm = 0
    t0 = time.time()
    for n in range(1, N + 1):
        for t in terms(n):
            nf, steps = lo_nf(t, CAP)
            if nf is None: nonnorm += 1; continue
            net, root = build(t)
            st = run(net)
            if not st['normal']: bad += 1; continue
            rb = readback(net, net.link[(root, 0)])
            if rb != nf: bad += 1; print('MISMATCH', t); continue
            rows.append((n, steps, st['sstep'], st['dup'], st['total'], st['rounds'], size(nf)))
    print(f'sizes <= {N}: normalizing {len(rows)}, non-normalizing within cap {nonnorm}, mismatches {bad} ({time.time()-t0:.1f}s)')
    import statistics as S
    for n in range(1, N + 1):
        R = [r for r in rows if r[0] == n]
        if not R: continue
        print(f'size {n:2d}: {len(R):6d} terms | LO steps max {max(r[1] for r in R):5d} | net S-steps max {max(r[2] for r in R):5d} '
              f'| total max {max(r[4] for r in R):6d} | rounds max {max(r[5] for r in R):5d} | nf size max {max(r[6] for r in R):6d}')
    worst = sorted(rows, key=lambda r: -r[1])[:5]
    print('largest LO step counts (size, LO, netS, dup, total, rounds, nfsize):'); [print(' ', w) for w in worst]

if __name__ == '__main__':
    main()
