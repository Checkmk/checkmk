#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine
from pydantic import TypeAdapter

from cmk.gui.monitor.legacy_context import (
    ContextFilterTranslation,
    PageFilterModel,
    translate_context,
)
from cmk.gui.type_defs import FilterHTTPVariables, FilterName, VisualContext

from .testlib import ANY_PAGE, label_group_variables

type _JSON = dict[str, object]

# While the clock is set, time_machine also makes this timezone the local one of the process, whatever
# the environment of the test run is. The dates of the server are in it.
_SERVER_TIMEZONE = ZoneInfo("Europe/Berlin")
_NOW = datetime(2026, 1, 1, 12, 0, tzinfo=_SERVER_TIMEZONE)
_NOW_TS = int(_NOW.timestamp())

type _Fields = dict[FilterName, str | Mapping[str, str]]

_FIELDS: _Fields = {
    "sites": "site_id",
    "site": "site_id",
    "siteopt": "site_id",
    "host": "name",
    "hostregex": "name",
    "hostalias": "alias",
    "hostnameoralias": {"name": "name", "alias": "alias"},
    "host_address": "address",
    "address_family": "tags",
    "address_families": "tags",
    "host_auxtags": "tags",
    "host_tags": "tags",
    "host_labels": "labels",
    "host_last_check": "last_check",
    "host_last_state_change": "last_state_change",
    "kubernetes_cluster": "labels",
    "kubernetes_node": "labels",
    "opthostgroup": "groups",
    "host_ctc": "contacts",
    "host_ctc_regex": "contacts",
    "opthost_contactgroup": "contact_groups",
    "hoststate": "state",
    "hosts_having_service_problems": {
        "warn": "num_services_warn",
        "crit": "num_services_crit",
        "pending": "num_services_pending",
        "unknown": "num_services_unknown",
    },
    "host_acknowledged": "acknowledged",
    "host_num_services": "num_services",
}


_TAG_GROUPS = frozenset({"criticality", "agent"})


def _condition(field: str, op: str, value: object) -> _JSON:
    return {"type": "condition", "field": field, "op": op, "value": value}


def _not(child: _JSON) -> _JSON:
    return {"type": "not", "child": child}


def _label(label: str) -> _JSON:
    return _condition("labels", "all_of", [label])


def _tag_rows(*rows: tuple[str, str, str]) -> FilterHTTPVariables:
    """The variables the legacy form sends for the tags, a row of tag group, operator and tag each."""
    return {
        f"host_tag_{number}_{part}": text
        for number, row in enumerate(rows)
        for part, text in zip(("grp", "op", "val"), row, strict=True)
    }


def _translate(context: VisualContext) -> ContextFilterTranslation[_JSON]:
    return translate_context(context, _FIELDS, ANY_PAGE, tag_groups=_TAG_GROUPS)


