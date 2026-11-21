"""The bird table: (name, Vine identifier, bird name, arity, rule).

The rule is the right-hand side over the formals a, b, c, ... in order; application
is juxtaposition and associates to the left. Transcribed from the registry of the
Aviary kernel (aviary_kernel/birds.py), whose rows were checked there against Rathman's
"Combinator Birds" chart and combinatorylogic.com. `tools/check_table.py` compares this
table with an installed aviary_kernel.
"""

BIRDS = (
    ("B", "B", "Bluebird", 3, "a (b c)"),
    ("B1", "B1", "Blackbird", 4, "a (b c d)"),
    ("B2", "B2", "Bunting", 5, "a (b c d e)"),
    ("B3", "B3", "Becard", 4, "a (b (c d))"),
    ("C", "C", "Cardinal", 3, "a c b"),
    ("C*", "Cs", "Cardinal Once Removed", 4, "a b d c"),
    ("C**", "Css", "Cardinal Twice Removed", 5, "a b c e d"),
    ("D", "D", "Dove", 4, "a b (c d)"),
    ("D1", "D1", "Dickcissel", 5, "a b c (d e)"),
    ("D2", "D2", "Dovekie", 5, "a (b c) (d e)"),
    ("E", "E", "Eagle", 5, "a b (c d e)"),
    ("Ê", "Eh", "Bald Eagle", 7, "a (b c d) (e f g)"),
    ("F", "F", "Finch", 3, "c b a"),
    ("F*", "Fs", "Finch Once Removed", 4, "a d c b"),
    ("F**", "Fss", "Finch Twice Removed", 5, "a b e d c"),
    ("G", "G", "Goldfinch", 4, "a d (b c)"),
    ("H", "H", "Hummingbird", 3, "a b c b"),
    ("I", "I", "Identity (Idiot)", 1, "a"),
    ("I*", "Is", "Identity Once Removed", 2, "a b"),
    ("I**", "Iss", "Identity Twice Removed", 3, "a b c"),
    ("J", "J", "Jay", 4, "a b (a d c)"),
    ("K", "K", "Kestrel", 2, "a"),
    ("Ki", "Ki", "Kite", 2, "b"),
    ("KM", "KM", "Konstant Mocker", 2, "b b"),
    ("KM'", "KMp", "Crossed Konstant Mocker", 2, "a a"),
    ("L", "L", "Lark", 2, "a (b b)"),
    ("M", "M", "Mockingbird", 1, "a a"),
    ("M2", "M2", "Double Mockingbird", 2, "a b (a b)"),
    ("O", "O", "Owl", 2, "b (a b)"),
    ("Φ", "Phi", "Phoenix", 4, "a (b d) (c d)"),
    ("Ψ", "Psi", "Psi Bird", 4, "a (b c) (b d)"),
    ("Q", "Q", "Queer Bird", 3, "b (a c)"),
    ("Q1", "Q1", "Quixotic Bird", 3, "a (c b)"),
    ("Q2", "Q2", "Quizzical Bird", 3, "b (c a)"),
    ("Q3", "Q3", "Quirky Bird", 3, "c (a b)"),
    ("Q4", "Q4", "Quacky Bird", 3, "c (b a)"),
    ("R", "R", "Robin", 3, "b c a"),
    ("R*", "Rs", "Robin Once Removed", 4, "a c d b"),
    ("R**", "Rss", "Robin Twice Removed", 5, "a b d e c"),
    ("S", "S", "Starling", 3, "a c (b c)"),
    ("T", "T", "Thrush", 2, "b a"),
    ("U", "U", "Turing Bird", 2, "b (a a b)"),
    ("V", "V", "Vireo", 3, "c a b"),
    ("V*", "Vs", "Vireo Once Removed", 4, "a d b c"),
    ("V**", "Vss", "Vireo Twice Removed", 5, "a b e c d"),
    ("W", "W", "Warbler", 2, "a b b"),
    ("W*", "Ws", "Warbler Once Removed", 3, "a b c c"),
    ("W**", "Wss", "Warbler Twice Removed", 4, "a b c d d"),
    ("W'", "Wp", "Converse Warbler", 2, "b a a"),
    ("Y", "Y", "Sage Bird", 1, "a (Y a)"),
)

FORMALS = "abcdefg"


def parse_rule(src):
    """The rule as a tree: a formal or bird name (str), or a pair (function, argument)."""
    tokens = src.replace("(", " ( ").replace(")", " ) ").split()
    pos = 0

    def expr():
        nonlocal pos
        t = None
        while pos < len(tokens) and tokens[pos] != ")":
            if tokens[pos] == "(":
                pos += 1
                a = expr()
                pos += 1
            else:
                a = tokens[pos]
                pos += 1
            t = a if t is None else (t, a)
        return t

    return expr()
