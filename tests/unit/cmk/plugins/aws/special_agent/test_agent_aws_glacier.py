#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from argparse import Namespace as Args
from collections.abc import Sequence
from typing import Protocol

import pytest

from cmk.plugins.aws.special_agent.agent_aws import (
    AWSConfig,
    Glacier,
    GlacierLimits,
    NamingConvention,
    OverallTags,
    ResultDistributor,
    TagsImportPatternOption,
    TagsOption,
)

from .agent_aws_fake_clients import GlacierListTagsInstancesIB, GlacierListVaultsIB


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


GlacierSections = tuple[GlacierLimits, Glacier]


class GetGlacierSections(Protocol):
    def __call__(
        self,
        names: object | None = None,
        tags: OverallTags = (None, None),
        tag_import: TagsOption = TagsImportPatternOption.import_all,
    ) -> GlacierSections: ...


@pytest.fixture()
def get_glacier_sections() -> GetGlacierSections:
    def _create_glacier_sections(
        names: object | None = None,
        tags: OverallTags = (None, None),
        tag_import: TagsOption = TagsImportPatternOption.import_all,
    ) -> GlacierSections:
        region = "eu-central-1"
        config = AWSConfig(
            "hostname", Args(), ([], []), NamingConvention.ip_region_instance, tag_import
        )
        config.add_single_service_config("glacier_names", names)
        config.add_service_tags("glacier_tags", tags)

        fake_glacier_client = FakeGlacierClient()

        distributor = ResultDistributor()

        # TODO: FakeGlacierClient should actually subclass GlacierClient, etc.
        glacier_limits = GlacierLimits(fake_glacier_client, region, config, distributor)  # type: ignore[arg-type]
        glacier = Glacier(fake_glacier_client, region, config)  # type: ignore[arg-type]

        distributor.add(glacier_limits.name, glacier)
        return glacier_limits, glacier

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
    get_glacier_sections: GetGlacierSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    amount_vaults: int,
) -> None:
    glacier_limits, _glacier = get_glacier_sections(names, tags)
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
def test_agent_aws_glacier(
    get_glacier_sections: GetGlacierSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    amount_vaults: int,
) -> None:
    glacier_limits, glacier = get_glacier_sections(names, tags)
    glacier_limits.run()
    glacier_results = glacier.run().results

    assert glacier.name == "glacier"

    if amount_vaults:
        assert len(glacier_results) == 1
        glacier_result = glacier_results[0]
        assert glacier_result.piggyback_hostname == ""
        assert len(glacier_result.content) == amount_vaults
        assert "Tagging" in glacier_result.content[0]
    else:
        assert not glacier_results


@pytest.mark.parametrize("names,tags,amount_vaults", glacier_params)
def test_agent_aws_glacier_without_limits(
    get_glacier_sections: GetGlacierSections,
    names: Sequence[str] | None,
    tags: OverallTags,
    amount_vaults: int,
) -> None:
    _glacier_limits, glacier = get_glacier_sections(names, tags)
    glacier_results = glacier.run().results

    assert glacier.name == "glacier"

    if amount_vaults:
        assert len(glacier_results) == 1
        glacier_result = glacier_results[0]
        assert glacier_result.piggyback_hostname == ""
        assert len(glacier_result.content) == amount_vaults
        assert "Tagging" in glacier_result.content[0]
    else:
        assert not glacier_results


@pytest.mark.parametrize(
    "tag_import, expected_tags",
    [
        (
            TagsImportPatternOption.import_all,
            {"VaultName-0": ["Tag-0"], "VaultName-1": ["Tag-0", "Tag-1"]},
        ),
        (r".*-1$", {"VaultName-1": ["Tag-1"]}),
        (TagsImportPatternOption.ignore_all, {}),
    ],
)
def test_agent_aws_glacier_filters_tags(
    get_glacier_sections: GetGlacierSections,
    tag_import: TagsOption,
    expected_tags: dict[str, list[str]],
) -> None:
    glacier_limits, glacier = get_glacier_sections(tag_import=tag_import)
    glacier_limits.run()
    glacier_results = glacier.run().results

    assert glacier_results
    for result in glacier_results:
        assert result.content
        for row in result.content:
            assert list(row["TagsForCmkLabels"].keys()) == expected_tags.get(row["VaultName"], [])
