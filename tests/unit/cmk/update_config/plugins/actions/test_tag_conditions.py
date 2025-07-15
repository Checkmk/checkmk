#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import MutableMapping

import pytest

from cmk.utils.notify_types import EventRule
from cmk.utils.rulesets.ruleset_matcher import TagCondition
from cmk.utils.tags import BuiltinTagConfig, TagConfig, TagGroupID, TagID

from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.notifications import NotificationRuleConfigFile
from cmk.gui.watolib.tags import TagConfigFile

from cmk.update_config.plugins.actions.tag_conditions import (
    transform_host_tags,
    UpdateNotificationTagConditions,
)


@pytest.mark.parametrize(
    ["tags_as_list", "tags_as_dict"],
    [
        pytest.param(
            ["ip-v4-only", "ip-v4", "ip-v6"],
            {"address_family": "ip-v4-only", "ip-v4": "ip-v4", "ip-v6": "ip-v6"},
            id="Builtin tags without negate",
        ),
        pytest.param(
            ["!ip-v4-only", "!ip-v4", "ip-v6"],
            {"address_family": {"$ne": "ip-v4-only"}, "ip-v4": {"$ne": "ip-v4"}, "ip-v6": "ip-v6"},
            id="Builtin tags with negate",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_tag_conditions_with_builtin_tags(
    tags_as_list: list[str],
    tags_as_dict: MutableMapping[TagGroupID, TagCondition],
) -> None:
    assert (
        transform_host_tags(
            tags_as_list, BuiltinTagConfig().tag_groups, BuiltinTagConfig().aux_tag_list
        )
        == tags_as_dict
    )


@pytest.fixture(name="test_tag_cfg")
def fixture_test_tag_cfg() -> TagConfig:
    return TagConfig.from_config(
        {
            "tag_groups": [
                {
                    "id": TagGroupID("criticality"),
                    "title": "Criticality",
                    "tags": [
                        {"id": TagID("prod"), "title": "Productive system", "aux_tags": []},
                        {"id": TagID("critical"), "title": "Business critical", "aux_tags": []},
                        {"id": TagID("test"), "title": "Test system", "aux_tags": []},
                        {
                            "id": TagID("offline"),
                            "title": "Do not monitor this host",
                            "aux_tags": [],
                        },
                    ],
                },
                {
                    "id": TagGroupID("networking"),
                    "title": "Networking Segment",
                    "tags": [
                        {
                            "id": TagID("lan"),
                            "title": "Local network (low latency)",
                            "aux_tags": [],
                        },
                        {"id": TagID("wan"), "title": "WAN (high latency)", "aux_tags": []},
                        {
                            "id": TagID("dmz"),
                            "title": "DMZ (low latency, secure access)",
                            "aux_tags": [],
                        },
                    ],
                },
                {
                    "id": TagGroupID("testgroup"),
                    "title": "Testgroup",
                    "tags": [
                        {"id": None, "title": "None", "aux_tags": []},
                        {"id": TagID("tag_id_1"), "title": "TagID1", "aux_tags": []},
                        {"id": TagID("tag_id_2"), "title": "TagID2", "aux_tags": []},
                        {"id": TagID("auxtag_like_tagid"), "title": "TagID3", "aux_tags": []},
                    ],
                    "topic": "Address",
                },
                {
                    "id": TagGroupID("auxtag_like_taggroupid"),
                    "title": "Testgroup",
                    "tags": [
                        {"id": None, "title": "None", "aux_tags": []},
                        {"id": TagID("tag_id_3"), "title": "TagID3", "aux_tags": []},
                        {"id": TagID("tag_id_4"), "title": "TagID4", "aux_tags": []},
                    ],
                    "topic": "Address",
                },
            ],
            "aux_tags": [
                {"id": TagID("auxtag"), "title": "AuxTag", "topic": "Address"},
                {
                    "id": TagID("auxtag_like_tagid"),
                    "title": "AuxTag named like a TagID",
                    "topic": "Address",
                },
                {
                    "id": TagID("auxtag_like_taggroupid"),
                    "title": "AuxTag named like a TagGroupID",
                    "topic": "Address",
                },
            ],
        }
    )


@pytest.mark.parametrize(
    ["tags_as_list", "tags_as_dict"],
    [
        pytest.param(
            ["prod", "tag_id_2", "auxtag", "auxtag_like_taggroupid", "auxtag_like_tagid"],
            {
                "criticality": "prod",
                "testgroup": "tag_id_2",
                "auxtag": "auxtag",
                "auxtag_like_taggroupid": "auxtag_like_taggroupid",
                "auxtag_like_tagid": "auxtag_like_tagid",
            },
            id="Mixed tags without negate",
        ),
        pytest.param(
            ["prod", "!tag_id_2", "!auxtag"],
            {"criticality": "prod", "testgroup": {"$ne": "tag_id_2"}, "auxtag": {"$ne": "auxtag"}},
            id="Mixed tags with negate",
        ),
    ],
)
def test_tag_conditions_with_mixed_tags(
    test_tag_cfg: TagConfig,
    tags_as_list: list[str],
    tags_as_dict: MutableMapping[TagGroupID, TagCondition],
) -> None:
    assert (
        transform_host_tags(tags_as_list, test_tag_cfg.tag_groups, test_tag_cfg.aux_tag_list)
        == tags_as_dict
    )


@pytest.mark.parametrize(
    ["notification_rule", "updated_rule"],
    [
        pytest.param(
            [
                {
                    "description": "Notify all contacts of a host/service via HTML email",
                    "comment": "",
                    "docu_url": "",
                    "disabled": False,
                    "allow_disable": True,
                    "match_hosttags": ["prod", "tag_id_2", "auxtag"],
                    "contact_object": True,
                    "contact_all": False,
                    "contact_all_with_email": False,
                    "rule_id": "db16ecd8-3b12-4ddc-be04-9f7fb9ba155b",
                    "notify_plugin": ("mail", {}),
                }
            ],
            [
                {
                    "description": "Notify all contacts of a host/service via HTML email",
                    "comment": "",
                    "docu_url": "",
                    "disabled": False,
                    "allow_disable": True,
                    "match_hosttags": {
                        "criticality": "prod",
                        "testgroup": "tag_id_2",
                        "auxtag": "auxtag",
                    },
                    "contact_object": True,
                    "contact_all": False,
                    "contact_all_with_email": False,
                    "rule_id": "db16ecd8-3b12-4ddc-be04-9f7fb9ba155b",
                    "notify_plugin": ("mail", {}),
                }
            ],
            id="Update without negated tags",
        ),
        pytest.param(
            [
                {
                    "description": "Notify all contacts of a host/service via HTML email",
                    "comment": "",
                    "docu_url": "",
                    "disabled": False,
                    "allow_disable": True,
                    "match_hosttags": ["!prod", "tag_id_2", "!auxtag"],
                    "contact_object": True,
                    "contact_all": False,
                    "contact_all_with_email": False,
                    "rule_id": "db16ecd8-3b12-4ddc-be04-9f7fb9ba155b",
                    "notify_plugin": ("mail", {}),
                }
            ],
            [
                {
                    "description": "Notify all contacts of a host/service via HTML email",
                    "comment": "",
                    "docu_url": "",
                    "disabled": False,
                    "allow_disable": True,
                    "match_hosttags": {
                        "criticality": {"$ne": "prod"},
                        "testgroup": "tag_id_2",
                        "auxtag": {"$ne": "auxtag"},
                    },
                    "contact_object": True,
                    "contact_all": False,
                    "contact_all_with_email": False,
                    "rule_id": "db16ecd8-3b12-4ddc-be04-9f7fb9ba155b",
                    "notify_plugin": ("mail", {}),
                }
            ],
            id="Update with negated tags",
        ),
    ],
)
@pytest.mark.usefixtures("patch_omd_site")
def test_update_notification_conditions(
    test_tag_cfg: TagConfig,
    notification_rule: list[EventRule],
    updated_rule: list[EventRule],
) -> None:
    NotificationRuleConfigFile().save(notification_rule, pprint_value=False)
    TagConfigFile().save(test_tag_cfg.get_dict_format(), pprint_value=False)

    with gui_context():
        UpdateNotificationTagConditions(
            name="notification_tag_conditions",
            title="Notification host tag conditions",
            sort_index=31,
        )(logging.getLogger())

    assert NotificationRuleConfigFile().load_for_reading()[0] == updated_rule[0]
