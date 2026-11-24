#!/usr/bin/env python3
"""Checks of the graph reducer written in Vine (skivine/graph.vi), run on the IVM.

    graph_check.py census [N]          every term of S, K, I up to size N (default 6), and
                                       with two atoms up to size 5
    graph_check.py skijack [t0 ...] [--need]    programs of SKIjack's `tower` (default t0 t1)

Needs VINE and IVM (the vine and ivm binaries; default: on the path). The program is
built once (`vine build bench/graph.vi --lib skivine`) and given a term on each line.

census: each term with a normal form (tree reduction, within caps) must print it, and the
contractions the machine reports must equal those of reduction by need on the table
machine (ski/machine.py, the `inets` package).

skijack (needs the skijack and aviary_kernel packages): each program is reduced until its
head is a value, and its contractions must equal the table machine's by need; the
reference reducer's count is printed beside them. For t2 the table machine is run only
with --need (minutes, and several GB). Then the program applied to one atom for each
constructor of its result is reduced to normal form, which must be the reference's.
"""
import os, re, subprocess, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ski"))
from machine import run as by_table, show, name_subterms
from check import terms, lo_normal_form

VINE = os.environ.get("VINE", "vine")
IVM = os.environ.get("IVM", "ivm")
ROOT = os.path.join(HERE, "..")


def build(directory):
    path = os.path.join(directory, "graph.iv")
    with open(path, "w") as out:
        subprocess.run([VINE, "build", os.path.join(ROOT, "bench", "graph.vi"), "--lib", os.path.join(ROOT, "skivine")],
                       stdout=out, check=True)
    return path


def run(program, lines, heap=None):
    """(output lines, the IVM's statistics, seconds)."""
    start = time.time()
    r = subprocess.run([IVM, "run", program] + (["--heap", str(heap)] if heap else []),
                       input="\n".join(lines) + "\n", capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("the IVM stopped: " + r.stderr[-400:])
    stats = {}
    for line in r.stderr.split("\n"):
        parts = line.split()
        if len(parts) >= 2 and parts[0] in ("Total", "Heap", "Depth"):
            stats[parts[0]] = int(parts[1].replace("_", ""))
    return r.stdout.split("\n"), stats, time.time() - start


def census(n_max):
    todo, memo = [], {}
    for leaves, top in ((["S", "K", "I"], n_max), (["S", "K", "I", 0, 1], min(n_max, 5))):
        for n in range(1, top + 1):
            for t in terms(leaves, n, memo.setdefault(len(leaves), {})):
                nf, _ = lo_normal_form(t)
                if nf is None:
                    continue
                r = by_table(t, "need", max_interactions=20000)
                todo.append((t, show(nf), r.result.counts.get("contract", 0)))
    with tempfile.TemporaryDirectory() as directory:
        out, stats, seconds = run(build(directory), [show(t) for t, _, _ in todo])
    wrong = same = fewer = more = 0
    if len(out) < 2 * len(todo):
        sys.exit(f"the program printed {len(out)} lines for {len(todo)} terms")
    for i, (t, nf, need) in enumerate(todo):
        got, count = out[2 * i], int(out[2 * i + 1].split()[1])
        if got != nf:
            wrong += 1
            print(f"WRONG: {show(t)} gives {got}, not {nf}")
        same += count == need
        fewer += count < need
        more += count > need
    print(f"graph reducer on the IVM; S, K, I to size {n_max} and with two atoms to size {min(n_max, 5)}: "
          f"{len(todo)} terms with a normal form, {wrong} wrong")
    print(f"  contractions against reduction by need on the table machine: equal for {same}, fewer for {fewer}, more for {more}")
    print(f"  {stats.get('Total', 0)} IVM interactions in {seconds:.0f} s")
    return wrong or fewer or more


def skijack_programs(names):
    import pathlib
    import skijack
    from skijack.expand import expand_program
    from skijack.parser import parse
    from skijack.run import run_level0, run_level1
    from aviary_kernel.terms import App, Atom
    from skijack_check import convert
    source = pathlib.Path(skijack.__file__).parent / "corpus" / "tower.ascii.ski"
    program = expand_program(parse(source.read_text(encoding="utf-8"), "ascii"))
    bad = 0
    with tempfile.TemporaryDirectory() as directory:
        built = build(directory)
        for name in names:
            p = program.level1[name]
            ref = run_level1(p, 3_000_000)
            term = convert(p.term)
            marked, ours = p.term, term
            for i in range(len(p.result_type.ctors)):
                marked, ours = App(marked, Atom(f"m{i}")), (ours, i)
            want = show(convert(run_level0(marked, 3_000_000, whnf_only=False).term))
            out, stats, seconds = run(built, ["!" + show(term)])
            count, places = int(out[0].split()[1]), int(out[0].split()[3])
            out2, stats2, seconds2 = run(built, [show(ours)])
            ok = out2[0] == want
            bad |= not ok
            if name == "t2" and "--need" not in sys.argv:
                need = "not run here: it takes minutes and GBs; --need runs it"
            else:
                main, defs = name_subterms(term)
                need = by_table(main, "need", defs, True, deep=False, max_interactions=10 ** 9).result.counts.get("contract", 0)
                bad |= need != count
            print(f"{name}: to a value, {count} contractions on the IVM (by need on the table machine: {need}; "
                  f"the reference reducer: {ref.steps}); "
                  f"{places} places in the store; {stats.get('Total', 0)} IVM interactions, "
                  f"{stats.get('Total', 0) // max(count, 1)} for each contraction; heap {stats.get('Heap', 0) // 2 ** 20} MB; {seconds:.0f} s")
            print(f"  answer, applied to {len(p.result_type.ctors)} atoms: {out2[0][:60]}{'...' if len(out2[0]) > 60 else ''}; "
                  f"{'equal to' if ok else 'DIFFERENT FROM'} the reference's normal form; {stats2.get('Total', 0)} IVM interactions, {seconds2:.0f} s")
    return bad


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "census"
    if mode == "census":
        sys.exit(bool(census(int(sys.argv[2]) if len(sys.argv) > 2 else 6)))
    if mode == "skijack":
        sys.exit(bool(skijack_programs([a for a in sys.argv[2:] if a != "--need"] or ["t0", "t1"])))
    sys.exit("usage: graph_check.py census [N] | skijack [t0 ...]")
