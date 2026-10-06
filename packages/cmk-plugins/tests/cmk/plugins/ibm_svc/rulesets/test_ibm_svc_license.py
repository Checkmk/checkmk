#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.ibm_svc.rulesets.ibm_svc_license import rule_spec_ibm_svc_license


def _migrate(params: object) -> Mapping[str, object]:
    migrate = rule_spec_ibm_svc_license.parameter_form().migrate
    assert migrate is not None, "rule_spec_ibm_svc_license has no migrate wired"
    return migrate(params)


@pytest.mark.parametrize(
    ["params", "expected"],
    [
        pytest.param(
            {"levels": ("absolute", (5, 0))},
            {"levels": ("absolute", {"warn": 5, "crit": 0})},
            id="absolute",
        ),
        pytest.param(
            {"levels": ("percentage", (10.0, 0))},
            {"levels": ("percentage", {"warn": 10.0, "crit": 0.0})},
            id="percentage-with-integer-default",
        ),
        pytest.param(
            {"levels": ("crit_on_all", None)},
            {"levels": ("crit_on_all", None)},
            id="crit-on-all",
        ),
        pytest.param(
            {"levels": ("always_ok", False)},
            {"levels": ("always_ok", None)},
            id="always-ok",
        ),
    ],
)
def test_migrate_legacy_levels(
    params: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    assert _migrate(params) == expected


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"levels": ("absolute", {"warn": 5, "crit": 0})}, id="absolute"),
        pytest.param({"levels": ("percentage", {"warn": 10.0, "crit": 0.0})}, id="percentage"),
        pytest.param({"levels": ("crit_on_all", None)}, id="crit-on-all"),
        pytest.param({"levels": ("always_ok", None)}, id="always-ok"),
    ],
)
def test_migrate_keeps_migrated_levels(params: Mapping[str, object]) -> None:
    assert _migrate(params) == params
