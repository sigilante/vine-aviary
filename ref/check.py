#!/usr/bin/env python3
"""Checks the Vine programs against reference evaluators written here.

  check.py census [N]   pure S, sizes <= N (default 9), with skivine/ski.vi
  check.py ski [N]      S, K, I, sizes <= N (default 7), with skivine/ski.vi
  check.py birds [N]    all birds, sizes <= N (default 3), with skivine/combinators.vi
  check.py lazy [N]     S, K, I, Y, sizes <= N (default 5), with skivine/lazy.vi, which
                        evaluates in normal order: every term with a leftmost-
                        outermost normal form is run, and Y is included
  check.py rules        each bird applied to as many distinct inert arguments as its
                        arity, so that its rule fires once (the census at size 3
                        fires only rules of arity 1 and 2)
  check.py monsters     two pure-S terms with large normal forms: IVM statistics
                        beside the Python net simulator's

The IVM reduces every redex, including those in arguments that are later dropped.
So the terms that are run are those on which a *strict* evaluator terminates:
`strict` below makes the same calls to `apply` as the Vine program does. For each
such term the IVM's answer must equal the strict evaluator's, and that must equal
the leftmost-outermost normal form. Terms that normalize leftmost-outermost but
not strictly are counted and not run.

Set VINE to the vine binary (default: vine on PATH)."""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
_argv, sys.argv = sys.argv, sys.argv[:1]  # census.py reads its own arguments at import
from census import lo_nf, size
sys.argv = _argv
from snet import build, run
from birds import BIRDS, parse_rule
from gen_combinators_excluded import EXCLUDED

VINE = os.environ.get("VINE", "vine")
sys.setrecursionlimit(1000000)

RULES = {name: (arity, parse_rule(rule)) for name, _, _, arity, rule in BIRDS if name not in EXCLUDED}
FORMALS = "abcdefg"


class Diverged(Exception):
    pass


# Terms are a bird name (str) or a pair (function, argument).

def spine(t):
    args = []
    while not isinstance(t, str):
        args.append(t[1])
        t = t[0]
    args.reverse()
    return t, args


def unspine(head, args):
    for a in args:
        head = (head, a)
    return head


def subst(tree, env):
    if isinstance(tree, str):
        return env.get(tree, tree)
    return (subst(tree[0], env), subst(tree[1], env))


def lo_step(t):
    """One leftmost-outermost step, or None if the term is normal."""
    head, args = spine(t)
    arity, rule = RULES[head]
    if len(args) >= arity:
        return unspine(subst(rule, dict(zip(FORMALS, args[:arity]))), args[arity:])
    for i, a in enumerate(args):
        a2 = lo_step(a)
        if a2 is not None:
            return unspine(head, args[:i] + [a2] + args[i + 1:])
    return None


def tree_size(t):
    return 1 if isinstance(t, str) else tree_size(t[0]) + tree_size(t[1])


def lo_normal_form(t, cap=2000, max_size=20000):
    for _ in range(cap):
        u = lo_step(t)
        if u is None:
            return t
        t = u
        if tree_size(t) > max_size:
            return None
    return None


def strict(t, cap=20000):
    """The value of t when every application is evaluated, or Diverged."""
    calls = 0

    def apply(f, x):
        nonlocal calls
        calls += 1
        if calls > cap:
            raise Diverged
        head, args = f
        arity, rule = RULES[head]
        if len(args) + 1 < arity:
            return (head, args + (x,))
        return ev(rule, dict(zip(FORMALS, args + (x,))))

    def ev(tree, env):
        if isinstance(tree, str):
            return env[tree] if tree in env else (tree, ())
        return apply(ev(tree[0], env), ev(tree[1], env))

    return ev(t, {})


def value_tree(v):
    return unspine(v[0], [value_tree(a) for a in v[1]])


def prefix(t, spaced):
    """Prefix form. `spaced` separates names with spaces (combinators.vi); otherwise
    names are single characters written together (ski.vi)."""
    out, stack = [], [t]
    while stack:
        u = stack.pop()
        if isinstance(u, str):
            out.append(u + (" " if spaced else ""))
        else:
            out.append("`")
            stack.append(u[1])
            stack.append(u[0])
    return "".join(out).strip()


def terms(atoms, n, memo):
    if n not in memo:
        memo[n] = list(atoms) if n == 1 else [
            (a, b) for k in range(1, n) for a in terms(atoms, k, memo) for b in terms(atoms, n - k, memo)]
    return memo[n]


