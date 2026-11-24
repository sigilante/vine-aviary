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
(`collapse` in `inets.Net.sweep`; the tables declare `dup` a duplicator). Contractions do
not depend on that; copies do.
"""
import os
import re
import inets
from inets import ski
from inets.errors import TermError

if tuple(int(re.match(r"\d*", x).group() or 0) for x in inets.__version__.split(".")[:3]) < (0, 1, 3):
    raise ImportError(f"ski/machine.py needs inets 0.1.3 or later (for the tables' declared duplicator and "
                      f"inets.ski.run's table and net_class); this is inets {inets.__version__}: pip install 'inets>=0.1.3'")
from inets.ski import Ref, Run, parse, show, unfold, is_normal, name_subterms, ARITY, PARTIAL  # noqa: F401

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


def run(term, schedule="need", definitions=None, direct=False, deep=True, sweep_above=20000,
        max_interactions=10 ** 6):
    """`inets.ski.run` with the tables here (in place of its `table`) and a `Net` that keeps
    the tallies above (in place of its `net_class`). The schedule "lazy" is lazy.rules
    reduced in rounds."""
    if schedule not in ("need", "rounds", "lazy"):
        raise TermError('schedule is "need", "rounds" or "lazy"')
    lazy = schedule == "lazy"
    r = ski.run(term, "rounds" if lazy else schedule, definitions, direct, deep, sweep_above, max_interactions,
                table=system(lazy), net_class=Net)
    r.net.most = max(r.net.most, len(r.net.kind))
    return r
