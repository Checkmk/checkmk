#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import re
from collections.abc import Iterator
from typing import Any

import pytest

from cmk.plugins.oracle.rulesets.mk_oracle_unified import (
    _agent_config_mk_oracle,
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
    SingleChoice,
)


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
    main = _agent_config_mk_oracle().elements["main"].parameter_form
    assert isinstance(main, Dictionary)
    discovery = main.elements["discovery"].parameter_form
    assert isinstance(discovery, Dictionary)
    for key in ("include", "exclude"):
        assert isinstance(discovery.elements[key].parameter_form, ListOfStrings)


def test_options_is_top_level() -> None:
    # `options` is a top-level GUI section; the bakery routes it into `oracle.main.options`
    form = _agent_config_mk_oracle()
    assert "options" in form.elements, "`options` must be a top-level element"
    main_form = form.elements["main"].parameter_form
    assert isinstance(main_form, Dictionary)
    assert "options" not in main_form.elements, "`options` must not be nested under `main`"


@pytest.mark.parametrize("section", ["instance", "asm_instance"])
def test_instance_sections_offer_synchronous_only(section: str) -> None:
    main = _agent_config_mk_oracle().elements["main"].parameter_form
    assert isinstance(main, Dictionary)
    sections = main.elements["sections"].parameter_form
    assert isinstance(sections, Dictionary)
    modes = sections.elements[section].parameter_form
    assert isinstance(modes, SingleChoice)

    assert [element.name for element in modes.elements] == ["synchronous"]


def test_other_sections_offer_all_modes() -> None:
    main = _agent_config_mk_oracle().elements["main"].parameter_form
    assert isinstance(main, Dictionary)
    sections = main.elements["sections"].parameter_form
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
