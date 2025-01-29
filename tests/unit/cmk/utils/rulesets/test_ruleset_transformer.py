#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets import ruleset_matcher
from cmk.utils.tags import TagConfig, TagGroupID, TagID


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
    assert ruleset_matcher.get_tag_to_group_map(tag_config) == {
        "bla": "bla",
        "lan": "networking",
        "prod": "criticality",
    }
