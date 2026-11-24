# The `ski:` interaction system

Written 2026-11-24. S, K and I as an interaction system of their own, declared as a table,
with a machine that reduces by need. It extends the six-rule system for pure S
(`inets-pure-S.md`) with K, I, an eraser and inert atoms, and supplies the call-by-need
evaluation that `NOTES.md` lists as wanted.

Later on 2026-11-24 the machine became the `inets` package, built from `table.py`,
`net.py` and `names.py`. Those three files are gone. The names in this note map as
follows:

| Here | In `inets` |
|---|---|
| `run_all` | `Net.reduce_in_rounds` |
| `normalize`, `head` | `Net.reduce_by_need` (deep or not) |
| `names.py` | `inets.ski.name_subterms`, which names every normal application (the old minimum of 2 leaves excluded nothing, since an application has at least 2) |
| `Net.sweep` | `inets.Net.sweep` with `collapse=("dup",)` |

Each kept check, rerun with the package, prints the same output as before, line for
line, counts included:

- `check.py all`, `check.py census 7` and `check.py demand 7`;
- `skijack_check.py t0 t1`;
- `ivm_check.py 5`, with and without `--names` and `--demand`, and `ivm_check.py
  --skijack t0`;
- `ref/graph_check.py census 6` and `ref/graph_check.py skijack t0 t1`, which compare the
  graph reducer with the machine.

The package needed one addition, `collapse`, which removes a duplicator that has lost a
copy. Without it, the copies by need on t1 are 23,475,006, not 2,030,766. Not rerun: t2,
and the figures this note marks as runs by hand. The censuses take about twice as long as
before, and t1 by need about four times as long (40 s against 11 s, timed one after the
other on 2026-11-25), because the package is a general machine.

| File | Holds |
|---|---|
| `ski/ski.rules` | The system: 12 agents, 27 rules |
| `ski/lazy.rules` | A second table, with the demand carried in the net: 15 agents, 50 rules |
| `ski/machine.py` | The tables loaded by the `inets` package, which checks them and is the machine: by need or all at once by `ski.rules`, all at once by `lazy.rules` |
| `ski/check.py` | Census against tree reduction and the reference reducer |
| `ski/skijack_check.py` | Programs compiled by SKIjack, against its reference reducer |
| `ski/ivy.py` | Either table as Ivy text, and its lowering to the IVM's own agents |
| `ski/ivm_check.py` | The lowering run on the IVM itself |

Everything here is a test, not a proof.

## The system

This section and the next four are about the first table, `ski.rules`. The second,
`lazy.rules`, has a section of its own.

