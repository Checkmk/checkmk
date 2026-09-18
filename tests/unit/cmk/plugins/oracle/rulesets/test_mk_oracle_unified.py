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
    _oracle_id,
    SECTIONS,
    SYNC_ONLY_SECTIONS,
    USE_HOST_CLIENT_PATH_RE,
)
from cmk.rulesets.internal.form_specs import (
    DictionaryExtended,
    ListOfStrings,
)
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    DictElement,
    Dictionary,
    FixedValue,
    FormSpec,
    List,
    Password,
    SingleChoice,
    String,
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

_INSTANCES = [
    {"oracle_id": ("descriptor", {"service_name": "orcl"}), "piggyback_host": "orcl.example"},
    {"oracle_id": ("alias", {"alias": "PROD"})},
]

# What the form wrote before the revision.
OLD_RULE: Mapping[str, object] = {
    "deploy": ("deploy", None),
    "options": {
        "ignore_db_name": False,
        "oracle_client_library": {"use_host_client": ("custom", "$ORACLE_HOME/lib")},
    },
    "main": _SHARED,
    "instances": _INSTANCES,
}

CURRENT_RULE: Mapping[str, object] = {
    "deploy_rev2": "deploy",
    "options": {"ignore_db_name": False, "use_host_client": ("custom", "$ORACLE_HOME/lib")},
    "instances_rev2": [
        {"oracle_id": ("descriptor", {"service_name": "orcl"}), "piggyback_host": "orcl.example"},
        {"oracle_id": ("alias", "PROD")},
    ],
    **_SHARED,
    "discovery": {"enabled": "enabled", "include": ["ORCL"]},
    "sections": {"tablespaces": True, "locks": False},
    "excluded_sections": [{"target_id": ("sid", "XE"), "sections": ["rman"]}],
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


def test_migrate_drops_an_entry_that_names_no_database() -> None:
    # The bakery dropped these silently, so a rule can carry one.
    old = {**OLD_RULE, "instances": [{"oracle_id": ("sid", {})}, *_INSTANCES]}
    assert _migrate(old)["instances_rev2"] == CURRENT_RULE["instances_rev2"]


def test_an_alias_or_sid_is_offered_as_the_string_it_is() -> None:
    by_name = {choice.name: choice.parameter_form for choice in _oracle_id().elements}
    assert isinstance(by_name["alias"], String)
    assert isinstance(by_name["sid"], String)
    assert isinstance(by_name["descriptor"], Dictionary), "three fields, so it stays a dictionary"


def test_an_empty_database_list_points_at_instance_discovery() -> None:
    instances = _agent_config_mk_oracle().elements["instances_rev2"].parameter_form
    assert isinstance(instances, List)
    assert "discovery" in instances.no_element_label.localize(str).lower()


@pytest.mark.usefixtures("registered_visitors")
def test_a_cache_age_reaches_the_bakery_as_an_integer() -> None:
    # TimeSpan works in floats, so rules.mk holds 900.0 where it used to hold
    # 900. The bakery parses through StoredConfig, which coerces it back.
    visitor = get_visitor(
        _agent_config_mk_oracle(), VisitorOptions(migrate_values=True, mask_values=False)
    )
    stored = visitor.to_disk(RawDiskData(CURRENT_RULE))
    assert isinstance(stored, Mapping)
    assert type(stored["cache_age"]) is float
    assert type(StoredConfig.model_validate(stored).cache_age) is int


def test_discovery_is_offered_as_a_choice() -> None:
    discovery = _agent_config_mk_oracle().elements["discovery"].parameter_form
    assert isinstance(discovery, Dictionary)
    assert isinstance(discovery.elements["enabled"].parameter_form, SingleChoice)


def test_the_client_library_is_offered_flat() -> None:
    options_form = _agent_config_mk_oracle().elements["options"].parameter_form
    assert isinstance(options_form, Dictionary)
    assert "use_host_client" in options_form.elements
    assert "oracle_client_library" not in options_form.elements


def test_an_empty_client_library_block_names_no_client() -> None:
    migrated = _migrate({**OLD_RULE, "options": {"oracle_client_library": {}}})
    assert migrated["options"] == {}


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


def test_every_checkbox_and_fixed_value_renders_something() -> None:
    # The rule summary renders a FixedValue as its label, falling back to its
    # value, so a value of None without a label leaves the row empty. A
    # BooleanChoice without a label renders a checkbox with nothing beside it.
    empty = [
        form_spec
        for form_spec in _walk(_agent_config_mk_oracle())
        if (
            isinstance(form_spec, FixedValue)
            and form_spec.value is None
            and form_spec.label is None
        )
        or (isinstance(form_spec, BooleanChoice) and form_spec.label is None)
    ]
    assert not empty


def test_the_form_declares_max_connections_as_ignored() -> None:
    options_form = _agent_config_mk_oracle().elements["options"].parameter_form
    assert isinstance(options_form, Dictionary)
    assert "max_connections" in options_form.ignored_elements


def test_the_string_lists_are_offered_as_one_line_each() -> None:
    discovery = _agent_config_mk_oracle().elements["discovery"].parameter_form
    assert isinstance(discovery, Dictionary)
    for key in ("include", "exclude"):
        assert isinstance(discovery.elements[key].parameter_form, ListOfStrings)


def _section_elements() -> Mapping[str, DictElement[object]]:
    sections = _agent_config_mk_oracle().elements["sections"].parameter_form
    assert isinstance(sections, Dictionary)
    return sections.elements


@pytest.mark.parametrize("section", ["instance", "asm_instance"])
def test_the_sections_that_have_no_choice_are_not_offered(section: str) -> None:
    assert section not in _section_elements()


def test_every_configurable_section_is_offered() -> None:
    offered = _section_elements()
    assert {section.section for section in SECTIONS} - set(offered) == set(SYNC_ONLY_SECTIONS)


def test_a_section_is_a_labelled_checkbox_that_is_on_by_default() -> None:
    sections = _agent_config_mk_oracle().elements["sections"].parameter_form
    assert isinstance(sections, DictionaryExtended)
    cached = sections.elements["tablespaces"].parameter_form
    assert isinstance(cached, BooleanChoice)
    assert cached.label is not None, "an unlabelled checkbox renders bare"
    assert not sections.elements["tablespaces"].required, "unchecked means not collected"
    assert "tablespaces" in (sections.default_checked or [])


def test_a_section_that_defaults_to_off_is_not_checked() -> None:
    sections = _agent_config_mk_oracle().elements["sections"].parameter_form
    assert isinstance(sections, DictionaryExtended)
    assert "iostats" not in (sections.default_checked or [])


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
