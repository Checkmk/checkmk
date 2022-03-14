#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions for dealing with Check_MK tags"""

from __future__ import annotations

import re
from typing import Dict, List, Mapping, NamedTuple, Optional, Sequence, Set, Tuple, Union

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _
from cmk.utils.type_defs import (
    AuxTagSpec,
    GroupedTagSpec,
    TagConfigSpec,
    TaggroupID,
    TaggroupIDToTagID,
    TaggroupSpec,
    TagID,
)


def get_effective_tag_config(tag_config: TagConfigSpec) -> TagConfig:
    # We don't want to access the plain config data structure during GUI code processing
    tags = TagConfig.from_config(tag_config)

    # Merge builtin tags with configured tags. The logic favors the configured tags, even
    # when the user config should not conflict with the builtin tags. This is something
    # which could be left over from pre 1.5 setups.
    tags += BuiltinTagConfig()
    return tags


def _validate_tag_id(tag_id: TagID) -> None:
    if not re.match("^[-a-z0-9A-Z_]*$", tag_id):
        raise MKGeneralException(
            _("Invalid tag ID. Only the characters a-z, A-Z, 0-9, _ and - are allowed.")
        )


class AuxTag:
    @classmethod
    def from_config(cls, tag_info: AuxTagSpec) -> AuxTag:
        return AuxTag(
            tag_id=tag_info["id"],
            title=tag_info["title"],
            topic=tag_info.get("topic"),
        )

    def __init__(self, tag_id: TagID, title: str, topic: Optional[str]) -> None:
        self.id = tag_id
        self.title = title
        self.topic = topic

    # TODO: Rename to "to_config"
    def get_dict_format(self) -> AuxTagSpec:
        response = AuxTagSpec({"id": self.id, "title": self.title})
        if self.topic:
            response["topic"] = self.topic
        return response

    @property
    def choice_title(self) -> str:
        if self.topic:
            return "%s / %s" % (self.topic, self.title)
        return self.title

    def validate(self) -> None:
        if not self.id:
            raise MKGeneralException(_("Please specify a tag ID"))

        _validate_tag_id(self.id)

        if not self.title:
            raise MKGeneralException(_("Please supply a title for you auxiliary tag."))


class AuxTagList:
    def __init__(self, aux_tags: List[AuxTag]) -> None:
        self._tags = aux_tags

    def __iadd__(self, other: AuxTagList) -> AuxTagList:
        tag_ids = self.get_tag_ids()
        for aux_tag in other.get_tags():
            if aux_tag.id not in tag_ids:
                self.append(aux_tag)
        return self

    def get_tags(self) -> Sequence[AuxTag]:
        return self._tags

    def append(self, aux_tag: AuxTag) -> None:
        self._append(aux_tag)

    def _append(self, aux_tag: AuxTag) -> None:
        if self.exists(aux_tag.id):
            raise MKGeneralException(
                _('The tag ID "%s" does already exist in the list of auxiliary tags.') % aux_tag
            )
        self._tags.append(aux_tag)

    def update(self, aux_tag_id: TagID, aux_tag: AuxTag) -> None:
        for index, tmp_aux_tag in enumerate(self._tags):
            if tmp_aux_tag.id == aux_tag_id:
                self._tags[index] = aux_tag
                return

    def remove(self, aux_tag_id: TagID) -> None:
        for index, tmp_aux_tag in enumerate(self._tags[:]):
            if tmp_aux_tag.id == aux_tag_id:
                self._tags.pop(index)
                return

    def validate(self) -> None:
        seen: Set[str] = set()
        for aux_tag in self._tags:
            aux_tag.validate()

            # Tag groups were made builtin with ~1.4. Previously users could modify
            # these groups.  These users now have the modified tag groups in their
            # user configuration and should be able to cleanup this using the GUI
            # for the moment.
            # With 1.7 we use cmk-update-config to enforce the user to cleanup this.
            # Then we can re-enable this consistency check.
            # builtin_config = BuiltinTagConfig()
            # if builtin_config.aux_tag_list.exists(aux_tag.id):
            #    raise MKGeneralException(
            #        _("You can not override the builtin auxiliary tag \"%s\".") % aux_tag.id)

            if aux_tag.id in seen:
                raise MKGeneralException(_('Duplicate tag ID "%s" in auxilary tags') % aux_tag.id)

            seen.add(aux_tag.id)

    def exists(self, aux_tag_id: TagID) -> bool:
        try:
            self.get_aux_tag(aux_tag_id)
            return True
        except KeyError:
            return False

    def get_aux_tag(self, aux_tag_id: TagID) -> AuxTag:
        for aux_tag in self._tags:
            if aux_tag_id == aux_tag.id:
                return aux_tag
        raise KeyError(_("Aux tag '%s' does not exist") % aux_tag_id)

    def get_tag_ids(self) -> Set[TagID]:
        return {tag.id for tag in self._tags}

    def get_dict_format(self) -> List[AuxTagSpec]:
        response = []
        for tag in self._tags:
            response.append(tag.get_dict_format())
        return response

    def get_choices(self) -> Sequence[Tuple[str, str]]:
        return [(aux_tag.id, aux_tag.title) for aux_tag in self._tags]


