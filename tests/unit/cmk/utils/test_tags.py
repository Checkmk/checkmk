#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.tags import (
    get_effective_tag_config,
    get_tag_to_group_map,
    TagConfig,
    TagConfigSpec,
    TagGroupID,
    TagGroupSpec,
    TagID,
)


def test_get_tag_to_group_map() -> None:
    tag_config = TagConfig.from_config(
        {
            "aux_tags": [{"id": TagID("bla"), "title": "bl\xfcb"}],
            "tag_groups": [
                {
                    "id": TagGroupID("criticality"),
                    "tags": [
                        {
                            "aux_tags": [TagID("bla")],
                            "id": TagID("prod"),
                            "title": "Productive system",
                        },
                    ],
                    "title": "Criticality",
                },
                {
                    "id": TagGroupID("networking"),
                    "tags": [
                        {
                            "aux_tags": [],
                            "id": TagID("lan"),
                            "title": "Local network (low latency)",
                        },
                    ],
                    "title": "Networking Segment",
                },
            ],
        }
    )
    assert get_tag_to_group_map(tag_config) == {
        "bla": "bla",
        "lan": "networking",
        "prod": "criticality",
    }


def test_tag_to_group_map() -> None:
    # Typing forces us to use the TagConfigSpec constructor,
    # but this is actually the raw configuration
    tag_config = TagConfigSpec(
        aux_tags=[],
        tag_groups=[
            TagGroupSpec(
                id=TagGroupID("dingeling"),
                title="Dung",
                tags=[
                    {"aux_tags": [], "id": TagID("dong"), "title": "ABC"},
                ],
            )
        ],
    )

    assert get_tag_to_group_map(get_effective_tag_config(tag_config)) == {
        TagID("all-agents"): TagGroupID("agent"),
        TagID("auto-piggyback"): TagGroupID("piggyback"),
        TagID("cmk-agent"): TagGroupID("agent"),
        TagID("checkmk-agent"): TagGroupID("checkmk-agent"),
        TagID("dong"): TagGroupID("dingeling"),
        TagID("ip-v4"): TagGroupID("ip-v4"),
        TagID("ip-v4-only"): TagGroupID("address_family"),
        TagID("ip-v4v6"): TagGroupID("address_family"),
        TagID("ip-v6"): TagGroupID("ip-v6"),
        TagID("ip-v6-only"): TagGroupID("address_family"),
        TagID("no-agent"): TagGroupID("agent"),
        TagID("no-ip"): TagGroupID("address_family"),
        TagID("no-piggyback"): TagGroupID("piggyback"),
        TagID("no-snmp"): TagGroupID("snmp_ds"),
        TagID("piggyback"): TagGroupID("piggyback"),
        TagID("ping"): TagGroupID("ping"),
        TagID("snmp"): TagGroupID("snmp"),
        TagID("snmp-v1"): TagGroupID("snmp_ds"),
        TagID("snmp-v2"): TagGroupID("snmp_ds"),
        TagID("special-agents"): TagGroupID("agent"),
        TagID("tcp"): TagGroupID("tcp"),
    }
