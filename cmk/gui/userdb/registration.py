#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import register_post_config_load_hook
from cmk.gui.cron import register_job
from cmk.gui.plugins.userdb.utils import UserAttributeRegistry, UserConnectorRegistry
from cmk.gui.userdb import user_attributes
from cmk.gui.userdb.ldap_connector import register as ldap_connector_register

from . import (
    _fix_user_connections,
    execute_user_profile_cleanup_job,
    execute_userdb_job,
    update_config_based_user_attributes,
)

__all__ = ["register"]


def register(
    user_attribute_registry: UserAttributeRegistry, user_connector_registry: UserConnectorRegistry
) -> None:
    user_attributes.register(user_attribute_registry)

    register_post_config_load_hook(_fix_user_connections)
    register_post_config_load_hook(update_config_based_user_attributes)
    register_job(execute_userdb_job)
    register_job(execute_user_profile_cleanup_job)

    ldap_connector_register(user_connector_registry)
