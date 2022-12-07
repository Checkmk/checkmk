#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Literal

from cmk.utils.tags import BuiltinTagConfig
from cmk.utils.type_defs import TagID

from cmk.gui.watolib.tags import load_all_tag_config_read_only, load_tag_config_read_only

from cmk import fields


class AuxTagIDField(fields.String):
    default_error_messages = {
        "should_exist": "The aux_tag {aux_tag_id!r} should exist but it doesn't.",
        "should_not_exist": "The aux_tag {aux_tag_id!r} should not exist but it does.",
        "should_exist_and_should_be_builtin": "The aux_tag {aux_tag_id!r} should be an existing builtin aux tag but it's not.",
        "should_exist_and_should_be_custom": "The aux_tag {aux_tag_id!r} should be an existing custom aux tag but it's not.",
    }

    def __init__(
        self,
        presence: Literal[
            "should_exist_and_should_be_builtin",
            "should_exist_and_should_be_custom",
            "should_exist",
            "should_not_exist",
            "ignore",
        ] = "ignore",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            description="An auxiliary tag id",
            example="ip-v4",
            pattern="^[-a-z0-9A-Z_]*$",
            **kwargs,
        )
        self.presence = presence

    def _validate(self, value):
        super()._validate(value)
        tag_id = TagID(value)

        if self.presence == "should_exist_and_should_be_builtin":
            if not BuiltinTagConfig().aux_tag_list.exists(tag_id):
                raise self.make_error("should_exist_and_should_be_builtin", aux_tag_id=tag_id)

        if self.presence == "should_exist_and_should_be_custom":
            if not load_tag_config_read_only().aux_tag_list.exists(tag_id):
                raise self.make_error("should_exist_and_should_be_custom", aux_tag_id=tag_id)

        if self.presence == "should_not_exist":
            if load_all_tag_config_read_only().aux_tag_list.exists(tag_id):
                raise self.make_error("should_not_exist", aux_tag_id=tag_id)

        if self.presence == "should_exist":
            if not load_all_tag_config_read_only().aux_tag_list.exists(tag_id):
                raise self.make_error("should_exist", aux_tag_id=tag_id)
