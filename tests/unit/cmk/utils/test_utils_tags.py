#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.tags as tags
from cmk.utils.exceptions import MKGeneralException


@pytest.fixture(name="test_cfg")
def fixture_test_cfg() -> tags.TagConfig:
    cfg = tags.TagConfig()
    cfg.parse_config(
        {
            "aux_tags": [
                {
                    "id": "bla",
                    "topic": "Bluna",
                    "title": "bläää",
                }
            ],
            "tag_groups": [
                {
                    "id": "criticality",
                    "topic": "Blubberei",
                    "tags": [
                        {"aux_tags": ["bla"], "id": "prod", "title": "Productive system"},
                        {"aux_tags": [], "id": "critical", "title": "Business critical"},
                        {"aux_tags": [], "id": "test", "title": "Test system"},
                        {"aux_tags": [], "id": "offline", "title": "Do not monitor this host"},
                    ],
                    "title": "Criticality",
                },
                {
                    "id": "networking",
                    "tags": [
                        {"aux_tags": [], "id": "lan", "title": "Local network (low latency)"},
                        {"aux_tags": [], "id": "wan", "title": "WAN (high latency)"},
                        {"aux_tags": [], "id": "dmz", "title": "DMZ (low latency, secure access)"},
                    ],
                    "title": "Networking Segment",
                },
                {
                    "id": "none_choice",
                    "tags": [
                        {"aux_tags": ["bla"], "id": None, "title": "None"},
                        {"aux_tags": [], "id": "none_val", "title": "None value"},
                    ],
                    "title": "None choice",
                },
                {
                    "id": "none_2",
                    "tags": [
                        {"aux_tags": ["bla"], "id": "none_val", "title": "None value 2"},
                        {"aux_tags": [], "id": "none_val_2", "title": "None value again"},
                    ],
                    "title": "None 2",
                },
            ],
        }
    )
    return cfg


def test_tag_config() -> None:
    cfg = tags.TagConfig()
    assert cfg.tag_groups == []
    assert cfg.aux_tag_list.get_tags() == []


def test_iadd_tag_config(test_cfg: tags.TagConfig) -> None:
    cfg2 = tags.TagConfig()
    cfg2.insert_tag_group(tags.TagGroup(("tgid3", "Topics/titlor", [("tgid3", "tagid3", [])])))
    cfg2.insert_tag_group(tags.TagGroup(("tgid2", "BLAAA", [("tgid2", "tagid2", [])])))
    cfg2.aux_tag_list.append(tags.AuxTag(("blub", "BLUB")))
    cfg2.aux_tag_list.append(tags.AuxTag(("bla", "BLUB")))

    test_cfg += cfg2

    assert len(test_cfg.tag_groups) == 6
    assert test_cfg.tag_groups[0].id == "criticality"
    assert test_cfg.tag_groups[1].id == "networking"
    assert test_cfg.tag_groups[2].id == "none_choice"
    assert test_cfg.tag_groups[3].id == "none_2"
    assert test_cfg.tag_groups[4].id == "tgid3"
    assert test_cfg.tag_groups[4].title == "titlor"

    aux_tags = test_cfg.get_aux_tags()
    assert len(aux_tags) == 2
    assert aux_tags[0].id == "bla"
    assert aux_tags[0].title == "bläää"
    assert aux_tags[1].id == "blub"


def test_tag_config_get_topic_choices(test_cfg: tags.TagConfig) -> None:
    assert sorted(test_cfg.get_topic_choices()) == sorted(
        [
            ("Blubberei", "Blubberei"),
            ("Bluna", "Bluna"),
            ("Tags", "Tags"),
        ]
    )


def test_tag_groups_by_topic(test_cfg: tags.TagConfig) -> None:
    expected_groups = {
        "Blubberei": ["criticality"],
        "Tags": ["networking", "none_choice", "none_2"],
    }

    actual_groups = dict(test_cfg.get_tag_groups_by_topic())
    assert sorted(actual_groups.keys()) == sorted(expected_groups.keys())

    for topic, tag_group_ids in expected_groups.items():
        tg_ids = [tg.id for tg in actual_groups[topic] if tg.id is not None]
        assert sorted(tg_ids) == sorted(tag_group_ids)


def test_tag_group_exists(test_cfg: tags.TagConfig) -> None:
    assert test_cfg.tag_group_exists("networking") is True
    assert test_cfg.tag_group_exists("netnet") is False


def test_tag_config_get_tag_group(test_cfg: tags.TagConfig) -> None:
    assert test_cfg.get_tag_group("xyz") is None
    assert isinstance(test_cfg.get_tag_group("networking"), tags.TagGroup)


