"""The ski: tables in this directory, run by the `inets` package.

The tables (`ski.rules`, `lazy.rules`) are this repository's; the machine that reads,
checks and reduces them is `inets` (https://github.com/sigilante/inets), which grew out
of the code that was here. What this module adds is what the checks here print beside
the package's results: how often each rule of the table was applied (`Net.used`, by the
line the rule starts on) and the most nodes the net held at once (`Net.most`).

    run(term, schedule, ...)    schedule "need" (ski.rules, by need), "rounds" (ski.rules,
                                every pair fired) or "lazy" (lazy.rules, every pair fired)

Reduction by need sweeps away what is no longer wanted, and in a sweep a duplicator that
has lost one of its copies is removed and its input joined to the copy that is left
(`collapse` in `inets.Net.sweep`). Contractions do not depend on that; copies do.
"""
import os
from dataclasses import dataclass

import inets
from inets import ski
from inets.ski import Ref, parse, show, unfold, is_normal, name_subterms, ARITY, PARTIAL  # noqa: F401

HERE = os.path.dirname(os.path.abspath(__file__))
_SYSTEMS = {}


def system(lazy=False):
    """ski.rules, or lazy.rules, read by inets."""
    name = "lazy.rules" if lazy else "ski.rules"
    if name not in _SYSTEMS:
        _SYSTEMS[name] = inets.System.load(os.path.join(HERE, name))
    return _SYSTEMS[name]


class Net(inets.Net):
    """An inets net that also tallies each rule applied and the most nodes at once."""

    def __init__(self, system, host=None):
        super().__init__(system, host)
        self.used = {}
        self.most = 0

    def fire(self, a, b):
        rule = super().fire(a, b)
        self.used[rule.line] = self.used.get(rule.line, 0) + 1
        self.most = max(self.most, len(self.kind))
        return rule


@dataclass
class Run:
    net: Net
    result: inets.Result
    term: object        # the term read back, or None if the run stopped at its cap
    root: tuple


def run(term, schedule="need", definitions=None, direct=False, deep=True, sweep_above=20000,
        max_interactions=10 ** 6):
    """As `inets.ski.run`, with the tables here and a `Net` that keeps the tallies above."""
    if schedule not in ("need", "rounds", "lazy"):
        raise ValueError('schedule is "need", "rounds" or "lazy"')
    if isinstance(term, str):
        term = parse(term)
    definitions = definitions or {}
    lazy = schedule == "lazy"
    if not lazy:
        for k, t in definitions.items():
            if not is_normal(t):
                raise ValueError(f"the term named {k} is not in normal form: with ski.rules only normal forms may be named")
    host = inets.Library({k: (lambda net, t=t: ski.encode(net, t, direct)) for k, t in definitions.items()})
    net = Net(system(lazy), host)
    root = net.free()
    out = ski.encode(net, term, direct)
    if lazy:
        ask = net.add_node("nf")
        net.wire((ask, 0), out)
        net.wire(root, (ask, 1))
    else:
        net.wire(root, out)
    if schedule == "need":
        result = net.reduce_by_need(root, deep, sweep_above, max_interactions, collapse=("dup",))
    else:
        result = net.reduce_in_rounds(max_interactions)
    net.most = max(net.most, len(net.kind))
    return Run(net, result, ski.read_back(net, root, definitions) if result.finished else None, root)
