#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ruleset_matcher.tags import (
    expand_host_specs,
    HostSelectionError,
    HostTags,
    hosttags_match_taglist,
    TagConfigSpec,
    TagGroupID,
    TagID,
)

_EMPTY_TAG_CONFIG = TagConfigSpec(tag_groups=[], aux_tags=[])


def test_tag_list_of_host() -> None:
    """tag_list returns all tag values plus the host path and site:<id> tag."""
    xyz_host = HostName("xyz")
    # raw_host_tags as WATO would store them: primary tag groups plus aux tags
    xyz_raw_tags = {
        "address_family": "ip-v4-only",
        "agent": "cmk-agent",
        "checkmk-agent": "checkmk-agent",  # aux tag of cmk-agent
        "criticality": "prod",
        "ip-v4": "ip-v4",  # aux tag of ip-v4-only
        "networking": "lan",
        "piggyback": "auto-piggyback",
        "site": "unit",
        "snmp_ds": "no-snmp",
        "tcp": "tcp",  # aux tag of cmk-agent
    }
    host_tags = HostTags.make(
        host_paths={xyz_host: "/wato/"},
        tag_config_spec=_EMPTY_TAG_CONFIG,
        raw_host_tags={xyz_host: xyz_raw_tags},
        tagged_hosts=["xyz"],
        shadow_hosts={},
        site_id="mySite",
    )
    assert set(host_tags.tag_list(xyz_host)) == {
        TagID("/wato/"),
        TagID("lan"),
        TagID("ip-v4"),
        TagID("checkmk-agent"),
        TagID("cmk-agent"),
        TagID("no-snmp"),
        TagID("tcp"),
        TagID("auto-piggyback"),
        TagID("ip-v4-only"),
        TagID("site:unit"),
        TagID("prod"),
    }


def test_fallback_tags_for_unknown_host() -> None:
    """Unknown hosts fall back to a set of default tags including the site id."""
    unknown_host = HostName("unknown_host")
    host_tags = HostTags.make(
        host_paths={},
        tag_config_spec=_EMPTY_TAG_CONFIG,
        raw_host_tags={},
        tagged_hosts=(),
        shadow_hosts={},
        site_id="mySite",
    )
    assert host_tags.tags(unknown_host) == {
        TagGroupID("piggyback"): TagID("auto-piggyback"),
        TagGroupID("networking"): TagID("lan"),
        TagGroupID("agent"): TagID("cmk-agent"),
        TagGroupID("criticality"): TagID("prod"),
        TagGroupID("snmp_ds"): TagID("no-snmp"),
        TagGroupID("site"): TagID("mySite"),
        TagGroupID("address_family"): TagID("ip-v4-only"),
    }
    assert set(host_tags.tag_list(unknown_host)) == {
        TagID("/"),
        TagID("no-snmp"),
        TagID("prod"),
        TagID("auto-piggyback"),
        TagID("ip-v4-only"),
        TagID("lan"),
        TagID("cmk-agent"),
        TagID("site:mySite"),
    }


def test_tags_of_host() -> None:
    """tags() returns the stored tag groups map; aux tags appear as separate entries."""
    xyz_host = HostName("xyz")
    test_host = HostName("test-host")

    # agent=cmk-agent carries aux tags tcp and checkmk-agent
    xyz_tags = {
        TagGroupID("address_family"): TagID("ip-v4-only"),
        TagGroupID("agent"): TagID("cmk-agent"),
        TagGroupID("checkmk-agent"): TagID("checkmk-agent"),
        TagGroupID("criticality"): TagID("prod"),
        TagGroupID("ip-v4"): TagID("ip-v4"),
        TagGroupID("networking"): TagID("lan"),
        TagGroupID("piggyback"): TagID("auto-piggyback"),
        TagGroupID("site"): TagID("unit"),
        TagGroupID("snmp_ds"): TagID("no-snmp"),
        TagGroupID("tcp"): TagID("tcp"),
    }
    # agent=no-agent has no aux tags, so tcp and checkmk-agent are absent
    test_host_tags = {
        TagGroupID("address_family"): TagID("ip-v4-only"),
        TagGroupID("agent"): TagID("no-agent"),
        TagGroupID("criticality"): TagID("prod"),
        TagGroupID("ip-v4"): TagID("ip-v4"),
        TagGroupID("networking"): TagID("lan"),
        TagGroupID("piggyback"): TagID("auto-piggyback"),
        TagGroupID("site"): TagID("unit"),
        TagGroupID("snmp_ds"): TagID("no-snmp"),
    }

    host_tags = HostTags(
        host_tags_sequences={},
        host_tags_maps={xyz_host: xyz_tags, test_host: test_host_tags},
        site_id="mySite",
    )

    assert host_tags.tags(xyz_host) == xyz_tags
    assert host_tags.tags(test_host) == test_host_tags


