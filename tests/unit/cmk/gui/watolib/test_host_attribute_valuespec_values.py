#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from dataclasses import dataclass

import pytest

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.host_attributes import ABCHostAttributeValueSpec, all_host_attributes


@dataclass(frozen=True)
class CasePass:
    id: str
    value: object


@dataclass(frozen=True)
class CaseFail:
    id: str
    value: object


@dataclass(frozen=True)
class CaseRaises:
    id: str
    value: object
    exception: type[BaseException]


Case = CasePass | CaseFail | CaseRaises


CASES: Mapping[str, list[Case]] = {
    "additional_ipv4addresses": [
        CasePass("empty", []),
        CasePass("single-ip", ["10.0.0.1"]),
        CasePass("ip-and-host", ["10.0.0.2", "host.example.com"]),
        CaseFail("not-a-list", "10.0.0.1"),
        CaseFail("inner-wrong-type", [123]),
        CaseFail("inner-empty", [""]),
        CaseFail("inner-ipv6", ["2001:db8::1"]),
    ],
    "additional_ipv6addresses": [
        CasePass("empty", []),
        CasePass("single-ip", ["2001:db8::1"]),
        CasePass("loopback-and-linklocal", ["::1", "fe80::1"]),
        CaseFail("not-a-list", "::1"),
        CaseFail("inner-wrong-type", [123]),
        CaseFail("inner-empty", [""]),
        CaseFail("inner-ipv4", ["10.0.0.1"]),
    ],
    "inventory_failed": [
        CasePass("true", True),
        CasePass("false", False),
        CaseFail("str", "true"),
        CaseFail("int", 1),
    ],
    "waiting_for_discovery": [
        CasePass("true", True),
        CasePass("false", False),
        CaseFail("str", "false"),
        CaseFail("int", 0),
    ],
    "ipaddress": [
        # The "unset" default ("") is rejected by the ValueSpec itself.
        CaseFail("empty", ""),
        CasePass("ipv4", "10.0.0.1"),
        CasePass("hostname", "host.example.com"),
        CaseFail("wrong-type", 123),
    ],
    "ipv6address": [
        CaseFail("empty", ""),
        CasePass("ipv6", "2001:db8::1"),
        CasePass("hostname", "host.example.com"),
        CaseFail("wrong-type", 123),
    ],
    "management_address": [
        CaseFail("empty", ""),
        CasePass("ipv4", "10.0.0.1"),
        CasePass("hostname", "mgmt.example.com"),
        CaseFail("wrong-type", 123),
    ],
    "labels": [
        CasePass("empty", {}),
        CasePass("single", {"env": "prod"}),
        CasePass("multi", {"os": "linux", "env": "prod"}),
        CaseFail("not-a-dict", "env:prod"),
        CaseFail("value-not-str", {"env": 123}),
    ],
    "management_protocol": [
        CasePass("none", None),
        CasePass("snmp", "snmp"),
        CasePass("ipmi", "ipmi"),
        CaseFail("unknown", "ping"),
        CaseFail("wrong-type", 1),
    ],
    "snmp_community": [
        # Unlike management_snmp_community (allow_none=True), this ValueSpec rejects
        # None even though None is its default value.  It does not reject it cleanly,
        # though: the Password sub-ValueSpec calls .strip() on None and crashes.  The
        # FormSpec rejects None cleanly, so this expectation is expected to change to
        # CaseFail once snmp_community is migrated.
        CaseRaises("none", None, AttributeError),
        CasePass("community", "public"),
        CaseFail("wrong-type", 123),
    ],
    "management_snmp_community": [
        CasePass("none", None),
        CasePass("community", "public"),
        CaseFail("wrong-type", 123),
    ],
    "management_ipmi_credentials": [
        CasePass("none", None),
        CasePass("explicit", {"username": "admin", "password": "secret"}),
        CaseFail("wrong-type", "admin:secret"),
    ],
    "parents": [
        CasePass("empty", []),
        CasePass("single", ["parent1"]),
        CasePass("multi", ["parent1", "parent2"]),
        CaseFail("not-a-list", "parent1"),
        CaseFail("inner-wrong-type", [123]),
    ],
    "locked_attributes": [
        CasePass("empty", []),
        CasePass("single", ["ipaddress"]),
        CasePass("multi", ["ipaddress", "tag_agent"]),
        CaseFail("not-a-list", "ipaddress"),
        CaseFail("unknown-attr", ["does_not_exist"]),
    ],
    "locked_by": [
        CasePass("default", ["NO_SITE", "", ""]),
        CasePass("filled", ["NO_SITE", "dcd", "conn1"]),
        CaseFail("wrong-length", ["NO_SITE", "dcd"]),
        CaseFail("wrong-type", "NO_SITE"),
    ],
    "site": [
        CasePass("no-site", "NO_SITE"),
        CaseFail("unknown", "does_not_exist"),
    ],
    "meta_data": [
        CasePass("created", {"created_at": 1700000000.0, "created_by": "cmkadmin"}),
        CasePass("created-by-none", {"created_at": 1700000000.0, "created_by": None}),
        # The ValueSpec only knows created_at / created_by; extra keys are rejected.
        CaseFail(
            "extra-key",
            {"created_at": 1700000000.0, "created_by": None, "updated_at": 1700000100.0},
        ),
        CaseFail("not-a-dict", "created"),
    ],
    "network_scan_result": [
        CasePass("empty", {"start": None, "end": None, "state": None, "output": ""}),
        CasePass(
            "finished",
            {"start": 1700000000.0, "end": 1700000100.0, "state": True, "output": "done"},
        ),
        CaseFail("not-a-dict", "result"),
    ],
    "network_scan": [
        # The "run_as" key is a DropdownChoice of existing users.  No user exists in
        # the unit-test config, so even the otherwise-default-shaped dict (run_as=None)
        # is rejected.
        CaseFail(
            "run-as-none",
            {
                "ip_ranges": [],
                "exclude_ranges": [],
                "scan_interval": 86400,
                "time_allowed": [((0, 0), (24, 0))],
                "set_ipaddress": True,
                "run_as": None,
            },
        ),
        CaseFail(
            "populated-run-as-none",
            {
                "ip_ranges": [("ip_range", ("10.0.0.1", "10.0.0.10"))],
                "exclude_ranges": [],
                "scan_interval": 3600,
                "time_allowed": [((8, 0), (18, 0))],
                "set_ipaddress": False,
                "run_as": None,
            },
        ),
        CaseFail("not-a-dict", "scan"),
        CaseFail("missing-keys", {}),
    ],
    "tag_address_family": [
        CasePass("v4", "ip-v4-only"),
        CasePass("v4v6", "ip-v4v6"),
        CasePass("v6", "ip-v6-only"),
        CasePass("no-ip", "no-ip"),
        CaseFail("unknown", "foo"),
    ],
    "tag_agent": [
        CasePass("cmk-agent", "cmk-agent"),
        CasePass("all-agents", "all-agents"),
        CasePass("special-agents", "special-agents"),
        CasePass("no-agent", "no-agent"),
        CaseFail("unknown", "foo"),
    ],
    "tag_snmp_ds": [
        CasePass("no-snmp", "no-snmp"),
        CasePass("v1", "snmp-v1"),
        CasePass("v2", "snmp-v2"),
        CaseFail("unknown", "foo"),
    ],
    "tag_piggyback": [
        CasePass("auto", "auto-piggyback"),
        CasePass("piggyback", "piggyback"),
        CasePass("no-piggyback", "no-piggyback"),
        CaseFail("unknown", "foo"),
    ],
}


