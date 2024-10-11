#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import assert_never, Mapping, NamedTuple, NewType, Sequence

from cmk.utils.notify_types import NotificationParameterID, NotificationParameterMethod

from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.wato import notification_parameter_registry
from cmk.gui.watolib.configuration_entity.type_defs import ConfigEntityType
from cmk.gui.watolib.notification_parameter import (
    get_list_of_notification_parameter,
    get_notification_parameter,
    get_notification_parameter_schema,
    save_notification_parameter,
)

EntityId = NewType("EntityId", str)


@dataclass(frozen=True, kw_only=True)
class ConfigurationEntityDescription:
    ident: EntityId
    description: str


def save_configuration_entity(
    entity_type: ConfigEntityType,
    entity_type_specifier: str,
    data: object,
    object_id: EntityId | None,
) -> ConfigurationEntityDescription | Sequence[shared_type_defs.ValidationMessage]:
    match entity_type:
        case ConfigEntityType.notification_parameter:
            return_value = save_notification_parameter(
                notification_parameter_registry,
                NotificationParameterMethod(entity_type_specifier),
                data,
                NotificationParameterID(object_id) if object_id else None,
            )
            if isinstance(return_value, Sequence):
                return return_value
            return ConfigurationEntityDescription(
                ident=EntityId(return_value.ident), description=return_value.description
            )
        case other:
            assert_never(other)


class ConfigurationEntitySchema(NamedTuple):
    schema: shared_type_defs.FormSpec
    default_values: object


def get_configuration_entity_schema(
    entity_type: ConfigEntityType,
    entity_type_specifier: str,
) -> ConfigurationEntitySchema:
    match entity_type:
        case ConfigEntityType.notification_parameter:
            return ConfigurationEntitySchema(
                *get_notification_parameter_schema(
                    notification_parameter_registry,
                    NotificationParameterMethod(entity_type_specifier),
                )
            )
        case other:
            assert_never(other)


def get_configuration_entity_data(
    entity_type: ConfigEntityType,
    entity_id: EntityId,
) -> Mapping:
    match entity_type:
        case ConfigEntityType.notification_parameter:
            return get_notification_parameter(
                NotificationParameterID(entity_id),
            )
        case other:
            assert_never(other)


def get_list_of_configuration_entities(
    entity_type: ConfigEntityType,
    entity_type_specifier: str,
) -> Sequence[ConfigurationEntityDescription]:
    match entity_type:
        case ConfigEntityType.notification_parameter:
            return [
                ConfigurationEntityDescription(
                    ident=EntityId(obj.ident), description=obj.description
                )
                for obj in get_list_of_notification_parameter(
                    NotificationParameterMethod(entity_type_specifier),
                )
            ]
        case other:
            assert_never(other)
