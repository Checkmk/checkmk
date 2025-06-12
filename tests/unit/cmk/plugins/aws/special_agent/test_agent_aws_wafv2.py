#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from argparse import Namespace as Args
from collections.abc import Mapping, Sequence
from typing import Literal, Protocol

import pytest

from cmk.plugins.aws.special_agent.agent_aws import (
    _get_wafv2_web_acls,
    AWSConfig,
    NamingConvention,
    OverallTags,
    ResultDistributor,
    TagsImportPatternOption,
    TagsOption,
    WAFV2Limits,
    WAFV2Summary,
    WAFV2WebACL,
)

from .agent_aws_fake_clients import (
    FakeCloudwatchClient,
    WAFV2GetWebACLIB,
    WAFV2ListOperationIB,
    WAFV2ListTagsForResourceIB,
)


class FakeWAFV2Client:
    def __init__(self) -> None:
        self._web_acls = WAFV2GetWebACLIB.create_instances(amount=3)

    def list_web_acls(self, Scope=None):
        return {"WebACLs": WAFV2ListOperationIB.create_instances(amount=3)}

    def list_rule_groups(self, Scope=None):
        return {"RuleGroups": WAFV2ListOperationIB.create_instances(amount=4)}

    def list_ip_sets(self, Scope=None):
        return {"IPSets": WAFV2ListOperationIB.create_instances(amount=5)}

    def list_regex_pattern_sets(self, Scope=None):
        return {"RegexPatternSets": WAFV2ListOperationIB.create_instances(amount=6)}

    def get_web_acl(self, Name=None, Scope=None, Id=None):
        idx = int(Name[-1])
        return {"WebACL": self._web_acls[idx], "LockToken": "string"}

    def list_tags_for_resource(self, ResourceARN=None):
        if ResourceARN == "ARN-2":  # the third Web ACL has no tags
            tags = {}
        else:
            tags = WAFV2ListTagsForResourceIB.create_instances(amount=3)[0]
        return {"TagInfoForResource": tags, "NextMarker": "string"}


Wafv2Sections = Mapping[str, WAFV2Limits | WAFV2Summary | WAFV2WebACL]


def test_search_string_bytes_handling_in_get_wafv2_web_acls() -> None:
    fake_wafv2_client = FakeWAFV2Client()

    def get_response_content(response, key, dflt=None):
        if dflt is None:
            dflt = []
        if key in response:
            return response[key]
        return dflt

    res = _get_wafv2_web_acls(fake_wafv2_client, "us-east-1", get_response_content, None, None)  # type: ignore[arg-type]
    search_string = res[0]["Rules"][0]["Statement"]["ByteMatchStatement"]["SearchString"]  # type: ignore[index]
    assert isinstance(search_string, str)

    for rule in res[0]["Rules"]:  # type: ignore[attr-defined]
        if "RateBasedStatement" in rule["Statement"]:
            search_string = rule["Statement"]["RateBasedStatement"]["ScopeDownStatement"][
                "ByteMatchStatement"
            ]["SearchString"]
            assert isinstance(search_string, str)
        if "NotStatement" in rule["Statement"]:
            search_string = rule["Statement"]["NotStatement"]["ScopeDownStatement"][
                "ByteMatchStatement"
            ]["SearchString"]
            assert isinstance(search_string, str)
        if "AndStatement" in rule["Statement"]:
            search_string = rule["Statement"]["AndStatement"]["Statements"][0][
                "ByteMatchStatement"
            ]["SearchString"]
            assert isinstance(search_string, str)


def create_sections(
    names: object | None,
    tags: OverallTags,
    is_regional: bool,
    tag_import: TagsOption = TagsImportPatternOption.import_all,
) -> Wafv2Sections:
    region = "region" if is_regional else "us-east-1"
    scope: Literal["REGIONAL", "CLOUDFRONT"] = "REGIONAL" if is_regional else "CLOUDFRONT"

    config = AWSConfig(
        "hostname", Args(), ([], []), NamingConvention.ip_region_instance, tag_import
    )
    config.add_single_service_config("wafv2_names", names)
    config.add_service_tags("wafv2_tags", tags)

    fake_wafv2_client = FakeWAFV2Client()
    fake_cloudwatch_client = FakeCloudwatchClient()

    distributor = ResultDistributor()

    # TODO: FakeWAFV2Client shoud actually subclass WAFV2Client.
    wafv2_limits = WAFV2Limits(fake_wafv2_client, region, config, scope, distributor=distributor)  # type: ignore[arg-type]
    wafv2_summary = WAFV2Summary(fake_wafv2_client, region, config, scope, distributor=distributor)  # type: ignore[arg-type]
    wafv2_web_acl = WAFV2WebACL(fake_cloudwatch_client, region, config, is_regional)  # type: ignore[arg-type]

    distributor.add(wafv2_limits.name, wafv2_summary)
    distributor.add(wafv2_summary.name, wafv2_web_acl)

    return {
        "wafv2_limits": wafv2_limits,
        "wafv2_summary": wafv2_summary,
        "wafv2_web_acl": wafv2_web_acl,
    }


