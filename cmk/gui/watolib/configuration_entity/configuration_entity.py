#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never, NamedTuple, NewType

from cmk.utils.notify_types import NotificationParameterID, NotificationParameterMethod

from cmk.gui.form_specs.vue.visitors import (
    DataOrigin,
    get_visitor,
    VisitorOptions,
)
from cmk.gui.form_specs.vue.visitors._type_defs import DEFAULT_VALUE
from cmk.gui.i18n import _
from cmk.gui.watolib.configuration_entity._folder import (
    get_folder_slidein_schema,
    save_folder_from_slidein_schema,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.notification_parameter import (
    get_list_of_notification_parameter,
    get_notification_parameter,
    notification_parameter_registry,
    save_notification_parameter,
)
from cmk.gui.watolib.users import notification_script_title

from cmk.rulesets.v1.form_specs import FormSpec
from cmk.shared_typing import vue_formspec_components as shared_type_defs
from cmk.shared_typing.configuration_entity import ConfigEntityType

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
    pprint_value: bool,
) -> ConfigurationEntityDescription:
    """Save a configuration entity.

    Raises:
        FormSpecValidationError: if the data does not match the form spec
    """
    match entity_type:
        case ConfigEntityType.notification_parameter:
            param = save_notification_parameter(
                notification_parameter_registry,
                NotificationParameterMethod(entity_type_specifier),
                data,
                object_id=NotificationParameterID(object_id) if object_id else None,
                pprint_value=pprint_value,
            )
            return ConfigurationEntityDescription(
                ident=EntityId(param.ident), description=param.description
            )
        case ConfigEntityType.folder:
            folder = save_folder_from_slidein_schema(data, pprint_value=pprint_value)
            return ConfigurationEntityDescription(
                ident=EntityId(folder.path), description=folder.title
            )
        case other:
            assert_never(other)


def _get_configuration_fs(
    entity_type: ConfigEntityType,
    entity_type_specifier: str,
) -> FormSpec:
    match entity_type:
        case ConfigEntityType.notification_parameter:
            return notification_parameter_registry.form_spec(entity_type_specifier)
        case ConfigEntityType.folder:
            return get_folder_slidein_schema()
        case other:
            assert_never(other)


class ConfigurationEntitySchema(NamedTuple):
    schema: shared_type_defs.FormSpec
    default_values: object


def get_configuration_entity_schema(
    entity_type: ConfigEntityType,
    entity_type_specifier: str,
) -> ConfigurationEntitySchema:
    form_spec = _get_configuration_fs(entity_type, entity_type_specifier)
    visitor = get_visitor(form_spec, VisitorOptions(DataOrigin.DISK))
    schema, default_values = visitor.to_vue(DEFAULT_VALUE)
    return ConfigurationEntitySchema(schema=schema, default_values=default_values)


def get_readable_entity_selection(entity_type: ConfigEntityType, entity_type_specifier: str) -> str:
    match entity_type:
        case ConfigEntityType.notification_parameter:
            return _("%s parameter") % notification_script_title(entity_type_specifier)
        case ConfigEntityType.folder:
            return _("folder")
        case other:
            assert_never(other)


class ConfigurationEntity(NamedTuple):
    description: str
    data: Mapping


def get_configuration_entity(
    entity_type: ConfigEntityType,
    entity_id: EntityId,
) -> ConfigurationEntity:
    """Get configuration entity to supply to frontend.

    Raises:
        KeyError: if configuration entity with entity_id doesn't exist.
    """
    match entity_type:
        case ConfigEntityType.notification_parameter:
            entity = get_notification_parameter(
                notification_parameter_registry,
                NotificationParameterID(entity_id),
            )
            return ConfigurationEntity(description=entity.description, data=entity.data)
        case ConfigEntityType.folder:
            raise NotImplementedError("Editing folders via config entity API is not yet supported.")
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
        case ConfigEntityType.folder:
            return [
                ConfigurationEntityDescription(ident=EntityId(ident), description=description)
                for ident, description in folder_tree().folder_choices_fulltitle()
            ]
        case other:
            assert_never(other)
