#!/usr/bin/env python3
"""The lowering of ski: to the IVM's agents (ivy.py), run on the IVM itself.

    ivm_check.py [N] [--names]     (IVM: the ivm binary; default `ivm` on the path)

Every term of S, K, I and two atoms up to size N (default 5) on which reducing every pair
at once stops (net.py's `run_all`, within caps) is lowered, 500 terms to a program, and run
by `ivm run`. Each printed line must be the normal form `run_all` gives, and the IVM must
raise no error flag. With --names the terms' normal subterms are named first (names.py),
so references to nets are exercised; the answers must be the same.

Also printed: the IVM's interactions beside the table machine's for the same terms. The
IVM's count includes starting each term and printing its answer; that part is measured by
running the answers alone and taken off.
"""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table, names, ivy
from net import Net, Stop, show
from check import terms

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
    return r.stdout.split("\n"), stats, "Error" in r.stderr, r.stderr


def main(n_max, named):
    agents, rules = table.load(table.default_path())
    memo, batch, want = {}, [], []
    ran = skipped = wrong = 0
    ours = dict.fromkeys(("contract", "collect", "copy", "erase", "expand"), 0)
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
                main, d = names.name(t, 2)
                shift = len(defs) and max(defs) + 1
                move = lambda u: ivy.Ref(u.k + shift) if isinstance(u, ivy.Ref) else ((move(u[0]), move(u[1])) if isinstance(u, tuple) else u)
                defs.update({k + shift: move(v) for k, v in d.items()})
                mains.append(move(main))
            else:
                mains.append(t)
        lines, stats, error, log = run_ivm(ivy.lower(ivy.emit(mains, defs), agents, rules), directory)
        if error:
            wrong += len(batch)
            print("THE IVM RAISED A FLAG:", log[:300])
        for t, w, got in zip(batch, want, lines):
            if got != w:
                wrong += 1
                print(f"WRONG on the IVM: {show(t)} gives {got!r}, not {w}")
        for k in KINDS:
            theirs[k] += stats.get(k, 0)
        # The same answers lowered as they stand: nothing to reduce, only to print.
        from net import parse
        _, stats, error, log = run_ivm(ivy.lower(ivy.emit([parse(w) for w in want]), agents, rules), directory)
        for k in KINDS:
            printing[k] += stats.get(k, 0)
        batch.clear()
        want.clear()

    with tempfile.TemporaryDirectory() as directory:
        for n in range(1, n_max + 1):
            for t in terms(["S", "K", "I", 0, 1], n, memo):
                net = Net.of(t, agents, rules, direct=True)
                try:
                    net.run_all(20000, 50000)
                except Stop:
                    skipped += 1
                    continue
                ran += 1
                for k in ours:
                    ours[k] += net.counts.get(k, 0)
                batch.append(t)
                want.append(show(net.read()))
                if len(batch) == 500:
                    flush(directory)
        flush(directory)
    print(f"S, K, I and two atoms, sizes <= {n_max}{', normal subterms named' if named else ''}: {ran} terms run on the IVM "
          f"({skipped} do not stop all at once and are not run); {wrong} wrong")
    total = sum(ours.values())
    print(f"  the table machine, all at once: {total} interactions ({', '.join(f'{k} {v}' for k, v in ours.items() if v)})")
    work = {k: theirs[k] - printing[k] for k in KINDS}
    print(f"  the IVM: {theirs['Total']} interactions, of which {printing['Total']} are spent starting and printing "
          f"(measured by running the answers alone)")
    print(f"  the IVM, reduction alone: {work['Total']} interactions ({', '.join(f'{k.lower()} {work[k]}' for k in KINDS[1:])}), "
          f"{work['Total'] / max(total, 1):.1f} for each of the table machine's")
    return wrong


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--names"]
    sys.exit(bool(main(int(args[0]) if args else 5, "--names" in sys.argv)))
