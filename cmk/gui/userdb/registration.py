#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.background_job import BackgroundJobRegistry
from cmk.gui.config import register_post_config_load_hook
from cmk.gui.cron import register_job
from cmk.gui.pages import PageRegistry
from cmk.gui.watolib.groups import ContactGroupUsageFinderRegistry
from cmk.gui.watolib.timeperiods import TimeperiodUsageFinderRegistry

from . import ldap_connector, user_attributes
from ._connections import fix_user_connections
from ._connector import UserConnectorRegistry
from ._custom_attributes import update_config_based_user_attributes
from ._find_usage import find_timeperiod_usage_in_users, find_usages_of_contact_group_in_users
from ._user_attribute import UserAttributeRegistry
from ._user_profile_cleanup import execute_user_profile_cleanup_job, UserProfileCleanupBackgroundJob
from ._user_sync import ajax_sync, execute_userdb_job, UserSyncBackgroundJob
from .htpasswd import HtpasswdUserConnector

__all__ = ["register", "saas_register"]


def register(
    page_registry: PageRegistry,
    user_attribute_registry: UserAttributeRegistry,
    user_connector_registry: UserConnectorRegistry,
    job_registry: BackgroundJobRegistry,
    contact_group_usage_finder_registry: ContactGroupUsageFinderRegistry,
    timeperiod_usage_finder_registry: TimeperiodUsageFinderRegistry,
) -> None:
    user_attributes.register(user_attribute_registry)

    register_post_config_load_hook(fix_user_connections)
    register_post_config_load_hook(update_config_based_user_attributes)
    register_job(execute_userdb_job)

    register_job(execute_user_profile_cleanup_job)
    job_registry.register(UserProfileCleanupBackgroundJob)

    page_registry.register_page_handler("ajax_userdb_sync", ajax_sync)
    job_registry.register(UserSyncBackgroundJob)

    ldap_connector.register(user_connector_registry)
    contact_group_usage_finder_registry.register(find_usages_of_contact_group_in_users)
    timeperiod_usage_finder_registry.register(find_timeperiod_usage_in_users)
    user_connector_registry.register(HtpasswdUserConnector)


def saas_register(saas_user_attribute_registry: UserAttributeRegistry) -> None:
    user_attributes.saas_register(saas_user_attribute_registry)
