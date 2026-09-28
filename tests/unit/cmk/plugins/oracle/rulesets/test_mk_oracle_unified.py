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
    _connection_options,
    _instances,
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
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    DictElement,
    DictGroup,
    Dictionary,
    FixedValue,
    FormSpec,
    List,
    Password,
    SingleChoice,
    String,
)

PASSWORD = ("cmk_postprocessed", "explicit_password", ("uuid", "secret"))

_AUTH: Mapping[str, object] = {
    "auth_type": ("standard", {"username": "monitor", "password": PASSWORD}),
    "role": "sysdba",
}

# What the form wrote before the revision.
OLD_RULE: Mapping[str, object] = {
    "deploy": ("deploy", None),
    "options": {
        "ignore_db_name": False,
        "oracle_client_library": {"use_host_client": ("custom", "$ORACLE_HOME/lib")},
    },
    "main": {
        "auth": _AUTH,
        "connection": {"host": "db1.example.com", "port": 1521, "tns_admin": "/etc/oracle"},
        "cache_age": 900,
        "discovery": {"enabled": True, "include": ["ORCL"]},
        "sections": {"tablespaces": "asynchronous", "locks": "synchronous"},
        "excluded_sections": [{"target_id": ("sid", {"sid": "XE"}), "sections": ["rman"]}],
    },
    "instances": [
        {"oracle_id": ("descriptor", {"service_name": "orcl"}), "piggyback_host": "orcl.example"},
        {"oracle_id": ("alias", {"alias": "PROD"})},
    ],
}

CURRENT_RULE: Mapping[str, object] = {
    "deploy_rev2": "deploy",
    "ignore_db_name": False,
    "use_host_client": ("custom", "$ORACLE_HOME/lib"),
    "auth": _AUTH,
    "connection": {"host": "db1.example.com", "port": 1521},
    "tns_admin": "/etc/oracle",
    "cache_age": 900,
    "discovery": {"enabled": "enabled", "include": ["ORCL"]},
    "sections": {"tablespaces": True, "locks": False},
    "excluded_sections": [{"target_id": ("sid", "XE"), "sections": ["rman"]}],
    "instances_rev2": [
        {"oracle_id": ("descriptor", {"service_name": "orcl"}), "piggyback_host": "orcl.example"},
        {"oracle_id": ("alias", "PROD")},
    ],
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
    instances = OLD_RULE["instances"]
    assert isinstance(instances, list)
    old = {**OLD_RULE, "instances": [{"oracle_id": ("sid", {})}, *instances]}
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
    elements = _agent_config_mk_oracle().elements
    assert "use_host_client" in elements
    assert "oracle_client_library" not in elements


def test_an_empty_client_library_block_names_no_client() -> None:
    migrated = _migrate({**OLD_RULE, "options": {"oracle_client_library": {}}})
    assert "use_host_client" not in migrated


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


def test_the_form_groups_the_top_level_by_topic() -> None:
    titles = [
        element.group.title
        for element in _agent_config_mk_oracle().elements.values()
        if isinstance(element.group, DictGroup) and element.group.title is not None
    ]
    # Order matters: a group appears where its first element does.
    assert list(dict.fromkeys(titles)) == [
        Title("Activation"),
        Title("Instances to monitor"),
        Title("Standard settings for all instances"),
        Title("Monitoring options"),
        Title("Oracle client options"),
        Title("Plug-in behavior"),
    ]


def test_every_top_level_entry_sits_under_a_heading() -> None:
    # An ungrouped element would silently jump to the top of the rule summary.
    ungrouped = [
        key
        for key, element in _agent_config_mk_oracle().elements.items()
        if not isinstance(element.group, DictGroup)
    ]
    assert not ungrouped


def _database_entry() -> Dictionary:
    instances = _agent_config_mk_oracle().elements["instances_rev2"].parameter_form
    assert isinstance(instances, List)
    entry = instances.element_template
    assert isinstance(entry, Dictionary)
    return entry


def test_a_database_entry_marks_its_overrides_as_such() -> None:
    entry = _database_entry()
    for key in ("auth", "connection"):
        group = entry.elements[key].group
        assert isinstance(group, DictGroup)
        assert group.title == Title("Instance-specific settings")


def test_a_database_entry_keeps_the_piggyback_host_out_of_the_overrides() -> None:
    # An entry that follows a group without naming one of its own renders
    # inside that group's box, under a heading that does not describe it.
    group = _database_entry().elements["piggyback_host"].group
    assert isinstance(group, DictGroup)
    assert group.title == Title("Monitoring")


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
    assert "max_connections" in _agent_config_mk_oracle().ignored_elements


def test_the_oracle_file_paths_are_offered_once_and_not_per_database() -> None:
    # The plug-in sets TNS_ADMIN process wide and picks the client from one Grid
    # home, so neither path means anything per database.
    elements = _agent_config_mk_oracle().elements
    assert {"tns_admin", "oracle_local_registry"} <= set(elements)
    for form in (_connection_options(), _instances().element_template):
        assert isinstance(form, Dictionary)
        assert not {"tns_admin", "oracle_local_registry"} & set(form.elements)


def test_no_top_level_entry_is_required() -> None:
    # A required entry is stored by every rule, so only the most specific rule
    # could ever set it. The merged value is what has to be complete, and the
    # bakery says so when it is not.
    form = _agent_config_mk_oracle()
    assert not [key for key, element in form.elements.items() if element.required]
    assert isinstance(form, DictionaryExtended)
    assert form.default_checked == ["deploy_rev2", "auth"]


def test_every_setting_that_stands_alone_merges_on_its_own_key() -> None:
    # Two rules merge on the top-level keys they store, so a setting nested one
    # level deeper can only be overridden together with its neighbours.
    elements = _agent_config_mk_oracle().elements
    assert {"ignore_db_name", "use_host_client", "validate_permissions"} <= set(elements)
    assert "options" not in elements


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
