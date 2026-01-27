#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import assert_never, cast, NamedTuple, NewType

from cmk.gui.form_specs import (
    DEFAULT_VALUE,
    get_visitor,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.form_specs.unstable.oauth2_connection_setup import OAuth2ConnectionSetup
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.oauth2_connections.watolib.store import (
    load_oauth2_connections,
)
from cmk.gui.watolib.configuration_entity._folder import (
    get_folder_slidein_schema,
    save_folder_from_slidein_schema,
)
from cmk.gui.watolib.configuration_entity._oauth2_connections import (
    get_oauth2_connection,
    save_oauth2_connection_and_passwords_from_slidein_schema,
    update_oauth2_connection_and_passwords_from_slidein_schema,
)
from cmk.gui.watolib.configuration_entity._password import (
    get_password_slidein_schema,
    list_passwords,
    save_password_from_slidein_schema,
)
from cmk.gui.watolib.configuration_entity._rule_form_spec import (
    get_rule_form_spec_slidein_schema,
    list_rule_form_spec_descriptions,
    rule_form_spec_title,
    save_rule_form_spec_from_slidein_schema,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree, FolderTree
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
from cmk.utils.notify_types import NotificationParameterID, NotificationParameterMethod
from cmk.utils.oauth2_connection import OAuth2ConnectorType

EntityId = NewType("EntityId", str)


@dataclass(frozen=True, kw_only=True)
class ConfigurationEntityDescription:
    ident: EntityId
    description: str


def save_configuration_entity(
    entity_type: ConfigEntityType,
    entity_type_specifier: str,
    data: object,
    tree: FolderTree,
    user: LoggedInUser,
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
                object_id=None,
                user=user,
                pprint_value=pprint_value,
            )
            return ConfigurationEntityDescription(
                ident=EntityId(param.ident), description=param.description
            )
        case ConfigEntityType.folder:
            folder = save_folder_from_slidein_schema(
                tree, RawFrontendData(data), pprint_value=pprint_value, use_git=use_git
            )
            return ConfigurationEntityDescription(
                ident=EntityId(folder.path), description=folder.title
            )
        case ConfigEntityType.passwordstore_password:
            password = save_password_from_slidein_schema(
                RawFrontendData(data), user=user, pprint_value=pprint_value, use_git=use_git
            )
            return ConfigurationEntityDescription(
                ident=EntityId(password.id), description=password.title
            )
        case ConfigEntityType.oauth2_connection:
            user.need_permission("general.oauth2_connections")
            connector_type = cast(OAuth2ConnectorType, entity_type_specifier)
            ident, oauth2_connection = save_oauth2_connection_and_passwords_from_slidein_schema(
                RawFrontendData(data),
                connector_type,
                user=user,
                pprint_value=pprint_value,
                use_git=use_git,
            )
            return ConfigurationEntityDescription(
                ident=EntityId(ident), description=oauth2_connection["title"]
            )
        case ConfigEntityType.rule_form_spec:
            rule_form_spec_descr = save_rule_form_spec_from_slidein_schema(
                entity_type_specifier, RawFrontendData(data), tree, user
            )
            return ConfigurationEntityDescription(
                ident=EntityId(rule_form_spec_descr.ident),
                description=rule_form_spec_descr.description,
            )
        case other:
            assert_never(other)


def update_configuration_entity(
    entity_type: ConfigEntityType,
    entity_type_specifier: str,
    data: object,
    user: LoggedInUser,
    object_id: EntityId,
    pprint_value: bool,
    use_git: bool,
) -> ConfigurationEntityDescription:
    """Update a configuration entity.

    Raises:
        FormSpecValidationError: if the data does not match the form spec
    """
    match entity_type:
        case ConfigEntityType.notification_parameter:
            param = save_notification_parameter(
                notification_parameter_registry,
                NotificationParameterMethod(entity_type_specifier),
                RawFrontendData(data),
                object_id=NotificationParameterID(object_id),
                user=user,
                pprint_value=pprint_value,
            )
            return ConfigurationEntityDescription(
                ident=EntityId(param.ident), description=param.description
            )
        case ConfigEntityType.folder:
            raise NotImplementedError("Editing folders via config entity API is not supported.")
        case ConfigEntityType.passwordstore_password:
            raise NotImplementedError("Editing passwords via config entity API is not supported.")
        case ConfigEntityType.rule_form_spec:
            raise NotImplementedError(
                "Editing/updating rules via config entity API is not supported."
            )
        case ConfigEntityType.oauth2_connection:
            user.need_permission("general.oauth2_connections")
            connector_type = cast(OAuth2ConnectorType, entity_type_specifier)
            ident, oauth2_connection = update_oauth2_connection_and_passwords_from_slidein_schema(
                RawFrontendData(data),
                connector_type,
                user=user,
                pprint_value=pprint_value,
                use_git=use_git,
            )
            return ConfigurationEntityDescription(
                ident=EntityId(ident), description=oauth2_connection["title"]
            )
        case other:
            assert_never(other)


def _get_configuration_fs(
    entity_type: ConfigEntityType,
    entity_type_specifier: str,
    tree: FolderTree,
    user: LoggedInUser,
) -> FormSpec:
    match entity_type:
        case ConfigEntityType.notification_parameter:
            return notification_parameter_registry.form_spec(entity_type_specifier)
        case ConfigEntityType.oauth2_connection:
            connector_type = cast(OAuth2ConnectorType, entity_type_specifier)
            return OAuth2ConnectionSetup(connector_type=connector_type)
        case ConfigEntityType.folder:
            return get_folder_slidein_schema(tree)
        case ConfigEntityType.passwordstore_password:
            return get_password_slidein_schema(user)
        case ConfigEntityType.rule_form_spec:
            return get_rule_form_spec_slidein_schema(entity_type_specifier, tree, user)
        case other:
            assert_never(other)


class ConfigurationEntitySchema(NamedTuple):
    schema: shared_type_defs.FormSpec
    default_values: object


def get_configuration_entity_schema(
    entity_type: ConfigEntityType,
    entity_type_specifier: str,
    tree: FolderTree,
    user: LoggedInUser,
) -> ConfigurationEntitySchema:
    form_spec = _get_configuration_fs(entity_type, entity_type_specifier, tree, user)
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))
    schema, default_values = visitor.to_vue(DEFAULT_VALUE)
    return ConfigurationEntitySchema(schema=schema, default_values=default_values)