def test_tag_config_remove_tag_group(test_cfg: tags.TagConfig) -> None:
    assert test_cfg.get_tag_group("xyz") is None
    test_cfg.remove_tag_group("xyz")  # not existing -> fine

    assert test_cfg.get_tag_group("networking") is not None
    test_cfg.remove_tag_group("networking")
    assert test_cfg.get_tag_group("networking") is None


def test_tag_config_get_tag_group_choices(test_cfg: tags.TagConfig) -> None:
    assert test_cfg.get_tag_group_choices() == [
        ("criticality", "Blubberei / Criticality"),
        ("networking", "Networking Segment"),
        ("none_choice", "None choice"),
        ("none_2", "None 2"),
    ]


def test_tag_config_get_aux_tags(test_cfg: tags.TagConfig) -> None:
    assert [a.id for a in test_cfg.get_aux_tags()] == ["bla"]


def test_tag_config_get_aux_tags_by_tag(test_cfg: tags.TagConfig) -> None:
    assert test_cfg.get_aux_tags_by_tag() == {
        None: ["bla"],
        "none_val": ["bla"],  # none_val from none_2 overwrites none_val from none_choice
        "none_val_2": [],
        "critical": [],
        "dmz": [],
        "lan": [],
        "offline": [],
        "prod": ["bla"],
        "test": [],
        "wan": [],
    }


def test_tag_config_get_aux_tags_by_topic(test_cfg: tags.TagConfig) -> None:
    expected_groups = {
        "Bluna": ["bla"],
    }

    actual_groups = dict(test_cfg.get_aux_tags_by_topic())
    assert sorted(actual_groups.keys()) == sorted(expected_groups.keys())

    for topic, tag_group_ids in expected_groups.items():
        tg_ids = [tg.id for tg in actual_groups[topic]]
        assert sorted(tg_ids) == sorted(tag_group_ids)


def test_tag_config_get_tag_ids(test_cfg: tags.TagConfig) -> None:
    assert test_cfg.get_tag_ids() == {
        None,
        "none_val",
        "bla",
        "critical",
        "dmz",
        "lan",
        "offline",
        "prod",
        "test",
        "wan",
        "none_val_2",
    }


def test_tag_config_get_tag_ids_with_group_prefix(test_cfg: tags.TagConfig) -> None:
    assert test_cfg.get_tag_ids_by_group() == {
        ("bla", "bla"),
        ("criticality", "critical"),
        ("criticality", "offline"),
        ("criticality", "prod"),
        ("criticality", "test"),
        ("networking", "dmz"),
        ("networking", "lan"),
        ("networking", "wan"),
        ("none_2", "none_val_2"),
        ("none_2", "none_val"),
        ("none_choice", None),
        ("none_choice", "none_val"),
    }


def test_tag_config_get_tag_or_aux_tag(test_cfg: tags.TagConfig) -> None:
    assert test_cfg.get_tag_or_aux_tag("nonexisting_group", "blä") is None
    assert isinstance(test_cfg.get_tag_or_aux_tag("nonexisting_group", "bla"), tags.AuxTag)
    assert isinstance(test_cfg.get_tag_or_aux_tag("criticality", "prod"), tags.GroupedTag)


def test_tag_config_get_tag_or_aux_tag_duplicate(test_cfg: tags.TagConfig) -> None:
    tag_none_choice_1 = test_cfg.get_tag_or_aux_tag("none_choice", "none_val")
    assert isinstance(tag_none_choice_1, tags.GroupedTag)
    assert tag_none_choice_1.title == "None value"
    assert tag_none_choice_1.group.id == "none_choice"
    tag_none_choice_2 = test_cfg.get_tag_or_aux_tag("none_2", "none_val")
    assert isinstance(tag_none_choice_2, tags.GroupedTag)
    assert tag_none_choice_2.title == "None value 2"
    assert tag_none_choice_2.group.id == "none_2"


@pytest.fixture(name="cfg")
def fixture_cfg() -> tags.TagConfig:
    return tags.TagConfig()


def test_tag_config_insert_tag_group_twice(cfg: tags.TagConfig) -> None:
    cfg.insert_tag_group(tags.TagGroup(("tgid2", "Topics/titlor", [("tgid2", "tagid2", [])])))
    assert cfg.tag_groups[-1].id == "tgid2"

    cfg.insert_tag_group(tags.TagGroup(("tgidX", "Topics/titlor", [("tgid2", "tagid2", [])])))
    cfg.validate_config()

    with pytest.raises(MKGeneralException, match="is used twice"):
        cfg.insert_tag_group(tags.TagGroup(("tgid2", "Topics/titlor", [("tgid3", "tagid3", [])])))
        cfg.validate_config()