CreateWafv2SectionsOut = tuple[Wafv2Sections, Wafv2Sections]


class CreateWafv2Sections(Protocol):
    def __call__(
        self,
        names: object | None,
        tags: OverallTags,
        tag_import: TagsOption = TagsImportPatternOption.import_all,
    ) -> CreateWafv2SectionsOut: ...


@pytest.fixture()
def get_wafv2_sections() -> CreateWafv2Sections:
    def _create_wafv2_sections(
        names: object | None,
        tags: OverallTags,
        tag_import: TagsOption = TagsImportPatternOption.import_all,
    ) -> CreateWafv2SectionsOut:
        return create_sections(names, tags, True, tag_import), create_sections(
            names, tags, False, tag_import
        )

    return _create_wafv2_sections


wafv2_params = [
    (
        None,
        (None, None),
        ["Name-0", "Name-1", "Name-2"],
    ),
    (
        None,
        ([["FOO"]], [["BAR"]]),
        [],
    ),
    (
        None,
        ([["Key-0"]], [["Value-0"]]),
        ["Name-0", "Name-1"],
    ),
    (
        None,
        ([["Key-0", "Foo"]], [["Value-0", "Bar"]]),
        ["Name-0", "Name-1"],
    ),
    (
        ["Name-0"],
        (None, None),
        ["Name-0"],
    ),
    (
        ["Name-0", "Foobar"],
        (None, None),
        ["Name-0"],
    ),
    (
        ["Name-0", "Name-1"],
        (None, None),
        ["Name-0", "Name-1"],
    ),
    (
        ["Name-0", "Name-2"],
        ([["FOO"]], [["BAR"]]),
        ["Name-0", "Name-2"],
    ),
]


def test_agent_aws_wafv2_regional_cloudfront() -> None:
    config = AWSConfig("hostname", Args(), ([], []), NamingConvention.ip_region_instance)

    region = "region"
    # TODO: This is plainly wrong, the client can't be None.
    wafv2_limits_regional = WAFV2Limits(None, region, config, "REGIONAL")  # type: ignore[arg-type]
    assert wafv2_limits_regional._region_report == region

    wafv2_limits_regional = WAFV2Limits(None, "us-east-1", config, "CLOUDFRONT")  # type: ignore[arg-type]
    assert wafv2_limits_regional._region_report == "CloudFront"

    with pytest.raises(AssertionError):
        WAFV2Limits(None, "region", config, "CLOUDFRONT")  # type: ignore[arg-type]
        WAFV2Limits(None, "region", config, "WRONG")  # type: ignore[arg-type]
        WAFV2WebACL(None, "region", config, False)  # type: ignore[arg-type]

    assert len(WAFV2WebACL(None, "region", config, True)._static_metric_dimensions) == 2  # type: ignore[arg-type]
    assert len(WAFV2WebACL(None, "us-east-1", config, False)._static_metric_dimensions) == 1  # type: ignore[arg-type]


def _test_limits(wafv2_sections):
    wafv2_limits = wafv2_sections["wafv2_limits"]
    wafv2_limits_results = wafv2_limits.run().results

    assert wafv2_limits.cache_interval == 300
    assert wafv2_limits.period == 600
    assert wafv2_limits.name == "wafv2_limits"

    for result in wafv2_limits_results:
        if result.piggyback_hostname == "":
            assert len(result.content) == 4
        else:
            assert len(result.content) == 1


