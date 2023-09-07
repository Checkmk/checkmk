#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO: Rework connection management and multiplexing
from __future__ import annotations

import ast
import shutil
import time
import traceback
from collections.abc import Callable, Sequence
from contextlib import suppress
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import Any, Literal

import cmk.utils.paths

import cmk.gui.utils as utils
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobAlreadyRunning,
    BackgroundJobRegistry,
    BackgroundProcessInterface,
    InitialStatusArgs,
)
from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.plugins.userdb.utils import (
    active_connections,
    ConnectorType,
    get_connection,
    get_user_attributes,
    new_user_template,
    user_attribute_registry,
    user_sync_config,
    UserAttribute,
    UserAttributeRegistry,
    UserConnector,
)
from cmk.gui.type_defs import Users, UserSpec
from cmk.gui.userdb.session import is_valid_user_session, load_session_infos
from cmk.gui.userdb.store import (
    contactgroups_of_user,
    convert_idle_timeout,
    create_cmk_automation_user,
    custom_attr_path,
    general_userdb_job,
    get_last_activity,
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
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import (
    DEF_VALUE,
    DropdownChoice,
    TextInput,
    Transform,
    ValueSpec,
    ValueSpecDefault,
    ValueSpecHelp,
    ValueSpecText,
)

from ._check_credentials import check_credentials as check_credentials
from ._check_credentials import create_non_existing_user as create_non_existing_user
from ._check_credentials import (
    is_customer_user_allowed_to_login as is_customer_user_allowed_to_login,
)
from ._check_credentials import user_exists as user_exists
from ._check_credentials import user_exists_according_to_profile as user_exists_according_to_profile
from ._check_credentials import user_locked as user_locked
from ._need_to_change_pw import is_automation_user as is_automation_user
from ._need_to_change_pw import need_to_change_pw as need_to_change_pw
from ._on_access import on_access as on_access
from ._on_failed_login import on_failed_login as on_failed_login
from ._two_factor import disable_two_factor_authentication as disable_two_factor_authentication
from ._two_factor import is_two_factor_backup_code_valid as is_two_factor_backup_code_valid
from ._two_factor import is_two_factor_login_enabled as is_two_factor_login_enabled
from ._two_factor import load_two_factor_credentials as load_two_factor_credentials
from ._two_factor import make_two_factor_backup_codes as make_two_factor_backup_codes
from ._user_attribute import register_custom_user_attributes as register_custom_user_attributes
from ._user_attribute import (
    update_config_based_user_attributes as update_config_based_user_attributes,
)
from ._user_selection import UserSelection as UserSelection
from ._user_sync import UserSyncBackgroundJob as UserSyncBackgroundJob

__all__ = [
    "contactgroups_of_user",
    "create_cmk_automation_user",
    "custom_attr_path",
    "get_last_activity",
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
]


def load_plugins() -> None:
    """Plugin initialization hook (Called by cmk.gui.main_modules.load_plugins())"""
    utils.load_web_plugins("userdb", globals())


# The saved configuration for user connections is a bit inconsistent, let's fix
# this here once and for all.
def _fix_user_connections() -> None:
    for cfg in active_config.user_connections:
        # Although our current configuration always seems to have a 'disabled'
        # entry, this might not have always been the case.
        cfg.setdefault("disabled", False)
        # Only migrated configurations have a 'type' entry, all others are
        # implictly LDAP connections.
        cfg.setdefault("type", "ldap")


def locked_attributes(connection_id: str | None) -> Sequence[str]:
    """Returns a list of connection specific locked attributes"""
    return _get_attributes(connection_id, lambda c: c.locked_attributes())


def multisite_attributes(connection_id: str | None) -> Sequence[str]:
    """Returns a list of connection specific multisite attributes"""
    return _get_attributes(connection_id, lambda c: c.multisite_attributes())


def non_contact_attributes(connection_id: str | None) -> Sequence[str]:
    """Returns a list of connection specific non contact attributes"""
    return _get_attributes(connection_id, lambda c: c.non_contact_attributes())


def _get_attributes(
    connection_id: str | None, selector: Callable[[UserConnector], Sequence[str]]
) -> Sequence[str]:
    connection = get_connection(connection_id)
    return selector(connection) if connection else []
