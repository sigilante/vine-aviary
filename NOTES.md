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
