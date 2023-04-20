#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

from collections.abc import Callable, Sequence

import pytest

from cmk.special_agents.agent_aws import (
    AWSConfig,
    Glacier,
    GlacierLimits,
    GlacierSummary,
    NamingConvention,
    OverallTags,
    ResultDistributor,
)

from .agent_aws_fake_clients import (
    FakeCloudwatchClient,
    GlacierListTagsInstancesIB,
    GlacierListVaultsIB,
)


class FakeGlacierClient:
    def list_vaults(self):
        return {"VaultList": GlacierListVaultsIB.create_instances(amount=4), "Marker": "string"}

    def list_tags_for_vault(self, vaultName=""):
        if vaultName == "VaultName-0":
            return {
                "Tags": GlacierListTagsInstancesIB.create_instances(amount=1),
            }
        if vaultName == "VaultName-1":
            return {
                "Tags": GlacierListTagsInstancesIB.create_instances(amount=2),
            }
        return {"Tags": {}}


GlacierSections = Callable[
    [object | None, OverallTags], tuple[GlacierLimits, GlacierSummary, Glacier]
]


@pytest.fixture()
def get_glacier_sections() -> GlacierSections:
    def _create_glacier_sections(
        names: object | None, tags: OverallTags
    ) -> tuple[GlacierLimits, GlacierSummary, Glacier]:
        region = "eu-central-1"
        config = AWSConfig("hostname", [], ([], []), NamingConvention.ip_region_instance)
        config.add_single_service_config("glacier_names", names)
        config.add_service_tags("glacier_tags", tags)

        fake_glacier_client = FakeGlacierClient()
        fake_cloudwatch_client = FakeCloudwatchClient()

        distributor = ResultDistributor()

        glacier_limits = GlacierLimits(fake_glacier_client, region, config, distributor)
        glacier_summary = GlacierSummary(fake_glacier_client, region, config, distributor)
        glacier = Glacier(fake_cloudwatch_client, region, config)

        distributor.add(glacier_limits.name, glacier_summary)
        distributor.add(glacier_summary.name, glacier)
        return glacier_limits, glacier_summary, glacier

    return _create_glacier_sections


glacier_params = [
    (None, (None, None), 4),
    (["VaultName-0"], (None, None), 1),
    (["Uuuups"], (None, None), 0),
    (["VaultName-0", "VaultName-1"], (None, None), 2),
    (["VaultName-0", "VaultName-1", "VaultName-2"], (None, None), 3),
    (["VaultName-0", "VaultName-1", "VaultName-2", "string4"], (None, None), 3),
    (["VaultName-0", "VaultName-1", "VaultName-2", "FOOBAR"], (None, None), 3),
    (None, ([["Tag-1"]], [["Value-0"]]), 0),
    (None, ([["Tag-1"]], [["Value-1"]]), 1),
    (None, ([["Tag-0"]], [["Value-0"]]), 2),
    (None, ([["Tag-0"]], [["Value-0", "Value-1"]]), 2),
    (None, ([["Tag-0", "unknown-tag"]], [["Value-0", "Value-1"], ["unknown-val"]]), 2),
]


@pytest.mark.parametrize("names,tags,amount_vaults", glacier_params)
def test_agent_aws_glacier_limits(
    get_glacier_sections: GlacierSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    amount_vaults: int,
) -> None:
    glacier_limits, _glacier_summary, _glacier = get_glacier_sections(names, tags)
    glacier_limits_results = glacier_limits.run().results
    assert glacier_limits.name == "glacier_limits"

    glacier_limits_result = glacier_limits_results[0]
    assert glacier_limits_result.piggyback_hostname == ""
    assert len(glacier_limits_results) == 1

    glacier_limits_content = glacier_limits_result.content[0]
    assert glacier_limits_content.key == "number_of_vaults"
    assert glacier_limits_content.title == "Vaults"
    assert glacier_limits_content.limit == 1000
    assert glacier_limits_content.amount == 4


@pytest.mark.parametrize("names,tags,amount_vaults", glacier_params)
def test_agent_aws_glacier_summary(
    get_glacier_sections: GlacierSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    amount_vaults: int,
) -> None:
    glacier_limits, glacier_summary, _glacier = get_glacier_sections(names, tags)
    _glacier_summary_results = glacier_limits.run().results
    glacier_summary_results = glacier_summary.run().results

    assert glacier_summary.name == "glacier_summary"
    assert glacier_summary_results == []


@pytest.mark.parametrize("names,tags,amount_vaults", glacier_params)
def test_agent_aws_glacier(
    get_glacier_sections: GlacierSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    amount_vaults: int,
) -> None:
    glacier_limits, glacier_summary, glacier = get_glacier_sections(names, tags)
    _glacier_summary_results = glacier_limits.run().results
    _glacier_summary_results = glacier_summary.run().results
    glacier_results = glacier.run().results

    assert glacier_summary.name == "glacier_summary"

    if amount_vaults:
        assert len(glacier_results[0].content) == amount_vaults
    else:
        assert not glacier_results


@pytest.mark.parametrize("names,tags,amount_vaults", glacier_params)
def test_agent_aws_glacier_summary_without_limits(
    get_glacier_sections: GlacierSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    amount_vaults: int,
) -> None:
    _glacier_limits, glacier_summary, _glacier = get_glacier_sections(names, tags)
    glacier_summary_results = glacier_summary.run().results

    assert glacier_summary.name == "glacier_summary"
    assert glacier_summary_results == []


@pytest.mark.parametrize("names,tags,amount_vaults", glacier_params)
def test_agent_aws_glacier_summary_without_limits2(
    get_glacier_sections, names, tags, amount_vaults
):
    _glacier_limits, glacier_summary, glacier = get_glacier_sections(names, tags)
    _glacier_summary_results = glacier_summary.run().results
    glacier_results = glacier.run().results

    assert glacier_summary.name == "glacier_summary"

    if amount_vaults:
        assert len(glacier_results[0].content) == amount_vaults
    else:
        assert not glacier_results