Nine values: `S`, `K`, `I`; the partial applications `K1(x)`, `S1(x)`, `S2(x y)`; an inert
`atom` with a number; `stuck(head argument)`, a term whose head is an atom; and `ref`, a
reference to a named term (below). Three consumers: `app` (application, waiting on its function), `dup` (waiting on the term it
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
`inets` checks that every rule keeps this, so in a net built from a term the only
principal ports that can meet are a consumer's and a value's, and each such pair has a
rule. One rule is outside the typing: an application meeting a reference (below) is not a
net but an instruction to the machine, which puts a new copy of a term, with its one
output, where the reference was. That is an argument checked rule by rule, not a mechanized proof. Typing does not
make a rule right. Broken tables were tried by hand and by a reviewer (they are not kept
in the repository): a rule that joins two outputs, uses a port twice, shares where it
should copy, or is missing, is refused; S or K with arguments exchanged is well typed
and is caught by the census; a rule counted under the wrong name is caught only by the
exact counts in `check.py cases`; and a rule that leaves an extra, unreachable node
changes no answer and is caught by nothing.

## Two schedules, one system

(A third way, `lazy.rules` with every pair fired, is a second system and has its own
section below.)

- **All at once** (`run_all`, now `Net.reduce_in_rounds`): every active pair, in rounds. This is the IVM's way.
- **By need** (`normalize`, `head`, now `Net.reduce_by_need`): a cursor starts at the root and fires a pair only
  when it is waiting on it. An application fires when its result is asked for; a
  duplicator, when one of its copies is asked for, so a shared term is evaluated once.
  The cursor lives in the reducer, not in the net: the rules are the same.

Reduction by need never fires an eraser, so the machine removes what the root cannot reach
(`Net.sweep`), and replaces a duplicator that has lost one copy by a wire. That is
housekeeping, not a rule. It runs when the net passes 20,000 nodes and then at twice what
was left, so t0 below is never swept. When it runs changes the number of copies and of
interactions in all, but not the number of contractions or the answer: sweeping after
every interaction gave the same of both on some 29,000 random terms of sizes 8 to 40 (a
reviewer's run, not kept) and on the terms in `check.py cases`.

## Results

`python3 ski/check.py all` (under a minute), and `check.py census 7` (a few minutes):

| Terms | With a normal form | By need | All at once |
|---|---|---|---|
| S, K, I, sizes ≤ 7 | 322,998 (177 more have none within the caps and are not run) | all give it | 322,985 give it; 13 do not stop |
| S, K, I and two atoms, sizes ≤ 5 | 47,155 | all give it | all give it |

- The 13 terms that do not stop all at once (within the caps: 20,000 interactions, 50,000
  nodes) are as many as `NOTES.md` records for `strict`, its model of the IVM, at this
  size, and the first is the same term, `S I I (S I (S K))`. By need they stop: `K I Ω`
  gives `I` in two interactions.
- Every rule is applied in the two censuses together. (An eraser meets a reference only
  when every pair is fired on a term with names, which the census does for that reason.)
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

t2 took about six and a half minutes here, in Python, and several GB (as the script then
was; it now makes three runs of each program).

## Named nets

Every subterm of a closed term of S, K and I is closed, so any of them can be made a
definition. `names.py` (now `inets.ski.name_subterms`) names each application in argument
position (and the whole term) that is in normal form; equal subterms get one name. The term then holds references in their place. A reference has three rules: applied,
it is replaced by a new copy of the term it names; duplicated, the name is copied and the
term is not touched; erased, it vanishes. These are what the IVM does with a reference to
a net at a label-0 combinator, a label-1 combinator and an eraser. One expansion is not a
rule: when the cursor asks for a value and finds a reference with nothing consuming it
(at the root, or in an argument of the normal form), the machine expands it; and reading
a result back unfolds any reference left.

Only normal forms are named. A reference is expanded afresh at each use, so naming a term
with work left in it would repeat the work; a normal form has none. The census checks
this: with names, every term gives the same normal form in the same number of
contractions (19,144 of the size-6 terms have something to name).

On SKIjack's programs, by need (`python3 ski/skijack_check.py`). "Directly" means a
combinator short of arguments is built as the value it is, not as applications that will
make it; the named runs do that too, so the middle column separates the two changes.
"Named" names every normal subterm of 2 leaves or more.

| Program | Contractions | Copies: as applications | directly | directly and named | Expansions | Interactions in all: as applications | directly and named | Most nodes: as applications | directly and named |
|---|---|---|---|---|---|---|---|---|---|
| t0 | 323 | 2,702 | 2,702 | 765 | 190 | 3,407 | 1,403 | 3,859 | 1,097 |
| t1 | 63,520 | 2,030,766 | 2,011,521 | 970,591 | 37,805 | 2,125,278 | 1,098,665 | 408,263 | 223,566 |
| t2 | 314,309 | 31,013,168 | (not run) | 15,383,081 | 188,463 | (not recorded) | 16,019,609 | 8,631,616 | 4,835,397 |

The t2 row is from two runs made by hand before the script took its present form.

Naming halves the copying on the larger two and leaves the contractions exactly as they
were; building values directly accounts for almost none of it. Naming larger pieces only
(4, 8 or 32 leaves) did worse on t1 in a trial that is not kept. What is left, about 15
copies for each contraction on t1 and 49 on t2, is copying of values made while the
program runs, which no name can stand for: an S step shares its third argument, and when
both uses are wanted the argument is copied node by node.

## Ivy text and the IVM

`ivy.py` writes a term as a net of the `ski:` system in Ivy, Vine's text for nets
(`ski:s2(x y)`, `ski:app(argument result)`, `ski:ref[name]` and so on), and lowers that
text to the IVM's own system, agent by agent, as Vine lowers its own:

| `ski:` | `ivm:` |
|---|---|
| a value | a label-0 combinator holding a tag (an N32) and a payload |
| `dup` | a label-1 combinator |
| `era` | the eraser |
| `ref` | a reference to a net |
| `app` | a label-0 combinator that takes the value apart, and the IVM's branch on the tag, which picks the net for that value's rule |

The nets for the application rules are not written by hand: each `app >< value` rule of
`ski.rules` is lowered, right-hand side and all, by that same table. Written by hand: the
table above, the order of the tags, the main net, and the nets that print a value. The duplication, erasure and
reference rules are not lowered at all. The claim is that the IVM's own commutation,
erasure and treatment of references do to the lowered nodes what those rules say.

`IVM=/path/to/ivm python3 ski/ivm_check.py`: all 47,155 terms of S, K, I and two atoms up
to size 5 are lowered and run by `ivm run`, and each prints the normal form the table
machine gives, with no error flag; the same again with their normal subterms named.

| | Interactions |
|---|---|
| The table machine, every pair at once | 90,176 (43,076 contractions, 23,179 arguments taken, 4,775 copies, 19,146 erasures) |
| The IVM, reduction alone | 445,134: 4.9 for each of the table machine's |
| The IVM, with names | 482,809: 5.4, against the same 90,176 |

Starting each term and printing its answer cost the IVM another 1,945,110, measured by
running the answers alone and taken off; the two runs differ only in the reduction, but
that the difference is exactly the reduction has not been checked by hand. An application rule costs the IVM one extrinsic
call (the branch) and one expansion of a net: 66,255 of each, the number of contractions
and arguments taken together.

**What does not run on the IVM by `ski.rules`: SKIjack's programs.** The IVM fires every
pair, and all at once t0 does not stop: in a run by hand on the table machine it was still
going after two million interactions, where by need it takes 3,407, or 1,403 with names.
An interpreter that recurses needs the demand carried in the net: the next section.

## The demand carried in the net

`lazy.rules` is a second table. An application in a term is an inert node, `ap`, and
nothing happens to it until a demand reaches it. A demand is an agent, `ev`, sent to a
term's output; where it meets an `ap` it turns it into the `app` of `ski.rules` and goes
on to the function. So every `app` in a net is there because its result was asked for.
An S step asks for `x z` and leaves `y z` as an `ap`; an eraser discards an `ap` without
running it. A second demand agent, `nf`, asks for the whole normal form. The cursor of
"by need" above has become an agent, and a machine that fires every pair does only
wanted work.

**It does not share work.** A duplicator that meets an `ap` copies it as it stands, and
each copy is evaluated by whoever asks: call by name. A term that is already a value is
copied as a value.

`python3 ski/check.py demand 7` (a few minutes), every pair fired:

- All 322,998 terms of S, K, I to size 7 with a normal form, and all 47,155 with two atoms
  as well to size 5 (which include the first family's 3,873 up to that size), stop and
  give it, including the 13 that never stop under `ski.rules`. Each is run as
  applications, with values built directly, and with every subterm named.
- Each takes exactly as many contractions as leftmost-outermost tree reduction takes
  steps. This table is normal order without shared work, to the step.
- Two rules are never applied, and I believe cannot be: an `app` meeting a reference or an
  `ap`. A demand sends on only values, so an `app` only ever meets one. (A reviewer made
  the machine raise an error if either fired, over some 6,000 random terms; neither did.
  That is not a proof.)

`ivy.py` lowers this table as it does the other (`--demand`): `ap` becomes one more tagged
value, and the nets for `ev`, `nf` and `app` are generated from the table.
`IVM=... python3 ski/ivm_check.py 5 --demand`: the 47,155 terms give their normal forms on
the IVM, with and without names; 486,885 interactions on the table machine (338,420 of
them a demand arriving at a value), 1,119,767 on the IVM for reduction alone, 2.3 each
(1,197,667 with names, 2.5 each against the same 486,885).

**SKIjack's t0 runs on the IVM** (`ivm_check.py --skijack t0`): applied to two atoms it
prints `` `1`K``S`KKK ``, the reference reducer's normal form, in 60,797 IVM interactions
with no error flag. On the table machine, to a value (runs by hand, not kept; of the
figures in this table only the 340 is printed by a kept script, as the reference's count):

| t0, every pair fired | Contractions | Copies | Erasures | Interactions in all | Most nodes |
|---|---|---|---|---|---|
| values built directly | 340 | 336,720 | 329,908 | 667,577 | 116,291 |
| normal subterms named | 340 | 38,185 | 37,448 | 76,786 | 13,530 |
| every subterm named | 340 | 12,009 | 11,823 | 25,022 | 4,299 |

The 340 contractions are the reference reducer's count for t0. I have not looked into
whether that is more than a coincidence of this program.

**t1 does not finish** (t2 was not tried). With every subterm named, a run by hand, not
kept, was stopped at 13.6 million
interactions and 3 million nodes, having made 789 contractions and 8.3 million copies. An
unevaluated term is copied whole, at once, whether or not the copy is ever asked for, and
copies of copies compound.

**Why not by need in the net, and what could do it instead.** Sharing work needs a term
that is evaluated on the first demand from either of two holders.

- *No local cell can do it.* Suppose a piece of net stands between the two copies and the
  unevaluated term, is quiet (has no active pair) until a demand comes, and is touched by
  the rest of the net only at the two copies. In a quiet net every node has one owner
  among the free ports: follow its principal wire, which ends at a free port or at an
  auxiliary port of a node whose owner it shares. A node can be consumed only after a
  demand at its owner, by induction over the run, since an auxiliary port changes only when
  its node is consumed. So nothing in the piece can be consumed both on a demand from one
  copy alone and on a demand from the other alone, and the term's first contraction
  consumes its root. This argument was mine in outline and was made exact by a reviewer;
  it is a proof on paper, not mechanized. A piece that never goes quiet (one that polls) is
  not covered; we believe that fails too.
- *Forcing a term when it is shared* shares work but runs terms nobody wants. A reviewer
  tried it (a table with one rule changed, not kept): `Y (K 0)` still stops, but `Y f` with
  `f = S (K (K 0)) I` does not, nor does `S (K (K 0)) I Ω`, though all three stop here.
- *A net that is its own reducer* is not ruled out. If a single token is the only active
  thing, the token is the strategy, and it can carry a store of shared terms with it and
  reach them by address: a graph-reduction machine written as a program in the net. That
  gives up the directness of combinators as agents, and all parallelism. It is
  `skivine/graph.vi`, described in `graph-machine.md`, and it runs t1 and t2. I recall papers on token-passing nets, by Sinot, that claim call by
  need; neither the reviewer nor I remember how, and single-token nets are of this kind.

## What this shows

1. **With a reducer that chooses, call by need needs nothing added.** The typed rules of
   `ski.rules` give strict, parallel reduction or lazy, shared reduction, depending only
   on which pairs are fired. Carried in the net, the demand needs agents of its own
   (`lazy.rules`) and no work is shared.
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
   deal with. Named nets halve it (above); the rest is copying of run-time values.

## Limits

- Tests on small terms and three programs; no simulation theorem.
- Reduction by need, with shared work, has its cursor in the reducer. What runs on the
  IVM is `ski.rules` on terms that stop when every pair fires, or `lazy.rules` on any
  term with a normal form but without shared work, which SKIjack's t1 is too large for.
  The exception is not a rule table at all: `skivine/graph.vi`, a graph reducer with a
  store, runs t1 and t2 on the IVM with shared work (`graph-machine.md`).
- The lowering uses the IVM's N32 values and its branch, which are extrinsic to the
  combinators; a lowering to combinators alone is not attempted.
- The lowered programs print atoms 0 to 9 only, and a term whose arguments nest more than
  a few thousand deep cannot be written as Ivy text unless its subterms are named.
- A reviewer ran some 8,000 more terms on the IVM (random, of sizes 6 to 30, and built to
  duplicate what is already shared), named and unnamed, with no wrong answer; those runs
  are not kept.
- The machine is a reference in Python (t1's two million interactions took about ten
  seconds on the old machine, and take about forty with `inets`), and its sweeping of unreachable nodes is its own business, not part of the
  system. Reducing all at once rescans every node each round and is slow on long terms.
- Reading a result unfolds all sharing.