class GroupedTag:
    @classmethod
    def from_config(cls, group: TagGroup, tag_info: GroupedTagSpec) -> GroupedTag:
        return GroupedTag(
            group,
            tag_id=tag_info["id"],
            title=tag_info["title"],
            aux_tag_ids=tag_info["aux_tags"],
        )

    def __init__(
        self, group: TagGroup, tag_id: Optional[TagID], title: str, aux_tag_ids: List[TagID]
    ) -> None:
        self.id = tag_id
        self.title = title
        self.group = group
        self.aux_tag_ids = aux_tag_ids

    # TODO: Rename to "to_config"
    def get_dict_format(self) -> GroupedTagSpec:
        return {"id": self.id, "title": self.title, "aux_tags": self.aux_tag_ids}

    @property
    def choice_title(self) -> str:
        return self.title


class TagGroup:
    @classmethod
    def from_config(cls, group_info: TaggroupSpec) -> TagGroup:
        group = TagGroup(
            group_id=group_info["id"],
            title=group_info["title"],
            topic=group_info.get("topic"),
            help=group_info.get("help"),
            tags=[],
        )
        group.tags = [GroupedTag.from_config(group, tag) for tag in group_info["tags"]]
        return group

    def __init__(
        self,
        group_id: TaggroupID,
        title: str,
        topic: Optional[str],
        help: Optional[str],  # pylint: disable=redefined-builtin
        tags: List[GroupedTag],
    ) -> None:
        self.id = group_id
        self.title = title
        self.topic = topic
        self.help = help
        self.tags = tags

    @property
    def choice_title(self) -> str:
        if self.topic:
            return "%s / %s" % (self.topic, self.title)
        return self.title

    @property
    def is_checkbox_tag_group(self) -> bool:
        return len(self.tags) == 1

    @property
    def default_value(self) -> Optional[TagID]:
        return self.tags[0].id

    def get_tag(self, tag_id: TagID) -> Optional[GroupedTag]:
        for tag in self.tags:
            if tag_id == tag.id:
                return tag
        return None

    def get_tag_ids(self) -> Set[Optional[TagID]]:
        if self.is_checkbox_tag_group:
            return {None, self.tags[0].id}
        return {tag.id for tag in self.tags}

    def get_dict_format(self) -> TaggroupSpec:
        response: TaggroupSpec = {"id": self.id, "title": self.title, "tags": []}
        if self.topic:
            response["topic"] = self.topic

        if self.help:
            response["help"] = self.help

        for tag in self.tags:
            response["tags"].append(tag.get_dict_format())

        return response

    def get_tag_choices(self) -> Sequence[Tuple[Optional[TagID], str]]:
        choices = []
        for tag in self.tags:
            choices.append((tag.id, tag.title))
        return choices

    def get_tag_group_config(self, value: Optional[TagID]) -> TaggroupIDToTagID:
        """Return the set of tag groups which should be set for a host based on the given value"""
        tag_groups = {}

        if value is not None:
            tag_groups[self.id] = value

        # add optional aux tags
        for grouped_tag in self.tags:
            if grouped_tag.id == value:
                tag_groups.update({t: t for t in grouped_tag.aux_tag_ids})

        return tag_groups


