# Notes

Append dated lines to Status; do not rewrite earlier ones.

## How S is put on the IVM

`skivine/s.vi` does not define new agents. It is an ordinary Vine program: a three-variant
enum for values and a function `apply` that matches on the function and forks the argument
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
- K, I, and an eraser. A licence.

## Boundaries

lean-ski results are cited by tag and DOI. No text from unpublished drafts goes in this
repository.

## Status

- 2026-11-21: Repository created (branch `master`). Pure S in Vine; census and large-term
  checks pass as above. Seed files copied from `~/Code/ski/notes` with skinock's agreement.
  Remote `origin` = `sigilante/ski-vine` added; first commit local, not pushed.
