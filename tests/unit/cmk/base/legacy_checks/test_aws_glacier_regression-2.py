#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

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
def parsed_fixture(string_table: list[list[str]]) -> dict[str, dict]:
    """Parsed AWS Glacier data"""
    return parse_aws_glacier(string_table)


def test_discover_aws_glacier(parsed: dict[str, dict]) -> None:
    """Test vault discovery finds both vaults"""
    discovered = list(discover_aws_glacier(parsed))
    assert len(discovered) == 2
    vault_names = [item[0] for item in discovered]
    assert "axi_empty_vault" in vault_names
    assert "axi_vault" in vault_names


def test_check_aws_glacier_archives_axi_empty_vault(parsed: dict[str, dict]) -> None:
    """Test archives check for empty vault with minimal data"""
    result = list(check_aws_glacier_archives("axi_empty_vault", {}, parsed))
    assert len(result) >= 1
    # Should have vault size check
    vault_size_result = result[0]
    assert vault_size_result[0] == 0  # OK status
    assert "Vault size" in vault_size_result[1]

    # Should have number of archives
    num_archives_result = result[1]
    assert num_archives_result[0] == 0  # OK status
    assert "Number of archives: 0" in num_archives_result[1]


def test_check_aws_glacier_archives_axi_vault(parsed: dict[str, dict]) -> None:
    """Test archives check for vault with archives but zero size"""
    result = list(check_aws_glacier_archives("axi_vault", {}, parsed))
    assert len(result) >= 2

    # Should have vault size check
    vault_size_result = result[0]
    assert vault_size_result[0] == 0  # OK status
    assert "Vault size" in vault_size_result[1]

    # Should have number of archives
    num_archives_result = result[1]
    assert num_archives_result[0] == 0  # OK status
    assert "Number of archives: 15" in num_archives_result[1]


def test_check_aws_glacier_summary(parsed: dict[str, dict]) -> None:
    """Test summary aggregates values from all vaults"""
    result = list(check_aws_glacier_summary(None, {}, parsed))
    assert len(result) >= 1

    # Should have total size
    total_size_result = result[0]
    assert total_size_result[0] == 0  # OK status
    assert "Total size" in total_size_result[1]

    # Should have largest vault info
    if len(result) > 1:
        largest_vault_result = result[1]
        assert largest_vault_result[0] == 0  # OK status
        assert "Largest vault" in largest_vault_result[1]


def test_discover_aws_glacier_summary(parsed: dict[str, dict]) -> None:
    """Test summary discovery creates summary item"""
    discovered = list(discover_aws_glacier_summary(parsed))
    assert len(discovered) == 1
    assert discovered[0][0] is None  # No item name for summary


def test_parse_aws_glacier(string_table: list[list[str]]) -> None:
    """Test that parsing creates proper vault mapping"""
    parsed = parse_aws_glacier(string_table)
    assert isinstance(parsed, dict)
    assert "axi_empty_vault" in parsed
    assert "axi_vault" in parsed

    # Check vault data structure
    empty_vault = parsed["axi_empty_vault"]
    assert empty_vault["SizeInBytes"] == 12.12
    assert empty_vault["NumberOfArchives"] == 0

    vault_with_archives = parsed["axi_vault"]
    assert vault_with_archives["SizeInBytes"] == 0
    assert vault_with_archives["NumberOfArchives"] == 15.5
