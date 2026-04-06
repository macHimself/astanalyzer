"""
Rule definition and registration system for AstroDSL.

This module defines:
  - RuleMeta: metaclass that automatically instantiates and registers Rule subclasses
    into `Rule.registry`.
  - Rule: base class for all rules. A rule defines one or more matchers and may
    provide fix builders and/or fix plans.
  - A small custom-fixer registry integration (via register_custom).

Two matching modes exist:
  1) tree-based mode: `Rule.find_matches(tree)` — returns all matching nodes in a module AST
  2) one-pass mode: `Rule.match_node(node, ctx=...)` — evaluates only the current node,
     intended for fast streaming scans over `(module, node)`.

Important invariants enforced by RuleMeta:
  - Every concrete Rule subclass must define at least one matcher (`matcher` or `matchers`)
  - `id`, `category`, `severity` are defaulted if not provided

Notes:
  - The bottom section contains temporary test rules used during development.
    These should be removed or moved into a dedicated test module.
"""

from __future__ import annotations

import logging
from typing import Any

from .enums import Severity, RuleCategory, NodeType 
from .matcher import MatchResult

log = logging.getLogger(__name__)

class RuleMeta(type):
    """Metaclass for Rule subclasses with auto-registration.

    Any concrete subclass of `Rule` is instantiated at class creation time and
    appended to `Rule.registry`.

    Validation performed for every registered rule:
      - the rule must define either `matcher` or `matchers`
      - at least one matcher must support `.find_matches(...)` (or be matcher-like)
      - missing metadata is defaulted:
          id -> class name
          category -> "uncategorized"
          severity -> "info"

    Raises:
        ValueError: If a rule defines no matchers, or matchers are not matcher-like.

    Notes:
        The base class `Rule` itself is not instantiated/registered.
    """

    id = None
    category = "uncategorized"
    severity = "info"
    node_type = []

    def __new__(mcls, name: str, bases: tuple[type, ...], ns: dict[str, Any]):
        cls = super().__new__(mcls, name, bases, ns)

        if name == "Rule":
            return cls

        # --- severity ---
        sev = getattr(cls, "severity", None)
        if sev is not None and not isinstance(sev, Severity):
            raise TypeError(f"{name}.severity must be Severity, got {type(sev).__name__}: {sev!r}")

        # --- category ---
        cat = getattr(cls, "category", None)
        if cat is not None and not isinstance(cat, RuleCategory):
            raise TypeError(f"{name}.category must be RuleCategory, got {type(cat).__name__}: {cat!r}")

        # --- node_type ---
        nt = getattr(cls, "node_type", None)
        if nt is not None:
            if isinstance(nt, NodeType):
                nt = {nt}
                setattr(cls, "node_type", nt)

            if not isinstance(nt, set) or not all(isinstance(x, NodeType) for x in nt):
                raise TypeError(f"{name}.node_type must be NodeType or set[NodeType], got: {nt!r}")

        return cls

    def __init__(cls, name, bases, dct):
        if not hasattr(cls, 'registry'):
            cls.registry = []
        else:
            instance = cls()

            single = getattr(instance, "matcher", None)
            multi = getattr(instance, "matchers", [])

            has_single = single is not None and hasattr(single, "find_matches")
            has_multi = bool(multi) and any(hasattr(m, "find_matches") for m in multi)

            if not getattr(instance, 'matcher', None) and not getattr(instance, 'matchers', []):
                raise ValueError(f"Rule '{name}' must define at least one matcher or group of matchers.")
            
            if not (has_single or has_multi):
                raise ValueError(
                    f"Rule '{name}' must define at least one matcher "
                    f"(got matcher={type(single).__name__ if single else None}, "
                    f"matchers_len={len(multi) if isinstance(multi, list) else 'n/a'})"
                )
            
            if getattr(instance, 'id', None) is None:
                instance.id = name
            if not getattr(instance, 'category', None):
                instance.category = "uncategorized"
            if not getattr(instance, 'severity', None):
                instance.severity = "info"

            cls.registry.append(instance)

        super().__init__(name, bases, dct)

