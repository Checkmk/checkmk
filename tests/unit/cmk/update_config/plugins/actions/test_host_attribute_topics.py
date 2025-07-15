#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.gui.type_defs import CustomHostAttrSpec
from cmk.gui.watolib.custom_attributes import (
    load_custom_attrs_from_mk_file,
    save_custom_attrs_to_mk_file,
)
from cmk.update_config.plugins.actions.host_attribute_topics import (
    transform_pre_16_host_topics,
    UpdateHostAttributeTopics,
)


@pytest.mark.parametrize(
    "old,new",
    [
        ("Basic settings", "basic"),
        ("Management board", "management_board"),
    ],
)
def test_custom_host_attribute_transform(old: str, new: str) -> None:
    attributes = [
        CustomHostAttrSpec(
            {
                "add_custom_macro": True,
                "help": "",
                "name": "attr1",
                "show_in_table": True,
                "title": "Attribute 1",
                "topic": old,
                "type": "TextAscii",
            }
        )
    ]

    transformed_attributes = transform_pre_16_host_topics(attributes)
    assert transformed_attributes[0]["topic"] == new


def test_update_host_attribute_topics() -> None:
    attributes = [
        CustomHostAttrSpec(
            {
                "add_custom_macro": True,
                "help": "",
                "name": "attr1",
                "show_in_table": True,
                "title": "Attribute 1",
                "topic": "Basic settings",
                "type": "TextAscii",
            }
        )
    ]
    save_custom_attrs_to_mk_file({"user": [], "host": attributes})

    UpdateHostAttributeTopics(
        name="host_attribute_topics",
        title="Host attribute topics",
        sort_index=100,
    )(logging.getLogger())

    all_attributes = load_custom_attrs_from_mk_file(lock=True)
    assert all_attributes["host"][0]["topic"] == "basic"
