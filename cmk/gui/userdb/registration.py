#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import timedelta

from cmk.gui.background_job import BackgroundJobRegistry
from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.watolib.groups import ContactGroupUsageFinderRegistry
from cmk.gui.watolib.timeperiods import TimeperiodUsageFinderRegistry

from . import ldap_connector, user_attributes
from ._connector import UserConnectorRegistry
from ._find_usage import find_timeperiod_usage_in_users, find_usages_of_contact_group_in_users
from ._user_attribute import UserAttributeRegistry
from ._user_profile_cleanup import execute_user_profile_cleanup_job
from .htpasswd import HtpasswdUserConnector
from .user_sync_job import ajax_sync, execute_userdb_job, UserSyncBackgroundJob

__all__ = ["register"]


def register(
    page_registry: PageRegistry,
    user_attribute_registry: UserAttributeRegistry,
    user_connector_registry: UserConnectorRegistry,
    job_registry: BackgroundJobRegistry,
    contact_group_usage_finder_registry: ContactGroupUsageFinderRegistry,
    timeperiod_usage_finder_registry: TimeperiodUsageFinderRegistry,
    cron_job_registry: CronJobRegistry,
) -> None:
    user_attributes.register(user_attribute_registry)

    cron_job_registry.register(
        CronJob(
            name="execute_userdb_job",
            callable=execute_userdb_job,
            interval=timedelta(minutes=1),
        )
    )

    cron_job_registry.register(
        CronJob(
            name="execute_user_profile_cleanup_job",
            callable=execute_user_profile_cleanup_job,
            interval=timedelta(hours=1),
            run_in_thread=True,
        )
    )

    page_registry.register(PageEndpoint("ajax_userdb_sync", ajax_sync))
    job_registry.register(UserSyncBackgroundJob)

    ldap_connector.register(user_connector_registry)
    contact_group_usage_finder_registry.register(find_usages_of_contact_group_in_users)
    timeperiod_usage_finder_registry.register(find_timeperiod_usage_in_users)
    user_connector_registry.register(HtpasswdUserConnector)
