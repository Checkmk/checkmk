#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions for dealing with Check_MK tags"""

from __future__ import annotations

import contextlib
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Any, Final, NamedTuple, NewType, NotRequired, Self, TypedDict

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.i18n import _
from cmk.ccc.site import omd_site

TagID = NewType("TagID", str)
TagGroupID = NewType("TagGroupID", str)
TAG_GROUP_NAME_PATTERN = r"^\A[-a-z0-9A-Z_]*\Z"


class HostTags:
    def __init__(
        self,
        host_tags_sequences: Mapping[HostName, Sequence[TagID]],
        host_tags_maps: Mapping[HostName, Mapping[TagGroupID, TagID]],
    ) -> None:
        self.host_tags_sequences: Final = host_tags_sequences
        self.host_tags_maps: Final = host_tags_maps

    @classmethod
    def make(
        cls,
        host_paths: Mapping[HostName, str],
        tag_config_spec: TagConfigSpec,
        raw_host_tags: Mapping[HostName, Mapping[TagGroupID, TagID]],
        tagged_hosts: Iterable[str],
        shadow_hosts: Mapping[HostName, Mapping[str, Any]],
    ) -> Self:
        """Calculate the effective tags for all configured hosts

        WATO ensures that all hosts configured with WATO have host_tags set, but there may also be hosts defined
        by the etc/check_mk/conf.d directory that are not managed by WATO. They may use the old style pipe separated
        all_hosts configuration. Detect it and try to be compatible.
        """
        tag_to_group_map = get_tag_to_group_map(get_effective_tag_config(tag_config_spec))
        tags_sequences = dict[HostName, Sequence[TagID]]()
        tags_maps = {**raw_host_tags}
        for tagged_host in tagged_hosts:
            raw_hostname, *raw_tags = tagged_host.split("|")
            hostname = HostName(raw_hostname)

            if hostname in tags_maps:
                # New dict host_tags are available: only need to compute the tag list
                tags_sequences[hostname] = cls._tag_groups_to_tag_list(
                    host_paths.get(hostname, "/"), tags_maps[hostname]
                )
            else:
                # Only tag list available. Use it and compute the tag groups.
                tags_sequences[hostname] = tuple(TagID(t) for t in raw_tags)
                tags_maps[hostname] = cls._tag_list_to_tag_groups(
                    tag_to_group_map, tags_sequences[hostname]
                )

        for shadow_host_name, shadow_host_spec in shadow_hosts.items():
            tags_sequences[shadow_host_name] = tuple(
                set(shadow_host_spec.get("custom_variables", {}).get("TAGS", TagID("")).split())
            )
            tags_maps[shadow_host_name] = cls._tag_list_to_tag_groups(
                tag_to_group_map, tags_sequences[shadow_host_name]
            )
        return cls(tags_sequences, tags_maps)

    @staticmethod
    def _tag_groups_to_tag_list(
        host_path: str, tag_groups: Mapping[TagGroupID, TagID]
    ) -> Sequence[TagID]:
        # The pre 1.6 tags contained only the tag group values (-> chosen tag id),
        # but there was a single tag group added with it's leading tag group id. This
        # was the internal "site" tag that is created by HostAttributeSite.
        tags = {v for k, v in tag_groups.items() if k != TagGroupID("site")}
        tags.add(TagID(host_path))
        tags.add(TagID(f"site:{tag_groups[TagGroupID('site')]}"))
        return tuple(tags)

    @staticmethod
    def _tag_list_to_tag_groups(
        tag_to_group_map: Mapping[TagID, TagGroupID], tag_list: Iterable[TagID]
    ) -> Mapping[TagGroupID, TagID]:
        # This assumes all needed aux tags of grouped are already in the tag_list
        return {
            **fallback_tags(omd_site()),
            # Assume it's an aux tag in case there is a tag configured without known group
            **{tag_to_group_map.get(tag_id, TagGroupID(tag_id)): tag_id for tag_id in tag_list},
        }

    def tag_list(self, hostname: HostName) -> Sequence[TagID]:
        """Returns the list of all configured tags of a host. In case
        a host has no tags configured or is not known, it returns an
        empty list."""
        if hostname in self.host_tags_sequences:
            return self.host_tags_sequences[hostname]

        # Handle not existing hosts (No need to performance optimize this)
        return self._tag_groups_to_tag_list("/", self.tags(hostname))

    def tags(self, hostname: HostName) -> Mapping[TagGroupID, TagID]:
        """Returns the dict of all configured tag groups and values of a host."""
        with contextlib.suppress(KeyError):
            return self.host_tags_maps[hostname]

        return fallback_tags(omd_site())


