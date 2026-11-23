#!/usr/bin/env python3
"""Checks of the ski: system (ski.rules) and its machine (net.py).

    check.py table            the table is complete and its rules are typed
    check.py census [N]       every term of S, K, I up to size N (default 6)
    check.py atoms [N]        the same with two atoms among the leaves (default 5)
    check.py cases            a few named terms
    check.py all              the three above with their defaults

In the census, for every term with a leftmost-outermost normal form (tree reduction,
within caps) reduction by need must stop and give that normal form. Reduction of every
pair at once must give it too whenever it stops within its caps. Where the reference
reducer `aviary_kernel` is installed, its number of contractions is compared with the
number of `contract` rules applied by need.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table
from net import Net, Stop, parse, show

ARITY = {"S": 3, "K": 2, "I": 1}


def spine(t):
    args = []
    while isinstance(t, tuple):
        args.append(t[1])
        t = t[0]
    args.reverse()
    return t, args


def unspine(head, args):
    for a in args:
        head = (head, a)
    return head


def lo_step(t):
    """One leftmost-outermost step of tree reduction, or None if t is normal."""
    head, args = spine(t)
    n = ARITY.get(head)
    if n is not None and len(args) >= n:
        if head == "I":
            new = args[0]
        elif head == "K":
            new = args[0]
        else:
            new = ((args[0], args[2]), (args[1], args[2]))
        return unspine(new, args[n:])
    for i, a in enumerate(args):
        b = lo_step(a)
        if b is not None:
            return unspine(head, args[:i] + [b] + args[i + 1:])
    return None


def size(t):
    n, stack = 0, [t]
    while stack:
        u = stack.pop()
        if isinstance(u, tuple):
            stack.extend(u)
        else:
            n += 1
    return n


def lo_normal_form(t, cap=2000, max_size=20000):
    """(normal form, steps), or (None, steps) at a cap."""
    for steps in range(cap):
        u = lo_step(t)
        if u is None:
            return t, steps
        t = u
        if size(t) > max_size:
            return None, steps
    return None, cap


def terms(leaves, n, memo):
    if n not in memo:
        memo[n] = list(leaves) if n == 1 else [
            (a, b) for k in range(1, n) for a in terms(leaves, k, memo) for b in terms(leaves, n - k, memo)]
    return memo[n]


def reference():
    """aviary_kernel's reducer as a function term -> (status, contractions), or None."""
    try:
        from aviary_kernel.reduce import reduce
        from aviary_kernel.environment import Environment
        from aviary_kernel.terms import Atom, App
    except ImportError:
        return None

    def convert(t):
        if isinstance(t, tuple):
            return App(convert(t[0]), convert(t[1]))
        return Atom(t if isinstance(t, str) else f"m{t}")

    def run(t, cap):
        r = reduce(convert(t), Environment(), max_steps=cap, max_size=10 ** 6)
        return r.status.value, r.steps

    return run


def census(label, leaves, n_max):
    agents, rules = table.load(table.default_path())
    ref = reference()
    memo = {}
    ran = wrong = unstopped = skipped = 0
    every_ok = every_wrong = every_unstopped = 0
    same = fewer = more = 0
    worst = (0, 0, None)
    used = {}
    for n in range(1, n_max + 1):
        for t in terms(leaves, n, memo):
            nf, steps = lo_normal_form(t)
            if nf is None:
                skipped += 1
                continue
            ran += 1
            net = Net.of(t, agents, rules)
            try:
                net.normalize(20000, 50000)
                if net.read() != nf:
                    wrong += 1
                    print("WRONG by need:", show(t))
            except Stop:
                unstopped += 1
                print("DID NOT STOP by need:", show(t))
                continue
            for line, k in net.used.items():
                used[line] = used.get(line, 0) + k
            need = net.counts.get("contract", 0)
            if ref:
                status, contractions = ref(t, 5000)
                if status == "normal":
                    same += need == contractions
                    fewer += need < contractions
                    more += need > contractions
            if steps - need > worst[0] - worst[1]:
                worst = (steps, need, t)
            net = Net.of(t, agents, rules)
            try:
                net.run_all(20000, 50000)
                if net.read() == nf:
                    every_ok += 1
                else:
                    every_wrong += 1
                    print("WRONG all at once:", show(t))
                for line, k in net.used.items():
                    used[line] = used.get(line, 0) + k
            except Stop:
                every_unstopped += 1
    print(f"{label}, sizes <= {n_max}: {ran} terms with a normal form ({skipped} without one within the caps, not run)")
    print(f"  by need: {ran - wrong - unstopped} give it, {wrong} wrong, {unstopped} did not stop")
    print(f"  all at once: {every_ok} give it, {every_wrong} wrong, {every_unstopped} did not stop within the caps")
    if ref:
        print(f"  contractions by need against the reference reducer's: equal for {same}, fewer for {fewer}, more for {more}")
    if worst[2] is not None:
        print(f"  largest saving over tree reduction: {worst[0]} steps against {worst[1]} contractions, for {show(worst[2])}")
    unused = [r.title() for r in rules if r.line not in used]
    print("  rules never applied: " + ("; ".join(unused) if unused else "none"))
    return wrong or unstopped or every_wrong or more


def cases():
    agents, rules = table.load(table.default_path())
    bad = 0
    omega = "```SII``SII"
    rows = [
        ("K I Ω: a dropped argument that never stops", "``KI" + omega, "I"),
        ("S K K x", "```SKK0", "0"),
        ("S I I x: the argument is used twice", "```SII0", "`00"),
        ("an atom applied stays", "```K012", "`02"),
        ("K x Ω under an atom", "`0``K1" + omega, "`01"),
    ]
    for name, text, want in rows:
        net = Net.of(parse(text), agents, rules)
        net.normalize()
        got = show(net.read())
        ok = got == want
        bad |= not ok
        print(f"{name}: {text} -> {got} ({'as expected' if ok else 'EXPECTED ' + want}); {net.fired} interactions, {net.counts.get('contract', 0)} contractions")
    net = Net.of(parse("``KI" + omega), agents, rules)
    try:
        net.run_all(20000, 50000)
        print("K I Ω all at once: stopped, which is not expected")
        bad = 1
    except Stop:
        print(f"K I Ω all at once: still running after {net.fired} interactions, as expected")
    # Shared work: (S I I) applied to a term that takes work to evaluate.
    work = "```SKK```SKK```SKK0"
    twice = "```SII" + work
    one, two = Net.of(parse(work), agents, rules), Net.of(parse(twice), agents, rules)
    one.normalize()
    two.normalize()
    _, tree = lo_normal_form(parse(twice))
    print(f"a shared argument: evaluating it once takes {one.counts['contract']} contractions; used twice, {two.counts['contract']} by need, {tree} by tree reduction")
    return bad


def check_table():
    agents, rules = table.load(table.default_path())
    problems = table.check(agents, rules)
    values = sum(1 for a in agents.values() if a.value)
    print(f"table: {len(agents)} agents ({values} values, {len(agents) - values} consumers), {len(rules)} rules, {len(problems)} problems")
    for p in problems:
        print("  PROBLEM:", p)
    return len(problems)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else None
    rc = 0
    if mode in ("table", "all"):
        rc |= bool(check_table())
    if mode in ("census", "all"):
        rc |= bool(census("S, K, I", ["S", "K", "I"], n or 6))
    if mode in ("atoms", "all"):
        rc |= bool(census("S, K, I and two atoms", ["S", "K", "I", 0, 1], n or 5))
    if mode in ("cases", "all"):
        rc |= bool(cases())
    sys.exit(rc)
