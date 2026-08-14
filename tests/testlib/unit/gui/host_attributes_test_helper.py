#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

"""Shared helpers for host attributes tests across editions."""

import json
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, NamedTuple

import pytest

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.http import request
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.watolib.host_attributes import (
    ABCHostAttributeFormSpec,
    all_host_attributes,
    collect_attributes,
)
from cmk.rulesets.v1.form_specs import FormSpec

BASE_EXPECTED_ATTRIBUTES: dict[str, dict[str, Any]] = {
    "additional_ipv4addresses": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": ["ip-v4"],
        "editable": True,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Network address",
    },
    "additional_ipv6addresses": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": ["ip-v6"],
        "editable": True,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Network address",
    },
    "alias": {
        "class_name": "NagiosTextAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": True,
        "show_inherited_value": True,
        "topic": "Basic settings",
    },
    "contactgroups": {
        "class_name": "ContactGroupsAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Basic settings",
    },
    "ipaddress": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": ["ip-v4"],
        "editable": True,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": True,
        "show_inherited_value": True,
        "topic": "Network address",
    },
    "ipv6address": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": ["ip-v6"],
        "editable": True,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": True,
        "show_inherited_value": True,
        "topic": "Network address",
    },
    "locked_attributes": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": False,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": False,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Creation / Locking",
    },
    "locked_by": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": False,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Creation / Locking",
    },
    "management_address": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Management board",
    },
    "management_ipmi_credentials": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Management board",
    },
    "management_protocol": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Management board",
    },
    "management_snmp_community": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Management board",
    },
    "meta_data": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": False,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": False,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Creation / Locking",
    },
    "network_scan": {
        "class_name": "HostAttributeNetworkScan",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": False,
        "show_in_host_search": False,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Network scan",
    },
    "network_scan_result": {
        "class_name": "NetworkScanResultAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": False,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": False,
        "show_in_host_search": False,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Network scan",
    },
    "parents": {
        "class_name": "ParentsAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": True,
        "show_inherited_value": True,
        "topic": "Basic settings",
    },
    "site": {
        "class_name": "SiteAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": True,
        "show_inherited_value": True,
        "topic": "Basic settings",
    },
    "snmp_community": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": ["snmp"],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Monitoring agents",
    },
    "tag_address_family": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": True,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Network address",
    },
    "tag_agent": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": True,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Monitoring agents",
    },
    "tag_snmp_ds": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": True,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Monitoring agents",
    },
    "tag_piggyback": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": True,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Monitoring agents",
    },
    "labels": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Custom attributes",
    },
    "inventory_failed": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": False,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": False,
        "show_in_host_search": False,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Creation / Locking",
    },
    "waiting_for_discovery": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": False,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": False,
        "show_in_host_search": False,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Custom attributes",
    },
}

CMK_AGENT_CONNECTION_ATTR: dict[str, dict[str, Any]] = {
    "cmk_agent_connection": {
        "depends_on_roles": [],
        "depends_on_tags": ["checkmk-agent"],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Monitoring agents",
    },
}

METRICS_ASSOCIATION_ATTR: dict[str, dict[str, Any]] = {
    "metrics_association": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Monitoring agents",
    },
}

BAKE_AGENT_PACKAGE_ATTR: dict[str, dict[str, Any]] = {
    "bake_agent_package": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": False,
        "show_in_host_search": False,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Monitoring agents",
    },
}

RELAY_ATTR: dict[str, dict[str, Any]] = {
    "relay": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": True,
        "show_inherited_value": True,
        "topic": "Basic settings",
    },
}


@dataclass(frozen=True)
class CasePass:
    """A value that is accepted and stored on disk unchanged."""

    id: str
    value: object


@dataclass(frozen=True)
class CaseFail:
    """A value that the form spec rejects."""

    id: str
    value: object


Case = CasePass | CaseFail


# The attributes available in every edition, so every edition's module composes its cases
# on top of these. No attribute is FormSpec-native yet; each migration adds its values here.
BASE_FORM_SPEC_CASES: Mapping[str, list[Case]] = {}


def form_spec_attributes() -> dict[str, ABCHostAttributeFormSpec]:
    """All registered attributes whose whole lifecycle is backed by a form spec."""
    return {
        name: attr
        for name, attr in all_host_attributes(
            active_config.wato_host_attrs,
            active_config.tags.get_tag_groups_by_topic(),
        ).items()
        if isinstance(attr, ABCHostAttributeFormSpec)
    }


