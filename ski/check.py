#!/usr/bin/env python3
"""Checks of the ski: system (ski.rules and lazy.rules), run by the inets package
(machine.py).

    check.py table            the tables are complete and their rules are typed, and are the
                              same as the copies that come with inets
    check.py census [N]       every term of S, K, I up to size N (default 6)
    check.py atoms [N]        the same with two atoms among the leaves (default 5)
    check.py cases            a few named terms; the count of each kind of rule on single
                              rules; sweeping after every interaction changes no answer or
                              contraction; K I Ω does not stop all at once
    check.py demand [N]       lazy.rules, the demand carried in the net (default 6)
    check.py all              all of the above, with their defaults

In the census, for every term with a leftmost-outermost normal form (tree reduction,
within caps) reduction by need must stop and give that normal form, and must do so again,
in the same number of contractions, when the term's normal subterms are named
(`inets.ski.name_subterms`).
Reduction of every pair at once must give it too whenever it stops within its caps, with
and without names. Where the reference
reducer `aviary_kernel` is installed, its number of contractions is compared with the
number of `contract` rules applied by need (without it that line is not printed). By need
must never take more contractions than the reference or than tree reduction; taking fewer
is reported, not refused. `cases` checks the counts of single rules exactly, which is what
would catch a rule counted under the wrong name.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inets
from machine import run, system, parse, show, unfold, name_subterms

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
    rules = system().rules
    ref = reference()
    memo = {}
    ran = wrong = unstopped = skipped = 0
    every_ok = every_wrong = every_unstopped = 0
    same = fewer = more = 0
    named_terms = 0
    worst = (0, 0, None)
    used = {}
    for n in range(1, n_max + 1):
        for t in terms(leaves, n, memo):
            nf, steps = lo_normal_form(t)
            if nf is None:
                skipped += 1
                continue
            ran += 1
            r = run(t, "need", max_interactions=20000)
            if not r.result.finished:
                unstopped += 1
                print("DID NOT STOP by need:", show(t))
                continue
            if r.term != nf:
                wrong += 1
                print("WRONG by need:", show(t))
            tally(used, r)
            need = r.result.counts.get("contract", 0)
            if ref:
                status, contractions = ref(t, 5000)
                if status == "normal":
                    same += need == contractions
                    fewer += need < contractions
                    more += need > contractions
            if need > steps:
                wrong += 1
                print("MORE CONTRACTIONS THAN TREE STEPS:", show(t))
            # With its normal subterms named and values built directly: the same normal form
            # in the same number of contractions.
            main, defs = name_subterms(t)
            r = run(main, "need", defs, True, max_interactions=20000)
            if not r.result.finished:
                unstopped += 1
                print("DID NOT STOP with names:", show(t))
            elif unfold(main, defs) != t or r.term != nf or r.result.counts.get("contract", 0) != need:
                wrong += 1
                print("WRONG with names:", show(t))
            named_terms += bool(defs)
            tally(used, r)
            if steps - need > worst[0] - worst[1]:
                worst = (steps, need, t)
            r = run(t, "rounds", max_interactions=20000)
            if not r.result.finished:
                every_unstopped += 1
                continue
            if r.term == nf:
                every_ok += 1
            else:
                every_wrong += 1
                print("WRONG all at once:", show(t))
            tally(used, r)
            # All at once with names: the same normal form. (Here an eraser can meet a
            # reference, which reduction by need never asks for.)
            r = run(main, "rounds", defs, True, max_interactions=20000)
            if not r.result.finished:
                every_wrong += 1
                print("DID NOT STOP all at once with names:", show(t))
                continue
            if r.term != nf:
                every_wrong += 1
                print("WRONG all at once with names:", show(t))
            tally(used, r)
    print(f"{label}, sizes <= {n_max}: {ran} terms with a normal form ({skipped} without one within the caps, not run)")
    print(f"  by need: {ran - wrong - unstopped} give it, {wrong} wrong, {unstopped} did not stop")
    print(f"  by need with normal subterms named: the same normal forms and contraction counts ({named_terms} terms have something to name)")
    print(f"  all at once, and again with names: {every_ok} give it, {every_wrong} wrong, {every_unstopped} did not stop within the caps")
    if ref:
        print(f"  contractions by need against the reference reducer's: equal for {same}, fewer for {fewer}, more for {more}")
    if worst[2] is not None:
        print(f"  largest saving over tree reduction: {worst[0]} steps against {worst[1]} contractions, for {show(worst[2])}")
    unused = [str(r) for r in rules if r.line not in used]
    print("  rules never applied: " + ("; ".join(unused) if unused else "none"))
    return wrong or unstopped or every_wrong or more


def cases():
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
        r = run(text, "need")
        got = show(r.term)
        ok = got == want
        bad |= not ok
        print(f"{name}: {text} -> {got} ({'as expected' if ok else 'EXPECTED ' + want}); {r.result.interactions} interactions, {r.result.counts.get('contract', 0)} contraction{'' if r.result.counts.get('contract', 0) == 1 else 's'}")
    # One rule at a time: what each is counted as.
    for text, want in (("`I0", {"contract": 1}), ("``K01", {"collect": 1, "contract": 1}),
                       ("```S012", {"collect": 4, "contract": 1}), ("`01", {"collect": 1})):
        r = run(text, "need", deep=False)
        got = {k: v for k, v in r.result.counts.items() if k in ("collect", "contract")}
        if got != want:
            bad = 1
            print(f"COUNTS: {text} gives {got}, expected {want}")
    print("the counts of single rules are as expected" if not bad else "see above")
    # Sweeping after every interaction must change no answer and no contraction count.
    for text in ("```SII```SKK```SKK0", "``KI" + omega, "```S``SKK``SKK```SII0", "````SSS`IS0"):
        runs = []
        for above in (20000, 0):
            r = run(text, "need", sweep_above=above)
            runs.append((show(r.term), r.result.counts.get("contract", 0)))
        if runs[0] != runs[1]:
            bad = 1
            print(f"SWEEPING CHANGED {text}: {runs}")
    r = run("``KI" + omega, "rounds", max_interactions=20000)
    if r.result.finished:
        print("K I Ω all at once: stopped, which is not expected")
        bad = 1
    else:
        print(f"K I Ω all at once: still running after {r.result.interactions} interactions, as expected")
    # Shared work: (S I I) applied to a term that takes work to evaluate.
    work = "```SKK```SKK```SKK0"
    twice = "```SII" + work
    one, two = run(work, "need"), run(twice, "need")
    _, tree = lo_normal_form(parse(twice))
    print(f"a shared argument: evaluating it once takes {one.result.counts['contract']} contractions; used twice, {two.result.counts['contract']} by need, {tree} by tree reduction")
    return bad


def tally(used, r):
    for line, k in r.net.used.items():
        used[line] = used.get(line, 0) + k


def demand(n_max):
    """lazy.rules, which carries the demand in the net, with every pair fired: every term
    with a normal form must stop and give it, in exactly as many contractions as
    leftmost-outermost tree reduction takes steps."""
    rules = system(lazy=True).rules
    memo, used = {}, {}
    wrong, counts = 0, []
    for leaves, top in ((["S", "K", "I"], n_max), (["S", "K", "I", 0, 1], min(n_max, 5))):
        ran = skipped = 0
        counts.append(None)
        for n in range(1, top + 1):
            for t in terms(leaves, n, memo.setdefault(len(leaves), {})):
                nf, steps = lo_normal_form(t)
                counts[-1] = (ran + (nf is not None), skipped + (nf is None))
                if nf is None:
                    skipped += 1
                    continue
                ran += 1
                main, defs = name_subterms(t, any_term=True)
                for term, d, direct in ((t, {}, False), (t, {}, True), (main, defs, True)):
                    r = run(term, "lazy", d, direct, max_interactions=50000)
                    if not r.result.finished:
                        wrong += 1
                        print("DID NOT STOP:", show(t))
                        continue
                    if r.term != nf or r.result.counts.get("contract", 0) != steps:
                        wrong += 1
                        print("WRONG:", show(t), show(r.term), r.result.counts.get("contract", 0), steps)
                    tally(used, r)
    print(f"lazy.rules, every pair fired; S, K, I to size {n_max}: {counts[0][0]} terms with a normal form "
          f"({counts[0][1]} without one within the caps, not run); with two atoms as well, to size {min(n_max, 5)}: "
          f"{counts[1][0]} (these include the first family's terms up to that size); each as applications, with values "
          f"built directly, and with every subterm named: {wrong} wrong")
    print("  each stops with its normal form in as many contractions as tree reduction takes steps" if not wrong else "  see above")
    unused = [str(r) for r in rules if r.line not in used]
    print("  rules never applied: " + ("; ".join(unused) if unused else "none"))
    return wrong


def check_table():
    """The checks of inets (`inets check`): for these signed tables, one rule for each
    consumer and value and no other, and no rule that joins two outputs or two inputs."""
    bad = 0
    for lazy, name in ((False, "ski.rules"), (True, "lazy.rules")):
        table = system(lazy)
        problems = table.check()
        values = sum(1 for a in table.agents.values() if a.is_value)
        print(f"{name}: {len(table.agents)} agents ({values} values, {len(table.agents) - values} consumers), {len(table.rules)} rules, {len(problems)} problems")
        for p in problems:
            print("  PROBLEM:", p)
        bad += len(problems)
        # inets comes with a copy of each table; `inets run ski` uses it.
        rule = lambda r: (str(r), r.count, r.body, r.when)
        copy = inets.bundled("lazy" if lazy else "ski")
        if copy.agents != table.agents or [rule(r) for r in copy.rules] != [rule(r) for r in table.rules]:
            print(f"  PROBLEM: inets' bundled copy of {name} differs from this one")
            bad += 1
        else:
            print(f"  the same agents and rules as the copy that comes with inets {inets.__version__}")
    return bad


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
    if mode in ("demand", "all"):
        rc |= bool(demand(n or 6))
    sys.exit(rc)
