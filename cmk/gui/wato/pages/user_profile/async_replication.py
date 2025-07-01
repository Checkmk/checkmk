#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Displaying the asynchronous replication of the current users user profile"""

import time
from typing import get_args

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId

import cmk.gui.sites
from cmk.gui import userdb
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import AjaxPage, PageEndpoint, PageRegistry, PageResult
from cmk.gui.type_defs import VisualTypeName
from cmk.gui.user_async_replication import add_profile_replication_change
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.visuals._store import load_raw_visuals_of_a_user
from cmk.gui.watolib.activate_changes import ACTIVATION_TIME_PROFILE_SYNC, update_activation_time
from cmk.gui.watolib.automations import RemoteAutomationConfig
from cmk.gui.watolib.user_profile import push_user_profiles_to_site_transitional_wrapper


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("wato_ajax_profile_repl", ModeAjaxProfileReplication))


class ModeAjaxProfileReplication(AjaxPage):
    """AJAX handler for asynchronous replication of user profiles (changed passwords)"""

    def page(self, config: Config) -> PageResult:
        check_csrf_token()
        ajax_request = self.webapi_request()

        site_id_val = ajax_request.get("site")
        if not site_id_val:
            raise MKUserError(None, "The site_id is missing")
        site_id = site_id_val
        if site_id not in config.sites:
            raise MKUserError(None, _("The requested site does not exist"))

        status = (
            cmk.gui.sites.states()
            .get(site_id, cmk.gui.sites.SiteStatus({}))
            .get("state", "unknown")
        )
        if status == "dead":
            raise MKGeneralException(_("The site is marked as dead. Not trying to replicate."))

        assert user.id is not None
        result = self._synchronize_profile(
            site_id,
            RemoteAutomationConfig.from_site_config(config.sites[site_id]),
            user.id,
            debug=config.debug,
        )

        if result is not True:
            assert result is not False
            add_profile_replication_change(site_id, result)
            raise MKGeneralException(result)

        return _("Replication completed successfully.")

    def _synchronize_profile(
        self,
        site_id: SiteId,
        automation_config: RemoteAutomationConfig,
        user_id: UserId,
        *,
        debug: bool,
    ) -> bool | str:
        users = userdb.load_users(lock=False)
        visuals_of_user = {
            what: load_raw_visuals_of_a_user(what, user_id) for what in get_args(VisualTypeName)
        }

        if user_id not in users:
            raise MKUserError(None, _("The requested user does not exist"))

        start = time.time()
        result = push_user_profiles_to_site_transitional_wrapper(
            automation_config, {user_id: users[user_id]}, {user_id: visuals_of_user}, debug=debug
        )

        duration = time.time() - start
        update_activation_time(site_id, ACTIVATION_TIME_PROFILE_SYNC, duration)
        return result
