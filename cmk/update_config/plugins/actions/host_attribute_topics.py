#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger

from cmk.gui.type_defs import CustomHostAttrSpec
from cmk.gui.watolib.custom_attributes import (
    CustomAttrSpecs,
    load_custom_attrs_from_mk_file,
    save_custom_attrs_to_mk_file,
)
from cmk.gui.watolib.host_attributes import (
    host_attribute_topic_registry,
    transform_attribute_topic_title_to_id,
)

from cmk.update_config.registry import update_action_registry, UpdateAction


class UpdateHostAttributeTopics(UpdateAction):
    def __call__(self, logger: Logger) -> None:
        all_attributes = load_custom_attrs_from_mk_file(lock=True)
        save_custom_attrs_to_mk_file(_update_attributes(logger, all_attributes))


def _update_attributes(logger: Logger, all_attributes: CustomAttrSpecs) -> CustomAttrSpecs:
    all_attributes["host"] = transform_pre_16_host_topics(all_attributes["host"])
    return all_attributes


def transform_pre_16_host_topics(
    custom_attributes: list[CustomHostAttrSpec],
) -> list[CustomHostAttrSpec]:
    """Previous to 1.6 the titles of the host attribute topics were stored.

    This lead to issues with localized topics. We now have internal IDs for
    all the topics and try to convert the values here to the new format.

    We translate the titles which have been distributed with Checkmk to their
    internal topic ID. No action should be needed. Custom topics or topics of
    other languages are not translated. The attributes are put into the
    "Custom attributes" topic once. Users will have to re-configure the topic,
    sorry :-/."""
    for custom_attr in custom_attributes:
        if custom_attr["topic"] in host_attribute_topic_registry:
            continue

        custom_attr["topic"] = (
            transform_attribute_topic_title_to_id(custom_attr["topic"]) or "custom_attributes"
        )

    return custom_attributes


update_action_registry.register(
    UpdateHostAttributeTopics(
        name="host_attribute_topics",
        title="Host attribute topics",
        sort_index=100,  # I am not aware of any constrains
    )
)
