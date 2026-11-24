# A graph reducer with a store, on the IVM

Written 2026-11-24. `skivine/graph.vi` is S, K and I by graph reduction, written in Vine
and run on the IVM. It is the thing `ski-system.md` says a local net cannot be and a
program in the net can: call by need with every pair fired.

## How it shares work

The term is a graph kept in an array, and a node names its parts by their places in the
array. A place can be named any number of times, so `S x y z` builds `x z` and `y z` with
the same `z` and copies nothing. When a shared application is reduced, its place is
overwritten with the result, or with a pointer to it, and whoever else names that place
finds the work done. Reduction is normal order: walk down the spine of applications,
keeping their places on a stack, and contract the head whenever it has all its arguments.

This is one cursor carrying its store with it. It is an ordinary program: nothing in it is
particular to interaction nets, the combinators are data and not agents, and it is
sequential.

## Results

`VINE=... IVM=... python3 ref/graph_check.py census 6`: all 81,641 terms with a normal form
(S, K, I to size 6; with two atoms as well, to size 5, which includes the first family's
terms up to that size) print it. For every one the machine reports exactly the number of
contractions that reduction by need takes on the table machine of `ski/`.

`python3 ref/graph_check.py skijack t0 t1 t2`: the level-1 programs of SKIjack's `tower`.
Each is reduced until its head is a value; then, applied to one atom for each constructor
of its result, to normal form, which equals the reference reducer's in all three.

| Program | Contractions | The reference reducer's | Places in the store | IVM interactions | For each contraction | Heap | Time |
|---|---|---|---|---|---|---|---|
| t0 | 323 | 340 | 1,007 | 864,267 | 2,675 | under 1 MB | under 1 s |
| t1 | 63,520 | 91,556 | 68,714 | 199,601,312 | 3,142 | 6 MB | 3 s |
| t2 | 314,309 | 504,930 | 349,456 | 1,147,105,497 | 3,649 | 30 MB | 83 s |

The contraction counts are those of reduction by need on the table machine (323, 63,520,
314,309), which that machine reached with 765 to 15 million copies; here there are none.
Times are single runs on a machine doing other work.

## What it costs, and what it is not

- **About 3,000 IVM interactions for each contraction**, rising slowly with the size of the
  store, since each look into the array walks a tree. The IVM's own counts for these runs
  include reading the term.
- **Nothing is ever freed.** A place, once used, stays: the store only grows (349,456 places
  for t2). A collector is not written.
- **It is sequential.** Depth was not measured; there is nothing here for a second worker
  to do.
- **Reading a result back unfolds sharing**, so a normal form with much sharing prints
  long (t2's answer applied to atoms is some 189,000 characters).
- **The printer prints atoms 0 to 9**, and `parse` reads anything that is not a backtick,
  `S`, `K` or `I` as an atom.
- It is tested, not proved, and on the programs above.

## Against the other ways in this repository

| | Stops whenever a normal form exists | Shares work | SKIjack's t1 | Where the strategy lives |
|---|---|---|---|---|
| `ski.vi`, `ski/ski.rules` with every pair fired | no | yes | does not stop | nowhere: everything fires |
| `lazy.vi`, `ski/lazy.rules` with every pair fired | yes | no | does not finish | in the net, as demand agents |
| `ski/ski.rules` by need | yes | yes | 63,520 contractions, 2 million interactions | in the reducer, which the IVM is not |
| `graph.vi` | yes | yes | 63,520 contractions, 200 million IVM interactions | in the program, with a store |
