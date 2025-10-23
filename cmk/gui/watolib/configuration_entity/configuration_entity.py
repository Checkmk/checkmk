#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never, NamedTuple, NewType

from cmk.gui.form_specs import DEFAULT_VALUE, get_visitor, RawFrontendData, VisitorOptions
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.watolib.configuration_entity._folder import (
    get_folder_slidein_schema,
    save_folder_from_slidein_schema,
)
from cmk.gui.watolib.configuration_entity._password import (
    get_password_slidein_schema,
    save_password_from_slidein_schema,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.notification_parameter import (
    get_list_of_notification_parameter,
    get_notification_parameter,
    notification_parameter_registry,
    save_notification_parameter,
)
from cmk.gui.watolib.password_store import passwordstore_choices
from cmk.gui.watolib.users import notification_script_title
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.shared_typing import vue_formspec_components as shared_type_defs
from cmk.shared_typing.configuration_entity import ConfigEntityType
from cmk.utils.notify_types import NotificationParameterID, NotificationParameterMethod

EntityId = NewType("EntityId", str)


@dataclass(frozen=True, kw_only=True)
class ConfigurationEntityDescription:
    ident: EntityId
    description: str


def save_configuration_entity(
    entity_type: ConfigEntityType,
    entity_type_specifier: str,
    data: object,
    user: LoggedInUser,
    object_id: EntityId | None,
    pprint_value: bool,
    use_git: bool,
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
                RawFrontendData(data),
                object_id=NotificationParameterID(object_id) if object_id else None,
                pprint_value=pprint_value,
            )
            return ConfigurationEntityDescription(
                ident=EntityId(param.ident), description=param.description
            )
        case ConfigEntityType.folder:
            folder = save_folder_from_slidein_schema(
                RawFrontendData(data), pprint_value=pprint_value, use_git=use_git
            )
            return ConfigurationEntityDescription(
                ident=EntityId(folder.path), description=folder.title
            )
        case ConfigEntityType.password:
            password = save_password_from_slidein_schema(
                RawFrontendData(data), user=user, pprint_value=pprint_value, use_git=use_git
            )
            return ConfigurationEntityDescription(
                ident=EntityId(password.id), description=password.title
            )
        case other:
            assert_never(other)


def _get_configuration_fs(
    entity_type: ConfigEntityType,
    entity_type_specifier: str,
    user: LoggedInUser,
) -> FormSpec:
    match entity_type:
        case ConfigEntityType.notification_parameter:
            return notification_parameter_registry.form_spec(entity_type_specifier)
        case ConfigEntityType.folder:
            return get_folder_slidein_schema()
        case ConfigEntityType.password:
            return get_password_slidein_schema(user)
        case other:
            assert_never(other)


class ConfigurationEntitySchema(NamedTuple):
    schema: shared_type_defs.FormSpec
    default_values: object


def get_configuration_entity_schema(
    entity_type: ConfigEntityType,
    entity_type_specifier: str,
    user: LoggedInUser,
) -> ConfigurationEntitySchema:
    form_spec = _get_configuration_fs(entity_type, entity_type_specifier, user)
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))
    schema, default_values = visitor.to_vue(DEFAULT_VALUE)
    return ConfigurationEntitySchema(schema=schema, default_values=default_values)


def get_readable_entity_selection(entity_type: ConfigEntityType, entity_type_specifier: str) -> str:
    match entity_type:
        case ConfigEntityType.notification_parameter:
            return _("%s parameter") % notification_script_title(entity_type_specifier)
        case ConfigEntityType.folder:
            return _("folder")
        case ConfigEntityType.password:
            return _("password")
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
        case ConfigEntityType.password:
            raise NotImplementedError(
                "Editing passwords via config entity API is not yet supported."
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
        case ConfigEntityType.folder:
            return [
                ConfigurationEntityDescription(ident=EntityId(ident), description=description)
                for ident, description in folder_tree().folder_choices_fulltitle()
            ]
        case ConfigEntityType.password:
            return [
                ConfigurationEntityDescription(ident=EntityId(ident), description=title)
                for ident, title in passwordstore_choices()
                if ident is not None
            ]
        case other:
            assert_never(other)
