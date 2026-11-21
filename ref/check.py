#!/usr/bin/env python3
"""Checks skivine against tree reduction and against the Python net simulator.

  check.py census [N]   every S-term of size <= N (default 9) that normalizes by
                        leftmost-outermost reduction within census.py's caps: the
                        IVM's normal form must equal the tree normal form.
  check.py monsters     two terms with large normal forms: IVM statistics beside
                        the simulator's.
Set VINE to the vine binary (default: vine on PATH)."""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
_argv, sys.argv = sys.argv, sys.argv[:1]  # census.py reads its own arguments at import
from census import terms, lo_nf, size
sys.argv = _argv
from snet import build, run

VINE = os.environ.get("VINE", "vine")
sys.setrecursionlimit(1000000)


def prefix(t):
    out, stack = [], [t]
    while stack:
        u = stack.pop()
        if u == "S":
            out.append("S")
        else:
            out.append("`")
            stack.append(u[1])
            stack.append(u[0])
    return "".join(out)


def vine(program, *args, stdin=None):
    cmd = [VINE, "run", f"bench/{program}.vi", "--lib", "skivine", "--no-perf", *args]
    r = subprocess.run(cmd, cwd=ROOT, input=stdin, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"vine failed: {r.stdout}{r.stderr}")
    return r.stdout + r.stderr


def stat(out, name):
    return int(re.search(rf"{name}\s+([\d_]+)", out).group(1).replace("_", ""))


def census(n_max):
    cases = []
    for n in range(1, n_max + 1):
        for t in terms(n):
            nf, _ = lo_nf(t, 2000)
            if nf is not None:
                cases.append((t, nf))
    out = vine("lines", "--no-stats", stdin="".join(prefix(t) + "\n" for t, _ in cases))
    got = out.split("\n")[: len(cases)]
    bad = [(t, g) for (t, nf), g in zip(cases, got) if g != prefix(nf)]
    for t, g in bad[:10]:
        print("MISMATCH", prefix(t), "->", g)
    print(f"sizes <= {n_max}: {len(cases)} normalizing terms, {len(got)} answers, {len(bad)} mismatches")
    return 1 if bad or len(got) != len(cases) else 0


def app(*xs):
    t = xs[0]
    for x in xs[1:]:
        t = (t, x)
    return t


def monsters():
    S = "S"
    A, T = app(S, S, S), app(S, S)
    rc = 0
    for name, t in [("S A (S S S S S S) S S S", app(S, A, app(S, S, S, S, S, S), S, S, S)),
                    ("S T T S S", app(S, T, T, S, S))]:
        nf, lo = lo_nf(t, 200000)
        net, _ = build(t)
        st = run(net, max_rounds=100000, max_nodes=3_000_000)
        out = vine("normalize", "--breadth-first", "--config", "term", prefix(t), "--config", "print", "false")
        ok = out.split("\n")[0] == f"size {size(nf)}"
        rc |= not ok
        print(f"{name}: normal form of {size(nf)} leaves; size agrees: {ok}")
        print(f"  tree: {lo} leftmost-outermost steps")
        print(f"  simulator: {st['total']} interactions ({st['sstep']} S-steps), {st['rounds']} rounds")
        print(f"  IVM: {stat(out, 'Total')} interactions, depth {stat(out, 'Depth')}, breadth {stat(out, 'Breadth')}")
    return rc


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "census"
    sys.exit(census(int(sys.argv[2]) if len(sys.argv) > 2 else 9) if mode == "census" else monsters())
