#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.hostaddress import HostName
from cmk.ruleset_matcher.tags import (
    HostTags,
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
