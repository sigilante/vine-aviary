#!/usr/bin/env python3
"""The ski: system as Ivy text, and its lowering to the IVM's own agents.

    ivy.py emit [--demand] TERM...     the terms as nets of the ski: system, in Ivy text
    ivy.py lower [--demand] TERM...    the same lowered to the ivm: system: a program for
                                       `ivm run` that prints each term's normal form on a line

Without --demand the table is ski.rules; with it, lazy.rules, where an application in a
term is the inert `ski:ap` and the demand is carried by `ski:ev` and `ski:nf`.

A term is in prefix form (`inets.ski.parse`); its arguments may nest a few thousand deep
at most, unless its subterms are named first (`inets.ski.name_subterms`). Ivy is Vine's text for nets: a file is named nets, a
net is equations between trees of nodes, a node stands for its principal port, a wire is a
name used twice, and `^` is the net's free port.

**ski: text.** One node for each agent of ski.rules, with its auxiliary ports as children:
`ski:s`, `ski:k`, `ski:i`, `ski:k1(x)`, `ski:s1(x)`, `ski:s2(x y)`, `ski:atom#3`,
`ski:stuck(h x)`, `ski:app(argument result)`, `ski:dup(p q)`, `ski:era`,
`ski:ref[NAME]` for a reference to the net NAME, and for lazy.rules `ski:ap(function
argument)`, `ski:ev(to)` and `ski:nf(to)`. A term's net has the term's output on its
free port.

**The lowering** is agent by agent, as Vine lowers its own system to the IVM's:

| ski: | ivm: |
|---|---|
| a value | a label-0 combinator holding a tag (an N32) and a payload: nothing, one port, a pair of ports, or an atom's number |
| `ski:dup` | a label-1 combinator, which copies such a node by commuting with it |
| `ski:era` | the eraser |
| `ski:ref[N]` | a reference to the net N: the IVM expands it at a label-0 combinator and copies it at a label-1 one, which are the table's three rules for `ref` |
| `ski:app`, `ski:ev`, `ski:nf` | a label-0 combinator that takes the value apart, then the IVM's branch on the tag, which picks the net for that consumer's rule with that value and joins it to the payload and the consumer's own ports |

The nets for the rules are not written here: each rule of the table for one of those
consumers is lowered, right-hand side and all, by the same table of agents. In lazy.rules
`ski:ap` is one more tagged value. Written by hand, and not
derived from the rule table: how each agent is lowered (above), the order of the tags, the
main net, and the nets that print a value. The duplication and erasure
rules are not lowered at all: the claim, which the checks test, is that the IVM's own
commutation and erasure do to the lowered nodes what those rules say.

The IVM fires every pair, so a lowered program behaves as reducing every pair in rounds
does, not as reduction by need. By ski.rules a term whose dropped argument never stops never stops; by lazy.rules
it stops, but no work is shared.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from machine import system, Ref, parse as parse_term, ARITY, PARTIAL  # first: it checks the inets version
from inets import Expand, Ext, New

# The values that are lowered to a tagged node; the order is the tag. `ap`, an application
# not yet asked for, is one of them in a table that has it (lazy.rules).
VALUES = ["S", "K", "I", "K1", "S1", "S2", "atom", "stuck", "ap"]
TAG = {name: i for i, name in enumerate(VALUES)}
NODE = {"S": "ski:s", "K": "ski:k", "I": "ski:i", "K1": "ski:k1", "S1": "ski:s1", "S2": "ski:s2",
        "atom": "ski:atom", "stuck": "ski:stuck", "ap": "ski:ap", "ref": "ski:ref",
        "app": "ski:app", "ev": "ski:ev", "nf": "ski:nf", "dup": "ski:dup", "era": "ski:era"}
AGENT = {v: k for k, v in NODE.items()}


def tagged(agents):
    return [v for v in VALUES if v in agents]


def pack(kids):
    """Several ports as one: nothing, the port itself, or a pair."""
    if not kids:
        return node("ivm:eraser")
    return kids[0] if len(kids) == 1 else node("ivm:x", *kids)


# ---------------------------------------------------------------------------------------
# Trees. A tree is a wire name (str) or (path, payload, [names], [children]).

def node(path, *kids, payload=None, names=()):
    return (path, payload, list(names), list(kids))


def text_of(tree):
    if isinstance(tree, str):
        return tree
    path, payload, names, kids = tree
    out = path
    if payload is not None:
        out += f"#{payload}"
    if names:
        out += "[" + ", ".join(names) + "]"
    if kids:
        out += "(" + " ".join(text_of(k) for k in kids) + ")"
    return out


def net_text(name, eqs):
    return name + " {\n" + "".join(f"  {text_of(a)} = {text_of(b)}\n" for a, b in eqs) + "}\n"


# ---------------------------------------------------------------------------------------
# Terms to ski: text.

class Fresh:
    def __init__(self, prefix="w"):
        self.n, self.prefix = 0, prefix

    def __call__(self):
        self.n += 1
        return f"{self.prefix}{self.n}"


def term_net(term, fresh=None, lazy=False):
    """The equations of a net whose free port is the term's output. With `lazy` an
    application is the inert `ski:ap`, for a table that carries its demand in the net."""
    fresh = fresh or Fresh()
    eqs = []

    def out(t):
        if isinstance(t, str):
            return node(NODE[t])
        if isinstance(t, int):
            return node("ski:atom", payload=t)
        if isinstance(t, Ref):
            return node("ski:ref", names=[f"ski:def:{t.name}"])
        head, args = t, []
        while isinstance(head, tuple):
            args.append(head[1])
            head = head[0]
        args.reverse()
        take = min(len(args), ARITY[head] - 1) if isinstance(head, str) else 0
        if take:
            cur = node(NODE[PARTIAL[(head, take)]], *[out(a) for a in args[:take]])
        else:
            cur = out(head)
        for a in args[take:]:
            if isinstance(head, int):
                cur = node("ski:stuck", cur, out(a))
            elif lazy:
                cur = node("ski:ap", cur, out(a))
            else:
                r = fresh()
                eqs.append((cur, node("ski:app", out(a), r)))
                cur = r
        return cur

    eqs.insert(0, ("^", out(term)))
    return eqs


def emit(terms, defs=None, lazy=False):
    """ski: Ivy text: a net `ski:term:i` for each term and `ski:def:k` for each name."""
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 100000))
    try:
        parts = [net_text(f"ski:term:{i}", term_net(t, lazy=lazy)) for i, t in enumerate(terms)]
        parts += [net_text(f"ski:def:{k}", term_net(t, lazy=lazy)) for k, t in sorted((defs or {}).items())]
    except RecursionError:
        # The text is a tree as deep as the term's arguments nest, and it is written by
        # recursion: a few thousand levels is the most. Named terms nest one level each.
        raise ValueError("arguments nest too deeply to write as one tree: name the subterms first (inets.ski.name_subterms)") from None
    return "\n".join(parts)


# ---------------------------------------------------------------------------------------
# Reading Ivy text.

IVY = re.compile(r"\s*(?://[^\n]*\s*)*([{}()\[\],=^]|#[0-9]+|[A-Za-z0-9_:]+)")


def read(text):
    """{net name: [(tree, tree)]}."""
    toks, at = [], 0
    text = text.rstrip()
    while at < len(text):
        m = IVY.match(text, at)
        if not m:
            raise SyntaxError("cannot read: " + text[at:at + 40])
        toks.append(m.group(1))
        at = m.end()
    pos = 0

    def name():
        nonlocal pos
        path = toks[pos]
        pos += 1
        payload, names = None, []
        if pos < len(toks) and toks[pos].startswith("#"):
            payload = int(toks[pos][1:])
            pos += 1
        if pos < len(toks) and toks[pos] == "[":
            pos += 1
            while toks[pos] != "]":
                names.append(toks[pos])
                pos += 1
                if toks[pos] == ",":
                    pos += 1
            pos += 1
        return path, payload, names

    def tree():
        nonlocal pos
        if toks[pos] == "^" or ":" not in toks[pos]:
            pos += 1
            return toks[pos - 1]
        path, payload, names = name()
        kids = []
        if pos < len(toks) and toks[pos] == "(":
            pos += 1
            while toks[pos] != ")":
                kids.append(tree())
            pos += 1
        return (path, payload, names, kids)

    nets = {}
    while pos < len(toks):
        net = toks[pos]
        pos += 1
        assert toks[pos] == "{", "expected { after " + net
        pos += 1
        eqs = []
        while toks[pos] != "}":
            a = tree()
            assert toks[pos] == "=", "expected ="
            pos += 1
            eqs.append((a, tree()))
        pos += 1
        nets[net] = eqs
    return nets


# ---------------------------------------------------------------------------------------
# The lowering.

def n32(k):
    return node("ivm:n32", payload=k)


def branches(prefix, values):
    return node("ivm:branch", names=[f"{prefix}:{v.lower()}" for v in values])


def dispatch(prefix, rest, fresh, values):
    """A consumer that takes a value apart and joins the net `prefix:VALUE` to the
    value's payload and to the consumer's own ports (`rest`, packed as one)."""
    p = fresh()
    choose = node("ivm:ext:merge", branches(prefix, values), node("ivm:x", p, rest), names=["ivm:branch"])
    return node("ivm:x", choose, p)


def lower_tree(tree, fresh, values):
    """A ski: tree as an ivm: tree."""
    if isinstance(tree, str):
        return tree
    path, payload, names, kids = tree
    kids = [lower_tree(k, fresh, values) for k in kids]
    agent = AGENT[path]
    if agent == "dup":
        return node("ivm:y", *kids)
    if agent == "era":
        return node("ivm:eraser")
    if agent == "ref":
        return node("ivm:graft", names=names)
    if agent not in values:
        # A consumer that looks at what it meets: application, or a demand.
        return dispatch(path, pack(kids), fresh, values)
    if agent == "atom":
        # The number is a literal in a term, and a wire in a rule (where it is `k`).
        held = n32(payload) if isinstance(payload, int) else payload
    else:
        held = pack(kids)
    return node("ivm:x", n32(TAG[agent]), held)


def lower_net(eqs, values, fresh=None):
    fresh = fresh or Fresh("v")
    return [(lower_tree(a, fresh, values), lower_tree(b, fresh, values)) for a, b in eqs]


def rule_equations(rule, agents):
    """The right-hand side of a rule as equations between ski: trees. A port of the pair
    is the letter the rule names it by, and a wire between two new nodes is a new name."""
    body = rule.body
    wires = {}

    def end(e):
        if isinstance(e, Ext):
            return e.letter
        assert isinstance(e, New), f"{rule}: a rule that keeps a node of its pair is not lowered"
        i, j = e.node, e.port
        if j == 0:
            return trees[i]
        return wires.setdefault((i, j), f"n{i}p{j}")

    trees = [(NODE[name], param, [], [wires.setdefault((i, j), f"n{i}p{j}") for j in range(1, agents[name].arity + 1)])
             for i, (name, param) in enumerate(body.nodes)]
    return [(end(a), end(b)) for a, b in body.links]


def rule_nets(table):
    """For each rule of a consumer that looks at what it meets (application, a demand)
    and a tagged value, the ivm: net that the branch picks: its free port takes the
    value's payload, then the consumer's own ports."""
    values = tagged(table.agents)
    out = []
    for r in table.rules:
        if r.left.agent in ("dup", "era") or isinstance(r.body, Expand):
            continue
        payload = r.right.param if r.right.param else pack(list(r.right.aux))
        fresh = Fresh("v")
        eqs = [("^", node("ivm:x", payload, pack(list(r.left.aux))))]
        eqs += [(lower_tree(a, fresh, values), lower_tree(b, fresh, values)) for a, b in rule_equations(r, table.agents)]
        out.append(net_text(f"{NODE[r.left.agent]}:{r.right.agent.lower()}", simplify(eqs)))
    return out


def simplify(eqs):
    """Ivy wants each wire named exactly twice and has no use for `a = b` between two
    wires: such an equation is removed by renaming."""
    eqs = list(eqs)
    while True:
        i = next((i for i, (a, b) in enumerate(eqs) if isinstance(a, str) and isinstance(b, str) and "^" not in (a, b)), None)
        if i is None:
            return eqs
        a, b = eqs.pop(i)

        def rename(t):
            if isinstance(t, str):
                return a if t == b else t
            return (t[0], rename(t[1]) if isinstance(t[1], str) else t[1], t[2], [rename(k) for k in t[3]])

        eqs = [(rename(x), rename(y)) for x, y in eqs]


def print_char(code, io_in, io_out):
    """An equation: the IO value arriving on io_in prints a character and leaves on io_out."""
    return (io_in, node("ivm:ext:merge", n32(code) if isinstance(code, int) else code, io_out, names=["root:io:print_char"]))


def show_nets(values):
    """Nets that print a value in prefix form: free port takes the payload, then the IO
    value in and out. Written by hand; they are the host's business, not the system's.
    An application not yet asked for is asked for, and its value printed."""
    def shown(value, i, o, fresh):
        return (value, dispatch("ski:show", node("ivm:x", i, o), fresh, values))

    out = []
    for name in values:
        fresh = Fresh("v")
        eqs = []
        if name in ("S", "K", "I"):
            payload = node("ivm:eraser")
            eqs.append(print_char(ord(name), "i", "o"))
        elif name in ("K1", "S1"):
            payload = "x"
            eqs += [print_char(96, "i", "a"), print_char(ord(name[0]), "a", "b"), shown("x", "b", "o", fresh)]
        elif name == "S2":
            payload = node("ivm:x", "x", "y")
            eqs += [print_char(96, "i", "a"), print_char(96, "a", "b"), print_char(83, "b", "c"),
                    shown("x", "c", "d", fresh), shown("y", "d", "o", fresh)]
        elif name == "atom":
            payload = "k"
            eqs.append(("k", node("ivm:ext:merge", n32(48), "c", names=["vi:n32:add"])))
            eqs.append(print_char("c", "i", "o"))
        elif name == "ap":
            # f = ev (c); c = app (a d), and d is printed.
            payload = node("ivm:x", "f", "a")
            eqs.append(("f", lower_tree(node("ski:ev", "c"), fresh, values)))
            eqs.append(("c", lower_tree(node("ski:app", "a", "d"), fresh, values)))
            eqs.append(shown("d", "i", "o", fresh))
        else:
            payload = node("ivm:x", "x", "y")
            eqs += [print_char(96, "i", "a"), shown("x", "a", "b", fresh), shown("y", "b", "o", fresh)]
        eqs.insert(0, ("^", node("ivm:x", payload, node("ivm:x", "i", "o"))))
        out.append(net_text(f"ski:show:{name.lower()}", eqs))
    return out


def lower(ski_text, table=None):
    """ski: Ivy text as a program in the ivm: system that prints each `ski:term:i`'s
    normal form on a line, by `table` (an `inets.System`; ski.rules if not given)."""
    table = table or system()
    nets = read(ski_text)
    values = tagged(table.agents)

    def atoms(tree):
        if not isinstance(tree, str):
            if tree[0] == "ski:atom" and not 0 <= tree[1] <= 9:
                raise ValueError(f"the lowered program prints atoms 0 to 9 only, not {tree[1]}")
            for kid in tree[3]:
                atoms(kid)

    for body in nets.values():
        for a, b in body:
            atoms(a)
            atoms(b)
    parts = []
    count = sum(1 for n in nets if n.startswith("ski:term:"))
    fresh = Fresh("m")
    eqs, io = [], "io0"
    for i in range(count):
        mid, after = fresh(), fresh()
        eqs.append((node("ivm:graft", names=[f"ski:term:{i}"]), dispatch("ski:show", node("ivm:x", io, mid), fresh, values)))
        eqs.append(print_char(10, mid, after))
        io = after
    eqs.insert(0, ("^", node("ivm:x", "io0", io)))
    parts.append(net_text("iv:main", eqs))
    for name, body in nets.items():
        parts.append(net_text(name, lower_net(body, values)))
    parts += rule_nets(table)
    parts += show_nets(values)
    return "\n".join(parts)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("emit", "lower"):
        sys.exit("usage: ivy.py emit|lower [--demand] TERM...")
    mode, texts = sys.argv[1], sys.argv[2:]
    demand = "--demand" in texts
    terms = [parse_term(t) for t in texts if t != "--demand"]
    ski = emit(terms, lazy=demand)
    print(ski if mode == "emit" else lower(ski, system(demand)))