@pytest.mark.parametrize(
    "name, value, expected",
    [
        pytest.param(
            "hostregex",
            {"host_regex": "web.*(01|02)"},
            _condition("name", "contains", "web.*(01|02)"),
            id="text",
        ),
        pytest.param(
            "hostregex",
            {"host_regex": "web", "neg_host_regex": "on"},
            _not(_condition("name", "contains", "web")),
            id="negated text",
        ),
        pytest.param(
            "hostregex",
            {"host_regex": "-1"},
            _condition("name", "contains", "-1"),
            id="text that reads like an ignored flag",
        ),
        pytest.param(
            "host",
            {"host": "web-01"},
            _condition("name", "matches", r"^web\-01$"),
            id="exact text",
        ),
        pytest.param(
            "hostnameoralias",
            {"hostnameoralias": "web"},
            {
                "type": "or",
                "children": [
                    _condition("name", "contains", "web"),
                    _condition("alias", "contains", "web"),
                ],
            },
            id="text in either of two fields",
        ),
        pytest.param(
            "host_address",
            {"host_address": "10.0.0.1"},
            _condition("address", "matches", r"^10\.0\.0\.1$"),
            id="exact address",
        ),
        pytest.param(
            "host_address",
            {"host_address": "10.0.", "host_address_prefix": "yes"},
            _condition("address", "matches", r"^10\.0\."),
            id="address prefix",
        ),
        pytest.param(
            "address_family",
            {"address_family": "4"},
            _condition("tags", "all_of", ["address_family:ip-v4-only"]),
            id="address family IPv4",
        ),
        pytest.param(
            "address_family",
            {"address_family": "6"},
            _condition("tags", "all_of", ["address_family:ip-v6-only"]),
            id="address family IPv6",
        ),
        pytest.param(
            "address_families",
            {"address_families": "4"},
            _condition("tags", "all_of", ["ip-v4:ip-v4"]),
            id="address families with IPv4",
        ),
        pytest.param(
            "address_families",
            {"address_families": "6"},
            _condition("tags", "all_of", ["ip-v6:ip-v6"]),
            id="address families with IPv6",
        ),
        pytest.param(
            "address_families",
            {"address_families": "both"},
            _condition("tags", "one_of", ["ip-v4:ip-v4", "ip-v6:ip-v6"]),
            id="address families with either",
        ),
        pytest.param(
            "address_families",
            {"address_families": "4_only"},
            {
                "type": "and",
                "children": [
                    _condition("tags", "all_of", ["ip-v4:ip-v4"]),
                    _not(_condition("tags", "all_of", ["ip-v6:ip-v6"])),
                ],
            },
            id="address families with IPv4 only",
        ),
        pytest.param(
            "address_families",
            {"address_families": "6_only"},
            {
                "type": "and",
                "children": [
                    _condition("tags", "all_of", ["ip-v6:ip-v6"]),
                    _not(_condition("tags", "all_of", ["ip-v4:ip-v4"])),
                ],
            },
            id="address families with IPv6 only",
        ),
        pytest.param(
            "host_auxtags",
            {"host_auxtags_0": "snmp"},
            _condition("tags", "all_of", ["snmp:snmp"]),
            id="auxiliary tag",
        ),
        pytest.param(
            "host_auxtags",
            {"host_auxtags_0": "snmp", "host_auxtags_1": "tcp", "host_auxtags_1_neg": "on"},
            {
                "type": "and",
                "children": [
                    _condition("tags", "all_of", ["snmp:snmp"]),
                    _not(_condition("tags", "all_of", ["tcp:tcp"])),
                ],
            },
            id="auxiliary tags, one negated",
        ),
        pytest.param(
            "host_auxtags",
            {"host_auxtags_0": "", "host_auxtags_1": "snmp"},
            _condition("tags", "all_of", ["snmp:snmp"]),
            id="empty auxiliary tag is skipped",
        ),
        pytest.param(
            "host_auxtags",
            {"host_auxtags_0": "snmp", "host_auxtags_2": "tcp"},
            _condition("tags", "all_of", ["snmp:snmp"]),
            id="auxiliary tags end at the first number missing",
        ),
        pytest.param(
            "host_tags",
            _tag_rows(("criticality", "is", "prod")),
            _condition("tags", "all_of", ["criticality:prod"]),
            id="tag",
        ),
        pytest.param(
            "host_tags",
            _tag_rows(("criticality", "isnot", "prod")),
            _not(_condition("tags", "all_of", ["criticality:prod"])),
            id="tag the host does not have",
        ),
        pytest.param(
            "host_tags",
            _tag_rows(("criticality", "is", "prod"), ("agent", "isnot", "no-agent")),
            {
                "type": "and",
                "children": [
                    _condition("tags", "all_of", ["criticality:prod"]),
                    _not(_condition("tags", "all_of", ["agent:no-agent"])),
                ],
            },
            id="tags, one negated",
        ),
        pytest.param(
            "host_tags",
            _tag_rows(("criticality", "", "prod"), ("agent", "is", "cmk-agent")),
            _condition("tags", "all_of", ["agent:cmk-agent"]),
            id="tag without an operator is skipped",
        ),
        pytest.param(
            "host_tags",
            _tag_rows(("criticality", "is", "prod"), ("", "", ""), ("agent", "is", "cmk-agent")),
            _condition("tags", "all_of", ["criticality:prod"]),
            id="tags end at the first without a tag group",
        ),
        pytest.param(
            "host_tags",
            _tag_rows(*[("criticality", "isnot", f"tag{number}") for number in range(4)]),
            {
                "type": "and",
                "children": [
                    _not(_condition("tags", "all_of", [f"criticality:tag{number}"]))
                    for number in range(4)
                ],
            },
            id="more tags than the form has rows",
        ),
        pytest.param(
            "host_labels",
            label_group_variables([("and", [("and", "cmk/os_family:linux")])]),
            _label("cmk/os_family:linux"),
            id="label",
        ),
        pytest.param(
            "host_labels",
            label_group_variables([("and", [("and", "a:b:c")])]),
            _label("a:b:c"),
            id="label with a colon in its value",
        ),
        pytest.param(
            "host_labels",
            label_group_variables([("and", [("and", "a:1"), ("and", "b:2")])]),
            {"type": "and", "children": [_label("a:1"), _label("b:2")]},
            id="labels joined by and",
        ),
        pytest.param(
            "host_labels",
            label_group_variables([("and", [("and", "a:1"), ("or", "b:2")])]),
            {"type": "or", "children": [_label("a:1"), _label("b:2")]},
            id="labels joined by or",
        ),
        pytest.param(
            "host_labels",
            label_group_variables([("and", [("and", "a:1"), ("not", "b:2")])]),
            {"type": "and", "children": [_label("a:1"), _not(_label("b:2"))]},
            id="label joined by not",
        ),
        pytest.param(
            "host_labels",
            label_group_variables([("and", [("and", "a:1"), ("or", "b:2"), ("and", "c:3")])]),
            {
                "type": "or",
                "children": [
                    _label("a:1"),
                    {"type": "and", "children": [_label("b:2"), _label("c:3")]},
                ],
            },
            id="and binds tighter than or, as in the legacy filter",
        ),
        pytest.param(
            "host_labels",
            label_group_variables([("and", [("and", "a:1"), ("and", "b:2"), ("or", "c:3")])]),
            {
                "type": "or",
                "children": [
                    {"type": "and", "children": [_label("a:1"), _label("b:2")]},
                    _label("c:3"),
                ],
            },
            id="or after labels joined by and",
        ),
        pytest.param(
            "host_labels",
            label_group_variables([("and", [("and", "a:1"), ("or", "b:2"), ("not", "c:3")])]),
            {
                "type": "or",
                "children": [
                    _label("a:1"),
                    {"type": "and", "children": [_label("b:2"), _not(_label("c:3"))]},
                ],
            },
            id="not after or extends the alternative",
        ),
        pytest.param(
            "host_labels",
            label_group_variables([("and", [("not", "a:1"), ("and", "b:2")])]),
            {"type": "and", "children": [_not(_label("a:1")), _label("b:2")]},
            id="first label joined by not",
        ),
        pytest.param(
            "host_labels",
            label_group_variables([("and", [("or", "a:1"), ("and", "b:2")])]),
            {"type": "and", "children": [_label("a:1"), _label("b:2")]},
            id="operator of the first label is ignored unless it is not",
        ),
        pytest.param(
            "host_labels",
            label_group_variables([("and", [("and", ""), ("not", "a:1")])]),
            _not(_label("a:1")),
            id="empty label is skipped, so the next one is the first",
        ),
        pytest.param(
            "host_labels",
            label_group_variables([("and", [("and", "a:1")]), ("or", [("and", "b:2")])]),
            {"type": "or", "children": [_label("a:1"), _label("b:2")]},
            id="groups joined by or",
        ),
        pytest.param(
            "host_labels",
            label_group_variables([("and", [("and", "a:1")]), ("not", [("and", "b:2")])]),
            {"type": "and", "children": [_label("a:1"), _not(_label("b:2"))]},
            id="group joined by not",
        ),
        pytest.param(
            "host_labels",
            label_group_variables(
                [
                    ("and", [("not", "a:1")]),
                    ("or", [("and", "b:2")]),
                    ("not", [("and", "c:3")]),
                ]
            ),
            {
                "type": "or",
                "children": [
                    _not(_label("a:1")),
                    {"type": "and", "children": [_label("b:2"), _not(_label("c:3"))]},
                ],
            },
            id="groups of the legacy filter's own examples",
        ),
        pytest.param(
            "host_labels",
            label_group_variables(
                [("not", [("and", "a:1"), ("and", "b:2")]), ("and", [("and", "c:3")])]
            ),
            {
                "type": "and",
                "children": [
                    _not({"type": "and", "children": [_label("a:1"), _label("b:2")]}),
                    _label("c:3"),
                ],
            },
            id="first group joined by not",
        ),
        pytest.param(
            "host_labels",
            label_group_variables(
                [
                    ("and", [("and", "a:1"), ("and", "b:2")]),
                    ("or", [("and", "c:3"), ("or", "d:4")]),
                    ("and", [("and", "e:5")]),
                ]
            ),
            {
                "type": "or",
                "children": [
                    {"type": "and", "children": [_label("a:1"), _label("b:2")]},
                    {
                        "type": "and",
                        "children": [
                            {"type": "or", "children": [_label("c:3"), _label("d:4")]},
                            _label("e:5"),
                        ],
                    },
                ],
            },
            id="groups with several labels, joined by and and or",
        ),
        pytest.param(
            "siteopt",
            {"site": "remote"},
            _condition("site_id", "one_of", ["remote"]),
            id="site",
        ),
        pytest.param(
            "sites",
            {"sites": "a|b|a"},
            _condition("site_id", "one_of", ["a", "b"]),
            id="sites",
        ),
        pytest.param(
            "opthost_contactgroup",
            {"opthost_contact_group": "all|admins"},
            _condition("contact_groups", "one_of", ["all", "admins"]),
            id="name list",
        ),
        pytest.param(
            "opthost_contactgroup",
            {"opthost_contact_group": "all||admins|"},
            _condition("contact_groups", "one_of", ["all", "admins"]),
            id="name list with empty names",
        ),
        pytest.param(
            "opthost_contactgroup",
            {"opthost_contact_group": "all", "neg_opthost_contact_group": "on"},
            _not(_condition("contact_groups", "one_of", ["all"])),
            id="negated name list",
        ),
        pytest.param(
            "opthostgroup",
            {"opthost_group": "linux|windows"},
            _condition("groups", "one_of", ["linux", "windows"]),
            id="host groups",
        ),
        pytest.param(
            "opthostgroup",
            {"opthost_group": "linux", "neg_opthost_group": "on"},
            _not(_condition("groups", "one_of", ["linux"])),
            id="negated host groups",
        ),
        pytest.param(
            "opthostgroup",
            {"opthost_group": "linux|windows", "neg_opthost_group": "on"},
            _not(_condition("groups", "one_of", ["linux", "windows"])),
            id="negated host groups of several names",
        ),
        pytest.param(
            "host_ctc",
            {"host_ctc": "admin|ops"},
            _condition("contacts", "one_of", ["admin|ops"]),
            id="single name",
        ),
        pytest.param(
            "host_ctc_regex",
            {"host_ctc_regex": "adm.*"},
            _condition("contacts", "contains", "adm.*"),
            id="text of a filter that cannot be negated",
        ),
        pytest.param(
            "host_ctc_regex",
            {"host_ctc_regex": "adm", "neg_host_ctc_regex": "on"},
            _condition("contacts", "contains", "adm"),
            id="negation variable of a filter that cannot be negated is ignored",
        ),
        pytest.param(
            "host_acknowledged",
            {"is_host_acknowledged": "0"},
            _condition("acknowledged", "eq", False),
            id="flag",
        ),
        pytest.param(
            "hoststate",
            {"hst0": "", "hst1": "on", "hst2": "on", "hstp": ""},
            _condition("state", "one_of", ["DOWN", "UNREACHABLE"]),
            id="state choice",
        ),
        pytest.param(
            "hosts_having_service_problems",
            {"hosts_having_services_warn": "on", "hosts_having_services_crit": "on"},
            {
                "type": "or",
                "children": [
                    _condition("num_services_warn", "gt", 0),
                    _condition("num_services_crit", "gt", 0),
                ],
            },
            id="service problems to count",
        ),
        pytest.param(
            "hosts_having_service_problems",
            {"hosts_having_services_unknown": "on"},
            _condition("num_services_unknown", "gt", 0),
            id="one service problem to count",
        ),
        pytest.param(
            "host_num_services",
            {"host_num_services_from": "1", "host_num_services_until": "9"},
            {
                "type": "and",
                "children": [
                    _condition("num_services", "gte", 1),
                    _condition("num_services", "lte", 9),
                ],
            },
            id="number range",
        ),
        pytest.param(
            "host_num_services",
            {"host_num_services_until": "9"},
            _condition("num_services", "lte", 9),
            id="number range with one bound",
        ),
        pytest.param(
            "host_num_services",
            {"host_num_services_until": "-1"},
            _condition("num_services", "lte", -1),
            id="bound that reads like an ignored flag",
        ),
    ],
)
def test_legacy_filter_translates_to_condition_on_its_field(
    name: FilterName, value: FilterHTTPVariables, expected: _JSON
) -> None:
    assert _translate({name: value}) == ContextFilterTranslation(filter=expected, unapplied=[])


