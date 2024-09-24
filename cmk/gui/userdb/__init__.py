#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.utils as utils
from cmk.gui.type_defs import Users, UserSpec

from ._check_credentials import check_credentials as check_credentials
from ._check_credentials import create_non_existing_user as create_non_existing_user
from ._check_credentials import (
    is_customer_user_allowed_to_login as is_customer_user_allowed_to_login,
)
from ._check_credentials import user_exists as user_exists
from ._check_credentials import (
    user_exists_according_to_profile as user_exists_according_to_profile,
)
from ._check_credentials import user_locked as user_locked
from ._connections import active_connections as active_connections
from ._connections import active_connections_by_type as active_connections_by_type
from ._connections import builtin_connections
from ._connections import clear_user_connection_cache as clear_user_connection_cache
from ._connections import connection_choices as connection_choices
from ._connections import connections_by_type as connections_by_type
from ._connections import get_connection as get_connection
from ._connections import load_connection_config as load_connection_config
from ._connections import locked_attributes as locked_attributes
from ._connections import multisite_attributes as multisite_attributes
from ._connections import non_contact_attributes as non_contact_attributes
from ._connections import save_connection_config as save_connection_config
from ._connections import UserConnectionSpec as UserConnectionSpec
from ._connector import CheckCredentialsResult as CheckCredentialsResult
from ._connector import ConnectorType as ConnectorType
from ._connector import user_connector_registry as user_connector_registry
from ._connector import UserConnector as UserConnector
from ._connector import UserConnectorRegistry as UserConnectorRegistry
from ._custom_attributes import (
    update_config_based_user_attributes as update_config_based_user_attributes,
)
from ._find_usage import (
    find_timeperiod_usage_in_notification_rule as find_timeperiod_usage_in_notification_rule,
)
from ._need_to_change_pw import is_automation_user as is_automation_user
from ._need_to_change_pw import need_to_change_pw as need_to_change_pw
from ._on_failed_login import on_failed_login as on_failed_login
from ._roles import load_roles as load_roles
from ._two_factor import (
    disable_two_factor_authentication as disable_two_factor_authentication,
)
from ._two_factor import (
    is_two_factor_backup_code_valid as is_two_factor_backup_code_valid,
)
from ._two_factor import is_two_factor_login_enabled as is_two_factor_login_enabled
from ._two_factor import load_two_factor_credentials as load_two_factor_credentials
from ._two_factor import make_two_factor_backup_codes as make_two_factor_backup_codes
from ._user_attribute import get_user_attributes as get_user_attributes
from ._user_attribute import (
    get_user_attributes_by_topic as get_user_attributes_by_topic,
)
from ._user_attribute import user_attribute_registry as user_attribute_registry
from ._user_attribute import UserAttribute as UserAttribute
from ._user_attribute import UserAttributeRegistry as UserAttributeRegistry
from ._user_selection import UserSelection as UserSelection
from ._user_spec import add_internal_attributes as add_internal_attributes
from ._user_spec import new_user_template as new_user_template
from ._user_spec import USER_SCHEME_SERIAL as USER_SCHEME_SERIAL
from ._user_sync import user_sync_config as user_sync_config
from ._user_sync import user_sync_default_config as user_sync_default_config
from ._user_sync import UserSyncBackgroundJob as UserSyncBackgroundJob
from .session import is_valid_user_session, load_session_infos
from .store import (
    contactgroups_of_user,
    convert_idle_timeout,
    create_cmk_automation_user,
    custom_attr_path,
    general_userdb_job,
    get_last_activity,
    get_last_seen,
    get_online_user_ids,
    load_contacts,
    load_custom_attr,
    load_multisite_users,
    load_user,
    load_users,
    remove_custom_attr,
    rewrite_users,
    save_custom_attr,
    save_two_factor_credentials,
    save_users,
    write_contacts_and_users_file,
)
from .store import release_users_lock as release_users_lock
from .user_attributes import show_mode_choices as show_mode_choices
from .user_attributes import validate_start_url as validate_start_url

__all__ = [
    "contactgroups_of_user",
    "create_cmk_automation_user",
    "custom_attr_path",
    "get_last_activity",
    "get_last_seen",
    "get_online_user_ids",
    "load_contacts",
    "load_custom_attr",
    "load_multisite_users",
    "load_user",
    "load_users",
    "remove_custom_attr",
    "rewrite_users",
    "save_custom_attr",
    "save_users",
    "Users",
    "UserSpec",
    "write_contacts_and_users_file",
    "UserSyncBackgroundJob",
    "builtin_connections",
    "user_sync_default_config",
]


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    utils.load_web_plugins("userdb", globals())
