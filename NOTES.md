# Notes

Append dated lines to Status; do not rewrite earlier ones.

## How a combinator is put on the IVM

`skivine/ski.vi` does not define new agents. It is an ordinary Vine program: an enum of
values (a combinator and the arguments it holds so far) and a function `apply` that matches on the function and forks the argument
in the `S x y z` case. The Vine compiler turns that into IVM nets. The correspondence with
the six rules of `docs/inets-pure-S.md` (application waits on the function; a duplicator
waits on a value and copies one constructor) is the intent; it has not been checked rule by rule.

## Results, 2026-11-21

Vine `cf0c325`, release build, Apple M4 Max.

1. **Census.** `ref/check.py census 9`: for all 1,737 S-terms of size ≤ 9 that normalize by
   leftmost-outermost reduction within the caps of `census.py` (2,000 steps, size 20,000),
   the IVM's normal form equals the tree normal form. 0 mismatches. The 319 terms that do
   not normalize within the caps are not run.
2. **Large normal forms** (`ref/check.py monsters`; the check is on the size of the normal
   form only, and the IVM figures include reading the term and folding the result):

| Term | Leaves in normal form | Tree steps | Simulator: interactions, S-steps, rounds | IVM: interactions, depth, breadth |
|---|---|---|---|---|
| `S A (S S S S S S) S S S`, A = `S S S` | 3,066 | 4,206 | 3,285; 55; 52 | 29,546; 819; 36 |
| `S T T S S`, T = `S S` | 13 | 5 | 32; 5; 15 | 778; 413; 1 |

The second row shows a fixed cost of about 400 in depth and 700 in interactions for reading
and reporting a small term, so the first row's IVM figures overstate the reduction itself.
That cost has not been separated out.

## Results with K, I and the other birds, 2026-11-21

Same build and machine. `strict` in `ref/check.py` makes the same calls to `apply` as the
Vine program, so it terminates exactly when the IVM should; each answer is also compared
with the leftmost-outermost normal form.

| Check | Terms run | Mismatches | Normalize leftmost-outermost but not strictly (not run) |
|---|---|---|---|
| `ski 7`: S, K, I, sizes ≤ 7 | 322,985 | 0 | 13, the first being `S I I (S I (S K))` |
| `birds 3`: 49 birds, sizes ≤ 3 | 236,860 | 0 | 0 |
| `rules`: each bird on as many inert arguments as its arity | 49 | 0 | n/a |
| `census 9`: pure S, sizes ≤ 9 (rerun) | 1,737 | 0 | 0 |

Limits of these checks: `birds 3` fires only rules of arity 1 and 2, and `rules` fires each
rule once on inert arguments; rules of arity 3 and more are not tested in combination,
except S. Caps: 2,000 leftmost-outermost steps, 20,000 strict calls.

Three findings:

1. **The IVM gives strict evaluation.** Before the strict filter was added, the size-7
   S, K, I census ran the IVM out of memory: 13 terms there have a normal form that
   strict evaluation never reaches, because a dropped argument diverges. Normal-order
   behaviour needs a lazy encoding, which is not written.
2. **Y is left out** (`tools/gen_combinators_excluded.py`). Under strict evaluation
   `Y a` never stops. Separately, with Y in the table the Vine optimizer emits an
   `ivm:graft[...]` node with a child (`ivm:graft[...apply#0x149](ivm:eraser)`), and the
   IVM panics at `ivm/src/program.rs:217`; `--no-opt` avoids it. Bisected to Y alone;
   no minimal reproduction yet, and not reported upstream.
