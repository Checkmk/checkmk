#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import MutableMapping, Sequence
from logging import Logger
from typing import override

from cmk.utils.rulesets.ruleset_matcher import TagCondition
from cmk.utils.tags import AuxTagList, BuiltinTagConfig, TagConfig, TagGroup, TagGroupID, TagID

from cmk.gui.config import active_config
from cmk.gui.watolib.notifications import NotificationRuleConfigFile
from cmk.gui.watolib.tags import TagConfigFile

from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateNotificationTagConditions(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        tag_groups, aux_tag_list = get_tag_config()
        for rule in (notification_rules := NotificationRuleConfigFile().load_for_modification()):
            if "match_hosttags" not in rule:
                continue

            if isinstance(host_tags := rule["match_hosttags"], dict):
                continue
            assert isinstance(host_tags, list)
            rule["match_hosttags"] = transform_host_tags(host_tags, tag_groups, aux_tag_list)
        NotificationRuleConfigFile().save(
            notification_rules, pprint_value=active_config.wato_pprint_config
        )


def get_tag_config() -> tuple[Sequence[TagGroup], AuxTagList]:
    hosttags_config = TagConfig().from_config(TagConfigFile().load_for_modification())
    return BuiltinTagConfig().tag_groups + hosttags_config.tag_groups, AuxTagList(
        list(BuiltinTagConfig().aux_tag_list) + list(hosttags_config.aux_tag_list)
    )


def transform_host_tags(
    host_tags: list[str],
    tag_groups: Sequence[TagGroup],
    aux_tag_list: AuxTagList,
) -> MutableMapping[TagGroupID, TagCondition]:
    conditions: MutableMapping[TagGroupID, TagCondition] = {}
    for host_tag in host_tags:
        negate = False
        for tag_group in tag_groups:
            for tag in tag_group.tags:
                if tag.id is None or tag_group.id in conditions:
                    continue
                _convert_condition(host_tag, tag.id, tag_group.id, negate, conditions)

        for aux_tag in aux_tag_list:
            _convert_condition(host_tag, aux_tag.id, TagGroupID(aux_tag.id), negate, conditions)

    return conditions


def _convert_condition(
    host_tag: str,
    tag_id: TagID,
    tag_group_id: TagGroupID,
    negate: bool,
    conditions: MutableMapping[TagGroupID, TagCondition],
) -> None:
    if host_tag[0] == "!":
        host_tag = host_tag[1:]
        negate = True

    if tag_id != host_tag:
        return

    conditions[tag_group_id] = {"$ne": TagID(host_tag)} if negate else TagID(host_tag)


update_action_registry.register(
    UpdateNotificationTagConditions(
        name="notification_tag_conditions",
        title="Notification host tag conditions",
        sort_index=31,
    )
)