@pytest.mark.parametrize(
    "context",
    [
        pytest.param({}, id="no filters"),
        pytest.param({"siteopt": {}, "hostregex": {}}, id="defaults of a view"),
        pytest.param({"hostregex": {"host_regex": "", "neg_host_regex": ""}}, id="empty vars"),
        pytest.param({"sites": {"sites": "|"}}, id="no site"),
        pytest.param(
            {"opthostgroup": {"opthost_group": "|", "neg_opthost_group": "on"}},
            id="negated host groups naming no group",
        ),
        pytest.param(
            {"host_ctc_regex": {"neg_host_ctc_regex": "on"}}, id="negation without a pattern"
        ),
        pytest.param({"hostnameoralias": {"hostnameoralias": ""}}, id="no text in either field"),
        pytest.param({"address_family": {"address_family": "both"}}, id="either address family"),
        pytest.param({"address_family": {"address_family": "7"}}, id="unknown address family"),
        pytest.param({"address_families": {"address_families": ""}}, id="ignored address families"),
        pytest.param(
            {"address_families": {"address_families": "7"}}, id="unknown address families"
        ),
        pytest.param({"host_auxtags": {"host_auxtags_0": ""}}, id="no auxiliary tag"),
        pytest.param(
            {"host_auxtags": {"host_auxtags_0_neg": "on", "host_auxtags_1": "snmp"}},
            id="auxiliary tags ending before the first",
        ),
        pytest.param({"host_tags": {}}, id="no tag variables"),
        pytest.param(
            {"host_tags": _tag_rows(("criticality", "", "prod"))}, id="tag without an operator"
        ),
        pytest.param(
            {"host_tags": _tag_rows(("", "is", "prod"), ("criticality", "is", "prod"))},
            id="tags ending before the first",
        ),
        pytest.param({"kubernetes_cluster": {"kubernetes_cluster": ""}}, id="no Kubernetes object"),
        pytest.param({"host_labels": {}}, id="no label variables"),
        pytest.param({"host_last_check": {}}, id="no time bounds"),
        pytest.param(
            {"host_last_check": {"host_last_check_from": "2"}}, id="time bound without its range"
        ),
        pytest.param(
            {
                "host_last_check": {
                    "host_last_check_until": "",
                    "host_last_check_until_range": "abs",
                }
            },
            id="time bound that was not set",
        ),
        pytest.param({"host_labels": {"host_labels_count": "0"}}, id="no label group"),
        pytest.param(
            {"host_labels": label_group_variables([("and", [("and", "")])])},
            id="group of an empty label",
        ),
        pytest.param(
            {"hosts_having_service_problems": {"hosts_having_services_warn": ""}},
            id="no service problem to count",
        ),
        pytest.param(
            {
                "hosts_having_service_problems": {
                    "hosts_having_services_warn": "on",
                    "hosts_having_services_crit": "on",
                    "hosts_having_services_pending": "on",
                    "hosts_having_services_unknown": "on",
                }
            },
            id="every service problem to count",
        ),
        pytest.param({"host_acknowledged": {"is_host_acknowledged": "-1"}}, id="ignored flag"),
        pytest.param(
            {"host_staleness": {"is_host_staleness": "-1"}},
            id="ignored flag the page does not map",
        ),
        pytest.param(
            {"wato_folder": {"wato_folder": "-1"}},
            id="filter outside the catalog that reads like an ignored flag",
        ),
        pytest.param(
            {"hoststate": {"hst0": "on", "hst1": "on", "hst2": "on", "hstp": "on"}},
            id="every state",
        ),
        pytest.param(
            {"host_address": {"host_address": "", "host_address_prefix": "yes\n"}},
            id="line break in a variable that restricts nothing",
        ),
    ],
)
def test_inactive_context_translates_to_no_filter(context: VisualContext) -> None:
    assert _translate(context) == ContextFilterTranslation(filter=None, unapplied=[])


