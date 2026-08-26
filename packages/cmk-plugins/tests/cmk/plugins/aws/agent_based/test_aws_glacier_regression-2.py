#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.aws.agent_based.aws_glacier import (
    check_aws_glacier_archives,
    check_aws_glacier_summary,
    discover_aws_glacier,
    discover_aws_glacier_summary,
    GlacierVault,
    parse_aws_glacier,
)


@pytest.fixture(name="string_table")
def string_table_fixture() -> list[list[str]]:
    """Test data for AWS Glacier with empty and non-empty vaults"""
    return [
        [
            '[{"SizeInBytes":',
            "12.12,",
            '"VaultARN":',
            '"arn:aws:glacier:eu-central-1:710145618630:vaults/axi_empty_vault",',
            '"VaultName":',
            '"axi_empty_vault",',
            '"Label":',
            '"axi_empty_vault",',
            '"Values":',
            "[],",
            '"NumberOfArchives":',
            "0,",
            '"Timestamps":',
            "[],",
            '"CreationDate":',
            '"2019-07-22T09:39:34.135Z",',
            '"Id":',
            '"id_0_GlacierMetric",',
            '"Tagging":',
            "{},",
            '"StatusCode":',
            '"Complete"},',
            '{"SizeInBytes":',
            "0,",
            '"VaultARN":',
            '"arn:aws:glacier:eu-central-1:710145618630:vaults/axi_vault",',
            '"VaultName":',
            '"axi_vault",',
            '"Label":',
            '"axi_vault",',
            '"Values":',
            "[],",
            '"NumberOfArchives":',
            "15.5,",
            '"Timestamps":',
            "[],",
            '"CreationDate":',
            '"2019-07-22T09:39:34.135Z",',
            '"Id":',
            '"id_1_GlacierMetric",',
            '"Tagging":',
            "{},",
            '"StatusCode":',
            '"Complete"}]',
        ]
    ]


@pytest.fixture(name="parsed")
def parsed_fixture(string_table: list[list[str]]) -> Mapping[str, GlacierVault]:
    """Parsed AWS Glacier data"""
    return parse_aws_glacier(string_table)


def test_discover_aws_glacier(parsed: Mapping[str, GlacierVault]) -> None:
    """Test vault discovery finds both vaults"""
    discovered = list(discover_aws_glacier(parsed))
    assert len(discovered) == 2
    vault_names = [service.item for service in discovered]
    assert "axi_empty_vault" in vault_names
    assert "axi_vault" in vault_names


def test_check_aws_glacier_archives_axi_empty_vault(parsed: Mapping[str, GlacierVault]) -> None:
    """Test archives check for empty vault with minimal data"""
    result = list(check_aws_glacier_archives("axi_empty_vault", {}, parsed))

    assert result == [
        Result(state=State.OK, summary="Vault size: 12 B"),
        Metric("aws_glacier_vault_size", 12.12),
        Result(state=State.OK, summary="Number of archives: 0"),
        Metric("aws_glacier_num_archives", 0.0),
    ]


def test_check_aws_glacier_archives_axi_vault(parsed: Mapping[str, GlacierVault]) -> None:
    """Test archives check for vault with archives but zero size"""
    result = list(check_aws_glacier_archives("axi_vault", {}, parsed))

    assert result == [
        Result(state=State.OK, summary="Vault size: 0 B"),
        Metric("aws_glacier_vault_size", 0.0),
        Result(state=State.OK, summary="Number of archives: 15"),
        Metric("aws_glacier_num_archives", 15.5),
    ]


def test_check_aws_glacier_summary(parsed: Mapping[str, GlacierVault]) -> None:
    """Test summary aggregates values from all vaults"""
    result = list(check_aws_glacier_summary({}, parsed))

    assert result == [
        Result(state=State.OK, summary="Total size: 12 B"),
        Metric("aws_glacier_total_vault_size", 12.12),
        Result(state=State.OK, summary="Largest vault: axi_empty_vault (12 B)"),
        Metric("aws_glacier_largest_vault_size", 12.12),
    ]


def test_discover_aws_glacier_summary(parsed: Mapping[str, GlacierVault]) -> None:
    """Test summary discovery creates summary item"""
    discovered = list(discover_aws_glacier_summary(parsed))
    assert len(discovered) == 1
    assert discovered[0].item is None  # No item name for summary


def test_parse_aws_glacier(string_table: list[list[str]]) -> None:
    """Test that parsing creates proper vault mapping"""
    parsed = parse_aws_glacier(string_table)
    assert isinstance(parsed, dict)
    assert "axi_empty_vault" in parsed
    assert "axi_vault" in parsed

    # Check vault data structure
    empty_vault = parsed["axi_empty_vault"]
    assert empty_vault.size_in_bytes == 12.12
    assert empty_vault.number_of_archives == 0

    vault_with_archives = parsed["axi_vault"]
    assert vault_with_archives.size_in_bytes == 0
    assert vault_with_archives.number_of_archives == 15.5
