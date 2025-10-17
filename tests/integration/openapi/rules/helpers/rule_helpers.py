#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="misc"

"""Helper functions for tests against rules with predictive and fixed levels.."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Literal

from tests.integration.openapi.rules.helpers.assertions import (
    assert_fixed_levels_structure,
    assert_predictive_levels_structure,
)
from tests.integration.openapi.rules.helpers.rule_configs import (
    DEFAULT_HORIZON,
    DEFAULT_LEVELS,
    DEFAULT_PERIOD,
)
from tests.testlib.site import Site
from tests.testlib.utils import is_cleanup_enabled

logger = logging.getLogger(__name__)

DISKSTAT_RULESET = "checkgroup_parameters:diskstat"
HOSTNAME = "rules-api-test-host"
FOLDER_PATH = "/rules_api_test_folder"


def build_predictive_rule_value(
    metric: str,
    period: str = DEFAULT_PERIOD,
    horizon: int = DEFAULT_HORIZON,
    levels: tuple[float, float] | tuple[str, tuple[float, float]] = DEFAULT_LEVELS,
    bound: tuple[float, float] | None = None,
) -> dict[str, Any]:
    return {
        metric: (
            "cmk_postprocessed",
            "predictive_levels",
            {
                "period": period,
                "horizon": horizon,
                "levels": levels,
                "bound": bound,
            },
        )
    }


def build_fixed_rule_value(metric: str, levels: tuple[float, float]) -> dict[str, Any]:
    return {metric: ("fixed", levels)}


def create_and_verify_rule_with_levels(
    site: Site,
    rule_value: dict[str, Any],
    comment: str,
    expected_checks: list[str] | None = None,
    rule_type: Literal["predictive_levels", "fixed_levels"] = "predictive_levels",
    folder: str = FOLDER_PATH,
    host: str = HOSTNAME,
    ruleset: str = DISKSTAT_RULESET,
) -> str:
    """Create a rule, verify its creation, and return the rule ID."""
    rule_id = site.openapi.rules.create(
        value=rule_value,
        ruleset_name=ruleset,
        folder=folder,
        conditions={
            "host_name": {
                "match_on": [host],
                "operator": "one_of",
            }
        },
        properties={
            "disabled": False,
            "comment": comment,
        },
    )
    logger.info(f"Created '{rule_type}' rule with ID: {rule_id}")
    # Basic validation
    assert rule_id is not None, "Rule ID should not be None"
    assert isinstance(rule_id, str), "Rule ID should be string"

    result = site.openapi.rules.get(rule_id)
    assert result is not None, f"Rule {rule_id} not found or could not be retrieved"
    rule_data, etag = result
    assert rule_data is not None, f"Data of rule {rule_id} should be retrievable"

    if rule_type == "predictive_levels":
        assert etag is not None, "ETag should be provided"
        assert rule_data["ruleset"] == ruleset, (
            f"Expected ruleset {ruleset}, got {rule_data['ruleset']}"
        )
        assert rule_data["folder"] == FOLDER_PATH, (
            f"Expected folder {folder}, got {rule_data['folder']}"
        )

    # Verify content structure
    stored_value = str(rule_data["value_raw"])

    if rule_type == "predictive_levels":
        assert_predictive_levels_structure(stored_value, expected_checks)
    else:
        assert_fixed_levels_structure(stored_value, expected_checks or [])

    logger.info(f"Successfully created and verified {rule_type} rule: {rule_id}")
    return rule_id


def verify_rule_conversion(
    site: Site, rule_id: str, expected_checks: list[str], conversion_type: str
) -> None:
    """Helper function to verify rule after conversion."""
    result = site.openapi.rules.get(rule_id)
    assert result is not None, f"Rule {rule_id} should exist after {conversion_type}"
    rule_data, _ = result

    stored_value = str(rule_data["value_raw"])
    for check in expected_checks:
        assert check in stored_value, f"Should contain {check} after {conversion_type}"

    logger.info(f"{conversion_type} conversion verified for rule {rule_id}")


@contextmanager
def managed_rule_with_levels(
    site: Site,
    rule_value: dict[str, Any],
    comment: str,
    expected_checks: list[str] | None = None,
    rule_type: Literal["predictive_levels", "fixed_levels"] = "predictive_levels",
) -> Generator[str]:
    """Automatically handles rule creation, validation, and cleanup."""
    rule_id = create_and_verify_rule_with_levels(
        site, rule_value, comment, expected_checks, rule_type
    )
    try:
        yield rule_id
    finally:
        site.openapi.rules.delete(rule_id)


@contextmanager
def setup_test_environment(
    site: Site,
    hostname: str = HOSTNAME,
    folder: str = FOLDER_PATH,
    folder_title: str = "RulesAPI Tests",
    allow_foreign_changes: bool = False,
) -> Generator[None]:
    """Creates and cleans up a test environment with a folder and a host."""
    logger.info(f"Create test environment: folder='{folder}', host='{hostname}' via API")
    try:
        site.openapi.folders.create(
            folder=folder,
            title=folder_title,
            attributes={"tag_agent": "cmk-agent"},
        )

        site.openapi.hosts.create(
            hostname=hostname,
            folder=folder,
            attributes={
                "ipaddress": "127.0.0.1",
                "tag_agent": "cmk-agent",
            },
        )

        site.openapi.changes.activate_and_wait_for_completion(
            force_foreign_changes=allow_foreign_changes
        )
        yield

    finally:
        if is_cleanup_enabled():
            logger.info(f"Delete test environment: folder='{folder}', host='{hostname}' via API")
            site.openapi.hosts.delete(hostname)
            site.openapi.folders.delete(folder)
            site.openapi.changes.activate_and_wait_for_completion(
                force_foreign_changes=allow_foreign_changes
            )
