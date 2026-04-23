import pytest

from astanalyzer.rule_filtering import (
    RuleFilterError,
    build_rule_selection,
    filter_rules,
    parse_csv_arg,
)


class RuleA:
    id = "STYLE-002"
    category = "STYLE"


class RuleB:
    id = "STYLE-003"
    category = "STYLE"


class RuleC:
    id = "SEC-031"
    category = "SECURITY"


ALL_RULES = [RuleA, RuleB, RuleC]


def test_parse_csv_arg_splits_and_strips_values():
    assert parse_csv_arg("STYLE-002, STYLE-003 ,SEC-031") == {
        "STYLE-002",
        "STYLE-003",
        "SEC-031",
    }


def test_filter_rules_returns_all_rules_when_no_filters_are_used():
    selection = build_rule_selection()
    result = filter_rules(ALL_RULES, selection)
    assert result == ALL_RULES


def test_filter_rules_only_ids():
    selection = build_rule_selection(only="STYLE-002,SEC-031")
    result = filter_rules(ALL_RULES, selection)
    assert result == [RuleA, RuleC]


def test_filter_rules_exclude_ids():
    selection = build_rule_selection(exclude="STYLE-003")
    result = filter_rules(ALL_RULES, selection)
    assert result == [RuleA, RuleC]


def test_filter_rules_only_category():
    selection = build_rule_selection(only_category="STYLE")
    result = filter_rules(ALL_RULES, selection)
    assert result == [RuleA, RuleB]


def test_filter_rules_exclude_category():
    selection = build_rule_selection(exclude_category="SECURITY")
    result = filter_rules(ALL_RULES, selection)
    assert result == [RuleA, RuleB]


def test_filter_rules_combines_only_and_exclude():
    selection = build_rule_selection(
        only="STYLE-002,STYLE-003",
        exclude="STYLE-003",
    )
    result = filter_rules(ALL_RULES, selection)
    assert result == [RuleA]


def test_filter_rules_combines_rule_and_category_filters():
    selection = build_rule_selection(
        only="STYLE-002,SEC-031",
        exclude_category="SECURITY",
    )
    result = filter_rules(ALL_RULES, selection)
    assert result == [RuleA]


def test_filter_rules_include_adds_rule_back_after_category_exclusion():
    selection = build_rule_selection(
        exclude_category="STYLE",
        include="STYLE-002",
    )
    result = filter_rules(ALL_RULES, selection)
    assert result == [RuleC, RuleA]


def test_filter_rules_include_adds_rule_back_after_direct_exclusion():
    selection = build_rule_selection(
        exclude="STYLE-002",
        include="STYLE-002",
    )
    result = filter_rules(ALL_RULES, selection)
    assert result == [RuleB, RuleC, RuleA]


def test_filter_rules_include_does_not_duplicate_existing_rule():
    selection = build_rule_selection(include="STYLE-002")
    result = filter_rules(ALL_RULES, selection)
    assert result == ALL_RULES


def test_filter_rules_include_can_restore_multiple_rules():
    selection = build_rule_selection(
        exclude_category="STYLE",
        include="STYLE-002,STYLE-003",
    )
    result = filter_rules(ALL_RULES, selection)
    assert result == [RuleC, RuleA, RuleB]


def test_filter_rules_only_then_include_keeps_only_result_when_rule_already_present():
    selection = build_rule_selection(
        only="STYLE-002",
        include="STYLE-002",
    )
    result = filter_rules(ALL_RULES, selection)
    assert result == [RuleA]


def test_filter_rules_only_then_exclude_category_can_end_empty():
    selection = build_rule_selection(
        only="STYLE-002",
        exclude_category="STYLE",
    )
    with pytest.raises(RuleFilterError, match="No rules selected for scan"):
        filter_rules(ALL_RULES, selection)


def test_filter_rules_fails_on_unknown_only_rule():
    selection = build_rule_selection(only="STYLE-999")
    with pytest.raises(RuleFilterError, match="Unknown rule IDs in --only"):
        filter_rules(ALL_RULES, selection)


def test_filter_rules_fails_on_unknown_exclude_rule():
    selection = build_rule_selection(exclude="SEC-999")
    with pytest.raises(RuleFilterError, match="Unknown rule IDs in --exclude"):
        filter_rules(ALL_RULES, selection)


def test_filter_rules_fails_on_unknown_include_rule():
    selection = build_rule_selection(include="STYLE-999")
    with pytest.raises(RuleFilterError, match="Unknown rule IDs in --include"):
        filter_rules(ALL_RULES, selection)


def test_filter_rules_fails_on_unknown_category():
    selection = build_rule_selection(only_category="FOO")
    with pytest.raises(RuleFilterError, match="Unknown categories in --only-category"):
        filter_rules(ALL_RULES, selection)


def test_filter_rules_fails_when_selection_is_empty_after_filters():
    selection = build_rule_selection(only="STYLE-002", exclude="STYLE-002")
    with pytest.raises(RuleFilterError, match="No rules selected for scan"):
        filter_rules(ALL_RULES, selection)