@pytest.mark.parametrize("names,tags,found_instances", wafv2_params)
def test_agent_aws_wafv2_limits(
    get_wafv2_sections: CreateWafv2Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_instances: Sequence[str],
) -> None:
    for wafv2_sections in get_wafv2_sections(names, tags):
        _test_limits(wafv2_sections)


def _test_summary(wafv2_summary, found_instances):
    wafv2_summary_results = wafv2_summary.run().results

    assert wafv2_summary.cache_interval == 300
    assert wafv2_summary.period == 600
    assert wafv2_summary.name == "wafv2_summary"

    if found_instances:
        assert len(wafv2_summary_results) == 1
        wafv2_summary_results = wafv2_summary_results[0]
        assert wafv2_summary_results.piggyback_hostname == ""
        assert len(wafv2_summary_results.content) == len(found_instances)

    else:
        assert len(wafv2_summary_results) == 0


@pytest.mark.parametrize("names,tags,found_instances", wafv2_params)
def test_agent_aws_wafv2_summary_w_limits(
    get_wafv2_sections: CreateWafv2Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_instances: Sequence[str],
) -> None:
    for wafv2_sections in get_wafv2_sections(names, tags):
        _wafv2_limits_results = wafv2_sections["wafv2_limits"].run().results
        _test_summary(wafv2_sections["wafv2_summary"], found_instances)


@pytest.mark.parametrize("names,tags,found_instances", wafv2_params)
def test_agent_aws_wafv2_summary_wo_limits(
    get_wafv2_sections: CreateWafv2Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_instances: Sequence[str],
) -> None:
    for wafv2_sections in get_wafv2_sections(names, tags):
        _test_summary(wafv2_sections["wafv2_summary"], found_instances)


def _test_web_acl(wafv2_sections, found_instances):
    _wafv2_summary_results = wafv2_sections["wafv2_summary"].run().results
    wafv2_web_acl = wafv2_sections["wafv2_web_acl"]
    wafv2_web_acl_results = wafv2_web_acl.run().results

    assert wafv2_web_acl.cache_interval == 300
    assert wafv2_web_acl.period == 600
    assert wafv2_web_acl.name == "wafv2_web_acl"
    assert len(wafv2_web_acl_results) == len(found_instances)

    for result in wafv2_web_acl_results:
        assert result.piggyback_hostname != ""
        assert len(result.content) == 2


@pytest.mark.parametrize("names,tags,found_instances", wafv2_params)
def test_agent_aws_wafv2_web_acls_w_limits(
    get_wafv2_sections: CreateWafv2Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_instances: Sequence[str],
) -> None:
    for wafv2_sections in get_wafv2_sections(names, tags):
        _wafv2_limits_results = wafv2_sections["wafv2_limits"].run().results
        _test_web_acl(wafv2_sections, found_instances)


@pytest.mark.parametrize("names,tags,found_instances", wafv2_params)
def test_agent_aws_wafv2_web_acls_wo_limits(
    get_wafv2_sections: CreateWafv2Sections,
    names: Sequence[str] | None,
    tags: OverallTags,
    found_instances: Sequence[str],
) -> None:
    for wafv2_sections in get_wafv2_sections(names, tags):
        _test_web_acl(wafv2_sections, found_instances)


@pytest.mark.parametrize(
    "tag_import, expected_tags",
    [
        (
            TagsImportPatternOption.import_all,
            {
                "ARN-0": ["Key-0", "Key-1", "Key-2"],
                "ARN-1": ["Key-0", "Key-1", "Key-2"],
                "ARN-2": [],
            },
        ),
        (r".*-1$", {"ARN-0": ["Key-1"], "ARN-1": ["Key-1"], "ARN-2": []}),
        (
            TagsImportPatternOption.ignore_all,
            {"ARN-0": [], "ARN-1": [], "ARN-2": []},
        ),
    ],
)
def test_agent_aws_wafv2_summary_filters_tags(
    get_wafv2_sections: CreateWafv2Sections,
    tag_import: TagsOption,
    expected_tags: dict[str, Sequence[str]],
) -> None:
    for wafv2_sections in get_wafv2_sections(None, (None, None), tag_import):
        wafv2_sections["wafv2_limits"].run()
        wafv2_summary_results = wafv2_sections["wafv2_summary"].run().results
        wafv2_summary_result = wafv2_summary_results[0]

        for result in wafv2_summary_result.content:
            assert list(result["TagsForCmkLabels"].keys()) == expected_tags[result["ARN"]]
