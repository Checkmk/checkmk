#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import re
from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.form_specs.registration import register_form_specs
from cmk.gui.form_specs.visitors import register_visitor_class
from cmk.gui.watolib.password_visitor import PasswordVisitor
from cmk.plugins.oracle.lib.unified_config import StoredConfig
from cmk.plugins.oracle.rulesets.mk_oracle_unified import (
    _agent_config_mk_oracle,
    _migrate,
    USE_HOST_CLIENT_PATH_RE,
)
from cmk.rulesets.internal.form_specs import (
    ListOfStrings,
)
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    Dictionary,
    FixedValue,
    FormSpec,
    List,
    Password,
    SingleChoice,
)

PASSWORD = ("cmk_postprocessed", "explicit_password", ("uuid", "secret"))

_SHARED: Mapping[str, object] = {
    "auth": {
        "auth_type": ("standard", {"username": "monitor", "password": PASSWORD}),
        "role": "sysdba",
    },
    "connection": {"host": "db1.example.com", "port": 1521},
    "cache_age": 900,
    "custom_metrics_cache_age": 1200,
    "discovery": {"enabled": True, "include": ["ORCL"]},
    "sections": {"tablespaces": "asynchronous", "locks": "synchronous"},
    "excluded_sections": [{"target_id": ("sid", {"sid": "XE"}), "sections": ["rman"]}],
}

# What the form wrote before the revision.
OLD_RULE: Mapping[str, object] = {
    "deploy": ("deploy", None),
    "options": {"ignore_db_name": False},
    "main": _SHARED,
    "instances": [{"oracle_id": ("alias", {"alias": "PROD"})}],
}

CURRENT_RULE: Mapping[str, object] = {
    "deploy_rev2": "deploy",
    "options": {"ignore_db_name": False},
    "instances": [{"oracle_id": ("alias", {"alias": "PROD"})}],
    **_SHARED,
}


@pytest.fixture(name="registered_visitors")
def _registered_visitors() -> None:
    register_form_specs()
    # The Password visitor is registered by cmk.gui.watolib, which this suite does not load.
    register_visitor_class(Password, PasswordVisitor)


def test_migrate_maps_the_old_rule_onto_the_current_shape() -> None:
    assert _migrate(OLD_RULE) == CURRENT_RULE


def test_migrate_leaves_a_current_rule_alone() -> None:
    assert _migrate(CURRENT_RULE) == CURRENT_RULE


@pytest.mark.usefixtures("registered_visitors")
def test_the_migrated_rule_is_what_the_form_stores() -> None:
    visitor = get_visitor(
        _agent_config_mk_oracle(), VisitorOptions(migrate_values=True, mask_values=False)
    )
    assert visitor.to_disk(RawDiskData(OLD_RULE)) == CURRENT_RULE
    assert visitor.to_disk(RawDiskData(CURRENT_RULE)) == CURRENT_RULE


def test_the_current_rule_parses_as_the_stored_model() -> None:
    parsed = StoredConfig.model_validate(CURRENT_RULE)
    assert parsed.model_dump(mode="python", exclude_unset=True) == CURRENT_RULE


def test_deploy_is_offered_as_a_choice() -> None:
    deploy = _agent_config_mk_oracle().elements["deploy_rev2"].parameter_form
    assert isinstance(deploy, SingleChoice)


def test_the_form_shows_no_main_container() -> None:
    assert "main" not in _agent_config_mk_oracle().elements


def _walk(form_spec: FormSpec[Any]) -> Iterator[FormSpec[Any]]:
    yield form_spec
    match form_spec:
        case Dictionary():
            for element in form_spec.elements.values():
                yield from _walk(element.parameter_form)
        case CascadingSingleChoice():
            for choice in form_spec.elements:
                yield from _walk(choice.parameter_form)
        case List():
            yield from _walk(form_spec.element_template)
        case _:
            pass


def test_every_fixed_value_renders_something() -> None:
    # The rule summary renders a FixedValue as its label, falling back to its
    # value, so a value of None without a label leaves the row empty.
    empty = [
        form_spec
        for form_spec in _walk(_agent_config_mk_oracle())
        if isinstance(form_spec, FixedValue) and form_spec.value is None and form_spec.label is None
    ]
    assert not empty


def test_an_empty_database_list_points_at_instance_discovery() -> None:
    instances = _agent_config_mk_oracle().elements["instances"].parameter_form
    assert isinstance(instances, List)
    assert "discovery" in instances.no_element_label.localize(str).lower()


def test_the_form_declares_max_connections_as_ignored() -> None:
    options_form = _agent_config_mk_oracle().elements["options"].parameter_form
    assert isinstance(options_form, Dictionary)
    assert "max_connections" in options_form.ignored_elements


def test_the_string_lists_are_offered_as_one_line_each() -> None:
    discovery = _agent_config_mk_oracle().elements["discovery"].parameter_form
    assert isinstance(discovery, Dictionary)
    for key in ("include", "exclude"):
        assert isinstance(discovery.elements[key].parameter_form, ListOfStrings)


@pytest.mark.parametrize("section", ["instance", "asm_instance"])
def test_instance_sections_offer_synchronous_only(section: str) -> None:
    sections = _agent_config_mk_oracle().elements["sections"].parameter_form
    assert isinstance(sections, Dictionary)
    modes = sections.elements[section].parameter_form
    assert isinstance(modes, SingleChoice)

    assert [element.name for element in modes.elements] == ["synchronous"]


def test_other_sections_offer_all_modes() -> None:
    sections = _agent_config_mk_oracle().elements["sections"].parameter_form
    assert isinstance(sections, Dictionary)
    modes = sections.elements["tablespaces"].parameter_form
    assert isinstance(modes, SingleChoice)

    assert [element.name for element in modes.elements] == [
        "synchronous",
        "asynchronous",
        "disabled",
    ]


@pytest.mark.parametrize(
    "value",
    [
        "/usr/lib/oracle",
        "/usr/lib/oracle/21/client64/lib",
        "$OCI_DIR/lib",
        "${OCI_DIR}/lib",
        "C:/oracle/client",
        "C:\\oracle\\client",
        "D:\\oracle\\product\\19c",
    ],
)
def test_use_host_client_path_regex_accepts_valid(value: str) -> None:
    assert re.match(USE_HOST_CLIENT_PATH_RE, value), f"Expected {value!r} to be accepted"


@pytest.mark.parametrize(
    "value",
    [
        "",  # empty
        "$",  # bare dollar — no variable name
        "relative/path",
        "oracle/lib",
        "1:\\bad_drive",  # invalid Windows drive letter
    ],
)
def test_use_host_client_path_regex_rejects_invalid(value: str) -> None:
    assert not re.match(USE_HOST_CLIENT_PATH_RE, value), f"Expected {value!r} to be rejected"
