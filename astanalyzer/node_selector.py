"""
Utilities for resolving user-facing node selectors into astroid node classes.

Selectors are used by the matcher DSL to describe which AST node types should
be accepted. Supported selector forms may include concrete node names such as
``"If"``, unions such as ``"If|For"``, and optionally higher-level abstractions
depending on project configuration.
"""

import logging
from typing import Set, Type, Union

from astroid import nodes

from .kinds import Domain, K

log = logging.getLogger(__name__)

NodeCls = Type[nodes.NodeNG]
NodeSelectorInput = Union[str, "NodeType", Domain, NodeCls]

DOMAIN_SELECTORS = {
    "loop": K.loop,
    "assignment": K.assignment,
    "scope": K.scope,
    "import": K.import_,
    "terminator": K.terminator,
    "expr": K.expr,
    "collection": K.collection,
    "comprehension": K.comprehension,
    "control_flow": K.control_flow,
    "pattern": K.pattern,
}

def resolve_node_selector(sel: NodeSelectorInput) -> Set[NodeCls]:
    """
    Resolve a matcher node selector into a set of astroid node classes.

    Supported selector forms include:

    - domain selectors such as `K.loop`
    - direct astroid node classes such as `nodes.For`
    - `NodeType` enum values
    - string node names such as `"If"`
    - union strings such as `"If|For|While"`
    - domain member strings such as `"loop:for_"`
    - whole-domain strings such as `"loop"`

    Args:
        sel (NodeSelectorInput): User-facing selector to resolve.

    Returns:
        Set[NodeCls]: Set of matching astroid node classes.

    Raises:
        ValueError: If the selector string or domain member is unknown.
        TypeError: If the selector type is unsupported.
    """
    # 1) Domain (K.loop, K.assignment, ...)
    if isinstance(sel, Domain):
        return set(sel.resolve())

    # 2) astroid class (nodes.For)
    if isinstance(sel, type) and issubclass(sel, nodes.NodeNG):
        return {sel}

    # 3) NodeType enum (NodeType.FOR -> "For") – duck-typing, ať nevzniknou cykly
    if hasattr(sel, "value") and sel.__class__.__name__ == "NodeType":
        name = str(sel.value)
        cls = getattr(nodes, name, None)
        if cls is None:
            raise ValueError(f"Unknown astroid node for NodeType: {name}")
        return {cls}

    # 4) string selectors
    if isinstance(sel, str):
        s = sel.strip()

        # 4.0) Union syntax: "If|For|While|Try"
        if "|" in s:
            parts = [p.strip() for p in s.split("|") if p.strip()]
            if not parts:
                raise ValueError(f"Empty union selector: {s!r}")
            out: Set[NodeCls] = set()
            for part in parts:
                out |= resolve_node_selector(part)  # rekurze
            return out

        # 4.1) Domain member syntax: "loop:for_"
        if ":" in s:
            dom, member = s.split(":", 1)
            dom = dom.strip()
            member = member.strip()
            d = DOMAIN_SELECTORS.get(dom)
            if d is None:
                log.debug("Unknown domain selector: %r", dom)
                raise ValueError(f"Unknown domain in selector: {dom!r}")

            try:
                cls = getattr(d, member)
            except AttributeError:
                log.debug("Unknown member %r in domain %r", member, dom)
                raise ValueError(f"Unknown member {member!r} in domain {dom!r}")
            return {cls}

        # 4.2) Domain whole syntax: "loop" -> K.loop (volitelné, ale fajn pro kompatibilitu)
        if s in DOMAIN_SELECTORS:
            return set(DOMAIN_SELECTORS[s].resolve())

        # 4.3) Concrete class name: "If", "For", "FunctionDef", ...
        cls = getattr(nodes, s, None)
        if cls is None or not isinstance(cls, type) or not issubclass(cls, nodes.NodeNG):
            log.debug("Unknown node selector string: %r", s)
            raise ValueError(f"Unknown node type string: {s}")
        return {cls}

    log.debug("Unsupported selector type: %r", type(sel))
    raise TypeError(f"Unsupported selector type: {type(sel)!r}")
