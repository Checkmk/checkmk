#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.plugins.ibm_mq.rulesets.ibm_mq_plugin import rule_spec_ibm_mq_plugin
from cmk.rulesets.v1.form_specs import Dictionary


def _migrate_version(version: object) -> object:
    form = rule_spec_ibm_mq_plugin.parameter_form()
    assert isinstance(form, Dictionary)
    assert (migrate := form.elements["version"].parameter_form.migrate) is not None
    return migrate(version)


# fmt: off
@pytest.mark.parametrize(
    "version, expected",
    [
        pytest.param((("at_least", "2.0"), 1), ("at_least", {"version": "2.0", "state": 1}), id="at least"),
        pytest.param((("specific", "9.1"), 2), ("specific", {"version": "9.1", "state": 2}), id="specific"),
    ],
)
# fmt: on
def test_version_check_keeps_its_comparison_version_and_state(
    version: object, expected: object
) -> None:
    assert _migrate_version(version) == expected


@pytest.mark.parametrize(
    "version",
    [
        pytest.param(("any", None), id="any version"),
        pytest.param(("at_least", {"version": "2.0", "state": 1}), id="at least"),
    ],
)
def test_migrated_version_check_stays_unchanged(version: object) -> None:
    assert _migrate_version(version) == version
