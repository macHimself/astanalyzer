from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Type


class RuleFilterError(ValueError):
    """Raised when rule selection arguments are invalid."""


@dataclass(frozen=True)
class RuleSelection:
    only_ids: frozenset[str]
    exclude_ids: frozenset[str]
    only_categories: frozenset[str]
    exclude_categories: frozenset[str]
    include_ids: frozenset[str]


def parse_csv_arg(raw: str | None) -> set[str]:
    """
    Parse a comma-separated CLI argument into a normalized set of values.

    Empty items are ignored. Values are stripped of surrounding whitespace.
    """
    if raw is None:
        return set()

    items = {item.strip() for item in raw.split(",")}
    return {item for item in items if item}


def normalize_category(value: str) -> str:
    """Normalize category names to uppercase for stable matching."""
    return value.strip().upper()


def build_rule_selection(
    only: str | None = None,
    exclude: str | None = None,
    only_category: str | None = None,
    exclude_category: str | None = None,
    include: str | None = None,
) -> RuleSelection:
    """
    Build a normalized rule selection object from CLI arguments.
    """
    return RuleSelection(
        only_ids=frozenset(parse_csv_arg(only)),
        exclude_ids=frozenset(parse_csv_arg(exclude)),
        only_categories=frozenset(
            normalize_category(x) for x in parse_csv_arg(only_category)
        ),
        exclude_categories=frozenset(
            normalize_category(x) for x in parse_csv_arg(exclude_category)
        ),
        include_ids=frozenset(parse_csv_arg(include)),
    )


def _rule_id(rule: Type) -> str:
    rule_id = getattr(rule, "id", None)
    if not rule_id:
        raise RuleFilterError(f"Rule {rule!r} has no 'id' attribute.")
    return str(rule_id)


def _rule_category(rule: Type) -> str:
    category = getattr(rule, "category", "")
    return normalize_category(str(category))


def validate_rule_selection(
    rules: Sequence[Type],
    selection: RuleSelection,
) -> None:
    """
    Validate that all requested rule IDs and categories exist.
    """
    available_ids = {_rule_id(rule) for rule in rules}
    available_categories = {_rule_category(rule) for rule in rules}

    unknown_only = selection.only_ids - available_ids
    unknown_exclude = selection.exclude_ids - available_ids
    unknown_include = selection.include_ids - available_ids
    unknown_only_categories = selection.only_categories - available_categories
    unknown_exclude_categories = selection.exclude_categories - available_categories

    errors: list[str] = []

    if unknown_only:
        errors.append(
            f"Unknown rule IDs in --only: {', '.join(sorted(unknown_only))}"
        )
    if unknown_exclude:
        errors.append(
            f"Unknown rule IDs in --exclude: {', '.join(sorted(unknown_exclude))}"
        )
    if unknown_include:
        errors.append(
            f"Unknown rule IDs in --include: {', '.join(sorted(unknown_include))}"
        )
    if unknown_only_categories:
        errors.append(
            "Unknown categories in --only-category: "
            f"{', '.join(sorted(unknown_only_categories))}"
        )
    if unknown_exclude_categories:
        errors.append(
            "Unknown categories in --exclude-category: "
            f"{', '.join(sorted(unknown_exclude_categories))}"
        )

    if errors:
        raise RuleFilterError("\n".join(errors))


def filter_rules(
    rules: Sequence[Type],
    selection: RuleSelection,
) -> list[Type]:
    """
    Filter rules before scan execution.

    Order is preserved from the original input sequence.

    Filtering order:
    1. only_ids
    2. only_categories
    3. exclude_ids
    4. exclude_categories
    5. include_ids are added back
    """
    validate_rule_selection(rules, selection)

    all_rules = list(rules)
    filtered = list(rules)

    if selection.only_ids:
        filtered = [rule for rule in filtered if _rule_id(rule) in selection.only_ids]

    if selection.only_categories:
        filtered = [
            rule for rule in filtered
            if _rule_category(rule) in selection.only_categories
        ]

    if selection.exclude_ids:
        filtered = [
            rule for rule in filtered
            if _rule_id(rule) not in selection.exclude_ids
        ]

    if selection.exclude_categories:
        filtered = [
            rule for rule in filtered
            if _rule_category(rule) not in selection.exclude_categories
        ]

    if selection.include_ids:
        existing_ids = {_rule_id(rule) for rule in filtered}
        for rule in all_rules:
            rule_id = _rule_id(rule)
            if rule_id in selection.include_ids and rule_id not in existing_ids:
                filtered.append(rule)
                existing_ids.add(rule_id)

    if not filtered:
        raise RuleFilterError(
            "No rules selected for scan after applying "
            "--only/--exclude/--only-category/--exclude-category/--include."
        )

    return filtered