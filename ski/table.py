#!/usr/bin/env python3
"""Reads an interaction system written as a table (ski.rules) and checks it.

    table.py [FILE]        (default: ski.rules beside this script)

A value is an agent whose principal port is an output (+); a consumer is one whose
principal port is an input (-). Checks:
- there is exactly one rule for each consumer and value, and no other rule;
- in each rule every auxiliary port of the pair is used exactly once, every new wire has
  exactly two ends, and every connection the rule makes joins an output to an input. (An
  `expand` rule makes no connections here: the machine puts a term's output where the
  value's was.)

The second check is a typing of the rules. A net built from a term joins outputs to
inputs only; if every rule keeps that, then the only pairs of principal ports that can ever
meet are a consumer's and a value's, and the first check says each has a rule. So no pair
can be stuck for want of one. This is an argument, checked rule by rule here; it is not a
machine-checked proof about nets.
"""
import os, re, sys

TOKEN = re.compile(r"\s*(><|[()=;]|[A-Za-z_][A-Za-z_0-9]*)")


def tokens(text):
    out, at = [], 0
    text = text.strip()
    while at < len(text):
        m = TOKEN.match(text, at)
        if not m:
            raise SyntaxError("cannot read: " + text[at:])
        out.append(m.group(1))
        at = m.end()
    return out


class Agent:
    def __init__(self, name, ports, param):
        self.name, self.ports, self.param = name, ports, param  # ports: "+" / "-" each
        self.arity = len(ports) - 1
        self.value = ports[0] == "+"


class Rule:
    """left, right: (agent name, parameter name or None, [auxiliary names]).
    nodes: [(agent name, parameter name or None)], the nodes the rule makes.
    links: [(end, end)], an end being ("ext", name) for what was joined to the pair's
    auxiliary port of that name, or ("new", node index, port index)."""

    def __init__(self):
        self.left = self.right = None
        self.count = None
        self.nodes, self.links, self.line, self.text = [], [], 0, ""
        self.expand = None  # the parameter naming the term to expand, for an `expand` rule

    def title(self):
        show = lambda s: s[0] + (" " + s[1] if s[1] else "") + (" (" + " ".join(s[2]) + ")" if s[2] else "")
        return show(self.left) + " >< " + show(self.right)


def parse_side(toks, agents):
    agent = agents[toks.pop(0)]
    param = toks.pop(0) if agent.param else None
    aux = []
    if agent.arity:
        assert toks.pop(0) == "(", "expected ("
        while toks[0] != ")":
            aux.append(toks.pop(0))
        toks.pop(0)
    assert len(aux) == agent.arity, f"{agent.name} has {agent.arity} auxiliary ports"
    return (agent.name, param, aux)


def parse_term(toks, agents, rule, raw):
    """An end: ("var", name) or ("new", node index, 0). Makes nodes and raw links."""
    head = toks.pop(0)
    if head not in agents:
        return ("var", head)
    agent = agents[head]
    param = toks.pop(0) if agent.param else None
    index = len(rule.nodes)
    rule.nodes.append((head, param))
    if agent.arity:
        assert toks.pop(0) == "(", "expected ( after " + head
        port = 1
        while toks[0] != ")":
            raw.append((("new", index, port), parse_term(toks, agents, rule, raw)))
            port += 1
        toks.pop(0)
        assert port == agent.arity + 1, f"{head} has {agent.arity} auxiliary ports"
    return ("new", index, 0)


def parse_body(text, agents, rule):
    raw = []
    toks = tokens(text)
    if len(toks) == 2 and toks[0] == "expand":
        rule.expand = toks[1]
        return
    if toks != ["nothing"]:
        while toks:
            a = parse_term(toks, agents, rule, raw)
            assert toks.pop(0) == "=", "expected ="
            raw.append((a, parse_term(toks, agents, rule, raw)))
            if toks:
                assert toks.pop(0) == ";", "expected ;"
    bound = set(rule.left[2] + rule.right[2])
    # Ends named by a bound letter become ("ext", name). A new wire's two ends are joined.
    ends = lambda e: ("ext", e[1]) if e[0] == "var" and e[1] in bound else e
    raw = [(ends(a), ends(b)) for a, b in raw]
    while True:
        fresh = next((e for pair in raw for e in pair if e[0] == "var"), None)
        if fresh is None:
            break
        uses = [(i, pair) for i, pair in enumerate(raw) if fresh in pair]
        if len(uses) == 1 and uses[0][1][0] == uses[0][1][1]:
            raise SyntaxError(f"wire {fresh[1]} is joined to itself")
        if len(uses) != 2:
            raise SyntaxError(f"new wire {fresh[1]} has {len(uses)} ends, not two")
        (i, p), (j, q) = uses
        other = lambda pair: pair[1] if pair[0] == fresh else pair[0]
        raw = [pair for k, pair in enumerate(raw) if k not in (i, j)] + [(other(p), other(q))]
    rule.links = raw


