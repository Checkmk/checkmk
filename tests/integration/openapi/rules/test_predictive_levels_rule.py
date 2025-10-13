#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="type-arg"

"""
Integration tests for predictive levels REST API functionality.

This test module ensures rules with predictive levels can be properly created, read, updated,
and deleted via the REST API, and that they function correctly with various
configurations including different periods, horizons, and level types.
"""

import logging
from collections.abc import Generator

import pytest

from tests.integration.openapi.rules.helpers import (
    assert_predictive_levels_structure,
    BOUND_CONFIGS,
    BoundConfig,
    build_fixed_rule_value,
    build_predictive_rule_value,
    DISKSTAT_RULESET,
    FOLDER_PATH,
    HOSTNAME,
    LEVEL_CONFIGS,
    LevelConfig,
    managed_rule_with_levels,
    PERIOD_CONFIGS,
    setup_test_environment,
    TestRuleConfig,
    verify_rule_conversion,
)
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True)
def setup_test_environment_fixture(site: Site) -> Generator:
    """Set up and tear down test environment with a folder and a host.."""
    with setup_test_environment(site=site, hostname=HOSTNAME, folder=FOLDER_PATH):
        yield


@pytest.mark.skip_if_edition("saas")
@pytest.mark.parametrize("config", PERIOD_CONFIGS)
def test_predictive_levels_periods(site: Site, config: TestRuleConfig) -> None:
    """Test different period types for predictive levels."""
    logger.info(f"Testing: {config.description} (period={config.period})")

    rule_value = build_predictive_rule_value(
        metric="read_ios",
        period=config.period,
        horizon=config.horizon,
        bound=config.bound,
    )

    with managed_rule_with_levels(
        site,
        rule_value,
        f"API Test: {config.description}",
        expected_checks=[f"period': '{config.period}'", "disk_read_ios"],
    ):
        logger.info(f"Successfully tested period {config.period}")


@pytest.mark.skip_if_edition("saas")
@pytest.mark.parametrize("config", LEVEL_CONFIGS)
def test_predictive_levels_types(site: Site, config: LevelConfig) -> None:
    """Test different level types for predictive levels (absolute, relative, stdev)."""
    logger.info(f"Testing: {config.description} for {config.metric}")

    rule_value = build_predictive_rule_value(
        metric=config.metric,
        levels=config.levels,
    )

    level_type = str(config.levels[0])
    with managed_rule_with_levels(
        site,
        rule_value,
        f"API Test: {config.description}",
        expected_checks=[level_type, f"disk_{config.metric}"],
    ):
        logger.info(f"Successfully tested {config.description}")


@pytest.mark.skip_if_edition("saas")
@pytest.mark.parametrize("config", BOUND_CONFIGS)
def test_predictive_levels_bounds(site: Site, config: BoundConfig) -> None:
    """Test predictive levels with different bound configurations."""
    logger.info(f"Testing: {config.description}")

    rule_value = build_predictive_rule_value(
        metric="read_ios",
        bound=config.bound,
    )

    expected_bound_check = "bound': None" if config.bound is None else f"bound': {config.bound}"
    with managed_rule_with_levels(
        site,
        rule_value,
        f"API Test: {config.description}",
        expected_checks=[expected_bound_check],
    ):
        logger.info(f"Successfully tested {config.description}")


@pytest.mark.skip_if_edition("saas")
def test_update_predictive_levels_rule(site: Site) -> None:
    """Test updating predictive levels rules via REST API."""
    logger.info("Testing: Update predictive levels rule")

    logger.info("Creating initial predictive levels rule")
    initial_value = build_predictive_rule_value(
        metric="read_ios",
        period="wday",
        horizon=90,
        levels=("absolute", (100.0, 200.0)),
        bound=None,
    )

    rule_id = site.openapi.rules.create(
        value=initial_value,
        ruleset_name=DISKSTAT_RULESET,
        folder=FOLDER_PATH,
        conditions={
            "host_name": {
                "match_on": [HOSTNAME],
                "operator": "one_of",
            }
        },
    )
    logger.info(f"Created rule with ID: {rule_id}")

    try:
        logger.info(f"Update created rule {rule_id}")
        updated_value = build_predictive_rule_value(
            metric="write_ios",
            period="day",
            horizon=30,
            levels=("relative", (15.0, 25.0)),
            bound=(10.0, 50.0),
        )

        site.openapi.rules.update(
            rule_id=rule_id,
            value_raw=updated_value,
            properties={"comment": "Updated via API test"},
        )

        logger.info(f"Read updated rule {rule_id}")
        result = site.openapi.rules.get(rule_id)
        assert result is not None, f"Updated rule {rule_id} should be retrievable"
        updated_rule_data, _ = result
        assert updated_rule_data is not None, (
            f"Updated data of rule {rule_id} should be retrievable"
        )

        stored_value = str(updated_rule_data["value_raw"])

        logger.info("Verifying updated rule contents")
        update_checks = [
            ("period': 'day'", "Period should be updated to 'day'"),
            ("horizon': 30", "Horizon should be updated to 30"),
            ("relative", "Levels type should be updated to 'relative'"),
            ("(15.0, 25.0)", "Levels values should be updated"),
            ("(10.0, 50.0)", "Bounds should be added"),
            ("disk_write_ios", "Should reference write I/O metric"),
        ]

        for check, message in update_checks:
            assert check in stored_value, message

        assert_predictive_levels_structure(stored_value)

        logger.info("Successfully updated predictive levels rule")
    finally:
        site.openapi.rules.delete(rule_id)


