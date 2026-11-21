# Pure S as an interaction system

Opened 2026-11-21 at Neal's request, after reading the Tendrils post on interaction nets
(tendrils.co/blog/2026-04-26/on-inets; their language Vine, vine.dev). The purpose is a short,
checked reference that a separate thread on Vine can build on. Scripts are in
`notes/checks/inets/` (`snet.py`, `census.py`, `extra.py`).

## Why pure S fits interaction nets

Interaction nets require linearity: a value is consumed exactly once, so copying and erasing
must be explicit agents. Combinatory logic uses both through K (erase) and S (copy z). Pure S
never erases: every argument of `S x y z → x z (y z)` survives. So CL(S) needs a duplicator
and **no eraser**, and it produces no garbage. Combinators have no bound variables, so none of
the scope bookkeeping of optimal λ-reduction (Lamping's brackets and croissants) arises.

## The system

Agents (port 0 is the principal port):

| Agent | Meaning | Ports |
|---|---|---|
| `S` | the atom S | 0: output |
| `S1(x)` | `S x` | 0: output, 1: x |
| `S2(x,y)` | `S x y` | 0: output, 1: x, 2: y |
| `A(arg,out)` | application; principal port on the *function* | 0: function, 1: argument, 2: result |
| `D(o1,o2)` | duplicator; principal port on its input | 0: input, 1, 2: copies |

Rules (an active pair is two principal ports joined):

- `A ⋈ S` → `S1(arg)` on `out`; `A ⋈ S1(x)` → `S2(x, arg)` on `out` (partial application).
- `A ⋈ S2(x,y)` → `out := A(A(x, z₁), A(y, z₂))`, with `D(z) = (z₁, z₂)`. This is the S-step.
- `D ⋈ S` → two `S`; `D ⋈ S1(x)` → two `S1`, with `D` pushed onto `x`; `D ⋈ S2(x,y)` → two
  `S2`, with `D` pushed onto `x` and `y`.

There are six rules and no eraser. A duplicator waits until its input is a value (an hnf), then
copies one constructor at a time and leaves the arguments shared. So arguments are shared,
and copied only as far as they are inspected: lazy duplication. Every interaction rebuilds or
copies the agents it consumes, so nothing is discarded. Active pairs are disjoint (one
principal port per agent), and the system is confluent in the usual interaction-net sense.

Read-back: a value agent reads as `S`, `S x` or `S x y`; an `A` at its result port reads as an
application; a `D` copy port reads as whatever the `D` shares, which unfolds the sharing.

## Measurements (`census.py`, `extra.py`)

The nets were run in parallel rounds (every active pair in every round, as in Vine's
`--breadth-first`).

- **Correctness check:** all 2,056 S-terms of size ≤ 9 were run. 1,737 normalize within the
  tree-reduction cap, and for every one of them the net reaches a normal form whose read-back
  equals the leftmost-outermost normal form (0 mismatches). This is a test, not a proof.
- **Small terms (size ≤ 9):** at most 22 S-steps, 256 interactions and 33 parallel rounds,
  against up to 86 leftmost-outermost tree steps.
- **A large normal form** (*Dance* §5.4: `S A (S S S S S S) S S S`, `A = S S S`). Its normal
  form has 3,066 leaves (6,131 nodes, matching *Dance*).
  - Tree reduction: 4,206 leftmost-outermost steps.
  - Net: **55 S-steps** and 3,108 duplications, 3,285 interactions in all, **52 rounds**,
    average breadth 63, at most 3,067 agents.
  - The duplications are the cost of building an output of that size. The S-steps are where
    sharing pays.
- **Terms without a normal form** (AAA; Zachos' `S T T (S T T)`, `T = S S`; Pettorossi's
  `S A A (S A A)`). The net grows without bound (AAA: 17,442 agents after 80 rounds;
  `S A A (S A A)`: 33,118). Yet the read-back to depth 6 stops changing (after about 40–80
  rounds). This is top-termination and convergence (S2) seen in a fully parallel schedule: the
  top of the term settles while work continues below it.

## How this meets the formal results (lean-ski)

- **Convergence is what a parallel machine needs.** Confluence (any order, same result) holds
  for interaction nets by construction, but it says nothing about non-terminating programs.
  - Top-termination (`TopTerm.top_termination`, v1.6.0) and convergence
    (`InfSN.not_weakInf`, v1.7.0) say that any reduction of a finite S-term, however
    scheduled, stabilizes level by level.
  - That is the guarantee that an "evaluate everywhere at once" machine produces a usable
    prefix of an infinite answer.
  - It is not yet proved for the net semantics: that would need a simulation theorem between
    nets and weak reduction.
- **What is known statically.** S1's 38-block fold decides in linear time whether a term ever
  reaches a head normal form (so whether a duplicator waiting on it will ever fire). S1.5's
  39-class automaton decides whether its Böhm tree is ⊥-free.
- **Cost models.** Interaction counts here can be compared with S1's head-step measure and
  with lean-ski's graph reduction with update in place (`Ski/Graph*.lean`). Neither comparison
  has been made.

## Not done

- No proof that the net simulates weak reduction (only the census above). A Lean development
  would need the net as a graph with a well-formedness invariant; lean-ski's graph machine is
  the nearest model.
- No mapping yet to Lafont's symmetric interaction combinators (γ, δ, ε), nor to Vine's IR.
  The Vine-overlap thread (hcom: `deli`, `~/Code/english-ivy`) is the natural place for that.
- **Rule breach:** `extra.py` reached 5.2 GB once before I killed it. It imported
  `census.py`, whose module code reran the census, and its read-back unfolded all sharing.
  Both are fixed (a `__main__` guard and a depth-bounded read-back), and the script now runs
  under the 3.5 GB cap (peak 12 MB).

## Status

- 2026-11-21: Note written; simulator and census checked (size ≤ 9, 0 mismatches).
- 2026-11-21: Neal: deli owns sigilante/ski-vine (private), consulting skinock. Seed pointers and cautions sent to deli (the s1tables dependency; the memory cap; tested, not proved; the disclosure boundary).
