#!/usr/bin/env python3
"""The lowering of ski: to the IVM's agents (ivy.py), run on the IVM itself.

    ivm_check.py [N] [--names] [--demand]     (IVM: the ivm binary; default `ivm` on the path)
    ivm_check.py --skijack [t0 ...]           (needs skijack and aviary_kernel)

Every term of S, K, I and two atoms up to size N (default 5) is lowered, 500 terms to a
program, and run by `ivm run`. Each printed line must be the term's normal form, and the
IVM must raise no error flag.

- Without --demand the table is ski.rules. The terms are those on which reducing every
  pair in rounds stops (within caps), and the normal form is the one that gives.
- With --demand the table is lazy.rules, which carries the demand in the net. The terms
  are all those with a normal form by tree reduction, including the ones that do not stop
  under ski.rules, and the table machine, every pair fired, must give that normal form too.
- With --names the terms' subterms are named first (`inets.ski.name_subterms`), so references to nets are
  exercised: normal subterms without --demand, every subterm with it.

Also printed: the IVM's interactions beside the table machine's for the same terms. The
IVM's count includes starting each term and printing its answer; that part is measured by
running the answers alone and taken off.

--skijack runs programs of SKIjack's `tower` on the IVM by lazy.rules, with every subterm
named: the program applied to one atom for each constructor of its result must print the
normal form the reference reducer gives.
"""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ivy
from machine import run, system, show, parse, name_subterms
from check import terms, lo_normal_form

IVM = os.environ.get("IVM", "ivm")
KINDS = ("Total", "Annihilate", "Commute", "Copy", "Erase", "Graft", "Extrinsic")


def run_ivm(program, directory):
    path = os.path.join(directory, "program.iv")
    open(path, "w").write(program)
    r = subprocess.run([IVM, "run", path], capture_output=True, text=True, stdin=subprocess.DEVNULL)
    stats = {}
    for line in r.stderr.split("\n"):
        parts = line.split()
        if len(parts) == 2 and parts[0] in KINDS:
            stats[parts[0]] = int(parts[1].replace("_", ""))
    # A flag is reported as "Error: ..."; a crash of the IVM is a non-zero exit.
    return r.stdout.split("\n"), stats, "Error" in r.stderr or r.returncode != 0, r.stderr


