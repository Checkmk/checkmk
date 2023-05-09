#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Union

import pytest
from _pytest.monkeypatch import MonkeyPatch

from cmk.utils.tags import TagConfig
from cmk.utils.type_defs import TagConditionNE, TaggroupID, TagID

from cmk.gui.htmllib import HTML
from cmk.gui.wato.pages.rulesets import config, RuleConditionRenderer


@pytest.fixture(name="tag_config")
def fixture_tag_config():
    tag_config = TagConfig()
    tag_config.parse_config({
        "aux_tags": [{
            "id": "aux_tag_1",
            "topic": "Auxiliary tags",
            "title": "Auxiliary tag 1",
        }],
        "tag_groups": [
            {
                "id": "tag_grp_1",
                "topic": "Topic 1",
                "title": "Tag group 1",
                "tags": [
                    {
                        "aux_tags": [],
                        "id": "grp_1_tg_1",
                        "title": "Tag 1.1",
                    },
                    {
                        "aux_tags": [],
                        "id": "grp_1_tg_2",
                        "title": "Tag 1.2",
                    },
                ],
            },
            {
                "id": "tag_grp_2",
                "topic": "Topic 2",
                "title": "Tag group 2",
                "tags": [
                    {
                        "aux_tags": [],
                        "id": "grp_2_tg_1",
                        "title": "Tag 2.1",
                    },
                    {
                        "aux_tags": [],
                        "id": "grp_2_tg_2",
                        "title": "Tag 2.2",
                    },
                ],
            },
            {
                "id": "tag_grp_3",
                "topic": "Topic 3",
                "title": "Tag group 3",
                "tags": [{
                    "aux_tags": [],
                    "id": "grp_3_tg_1",
                    "title": "Tag 3.1",
                },],
            },
        ],
    })
    return tag_config


@pytest.fixture(autouse=True)
def patch_tag_config(
    monkeypatch: MonkeyPatch,
    tag_config: TagConfig,
) -> None:
    monkeypatch.setattr(
        config,
        "tags",
        tag_config,
    )


class TestRuleConditionRenderer:
    @pytest.mark.parametrize(
        "taggroup_id, tag_spec, rendered_condition",
        [
            pytest.param(
                "tag_grp_1",
                "grp_1_tg_1",
                HTML("Host tag: Tag group 1 is <b>Tag 1.1</b>"),
                id="grouped tag",
            ),
            pytest.param(
                "tag_grp_1",
                {"$ne": "grp_1_tg_1"},
                HTML("Host tag: Tag group 1 is <b>not</b> <b>Tag 1.1</b>"),
                id="negated grouped tag",
            ),
            pytest.param(
                "aux_tag_1",
                "aux_tag_1",
                HTML("Host has tag <b>Auxiliary tag 1</b>"),
                id="auxiliary tag",
            ),
            pytest.param(
                "aux_tag_1",
                {"$ne": "aux_tag_1"},
                HTML("Host does not have tag <b>Auxiliary tag 1</b>"),
                id="negated auxiliary tag",
            ),
            pytest.param(
                "xyz",
                "a",
                HTML("Unknown tag: Host has the tag <tt>a</tt>"),
                id="unknown tag group",
            ),
            pytest.param(
                "xyz",
                "grp_1_tg_1",
                HTML("Unknown tag: Host has the tag <tt>grp_1_tg_1</tt>"),
                id="unknown tag",
            ),
        ],
    )
    def test_single_tag_condition(
        self,
        taggroup_id: TaggroupID,
        tag_spec: Union[Optional[TagID], TagConditionNE],
        rendered_condition: HTML,
    ) -> None:
        assert RuleConditionRenderer()._single_tag_condition(
            taggroup_id,
            tag_spec,
        ) == rendered_condition

    def test_tag_condition(self) -> None:
        assert list(RuleConditionRenderer()._tag_conditions({
            "tag_grp_1": {
                "$or": [
                    "grp_1_tg_1",
                    "grp_1_tg_2",
                ]
            },
            "tag_grp_2": {
                "$nor": [
                    "grp_2_tg_1",
                    "grp_2_tg_2",
                ]
            },
            "tag_grp_3": "grp_3_tg_1",
            "aux_tag_1": {
                "$ne": "aux_tag_1"
            },
        })) == [
            HTML(
                "Host tag: Tag group 1 is <b>Tag 1.1</b> <i>or</i> Host tag: Tag group 1 is <b>Tag 1.2</b>"
            ),
            HTML(
                "Neither Host tag: Tag group 2 is <b>Tag 2.1</b> <i>nor</i> Host tag: Tag group 2 is <b>Tag 2.2</b>"
            ),
            HTML("Host tag: Tag group 3 is <b>Tag 3.1</b>"),
            HTML("Host does not have tag <b>Auxiliary tag 1</b>"),
        ]
