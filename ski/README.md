# The `ski:` interaction system

The combinators $S$, $K$ and $I$ as agents of an interaction net, declared as a table of 
rules, run by the [`inets`](https://github.com/sigilante/inets) package, with a lowering
that turns the table into a program for the [IVM](https://github.com/VineLang/vine), and
checks against tree reduction, against the IVM, and against programs compiled by
[SKIjack](https://github.com/sigilante/SKIjack).

It is an experiment. Everything here is tested, on the
terms and programs named below; nothing is proved by machine. The full account, with every 
figure and how it was got, is [`docs/ski-system.md`](../docs/ski-system.md).

An *interaction net* is a graph whose nodes, called agents, rewrite in pairs by a fixed
table of rules. The main finding is that one term, $K\,I\,\Omega$ (where $\Omega$ reduces to
itself without end), stops or runs without end depending on which pairs the machine fires. With the combinators as agents, a machine
that fires every pair, as the IVM does, can be made to stop only by giving up shared work.

## Try it

The machine is the [`inets`](https://github.com/sigilante/inets) package, which grew out
of the code that was first written here; it needs Python 3.10 or later:

```sh
pip install 'inets>=0.1.3'
```

`inets` ships copies of the two tables in this directory, identical rule for rule
(`ski/check.py table` confirms it), so `inets run ski` runs this system. A term is written in prefix form: a
backtick applies the next term to the one after it; `S`, `K` and `I` stand for
themselves; a digit is an atom, a constant that does nothing. $\Omega$ below is
```` ```SII``SII ````, which reduces to itself without end.

```sh
$ inets run ski '```SII0'                    # S I I 0
stopped: wanted; 7 interactions; 0 active pairs left; collect 3, contract 3, copy 1
`00

$ inets run ski '``KI```SII``SII'            # K I Ω, by need: only the work the answer depends on
stopped: wanted; 2 interactions; 2 active pairs left; collect 1, contract 1
I

$ inets run ski --rounds '``KI```SII``SII'   # the same term, every pair fired
stopped: interactions; 1000000 interactions, 333334 rounds, widest 3; 3 active pairs left; collect 5, contract 499999, copy 499996
stopped at the cap

$ inets run ski --lazy '``KI```SII``SII'     # every pair fired, the demand carried in the net (lazy.rules)
stopped: normal; 18 interactions, 9 rounds, widest 4; 0 active pairs left; arrive 3, collect 1, contract 1, demand 2, erase 11
I
```

The last line of each output is the result (`` `00 `` is the atom 0 applied to itself),
or `stopped at the cap` if there is none, on standard output; why the run stopped and
what it counted go to standard error. `contract` counts contractions, the steps of the calculus (`I x → x`, `K x y → x`,
`S x y z → x z (y z)`). The other counts are work that a net does and a term rewriter does
not.

The last three commands reduce one term, $K\,I\,\Omega$, in three ways. Firing only the
pairs the result needs gives `I`. Firing every pair of `ski.rules` never stops, because
$\Omega$ runs although $K$ is about to discard it. Firing every pair of `lazy.rules`, which
carries the demand inside the net, gives `I` again.

## The system

Each agent has one *principal port*, the port through which it interacts, and some other
ports. A rule fires only where two principal ports meet. The table
[`ski.rules`](ski.rules) has twelve agents:

- nine **values**, whose principal port is their output: `S`, `K`, `I`; the partial
  applications `K1(x)`, `S1(x)`, `S2(x y)`; an inert `atom`; `stuck`, a term whose head is
  an atom; and `ref`, a reference to a named term;
- three **consumers**, whose principal port waits for a value: `app` (application, waiting
  on its function), `dup` (a duplicator) and `era` (an eraser).

There is one rule for each consumer and value, 27 in all. This is the rule for $S$:

```
rule app (z r) >< S2 (x y)
  => z = dup (p q); x = app (p f); y = app (q g); f = app (g r)
  count contract
```

Read it as: an application of `S x y` to `z` with result `r` becomes a duplicator on `z`
and three applications: `x p`, `y q`, and the first of those applied to the second.

**The rules are typed by port.** Every port is an output or an input, and
`inets` checks that each rule joins only an output to an input (`inets check ski/ski.rules`). In a net
built from a term, then, the only principal ports that can ever meet are a consumer's and
a value's, and every such pair has a rule. (One rule is outside this check: an application
meeting a `ref` is an instruction to the machine, not a net.) Typing does not make a rule
right: $S$ with its arguments exchanged is well typed, and the tests catch it.

**A duplicator copies one node at a time** and leaves that node's arguments shared behind
new duplicators. An eraser works the same way.

## Three ways to run a term

A term is in *normal form* when no step is left to take. *Tree reduction* is ordinary
rewriting of the term as a tree, leftmost-outermost first; it is the yardstick here.

| Table, and which pairs fire | Stops if a normal form exists | Work is shared |
|---|---|---|
| `ski.rules`, all at once: every pair fires | no | yes |
| `ski.rules`, by need: only the pairs the result needs | yes, on the terms tested | yes |
| [`lazy.rules`](lazy.rules), all at once: every pair fires | yes, on the terms tested | no |

**All at once** is how the IVM works. An application fires as soon as its function is a
value, wanted or not. An argument that $K$ is about to discard runs anyway, and if it
never finishes, neither does the net.

**By need**, a cursor starts at the root and fires a pair only when it is waiting on it.
The cursor is a marker that moves only to work the result needs. A shared term is
evaluated once, when one of its copies is first asked for. The cursor is part of the
reducer (`reduce_by_need` in `inets`), not of the net: the 27 rules are untouched.

**`lazy.rules`** puts the cursor in the net. An application in a term is an inert node,
`ap`. A demand is an agent, `ev`, that turns an `ap` into an `app` and goes on to the
function. Every `app` is then there because its result was asked for, and a machine that
fires everything does only wanted work. The table has 15 agents and 50 rules. What it
gives up is sharing: a duplicator that meets an `ap` copies it unevaluated, so each copy
is evaluated by whoever asks. Its count of contractions equals the count of steps of tree
reduction, on every term tested.

Can one net both stop and share? Not locally. An agent can be reached only through its one
principal port, so a piece of net that waits to be asked cannot be woken from two sides.
[`docs/ski-system.md`](../docs/ski-system.md) gives the argument as a proof on paper; its
assumptions are stated there. It does not rule out a net that is its own reducer, and one
exists here: see [the last section](#a-graph-reducer-written-in-vine).

## Named nets

Every subterm of a closed term of $S$, $K$ and $I$ is closed, so any of them can be a
definition. `inets.ski.name_subterms` names subterms, and the term then holds a `ref` where
each stood. A reference that is applied is replaced by a fresh copy of what it names. A
reference that is duplicated is copied as a name, and the term it names is not touched.
The IVM treats a reference to a net the same way.

For `ski.rules` only subterms in normal form are named: a reference is expanded afresh at
each use, so naming unfinished work would repeat it. For `lazy.rules`, which shares no
work anyway, every subterm can be named.

## On the IVM

[`ivy.py`](ivy.py) writes a term as a net of the `ski:` system in Ivy, Vine's text for
nets, and translates that text to the IVM's own agents. The IVM has two kinds of binary
node, called combinators, with labels 0 and 1; an eraser; references to nets; and values
such as N32, a 32-bit number.

| `ski:` | `ivm:` |
|---|---|
| a value | a label-0 combinator holding a tag (an N32) and a payload |
| `dup` | a label-1 combinator |
| `era` | the eraser |
| `ref` | a reference to a net |
| `app`, `ev`, `nf` (an application, a demand for a value, a demand for the whole normal form) | a label-0 combinator that takes the value apart, and the IVM's branch on the tag, which picks the net for that rule |

```sh
$ python3 ski/ivy.py emit '```SKK0'
ski:term:0 {
  ^ = w1
  ski:s2(ski:k ski:k) = ski:app(ski:atom#0 w1)
}

$ export IVM=/path/to/ivm
$ python3 ski/ivy.py lower --demand '``KI```SII``SII' > kio.iv && "$IVM" run kio.iv
I
```

(The IVM's statistics follow on standard error.)

The nets for the rules of `app`, `ev` and `nf` are generated from the rule table. The
rules for `dup`, `era` and `ref` are not translated at all: the IVM's own commutation,
erasure and references do what those rules say, and the checks test this. Written by hand
are the table above, the order of the tags, the main net, and the nets that print a value.
The translation uses the IVM's N32 values and its branch; it is not a translation to
combinators alone.

## What was found

These come from the checks below. The terms are of $S$, $K$ and $I$ and have a normal form
by tree reduction within the scripts' caps. `check.py` calls the exhaustive test of every
term up to a size a census.

- **By need gives the right normal form on every term tried**: all 322,998 up to size 7.
  With every pair fired at once, 13 of those never stop.
- **By need never takes more contractions than SKIjack's reference reducer** on any term
  tried, and takes fewer on some. We have not found why the reference takes more.
- **`lazy.rules` stops on every one** with every pair fired, each in exactly as many
  contractions as tree reduction takes steps.
- **On the IVM, both tables give the right normal form** on all 47,155 terms of $S$, $K$,
  $I$ and two atoms up to size 5, with and without names. For reduction alone, the IVM
  spends 4.9 interactions for each one the table machine spends on `ski.rules`, and 2.3
  on `lazy.rules` (5.4 and 2.5 with names).

**Why a net copies.** A graph reducer lets many applications share one partial
application. A net cannot, because an application consumes the node it meets, so a value
used twice is copied node by node.

SKIjack's `tower` has three programs: an interpreter written in $S$, $K$ and $I$ running a
quoted program (t0), the quoted unquoter (t1), and the quoted interpreter itself (t2).
Each is reduced here until its head is a value.

| | t0 | t1 | t2 |
|---|---|---|---|
| SKIjack's reference reducer: contractions | 340 | 91,556 | 504,930 |
| `ski.rules` by need: contractions | 323 | 63,520 | 314,309 |
| `ski.rules` by need: copies | 2,702 | 2,030,766 | 31,013,168 |
| `ski.rules` by need: copies, with normal subterms named | 765 | 970,591 | 15,383,081 |
| `ski.rules`, all at once | does not stop | not tried | not tried |
| `lazy.rules`, all at once: contractions | 340 | does not finish | not tried |
| `lazy.rules` on the IVM: IVM interactions | 60,797 | not tried | not tried |

Each answer that was reached equals the reference's. Some entries come from runs made by
hand that the kept scripts do not repeat: the t2 figures, the 340 for `lazy.rules` on t0,
and the "does not stop" and "does not finish" entries; `docs/ski-system.md` says which. Naming cuts
the copying to between a quarter and a half, and changes no contraction count.

## Files

| File | Holds |
|---|---|
| `ski.rules` | The system: 12 agents, 27 rules |
| `lazy.rules` | The system with the demand carried in the net: 15 agents, 50 rules |
| `machine.py` | The two tables loaded by `inets`, and a net that also counts each rule applied and the most nodes at once |
| `ivy.py` | A term as Ivy text in the `ski:` system, and the translation to the IVM's agents |
| `check.py` | The census: both tables against tree reduction and the reference reducer |
| `skijack_check.py` | SKIjack's `tower` programs by need, against its reference reducer |
| `ivm_check.py` | The translated programs run on the IVM |

## The checks

```sh
inets check ski/ski.rules               # complete and typed; also ski/lazy.rules
python3 ski/check.py all                # the census to size 6, both tables; about a minute
python3 ski/check.py census 7           # ski.rules to size 7; a few minutes
python3 ski/check.py demand 7           # lazy.rules to size 7; a few minutes
```

With SKIjack's packages installed (`skijack`, `aviary_kernel`):

```sh
python3 ski/skijack_check.py t0 t1      # about four minutes; t2 has not been run with inets (see Limits)
```

With an `ivm` binary built from VineLang/vine (tested at commit `cf0c325`):

```sh
export IVM=/path/to/ivm
python3 ski/ivm_check.py 5                  # ski.rules translated, on the IVM
python3 ski/ivm_check.py 5 --names          # with normal subterms named
python3 ski/ivm_check.py 5 --demand         # lazy.rules translated; --names may be added
python3 ski/ivm_check.py --skijack t0       # SKIjack's t0 on the IVM (needs its packages too)
```

Each script's opening lines say what it compares.

## Limits

- The evidence is tests, on small terms and three programs. There is no simulation theorem;
  the typing argument and the argument about sharing are on paper.
- The machine (`inets`) is a general reference implementation in Python, not a tool. On
  t1 it is about five times slower than the machine written for this table that it
  replaced (55 and 56 s against 12 and 10 s by need, with inets 0.1.3, in runs alternated
  on one machine on 2026-11-25; the machine was under load, so the ratio is rough). t2 took about six and a half minutes and several GB of memory on
  the old machine and has not been run with `inets`; at the same ratio it would take
  about half an hour, a guess that has not been measured.
- By need never fires an eraser, so the machine sweeps away what the root cannot reach.
  That is housekeeping, not a rule. It changes the count of copies, never the count of
  contractions or the answer.
- Reading a result back unfolds all sharing.
- The translated programs print atoms 0 to 9 only, and a term whose arguments nest more
  than a few thousand deep cannot be written as Ivy text unless its subterms are named
  first.
- The translation leans on the IVM's N32 values and branch.

## A graph reducer written in Vine

[`skivine/graph.vi`](../skivine/graph.vi) is not part of the `ski:` system. It is $S$, $K$
and $I$ by graph reduction, written in Vine as an ordinary program: the term is a graph in
an array, nodes name their parts by position, and a reduced application is overwritten in
place. That is a net that is its own reducer. It runs t1 and t2 on the IVM with shared
work, at about 3,000 IVM interactions for each contraction. It makes the same
contractions as reduction by need: 63,520 on t1 (a script checks this) and 314,309 on t2
(the figure to match comes from a run by hand). See
[`docs/graph-machine.md`](../docs/graph-machine.md).

Set beside the table above, it shows what the agents cost and what they would save. By
need, the table machine takes about two million of its interactions on t1, and the IVM
cannot run the agents that way. `graph.vi` takes two hundred million IVM interactions, and
the IVM can run it. The two counts are of different machines' interactions.