class GroupedTagSpec(TypedDict):
    id: TagID | None
    title: str
    aux_tags: list[TagID]


class AuxTagSpec(TypedDict):
    id: TagID
    title: str
    topic: NotRequired[str]
    help: NotRequired[str]


class TagGroupSpec(TypedDict):
    id: TagGroupID
    title: str
    tags: list[GroupedTagSpec]
    topic: NotRequired[str]
    help: NotRequired[str]


class TagConfigSpec(TypedDict):
    tag_groups: list[TagGroupSpec]
    aux_tags: list[AuxTagSpec]


def get_effective_tag_config(tag_config: TagConfigSpec) -> TagConfig:
    # We don't want to access the plain config data structure during GUI code processing
    tags = TagConfig.from_config(tag_config)

    # Merge builtin tags with configured tags. The logic favors the configured tags, even
    # when the user config should not conflict with the builtin tags. This is something
    # which could be left over from pre 1.5 setups.
    tags += BuiltinTagConfig()
    return tags


def _validate_tag_id(tag_id: TagID | TagGroupID) -> None:
    if not re.match(TAG_GROUP_NAME_PATTERN, tag_id):
        raise MKGeneralException(
            _("Invalid tag ID. Only the characters a-z, A-Z, 0-9, _ and - are allowed.")
        )


class AuxTagInUseError(Exception): ...


class AuxTag:
    @classmethod
    def from_config(cls, tag_info: AuxTagSpec) -> AuxTag:
        return AuxTag(
            tag_id=tag_info["id"],
            title=tag_info["title"],
            topic=tag_info.get("topic"),
            help=tag_info.get("help"),
        )

    def __init__(
        self,
        tag_id: TagID,
        title: str,
        topic: str | None,
        help: str | None,
    ) -> None:
        self.id = tag_id
        self.title = title
        self.topic = topic
        self.help = help

    def to_config(self) -> AuxTagSpec:
        response = AuxTagSpec({"id": self.id, "title": self.title})
        if self.topic:
            response["topic"] = self.topic
        if self.help:
            response["help"] = self.help
        return response

    @property
    def choice_title(self) -> str:
        return f"{self.topic} / {self.title}" if self.topic else self.title

    def validate(self) -> None:
        if not self.id:
            raise MKGeneralException(_("Please specify a tag ID"))

        _validate_tag_id(self.id)

        if not self.title:
            raise MKGeneralException(_("Please supply a title for you auxiliary tag."))