class Rule(metaclass=RuleMeta):
    """Base class for all analysis rules.

    A rule describes *what to match* (via matchers) and optionally *how to fix* it
    (via fix builders and/or fix plans).

    Attributes:
        matcher: Optional single matcher instance.
        matchers: Optional list of matcher instances.
        description: Human-readable rule description (defaults to class docstring).
        fixer_plans: List of plan builders (data-only plans for UI).
        fixer_builders: List of fix builders (materialised fixes/patches).

    Matching APIs:
        - find_matches(tree): find all matching nodes within a module AST
        - match_node(node, ctx): one-pass evaluation for a single node during streaming scan
    """
    def __init__(self):
        self.matcher = None
        self.matchers = []
        self.description = self.__doc__ or "No description"
        self.fixer_plans = []
        self.fixer_builders = []
        self.plan_builders = []

    def find_matches(self, tree):
        """Return all matches of this rule within a module AST tree.

        Args:
            tree: Root node of a module AST (astroid).

        Returns:
            List of matching nodes across `self.matcher` and all `self.matchers`.

        Notes:
            This is the slower, tree-based scan mode. The one-pass engine prefers
            `match_node(node, ctx)` for streaming over nodes.
        """
        matches = []
        if self.matcher:
            matches.extend(self.matcher.find_matches(tree))
        for m in self.matchers:
            matches.extend(m.find_matches(tree))
        return matches
    
    def _stable_ref_value(self, value):
        if value is None:
            return None

        if hasattr(value, "__class__"):
            return (
                value.__class__.__name__,
                getattr(value, "lineno", None),
                getattr(value, "col_offset", None),
                getattr(value, "end_lineno", None),
                getattr(value, "end_col_offset", None),
            )

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, (list, tuple)):
            return tuple(self._stable_ref_value(v) for v in value)

        if isinstance(value, dict):
            return tuple(sorted((k, self._stable_ref_value(v)) for k, v in value.items()))

        return repr(value)
    

    def match_node(self, node, ctx=None):
        """One-pass matching for the current node.

        Returns:
            list[MatchResult]
        """
        hits: list[MatchResult] = []

        single = getattr(self, "matcher", None)
        multi = getattr(self, "matchers", []) or []

        def eval_matcher(m) -> MatchResult | None:
            if m is None:
                return None

            if hasattr(m, "match_result"):
                return m.match_result(node, ctx)

            if hasattr(m, "matches_node"):
                ok = bool(m.matches_node(node, ctx))
                return MatchResult(node=node, refs={}) if ok else None

            if hasattr(m, "evaluate"):
                ok = bool(m.evaluate(node, ctx) if ctx is not None else m.evaluate(node))
                return MatchResult(node=node, refs={}) if ok else None

            if hasattr(m, "find_matches"):
                ok = node in m.find_matches(node.root())
                return MatchResult(node=node, refs={}) if ok else None

            return None

        if single is not None:
            result = eval_matcher(single)
            if result is not None:
                hits.append(result)

        for m in multi:
            result = eval_matcher(m)
            if result is not None:
                hits.append(result)

        unique_hits: list[MatchResult] = []
        seen = set()

        for hit in hits:
            match_obj = hit.node

            refs_items = tuple(
                sorted(
                    (k, self._stable_ref_value(v))
                    for k, v in (hit.refs or {}).items()
                )
            )

            key = (
                match_obj.__class__.__name__,
                getattr(match_obj, "lineno", None),
                getattr(match_obj, "col_offset", None),
                getattr(match_obj, "end_lineno", None),
                getattr(match_obj, "end_col_offset", None),
                refs_items,
            )

            if key in seen:
                log.debug(
                    "[DEDUP MATCH] rule=%s node=%s line=%s end_line=%s col=%s refs=%s",
                    getattr(self, "id", self.__class__.__name__),
                    match_obj.__class__.__name__,
                    getattr(match_obj, "lineno", None),
                    getattr(match_obj, "end_lineno", None),
                    getattr(match_obj, "col_offset", None),
                    sorted((hit.refs or {}).keys()),
                )
                continue

            seen.add(key)
            unique_hits.append(hit)

        return unique_hits
