#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re
from typing import Any

from cmk.utils.regex import REGEX_ID
from cmk.utils.tags import TAG_GROUP_NAME_PATTERN, TagID

from cmk.gui.fields import AuxTagIDField
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.watolib.tags import load_all_tag_config_read_only, tag_group_exists

from cmk import fields


class Tags(fields.List):
    """A field representing a tags list"""

    default_error_messages = {
        "duplicate": "Tags IDs must be unique. You've used the following at least twice: {name!r}",
        "invalid_none": "Cannot use an empty tag ID for single entry",
        "multi_none": "Only one tag id is allowed to be empty",
    }

    def __init__(
        self,
        cls,
        example,
        required=True,
        validate=None,
        **kwargs,
    ):
        super().__init__(
            cls_or_instance=cls,
            example=example,
            required=required,
            validate=validate,
            **kwargs,
        )

    def _validate(self, value):
        super()._validate(value)

        self._unique_ids(value)
        self._valid_none_tag(value)

    def _valid_none_tag(self, value):
        none_tag_exists = False
        for tag in value:
            tag_id = tag.get("id")
            if tag_id is None:
                if len(value) == 1:
                    raise self.make_error("invalid_none")

                if none_tag_exists:
                    raise self.make_error("multi_none")

                none_tag_exists = True

    def _unique_ids(self, tags):
        seen_ids = set()
        for tag in tags:
            tag_id = tag.get("id")
            if tag_id in seen_ids:
                raise self.make_error("duplicate", name=tag_id)
            seen_ids.add(tag_id)


class HostTagGroupId(fields.String):
    """A field representing a host tag group id"""

    default_error_messages = {
        "used": "The specified tag group id is already in use: {name!r}",
        "pattern": "Invalid tag ID: {value!r}. Only the characters a-z, A-Z, 0-9, _ and - are allowed.",
    }

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def _validate(self, value):
        super()._validate(value)
        if not (re.match(TAG_GROUP_NAME_PATTERN, value) and re.match(REGEX_ID, value)):
            raise self.make_error("pattern", value=value)
        group_exists = tag_group_exists(value, builtin_included=True)
        if group_exists:
            raise self.make_error("used", name=value)

        if load_all_tag_config_read_only().aux_tag_list.exists(TagID(value)):
            raise self.make_error("used", name=value)


class HostTag(BaseSchema):
    id = fields.String(
        required=False,
        example="tag_id",
        description="An unique id for the tag",
        load_default=None,
        attribute="id",
    )
    title = fields.String(
        required=True,
        example="Tag",
        description="The title of the tag",
    )
    aux_tags = fields.List(
        AuxTagIDField(
            required=False,
            presence="should_exist",
        ),
        description="The list of auxiliary tag ids. Built-in tags (ip-v4, ip-v6, snmp, tcp, ping) and custom defined tags are allowed.",
        example=["ip-v4, ip-v6"],
        required=False,
        load_default=list,
    )


class InputHostTagGroup(BaseSchema):
    id = HostTagGroupId(
        required=True,
        example="group_id",
        description="An id for the host tag group",
        attribute="id",
    )
    title = fields.String(
        required=True,
        example="Kubernetes",
        description="A title for the host tag",
    )
    topic = fields.String(
        example="Data Sources",
        description="Different tags can be grouped in a topic",
    )

    help = fields.String(
        required=False,
        example="Kubernetes Pods",
        description="A help description for the tag group",
        load_default="",
    )
    tags = Tags(
        fields.Nested(HostTag),
        required=True,
        example=[{"id": "pod", "title": "Pod"}],
        description="A list of host tags belonging to the host tag group",
        minLength=1,
    )


class UpdateHostTagGroup(BaseSchema):
    title = fields.String(
        required=False,
        example="Kubernetes",
        description="A title for the host tag",
    )
    topic = fields.String(
        required=False,
        example="Data Sources",
        description="Different tags can be grouped in a topic",
    )

    help = fields.String(
        required=False,
        example="Kubernetes Pods",
        description="A help description for the tag group",
    )
    tags = Tags(
        fields.Nested(HostTag),
        required=False,
        example=[{"id": "pod", "title": "Pod"}],
        description="A list of host tags belonging to the host tag group",
        minLength=1,
    )
    repair = fields.Boolean(
        required=False,
        load_default=False,
        example=False,
        description="The host tag group can be in use by other hosts. Setting repair to True gives permission to automatically update the tag from the affected hosts.",
    )


class DeleteHostTagGroup(BaseSchema):
    repair = fields.Boolean(
        required=False,
        load_default=False,
        example=False,
        description="The host tag group can still be in use. Setting repair to True gives permission to automatically remove the tag from the affected hosts.",
    )
    mode = fields.String(
        enum=["abort", "delete", "remove", None],
        required=False,
        load_default=None,
        example="delete",
        description=(
            "The host tag group can still be in use. Set mode to determine what should happen. "
            "Either 'abort' the deletion, 'delete' affected rules or 'remove' the tag from "
            "affected rules."
        ),
    )
