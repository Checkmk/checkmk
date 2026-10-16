#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.views.sorter import all_sorters
from cmk.ruleset_matcher.tags import TagConfig, TagGroupID, TagID


def test_host_tag_sorter_registration() -> None:
    tags = TagConfig.from_config(
        {
            "aux_tags": [],
            "tag_groups": [
                {
                    "id": TagGroupID("whoot"),
                    "topic": "Blubberei",
                    "tags": [
                        {
                            "aux_tags": [],
                            "id": TagID("bla"),
                            "title": "Bla",
                        },
                    ],
                    "title": "Whoot",
                },
            ],
        }
    )
    assert "host_tag_whoot" in all_sorters(tags.tag_groups)
