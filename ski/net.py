#!/usr/bin/env python3
"""A net machine for an interaction system given as a table (table.py), with two
schedules, and terms of S, K, I and atoms read into and out of nets.

A term is "S", "K", "I", an int (an atom), or a pair (function, argument).

Schedules:
- `run_all`: every active pair, in rounds, until none is left. This is how the IVM reduces.
  Work that is no longer wanted still runs, so a term such as K I Ω never stops.
- `normalize`: by need. A cursor starts at the root and asks for the value there; a pair
  is fired only when the cursor is waiting on it. An application is fired when its result
  is asked for and its function has become a value; a duplicator, when one of its copies is
  asked for and its term has become a value, so a shared term is evaluated once. When the
  root is a value, its arguments are asked for from left to right. Erasers are never asked,
  and what they would erase is left where it is.

The rules are the table's; nothing here knows what S does.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table

HEADS = {"S": ("S", "S1", "S2"), "K": ("K", "K1")}


class Stop(Exception):
    """A cap was reached."""


class Net:
    def __init__(self, agents=None, rules=None):
        if agents is None:
            agents, rules = table.load(table.default_path())
        self.agents = agents
        self.rules = {(r.left[0], r.right[0]): r for r in rules}
        self.kind, self.param, self.link = {}, {}, {}
        self.next = 0
        self.counts = {}
        self.used = {}
        self.fired = 0
        self.most = 0          # most nodes at once
        self.collect_at = 20000  # reduction by need collects when the net passes this size
        self.collected = 0

    # --- building ---------------------------------------------------------------------

    def new(self, kind, param=None):
        self.next += 1
        self.kind[self.next] = kind
        if param is not None:
            self.param[self.next] = param
        return self.next

    def wire(self, p, q):
        self.link[p] = q
        self.link[q] = p

    def encode(self, term):
        """The output port of a term. (An explicit stack, since terms can be deep.)"""
        result = [None]
        work = [(term, result, 0)]
        pending = []
        while work:
            t, box, at = work.pop()
            if isinstance(t, str):
                box[at] = (self.new(t), 0)
            elif isinstance(t, int):
                box[at] = (self.new("atom", t), 0)
            else:
                a = self.new("app")
                ports = [None, None]
                pending.append((a, ports))
                box[at] = (a, 2)
                work.append((t[0], ports, 0))
                work.append((t[1], ports, 1))
        for a, ports in pending:
            self.wire((a, 0), ports[0])
            self.wire((a, 1), ports[1])
        return result[0]

    @classmethod
    def of(cls, term, agents=None, rules=None):
        net = cls(agents, rules)
        net.root = (net.new("root"), 0)
        net.wire(net.root, net.encode(term))
        return net

    # --- one interaction --------------------------------------------------------------

    def is_value(self, node):
        kind = self.kind[node]
        return kind != "root" and self.agents[kind].value

    def fire(self, c, v):
        """The consumer c meets the value v on their principal ports."""
        rule = self.rules[(self.kind[c], self.kind[v])]
        outside, params = {}, {}
        for node, (_, param, aux) in ((c, rule.left), (v, rule.right)):
            if param:
                params[param] = self.param[node]
            for i, letter in enumerate(aux, 1):
                outside[letter] = self.link[(node, i)]
        for node in (c, v):
            for i in range(self.agents[self.kind[node]].arity + 1):
                del self.link[(node, i)]
            del self.kind[node]
            self.param.pop(node, None)
        made = [self.new(name, params[p] if p else None) for name, p in rule.nodes]
        port = lambda end: outside[end[1]] if end[0] == "ext" else (made[end[1]], end[2])
        for a, b in rule.links:
            self.wire(port(a), port(b))
        self.counts[rule.count] = self.counts.get(rule.count, 0) + 1
        self.used[rule.line] = self.used.get(rule.line, 0) + 1
        self.fired += 1
        if len(self.kind) > self.most:
            self.most = len(self.kind)

    # --- schedules --------------------------------------------------------------------

    def active(self):
        out = []
        for n, kind in self.kind.items():
            if kind != "root" and not self.agents[kind].value:
                q = self.link[(n, 0)]
                if q[1] == 0 and self.is_value(q[0]):
                    out.append((n, q[0]))
        return out

    def run_all(self, max_fired=200000, max_nodes=200000):
        """Every active pair, in rounds. Returns the number of rounds; raises Stop."""
        rounds = 0
        while True:
            pairs = self.active()
            if not pairs:
                return rounds
            for c, v in pairs:
                self.fire(c, v)
            rounds += 1
            if self.fired > max_fired or len(self.kind) > max_nodes:
                raise Stop

    def value_at(self, port, max_fired, max_nodes):
        """Fires what is needed for the output joined to the input `port` to be a
        value's principal port. Returns that value's node."""
        stack = [port]
        while stack:
            n, i = self.link[stack[-1]]
            if self.is_value(n):
                stack.pop()
                continue
            # n is an application whose result, or a duplicator whose copy, is wanted.
            f = self.link[(n, 0)]
            if f[1] == 0 and self.is_value(f[0]):
                self.fire(n, f[0])
                if self.fired > max_fired:
                    raise Stop
                if len(self.kind) > self.collect_at:
                    self.collect()
                    self.collect_at = max(2 * len(self.kind), 20000)
                    if len(self.kind) > max_nodes:
                        raise Stop
                    stack = [port]
            else:
                stack.append((n, 0))
        return self.link[port][0]

    def collect(self):
        """Housekeeping for reduction by need, not a rule of the system: removes every
        node the root cannot reach. Reduction by need never fires an eraser, so what an
        eraser holds stays until this removes it. A duplicator one of whose copies is
        unreachable is replaced by a wire to the other copy: copying and discarding one
        copy leaves the term as it was."""
        live, stack = set(), [self.link[self.root]]
        while stack:
            n = stack.pop()[0]
            if n in live:
                continue
            live.add(n)
            for j, sign in enumerate(self.agents[self.kind[n]].ports):
                if sign == "-":
                    stack.append(self.link[(n, j)])
        live.add(self.root[0])
        halved = []
        for n in [n for n in self.kind if n not in live]:
            for j in range(self.agents[self.kind[n]].arity + 1):
                q = self.link.pop((n, j))
                if q[0] in live:
                    # Only a duplicator's copy port can be held by an unreachable node.
                    assert self.kind[q[0]] == "dup" and q[1] in (1, 2), (self.kind[q[0]], q)
                    halved.append(q)
            del self.kind[n]
            self.param.pop(n, None)
        for n, dead in halved:
            source, other = self.link[(n, 0)], self.link[(n, 3 - dead)]
            for j in (0, 3 - dead):
                del self.link[(n, j)]
            self.link.pop((n, dead), None)
            del self.kind[n]
            self.wire(source, other)
        self.collected += 1

    def normalize(self, max_fired=200000, max_nodes=200000):
        """By need, to normal form: the root's value, then its arguments from the left."""
        todo = [self.root]
        while todo:
            v = self.value_at(todo.pop(), max_fired, max_nodes)
            for i in range(self.agents[self.kind[v]].arity, 0, -1):
                todo.append((v, i))

    def head(self, max_fired=200000, max_nodes=200000):
        """By need, to a value at the root only."""
        self.value_at(self.root, max_fired, max_nodes)

    # --- reading back -----------------------------------------------------------------

    def read(self, port=None, limit=10 ** 7):
        """The term whose output is joined to the input `port` (default: the root).
        Sharing is unfolded; `limit` bounds the nodes visited."""
        result = [None]
        work = [("go", self.link[port or self.root], result, 0)]
        seen = 0
        while work:
            op = work.pop()
            if op[0] == "pair":
                _, pair, box, at = op
                box[at] = (pair[0], pair[1])
                continue
            _, (n, i), box, at = op
            seen += 1
            if seen > limit:
                raise Stop
            kind = self.kind[n]
            if kind == "atom":
                box[at] = self.param[n]
            elif kind in ("S", "K", "I"):
                box[at] = kind
            elif kind in ("K1", "S1"):
                pair = [kind[0], None]
                work.append(("pair", pair, box, at))
                work.append(("go", self.link[(n, 1)], pair, 1))
            elif kind == "S2":
                inner, pair = ["S", None], [None, None]
                work.append(("pair", pair, box, at))
                work.append(("go", self.link[(n, 2)], pair, 1))
                work.append(("pair", inner, pair, 0))
                work.append(("go", self.link[(n, 1)], inner, 1))
            elif kind == "stuck" or (kind == "app" and i == 2):
                pair = [None, None]
                first = (n, 1) if kind == "stuck" else (n, 0)
                second = (n, 2) if kind == "stuck" else (n, 1)
                work.append(("pair", pair, box, at))
                work.append(("go", self.link[second], pair, 1))
                work.append(("go", self.link[first], pair, 0))
            elif kind == "dup" and i in (1, 2):
                work.append(("go", self.link[(n, 0)], box, at))
            else:
                raise ValueError((kind, i))
        return result[0]


def parse(text):
    """Prefix form: a backtick applies the next two terms; S, K, I; a digit is an atom."""
    pos = 0

    def term():
        nonlocal pos
        while text[pos].isspace():
            pos += 1
        ch = text[pos]
        pos += 1
        if ch == "`":
            f = term()
            return (f, term())
        return int(ch) if ch.isdigit() else ch

    return term()


def show(t):
    out, stack = [], [t]
    while stack:
        u = stack.pop()
        if isinstance(u, tuple):
            out.append("`")
            stack.append(u[1])
            stack.append(u[0])
        else:
            out.append(str(u))
    return "".join(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    every = "--all" in args
    args = [a for a in args if a != "--all"]
    net = Net.of(parse(args[0] if args else sys.stdin.read()))
    rounds = None
    try:
        rounds = net.run_all() if every else net.normalize()
        print(show(net.read()))
    except Stop:
        print("stopped at a cap")
    print(" ".join(f"{k}={v}" for k, v in sorted(net.counts.items())) + (f" rounds={rounds}" if rounds is not None else "") + f" most_nodes={net.most}", file=sys.stderr)