class AuxTagList:
    def __init__(self, aux_tags: list[AuxTag]) -> None:
        self._tags = aux_tags

    def __iadd__(self, other: AuxTagList) -> AuxTagList:
        tag_ids = self.get_tag_ids()
        for aux_tag in other.get_tags():
            if aux_tag.id not in tag_ids:
                self.append(aux_tag)
        return self

    def __iter__(self) -> Iterator[AuxTag]:
        yield from self._tags

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
        seen: set[str] = set()
        for aux_tag in self._tags:
            aux_tag.validate()

            builtin_config = BuiltinTagConfig()
            if builtin_config.aux_tag_list.exists(aux_tag.id):
                raise MKGeneralException(
                    _('You can not override the builtin auxiliary tag "%s".') % aux_tag.id
                )

            if builtin_config.tag_group_exists(TagGroupID(aux_tag.id)):
                raise MKGeneralException(
                    _('You can not override the builtin tag group "%s".') % aux_tag.id
                )

            if aux_tag.id in seen:
                raise MKGeneralException(_('Duplicate tag ID "%s" in auxiliary tags') % aux_tag.id)

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

    def get_tag_ids(self) -> set[TagID]:
        return {tag.id for tag in self._tags}

    def get_dict_format(self) -> list[AuxTagSpec]:
        return [tag.to_config() for tag in self._tags]

    def get_choices(self) -> Sequence[tuple[str, str]]:
        return [
            (aux_tag.id, aux_tag.title)
            for aux_tag in sorted(self._tags, key=lambda t: t.title.lower())
        ]


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
        self, group: TagGroup, tag_id: TagID | None, title: str, aux_tag_ids: list[TagID]
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
    def from_config(cls, group_info: TagGroupSpec) -> TagGroup:
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
        group_id: TagGroupID,
        title: str,
        topic: str | None,
        help: str | None,
        tags: list[GroupedTag],
    ) -> None:
        self.id = group_id
        self.title = title
        self.topic = topic
        self.help = help
        self.tags = tags

    @property
    def choice_title(self) -> str:
        return f"{self.topic} / {self.title}" if self.topic else self.title

    @property
    def is_checkbox_tag_group(self) -> bool:
        return len(self.tags) == 1

    @property
    def default_value(self) -> TagID | None:
        return self.tags[0].id

    def get_tag_ids(self) -> set[TagID | None]:
        if self.is_checkbox_tag_group:
            return {None, self.tags[0].id}
        return {tag.id for tag in self.tags}

    def get_dict_format(self) -> TagGroupSpec:
        response: TagGroupSpec = {"id": self.id, "title": self.title, "tags": []}
        if self.topic:
            response["topic"] = self.topic

        if self.help:
            response["help"] = self.help

        for tag in self.tags:
            response["tags"].append(tag.get_dict_format())

        return response

    def get_tag_choices(self) -> Sequence[tuple[TagID | None, str]]:
        return [(tag.id, tag.title) for tag in self.tags]

    def get_non_empty_tag_choices(self) -> Sequence[tuple[TagID, str]]:
        return [(tag.id, tag.title) for tag in self.tags if tag.id is not None]

    def get_tag_group_config(self, value: TagID | None) -> Mapping[TagGroupID, TagID]:
        """Return the set of tag groups which should be set for a host based on the given value"""
        tag_groups: dict[TagGroupID, TagID] = {}

        if value is not None:
            tag_groups[self.id] = value

        # add optional aux tags
        for grouped_tag in self.tags:
            if grouped_tag.id == value:
                # We need to convert here.  Typing smell?
                tag_groups |= {TagGroupID(t): t for t in grouped_tag.aux_tag_ids}

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
        self, tag_groups: list[TagGroup] | None = None, aux_tags: AuxTagList | None = None
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

    def get_topic_choices(self) -> Sequence[tuple[str, str]]:
        names = set()
        for tag_group in self.tag_groups:
            if topic := tag_group.topic or _("Tags"):
                names.add((topic, topic))

        for aux_tag in self.aux_tag_list.get_tags():
            if topic := aux_tag.topic or _("Tags"):
                names.add((topic, topic))

        return sorted(list(names), key=lambda x: x[1])

    def get_tag_groups_by_topic(self) -> Sequence[tuple[str, Sequence[TagGroup]]]:
        by_topic: dict[str, list[TagGroup]] = {}
        for tag_group in self.tag_groups:
            topic = tag_group.topic or _("Tags")
            by_topic.setdefault(topic, []).append(tag_group)
        return sorted(by_topic.items(), key=lambda x: x[0])

    def tag_group_exists(self, tag_group_id: TagGroupID) -> bool:
        return self.get_tag_group(tag_group_id) is not None

    def get_tag_group(self, tag_group_id: TagGroupID) -> TagGroup | None:
        return next((group for group in self.tag_groups if group.id == tag_group_id), None)

    def remove_tag_group(self, tag_group_id: TagGroupID) -> None:
        group = self.get_tag_group(tag_group_id)
        if group is None:
            return
        self.tag_groups.remove(group)

    def get_tag_group_choices(self) -> Sequence[tuple[TagGroupID, str]]:
        return [(tg.id, tg.choice_title) for tg in self.tag_groups]

    # TODO: Clean this up and make call sites directly call the wrapped function
    def get_aux_tags(self) -> Sequence[AuxTag]:
        return self.aux_tag_list.get_tags()

    def get_aux_tags_by_tag(self) -> Mapping[TagID | None, Sequence[TagID]]:
        aux_tag_map = {}
        for tag_group in self.tag_groups:
            for grouped_tag in tag_group.tags:
                aux_tag_map[grouped_tag.id] = grouped_tag.aux_tag_ids
        return aux_tag_map

    def insert_aux_tag(self, aux_tag: AuxTag) -> None:
        self.aux_tag_list.append(aux_tag)
        self.aux_tag_list.validate()

    def update_aux_tag(self, aux_tag_id: TagID, aux_tag: AuxTag) -> None:
        self.aux_tag_list.update(aux_tag_id, aux_tag)

    def remove_aux_tag(self, tag_id: TagID) -> None:
        tag_groups_using_aux_tag: list[str] = []
        for group in self.tag_groups:
            tag_groups_using_aux_tag.extend(
                group.title for grouped_tag in group.tags if tag_id in grouped_tag.aux_tag_ids
            )
        if tag_groups_using_aux_tag:
            raise AuxTagInUseError(
                _(
                    "You cannot delete this auxiliary tag. "
                    'It is being used by the following tag groups: "%s"'
                )
                % ", ".join(tag_groups_using_aux_tag),
            )
        self.aux_tag_list.remove(tag_id)

    def get_aux_tags_by_topic(self) -> Sequence[tuple[str, Sequence[AuxTag]]]:
        by_topic: dict[str, list[AuxTag]] = {}
        for aux_tag in self.aux_tag_list.get_tags():
            topic = aux_tag.topic or _("Tags")
            by_topic.setdefault(topic, []).append(aux_tag)
        return sorted(by_topic.items(), key=lambda x: x[0])

    def get_tag_ids(self) -> set[TagID | None]:
        """Returns the raw ids of the grouped tags and the aux tags"""
        response: set[TagID | None] = set()
        for tag_group in self.tag_groups:
            response.update(tag_group.get_tag_ids())

        response.update(self.aux_tag_list.get_tag_ids())
        return response

    def get_tag_or_aux_tag(
        self,
        taggroupd_id: TagGroupID,
        tag_id: TagID | None,
    ) -> GroupedTag | AuxTag | None:
        for tag_group in (t_grp for t_grp in self.tag_groups if t_grp.id == taggroupd_id):
            for grouped_tag in tag_group.tags:
                if grouped_tag.id == tag_id:
                    return grouped_tag

        return next(
            (aux_tag for aux_tag in self.aux_tag_list.get_tags() if aux_tag.id == tag_id),
            None,
        )

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
        # `TagID | TagGroupID` type smell.
        seen_ids: set[TagID | TagGroupID] = set()
        for tag_group in self.tag_groups:
            if tag_group.id in seen_ids:
                raise MKGeneralException(_('The tag group ID "%s" is used twice.') % tag_group.id)
            seen_ids.add(tag_group.id)

        for aux_tag in self.aux_tag_list.get_tags():
            if aux_tag.id in seen_ids:
                raise MKGeneralException(_('The tag ID "%s" is used twice.') % aux_tag.id)
            seen_ids.add(aux_tag.id)

    def valid_id(self, tag_aux_id: TagID | TagGroupID) -> bool:
        """Verify if the proposed id is not already in use"""
        # Back to str, the code is untyped.
        tag_aux_id_str = str(tag_aux_id)

        return all(tag_aux_id_str != str(tag_group.id) for tag_group in self.tag_groups) and all(
            tag_aux_id_str != str(aux_tag.id) for aux_tag in self.aux_tag_list.get_tags()
        )

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

        builtin_config = BuiltinTagConfig()
        if builtin_config.tag_group_exists(tag_group.id):
            raise MKGeneralException(
                _('You can not override the builtin tag group "%s".') % tag_group.id
            )

        if builtin_config.aux_tag_list.exists(TagID(tag_group.id)):
            raise MKGeneralException(
                _('You can not override the builtin auxiliary tag "%s".') % tag_group.id
            )

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
                for n, x in enumerate(tag_group.tags):
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

    def _builtin_tag_groups(self) -> list[TagGroupSpec]:
        return [
            {
                "id": TagGroupID("agent"),
                "title": _("Checkmk agent / API integrations"),
                "topic": _("Monitoring agents"),
                "tags": [
                    {
                        "id": TagID("cmk-agent"),
                        "title": _("API integrations if configured, else Checkmk agent"),
                        "aux_tags": [TagID("tcp"), TagID("checkmk-agent")],
                    },
                    {
                        "id": TagID("all-agents"),
                        "title": _("Configured API integrations and Checkmk agent"),
                        "aux_tags": [TagID("tcp"), TagID("checkmk-agent")],
                    },
                    {
                        "id": TagID("special-agents"),
                        "title": _("Configured API integrations, no Checkmk agent"),
                        "aux_tags": [TagID("tcp")],
                    },
                    {
                        "id": TagID("no-agent"),
                        "title": _("No API integrations, no Checkmk agent"),
                        "aux_tags": [],
                    },
                ],
            },
            {
                "id": TagGroupID("piggyback"),
                "title": _("Piggyback"),
                "topic": _("Monitoring agents"),
                "help": _(
                    "By default, each host has a piggyback data "
                    "source.<br><br><b>Use piggyback data from other hosts if "
                    "present:</b><br>If selected, the <tt>Check_MK</tt> service "
                    "of this host will process the piggyback data, but will not "
                    "warn if no piggyback data is available. The associated "
                    "discovered services would become stale.<br><br><b>Always "
                    "use and expect piggyback data:</b><br>The host will expect "
                    "piggyback data, and the <tt>Check_MK</tt> service of this "
                    "host will warn if no piggyback data is "
                    "available.<br><br><b>Never use piggyback data:</b><br>The "
                    "<tt>Check_MK</tt> service does not process piggybacking "
                    "data at all, and will ignore it if it's available."
                ),
                "tags": [
                    {
                        "id": TagID("auto-piggyback"),
                        "title": _("Use piggyback data from other hosts if present"),
                        "aux_tags": [],
                    },
                    {
                        "id": TagID("piggyback"),
                        "title": _("Always use and expect piggyback data"),
                        "aux_tags": [],
                    },
                    {
                        "id": TagID("no-piggyback"),
                        "title": _("Never use piggyback data"),
                        "aux_tags": [],
                    },
                ],
            },
            {
                "id": TagGroupID("snmp_ds"),
                "title": _("SNMP"),
                "topic": _("Monitoring agents"),
                "tags": [
                    {
                        "id": TagID("no-snmp"),
                        "title": _("No SNMP"),
                        "aux_tags": [],
                    },
                    {
                        "id": TagID("snmp-v2"),
                        "title": _("SNMP v2 or v3"),
                        "aux_tags": [TagID("snmp")],
                    },
                    {
                        "id": TagID("snmp-v1"),
                        "title": _("SNMP v1"),
                        "aux_tags": [TagID("snmp")],
                    },
                ],
            },
            {
                # Shouldn't be used *directly* anywhere.  Always prefer
                # `ConfigCache.address_family(HostName) -> AddressFamily`
                # because it is typed.
                "id": TagGroupID("address_family"),
                "title": _("IP address family"),
                "topic": "Address",
                "tags": [
                    {
                        "id": TagID("ip-v4-only"),
                        "title": _("IPv4 only"),
                        "aux_tags": [TagID("ip-v4")],
                    },
                    {
                        "id": TagID("ip-v6-only"),
                        "title": _("IPv6 only"),
                        "aux_tags": [TagID("ip-v6")],
                    },
                    {
                        "id": TagID("ip-v4v6"),
                        "title": _("IPv4/IPv6 dual-stack"),
                        "aux_tags": [TagID("ip-v4"), TagID("ip-v6")],
                    },
                    {
                        "id": TagID("no-ip"),
                        "title": _("No IP"),
                        "aux_tags": [],
                    },
                ],
            },
        ]

    def _builtin_aux_tags(self) -> list[AuxTagSpec]:
        return [
            {
                "id": TagID("ip-v4"),
                "topic": _("Address"),
                "title": _("IPv4"),
            },
            {
                "id": TagID("ip-v6"),
                "topic": _("Address"),
                "title": _("IPv6"),
            },
            {
                "id": TagID("snmp"),
                "topic": _("Monitoring agents"),
                "title": _("Monitor via SNMP"),
            },
            {
                "id": TagID("tcp"),
                "topic": _("Monitoring agents"),
                "title": _("Monitor via Checkmk Agent or special agent"),
            },
            {
                "id": TagID("checkmk-agent"),
                "topic": _("Monitoring agents"),
                "title": _("Monitor via Checkmk Agent"),
            },
            {
                "id": TagID("ping"),
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
                "id": TagGroupID("criticality"),
                "tags": [
                    {"aux_tags": [], "id": TagID("prod"), "title": "Productive system"},
                    {"aux_tags": [], "id": TagID("critical"), "title": "Business critical"},
                    {"aux_tags": [], "id": TagID("test"), "title": "Test system"},
                    {"aux_tags": [], "id": TagID("offline"), "title": "Do not monitor this host"},
                ],
                "title": "Criticality",
            },
            {
                "id": TagGroupID("networking"),
                "tags": [
                    {"aux_tags": [], "id": TagID("lan"), "title": "Local network (low latency)"},
                    {"aux_tags": [], "id": TagID("wan"), "title": "WAN (high latency)"},
                    {
                        "aux_tags": [],
                        "id": TagID("dmz"),
                        "title": "DMZ (low latency, secure access)",
                    },
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


def compute_datasources(tag_groups: Mapping[TagGroupID, TagID]) -> ComputedDataSources:
    return ComputedDataSources(
        is_tcp=tag_groups.get(TagGroupID("tcp")) == TagID("tcp"),
        is_snmp=(
            tag_groups.get(TagGroupID("snmp_ds"))
            in [TagID("snmp"), TagID("snmp-v1"), TagID("snmp-v2")]
        ),
        is_all_agents_host=tag_groups.get(TagGroupID("agent")) == TagID("all-agents"),
        is_all_special_agents_host=tag_groups.get(TagGroupID("agent")) == TagID("special-agents"),
    )


def fallback_tags(site: str) -> Mapping[TagGroupID, TagID]:
    # Handle not existing hosts (No need to performance optimize this)
    # TODO: This immitates the logic of cmk.gui.watolib.Host.tag_groups which
    # is currently responsible for calculating the host tags of a host.
    # Would be better to untie the GUI code there and move it over to cmk.utils.tags.
    return {
        TagGroupID("piggyback"): TagID("auto-piggyback"),
        TagGroupID("networking"): TagID("lan"),
        TagGroupID("agent"): TagID("cmk-agent"),
        TagGroupID("criticality"): TagID("prod"),
        TagGroupID("snmp_ds"): TagID("no-snmp"),
        TagGroupID("site"): TagID(site),
        TagGroupID("address_family"): TagID("ip-v4-only"),
    }


def get_tag_to_group_map(tag_config: TagConfig) -> Mapping[TagID, TagGroupID]:
    """The old rules only have a list of tags and don't know anything about the
    tag groups they are coming from. Create a map based on the current tag config
    """
    tag_id_to_tag_group_id_map: dict[TagID, TagGroupID] = {}

    for aux_tag in tag_config.aux_tag_list.get_tags():
        tag_id_to_tag_group_id_map[aux_tag.id] = TagGroupID(aux_tag.id)

    for tag_group in tag_config.tag_groups:
        for grouped_tag in tag_group.tags:
            # Do not care for the choices with a None value here. They are not relevant for this map
            if grouped_tag.id is not None:
                tag_id_to_tag_group_id_map[grouped_tag.id] = tag_group.id
    return tag_id_to_tag_group_id_map