def load(path):
    agents, rules, rule = {}, [], None
    for number, line in enumerate(open(path), 1):
        line = line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        word, rest = (line.split(None, 1) + [""])[:2]
        try:
            if word == "agent":
                parts = rest.split()
                param = None
                if "param" in parts:
                    param = parts[parts.index("param") + 1]
                    parts = parts[:parts.index("param")]
                assert all(p in "+-" for p in parts[1:]) and len(parts) > 1, "ports are + or -"
                agents[parts[0]] = Agent(parts[0], parts[1:], param)
            elif word == "rule":
                rule = Rule()
                rule.line = number
                rules.append(rule)
                left, right = rest.split("><")
                rule.left = parse_side(tokens(left), agents)
                rule.right = parse_side(tokens(right), agents)
            elif word == "=>":
                rule.text = rest.strip()
                parse_body(rest, agents, rule)
            elif word == "count":
                rule.count = rest.strip()
            else:
                raise SyntaxError("unknown line")
        except (AssertionError, SyntaxError, KeyError, IndexError) as e:
            sys.exit(f"{path}:{number}: {e}")
    return agents, rules


def check(agents, rules):
    problems = []
    seen = {}
    for r in rules:
        left, right = agents[r.left[0]], agents[r.right[0]]
        if left.value or not right.value:
            problems.append(f"line {r.line}: a rule is written consumer >< value")
            continue
        if (left.name, right.name) in seen:
            problems.append(f"line {r.line}: a second rule for {left.name} >< {right.name}")
        seen[(left.name, right.name)] = r
        if r.count is None:
            problems.append(f"line {r.line}: no count")
        # What each bound letter is joined to, seen from outside the pair: the opposite of
        # its port on the consumed node.
        flip = {"+": "-", "-": "+"}
        outside = {}
        for (name, _, aux), agent in ((r.left, left), (r.right, right)):
            for letter, sign in zip(aux, agent.ports[1:]):
                if letter in outside:
                    problems.append(f"line {r.line}: {letter} names two ports")
                outside[letter] = flip[sign]
        params = {p for p in (r.left[1], r.right[1]) if p}
        for name, param in r.nodes:
            if (param is None) != (agents[name].param is None) or (param and param not in params):
                problems.append(f"line {r.line}: {name}'s parameter is missing or unknown")

        def sign(end):
            if end[0] == "ext":
                return outside[end[1]]
            return agents[r.nodes[end[1]][0]].ports[end[2]]

        if r.expand:
            # The consumer keeps its ports; the value must have none and carry the name.
            if right.arity or r.expand != r.right[1]:
                problems.append(f"line {r.line}: expand needs a value with no ports and its own parameter")
            continue
        used = [e[1] for pair in r.links for e in pair if e[0] == "ext"]
        for letter in outside:
            if used.count(letter) != 1:
                problems.append(f"line {r.line}: port {letter} is used {used.count(letter)} times, not once")
        ends = [e for pair in r.links for e in pair if e[0] == "new"]
        for index, (name, _) in enumerate(r.nodes):
            for port in range(agents[name].arity + 1):
                if ends.count(("new", index, port)) != 1:
                    problems.append(f"line {r.line}: port {port} of the new {name} is joined {ends.count(('new', index, port))} times")
        for a, b in r.links:
            if sign(a) == sign(b):
                problems.append(f"line {r.line}: joins two {'outputs' if sign(a) == '+' else 'inputs'}")
    for c in agents.values():
        for v in agents.values():
            if not c.value and v.value and (c.name, v.name) not in seen:
                problems.append(f"no rule for {c.name} >< {v.name}")
    return problems


def default_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "ski.rules")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else default_path()
    agents, rules = load(path)
    problems = check(agents, rules)
    for r in rules:
        print(f"{r.count:<9} {r.title():<28} => {r.text}")
    values = sum(1 for a in agents.values() if a.value)
    print(f"{len(agents)} agents ({values} values, {len(agents) - values} consumers), {len(rules)} rules")
    for p in problems:
        print("PROBLEM:", p)
    sys.exit(1 if problems else 0)