def test_hosttags_match_taglist() -> None:
    assert hosttags_match_taglist([TagID("no-agent")], [TagID("no-agent")])
    assert hosttags_match_taglist([TagID("no-agent"), TagID("test")], [TagID("no-agent")])
    assert hosttags_match_taglist(
        [TagID("no-agent"), TagID("test")], [TagID("no-agent"), TagID("test")]
    )


def test_hosttags_match_taglist_not_matching() -> None:
    assert not hosttags_match_taglist([TagID("no-agent")], [TagID("test")])
    assert not hosttags_match_taglist(
        [TagID("tag"), TagID("no-agent"), TagID("test2")], [TagID("test")]
    )
    assert not hosttags_match_taglist(
        [TagID("no-agent"), TagID("test")], [TagID("test"), TagID("tag3")]
    )


def test_hosttags_match_taglist_negate() -> None:
    assert not hosttags_match_taglist(
        [TagID("no-agent"), TagID("test")], [TagID("no-agent"), TagID("!test")]
    )
    assert hosttags_match_taglist([TagID("no-agent")], [TagID("no-agent"), TagID("!test")])


_HOST_TAGS = {
    HostName("lan1"): [TagID("lan")],
    HostName("lan2"): [TagID("lan")],
    HostName("wan1"): [TagID("wan")],
    HostName("wan-test"): [TagID("wan"), TagID("test")],
}


def _expand_host_specs(
    host_specs: Sequence[str],
    host_tags: Mapping[HostName, Sequence[TagID]] = _HOST_TAGS,
) -> Sequence[HostName]:
    return expand_host_specs(
        host_specs,
        choose_from=host_tags.keys(),
        host_tags=HostTags(host_tags_sequences=host_tags, host_tags_maps={}, site_id="site1"),
    )


def test_expand_host_specs_keeps_host_names_in_given_order() -> None:
    assert _expand_host_specs(["wan1", "lan1"]) == [HostName("wan1"), HostName("lan1")]


@pytest.mark.parametrize("arg", ["@wan", "wan"])
def test_expand_host_specs_selects_hosts_by_tag(arg: str) -> None:
    assert sorted(_expand_host_specs([arg])) == [HostName("wan-test"), HostName("wan1")]


def test_expand_host_specs_requires_all_comma_separated_tags() -> None:
    assert _expand_host_specs(["@wan,test"]) == [HostName("wan-test")]


@pytest.mark.parametrize(
    "arg, expected",
    [
        pytest.param("lan", [HostName("lan")], id="host name wins over tag"),
        pytest.param(
            "@lan", [HostName("lan"), HostName("lan1"), HostName("lan2")], id="@ forces tag"
        ),
    ],
)
def test_expand_host_specs_at_prefix_disambiguates_host_name_and_tag(
    arg: str, expected: Sequence[HostName]
) -> None:
    host_tags = {**_HOST_TAGS, HostName("lan"): [TagID("lan")]}

    assert sorted(_expand_host_specs([arg], host_tags)) == expected


def test_expand_host_specs_repeats_hosts_matched_by_several_args() -> None:
    # Pins current behavior: duplicates are not removed.
    assert sorted(_expand_host_specs(["lan1", "@lan"])) == [
        HostName("lan1"),
        HostName("lan1"),
        HostName("lan2"),
    ]


@pytest.mark.parametrize("arg", ["unknown-host", "@dmz", ""])
def test_expand_host_specs_rejects_spec_without_match(arg: str) -> None:
    with pytest.raises(HostSelectionError, match="does not match any host"):
        _expand_host_specs([arg])


def test_expand_host_specs_only_returns_valid_hosts() -> None:
    hostlist = expand_host_specs(
        ["@lan"],
        choose_from=[HostName("lan1")],
        host_tags=HostTags(host_tags_sequences=_HOST_TAGS, host_tags_maps={}, site_id="site1"),
    )

    assert hostlist == [HostName("lan1")]
