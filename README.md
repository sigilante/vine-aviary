# vine-aviary

Combinator calculi on interaction nets: S, K, I and the other combinator birds written
in [Vine](https://github.com/VineLang/vine) and run on the IVM, checked against reference
evaluators in Python and, for pure S, against a simulator of a six-rule interaction system.

State: an experiment. The results are tests, not proofs.

| Path | Holds |
|---|---|
| `skivine/ski.vi` | S, K, I by hand: `Term` (a combinator that still lacks arguments), `apply`, a reader and printer |
| `skivine/lazy.vi` | S, K, I, Y by normal-order evaluation: terminates whenever a normal form exists, without sharing |
| `skivine/graph.vi`, `docs/graph-machine.md` | S, K, I by graph reduction with a store: call by need as a program. Runs SKIjack's tower programs on the IVM |
| `skivine/combinators.vi` | 49 birds, generated: the same design for every bird in `tools/birds.py` except Y |
| `tools/birds.py` | The bird table (name, arity, rule), transcribed from the Aviary kernel |
| `tools/gen_combinators.py` | Writes `combinators.vi` from the table |
| `tools/check_table.py` | Compares the table with an installed `aviary_kernel` |
| `bench/` | `normalize.vi` (one S, K, I term, with statistics), `lines.vi` and `birds.vi` (one term per input line) |
| `ref/check.py` | The checks for the Vine programs: `census`, `ski`, `birds`, `rules`, `monsters` |
| `ref/snet.py`, `census.py`, `extra.py` | The Python net simulator for pure S and its census, copied from the SKI research notes |
| `docs/inets-pure-S.md` | The note that defines the six-rule system (a copy, dated 2026-11-21) |
| `ski/`, `docs/ski-system.md` | The `ski:` interaction system: S, K, I as agents, declared as a table of 27 typed rules, with a machine that reduces all at once or by need, checked against tree reduction and against programs compiled by SKIjack; named nets; Ivy text; a lowering to the IVM's own agents, run on the IVM; and a second table that carries the demand in the net, by which a program compiled by SKIjack runs on the IVM |
| `NOTES.md` | Results, limits, status log |

## Run

The Vine programs' checks need a `vine` binary built from VineLang/vine (tested at commit
`cf0c325`) and Python 3.

```sh
export VINE=/path/to/vine
python3 ref/check.py census 9     # pure S; about 90 s
python3 ref/check.py ski 7        # S, K, I; about 45 s
python3 ref/check.py birds 3      # all 49 birds; about 6 min
python3 ref/check.py rules        # every rule fired once
python3 ref/check.py lazy 5       # normal order, with Y; about 1 min
python3 ref/check.py monsters
IVM=/path/to/ivm python3 ref/graph_check.py census 6        # the graph reducer; about 15 s
IVM=/path/to/ivm python3 ref/graph_check.py skijack t0 t1   # needs skijack and aviary_kernel; t2 takes some minutes
python3 tools/gen_combinators.py  # regenerate skivine/combinators.vi
echo '```B S K I' | vine run bench/birds.vi --lib skivine --no-stats
```

The `ski:` system's checks need only Python 3; `skijack_check.py` also needs the `skijack`
and `aviary_kernel` packages, and `ivm_check.py` an `ivm` binary:

```sh
python3 ski/table.py                  # the first table and its typing; `ski/lazy.rules` for the second
python3 ski/check.py all              # a minute or two; `census 7` and `demand 7` take a few minutes each
python3 ski/skijack_check.py t0 t1    # t2 adds a quarter of an hour or so and several GB
IVM=/path/to/ivm python3 ski/ivm_check.py   # the lowering on the IVM; add --names, --demand
IVM=/path/to/ivm python3 ski/ivm_check.py --skijack t0   # a SKIjack program on the IVM
```

Terms are in prefix form: a backtick applies the next two terms. `ski.vi` reads the
single-character names `S`, `K`, `I` written together; `combinators.vi` reads bird names
separated by spaces. Run `ref/extra.py` only under a memory cap.

## The IVM is strict

The IVM reduces every redex, including those inside an argument that is later dropped.
A term such as `K I Ω` therefore does not stop, though it has a normal form. The checks run
the terms on which a strict evaluator terminates, and count the rest. See `NOTES.md`.
