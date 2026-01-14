#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from typing import Any

import pytest

from cmk.base.legacy_checks.aws_glacier import (
    check_aws_glacier_archives,
    check_aws_glacier_summary,
    discover_aws_glacier,
    discover_aws_glacier_summary,
    parse_aws_glacier,
)


@pytest.fixture(name="string_table")
def string_table_fixture() -> list[list[str]]:
    """Test data for AWS Glacier with two empty vaults"""
    return [
        [
            '[{"VaultARN":',
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
            '"Timestamps":',
            "[],",
            '"CreationDate":',
            '"2019-07-18T08:07:01.708Z",',
            '"Id":',
            '"id_1_GlacierMetric",',
            '"Tagging":',
            "{},",
            '"StatusCode":',
            '"Complete"}]',
        ]
    ]


@pytest.fixture(name="parsed")
def parsed_fixture(string_table: list[list[str]]) -> dict[str, dict[str, Any]]:
    """Parsed AWS Glacier data"""
    return parse_aws_glacier(string_table)


def test_parse_aws_glacier(string_table: list[list[str]]) -> None:
    """Test parsing creates proper vault mapping"""
    result = parse_aws_glacier(string_table)

    # Should parse 2 vaults
    assert len(result) == 2
    assert "axi_empty_vault" in result
    assert "axi_vault" in result

    # Check first vault data - has NumberOfArchives but no SizeInBytes
    empty_vault = result["axi_empty_vault"]
    assert empty_vault["VaultName"] == "axi_empty_vault"
    assert empty_vault["NumberOfArchives"] == 0
    assert empty_vault["StatusCode"] == "Complete"
    # This vault doesn't have SizeInBytes field
    assert "SizeInBytes" not in empty_vault

    # Check second vault data - has SizeInBytes but no NumberOfArchives
    axi_vault = result["axi_vault"]
    assert axi_vault["VaultName"] == "axi_vault"
    assert axi_vault["SizeInBytes"] == 0
    assert axi_vault["StatusCode"] == "Complete"
    # This vault doesn't have NumberOfArchives field
    assert "NumberOfArchives" not in axi_vault


def test_discover_aws_glacier(parsed: dict[str, dict[str, Any]]) -> None:
    """Test vault discovery finds both empty vaults"""
    discovered = list(discover_aws_glacier(parsed))

    assert len(discovered) == 2
    vault_names = [item[0] for item in discovered]
    assert "axi_empty_vault" in vault_names
    assert "axi_vault" in vault_names

    # Check parameters are empty
    for _, params in discovered:
        assert params == {}


def test_discover_aws_glacier_summary(parsed: dict[str, dict[str, Any]]) -> None:
    """Test summary discovery creates summary item"""
    discovered = list(discover_aws_glacier_summary(parsed))

    assert len(discovered) == 1
    item, params = discovered[0]
    assert item is None
    assert params == {}


def test_check_aws_glacier_archives_axi_empty_vault(parsed: dict[str, dict[str, Any]]) -> None:
    """Test archives check for first empty vault"""
    result = list(check_aws_glacier_archives("axi_empty_vault", {}, parsed))

    assert len(result) == 2

    # Vault size check
    state, summary, metrics = result[0]
    assert state == 0
    assert "Vault size: 0 B" in summary
    assert len(metrics) == 1
    assert metrics[0] == ("aws_glacier_vault_size", 0, None, None)

    # Number of archives check
    state, summary, metrics = result[1]
    assert state == 0
    assert "Number of archives: 0" in summary
    assert len(metrics) == 1
    assert metrics[0] == ("aws_glacier_num_archives", 0)


def test_check_aws_glacier_archives_axi_vault(parsed: dict[str, dict[str, Any]]) -> None:
    """Test archives check for second empty vault"""
    result = list(check_aws_glacier_archives("axi_vault", {}, parsed))

    assert len(result) == 2

    # Vault size check
    state, summary, metrics = result[0]
    assert state == 0
    assert "Vault size: 0 B" in summary
    assert len(metrics) == 1
    assert metrics[0] == ("aws_glacier_vault_size", 0, None, None)

    # Number of archives check
    state, summary, metrics = result[1]
    assert state == 0
    assert "Number of archives: 0" in summary
    assert len(metrics) == 1
    assert metrics[0] == ("aws_glacier_num_archives", 0)


def test_check_aws_glacier_archives_nonexistent_vault(parsed: dict[str, dict[str, Any]]) -> None:
    """Test check function with non-existent vault returns None"""
    result = list(check_aws_glacier_archives("nonexistent", {}, parsed))

    # Should return empty list when vault doesn't exist
    assert len(result) == 0


def test_check_aws_glacier_summary(parsed: dict[str, dict[str, Any]]) -> None:
    """Test summary aggregates values from both empty vaults"""
    result = list(check_aws_glacier_summary(None, {}, parsed))

    assert len(result) == 2

    # Total size check
    state, summary, metrics = result[0]
    assert state == 0
    assert "Total size: 0 B" in summary
    assert len(metrics) == 1
    assert metrics[0] == ("aws_glacier_total_vault_size", 0, None, None)

    # Largest vault check - should pick one of the two vaults (both are same size)
    state, summary, metrics = result[1]
    assert state == 0
    assert "Largest vault:" in summary
    assert "(0 B)" in summary
    # Could be either vault since both have same size
    assert "axi_empty_vault" in summary or "axi_vault" in summary
    assert len(metrics) == 1
    assert metrics[0] == ("aws_glacier_largest_vault_size", 0)