def get_readable_entity_selection(entity_type: ConfigEntityType, entity_type_specifier: str) -> str:
    match entity_type:
        case ConfigEntityType.notification_parameter:
            return _("%s parameter") % notification_script_title(entity_type_specifier)
        case ConfigEntityType.folder:
            return _("folder")
        case ConfigEntityType.oauth2_connection:
            return _("OAuth2 connection")
        case ConfigEntityType.passwordstore_password:
            return _("password")
        case ConfigEntityType.rule_form_spec:
            return _("rule %s") % rule_form_spec_title(entity_type_specifier)
        case other:
            assert_never(other)


class ConfigurationEntity(NamedTuple):
    description: str
    data: Mapping


def get_configuration_entity(
    entity_type: ConfigEntityType,
    entity_id: EntityId,
    user: LoggedInUser,
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
                user,
            )
            return ConfigurationEntity(description=entity.description, data=entity.data)
        case ConfigEntityType.folder:
            raise NotImplementedError("Editing folders via config entity API is not yet supported.")
        case ConfigEntityType.passwordstore_password:
            raise NotImplementedError(
                "Editing passwords via config entity API is not yet supported."
            )
        case ConfigEntityType.rule_form_spec:
            raise NotImplementedError("Editing rules via config entity API is not yet supported.")
        case ConfigEntityType.oauth2_connection:
            user.need_permission("general.oauth2_connections")
            oauth2_connection = get_oauth2_connection(entity_id)
            return ConfigurationEntity(
                description=oauth2_connection.description, data=oauth2_connection.data
            )
        case other:
            assert_never(other)


def get_list_of_configuration_entities(
    entity_type: ConfigEntityType,
    entity_type_specifier: str,
    *,
    user: LoggedInUser,
) -> Sequence[ConfigurationEntityDescription]:
    match entity_type:
        case ConfigEntityType.notification_parameter:
            return [
                ConfigurationEntityDescription(
                    ident=EntityId(obj.ident), description=obj.description
                )
                for obj in get_list_of_notification_parameter(
                    NotificationParameterMethod(entity_type_specifier),
                    user,
                )
            ]
        case ConfigEntityType.folder:
            return [
                ConfigurationEntityDescription(ident=EntityId(ident), description=description)
                for ident, description in folder_tree().folder_choices_fulltitle()
            ]
        case ConfigEntityType.oauth2_connection:
            user.need_permission("general.oauth2_connections")
            return [
                ConfigurationEntityDescription(ident=EntityId(ident), description=entry["title"])
                for ident, entry in load_oauth2_connections().items()
            ]
        case ConfigEntityType.passwordstore_password:
            return [
                ConfigurationEntityDescription(ident=EntityId(obj.id), description=obj.title)
                for obj in list_passwords(user)
            ]
        case ConfigEntityType.rule_form_spec:
            return [
                ConfigurationEntityDescription(
                    ident=EntityId(rule_form_spec_descr.ident),
                    description=rule_form_spec_descr.description,
                )
                for rule_form_spec_descr in list_rule_form_spec_descriptions(
                    entity_type_specifier, user
                )
            ]
        case other:
            assert_never(other)
