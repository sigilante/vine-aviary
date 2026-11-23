# The `ski:` interaction system

Written 2026-11-24. S, K and I as an interaction system of their own, declared as a table,
with a machine that reduces by need. It extends the six-rule system for pure S
(`inets-pure-S.md`) with K, I, an eraser and inert atoms, and supplies the call-by-need
evaluation that `NOTES.md` lists as wanted.

| File | Holds |
|---|---|
| `ski/ski.rules` | The system: 11 agents, 24 rules |
| `ski/table.py` | Reads the table and checks it |
| `ski/net.py` | A net machine driven by the table, with two schedules |
| `ski/check.py` | Census against tree reduction and the reference reducer |
| `ski/skijack_check.py` | Programs compiled by SKIjack, against its reference reducer |

Everything here is a test, not a proof.

## The system

Eight values: `S`, `K`, `I`; the partial applications `K1(x)`, `S1(x)`, `S2(x y)`; an inert
`atom` with a number; and `stuck(head argument)`, a term whose head is an atom. Three
consumers: `app` (application, waiting on its function), `dup` (waiting on the term it
copies) and `era`. There is one rule for each consumer and value:

```
rule app (z r) >< S2 (x y)
  => z = dup (p q); x = app (p f); y = app (q g); f = app (g r)
  count contract
```

A contraction of the calculus is exactly one application of a rule counted `contract`
(`I`, `K1`, `S2` under `app`). A duplicator copies one node and leaves that node's
arguments shared behind new duplicators.

**The rules are typed.** Each port is an output or an input, and a wire joins one of each.
`table.py` checks that every rule keeps this, so in a net built from a term the only
principal ports that can meet are a consumer's and a value's, and each such pair has a
rule. That is an argument checked rule by rule, not a mechanized proof. Typing does not
make a rule right. Broken tables were tried by hand and by a reviewer (they are not kept
in the repository): a rule that joins two outputs, uses a port twice, shares where it
should copy, or is missing, is refused; S or K with arguments exchanged is well typed
and is caught by the census; a rule counted under the wrong name is caught only by the
exact counts in `check.py cases`; and a rule that leaves an extra, unreachable node
changes no answer and is caught by nothing.

## Two schedules, one system

- **All at once** (`run_all`): every active pair, in rounds. This is the IVM's way.
- **By need** (`normalize`, `head`): a cursor starts at the root and fires a pair only
  when it is waiting on it. An application fires when its result is asked for; a
  duplicator, when one of its copies is asked for, so a shared term is evaluated once.
  The cursor lives in the reducer, not in the net: the rules are the same 24.

Reduction by need never fires an eraser, so the machine removes what the root cannot reach
(`Net.sweep`), and replaces a duplicator that has lost one copy by a wire. That is
housekeeping, not a rule. It runs when the net passes 20,000 nodes and then at twice what
was left, so t0 below is never swept. When it runs changes the number of copies and of
interactions in all, but not the number of contractions or the answer: sweeping after
every interaction gave the same of both on some 29,000 random terms of sizes 8 to 40 (a
reviewer's run, not kept) and on the terms in `check.py cases`.

## Results

`python3 ski/check.py all`, and `check.py census 7` (one minute):

| Terms | With a normal form | By need | All at once |
|---|---|---|---|
| S, K, I, sizes ≤ 7 | 322,998 (177 more have none within the caps and are not run) | all give it | 322,985 give it; 13 do not stop |
| S, K, I and two atoms, sizes ≤ 5 | 47,155 | all give it | all give it |

- The 13 terms that do not stop all at once (within the caps: 20,000 interactions, 50,000
  nodes) are as many as `NOTES.md` records for `strict`, its model of the IVM, at this
  size, and the first is the same term, `S I I (S I (S K))`. By need they stop: `K I Ω`
  gives `I` in two interactions.
- Every one of the 24 rules is applied in the two censuses together.
- A term used twice is evaluated once: an argument that costs 6 contractions, passed to
  `S I I`, costs 9 in all by need and 15 by tree reduction.
- **Contractions against the reference reducer** (`aviary_kernel`, normal order on a
  shared graph): by need the count is equal for 313,287 of the size-7 terms, lower for
  9,711, and higher for none (nor on the reviewer's random terms up to size 40). Why it is
  sometimes lower has not been looked into. "Arguments taken" below is the rule count
  `collect`: a value taking an argument it cannot yet act on.

`python3 ski/skijack_check.py t0 t1 t2`: the level-1 programs of SKIjack's `tower`: an
interpreter written in S, K, I running a quoted program (t0), the quoted unquoter (t1)
and the quoted interpreter itself (t2). Each answer equals the reference's (the program applied to one atom for each
constructor of its result, reduced to normal form on both machines).

| Program | Reference contractions | By need: contractions | arguments taken | copies | Most nodes at once |
|---|---|---|---|---|---|
| t0 | 340 | 323 | 382 | 2,702 | 3,859 |
| t1 | 91,556 | 63,520 | 30,992 | 2,030,766 | 408,263 |
| t2 | 504,930 | 314,309 | 146,192 | 31,013,168 | 8,631,616 |

t2 takes about six and a half minutes here, in Python, and several GB.

## What this shows

1. **Call by need needs nothing added to the system.** The same typed rules give strict,
   parallel reduction or lazy, shared reduction, depending only on which pairs are fired.
2. **It does not reproduce the reference's counts.** It does the same jobs in fewer
   contractions (323 for 340, and about a third fewer on the larger two). The reference
   counts belong to the reference reducer's own sharing.
3. **Copying is the cost.** There are 8, 32 and 99 copies for each contraction in t0, t1
   and t2, and the net holds up to 8.6 million nodes, where SKIjack's runtime design note
   (`RUNTIME-DESIGN.md` in its repository) says the tower's intermediate states are a few
   hundred nodes of shared graph (its figure, not measured here). A graph reducer can let many applications share one
   partial application; a net cannot, because an application consumes the node it meets,
   so a value used twice is copied node by node. An interpreter that recurses by copying
   itself pays this on every turn. This is the main thing a lowering to the IVM has to
   deal with. Named nets, which are expanded where needed and never copied, are the
   first thing I would try; that is untried.

## Limits

- Tests on small terms and three programs; no simulation theorem.
- The cursor is in the reducer. A machine that fires every pair, as the IVM does, needs
  the demand carried in the net; that is not written.
- Nothing here runs on the IVM or is written in Ivy text.
- The machine is a reference in Python (t1's two million interactions take about ten
  seconds), and its sweeping of unreachable nodes is its own business, not part of the
  system. Reducing all at once rescans every node each round and is slow on long terms.
- Reading a result unfolds all sharing.
