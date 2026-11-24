#!/usr/bin/env python3
"""Programs compiled by SKIjack, run on the ski: system by need and compared with
SKIjack's reference reducer.

    skijack_check.py [t0 t1 t2 ...]      (default: t0 t1; t2 takes a quarter of an hour
                                          or so and several GB of memory; not timed)

Needs the `skijack` and `aviary_kernel` packages. The programs are the level-1
declarations of `tower` in SKIjack's corpus: an interpreter written in S, K, I run on a
quoted program (t0), on the quoted unquoter (t1) and on the quoted interpreter itself (t2).

For each program:
- it is reduced by need until its root is a value, and the contractions are counted
  beside the reference reducer's count for the same job; then again with values built
  directly, and with its normal subterms named as well (names.py). All three must take
  the same number of contractions;
- its answer is compared with the reference's. The answer is Scott-encoded, so it is read
  as SKIjack reads it: the program is applied to one atom for each constructor of its
  result type and reduced to normal form, on both machines, and the two normal forms must
  be equal.
"""
import os, pathlib, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table
import names as naming
from net import Net, Stop, show

try:
    import skijack
    from skijack.expand import expand_program
    from skijack.parser import parse
    from skijack.run import run_level0, run_level1
    from aviary_kernel.terms import App, Atom
except ImportError as e:
    sys.exit(f"needs skijack and aviary_kernel: {e}")

CAP = 3_000_000


def convert(t):
    """A reference term as this machine's: names for S, K, I, pairs for applications."""
    out, stack = {}, [t]
    while stack:
        u = stack[-1]
        if id(u) in out:
            stack.pop()
        elif isinstance(u, Atom):
            out[id(u)] = int(u.name[1:]) if u.name.startswith("m") else u.name
            stack.pop()
        elif id(u.fn) in out and id(u.arg) in out:
            out[id(u)] = (out[id(u.fn)], out[id(u.arg)])
            stack.pop()
        else:
            stack.append(u.arg)
            stack.append(u.fn)
    return out[id(t)]


def main(names):
    agents, rules = table.load(table.default_path())
    source = pathlib.Path(skijack.__file__).parent / "corpus" / "tower.ascii.ski"
    program = expand_program(parse(source.read_text(encoding="utf-8"), "ascii"))
    bad = 0
    for name in names:
        p = program.level1[name]
        ref = run_level1(p, CAP)
        term = convert(p.term)
        print(f"{name}: to a value, the reference reducer takes {ref.steps} contractions ({ref.status.value})")
        counts = []
        for label, named, direct in (("as applications", False, False), ("values built directly", False, True),
                                     ("values built directly, normal subterms named", True, True)):
            main, defs = naming.name(term, 2) if named else (term, {})
            net = Net.of(main, agents, rules, defs, direct)
            start = time.time()
            net.head(10 ** 9, 6 * 10 ** 6)
            c = net.counts
            counts.append(c.get("contract", 0))
            print(f"  by need, {label}: {c.get('contract', 0)} contractions, {c.get('collect', 0)} arguments taken, "
                  f"{c.get('copy', 0)} copies, {c.get('expand', 0)} expansions of {len(defs)} names; "
                  f"{net.fired} interactions in all; at most {net.most} nodes; {time.time() - start:.0f} s")
        bad |= len(set(counts)) != 1
        marked, ours = p.term, convert(p.term)
        for i in range(len(p.result_type.ctors)):
            marked, ours = App(marked, Atom(f"m{i}")), (ours, i)
        want = run_level0(marked, CAP, whnf_only=False)
        net = Net.of(ours, agents, rules)
        net.normalize(10 ** 9, 5 * 10 ** 6)
        got = net.read()
        same = want.status.value == "normal" and got == convert(want.term)
        bad |= not same
        text = show(got)
        text = text if len(text) <= 60 else f"{text[:60]}... ({len(text)} characters)"
        print(f"  answer, applied to {len(p.result_type.ctors)} atoms: {text}; "
              f"{'equal to' if same else 'DIFFERENT FROM'} the reference's normal form")
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["t0", "t1"]))
