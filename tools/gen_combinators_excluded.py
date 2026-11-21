"""Birds left out of skivine/combinators.vi, and why.

Y: its rule, Y a -> a (Y a), unfolds without end when every redex is reduced, as
the IVM does; and at Vine cf0c325 the optimizer emits a malformed net for it (an
`ivm:graft` node with a child), which the IVM rejects.
"""

EXCLUDED = {"Y"}