@pytest.mark.skip_if_edition("saas")
def test_multiple_disk_metrics_predictive_levels(site: Site) -> None:
    """Test predictive levels for multiple disk metrics in one rule."""
    logger.info("Testing: Multiple disk metrics with predictive levels")

    multi_metric_value = {
        "read_ios": (
            "cmk_postprocessed",
            "predictive_levels",
            {
                "period": "wday",
                "horizon": 90,
                "levels": ("absolute", (100.0, 200.0)),
                "bound": None,
            },
        ),
        "write_ios": (
            "cmk_postprocessed",
            "predictive_levels",
            {
                "period": "wday",
                "horizon": 90,
                "levels": ("relative", (15.0, 25.0)),
                "bound": None,
            },
        ),
        "utilization": (
            "cmk_postprocessed",
            "predictive_levels",
            {
                "period": "wday",
                "horizon": 90,
                "levels": ("relative", (10.0, 20.0)),
                "bound": None,
            },
        ),
        "read_throughput": (
            "cmk_postprocessed",
            "predictive_levels",
            {
                "period": "wday",
                "horizon": 90,
                "levels": ("stdev", (2.0, 4.0)),
                "bound": None,
            },
        ),
        "write_throughput": (
            "cmk_postprocessed",
            "predictive_levels",
            {
                "period": "day",
                "horizon": 90,
                "levels": ("absolute", (200, 400)),
                "bound": None,
            },
        ),
        # TODO Add more metrics as needed
    }

    with managed_rule_with_levels(
        site,
        multi_metric_value,
        "API Test: Multiple metrics with predictive levels",
        expected_checks=[
            "disk_read_ios",
            "disk_write_ios",
            "period': 'wday'",
            "period': 'day'",
            "absolute",
            "relative",
        ],
    ):
        logger.info("Successfully tested multiple disk metrics")


@pytest.mark.skip_if_edition("saas")
def test_fixed_to_predictive_conversion(site: Site) -> None:
    """Test converting between fixed levels and predictive levels using RulesAPI::update method."""
    logger.info("Testing: Conversion between fixed and predictive levels")

    # Test data
    initial_fixed = build_fixed_rule_value("read_ios", (50.0, 100.0))
    predictive_config = build_predictive_rule_value(
        "read_ios",
        levels=("absolute", (80.0, 160.0)),
        bound=(200.0, 300.0),
    )
    final_fixed = build_fixed_rule_value("read_ios", (75.0, 150.0))

    logger.info("Creating initial fixed levels rule")
    with managed_rule_with_levels(
        site,
        initial_fixed,
        "API Test: Initial Fixed Levels",
        expected_checks=["50.0", "100.0"],
        rule_type="fixed_levels",
    ) as rule_id:
        logger.info(f"Converting created rule {rule_id} from fixed to predictive levels")
        site.openapi.rules.update(
            rule_id=rule_id,
            value_raw=predictive_config,
            properties={"comment": "API Test: Converted to Predictive Levels"},
        )
        logger.info(f"Verifying converted rule {rule_id} with predictive levels")
        verify_rule_conversion(
            site,
            rule_id,
            [
                "cmk_postprocessed",
                "predictive_levels",
                "period': 'wday'",
                "horizon': 90",
                "80.0, 160.0",
                "200.0, 300.0",
            ],
            "Predictive levels",
        )

        logger.info(f"Converting rule {rule_id} back to fixed levels")
        site.openapi.rules.update(
            rule_id=rule_id,
            value_raw=final_fixed,
            properties={"comment": "API Test: Converted back to Fixed Levels"},
        )
        logger.info(f"Verifying converted rule {rule_id} with fixed levels")
        verify_rule_conversion(
            site,
            rule_id,
            ["75.0", "150.0", "fixed"],
            "Fixed levels",
        )

        result = site.openapi.rules.get(rule_id)
        assert result is not None, f"Rule {rule_id} should exist after conversion to fixed"
        logger.info(f"Verifying predictive elements are removed from rule {rule_id}")
        stored_value = str(result[0]["value_raw"])
        assert "cmk_postprocessed" not in stored_value, "Predictive elements should be removed"
        assert "predictive_levels" not in stored_value, "Predictive elements should be removed"
