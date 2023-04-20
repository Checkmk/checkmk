#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.utils.paths
import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher
import cmk.utils.tags


def test_get_tag_to_group_map() -> None:
    tag_config = cmk.utils.tags.TagConfig.from_config(
        {
            "aux_tags": [{"id": "bla", "title": "bl\xfcb"}],
            "tag_groups": [
                {
                    "id": "criticality",
                    "tags": [
                        {"aux_tags": ["bla"], "id": "prod", "title": "Productive system"},
                    ],
                    "title": "Criticality",
                },
                {
                    "id": "networking",
                    "tags": [
                        {"aux_tags": [], "id": "lan", "title": "Local network (low latency)"},
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
