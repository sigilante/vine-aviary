#!/usr/bin/env python3
"""Compares tools/birds.py with the registry of an installed aviary_kernel.
Usage: check_table.py [path/to/aviary/checkout]"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) > 1:
    sys.path.insert(0, sys.argv[1])
from birds import BIRDS, parse_rule
from aviary_kernel.birds import BIRDS as THEIRS
from aviary_kernel.terms import Atom


def tree(t):
    return t.name if isinstance(t, Atom) else (tree(t.fn), tree(t.arg))


ours = {name: (arity, parse_rule(rule)) for name, _, _, arity, rule in BIRDS}
theirs = {b.name: (b.arity, tree(b.rule)) for b in THEIRS}
bad = sorted(n for n in ours.keys() | theirs.keys() if ours.get(n) != theirs.get(n))
print(f"{len(ours)} birds here, {len(theirs)} in aviary_kernel, {len(bad)} differences {bad}")
sys.exit(1 if bad else 0)