3. **Deriving `Fork` and `Drop` fails for the 163-variant enum** ("search limit reached
   when finding impl of trait `Fork[Term]`"), so the generator writes both by hand.
   Explained on 2026-11-22: the compiler resolves the derive by a search with a fixed
   budget of 2,000 steps (`STEPS_LIMIT`), and an enum costs about 10 steps per variant plus
   about 10 per field. The most that compiles is 199 variants with no fields, 66 with two
   fields each, 39 with four. With the constant raised, enums of 1,600 variants compile.
   Draft report: `~/Code/english-ivy/outreach/issues/derive-search-limit.md`.

## Strict, lazy, and what the crash was, 2026-11-21

Neal asked at which level the Y trouble sits: our definitions, our assumptions about
evaluation order, a compiler bug, or interaction nets themselves. There are two separate
problems, at different levels.

**The crash is a compiler bug**, not ours and not a property of nets. The unoptimized net
is well formed and runs. The optimizer's rule for a statically known enum match leaves a
two-port graft node that can never be inlined when a stage reaches itself, and the IVM
accepts only nilary grafts. It also hits programs that never enter the recursion, such as
mutual recursion that is never called. Root cause and the issue text:
`~/Code/english-ivy/outreach/issues/optimizer-self-graft.md`.

Correction, 2026-11-22: an earlier version of this note listed "an intended infinite loop
over a constant state" as a program the crash breaks. That example does not run without
optimization either: its unconditional recursion unfolds without end and exhausts the heap
before anything is printed. It was dropped from the report.

**Non-termination is a property of the encoding, and under it of nets.** In `ski.vi` and
`combinators.vi` an application is a function call, and on the IVM a call is an active
pair as soon as it exists. Dropping its result attaches an eraser to the result wire, but
an eraser acts only on a principal port, and the call does not offer one until it has
finished. So work that is no longer wanted still runs: `K I Ω` was still running after
4 s when stopped. That is how interaction nets reduce; laziness has to be put into the
encoding.

**A lazy encoding works, at the cost of sharing.** `skivine/lazy.vi` keeps arguments as
inert data (`Expr`) and evaluates heads only (`whnf`). `ref/check.py lazy 5`: all 7,667
S, K, I, Y terms of size ≤ 5 with a leftmost-outermost normal form (caps: 200 steps, size
2,000) give that normal form; 3,794 of them contain Y. `K I Ω` gives `I`. But copying an
argument copies the unevaluated term, so this is call by name. On the 3,066-leaf term,
with the whole normal form printed: strict 149,413 interactions, lazy 331,163 (both
figures include printing, which also sets the depth, about 84,000 in each).

| | Terminates whenever a normal form exists | Shares work | Y |
|---|---|---|---|
| `ski.vi`, `combinators.vi` (strict) | no | yes | never stops |
| `lazy.vi` (call by name) | yes, on the terms tested | no | works |
| call by need | wanted | wanted | not written |

Call by need on nets is a known problem with known answers (token-passing nets; from
memory, Sinot's papers of 2005–2006, not checked). It is the open design question here.

## Not done

- Terms without a normal form. The IVM runs until the net is normal, so such a term does
  not stop; showing that the top of the term settles (top-termination, lean-ski v1.6.0)
  needs output that is produced as the term is built, or a bounded run.
- Counting S-steps on the IVM, to see whether it shares work as the simulator does
  (55 S-steps against 4,206 tree steps).
- S compiled directly to the IVM's combinators as a graft for λx.λy.λz. x z (y z), and the
  six rules hosted on Ivy's rewrite engine. Open question for the first: with one
  duplicator label, two duplicators that meet annihilate, which may be wrong for some
  terms; the census would show it.
- Any proof. The simulation theorem belongs in lean-ski.
- A lazy encoding, so that normal-order behaviour (and Y) can be had.
- Interaction, depth and breadth figures for K, I and the other birds.
- A licence.

## Boundaries

lean-ski results are cited by tag and DOI. No text from unpublished drafts goes in this
repository.

## Status

- 2026-11-21: Repository created (branch `master`). Pure S in Vine; census and large-term
  checks pass as above. Seed files copied from `~/Code/ski/notes` with skinock's agreement.
  Remote `origin` = `sigilante/ski-vine` added; first commit local, not pushed.
- 2026-11-21: Pushed `master` (e7625ee) to `sigilante/ski-vine` with Neal's approval.
- 2026-11-21: `s.vi` renamed `ski.vi`; K and I finished (Neal began them). In Neal's draft I took an argument and held it (`I1`), which would make `I x y` reduce to `x`; `I x` now returns `x`. `combinators.vi` generated for 49 Aviary birds. Checks as in the table above. Neal renamed the remote to `sigilante/vine-aviary`, but GitHub still shows `sigilante/ski-vine` and no `vine-aviary`, so `origin` is unchanged for now. Committed locally, not pushed.
- 2026-11-21: Repository renamed `sigilante/vine-aviary` (Neal); local folder now `~/Code/vine-aviary`. `d85a1bd` pushed with Neal's approval. The library folder is still `skivine/`.
- 2026-11-21: The Y crash is reduced to 17 lines (an enum match whose arm calls the function on the same constant variant). It begins at `--opt-limit 6`; `--no-opt` avoids it. Reproduction and a draft issue, not sent: `~/Code/english-ivy/outreach/draft-issue-optimizer-self-graft/`. No matching upstream issue found in two searches.
- 2026-11-21: All 13 S, K, I terms of size ≤ 7 that normalize leftmost-outermost but not strictly contain K, as skinock predicted from the conservation theorem for non-erasing systems.
- 2026-11-21: Crash traced to the optimizer's enum-match rule (see the section above); `lazy.vi` added and checked. Committed locally, not pushed.
- 2026-11-22: Corrected the note on the optimizer crash (the infinite-loop example was wrong); issue texts moved to `~/Code/english-ivy/outreach/issues/`.
- 2026-11-24: The `ski:` system (`ski/`, `docs/ski-system.md`): S, K, I, atoms, a duplicator and an eraser as a table of 24 typed rules, and a machine that reduces by need with the cursor in the reducer. This is the call by need the table above lists as wanted, for a reference machine; it is not on the IVM. All 322,998 S, K, I terms of size ≤ 7 with a normal form give it by need; all at once, the same 13 do not stop. SKIjack's tower programs t0, t1, t2 give the reference's answers in fewer contractions (323 for 340; 63,520 for 91,556; 314,309 for 504,930) and many copies (up to 99 for each contraction). Branch `ski-system`, not pushed.
- 2026-11-24: `ski:` continued (branch `named-nets`). Named nets: a `ref` agent and `names.py`, which names normal subterms; on SKIjack's t1 and t2 the copies halve and the contractions are unchanged. Ivy text and a lowering to the IVM's agents (`ivy.py`), derived from the rule table: all 47,155 terms of S, K, I and two atoms up to size 5 give the table machine's normal forms on the IVM, at 4.9 IVM interactions for each of the table machine's. This is S, K, I on the IVM by a rule table, not through Vine; it is strict as `ski.vi` is, and SKIjack's t0 does not stop when every pair is fired (t1 and t2 not tried).
- 2026-11-24: The demand carried in the net (`ski/lazy.rules`, branch `demand`): applications are inert until a demand agent reaches them. With every pair fired, all 370,153 census terms with a normal form stop and give it, in exactly the number of steps of leftmost-outermost tree reduction: this is normal order without shared work (call by name), which is what `lazy.vi` does in Vine, now as a rule table lowered to the IVM. SKIjack's t0 runs on the IVM and prints the reference's answer (60,797 IVM interactions; 340 contractions on the table machine, the reference's count). t1 does not finish: unevaluated terms are copied whole. Call by need with the demand in the net is not written, and I argue in `docs/ski-system.md` that a net of fixed wiring cannot do it.
