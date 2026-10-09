#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.painter import all_painters
from cmk.ruleset_matcher.tags import TagConfig, TagGroupID, TagID

_TAG_GROUPS = TagConfig.from_config(
    {
        "aux_tags": [],
        "tag_groups": [
            {
                "id": TagGroupID("whoot"),
                "topic": "Blubberei",
                "tags": [{"aux_tags": [], "id": TagID("bla"), "title": "Bla"}],
                "title": "Whoot",
            },
        ],
    }
).tag_groups


@pytest.mark.usefixtures("load_config")
def test_host_tag_painter_registration() -> None:
    assert "host_tag_whoot" in all_painters(_TAG_GROUPS)


def test_host_tag_painter_titles_itself_after_its_tag_group() -> None:
    assert str(all_painters(_TAG_GROUPS)["host_tag_whoot"].static_title) == (
        "Host tag: Blubberei  / Whoot"
    )
