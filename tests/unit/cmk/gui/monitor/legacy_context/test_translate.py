#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest
from pydantic import TypeAdapter

from cmk.gui.monitor.legacy_context import (
    ContextFilterTranslation,
    PageFilterModel,
    translate_context,
)
from cmk.gui.type_defs import FilterHTTPVariables, FilterName, VisualContext

type _JSON = dict[str, object]

# A page that accepts any tree, so that these tests see the translation unchanged.
_ANY_PAGE = PageFilterModel(tree=TypeAdapter(dict[str, object]), check=lambda tree: tree)

_FIELDS: dict[FilterName, str] = {
    "sites": "site_id",
    "site": "site_id",
    "siteopt": "site_id",
    "host": "name",
    "hostregex": "name",
    "hostalias": "alias",
    "host_address": "address",
    "host_ctc": "contacts",
    "opthost_contactgroup": "contact_groups",
    "hoststate": "state",
    "host_acknowledged": "acknowledged",
    "host_num_services": "num_services",
}


def _condition(field: str, op: str, value: object) -> _JSON:
    return {"type": "condition", "field": field, "op": op, "value": value}


def _not(child: _JSON) -> _JSON:
    return {"type": "not", "child": child}


def _translate(context: VisualContext) -> ContextFilterTranslation[_JSON]:
    return translate_context(context, _FIELDS, _ANY_PAGE)


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
            "host_ctc",
            {"host_ctc": "admin|ops"},
            _condition("contacts", "one_of", ["admin|ops"]),
            id="single name",
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
            {"host_num_services": {"host_num_services_from": "1.5"}}, id="bound not a number"
        ),
        pytest.param({"wato_folder": {"wato_folder": "linux"}}, id="filter the page does not map"),
        pytest.param({"sites": {"sites": "a\nb"}}, id="line break in a site"),
    ],
)
def test_filter_without_equivalent_is_reported(context: VisualContext) -> None:
    assert _translate(context) == ContextFilterTranslation(filter=None, unapplied=list(context))


@pytest.mark.parametrize(
    "value, expected_unapplied",
    [
        pytest.param({"host_regex": "-1"}, ["hostregex"], id="reads like an ignored flag"),
        pytest.param({"host_regex": "web["}, ["hostregex"], id="untranslatable"),
        pytest.param({"neg_host_regex": "on"}, [], id="restricts nothing"),
    ],
)
def test_filter_the_page_does_not_map_is_reported_if_it_restricts_anything(
    value: FilterHTTPVariables, expected_unapplied: list[FilterName]
) -> None:
    translation = translate_context({"hostregex": value}, _fields_without("hostregex"), _ANY_PAGE)

    assert translation == ContextFilterTranslation(filter=None, unapplied=expected_unapplied)


def test_page_mapping_a_filter_outside_the_catalog_is_rejected() -> None:
    with pytest.raises(ValueError, match="hostgroups"):
        translate_context({}, {"hostgroups": "groups"}, _ANY_PAGE)


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


def _fields_without(name: FilterName) -> dict[FilterName, str]:
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
    fields: Mapping[FilterName, str],
    expected_sites: list[str],
    expected_unapplied: list[FilterName],
) -> None:
    assert translate_context(context, fields, _ANY_PAGE) == ContextFilterTranslation(
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
    context: VisualContext, fields: Mapping[FilterName, str]
) -> None:
    assert translate_context(context, fields, _ANY_PAGE) == ContextFilterTranslation(
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
