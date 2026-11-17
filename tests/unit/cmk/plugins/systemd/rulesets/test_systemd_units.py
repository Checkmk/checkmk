#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.gui.form_specs import get_visitor, RawDiskData, registration, VisitorOptions
from cmk.plugins.systemd.rulesets.systemd_units import (
    _migrate_to_label_list,
    _migrate_unit_not_found_key,
    rule_spec_discovery_systemd_units_services,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(
            {"else": 1, "cpu_time": (1.0, 2.0)},
            {"unit_not_found": 1, "cpu_time": (1.0, 2.0)},
            id="legacy else key",
        ),
        pytest.param(
            {"unit_not_found": 1, "cpu_time": ("fixed", (1.0, 2.0))},
            {"unit_not_found": 1, "cpu_time": ("fixed", (1.0, 2.0))},
            id="already migrated",
        ),
    ],
)
def test_migrate_unit_not_found_key(value: object, expected: dict[str, object]) -> None:
    assert _migrate_unit_not_found_key(value) == expected


@pytest.fixture
def _register_form_spec_visitors() -> None:
    registration.register()


def _validate(rule: Mapping[str, object]) -> Sequence[object]:
    return get_visitor(
        rule_spec_discovery_systemd_units_services.parameter_form(),
        VisitorOptions(migrate_values=True, mask_values=False),
    ).validate(RawDiskData(rule))


def _migrate(rule: Mapping[str, object]) -> object:
    return get_visitor(
        rule_spec_discovery_systemd_units_services.parameter_form(),
        VisitorOptions(migrate_values=True, mask_values=False),
    ).to_disk(RawDiskData(rule))


@pytest.mark.usefixtures("_register_form_spec_visitors")
@pytest.mark.parametrize(
    "stored, expected",
    [
        pytest.param("sshd.service", {"match": "exact", "pattern": "sshd.service"}, id="text"),
        pytest.param("~ssh.*", {"match": "regex", "pattern": "ssh.*"}, id="regex"),
    ],
)
def test_legacy_name_condition_is_migrated(stored: str, expected: Mapping[str, str]) -> None:
    assert _migrate({"names": [stored]}) == {"names": [expected]}


@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_legacy_automatic_host_labels_flag_is_migrated() -> None:
    assert _migrate({"host_labels_auto": True}) == {"host_labels_auto": None}


@pytest.mark.usefixtures("_register_form_spec_visitors")
@pytest.mark.parametrize("match", ["exact", "regex"])
def test_empty_pattern_is_rejected(match: str) -> None:
    rule = {"names": [{"match": match, "pattern": ""}]}

    assert _validate(rule)


@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_invalid_regex_is_rejected() -> None:
    rule = {"names": [{"match": "regex", "pattern": "ssh("}]}

    assert _validate(rule)


@pytest.mark.usefixtures("_register_form_spec_visitors")
def test_invalid_regex_is_accepted_as_explicit_text() -> None:
    rule = {"names": [{"match": "exact", "pattern": "ssh("}]}

    assert not _validate(rule)


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(
            {"role": "webserver", "tier": "1"},
            [{"key": "role", "value": "webserver"}, {"key": "tier", "value": "1"}],
            id="legacy labels",
        ),
        pytest.param(
            [{"key": "role", "value": "webserver"}],
            [{"key": "role", "value": "webserver"}],
            id="already migrated",
        ),
    ],
)
def test_migrate_to_label_list(value: object, expected: Sequence[Mapping[str, object]]) -> None:
    assert _migrate_to_label_list(value) == expected
