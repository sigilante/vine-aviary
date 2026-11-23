#!/usr/bin/env python3
"""Programs compiled by SKIjack, run on the ski: system by need and compared with
SKIjack's reference reducer.

    skijack_check.py [t0 t1 t2 ...]      (default: t0 t1; t2 takes about 6 minutes and
                                          several GB of memory: 8.6 million nodes at once)

Needs the `skijack` and `aviary_kernel` packages. The programs are the level-1
declarations of `tower` in SKIjack's corpus: an interpreter written in S, K, I run on a
quoted program (t0), and on a quoted interpreter running a quoted program (t1, t2).

For each program:
- it is reduced by need until its root is a value, and the contractions are counted
  beside the reference reducer's count for the same job;
- its answer is compared with the reference's. The answer is Scott-encoded, so it is read
  as SKIjack reads it: the program is applied to one atom for each constructor of its
  result type and reduced to normal form, on both machines, and the two normal forms must
  be equal.
"""
import os, pathlib, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table
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
        net = Net.of(convert(p.term), agents, rules)
        start = time.time()
        net.head(10 ** 9, 5 * 10 ** 6)
        c = net.counts
        print(f"{name}: to a value, the reference reducer takes {ref.steps} contractions ({ref.status.value}); "
              f"by need {c.get('contract', 0)} contractions, {c.get('collect', 0)} arguments taken, "
              f"{c.get('copy', 0)} copies; at most {net.most} nodes; {time.time() - start:.0f} s")
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
