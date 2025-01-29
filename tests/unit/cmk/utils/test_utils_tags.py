#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.ccc.exceptions import MKGeneralException

from cmk.utils import tags
from cmk.utils.tags import AuxTag, GroupedTag, TagConfig, TagGroup, TagGroupID, TagID


@pytest.fixture(name="test_cfg")
def fixture_test_cfg() -> TagConfig:
    cfg = TagConfig.from_config(
        {
            "aux_tags": [
                {
                    "id": TagID("bla"),
                    "topic": "Bluna",
                    "title": "bläää",
                }
            ],
            "tag_groups": [
                {
                    "id": TagGroupID("criticality"),
                    "topic": "Blubberei",
                    "tags": [
                        {
                            "aux_tags": [TagID("bla")],
                            "id": TagID("prod"),
                            "title": "Productive system",
                        },
                        {"aux_tags": [], "id": TagID("critical"), "title": "Business critical"},
                        {"aux_tags": [], "id": TagID("test"), "title": "Test system"},
                        {
                            "aux_tags": [],
                            "id": TagID("offline"),
                            "title": "Do not monitor this host",
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
                        {"aux_tags": [], "id": TagID("wan"), "title": "WAN (high latency)"},
                        {
                            "aux_tags": [],
                            "id": TagID("dmz"),
                            "title": "DMZ (low latency, secure access)",
                        },
                    ],
                    "title": "Networking Segment",
                },
                {
                    "id": TagGroupID("none_choice"),
                    "tags": [
                        {"aux_tags": [TagID("bla")], "id": None, "title": "None"},
                        {"aux_tags": [], "id": TagID("none_val"), "title": "None value"},
                    ],
                    "title": "None choice",
                },
                {
                    "id": TagGroupID("none_2"),
                    "tags": [
                        {
                            "aux_tags": [TagID("bla")],
                            "id": TagID("none_val"),
                            "title": "None value 2",
                        },
                        {"aux_tags": [], "id": TagID("none_val_2"), "title": "None value again"},
                    ],
                    "title": "None 2",
                },
            ],
        }
    )
    return cfg


def test_tag_config() -> None:
    cfg = TagConfig()
    assert cfg.tag_groups == []
    assert cfg.aux_tag_list.get_tags() == []


def test_iadd_tag_config(test_cfg: TagConfig) -> None:
    cfg2 = TagConfig()
    cfg2.insert_tag_group(
        TagGroup.from_config(
            {
                "id": TagGroupID("tgid3"),
                "title": "titlor",
                "topic": "Topics",
                "tags": [
                    {
                        "id": TagID("tgid3"),
                        "title": "tagid3",
                        "aux_tags": [],
                    }
                ],
            }
        )
    )
    cfg2.insert_tag_group(
        TagGroup.from_config(
            {
                "id": TagGroupID("tgid2"),
                "title": "BLAAA",
                "tags": [{"id": TagID("tgid2"), "title": "tagid2", "aux_tags": []}],
            }
        )
    )
    cfg2.aux_tag_list.append(AuxTag.from_config({"id": TagID("blub"), "title": "BLUB"}))
    cfg2.aux_tag_list.append(AuxTag.from_config({"id": TagID("bla"), "title": "BLUB"}))

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


def test_tag_config_get_topic_choices(test_cfg: TagConfig) -> None:
    assert sorted(test_cfg.get_topic_choices()) == sorted(
        [
            ("Blubberei", "Blubberei"),
            ("Bluna", "Bluna"),
            ("Tags", "Tags"),
        ]
    )


def test_tag_groups_by_topic(test_cfg: TagConfig) -> None:
    expected_groups = {
        "Blubberei": ["criticality"],
        "Tags": ["networking", "none_choice", "none_2"],
    }

    actual_groups = dict(test_cfg.get_tag_groups_by_topic())
    assert sorted(actual_groups.keys()) == sorted(expected_groups.keys())

    for topic, tag_group_ids in expected_groups.items():
        tg_ids = [tg.id for tg in actual_groups[topic] if tg.id is not None]
        assert sorted(tg_ids) == sorted(tag_group_ids)


def test_tag_group_exists(test_cfg: TagConfig) -> None:
    assert test_cfg.tag_group_exists(TagGroupID("networking")) is True
    assert test_cfg.tag_group_exists(TagGroupID("netnet")) is False


def test_tag_config_get_tag_group(test_cfg: TagConfig) -> None:
    assert test_cfg.get_tag_group(TagGroupID("xyz")) is None
    assert isinstance(test_cfg.get_tag_group(TagGroupID("networking")), TagGroup)


def test_tag_config_remove_tag_group(test_cfg: TagConfig) -> None:
    assert test_cfg.get_tag_group(TagGroupID("xyz")) is None
    test_cfg.remove_tag_group(TagGroupID("xyz"))  # not existing -> fine

    assert test_cfg.get_tag_group(TagGroupID("networking")) is not None
    test_cfg.remove_tag_group(TagGroupID("networking"))
    assert test_cfg.get_tag_group(TagGroupID("networking")) is None


def test_tag_config_get_tag_group_choices(test_cfg: TagConfig) -> None:
    assert test_cfg.get_tag_group_choices() == [
        ("criticality", "Blubberei / Criticality"),
        ("networking", "Networking Segment"),
        ("none_choice", "None choice"),
        ("none_2", "None 2"),
    ]


def test_tag_config_get_aux_tags(test_cfg: TagConfig) -> None:
    assert [a.id for a in test_cfg.get_aux_tags()] == ["bla"]


def test_tag_config_get_aux_tags_by_tag(test_cfg: TagConfig) -> None:
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


def test_tag_config_get_aux_tags_by_topic(test_cfg: TagConfig) -> None:
    expected_groups = {
        "Bluna": ["bla"],
    }

    actual_groups = dict(test_cfg.get_aux_tags_by_topic())
    assert sorted(actual_groups.keys()) == sorted(expected_groups.keys())

    for topic, tag_group_ids in expected_groups.items():
        tg_ids = [tg.id for tg in actual_groups[topic]]
        assert sorted(tg_ids) == sorted(tag_group_ids)


def test_tag_config_get_tag_ids(test_cfg: TagConfig) -> None:
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


def test_tag_config_get_tag_or_aux_tag(test_cfg: TagConfig) -> None:
    assert test_cfg.get_tag_or_aux_tag(TagGroupID("nonexisting_group"), TagID("blä")) is None
    assert isinstance(
        test_cfg.get_tag_or_aux_tag(TagGroupID("nonexisting_group"), TagID("bla")), AuxTag
    )
    assert isinstance(
        test_cfg.get_tag_or_aux_tag(TagGroupID("criticality"), TagID("prod")), GroupedTag
    )


def test_tag_config_get_tag_or_aux_tag_duplicate(test_cfg: TagConfig) -> None:
    tag_none_choice_1 = test_cfg.get_tag_or_aux_tag(TagGroupID("none_choice"), TagID("none_val"))
    assert isinstance(tag_none_choice_1, GroupedTag)
    assert tag_none_choice_1.title == "None value"
    assert tag_none_choice_1.group.id == "none_choice"
    tag_none_choice_2 = test_cfg.get_tag_or_aux_tag(TagGroupID("none_2"), TagID("none_val"))
    assert isinstance(tag_none_choice_2, GroupedTag)
    assert tag_none_choice_2.title == "None value 2"
    assert tag_none_choice_2.group.id == "none_2"


@pytest.fixture(name="cfg")
def fixture_cfg() -> TagConfig:
    return TagConfig()


def test_tag_config_insert_tag_group_twice(cfg: TagConfig) -> None:
    cfg.insert_tag_group(
        TagGroup.from_config(
            {
                "id": TagGroupID("tgid2"),
                "topic": "Topics",
                "title": "titlor",
                "tags": [{"id": TagID("tgid2"), "title": "tagid2", "aux_tags": []}],
            }
        )
    )
    assert cfg.tag_groups[-1].id == "tgid2"

    cfg.insert_tag_group(
        TagGroup.from_config(
            {
                "id": TagGroupID("tgidX"),
                "topic": "Topics",
                "title": "titlor",
                "tags": [{"id": TagID("tgid2"), "title": "tagid2", "aux_tags": []}],
            }
        )
    )
    cfg.validate_config()

    with pytest.raises(MKGeneralException, match="is used twice"):
        cfg.insert_tag_group(
            TagGroup.from_config(
                {
                    "id": TagGroupID("tgid2"),
                    "topic": "Topics",
                    "title": "titlor",
                    "tags": [{"id": TagID("tgid3"), "title": "tagid3", "aux_tags": []}],
                }
            )
        )
        cfg.validate_config()


def test_tag_config_insert_tag_group_missing_id(cfg: TagConfig) -> None:
    with pytest.raises(MKGeneralException, match="Please specify"):
        tg = TagGroup(group_id=TagGroupID(""), title="title", help=None, topic=None, tags=[])
        cfg.insert_tag_group(tg)
        cfg.validate_config()


def test_tag_config_insert_tag_group_missing_title(cfg: TagConfig) -> None:
    with pytest.raises(MKGeneralException, match="Please specify"):
        tg = TagGroup(group_id=TagGroupID("abc"), title="", help=None, topic=None, tags=[])
        cfg.insert_tag_group(tg)
        cfg.validate_config()


def test_tag_config_insert_tag_group_missing_multiple_tags_empty(cfg: TagConfig) -> None:
    with pytest.raises(MKGeneralException, match="Only one tag may be empty"):
        tg = TagGroup.from_config(
            {
                "id": TagGroupID("tgid3"),
                "topic": "Topics",
                "title": "titlor",
                "tags": [
                    {"id": None, "title": "tagid2", "aux_tags": []},
                    {"id": TagID(""), "title": "tagid3", "aux_tags": []},
                ],
            }
        )
        cfg.insert_tag_group(tg)
        cfg.validate_config()


def test_tag_config_insert_tag_group_missing_tag_not_unique(cfg: TagConfig) -> None:
    with pytest.raises(MKGeneralException, match="must be unique"):
        tg = TagGroup.from_config(
            {
                "id": TagGroupID("tgid4"),
                "topic": "Topics",
                "title": "titlor",
                "tags": [
                    {"id": TagID("ding"), "title": "tagid2", "aux_tags": []},
                    {"id": TagID("ding"), "title": "tagid3", "aux_tags": []},
                ],
            }
        )
        cfg.insert_tag_group(tg)
        cfg.validate_config()


def test_tag_config_insert_tag_group_aux_tag_id_conflict(cfg: TagConfig) -> None:
    cfg.aux_tag_list.append(AuxTag.from_config({"id": TagID("bla"), "title": "BLAAAA"}))
    tg = TagGroup.from_config(
        {
            "id": TagGroupID("tgid6"),
            "topic": "Topics",
            "title": "titlor",
            "tags": [
                {"id": TagID("bla"), "title": "tagid2", "aux_tags": []},
            ],
        }
    )
    cfg.insert_tag_group(tg)
    cfg.validate_config()

    with pytest.raises(MKGeneralException, match="is used twice"):
        tg = TagGroup.from_config(
            {
                "id": TagGroupID("bla"),
                "topic": "Topics",
                "title": "titlor",
                "tags": [
                    {"id": TagID("tagid2"), "title": "tagid2", "aux_tags": []},
                ],
            }
        )
        cfg.insert_tag_group(tg)
        cfg.validate_config()


def test_tag_config_insert_tag_group_no_tag(cfg: TagConfig) -> None:
    with pytest.raises(MKGeneralException, match="at least one tag"):
        tg = TagGroup.from_config(
            {"id": TagGroupID("tgid7"), "topic": "Topics", "title": "titlor", "tags": []}
        )
        cfg.insert_tag_group(tg)
        cfg.validate_config()


def test_tag_config_update_tag_group(test_cfg: TagConfig) -> None:
    with pytest.raises(MKGeneralException, match="Unknown tag group"):
        test_cfg.update_tag_group(
            TagGroup.from_config(
                {
                    "id": TagGroupID("tgid2"),
                    "topic": "Topics",
                    "title": "titlor",
                    "tags": [{"id": TagID("tgid2"), "title": "tagid2", "aux_tags": []}],
                }
            )
        )
        test_cfg.validate_config()

    test_cfg.update_tag_group(
        TagGroup.from_config(
            {
                "id": TagGroupID("networking"),
                "title": "title",
                "tags": [{"id": TagID("tgid2"), "title": "tagid2", "aux_tags": []}],
            }
        )
    )
    assert test_cfg.tag_groups[1].title == "title"
    test_cfg.validate_config()


def test_tag_group_get_tag_group_config(test_cfg: TagConfig) -> None:
    tg = test_cfg.get_tag_group(TagGroupID("criticality"))
    assert tg is not None
    assert tg.get_tag_group_config(TagID("prod")) == {
        TagGroupID("bla"): TagID("bla"),
        TagGroupID("criticality"): TagID("prod"),
    }


def test_tag_group_get_tag_group_config_none_choice(test_cfg: TagConfig) -> None:
    tg = test_cfg.get_tag_group(TagGroupID("none_choice"))
    assert tg is not None
    assert tg.get_tag_group_config(None) == {TagGroupID("bla"): TagID("bla")}


def test_tag_group_get_tag_group_config_none_val(test_cfg: TagConfig) -> None:
    tg = test_cfg.get_tag_group(TagGroupID("none_choice"))
    assert tg is not None
    assert tg.get_tag_group_config(TagID("none_val")) == {
        TagGroupID("none_choice"): TagID("none_val")
    }


def test_tag_group_get_tag_group_config_unknown_choice(test_cfg: TagConfig) -> None:
    tg = test_cfg.get_tag_group(TagGroupID("criticality"))
    assert tg is not None
    assert tg.get_tag_group_config(TagID("prodX")) == {TagGroupID("criticality"): TagID("prodX")}


def test_aux_tag_list_remove(test_cfg: TagConfig) -> None:
    xyz = TagID("xyz")
    assert xyz not in test_cfg.aux_tag_list.get_tag_ids()
    test_cfg.aux_tag_list.remove(xyz)  # not existing -> fine

    bla = TagID("bla")
    assert bla in test_cfg.aux_tag_list.get_tag_ids()
    test_cfg.aux_tag_list.remove(bla)
    assert bla not in test_cfg.aux_tag_list.get_tag_ids()


@pytest.mark.parametrize(
    "tag_groups, expected_computed_datasources",
    [
        (
            {},
            tags.ComputedDataSources(
                is_tcp=False,
                is_snmp=False,
                is_all_agents_host=False,
                is_all_special_agents_host=False,
            ),
        ),
        (
            {
                "tcp": "tcp",
            },
            tags.ComputedDataSources(
                is_tcp=True,
                is_snmp=False,
                is_all_agents_host=False,
                is_all_special_agents_host=False,
            ),
        ),
        (
            {
                "snmp_ds": "no-snmp",
            },
            tags.ComputedDataSources(
                is_tcp=False,
                is_snmp=False,
                is_all_agents_host=False,
                is_all_special_agents_host=False,
            ),
        ),
        (
            {
                "snmp_ds": "snmp-v1",
            },
            tags.ComputedDataSources(
                is_tcp=False,
                is_snmp=True,
                is_all_agents_host=False,
                is_all_special_agents_host=False,
            ),
        ),
        (
            {
                "snmp_ds": "snmp-v2",
            },
            tags.ComputedDataSources(
                is_tcp=False,
                is_snmp=True,
                is_all_agents_host=False,
                is_all_special_agents_host=False,
            ),
        ),
        (
            {
                "snmp_ds": "snmp",
            },
            tags.ComputedDataSources(
                is_tcp=False,
                is_snmp=True,
                is_all_agents_host=False,
                is_all_special_agents_host=False,
            ),
        ),
        (
            {
                "agent": "all-agents",
            },
            tags.ComputedDataSources(
                is_tcp=False,
                is_snmp=False,
                is_all_agents_host=True,
                is_all_special_agents_host=False,
            ),
        ),
        (
            {
                "agent": "special-agents",
            },
            tags.ComputedDataSources(
                is_tcp=False,
                is_snmp=False,
                is_all_agents_host=False,
                is_all_special_agents_host=True,
            ),
        ),
    ],
)
def test_compute_datasources(
    tag_groups: Mapping[TagGroupID, TagID], expected_computed_datasources: tags.ComputedDataSources
) -> None:
    assert tags.compute_datasources(tag_groups) == expected_computed_datasources


@pytest.mark.parametrize(
    "computed_datasources_0, computed_datasources_1, expected_datasource_differences",
    [
        (
            tags.ComputedDataSources(
                is_tcp=False,
                is_snmp=False,
                is_all_agents_host=False,
                is_all_special_agents_host=False,
            ),
            tags.ComputedDataSources(
                is_tcp=False,
                is_snmp=False,
                is_all_agents_host=False,
                is_all_special_agents_host=False,
            ),
            [],
        ),
        (
            tags.ComputedDataSources(
                is_tcp=True,
                is_snmp=True,
                is_all_agents_host=True,
                is_all_special_agents_host=True,
            ),
            tags.ComputedDataSources(
                is_tcp=False,
                is_snmp=False,
                is_all_agents_host=False,
                is_all_special_agents_host=False,
            ),
            [
                tags.DataSourceDifference(name="all agents", myself_is=True, other_is=False),
                tags.DataSourceDifference(
                    name="all special agents", myself_is=True, other_is=False
                ),
                tags.DataSourceDifference(name="TCP", myself_is=True, other_is=False),
                tags.DataSourceDifference(name="SNMP", myself_is=True, other_is=False),
            ],
        ),
    ],
)
def test_get_differences_to(
    computed_datasources_0: tags.ComputedDataSources,
    computed_datasources_1: tags.ComputedDataSources,
    expected_datasource_differences: tags.DataSourceDifferences,
) -> None:
    assert (
        computed_datasources_0.get_differences_to(computed_datasources_1)
        == expected_datasource_differences
    )
