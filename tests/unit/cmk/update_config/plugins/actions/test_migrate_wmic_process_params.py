#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from logging import getLogger

import pytest

from cmk.ccc.version import Edition
from cmk.checkengine.specs.parameters import (
    TimespecificParameters,
    TimespecificParameterSet,
)
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.rule_specs.legacy_converter import convert_to_legacy_rulespec
from cmk.gui.watolib.hosts_and_folders import FolderTree
from cmk.gui.watolib.rulesets import Rule, Ruleset, RulesetCollection
from cmk.plugins.windows.agent_based.wmic_process import check_plugin_wmic_process
from cmk.plugins.windows.rulesets.wmic_process import rule_spec_wmic_process
from cmk.update_config.plugins.actions.migrate_wmic_process_params import (
    migrate_rules,
    migrated_parameters,
)

_MIGRATED = {
    "name": "notepad.exe",
    "mem_levels": ("fixed", (100.0, 200.0)),
    "page_levels": ("fixed", (50.0, 100.0)),
    "cpu_levels": ("fixed", (80.0, 90.0)),
}


@pytest.mark.parametrize(
    "legacy, expected",
    [
        pytest.param(
            ("notepad.exe", 100, 200, 50, 100, 80.0, 90.0),
            _MIGRATED,
            id="positional_tuple",
        ),
        pytest.param(
            ("notepad.exe", 0, 0, 0, 0, 0.0, 0.0),
            {
                "name": "notepad.exe",
                "mem_levels": ("no_levels", None),
                "page_levels": ("no_levels", None),
                "cpu_levels": ("no_levels", None),
            },
            id="zeros_mean_no_levels",
        ),
        pytest.param(
            ("notepad.exe", 0, 200, 50, 0, 0.0, 90.0),
            {
                "name": "notepad.exe",
                "mem_levels": ("fixed", (200.0, 200.0)),
                "page_levels": ("fixed", (50.0, 50.0)),
                "cpu_levels": ("fixed", (90.0, 90.0)),
            },
            id="a_disabled_bound_collapses_onto_the_active_one",
        ),
    ],
)
def test_migrated_parameters(legacy: object, expected: dict[str, object]) -> None:
    assert migrated_parameters(legacy) == expected


@pytest.mark.parametrize(
    "unchanged",
    [
        pytest.param(_MIGRATED, id="already_migrated"),
        pytest.param(("notepad.exe", 100, 200), id="too_short"),
        pytest.param((100, 100, 200, 50, 100, 80.0, 90.0), id="name_not_a_string"),
        pytest.param(("notepad.exe", "100", 200, 50, 100, 80.0, 90.0), id="level_not_a_number"),
    ],
)
def test_migrated_parameters_leaves_unexpected_values_alone(unchanged: object) -> None:
    assert migrated_parameters(unchanged) is None


def test_migrated_parameters_are_accepted_by_the_check_engine() -> None:
    migrated = migrated_parameters(("notepad.exe", 100, 200, 50, 100, 80.0, 90.0))
    assert migrated is not None

    # This is what compute_enforced_service_parameters builds for an enforced service.
    effective = TimespecificParameters(
        [
            TimespecificParameterSet.from_parameters(migrated),
            TimespecificParameterSet.from_parameters(
                check_plugin_wmic_process.check_default_parameters or {}
            ),
        ]
    ).evaluate(lambda _timeperiod: False)

    assert effective == _MIGRATED


def test_migrated_parameters_are_accepted_by_the_ruleset() -> None:
    """The rewritten value has to survive the form spec, not just the check engine.

    The check engine merges whatever it is given, so only the ruleset notices a
    misspelled key or level tag -- and by then the rules have been written to disk.
    """
    migrated = migrated_parameters(("notepad.exe", 100, 200, 50, 100, 80.0, 90.0))
    assert migrated is not None

    # An enforced service may come without parameters, so the form is optional.
    parameter_form = rule_spec_wmic_process.parameter_form
    assert parameter_form is not None

    visitor = get_visitor(
        parameter_form(),
        VisitorOptions(migrate_values=False, mask_values=False),
    )

    assert not visitor.validate(RawDiskData(migrated))


def _ruleset_holding(tree: FolderTree, value: object) -> Ruleset:
    rulespec = convert_to_legacy_rulespec(rule_spec_wmic_process, Edition.COMMUNITY, lambda s: s)
    ruleset = Ruleset(rulespec.name, rulespec=rulespec)
    folder = tree.root_folder()
    ruleset.append_rule(folder, Rule.from_ruleset(folder, ruleset, value))
    return ruleset


def test_the_stored_parameters_of_an_enforced_service_are_rewritten(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    tree: FolderTree,
) -> None:
    ruleset = _ruleset_holding(
        tree, ("wmic_process", "notepad", ("notepad.exe", 100, 200, 50, 100, 80.0, 90.0))
    )

    n_migrated = migrate_rules(RulesetCollection({ruleset.name: ruleset}), getLogger())

    assert n_migrated == 1
    assert ruleset.get_rules()[0][2].value == ("wmic_process", "notepad", _MIGRATED)


def test_an_already_migrated_rule_is_left_untouched(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    tree: FolderTree,
) -> None:
    stored = ("wmic_process", "notepad", _MIGRATED)
    ruleset = _ruleset_holding(tree, stored)

    n_migrated = migrate_rules(RulesetCollection({ruleset.name: ruleset}), getLogger())

    assert n_migrated == 0
    assert ruleset.get_rules()[0][2].value == stored


def test_a_rule_we_cannot_migrate_is_reported_and_left_untouched(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    tree: FolderTree,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A value we do not understand must reach the user, not be dropped silently."""
    stored = ("wmic_process", "notepad", ("notepad.exe", "100", 200, 50, 100, 80.0, 90.0))
    ruleset = _ruleset_holding(tree, stored)

    with caplog.at_level(logging.WARNING):
        n_migrated = migrate_rules(RulesetCollection({ruleset.name: ruleset}), getLogger())

    assert n_migrated == 0
    assert ruleset.get_rules()[0][2].value == stored
    assert "Cannot migrate rule" in caplog.text


def test_time_specific_parameters_are_reported_rather_than_migrated(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    tree: FolderTree,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """We do not migrate these, but the user has to learn that we did not."""
    legacy = ("notepad.exe", 100, 200, 50, 100, 80.0, 90.0)
    stored = (
        "wmic_process",
        "notepad",
        {"tp_default_value": legacy, "tp_values": [("night", legacy)]},
    )
    ruleset = _ruleset_holding(tree, stored)

    with caplog.at_level(logging.WARNING):
        n_migrated = migrate_rules(RulesetCollection({ruleset.name: ruleset}), getLogger())

    assert n_migrated == 0
    assert ruleset.get_rules()[0][2].value == stored
    assert "Cannot migrate rule" in caplog.text