@pytest.mark.parametrize(
    "context",
    [
        pytest.param({"hostregex": {"host_regex": "web["}}, id="invalid regex"),
        pytest.param(
            {"opthost_contactgroup": {"opthost_contact_group": "adm*"}},
            id="name the page would read as a prefix",
        ),
        pytest.param(
            {"opthostgroup": {"opthost_group": "linux|win*"}},
            id="host group the page would read as a prefix",
        ),
        pytest.param({"host_ctc_regex": {"host_ctc_regex": "adm["}}, id="invalid contact regex"),
        pytest.param({"opthostgroup": {"opthost_group": "|"}}, id="host groups naming no group"),
        pytest.param(
            {"opthost_contactgroup": {"opthost_contact_group": "||"}},
            id="contact groups naming no group",
        ),
        pytest.param(
            {"hostnameoralias": {"hostnameoralias": "web["}}, id="invalid name or alias regex"
        ),
        pytest.param({"host_auxtags": {"host_auxtags_0": "a:b"}}, id="auxiliary tag with a colon"),
        pytest.param(
            {"host_auxtags": {"host_auxtags_0": "snmp", "host_auxtags_1": "tc*"}},
            id="auxiliary tag the page would read as a prefix",
        ),
        pytest.param(
            {"host_tags": _tag_rows(("gone", "is", "prod"))},
            id="tag of a group that is not configured",
        ),
        pytest.param(
            {"host_tags": _tag_rows(("criticality", "is", "prod"), ("gone", "isnot", "prod"))},
            id="tag of a group that is not configured after one that is",
        ),
        pytest.param(
            {"host_tags": _tag_rows(("criticality", "is", ""))}, id="host without a tag of a group"
        ),
        pytest.param(
            {"host_tags": _tag_rows(("criticality", "isnot", ""))}, id="host with a tag of a group"
        ),
        pytest.param(
            {"host_tags": _tag_rows(("criticality", "is", "pr*"))},
            id="tag the page would read as a prefix",
        ),
        pytest.param(
            {"kubernetes_cluster": {"kubernetes_cluster": "prod*"}},
            id="Kubernetes object the page would read as a prefix",
        ),
        pytest.param({"host_labels": {"host_labels_count": "many"}}, id="label count not a number"),
        pytest.param(
            {
                "host_last_check": {
                    "host_last_check_from": "soon",
                    "host_last_check_from_range": "60",
                }
            },
            id="time ago not a number",
        ),
        pytest.param(
            {
                "host_last_check": {
                    "host_last_check_from": "1.5",
                    "host_last_check_from_range": "60",
                }
            },
            id="time ago not a whole number",
        ),
        pytest.param(
            {
                "host_last_check": {
                    "host_last_check_until": "1",
                    "host_last_check_until_range": "weeks",
                }
            },
            id="unit of time ago not a number of seconds",
        ),
        pytest.param(
            {
                "host_last_check": {
                    "host_last_check_from": "2026-13-45",
                    "host_last_check_from_range": "abs",
                }
            },
            id="date that does not exist",
        ),
        pytest.param(
            {
                "host_last_check": {
                    "host_last_check_from": "2026-01-02",
                    "host_last_check_from_range": "ts",
                }
            },
            id="timestamp without a time",
        ),
        pytest.param(
            {
                "host_last_check": {
                    "host_last_check_from": "noon",
                    "host_last_check_from_range": "unix",
                }
            },
            id="Unix timestamp not a number",
        ),
        pytest.param(
            {
                "host_last_check": {
                    "host_last_check_from": "99999999999999999999999",
                    "host_last_check_from_range": "unix",
                }
            },
            id="Unix timestamp out of range",
        ),
        # Livestatus reads the bound of a time column as a 32 bit integer.
        pytest.param(
            {
                "host_last_check": {
                    "host_last_check_from": str(2**31),
                    "host_last_check_from_range": "unix",
                }
            },
            id="Unix timestamp just above 32 bits",
        ),
        pytest.param(
            {
                "host_last_check": {
                    "host_last_check_until": str(-(2**31) - 1),
                    "host_last_check_until_range": "unix",
                }
            },
            id="Unix timestamp just below 32 bits",
        ),
        pytest.param(
            {
                "host_last_check": {
                    "host_last_check_until": "2040-01-01",
                    "host_last_check_until_range": "abs",
                }
            },
            id="date after 2038",
        ),
        pytest.param(
            {
                "host_last_check": {
                    "host_last_check_from": "1900-01-01 00:00:00",
                    "host_last_check_from_range": "ts",
                }
            },
            id="date and time before 1901",
        ),
        pytest.param(
            {
                "host_last_check": {
                    "host_last_check_until": "9999999999999999999",
                    "host_last_check_until_range": "1",
                }
            },
            id="time ago out of range",
        ),
        pytest.param(
            {"host_labels": label_group_variables([("xor", [("and", "a:1")])])},
            id="unknown group operator",
        ),
        pytest.param(
            {"host_labels": label_group_variables([("and", [("xor", "a:1")])])},
            id="unknown label operator",
        ),
        pytest.param(
            {"host_labels": label_group_variables([("and", [("and", "a")])])},
            id="label without value",
        ),
        pytest.param(
            {"host_labels": label_group_variables([("and", [("and", "a:")])])},
            id="label with empty value",
        ),
        pytest.param(
            {"host_labels": label_group_variables([("and", [("and", "a:1*")])])},
            id="label the page would read as a prefix",
        ),
        pytest.param(
            {"host_labels": label_group_variables([("and", [("and", ":1")])])},
            id="label with empty key",
        ),
        # The legacy filter checks every operator, also the one of a label that is skipped.
        pytest.param(
            {"host_labels": label_group_variables([("and", [("xor", ""), ("and", "a:1")])])},
            id="unknown operator of an empty label",
        ),
        pytest.param(
            {"host_num_services": {"host_num_services_from": "1.5"}}, id="bound not a number"
        ),
        pytest.param({"wato_folder": {"wato_folder": "linux"}}, id="filter the page does not map"),
        pytest.param({"sites": {"sites": "a\nb"}}, id="line break in a site"),
    ],
)
def test_filter_without_equivalent_is_reported(context: VisualContext) -> None:
    assert _translate(context) == ContextFilterTranslation(filter=None, unapplied=list(context))


