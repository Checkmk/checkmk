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

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.aws.agent_based.aws_glacier import (
    check_aws_glacier_archives,
    check_aws_glacier_summary,
    discover_aws_glacier,
    discover_aws_glacier_summary,
    GlacierVault,
    parse_aws_glacier,
)


@pytest.fixture(name="parsed", scope="module")
def fixture_parsed() -> Mapping[str, GlacierVault]:
    string_table = [
        [
            '[{"SizeInBytes":',
            "0,",
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
            "22548578304,",
            '"VaultARN":',
            '"arn:aws:glacier:eu-central-1:710145618630:vaults/fake_vault_1",',
            '"VaultName":',
            '"fake_vault_1",',
            '"Label":',
            '"fake_vault_1",',
            '"Values":',
            "[],",
            '"NumberOfArchives":',
            "2025,",
            '"Timestamps":',
            "[],",
            '"CreationDate":',
            '"2019-07-18T08:07:01.708Z",',
            '"Id":',
            '"id_2_GlacierMetric",',
            '"Tagging":',
            "{},",
            '"StatusCode":',
            '"Complete"},',
            '{"SizeInBytes":',
            "117440512,",
            '"VaultARN":',
            '"arn:aws:glacier:eu-central-1:710145618630:vaults/fake_vault_2",',
            '"VaultName":',
            '"fake_vault_2",',
            '"Label":',
            '"fake_vault_2",',
            '"Values":',
            "[],",
            '"NumberOfArchives":',
            "17,",
            '"Timestamps":',
            "[],",
            '"CreationDate":',
            '"2019-07-18T08:07:01.708Z",',
            '"Id":',
            '"id_3_GlacierMetric",',
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
            "0,",
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
    return parse_aws_glacier(string_table)


def test_parse_aws_glacier(parsed: Mapping[str, GlacierVault]) -> None:
    """Test parsing of AWS Glacier vault data"""
    assert len(parsed) == 4

    # Check axi_empty_vault
    assert "axi_empty_vault" in parsed
    vault = parsed["axi_empty_vault"]
    assert vault.size_in_bytes == 0
    assert vault.number_of_archives == 0
    assert vault.vault_name == "axi_empty_vault"

    # Check fake_vault_1
    assert "fake_vault_1" in parsed
    vault = parsed["fake_vault_1"]
    assert vault.size_in_bytes == 22548578304
    assert vault.number_of_archives == 2025
    assert vault.vault_name == "fake_vault_1"

    # Check fake_vault_2
    assert "fake_vault_2" in parsed
    vault = parsed["fake_vault_2"]
    assert vault.size_in_bytes == 117440512
    assert vault.number_of_archives == 17
    assert vault.vault_name == "fake_vault_2"

    # Check axi_vault
    assert "axi_vault" in parsed
    vault = parsed["axi_vault"]
    assert vault.size_in_bytes == 0
    assert vault.number_of_archives == 0
    assert vault.vault_name == "axi_vault"


def test_discover_aws_glacier(parsed: Mapping[str, GlacierVault]) -> None:
    """Test discovery of AWS Glacier vaults"""
    result = list(discover_aws_glacier(parsed))

    expected = [
        Service(item="axi_empty_vault"),
        Service(item="axi_vault"),
        Service(item="fake_vault_1"),
        Service(item="fake_vault_2"),
    ]
    assert sorted(result, key=str) == sorted(expected, key=str)


def test_discover_aws_glacier_summary(parsed: Mapping[str, GlacierVault]) -> None:
    """Test discovery of AWS Glacier summary service"""
    result = list(discover_aws_glacier_summary(parsed))
    assert result == [Service()]


def test_check_aws_glacier_empty_vault(parsed: Mapping[str, GlacierVault]) -> None:
    """Test check function for empty vault"""
    result = list(check_aws_glacier_archives("axi_empty_vault", {}, parsed))

    assert result == [
        Result(state=State.OK, summary="Vault size: 0 B"),
        Metric("aws_glacier_vault_size", 0.0),
        Result(state=State.OK, summary="Number of archives: 0"),
        Metric("aws_glacier_num_archives", 0.0),
    ]


def test_check_aws_glacier_vault_with_data(parsed: Mapping[str, GlacierVault]) -> None:
    """Test check function for vault with data"""
    result = list(check_aws_glacier_archives("fake_vault_1", {}, parsed))

    assert result == [
        Result(state=State.OK, summary="Vault size: 22.5 GB"),
        Metric("aws_glacier_vault_size", 22548578304.0),
        Result(state=State.OK, summary="Number of archives: 2025"),
        Metric("aws_glacier_num_archives", 2025.0),
    ]


def test_check_aws_glacier_smaller_vault(parsed: Mapping[str, GlacierVault]) -> None:
    """Test check function for smaller vault"""
    result = list(check_aws_glacier_archives("fake_vault_2", {}, parsed))

    assert result == [
        Result(state=State.OK, summary="Vault size: 117 MB"),
        Metric("aws_glacier_vault_size", 117440512.0),
        Result(state=State.OK, summary="Number of archives: 17"),
        Metric("aws_glacier_num_archives", 17.0),
    ]


def test_check_aws_glacier_summary(parsed: Mapping[str, GlacierVault]) -> None:
    """Test summary check function"""
    result = list(check_aws_glacier_summary({}, parsed))

    assert result == [
        Result(state=State.OK, summary="Total size: 22.7 GB"),
        Metric("aws_glacier_total_vault_size", 22666018816.0),
        Result(state=State.OK, summary="Largest vault: fake_vault_1 (22.5 GB)"),
        Metric("aws_glacier_largest_vault_size", 22548578304.0),
    ]


def test_check_aws_glacier_nonexistent_vault() -> None:
    """Test check function with non-existent vault"""
    result = list(check_aws_glacier_archives("nonexistent", {}, {}))
    assert len(result) == 0