class TagConfig:
    """Container object encapsulating a whole set of configured
    tag groups with auxiliary tags"""

    @classmethod
    def from_config(cls, tag_config: TagConfigSpec) -> TagConfig:
        return TagConfig(
            tag_groups=[TagGroup.from_config(tag_group) for tag_group in tag_config["tag_groups"]],
            aux_tags=AuxTagList(
                [AuxTag.from_config(aux_tag) for aux_tag in tag_config["aux_tags"]]
            ),
        )

    def __init__(
        self, tag_groups: Optional[List[TagGroup]] = None, aux_tags: Optional[AuxTagList] = None
    ) -> None:
        self.tag_groups = tag_groups or []
        self.aux_tag_list = aux_tags or AuxTagList([])

    def __iadd__(self, other: TagConfig) -> TagConfig:
        tg_ids = [tg.id for tg in self.tag_groups]
        for tg in other.tag_groups:
            if tg.id not in tg_ids:
                self.tag_groups.append(tg)

        self.aux_tag_list += other.aux_tag_list
        return self

    def get_tag_groups(self) -> Sequence[TagGroup]:
        return self.tag_groups

    def get_topic_choices(self) -> Sequence[Tuple[str, str]]:
        names = set([])
        for tag_group in self.tag_groups:
            topic = tag_group.topic or _("Tags")
            if topic:
                names.add((topic, topic))

        for aux_tag in self.aux_tag_list.get_tags():
            topic = aux_tag.topic or _("Tags")
            if topic:
                names.add((topic, topic))

        return sorted(list(names), key=lambda x: x[1])

    def get_tag_groups_by_topic(self) -> Sequence[Tuple[str, Sequence[TagGroup]]]:
        by_topic: Dict[str, List[TagGroup]] = {}
        for tag_group in self.tag_groups:
            topic = tag_group.topic or _("Tags")
            by_topic.setdefault(topic, []).append(tag_group)
        return sorted(by_topic.items(), key=lambda x: x[0])

    def tag_group_exists(self, tag_group_id: TaggroupID) -> bool:
        return self.get_tag_group(tag_group_id) is not None

    def get_tag_group(self, tag_group_id: TaggroupID) -> Optional[TagGroup]:
        for group in self.tag_groups:
            if group.id == tag_group_id:
                return group
        return None

    def remove_tag_group(self, tag_group_id: TaggroupID) -> None:
        group = self.get_tag_group(tag_group_id)
        if group is None:
            return
        self.tag_groups.remove(group)

    def get_tag_group_choices(self) -> Sequence[Tuple[TaggroupID, str]]:
        return [(tg.id, tg.choice_title) for tg in self.tag_groups]

    # TODO: Clean this up and make call sites directly call the wrapped function
    def get_aux_tags(self) -> Sequence[AuxTag]:
        return self.aux_tag_list.get_tags()

    def get_aux_tags_by_tag(self) -> Mapping[Optional[TagID], Sequence[TagID]]:
        aux_tag_map = {}
        for tag_group in self.tag_groups:
            for grouped_tag in tag_group.tags:
                aux_tag_map[grouped_tag.id] = grouped_tag.aux_tag_ids
        return aux_tag_map

    def get_aux_tags_by_topic(self) -> Sequence[Tuple[str, Sequence[AuxTag]]]:
        by_topic: Dict[str, List[AuxTag]] = {}
        for aux_tag in self.aux_tag_list.get_tags():
            topic = aux_tag.topic or _("Tags")
            by_topic.setdefault(topic, []).append(aux_tag)
        return sorted(by_topic.items(), key=lambda x: x[0])

    def get_tag_ids(self) -> Set[Optional[TagID]]:
        """Returns the raw ids of the grouped tags and the aux tags"""
        response: Set[Optional[TagID]] = set()
        for tag_group in self.tag_groups:
            response.update(tag_group.get_tag_ids())

        response.update(self.aux_tag_list.get_tag_ids())
        return response

    def get_tag_ids_by_group(self) -> Set[Tuple[TaggroupID, Optional[TagID]]]:
        """Returns a set of (tag_group_id, tag_id) pairs"""
        response: Set[Tuple[TaggroupID, Optional[TagID]]] = set()
        for tag_group in self.tag_groups:
            response.update([(tag_group.id, tag) for tag in tag_group.get_tag_ids()])

        response.update(
            [(aux_tag_id, aux_tag_id) for aux_tag_id in self.aux_tag_list.get_tag_ids()]
        )
        return response

    def get_tag_or_aux_tag(
        self,
        taggroupd_id: TaggroupID,
        tag_id: Optional[TagID],
    ) -> Optional[Union[GroupedTag, AuxTag]]:
        for tag_group in (t_grp for t_grp in self.tag_groups if t_grp.id == taggroupd_id):
            for grouped_tag in tag_group.tags:
                if grouped_tag.id == tag_id:
                    return grouped_tag

        for aux_tag in self.aux_tag_list.get_tags():
            if aux_tag.id == tag_id:
                return aux_tag

        return None

    # TODO: Change API to use __add__/__setitem__?
    def insert_tag_group(self, tag_group: TagGroup) -> None:
        self._insert_tag_group(tag_group)

    def _insert_tag_group(self, tag_group: TagGroup) -> None:
        self.tag_groups.append(tag_group)
        self._validate_group(tag_group)

    def update_tag_group(self, tag_group: TagGroup) -> None:
        for idx, group in enumerate(self.tag_groups):
            if group.id == tag_group.id:
                self.tag_groups[idx] = tag_group
                break
        else:
            raise MKGeneralException(_('Unknown tag group "%s"') % tag_group.id)
        self._validate_group(tag_group)

    def validate_config(self) -> None:
        for tag_group in self.tag_groups:
            self._validate_group(tag_group)

        self.aux_tag_list.validate()
        self._validate_ids()

    def _validate_ids(self) -> None:
        """Make sure that no tag key is used twice as aux_tag ID or tag group id"""
        seen_ids: Set[TaggroupID] = set()
        for tag_group in self.tag_groups:
            if tag_group.id in seen_ids:
                raise MKGeneralException(_('The tag group ID "%s" is used twice.') % tag_group.id)
            seen_ids.add(tag_group.id)

        for aux_tag in self.aux_tag_list.get_tags():
            if aux_tag.id in seen_ids:
                raise MKGeneralException(_('The tag ID "%s" is used twice.') % aux_tag.id)
            seen_ids.add(aux_tag.id)

    def valid_id(self, tag_aux_id: TagID) -> bool:
        """Verify if the proposed id is not already in use"""
        if tag_aux_id in [tag_group.id for tag_group in self.tag_groups]:
            return False

        if tag_aux_id in [aux_tag.id for aux_tag in self.aux_tag_list.get_tags()]:
            return False

        return True

    # TODO: cleanup this mess
    # This validation is quite gui specific, I do not want to introduce this into the base classes
    def _validate_group(self, tag_group: TagGroup) -> None:
        if not tag_group.id:
            raise MKGeneralException(_("Please specify an ID for your tag group."))
        _validate_tag_id(tag_group.id)

        if tag_group.id == "site":
            raise MKGeneralException(
                _('The tag group "%s" is reserved for internal use.') % tag_group.id
            )

        # Tag groups were made builtin with ~1.4. Previously users could modify
        # these groups.  These users now have the modified tag groups in their
        # user configuration and should be able to cleanup this using the GUI
        # for the moment.
        # With 1.7 we use cmk-update-config to enforce the user to cleanup this.
        # Then we can re-enable this consistency check.
        # builtin_config = BuiltinTagConfig()
        # if builtin_config.tag_group_exists(tag_group.id):
        #    raise MKGeneralException(
        #        _("You can not override the builtin tag group \"%s\".") % tag_group.id)

        if not tag_group.title:
            raise MKGeneralException(
                _('Please specify a title for your tag group "%s".') % tag_group.id
            )

        have_none_tag = False
        for nr, tag in enumerate(tag_group.tags):
            if tag.id or tag.title:
                if not tag.id:
                    tag.id = None

                    if len(tag_group.tags) == 1:
                        raise MKGeneralException(
                            _("Can not use an empty tag ID with a single choice.")
                        )

                    if have_none_tag:
                        raise MKGeneralException(_("Only one tag may be empty."))

                    have_none_tag = True

                # Make sure tag ID is unique within this group
                for (n, x) in enumerate(tag_group.tags):
                    if n != nr and x.id == tag.id:
                        raise MKGeneralException(
                            _('Tags IDs must be unique. You\'ve used "%s" twice.') % tag.id
                        )

        if len(tag_group.tags) == 0:
            raise MKGeneralException(_("Please specify at least one tag."))
        if len(tag_group.tags) == 1 and tag_group.tags[0] is None:
            raise MKGeneralException(_("Tag groups with only one choice must have a tag ID."))

    def get_dict_format(self) -> TagConfigSpec:
        result: TagConfigSpec = {"tag_groups": [], "aux_tags": []}
        for tag_group in self.tag_groups:
            result["tag_groups"].append(tag_group.get_dict_format())

        result["aux_tags"] = self.aux_tag_list.get_dict_format()

        return result