@pytest.mark.parametrize(
    "name, value, expected",
    [
        pytest.param(
            "host_last_check",
            {"host_last_check_from": "2", "host_last_check_from_range": "3600"},
            _condition("last_check", "gte", _NOW_TS - 2 * 3600),
            id="hours ago",
        ),
        pytest.param(
            "host_last_check",
            {"host_last_check_until": "10", "host_last_check_until_range": "60"},
            _condition("last_check", "lte", _NOW_TS - 10 * 60),
            id="minutes ago",
        ),
        pytest.param(
            "host_last_check",
            {"host_last_check_from": "1", "host_last_check_from_range": "86400"},
            _condition("last_check", "gte", _NOW_TS - 86400),
            id="days ago",
        ),
        pytest.param(
            "host_last_check",
            {"host_last_check_from": "30", "host_last_check_from_range": "1"},
            _condition("last_check", "gte", _NOW_TS - 30),
            id="seconds ago",
        ),
        pytest.param(
            "host_last_check",
            {"host_last_check_from": "3", "host_last_check_from_range": "7"},
            _condition("last_check", "gte", _NOW_TS - 21),
            id="unit that is some other number of seconds",
        ),
        pytest.param(
            "host_last_check",
            {"host_last_check_from": "1700000000", "host_last_check_from_range": "unix"},
            _condition("last_check", "gte", 1700000000),
            id="Unix timestamp",
        ),
        pytest.param(
            "host_last_check",
            {"host_last_check_from": str(2**31 - 1), "host_last_check_from_range": "unix"},
            _condition("last_check", "gte", 2**31 - 1),
            id="latest Unix timestamp of 32 bits",
        ),
        pytest.param(
            "host_last_check",
            {"host_last_check_until": str(-(2**31)), "host_last_check_until_range": "unix"},
            _condition("last_check", "lte", -(2**31)),
            id="earliest Unix timestamp of 32 bits",
        ),
        pytest.param(
            "host_last_check",
            {"host_last_check_until": "2026-01-02", "host_last_check_until_range": "abs"},
            _condition(
                "last_check", "lte", int(datetime(2026, 1, 2, tzinfo=_SERVER_TIMEZONE).timestamp())
            ),
            id="date of the server",
        ),
        pytest.param(
            "host_last_check",
            {"host_last_check_from": "2026-01-02 03:04:05", "host_last_check_from_range": "ts"},
            _condition(
                "last_check",
                "gte",
                int(datetime(2026, 1, 2, 3, 4, 5, tzinfo=_SERVER_TIMEZONE).timestamp()),
            ),
            id="date and time of the server",
        ),
        pytest.param(
            "host_last_check",
            {
                "host_last_check_from": "2",
                "host_last_check_from_range": "3600",
                "host_last_check_until": "1",
                "host_last_check_until_range": "3600",
            },
            {
                "type": "and",
                "children": [
                    _condition("last_check", "gte", _NOW_TS - 2 * 3600),
                    _condition("last_check", "lte", _NOW_TS - 3600),
                ],
            },
            id="both bounds",
        ),
        pytest.param(
            "host_last_state_change",
            {"host_last_state_change_from": "5", "host_last_state_change_from_range": "60"},
            _condition("last_state_change", "gte", _NOW_TS - 5 * 60),
            id="last state change",
        ),
    ],
)
def test_time_range_filter_translates_to_bounds_on_timestamps(
    name: FilterName, value: FilterHTTPVariables, expected: _JSON
) -> None:
    with time_machine.travel(_NOW, tick=False):
        translation = _translate({name: value})

    assert translation == ContextFilterTranslation(filter=expected, unapplied=[])