def _value_spec_attributes() -> dict[str, ABCHostAttributeValueSpec]:
    return {
        name: attr
        for name, attr in all_host_attributes(
            active_config.wato_host_attrs,
            active_config.tags.get_tag_groups_by_topic(),
        ).items()
        if isinstance(attr, ABCHostAttributeValueSpec)
    }


@pytest.fixture(name="value_spec_attributes")
def _fixture_value_spec_attributes(
    load_config: object,
) -> dict[str, ABCHostAttributeValueSpec]:
    return _value_spec_attributes()


@pytest.mark.usefixtures("load_config")
def test_every_value_spec_attribute_has_cases() -> None:
    registered = set(_value_spec_attributes())
    documented = set(CASES)
    assert registered == documented, (
        f"missing cases for: {sorted(registered - documented)}; "
        f"unknown attributes in CASES: {sorted(documented - registered)}"
    )


@pytest.mark.parametrize(
    "attr_name, case",
    [
        pytest.param(name, case, id=f"{name}-{case.id}")
        for name, cases in CASES.items()
        for case in cases
    ],
)
def test_value_spec_value_behavior(
    value_spec_attributes: dict[str, ABCHostAttributeValueSpec],
    attr_name: str,
    case: Case,
) -> None:
    value_spec = value_spec_attributes[attr_name].valuespec()

    match case:
        case CasePass():
            value_spec.validate_datatype(case.value, "")
            value_spec.validate_value(case.value, "")
            assert value_spec.transform_value(case.value) == case.value
        case CaseFail():
            with pytest.raises(MKUserError):
                value_spec.validate_datatype(case.value, "")
                value_spec.validate_value(case.value, "")
        case CaseRaises():
            with pytest.raises(case.exception):
                value_spec.validate_datatype(case.value, "")
                value_spec.validate_value(case.value, "")