class BuiltinTagConfig(TagConfig):
    def __init__(self) -> None:
        super().__init__(
            tag_groups=[
                TagGroup.from_config(tag_group) for tag_group in self._builtin_tag_groups()
            ],
            aux_tags=AuxTagList(
                [AuxTag.from_config(aux_tag) for aux_tag in self._builtin_aux_tags()]
            ),
        )

    def _builtin_tag_groups(self) -> List[TaggroupSpec]:
        return [
            {
                "id": "agent",
                "title": _("Checkmk agent / API integrations"),
                "topic": _("Monitoring agents"),
                "tags": [
                    {
                        "id": "cmk-agent",
                        "title": _("API integrations if configured, else Checkmk agent"),
                        "aux_tags": ["tcp", "checkmk-agent"],
                    },
                    {
                        "id": "all-agents",
                        "title": _("Configured API integrations and Checkmk agent"),
                        "aux_tags": ["tcp", "checkmk-agent"],
                    },
                    {
                        "id": "special-agents",
                        "title": _("Configured API integrations, no Checkmk agent"),
                        "aux_tags": ["tcp"],
                    },
                    {
                        "id": "no-agent",
                        "title": _("No API integrations, no Checkmk agent"),
                        "aux_tags": [],
                    },
                ],
            },
            {
                "id": "piggyback",
                "title": _("Piggyback"),
                "topic": _("Monitoring agents"),
                "help": _(
                    "By default every host has the piggyback data source "
                    "<b>Use piggyback data from other hosts if present</b>. "
                    "In this case the <tt>Check_MK</tt> service of this host processes the piggyback data "
                    "but does not warn if no piggyback data is available. The related discovered services "
                    "would become stale. "
                    "If a host has configured <b>Always use and expect piggyback data</b> for the piggyback "
                    "data source then this host expects piggyback data and the <tt>Check_MK</tt> service of "
                    "this host warns if no piggyback data is available. "
                    "In the last case, ie. <b>Never use piggyback data</b>, the <tt>Check_MK</tt> service "
                    "does not process piggyback data at all and ignores it if available."
                ),
                "tags": [
                    {
                        "id": "auto-piggyback",
                        "title": _("Use piggyback data from other hosts if present"),
                        "aux_tags": [],
                    },
                    {
                        "id": "piggyback",
                        "title": _("Always use and expect piggyback data"),
                        "aux_tags": [],
                    },
                    {
                        "id": "no-piggyback",
                        "title": _("Never use piggyback data"),
                        "aux_tags": [],
                    },
                ],
            },
            {
                "id": "snmp_ds",
                "title": _("SNMP"),
                "topic": _("Monitoring agents"),
                "tags": [
                    {
                        "id": "no-snmp",
                        "title": _("No SNMP"),
                        "aux_tags": [],
                    },
                    {
                        "id": "snmp-v2",
                        "title": _("SNMP v2 or v3"),
                        "aux_tags": ["snmp"],
                    },
                    {
                        "id": "snmp-v1",
                        "title": _("SNMP v1"),
                        "aux_tags": ["snmp"],
                    },
                ],
            },
            {
                "id": "address_family",
                "title": _("IP address family"),
                "topic": "Address",
                "tags": [
                    {
                        "id": "ip-v4-only",
                        "title": _("IPv4 only"),
                        "aux_tags": ["ip-v4"],
                    },
                    {
                        "id": "ip-v6-only",
                        "title": _("IPv6 only"),
                        "aux_tags": ["ip-v6"],
                    },
                    {
                        "id": "ip-v4v6",
                        "title": _("IPv4/IPv6 dual-stack"),
                        "aux_tags": ["ip-v4", "ip-v6"],
                    },
                    {
                        "id": "no-ip",
                        "title": _("No IP"),
                        "aux_tags": [],
                    },
                ],
            },
        ]

    def _builtin_aux_tags(self) -> List[AuxTagSpec]:
        return [
            {
                "id": "ip-v4",
                "topic": _("Address"),
                "title": _("IPv4"),
            },
            {
                "id": "ip-v6",
                "topic": _("Address"),
                "title": _("IPv6"),
            },
            {
                "id": "snmp",
                "topic": _("Monitoring agents"),
                "title": _("Monitor via SNMP"),
            },
            {
                "id": "tcp",
                "topic": _("Monitoring agents"),
                "title": _("Monitor via Checkmk Agent or special agent"),
            },
            {
                "id": "checkmk-agent",
                "topic": _("Monitoring agents"),
                "title": _("Monitor via Checkmk Agent"),
            },
            {
                "id": "ping",
                "topic": _("Monitoring agents"),
                "title": _("Only ping this device"),
            },
        ]

    def insert_tag_group(self, tag_group: TagGroup) -> None:
        self._insert_tag_group(tag_group)