@pytest.mark.parametrize(
    "name, value, restricts",
    [
        pytest.param("hostregex", {"host_regex": "-1"}, True, id="reads like an ignored flag"),
        pytest.param("hostregex", {"host_regex": "web["}, True, id="untranslatable"),
        pytest.param("hostregex", {"neg_host_regex": "on"}, False, id="restricts nothing"),
        pytest.param("hostnameoralias", {"hostnameoralias": "web"}, True, id="text in two fields"),
        pytest.param("hostnameoralias", {}, False, id="no text in two fields"),
        pytest.param(
            "hosts_having_service_problems",
            {"hosts_having_services_warn": "on"},
            True,
            id="service problem to count",
        ),
        pytest.param("hosts_having_service_problems", {}, False, id="no service problem"),
        pytest.param("address_families", {"address_families": "both"}, True, id="address families"),
        pytest.param("address_families", {"address_families": ""}, False, id="ignored families"),
        pytest.param("host_auxtags", {"host_auxtags_0": "snmp"}, True, id="auxiliary tag"),
        pytest.param("host_auxtags", {"host_auxtags_0": ""}, False, id="empty auxiliary tag"),
        pytest.param("host_tags", _tag_rows(("criticality", "is", "prod")), True, id="tag"),
        pytest.param("host_tags", _tag_rows(("criticality", "", "prod")), False, id="no operator"),
        pytest.param("kubernetes_node", {"kubernetes_node": "n1"}, True, id="Kubernetes node"),
        pytest.param(
            "host_labels",
            label_group_variables([("and", [("and", "a:1")])]),
            True,
            id="label group",
        ),
        pytest.param("host_labels", {"host_labels_count": "0"}, False, id="no label group"),
        pytest.param(
            "host_last_check",
            {"host_last_check_from": "1", "host_last_check_from_range": "60"},
            True,
            id="time bound",
        ),
        pytest.param("host_last_check", {"host_last_check_from": "1"}, False, id="no time range"),
    ],
)
def test_filter_the_page_does_not_map_is_reported_only_if_it_restricts_anything(
    name: FilterName, value: FilterHTTPVariables, restricts: bool
) -> None:
    translation = translate_context({name: value}, _fields_without(name), ANY_PAGE)

    assert translation == ContextFilterTranslation(
        filter=None, unapplied=[name] if restricts else []
    )