class RoundTrip(NamedTuple):
    ok: bool
    detail: str


def validate_form_spec_default_value(form_spec: FormSpec[object], default: object) -> RoundTrip:
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=False, mask_values=False))
    raw = RawDiskData(default)
    try:
        on_disk = visitor.to_disk(raw)
    except Exception as exc:
        return RoundTrip(False, f"to_disk raised: {exc!r}")
    if on_disk != default:
        return RoundTrip(False, f"to_disk changed the value: {on_disk!r} != {default!r}")
    return RoundTrip(True, "")


def assert_round_trips(
    kind: str, results: Mapping[str, RoundTrip], skip: Collection[str] = ()
) -> None:
    failures: list[str] = []
    for name, result in sorted(results.items()):
        if not result.ok and name not in skip:
            failures.append(f"{name}: {result.detail}")

    assert not failures, f"{kind} failed to round-trip the default value of:\n" + "\n".join(
        failures
    )


def assert_form_spec_attributes_round_trip_default_value() -> None:
    """FormSpec-native attributes (no valuespec) must round-trip their own default value."""
    assert_round_trips(
        "native FormSpec",
        {
            name: validate_form_spec_default_value(attr.form_spec(), attr.default_value())
            for name, attr in form_spec_attributes().items()
        },
    )


def assert_cases_cover_form_spec_attributes(cases: Mapping[str, Sequence[Case]]) -> None:
    registered = set(form_spec_attributes())
    documented = set(cases)
    assert registered == documented, (
        f"missing cases for: {sorted(registered - documented)}; "
        f"unknown attributes in cases: {sorted(documented - registered)}"
    )


def assert_show_in_table_attributes_paint_plain_text(
    cases: Mapping[str, Sequence[Case]],
) -> None:
    """The folder's host table paints every show_in_table attribute of every row through
    ABCHostAttributeFormSpec.paint(), which renders plain str(value). That is only fit for
    string values; a structured value would show up as its Python repr."""
    for name, attr in form_spec_attributes().items():
        if not attr.show_in_table():
            continue
        if type(attr).paint is not ABCHostAttributeFormSpec.paint:
            # The attribute brings its own table rendering.
            continue
        for case in cases.get(name, []):
            if isinstance(case, CasePass):
                assert case.value is None or isinstance(case.value, str), (
                    f"{name} is shown in the folder's host table, where the base-class "
                    f"paint() renders str(value) - unfit for {case.value!r}. Override "
                    "paint() with a compact summary or set show_in_table=False."
                )


def assert_form_spec_value_behavior(attr: ABCHostAttributeFormSpec, case: Case) -> None:
    visitor = get_visitor(attr.form_spec(), VisitorOptions(migrate_values=False, mask_values=False))
    match case:
        case CasePass():
            assert not visitor.validate(RawDiskData(case.value))
            assert visitor.to_disk(RawDiskData(case.value)) == case.value
        case CaseFail():
            assert visitor.validate(RawDiskData(case.value))


def assert_form_spec_attribute_lifecycle(attr: ABCHostAttributeFormSpec, value: object) -> None:
    """Drive one value through render -> submit -> parse of the edit-page machinery.

    Needs a request context. The submitted data is the JSON the Vue mount posts back, so
    this also covers that the on-disk value survives the JSON leg of a real save.
    """
    with output_funnel.plugged():
        attr.render_input("", value)
        attr.render_input_readonly("", value)
        output_funnel.drain()

    request.set_var(attr.name(), json.dumps(value))
    assert attr.from_html_vars("") == value
    attr.validate_input(value, "")

    # Only attributes whose checkbox is ticked are collected, and they are validated.
    assert collect_attributes({attr.name(): attr}, for_what="host", new=True) == {}
    request.set_var(f"host_change_{attr.name()}", "on")
    assert collect_attributes({attr.name(): attr}, for_what="host", new=True) == {
        attr.name(): value
    }


def assert_form_spec_attribute_rejects(attr: ABCHostAttributeFormSpec, value: object) -> None:
    """A rejected value must not slip through the edit-page submit path."""
    with pytest.raises(MKUserError):
        attr.validate_input(value, "")

    request.set_var(attr.name(), json.dumps(value))
    request.set_var(f"host_change_{attr.name()}", "on")
    with pytest.raises(MKUserError):
        collect_attributes({attr.name(): attr}, for_what="host", new=True)
