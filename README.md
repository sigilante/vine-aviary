# ski-vine

Combinator calculi on interaction nets: the pure S calculus (`S x y z → x z (y z)`) written
in [Vine](https://github.com/VineLang/vine) and run on the IVM, checked against tree
reduction and against a Python simulator of a six-rule interaction system for S.

State: an experiment. The results are tests, not proofs.

| Path | Holds |
|---|---|
| `skivine/s.vi` | `Term` (the values `S`, `S x`, `S x y`), `apply`, a prefix-form reader and printer |
| `bench/` | `normalize.vi` (one term, with statistics), `lines.vi` (one term per input line) |
| `ref/check.py` | The census check and the large-term comparison |
| `ref/snet.py`, `census.py`, `extra.py` | The Python simulator and its census, copied from the SKI research notes |
| `docs/inets-pure-S.md` | The note that defines the six-rule system (a copy, dated 2026-11-21) |
| `NOTES.md` | Results, limits, status log |

## Run

Needs a `vine` binary built from VineLang/vine (tested at commit `cf0c325`) and Python 3.

```sh
VINE=/path/to/vine python3 ref/check.py census 9   # about 90 s
VINE=/path/to/vine python3 ref/check.py monsters
vine run bench/normalize.vi --lib skivine --breadth-first --config term '```SSSS'
```

Terms are written in prefix form: `S` is the atom and a backtick applies the next two terms.
Run `ref/extra.py` only under a memory cap.
