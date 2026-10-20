#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.utils import tags
from cmk.utils.rulesets.ruleset_matcher import TagCondition
from cmk.utils.tags import TagGroupID, TagID

import cmk.gui.watolib.tags
import cmk.gui.watolib.utils
from cmk.gui.watolib.hosts_and_folders import folder_tree, FolderTree
from cmk.gui.watolib.rulesets import (
    AllRulesets,
    FolderRulesets,
    Rule,
    RuleConditions,
    RuleOptions,
    Ruleset,
)
from cmk.gui.watolib.tags import (
    change_host_tags,
    OperationReplaceGroupedTags,
    TagCleanupMode,
    TagConfigFile,
)


def _tag_test_cfg():
    return {
        "tag_groups": [
            {
                "id": "criticality",
                "title": "Criticality",
                "tags": [
                    {"id": "prod", "title": "Productive system", "aux_tags": ["bla"]},
                    {"id": "critical", "title": "Business critical", "aux_tags": []},
                    {"id": "test", "title": "Test system", "aux_tags": []},
                    {
                        "id": "offline",
                        "title": "Do not monitor this host",
                        "aux_tags": [],
                    },
                ],
            },
            {
                "id": "networking",
                "title": "Networking Segment",
                "tags": [
                    {
                        "id": "lan",
                        "title": "Local network (low latency)",
                        "aux_tags": [],
                    },
                    {"id": "wan", "title": "WAN (high latency)", "aux_tags": []},
                    {
                        "id": "dmz",
                        "title": "DMZ (low latency, secure access)",
                        "aux_tags": [],
                    },
                ],
            },
        ],
        "aux_tags": [{"id": "bla", "title": "bläää"}],
    }


@pytest.fixture()
def test_cfg() -> Iterator[tags.TagConfig]:
    multisite_dir = Path(cmk.gui.watolib.utils.multisite_dir())
    tags_mk = multisite_dir / "tags.mk"
    hosttags_mk = multisite_dir / "hosttags.mk"

    with tags_mk.open("w", encoding="utf-8") as f:
        f.write(
            """# Created by WATO
# encoding: utf-8

wato_tags = %s
"""
            % repr(_tag_test_cfg())
        )

    with hosttags_mk.open("w", encoding="utf-8") as f:
        f.write("")

    cfg = tags.TagConfig.from_config(TagConfigFile().load_for_reading())

    yield cfg

    if tags_mk.exists():
        tags_mk.unlink()


def test_tag_config_load(request_context: None, test_cfg: tags.TagConfig) -> None:
    assert len(test_cfg.tag_groups) == 2
    assert len(test_cfg.aux_tag_list.get_tags()) == 1


@pytest.mark.usefixtures("request_context", "test_cfg")
def test_tag_config_save(mocker: MockerFixture) -> None:
    export_mock = mocker.patch.object(cmk.gui.watolib.tags, "_export_hosttags_to_php")

    config_file = TagConfigFile()
    base_config_mock = mocker.patch.object(config_file, "_save_base_config")

    cfg = tags.TagConfig()
    cfg.insert_tag_group(
        tags.TagGroup.from_config(
            {
                "id": TagGroupID("tgid2"),
                "topic": "Topics",
                "title": "titlor",
                "tags": [{"id": TagID("tgid2"), "title": "tagid2", "aux_tags": []}],
            }
        )
    )
    config_file.save(cfg.get_dict_format())

    export_mock.assert_called_once()
    base_config_mock.assert_called_once()

    cfg = tags.TagConfig.from_config(config_file.load_for_reading())
    assert len(cfg.tag_groups) == 1
    assert cfg.tag_groups[0].id == "tgid2"


def _save_networking_rule(tree: FolderTree, condition: TagCondition) -> None:
    folder = tree.root_folder()
    ruleset = Ruleset("only_hosts", {})
    ruleset.append_rule(
        folder,
        Rule(
            id_="1",
            folder=folder,
            ruleset=ruleset,
            conditions=RuleConditions(
                host_folder=folder.path(),
                host_tags={TagGroupID("networking"): condition},
                host_label_groups=None,
                host_name=None,
                service_description=None,
                service_label_groups=None,
            ),
            options=RuleOptions(disabled=None, description="", comment="", docu_url=""),
            value=True,
        ),
    )
    FolderRulesets({ruleset.name: ruleset}, folder=folder).save_folder()


def _networking_conditions() -> list[TagCondition | None]:
    return [
        rule.conditions.host_tags.get(TagGroupID("networking"))
        for _folder, _index, rule in AllRulesets.load_all_rulesets().get("only_hosts").get_rules()
    ]


@pytest.mark.usefixtures("with_admin_login")
@pytest.mark.parametrize(
    "condition",
    [
        pytest.param({"$or": [TagID("lan"), TagID("wan")]}, id="one of"),
        pytest.param({"$nor": [TagID("lan"), TagID("wan")]}, id="none of"),
    ],
)
def test_change_host_tags_finds_tag_in_list_condition(
    condition: TagCondition,
) -> None:
    tree = folder_tree()
    _save_networking_rule(tree, condition)

    _affected_folders, _affected_hosts, affected_rulesets = change_host_tags(
        OperationReplaceGroupedTags(
            TagGroupID("networking"), remove_tag_ids=[TagID("lan")], replace_tag_ids={}
        ),
        TagCleanupMode.CHECK,
    )

    assert [ruleset.name for ruleset in affected_rulesets] == ["only_hosts"]


@pytest.mark.usefixtures("with_admin_login")
@pytest.mark.parametrize(
    "condition, replace_tag_ids, mode, expected",
    [
        pytest.param(
            {"$or": [TagID("lan"), TagID("wan")]},
            {},
            TagCleanupMode.DELETE,
            [{"$or": [TagID("wan")]}],
            id="remove from one of",
        ),
        pytest.param(
            {"$nor": [TagID("lan"), TagID("wan")]},
            {TagID("lan"): TagID("dmz")},
            TagCleanupMode.DELETE,
            [{"$nor": [TagID("dmz"), TagID("wan")]}],
            id="rename in none of",
        ),
        pytest.param(
            {"$or": [TagID("lan")]},
            {},
            TagCleanupMode.DELETE,
            [],
            id="emptied one of deletes rule",
        ),
        pytest.param(
            {"$or": [TagID("lan")]},
            {},
            TagCleanupMode.REMOVE,
            [None],
            id="emptied one of drops condition",
        ),
        pytest.param(
            {"$nor": [TagID("lan")]},
            {},
            TagCleanupMode.DELETE,
            [None],
            id="emptied none of drops condition",
        ),
    ],
)
def test_change_host_tags_updates_list_condition(
    condition: TagCondition,
    replace_tag_ids: dict[TagID | None, TagID],
    mode: TagCleanupMode,
    expected: list[TagCondition | None],
) -> None:
    tree = folder_tree()
    _save_networking_rule(tree, condition)

    change_host_tags(
        OperationReplaceGroupedTags(
            TagGroupID("networking"),
            remove_tag_ids=[] if replace_tag_ids else [TagID("lan")],
            replace_tag_ids=replace_tag_ids,
        ),
        mode,
    )

    assert _networking_conditions() == expected
