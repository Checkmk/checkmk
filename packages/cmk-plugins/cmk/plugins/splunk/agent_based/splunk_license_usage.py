#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<splunk_license_usage>>>
# 524288000 5669830

from typing import Self, TypedDict

import pydantic

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)


class LicenseUsage(pydantic.BaseModel):
    """Describes the state of license usage."""

    model_config = pydantic.ConfigDict(frozen=True, extra="forbid")

    quota: int = pydantic.Field(..., ge=0)
    """Quota defined in bytes."""
    usage: int = pydantic.Field(..., ge=0)
    """Usage defined in bytes."""

    @classmethod
    def from_string_table_item(cls, table: list[str]) -> Self:
        """Build and validate the input from a string table item passed by the agent."""
        payload = dict(zip(cls.__pydantic_fields__, table))
        return cls.model_validate_strings(payload)


class SplunkLicenseUsageParsingError(Exception):
    """Raised when license usage agent section cannot be parsed."""


def parse_splunk_license_usage(string_table: StringTable) -> LicenseUsage:
    """
    Parse splunk license usage from agent output.

    Try and parse a valid license usage item using entire string table input. If the input data is
    empty, raise immediately. Otherwise, keep track of the most recent validation error and raise it
    at the end if no valid usage was found.
    """
    if not string_table:
        raise SplunkLicenseUsageParsingError("String table input empty.")

    validation_error: pydantic.ValidationError | None = None

    for item in string_table:
        try:
            return LicenseUsage.from_string_table_item(item)
        except pydantic.ValidationError as err:
            validation_error = err

    raise SplunkLicenseUsageParsingError(f"Invalid input: {string_table}") from validation_error


def discover_splunk_license_usage(section: LicenseUsage) -> DiscoveryResult:
    """Runs empty discovery since there is only a single service."""
    yield Service()


type FloatLevels = FixedLevelsT[float]
"""Fixed warn and critical float threshold."""


class CheckParams(TypedDict):
    """Parameters passed to plugin via ruleset (see defaults)."""

    usage_bytes: FloatLevels


def calculate_usage_threshold(quota: int, percentage: float) -> float:
    """
    Calculate a usage threshold based on a percentage of quota.

    >>> calculate_usage_threshold(quota=1000, percentage=80.0)
    800.0
    """
    return quota / 100 * percentage if percentage else 0.0


def percent_levels_to_bytes(quota: int, levels: FloatLevels) -> FloatLevels:
    """
    Transforms levels as a percentage into bytes.

    >>> pct_levels = ('fixed', (80.0, 90.0))
    >>> percent_levels_to_bytes(quota=1000, levels=pct_levels)
    ('fixed', (800.0, 900.0))
    """
    _, (warn_percentage, crit_percentage) = levels

    warn_threshold = calculate_usage_threshold(quota, warn_percentage)
    crit_threshold = calculate_usage_threshold(quota, crit_percentage)

    return ("fixed", (warn_threshold, crit_threshold))


def check_splunk_license_usage(params: CheckParams, section: LicenseUsage) -> CheckResult:
    """Checks the splunk license usage section returning valid checkmk results."""
    rendered_quota_bytes = render.bytes(section.quota)
    levels_as_bytes = percent_levels_to_bytes(section.quota, params["usage_bytes"])

    yield Result(state=State.OK, summary=f"Quota: {rendered_quota_bytes}")

    yield from check_levels(
        section.usage,
        levels_upper=levels_as_bytes,
        metric_name="splunk_slave_usage_bytes",
        render_func=render.bytes,
        label="Slaves usage",
    )


agent_section_splunk_license_usage = AgentSection(
    name="splunk_license_usage",
    parse_function=parse_splunk_license_usage,
)

check_plugin_splunk_license_usage = CheckPlugin(
    name="splunk_license_usage",
    service_name="Splunk License Usage",
    discovery_function=discover_splunk_license_usage,
    check_function=check_splunk_license_usage,
    check_ruleset_name="splunk_license_usage",
    check_default_parameters=CheckParams(usage_bytes=("fixed", (80.0, 90.0))),
)