def vine(program, *args, stdin=None):
    cmd = [VINE, "run", f"bench/{program}.vi", "--lib", "skivine", "--no-perf", *args]
    r = subprocess.run(cmd, cwd=ROOT, input=stdin, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        sys.exit(f"vine failed: ...{(r.stdout + r.stderr)[-400:]}")
    return r.stdout + r.stderr


def stat(out, name):
    return int(re.search(rf"{name}\s+([\d_]+)", out).group(1).replace("_", ""))


def census(label, atoms, n_max, program, spaced):
    cases, lazy_only, disagree = [], [], 0
    memo = {}
    for n in range(1, n_max + 1):
        for t in terms(atoms, n, memo):
            nf = lo_normal_form(t)
            try:
                v = value_tree(strict(t))
            except (Diverged, RecursionError):
                if nf is not None:
                    lazy_only.append(t)
                continue
            if nf is not None and v != nf:
                disagree += 1
            cases.append((t, v))
    out = vine(program, "--no-stats", stdin="".join(prefix(t, spaced) + "\n" for t, _ in cases))
    got = out.split("\n")[: len(cases)]
    bad = [(t, g) for (t, v), g in zip(cases, got) if g != prefix(v, spaced)]
    for t, g in bad[:10]:
        print("MISMATCH", prefix(t, spaced), "->", g)
    print(f"{label}, sizes <= {n_max}: {len(cases)} terms run, {len(got)} answers, {len(bad)} mismatches")
    print(f"  strict value differs from the leftmost-outermost normal form: {disagree}")
    print(f"  normalize leftmost-outermost but not strictly (not run): {len(lazy_only)}"
          + (f", e.g. {prefix(lazy_only[0], True)}" if lazy_only else ""))
    return 1 if bad or disagree or len(got) != len(cases) else 0


def lazy(n_max):
    RULES["Y"] = (1, parse_rule("a (Y a)"))
    cases, memo = [], {}
    for n in range(1, n_max + 1):
        for t in terms(["S", "K", "I", "Y"], n, memo):
            nf = lo_normal_form(t, cap=200, max_size=2000)  # smaller caps: Y terms grow fast
            if nf is not None:
                cases.append((t, nf))
    out = vine("lazy_lines", "--no-stats", stdin="".join(prefix(t, False) + "\n" for t, _ in cases))
    got = out.split("\n")[: len(cases)]
    bad = [(t, g) for (t, v), g in zip(cases, got) if g != prefix(v, False)]
    for t, g in bad[:10]:
        print("MISMATCH", prefix(t, False), "->", g)
    with_y = sum("Y" in prefix(t, False) for t, _ in cases)
    print(f"S, K, I, Y terms, sizes <= {n_max}, normal order: {len(cases)} terms run "
          f"({with_y} contain Y), {len(got)} answers, {len(bad)} mismatches")
    return 1 if bad or len(got) != len(cases) else 0


def rules():
    """Each bird on distinct arguments `Ê x`, which stay inert: no rule gives one of
    its formals more than five further arguments, and Ê needs seven."""
    markers = [("Ê", m) for m in ("S", "K", "I", "B", "C", "W", "M")]
    cases = []
    for name, (arity, _) in sorted(RULES.items()):
        t = unspine(name, markers[:arity])
        v = value_tree(strict(t))
        assert v == lo_normal_form(t), name
        cases.append((t, v))
    out = vine("birds", "--no-stats", stdin="".join(prefix(t, True) + "\n" for t, _ in cases))
    got = out.split("\n")[: len(cases)]
    bad = [(t, g) for (t, v), g in zip(cases, got) if g != prefix(v, True)]
    for t, g in bad:
        print("MISMATCH", prefix(t, True), "->", g)
    print(f"{len(cases)} rules fired once each, {len(bad)} mismatches")
    return 1 if bad else 0


def app(*xs):
    return unspine(xs[0], list(xs[1:]))


def monsters():
    S = "S"
    A, T = app(S, S, S), app(S, S)
    rc = 0
    for name, t in [("S A (S S S S S S) S S S", app(S, A, app(S, S, S, S, S, S), S, S, S)),
                    ("S T T S S", app(S, T, T, S, S))]:
        nf, lo = lo_nf(t, 200000)
        net, _ = build(t)
        st = run(net, max_rounds=100000, max_nodes=3_000_000)
        out = vine("normalize", "--breadth-first", "--config", "term", prefix(t, False), "--config", "print", "false")
        ok = out.split("\n")[0] == f"size {size(nf)}"
        rc |= not ok
        print(f"{name}: normal form of {size(nf)} leaves; size agrees: {ok}")
        print(f"  tree: {lo} leftmost-outermost steps")
        print(f"  simulator: {st['total']} interactions ({st['sstep']} S-steps), {st['rounds']} rounds")
        print(f"  IVM: {stat(out, 'Total')} interactions, depth {stat(out, 'Depth')}, breadth {stat(out, 'Breadth')}")
    return rc


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "census"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else None
    if mode == "census":
        sys.exit(census("S terms", ["S"], n or 9, "lines", False))
    if mode == "ski":
        sys.exit(census("S, K, I terms", ["S", "K", "I"], n or 7, "lines", False))
    if mode == "birds":
        sys.exit(census(f"{len(RULES)} birds", sorted(RULES), n or 3, "birds", True))
    if mode == "lazy":
        sys.exit(lazy(n or 5))
    if mode == "rules":
        sys.exit(rules())
    sys.exit(monsters())