def main(n_max, named, demand):
    table = system(demand)
    memo, batch, want = {}, [], []
    ran = skipped = wrong = 0
    ours = {}
    theirs = dict.fromkeys(KINDS, 0)
    printing = dict.fromkeys(KINDS, 0)

    def flush(directory):
        nonlocal wrong
        if not batch:
            return
        defs = {}
        mains = []
        for t in batch:
            if named:
                # Each term's names are kept apart by numbering them from where the last stopped.
                main, d = name_subterms(t, any_term=demand)
                shift = len(defs) and max(defs) + 1
                move = lambda u: ivy.Ref(u.name + shift) if isinstance(u, ivy.Ref) else ((move(u[0]), move(u[1])) if isinstance(u, tuple) else u)
                defs.update({k + shift: move(v) for k, v in d.items()})
                mains.append(move(main))
            else:
                mains.append(t)
        lines, stats, error, log = run_ivm(ivy.lower(ivy.emit(mains, defs, demand), table), directory)
        if error or len(lines) < len(batch):
            wrong += len(batch)
            print("THE IVM RAISED A FLAG, STOPPED, OR PRINTED TOO FEW LINES:", log[-300:])
        else:
            for t, w, got in zip(batch, want, lines):
                if got != w:
                    wrong += 1
                    print(f"WRONG on the IVM: {show(t)} gives {got!r}, not {w}")
        for k in KINDS:
            theirs[k] += stats.get(k, 0)
        # The same answers lowered as they stand: nothing to reduce, only to print.
        _, stats, error, log = run_ivm(ivy.lower(ivy.emit([parse(w) for w in want], None, demand), table), directory)
        for k in KINDS:
            printing[k] += stats.get(k, 0)
        batch.clear()
        want.clear()

    with tempfile.TemporaryDirectory() as directory:
        for n in range(1, n_max + 1):
            for t in terms(["S", "K", "I", 0, 1], n, memo):
                if demand:
                    nf, _ = lo_normal_form(t)
                    if nf is None:
                        skipped += 1
                        continue
                # More than check.py's cap: lazy.rules takes more interactions.
                r = run(t, "lazy" if demand else "rounds", direct=True, max_interactions=50000)
                if not r.result.finished:
                    if demand:
                        wrong += 1
                        print("DID NOT STOP on the table machine:", show(t))
                    skipped += 1
                    continue
                if demand and r.term != nf:
                    wrong += 1
                    print("WRONG on the table machine:", show(t))
                ran += 1
                for k, v in r.result.counts.items():
                    ours[k] = ours.get(k, 0) + v
                batch.append(t)
                want.append(show(r.term))
                if len(batch) == 500:
                    flush(directory)
        flush(directory)
    which = "lazy.rules" if demand else "ski.rules"
    why = "have no normal form within the caps" if demand else "do not stop all at once"
    print(f"{which}; S, K, I and two atoms, sizes <= {n_max}{', subterms named' if named else ''}: {ran} terms run on the IVM "
          f"({skipped} {why} and are not run); {wrong} wrong")
    total = sum(ours.values())
    print(f"  the table machine, all at once: {total} interactions ({', '.join(f'{k} {v}' for k, v in ours.items() if v)})")
    work = {k: theirs[k] - printing[k] for k in KINDS}
    print(f"  the IVM: {theirs['Total']} interactions, of which {printing['Total']} are spent starting and printing "
          f"(measured by running the answers alone)")
    print(f"  the IVM, reduction alone: {work['Total']} interactions ({', '.join(f'{k.lower()} {work[k]}' for k in KINDS[1:])}), "
          f"{work['Total'] / max(total, 1):.1f} for each of the table machine's")
    return wrong


def skijack_programs(which):
    import pathlib
    import skijack
    from skijack.expand import expand_program
    from skijack.parser import parse
    from skijack.run import run_level0
    from aviary_kernel.terms import App, Atom
    from skijack_check import convert
    source = pathlib.Path(skijack.__file__).parent / "corpus" / "tower.ascii.ski"
    program = expand_program(parse(source.read_text(encoding="utf-8"), "ascii"))
    bad = 0
    with tempfile.TemporaryDirectory() as directory:
        for name in which:
            p = program.level1[name]
            marked, ours = p.term, convert(p.term)
            for i in range(len(p.result_type.ctors)):
                marked, ours = App(marked, Atom(f"m{i}")), (ours, i)
            want = show(convert(run_level0(marked, 3_000_000, whnf_only=False).term))
            main, defs = name_subterms(ours, any_term=True)
            lines, stats, error, log = run_ivm(ivy.lower(ivy.emit([main], defs, True), system(True)), directory)
            ok = bool(lines) and lines[0] == want and not error
            bad |= not ok
            print(f"{name} on the IVM, applied to {len(p.result_type.ctors)} atoms: {lines[0][:60]}; "
                  f"{'equal to' if ok else 'DIFFERENT FROM'} the reference's normal form; "
                  f"{stats.get('Total', 0)} interactions ({', '.join(f'{k.lower()} {stats.get(k, 0)}' for k in KINDS[1:])})")
    return bad


if __name__ == "__main__":
    flags = ("--names", "--demand", "--skijack")
    args = [a for a in sys.argv[1:] if a not in flags]
    if "--skijack" in sys.argv:
        sys.exit(bool(skijack_programs(args or ["t0"])))
    sys.exit(bool(main(int(args[0]) if args else 5, "--names" in sys.argv, "--demand" in sys.argv)))