def test_tag_config_insert_tag_group_missing_id(cfg: tags.TagConfig) -> None:
    with pytest.raises(MKGeneralException, match="Please specify"):
        tg = tags.TagGroup()
        tg.id = ""
        cfg.insert_tag_group(tg)
        cfg.validate_config()


def test_tag_config_insert_tag_group_missing_title(cfg: tags.TagConfig) -> None:
    with pytest.raises(MKGeneralException, match="Please specify"):
        tg = tags.TagGroup()
        tg.id = "abc"
        tg.title = ""
        cfg.insert_tag_group(tg)
        cfg.validate_config()


def test_tag_config_insert_tag_group_missing_multiple_tags_empty(cfg: tags.TagConfig) -> None:
    with pytest.raises(MKGeneralException, match="Only one tag may be empty"):
        tg = tags.TagGroup(
            (
                "tgid3",
                "Topics/titlor",
                [
                    (None, "tagid2", []),
                    ("", "tagid3", []),
                ],
            )
        )
        cfg.insert_tag_group(tg)
        cfg.validate_config()


def test_tag_config_insert_tag_group_missing_tag_not_unique(cfg: tags.TagConfig) -> None:
    with pytest.raises(MKGeneralException, match="must be unique"):
        tg = tags.TagGroup(
            (
                "tgid4",
                "Topics/titlor",
                [
                    ("ding", "tagid2", []),
                    ("ding", "tagid3", []),
                ],
            )
        )
        cfg.insert_tag_group(tg)
        cfg.validate_config()


def test_tag_config_insert_tag_group_aux_tag_id_conflict(cfg: tags.TagConfig) -> None:
    cfg.aux_tag_list.append(tags.AuxTag(("bla", "BLAAAA")))
    tg = tags.TagGroup(
        (
            "tgid6",
            "Topics/titlor",
            [
                ("bla", "tagid2", []),
            ],
        )
    )
    cfg.insert_tag_group(tg)
    cfg.validate_config()

    with pytest.raises(MKGeneralException, match="is used twice"):
        tg = tags.TagGroup(
            (
                "bla",
                "Topics/titlor",
                [
                    ("tagid2", "tagid2", []),
                ],
            )
        )
        cfg.insert_tag_group(tg)
        cfg.validate_config()


def test_tag_config_insert_tag_group_no_tag(cfg: tags.TagConfig) -> None:
    with pytest.raises(MKGeneralException, match="at least one tag"):
        tg = tags.TagGroup(("tgid7", "Topics/titlor", []))
        cfg.insert_tag_group(tg)
        cfg.validate_config()


def test_tag_config_update_tag_group(test_cfg: tags.TagConfig) -> None:
    with pytest.raises(MKGeneralException, match="Unknown tag group"):
        test_cfg.update_tag_group(
            tags.TagGroup(("tgid2", "Topics/titlor", [("tgid2", "tagid2", [])]))
        )
        test_cfg.validate_config()

    test_cfg.update_tag_group(tags.TagGroup(("networking", "title", [("tgid2", "tagid2", [])])))
    assert test_cfg.tag_groups[1].title == "title"
    test_cfg.validate_config()


def test_tag_group_get_tag_group_config(test_cfg: tags.TagConfig) -> None:
    tg = test_cfg.get_tag_group("criticality")
    assert tg is not None
    assert tg.get_tag_group_config("prod") == {"bla": "bla", "criticality": "prod"}


def test_tag_group_get_tag_group_config_none_choice(test_cfg: tags.TagConfig) -> None:
    tg = test_cfg.get_tag_group("none_choice")
    assert tg is not None
    assert tg.get_tag_group_config(None) == {"bla": "bla"}


def test_tag_group_get_tag_group_config_none_val(test_cfg: tags.TagConfig) -> None:
    tg = test_cfg.get_tag_group("none_choice")
    assert tg is not None
    assert tg.get_tag_group_config("none_val") == {"none_choice": "none_val"}


def test_tag_group_get_tag_group_config_unknown_choice(test_cfg: tags.TagConfig) -> None:
    tg = test_cfg.get_tag_group("criticality")
    assert tg is not None
    assert tg.get_tag_group_config("prodX") == {"criticality": "prodX"}


def test_aux_tag_list_remove(test_cfg: tags.TagConfig) -> None:
    assert "xyz" not in test_cfg.aux_tag_list.get_tag_ids()
    test_cfg.aux_tag_list.remove("xyz")  # not existing -> fine

    assert "bla" in test_cfg.aux_tag_list.get_tag_ids()
    test_cfg.aux_tag_list.remove("bla")
    assert "bla" not in test_cfg.aux_tag_list.get_tag_ids()
