#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

import pytest
from pydantic import TypeAdapter, ValidationError

from cmk.ccc.site import SiteId
from cmk.gui.monitor.services._api._filters import (
    parse_as_livestatus_filter,
    scope_filter_by_site,
    ServiceAndNode,
    ServiceBooleanCondition,
    ServiceFilterNode,
    ServiceHostNode,
    ServiceHostStateChoiceCondition,
    ServiceLabelChoiceCondition,
    ServiceNameChoiceCondition,
    ServiceNotNode,
    ServiceOrNode,
    ServiceSiteChoiceCondition,
    ServiceStateChoiceCondition,
    ServiceStringCondition,
    ServiceStringOp,
    ServiceTimestampCondition,
    ServiceTimestampOp,
)
from cmk.gui.monitor.shared import (
    BooleanCondition,
    FolderCondition,
    LabelChoiceCondition,
    NameChoiceCondition,
    NotNode,
    SiteChoiceCondition,
    StateChoiceCondition,
)
from cmk.gui.monitor.shared import FilterNode as HostFilterNode
from tests.testlib.unit.gui.web_test_app import SetConfig


@pytest.mark.parametrize(
    "op, ls_op",
    [
        ("contains", "~~"),
        ("matches", "~"),
    ],
)
def test_query_builder_string_condition(op: ServiceStringOp, ls_op: str) -> None:
    condition = ServiceStringCondition(type="condition", field="name", op=op, value="CPU")
    assert parse_as_livestatus_filter(condition) == f"Filter: description {ls_op} CPU"


@pytest.mark.parametrize(
    "public, private",
    [
        ("name", "description"),
        ("summary", "plugin_output"),
    ],
)
def test_query_builder_string_fields_are_properly_overriden(
    public: Literal["name", "summary"],
    private: str,
) -> None:
    condition = ServiceStringCondition(type="condition", field=public, op="contains", value="CPU")
    assert parse_as_livestatus_filter(condition) == f"Filter: {private} ~~ CPU"


