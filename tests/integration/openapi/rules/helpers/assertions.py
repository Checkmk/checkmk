#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Assertion helper functions for tests against rules with predictive and fixed levels."""


def assert_predictive_levels_structure(
    stored_value: str, expected_checks: list[str] | None = None
) -> None:
    """Assert predictive levels structure is present."""
    required_elements = [
        "cmk_postprocessed",
        "predictive_levels",
        "__reference_metric__",
        "__direction__",
    ]
    for element in required_elements:
        assert element in stored_value, f"Rule should contain {element}"

    if expected_checks:
        for check in expected_checks:
            assert check in stored_value, f"Should contain: {check}"


def assert_fixed_levels_structure(stored_value: str, expected_checks: list[str]) -> None:
    """Assert fixed levels structure is present."""
    assert "fixed" in stored_value, "Should contain 'fixed'"
    for check in expected_checks:
        assert check in stored_value, f"Should contain: {check}"
