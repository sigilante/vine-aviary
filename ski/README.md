# The `ski:` interaction system

The combinators S, K and I as agents of an interaction net, declared as a table of rules,
with a machine that runs the table, a lowering that turns it into a program for the
[IVM](https://github.com/VineLang/vine), and checks against tree reduction, against the
IVM, and against programs compiled by [SKIjack](https://github.com/sigilante/SKIjack).

It is an experiment. Everything here is tested, on the terms and programs named below;
nothing is proved by machine. The full account, with every figure and how it was got, is
[`docs/ski-system.md`](../docs/ski-system.md).

## Try it

Python 3 is all these need. A term is written in prefix form: a backtick applies the next
two terms; `S`, `K`, `I`; a digit is an inert atom. `Ω` below is ```` ```SII``SII ````,
which reduces to itself for ever.

```sh
$ python3 ski/net.py '```SII0'             # S I I 0
`00
collect=3 contract=3 copy=1 most_nodes=8

$ python3 ski/net.py '``KI```SII``SII'     # K I Ω, reduced by need
I
collect=1 contract=1 most_nodes=15

$ python3 ski/net.py --all '``KI```SII``SII'      # the same, every pair fired
stopped at a cap

$ python3 ski/net.py --demand '``KI```SII``SII'   # every pair fired, demand carried in the net
I
arrive=3 collect=1 contract=1 demand=2 erase=11 rounds=9 most_nodes=18
```

The counts go to standard error. `contract` is the number of contractions of the calculus
(`I x → x`, `K x y → x`, `S x y z → x z (y z)`); the others are bookkeeping that a net has
to do and a term rewriter does not.

Those three runs are the subject of this directory. The same term stops or does not
according to which pairs are fired, and the second way is the one a machine that fires
everything cannot do.

## The system

An interaction net is a graph of agents. Each agent has one principal port and some
others, and a rule fires only where two principal ports meet. The table
[`ski.rules`](ski.rules) has twelve agents:

- nine **values**, whose principal port is their output: `S`, `K`, `I`; the partial
  applications `K1(x)`, `S1(x)`, `S2(x y)`; an inert `atom`; `stuck`, a term whose head is
  an atom; and `ref`, a reference to a named term;
- three **consumers**, whose principal port waits for a value: `app` (application, waiting
  on its function), `dup` (a duplicator) and `era` (an eraser).

There is one rule for each consumer and value, 27 in all. This is the S rule:

```
rule app (z r) >< S2 (x y)
  => z = dup (p q); x = app (p f); y = app (q g); f = app (g r)
  count contract
```

Read it as: an application of `S x y` to `z` with result `r` becomes a duplicator on `z`
and three applications, `x p`, `y q`, and the first of those applied to the second.

**The rules are typed.** Every port is an output or an input, and
[`table.py`](table.py) checks that each rule joins only an output to an input. In a net
built from a term, then, the only principal ports that can ever meet are a consumer's and
a value's, and every such pair has a rule. Typing does not make a rule right: S with its
arguments exchanged is well typed, and it is the census that catches it.

**A duplicator copies one node at a time** and leaves that node's arguments shared behind
new duplicators. An eraser works the same way.

## Three ways to run a term

| | Which pairs fire | Stops whenever a normal form exists | Work is shared |
|---|---|---|---|
| `ski.rules`, all at once | every active pair | no | yes |
| `ski.rules`, by need | only those a cursor from the root is waiting on | yes, on the terms tested | yes |
| [`lazy.rules`](lazy.rules), all at once | every active pair | yes, on the terms tested | no |

**All at once** is how the IVM works. An application fires as soon as its function is a
value, wanted or not, so an argument that `K` is about to discard runs anyway, and if it
never finishes, neither does the net.

**By need**, a cursor starts at the root and fires a pair only when it is waiting on it. A
shared term is evaluated once, when one of its copies is first asked for. The cursor is
part of the reducer ([`net.py`](net.py)), not of the net: the 27 rules are untouched.

**`lazy.rules`** puts the cursor in the net. An application in a term is an inert node,
`ap`; a demand is an agent, `ev`, that turns an `ap` into an `app` and goes on to the
function. Every `app` is then there because its result was asked for, and a machine that
fires everything does only wanted work. It has 15 agents and 50 rules. What it gives up is
sharing: a duplicator that meets an `ap` copies it unevaluated, so each copy is evaluated
by whoever asks. It is normal order without shared work, to the step.

Why not both, a net that stops and shares? Because an agent can be reached only through
its one principal port, a piece of net that is quiet until asked cannot be woken from two
sides. [`docs/ski-system.md`](../docs/ski-system.md) gives the argument, which is a proof
on paper with stated assumptions. What it does not rule out is a net that is its own
reducer, and that exists here too: see [the last section](#the-neighbour-a-reducer-with-a-store).

## Named nets

Every subterm of a closed term of S, K and I is closed, so any of them can be a
definition. [`names.py`](names.py) names subterms, and the term then holds a `ref` where
each stood. A reference that is applied is replaced by a fresh copy of what it names; one
that is duplicated is copied as a name, and the term is not touched. This is what the IVM
does with a reference to a net.

For `ski.rules` only subterms in normal form are named: a reference is expanded afresh at
each use, so naming unfinished work would repeat it. For `lazy.rules`, which shares no
work anyway, every subterm can be named.

## On the IVM

[`ivy.py`](ivy.py) writes a term as a net of the `ski:` system in Ivy, Vine's text for
nets, and lowers that text to the IVM's own agents:

| `ski:` | `ivm:` |
|---|---|
| a value | a label-0 combinator holding a tag (an N32) and a payload |
| `dup` | a label-1 combinator |
| `era` | the eraser |
| `ref` | a reference to a net |
| `app`, `ev`, `nf` | a label-0 combinator that takes the value apart, and the IVM's branch on the tag, which picks the net for that rule |

```sh
$ python3 ski/ivy.py emit '```SKK0'
ski:term:0 {
  ^ = w1
  ski:s2(ski:k ski:k) = ski:app(ski:atom#0 w1)
}

$ python3 ski/ivy.py lower --demand '``KI```SII``SII' > kio.iv && ivm run kio.iv
I
```

The nets for the rules of `app`, `ev` and `nf` are generated from the rule table. The
rules for `dup`, `era` and `ref` are not lowered at all: the IVM's own commutation,
erasure and references do what those rules say, which is a claim the checks test. The
table above, the order of the tags, the main net and the nets that print a value are
written by hand. The lowering uses the IVM's N32 values and its branch; it is not a
lowering to combinators alone.

## What was found

All of these are from the checks below; the terms are S, K and I, with a normal form by
tree reduction within the scripts' caps.

- **By need is right on every term tried**: all 322,998 terms up to size 7. Fired all at
  once, 13 of them never stop.
- **By need takes no more contractions than SKIjack's reference reducer on any term
  tried**, and fewer on some. Why the reference takes more has not been looked into.
- **`lazy.rules` stops on all of them** with every pair fired, each in exactly as many
  contractions as leftmost-outermost tree reduction takes steps.
- **On the IVM**, all 47,155 terms of S, K, I and two atoms up to size 5 print the right
  normal form by either table, with and without names. The IVM spends 4.9 interactions
  for each of the table machine's by `ski.rules`, and 2.3 by `lazy.rules`.
- **Copying is the cost of agents.** A graph reducer lets many applications share one
  partial application. A net cannot, because an application consumes the node it meets,
  so a value used twice is copied node by node.

On the three level-1 programs of SKIjack's `tower` (an interpreter written in S, K, I
running a quoted program, the quoted unquoter, and the quoted interpreter itself), each
reduced until its head is a value:

| | t0 | t1 | t2 |
|---|---|---|---|
| SKIjack's reference reducer: contractions | 340 | 91,556 | 504,930 |
| `ski.rules` by need: contractions | 323 | 63,520 | 314,309 |
| ... copies | 2,702 | 2,030,766 | 31,013,168 |
| ... copies, with normal subterms named | 765 | 970,591 | 15,383,081 |
| `ski.rules`, all at once | does not stop | not tried | not tried |
| `lazy.rules`, all at once: contractions | 340 | does not finish | not tried |
| `lazy.rules` on the IVM | runs: 60,797 IVM interactions | | |

Each answer that was reached equals the reference's. The t2 figures, the "does not stop"
and the "does not finish" are from runs made by hand, which the kept scripts do not
repeat; `docs/ski-system.md` says which. Naming halves the copying and changes no
contraction count.

## Files

| File | Holds |
|---|---|
| `ski.rules` | The system: 12 agents, 27 rules |
| `lazy.rules` | The system with the demand carried in the net: 15 agents, 50 rules |
| `table.py` | Reads a table and checks it: one rule for each consumer and value, and the typing |
| `net.py` | The machine: builds a net from a term, fires rules from a table all at once or by need, reads the result back |
| `names.py` | Names subterms, to be references to nets |
| `ivy.py` | A term as Ivy text in the `ski:` system, and the lowering to the IVM's agents |
| `check.py` | The census: both tables against tree reduction and the reference reducer |
| `skijack_check.py` | SKIjack's `tower` programs by need, against its reference reducer |
| `ivm_check.py` | The lowering run on the IVM |

## The checks

```sh
python3 ski/table.py                    # ski.rules: complete and typed
python3 ski/table.py ski/lazy.rules     # lazy.rules
python3 ski/check.py all                # the census to size 6, both tables; a minute or two
python3 ski/check.py census 7           # ski.rules to size 7; a few minutes
python3 ski/check.py demand 7           # lazy.rules to size 7; a few minutes
```

With SKIjack's packages installed (`skijack`, `aviary_kernel`):

```sh
python3 ski/skijack_check.py t0 t1      # t2 adds a quarter of an hour or so and several GB
```

With an `ivm` binary built from VineLang/vine (tested at commit `cf0c325`):

```sh
export IVM=/path/to/ivm
python3 ski/ivm_check.py 5                  # ski.rules lowered, on the IVM
python3 ski/ivm_check.py 5 --names          # with normal subterms named
python3 ski/ivm_check.py 5 --demand         # lazy.rules lowered; add --names too
python3 ski/ivm_check.py --skijack t0       # SKIjack's t0 on the IVM
```

Each script says in its first lines what it compares with what.

## Limits

- Tests, on small terms and three programs. No simulation theorem; the typing argument and
  the argument about sharing are on paper.
- The machine is a reference in Python, not a tool: t1 by need takes some seconds, t2
  minutes and several GB.
- By need never fires an eraser, so the machine sweeps away what the root cannot reach.
  That is housekeeping, not a rule. It changes the count of copies, never the count of
  contractions or the answer.
- Reading a result back unfolds all sharing.
- The lowered programs print atoms 0 to 9 only, and a term whose arguments nest more than
  a few thousand deep cannot be written as Ivy text unless its subterms are named first.
- The lowering leans on the IVM's N32 values and branch.

## The neighbour: a reducer with a store

[`skivine/graph.vi`](../skivine/graph.vi) is not part of the `ski:` system. It is S, K and
I by graph reduction, written in Vine as an ordinary program: the term is a graph in an
array, nodes name their parts by position, and a reduced application is overwritten in
place. That is a net that is its own reducer, and it runs t1 and t2 on the IVM with shared
work, in exactly the contractions of reduction by need (63,520 and 314,309), at about
3,000 IVM interactions each. See [`docs/graph-machine.md`](../docs/graph-machine.md).

Set beside the table above, it marks what the agents cost and what they would save. By
need, the agents take about two million interactions on t1 and the IVM cannot run them
that way; the program takes two hundred million and the IVM can.