@pytest.mark.parametrize(
    "field",
    ["acknowledged", "notifications_enabled", "is_flapping"],
)
@pytest.mark.parametrize(
    "value, ls_value",
    [
        (True, 1),
        (False, 0),
    ],
)
def test_query_builder_boolean_condition_fields(
    field: Literal["acknowledged", "notifications_enabled", "is_flapping"],
    value: bool,
    ls_value: int,
) -> None:
    condition = ServiceBooleanCondition(type="condition", field=field, op="eq", value=value)
    assert parse_as_livestatus_filter(condition) == f"Filter: {field} = {ls_value}"


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, "Filter: scheduled_downtime_depth > 0"),
        (False, "Filter: scheduled_downtime_depth = 0"),
    ],
)
def test_query_builder_downtime_condition(value: bool, expected: str) -> None:
    condition = ServiceBooleanCondition(type="condition", field="in_downtime", op="eq", value=value)
    assert parse_as_livestatus_filter(condition) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(
            True,
            "Filter: modified_attributes_list >= active_checks_enabled\n"
            "Filter: active_checks_enabled = 0\n"
            "And: 2",
            id="manually disabled",
        ),
        pytest.param(
            False,
            "Filter: modified_attributes_list >= active_checks_enabled\n"
            "Filter: active_checks_enabled = 0\n"
            "And: 2\n"
            "Negate:",
            id="not manually disabled",
        ),
    ],
)
def test_query_builder_active_checks_disabled_condition(value: bool, expected: str) -> None:
    condition = ServiceBooleanCondition(
        type="condition", field="active_checks_disabled", op="eq", value=value
    )
    assert parse_as_livestatus_filter(condition) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(
            True,
            "Filter: modified_attributes_list >= passive_checks_enabled\n"
            "Filter: accept_passive_checks = 0\n"
            "And: 2",
            id="manually disabled",
        ),
        pytest.param(
            False,
            "Filter: modified_attributes_list >= passive_checks_enabled\n"
            "Filter: accept_passive_checks = 0\n"
            "And: 2\n"
            "Negate:",
            id="not manually disabled",
        ),
    ],
)
def test_query_builder_passive_checks_disabled_condition(value: bool, expected: str) -> None:
    condition = ServiceBooleanCondition(
        type="condition", field="passive_checks_disabled", op="eq", value=value
    )
    assert parse_as_livestatus_filter(condition) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(
            True,
            "Filter: in_check_period = 1\nFilter: in_passive_check_period = 1\nAnd: 2",
            id="inside both check periods",
        ),
        pytest.param(
            False,
            "Filter: in_check_period = 1\nFilter: in_passive_check_period = 1\nAnd: 2\nNegate:",
            id="outside at least one check period",
        ),
    ],
)
def test_query_builder_in_check_period_condition(value: bool, expected: str) -> None:
    condition = ServiceBooleanCondition(
        type="condition", field="in_check_period", op="eq", value=value
    )
    assert parse_as_livestatus_filter(condition) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(
            True,
            "Filter: state = 3\n"
            "Filter: plugin_output ~ check failed - please submit a crash report!\n"
            "And: 2",
            id="crashed",
        ),
        pytest.param(
            False,
            "Filter: state = 3\n"
            "Filter: plugin_output ~ check failed - please submit a crash report!\n"
            "And: 2\n"
            "Negate:",
            id="did not crash",
        ),
    ],
)
def test_query_builder_check_crashed_condition(value: bool, expected: str) -> None:
    condition = ServiceBooleanCondition(
        type="condition", field="check_crashed", op="eq", value=value
    )
    assert parse_as_livestatus_filter(condition) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, "Filter: comments !="),
        (False, "Filter: comments ="),
    ],
)
def test_query_builder_has_comments_condition(value: bool, expected: str) -> None:
    condition = ServiceBooleanCondition(
        type="condition", field="has_comments", op="eq", value=value
    )
    assert parse_as_livestatus_filter(condition) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, "Filter: staleness >= 3.5"),
        (False, "Filter: staleness < 3.5"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_query_builder_stale_condition(value: bool, expected: str, set_config: SetConfig) -> None:
    condition = ServiceBooleanCondition(type="condition", field="stale", op="eq", value=value)
    with set_config(staleness_threshold=3.5):
        assert parse_as_livestatus_filter(condition) == expected


def test_query_builder_state_choice_single_no_or() -> None:
    condition = ServiceStateChoiceCondition(
        type="condition", field="state", op="one_of", value=["WARN"]
    )
    value = parse_as_livestatus_filter(condition)
    expected = "\n".join(  # noqa: FLY002
        [
            "Filter: state = 1",
            "Filter: has_been_checked = 1",
            "And: 2",
        ]
    )

    assert value == expected


def test_query_builder_state_choice_multiple_with_or() -> None:
    condition = ServiceStateChoiceCondition(
        type="condition",
        field="state",
        op="one_of",
        value=["WARN", "CRIT"],
    )

    value = parse_as_livestatus_filter(condition)
    expected = "\n".join(  # noqa: FLY002
        [
            "Filter: state = 1",
            "Filter: has_been_checked = 1",
            "And: 2",
            "Filter: state = 2",
            "Filter: has_been_checked = 1",
            "And: 2",
            "Or: 2",
        ]
    )

    assert value == expected


def test_query_builder_state_choice_pending_matches_has_been_checked_only() -> None:
    """A pending service's raw ``state`` column is meaningless, so 'PENDING' is not translated
    into a ``state = X`` filter at all - only into ``has_been_checked``."""
    condition = ServiceStateChoiceCondition(
        type="condition", field="state", op="one_of", value=["PENDING"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: has_been_checked = 0"


@pytest.mark.parametrize(
    "states, expected",
    [
        pytest.param(
            ["DOWN"],
            "Filter: host_state = 1\nFilter: host_has_been_checked = 1\nAnd: 2",
            id="a checked host in that state",
        ),
        pytest.param(
            ["PENDING"],
            "Filter: host_has_been_checked = 0",
            id="pending host by its missing check, not by its state",
        ),
        pytest.param(
            ["UP", "PENDING"],
            "Filter: host_state = 0\nFilter: host_has_been_checked = 1\nAnd: 2\n"
            "Filter: host_has_been_checked = 0\nOr: 2",
            id="any of several host states",
        ),
    ],
)
def test_query_builder_host_state_choice(
    states: list[Literal["UP", "DOWN", "UNREACHABLE", "PENDING"]], expected: str
) -> None:
    condition = ServiceHostStateChoiceCondition(
        type="condition", field="host_state", op="one_of", value=states
    )

    assert parse_as_livestatus_filter(condition) == expected


def test_query_builder_state_choice_mixes_pending_and_real_states() -> None:
    condition = ServiceStateChoiceCondition(
        type="condition", field="state", op="one_of", value=["OK", "PENDING"]
    )

    value = parse_as_livestatus_filter(condition)
    expected = "\n".join(  # noqa: FLY002
        [
            "Filter: state = 0",
            "Filter: has_been_checked = 1",
            "And: 2",
            "Filter: has_been_checked = 0",
            "Or: 2",
        ]
    )

    assert value == expected


def test_query_builder_label_choice_single_no_and() -> None:
    condition = ServiceLabelChoiceCondition(
        type="condition", field="labels", op="all_of", value=["cmk/os_family:linux"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: labels = 'cmk/os_family' 'linux'"


def test_query_builder_label_choice_multiple_with_and() -> None:
    condition = ServiceLabelChoiceCondition(
        type="condition",
        field="tags",
        op="all_of",
        value=["criticality:prod", "networking:core"],
    )

    expected = "\n".join(  # noqa: FLY002
        [
            "Filter: tags = 'criticality' 'prod'",
            "Filter: tags = 'networking' 'core'",
            "And: 2",
        ]
    )

    assert parse_as_livestatus_filter(condition) == expected


def test_label_choice_condition_rejects_a_newline() -> None:
    payload = {
        "type": "condition",
        "field": "labels",
        "op": "all_of",
        "value": ["key:va\nlue"],
    }

    with pytest.raises(ValidationError):
        TypeAdapter(ServiceFilterNode).validate_python(  # astrein: disable=pydantic-type-adapter
            payload, strict=False
        )


def test_query_builder_label_choice_splits_on_the_first_colon_only() -> None:
    condition = ServiceLabelChoiceCondition(
        type="condition", field="labels", op="all_of", value=["url:https://example.com"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: labels = 'url' 'https://example.com'"


def test_query_builder_label_choice_value_prefix_matches_by_regex() -> None:
    condition = ServiceLabelChoiceCondition(
        type="condition", field="labels", op="all_of", value=["cmk/os_family:lin*"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: labels ~ 'cmk/os_family' '^lin'"


def test_query_builder_label_choice_key_prefix_matches_the_names_column() -> None:
    condition = ServiceLabelChoiceCondition(
        type="condition", field="labels", op="all_of", value=["cmk/os*"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: label_names ~ ^cmk/os"


def test_query_builder_tag_key_prefix_matches_its_own_names_column() -> None:
    condition = ServiceLabelChoiceCondition(
        type="condition", field="tags", op="all_of", value=["crit*"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: tag_names ~ ^crit"


def test_query_builder_label_choice_prefix_is_a_literal_not_a_pattern() -> None:
    condition = ServiceLabelChoiceCondition(
        type="condition", field="labels", op="all_of", value=["cmk/os_family:a.b*"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: labels ~ 'cmk/os_family' '^a\\.b'"


def test_query_builder_name_choice_single_no_or() -> None:
    condition = ServiceNameChoiceCondition(
        type="condition", field="contact_groups", op="one_of", value=["all"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: contact_groups >= all"


def test_query_builder_name_choice_multiple_with_or() -> None:
    condition = ServiceNameChoiceCondition(
        type="condition", field="contacts", op="one_of", value=["alice", "bob"]
    )

    expected = "\n".join(  # noqa: FLY002
        [
            "Filter: contacts >= alice",
            "Filter: contacts >= bob",
            "Or: 2",
        ]
    )

    assert parse_as_livestatus_filter(condition) == expected


def test_query_builder_name_choice_prefix_matches_by_regex() -> None:
    condition = ServiceNameChoiceCondition(
        type="condition", field="contact_groups", op="one_of", value=["ops*"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: contact_groups ~ ^ops"


def test_query_builder_name_choice_matches_service_groups() -> None:
    condition = ServiceNameChoiceCondition(
        type="condition", field="groups", op="one_of", value=["databases"]
    )

    assert parse_as_livestatus_filter(condition) == "Filter: groups >= databases"


def test_query_builder_nested_conditions() -> None:
    nodes = ServiceAndNode(
        type="and",
        children=[
            ServiceStateChoiceCondition(
                type="condition", field="state", op="one_of", value=["WARN"]
            ),
            ServiceNotNode(
                type="not",
                child=ServiceOrNode(
                    type="or",
                    children=[
                        ServiceStateChoiceCondition(
                            type="condition", field="state", op="one_of", value=["OK"]
                        ),
                        ServiceStateChoiceCondition(
                            type="condition", field="state", op="one_of", value=["UNKNOWN"]
                        ),
                    ],
                ),
            ),
        ],
    )

    value = parse_as_livestatus_filter(nodes)
    expected = "\n".join(  # noqa: FLY002
        [
            "Filter: state = 1",
            "Filter: has_been_checked = 1",
            "And: 2",
            "Filter: state = 0",
            "Filter: has_been_checked = 1",
            "And: 2",
            "Filter: state = 3",
            "Filter: has_been_checked = 1",
            "And: 2",
            "Or: 2",
            "Negate:",
            "And: 2",
        ]
    )

    assert value == expected


def test_query_builder_mixed_string_and_state_conditions() -> None:
    nodes = ServiceAndNode(
        type="and",
        children=[
            ServiceStringCondition(type="condition", field="name", op="contains", value="CPU"),
            ServiceStateChoiceCondition(
                type="condition", field="state", op="one_of", value=["WARN"]
            ),
        ],
    )

    value = parse_as_livestatus_filter(nodes)
    expected = "\n".join(  # noqa: FLY002
        [
            "Filter: description ~~ CPU",
            "Filter: state = 1",
            "Filter: has_been_checked = 1",
            "And: 2",
            "And: 2",
        ]
    )

    assert value == expected


def test_query_builder_combines_multiple_boolean_conditions() -> None:
    nodes = ServiceAndNode(
        type="and",
        children=[
            ServiceBooleanCondition(type="condition", field="acknowledged", op="eq", value=False),
            ServiceBooleanCondition(type="condition", field="in_downtime", op="eq", value=False),
        ],
    )

    value = parse_as_livestatus_filter(nodes)
    expected = "Filter: acknowledged = 0\nFilter: scheduled_downtime_depth = 0\nAnd: 2"

    assert value == expected


@pytest.mark.parametrize(
    "op, ls_op",
    [
        ("lt", "<"),
        ("lte", "<="),
        ("gt", ">"),
        ("gte", ">="),
    ],
)
@pytest.mark.parametrize("field", ["last_check", "last_state_change"])
def test_query_builder_timestamp_condition(
    field: Literal["last_check", "last_state_change"],
    op: ServiceTimestampOp,
    ls_op: str,
) -> None:
    condition = ServiceTimestampCondition(type="condition", field=field, op=op, value=1752405510)
    assert parse_as_livestatus_filter(condition) == f"Filter: {field} {ls_op} 1752405510"


def test_query_builder_timestamp_range() -> None:
    nodes = ServiceAndNode(
        type="and",
        children=[
            ServiceTimestampCondition(
                type="condition", field="last_check", op="gte", value=1752405510
            ),
            ServiceTimestampCondition(
                type="condition", field="last_check", op="lte", value=1752491910
            ),
        ],
    )

    value = parse_as_livestatus_filter(nodes)
    expected = "Filter: last_check >= 1752405510\nFilter: last_check <= 1752491910\nAnd: 2"

    assert value == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("1752405510", id="numeric string"),
        pytest.param(1752405510.0, id="float"),
        pytest.param("2026-07-13T11:38:30Z", id="iso timestamp"),
        pytest.param(True, id="boolean"),
    ],
)
def test_timestamp_condition_only_accepts_unix_timestamps(value: object) -> None:
    payload = {"type": "condition", "field": "last_check", "op": "gte", "value": value}

    with pytest.raises(ValidationError):
        TypeAdapter(ServiceFilterNode).validate_python(  # astrein: disable=pydantic-type-adapter
            payload, strict=False
        )


def test_query_builder_host_name_condition() -> None:
    condition = ServiceStringCondition(
        type="condition", field="host_name", op="matches", value="^web"
    )
    assert parse_as_livestatus_filter(condition) == "Filter: host_name ~ ^web"


_SITE = SiteId("NO_SITE")
_OTHER_SITE = SiteId("other")
_SITE_CONDITION = ServiceSiteChoiceCondition(
    type="condition", field="site_id", op="one_of", value=[_SITE]
)
_NAME_CONDITION = ServiceStringCondition(type="condition", field="name", op="contains", value="CPU")


def test_scope_filter_by_site_restricts_to_the_named_sites() -> None:
    scoped = scope_filter_by_site(
        ServiceAndNode(type="and", children=[_SITE_CONDITION, _NAME_CONDITION])
    )

    assert (scoped.node, scoped.site_scope(frozenset({_SITE, _OTHER_SITE}))) == (
        _NAME_CONDITION,
        [_SITE],
    )


def test_scope_filter_by_site_negated_condition_is_a_complement() -> None:
    scoped = scope_filter_by_site(ServiceNotNode(type="not", child=_SITE_CONDITION))

    assert (scoped.node, scoped.site_scope(frozenset({_SITE, _OTHER_SITE}))) == (
        None,
        [_OTHER_SITE],
    )


def test_scope_filter_by_site_leaves_a_site_free_tree_unaffected() -> None:
    scoped = scope_filter_by_site(_NAME_CONDITION)

    assert (scoped.node, scoped.sites) == (_NAME_CONDITION, None)


def test_scope_filter_by_site_rejects_a_site_condition_under_or() -> None:
    node = ServiceOrNode(type="or", children=[_SITE_CONDITION, _NAME_CONDITION])

    with pytest.raises(ValueError, match="only be combined via 'and'"):
        scope_filter_by_site(node)


def test_site_condition_accepts_a_site_that_is_not_configured() -> None:
    payload = {"type": "condition", "field": "site_id", "op": "one_of", "value": ["gone"]}

    node = TypeAdapter(ServiceFilterNode).validate_python(  # astrein: disable=pydantic-type-adapter
        payload, strict=False
    )

    assert node == ServiceSiteChoiceCondition(
        type="condition", field="site_id", op="one_of", value=[SiteId("gone")]
    )


@pytest.mark.parametrize(
    "host_node, expected",
    [
        pytest.param(
            StateChoiceCondition(type="condition", field="state", op="one_of", value=["DOWN"]),
            "Filter: host_state = 1\nFilter: host_has_been_checked = 1\nAnd: 2",
            id="host state",
        ),
        pytest.param(
            BooleanCondition(type="condition", field="in_downtime", op="eq", value=True),
            "Filter: host_scheduled_downtime_depth > 0",
            id="host in downtime",
        ),
        pytest.param(
            BooleanCondition(type="condition", field="active_checks_disabled", op="eq", value=True),
            "Filter: host_modified_attributes_list >= active_checks_enabled\n"
            "Filter: host_active_checks_enabled = 0\nAnd: 2",
            id="host active checks disabled",
        ),
        pytest.param(
            LabelChoiceCondition(
                type="condition", field="labels", op="all_of", value=["env:prod", "os*"]
            ),
            "Filter: host_labels = 'env' 'prod'\nFilter: host_label_names ~ ^os\nAnd: 2",
            id="host labels",
        ),
        pytest.param(
            NameChoiceCondition(type="condition", field="groups", op="one_of", value=["linux"]),
            "Filter: host_groups >= linux",
            id="host groups",
        ),
        pytest.param(
            NotNode(
                type="not",
                child=BooleanCondition(type="condition", field="acknowledged", op="eq", value=True),
            ),
            "Filter: host_acknowledged = 1\nNegate:",
            id="negated host condition",
        ),
    ],
)
def test_query_builder_host_node_filters_the_host_columns(
    host_node: HostFilterNode, expected: str
) -> None:
    condition = ServiceHostNode(type="host", child=host_node)
    assert parse_as_livestatus_filter(condition) == expected


@pytest.mark.usefixtures("request_context")
def test_query_builder_host_node_stale_uses_the_host_staleness(set_config: SetConfig) -> None:
    condition = ServiceHostNode(
        type="host",
        child=BooleanCondition(type="condition", field="stale", op="eq", value=True),
    )
    with set_config(staleness_threshold=3.5):
        assert parse_as_livestatus_filter(condition) == "Filter: host_staleness >= 3.5"


@pytest.mark.parametrize(
    "host_node",
    [
        pytest.param(
            SiteChoiceCondition(
                type="condition", field="site_id", op="one_of", value=[SiteId("local")]
            ),
            id="site",
        ),
        pytest.param(
            NotNode(
                type="not",
                child=FolderCondition(
                    type="condition", field="folder", op="contains", value="Munich"
                ),
            ),
            id="folder inside not",
        ),
    ],
)
def test_host_node_rejects_conditions_beyond_the_host_columns(host_node: object) -> None:
    with pytest.raises(ValidationError):
        TypeAdapter(ServiceFilterNode).validate_python(  # astrein: disable=pydantic-type-adapter
            {"type": "host", "child": host_node}
        )