def test_page_mapping_a_filter_outside_the_catalog_is_rejected() -> None:
    with pytest.raises(ValueError, match="hostgroups"):
        translate_context({}, {"hostgroups": "groups"}, ANY_PAGE)


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param({"hostnameoralias": "name"}, id="single field for a filter with roles"),
        pytest.param({"hostnameoralias": {"name": "name"}}, id="missing role"),
        pytest.param(
            {"hostnameoralias": {"name": "name", "alias": "alias", "address": "address"}},
            id="unknown role",
        ),
        pytest.param({"hostregex": {"name": "name"}}, id="roles for a filter with a single field"),
        pytest.param({"siteopt": {"name": "name"}}, id="roles for a site filter that is not set"),
    ],
)
def test_page_mapping_a_filter_to_fields_that_do_not_fit_it_is_rejected(fields: _Fields) -> None:
    with pytest.raises(ValueError, match="Expected"):
        translate_context({}, fields, ANY_PAGE)


def test_unapplied_filters_are_reported_in_context_order() -> None:
    translation = _translate(
        {
            "wato_folder": {"wato_folder": "linux"},
            "hostregex": {"host_regex": "web"},
            "hostalias": {"hostalias": "(Web"},
        }
    )

    assert translation == ContextFilterTranslation(
        filter=_condition("name", "contains", "web"), unapplied=["wato_folder", "hostalias"]
    )


