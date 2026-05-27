#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.azure_deprecated.rulesets.azure_usagedetails import (
    rule_spec_azure_usagedetails,
)


def _migrate(params: object) -> Mapping[str, object]:
    migrate = rule_spec_azure_usagedetails.parameter_form().migrate
    assert migrate is not None, "rule_spec_azure_usagedetails has no migrate wired"
    return migrate(params)


@pytest.mark.parametrize(
    ["params", "expected"],
    [
        pytest.param(
            {"levels": (0.1, 0.2)},
            {"costs": ("fixed", (0.1, 0.2))},
            id="legacy-tuple-levels",
        ),
        pytest.param(
            {"levels": None},
            {"costs": ("no_levels", None)},
            id="legacy-none-levels",
        ),
    ],
)
def test_migrate_params_legacy_levels(
    params: Mapping[str, object], expected: Mapping[str, object]
) -> None:
    assert _migrate(params) == expected


def test_migrate_params_already_migrated() -> None:
    params = {"costs": ("fixed", (0.1, 0.2))}
    assert _migrate(params) == params


def test_migrate_params_empty_list() -> None:
    assert _migrate({}) == {}