def sample_tag_config() -> TagConfigSpec:
    """Returns the WATO sample tag config

    The difference between the builtin and sample tag config is that the builtin
    tag configuration can not be changed by the user. The sample tag config is
    created on site creation (more precisely: during first WATO access).
    """
    return {
        "aux_tags": [],
        "tag_groups": [
            {
                "id": "criticality",
                "tags": [
                    {"aux_tags": [], "id": "prod", "title": "Productive system"},
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
        ],
    }


class DataSourceDifference(NamedTuple):
    name: str
    myself_is: bool
    other_is: bool


DataSourceDifferences = Sequence[DataSourceDifference]


class ComputedDataSources(NamedTuple):
    is_all_agents_host: bool
    is_all_special_agents_host: bool
    is_tcp: bool
    is_snmp: bool

    def get_differences_to(self, other: ComputedDataSources) -> DataSourceDifferences:
        return [
            DataSourceDifference(
                name,
                myself_is=myself_is,
                other_is=other_is,
            )
            for name, is_ds_func in [
                (_("all agents"), lambda obj: obj.is_all_agents_host),
                (_("all special agents"), lambda obj: obj.is_all_special_agents_host),
                ("TCP", lambda obj: obj.is_tcp),
                ("SNMP", lambda obj: obj.is_snmp),
            ]
            if (myself_is := is_ds_func(self)) != (other_is := is_ds_func(other))
        ]


def compute_datasources(tag_groups: TaggroupIDToTagID) -> ComputedDataSources:
    return ComputedDataSources(
        is_tcp=tag_groups.get("tcp") == "tcp",
        is_snmp=tag_groups.get("snmp_ds") in ["snmp", "snmp-v1", "snmp-v2"],
        is_all_agents_host=tag_groups.get("agent") == "all-agents",
        is_all_special_agents_host=tag_groups.get("agent") == "special-agents",
    )