def _fields_without(name: FilterName) -> _Fields:
    return {other: field for other, field in _FIELDS.items() if other != name}


@pytest.mark.parametrize(
    "context, fields, expected_sites, expected_unapplied",
    [
        pytest.param(
            {"siteopt": {"site": "c"}, "site": {"site": "b"}, "sites": {"sites": "a"}},
            _FIELDS,
            ["a"],
            ["siteopt", "site"],
            id="sites over site and siteopt",
        ),
        pytest.param(
            {"siteopt": {"site": "c"}, "site": {"site": "b"}},
            _FIELDS,
            ["b"],
            ["siteopt"],
            id="site over siteopt",
        ),
        pytest.param(
            {"sites": {"sites": "|"}, "siteopt": {"site": "c"}},
            _FIELDS,
            ["c"],
            [],
            id="a site filter naming no site does not count",
        ),
        pytest.param(
            {"sites": {"sites": "|"}, "siteopt": {"site": "c"}},
            _fields_without("sites"),
            ["c"],
            [],
            id="an unmapped site filter naming no site does not count",
        ),
        pytest.param(
            {"sites": {"sites": "a"}, "site": {"site": "b"}},
            _fields_without("site"),
            ["a"],
            ["site"],
            id="unmapped site filter after the first",
        ),
        pytest.param(
            {"sites": {"sites": "a|b"}, "site": {"site": "a"}},
            _FIELDS,
            ["a", "b"],
            ["site"],
            id="site filter after the first naming fewer sites",
        ),
        pytest.param(
            {"sites": {"sites": "a"}, "siteopt": {"site": "a"}},
            _FIELDS,
            ["a"],
            [],
            id="site filter after the first naming the same site",
        ),
        pytest.param(
            {"sites": {"sites": "a"}, "site": {"site": "a\nb"}},
            _FIELDS,
            ["a"],
            ["site"],
            id="site filter after the first naming a site the page cannot take",
        ),
    ],
)
def test_only_the_first_site_filter_applies_and_the_others_are_reported_if_they_narrow_the_sites(
    context: VisualContext,
    fields: _Fields,
    expected_sites: list[str],
    expected_unapplied: list[FilterName],
) -> None:
    assert translate_context(context, fields, ANY_PAGE) == ContextFilterTranslation(
        filter=_condition("site_id", "one_of", expected_sites), unapplied=expected_unapplied
    )


@pytest.mark.parametrize(
    "context, fields",
    [
        pytest.param(
            {"sites": {"sites": "a\nb"}, "siteopt": {"site": "c"}},
            _FIELDS,
            id="untranslatable",
        ),
        pytest.param(
            {"sites": {"sites": "a"}, "site": {"site": "b"}},
            _fields_without("sites"),
            id="not mapped",
        ),
        pytest.param(
            {"sites": {"sites": "a"}, "site": {"site": "a"}},
            _fields_without("sites"),
            id="not mapped, with a later one naming the same site",
        ),
    ],
)
def test_first_site_filter_that_cannot_apply_is_reported_and_keeps_the_others_from_applying(
    context: VisualContext, fields: _Fields
) -> None:
    assert translate_context(context, fields, ANY_PAGE) == ContextFilterTranslation(
        filter=None, unapplied=list(context)
    )


def _at_most_one_condition(node: _JSON) -> _JSON:
    if node["type"] == "and":
        raise ValueError("more than one condition")
    return node


_ONE_CONDITION_PAGE = PageFilterModel(
    tree=TypeAdapter(dict[str, object]), check=_at_most_one_condition
)


def test_filter_the_page_does_not_accept_together_with_an_earlier_one_is_reported() -> None:
    translation = translate_context(
        {"hostalias": {"hostalias": "Web"}, "hostregex": {"host_regex": "web"}},
        _FIELDS,
        _ONE_CONDITION_PAGE,
    )

    # The filter listed first in the fields wins, whatever the order of the context.
    assert translation == ContextFilterTranslation(
        filter=_condition("name", "contains", "web"), unapplied=["hostalias"]
    )
