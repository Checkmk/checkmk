#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.vsphere.lib.special_agent import QueryType
from cmk.plugins.vsphere.rulesets.special_agent import rule_spec_special_agent_vsphere
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    DefaultValue,
    Dictionary,
    MultipleChoice,
    SingleChoice,
)

HOST_SYSTEM_INFOS = ["hostsystem", "counters"]
VCENTER_INFOS = ["hostsystem", "virtualmachine", "datastore", "counters"]


def _form() -> Dictionary:
    return rule_spec_special_agent_vsphere.parameter_form()


def _migrate(value: Mapping[str, object]) -> Mapping[str, object]:
    migrate = _form().migrate
    assert migrate is not None
    return migrate(dict(value))


def _migrate_ssl(value: object) -> object:
    ssl_form = _form().elements["ssl"].parameter_form
    assert isinstance(ssl_form, CascadingSingleChoice)
    assert ssl_form.migrate is not None
    return ssl_form.migrate(value)


def _migrate_power_display(element: str, value: object) -> object:
    display_form = _form().elements[element].parameter_form
    assert isinstance(display_form, SingleChoice)
    assert display_form.migrate is not None
    return display_form.migrate(value)


def _preselected_infos(query_type: QueryType) -> object:
    query_form = _form().elements["direct"].parameter_form
    assert isinstance(query_form, CascadingSingleChoice)
    info_form = next(e.parameter_form for e in query_form.elements if e.name == query_type)
    assert isinstance(info_form, MultipleChoice)
    assert isinstance(info_form.prefill, DefaultValue)
    return info_form.prefill.value


def test_legacy_direct_flag_becomes_a_host_system_query_with_its_default_infos() -> None:
    migrated = _migrate({"direct": True})

    assert migrated["direct"] == (QueryType.HOST_SYSTEM, HOST_SYSTEM_INFOS)


def test_legacy_vcenter_flag_becomes_a_vcenter_query_with_its_default_infos() -> None:
    migrated = _migrate({"direct": False})

    assert migrated["direct"] == (QueryType.VCENTER, VCENTER_INFOS)


def test_legacy_info_selection_moves_into_the_query_type() -> None:
    migrated = _migrate({"direct": True, "infos": ["licenses"]})

    assert migrated["direct"] == (QueryType.HOST_SYSTEM, ["licenses"])
    assert "infos" not in migrated


def test_query_type_given_as_string_is_converted_to_the_enum() -> None:
    migrated = _migrate({"direct": "standalone", "infos": ["datastore"]})

    assert migrated["direct"] == (QueryType.STANDALONE, ["datastore"])


def test_query_type_given_as_enum_keeps_the_selected_infos() -> None:
    migrated = _migrate({"direct": QueryType.VCENTER, "infos": ["licenses"]})

    assert migrated["direct"] == (QueryType.VCENTER, ["licenses"])


def test_migrated_query_type_is_left_unchanged() -> None:
    value = {"direct": (QueryType.VCENTER, ["hostsystem"]), "user": "monitoring"}

    assert _migrate(_migrate(value)) == value


def test_disabled_certificate_check_is_migrated() -> None:
    assert _migrate_ssl(False) == ("deactivated", None)


def test_certificate_check_against_the_host_name_is_migrated() -> None:
    assert _migrate_ssl(True) == ("hostname", None)


def test_certificate_check_against_a_custom_name_is_migrated() -> None:
    assert _migrate_ssl("vcenter.example.com") == ("custom_hostname", "vcenter.example.com")


def test_migrated_ssl_setting_is_left_unchanged() -> None:
    assert _migrate_ssl(("hostname", None)) == ("hostname", None)


def test_unexpected_ssl_setting_is_rejected() -> None:
    with pytest.raises(TypeError):
        _migrate_ssl(443)


def test_unset_power_state_displays_default_to_the_queried_system() -> None:
    assert _migrate_power_display("host_pwr_display", None) == "host"
    assert _migrate_power_display("vm_pwr_display", None) == "host"


def test_configured_power_state_displays_are_kept() -> None:
    assert _migrate_power_display("host_pwr_display", "esxhost") == "esxhost"
    assert _migrate_power_display("vm_pwr_display", "vm") == "vm"


def test_host_system_queries_preselect_host_and_counter_infos() -> None:
    assert _preselected_infos(QueryType.HOST_SYSTEM) == HOST_SYSTEM_INFOS


def test_vcenter_and_standalone_queries_preselect_everything_but_licenses() -> None:
    assert _preselected_infos(QueryType.VCENTER) == VCENTER_INFOS
    assert _preselected_infos(QueryType.STANDALONE) == VCENTER_INFOS
