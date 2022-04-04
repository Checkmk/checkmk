#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Displaying the asynchronous replication of the current users user profile"""

import json
import time
from typing import Sequence, Union

from livestatus import SiteConfiguration, SiteId

from cmk.utils.type_defs import UserId

import cmk.gui.sites
from cmk.gui import userdb
from cmk.gui.exceptions import MKGeneralException, MKUserError
from cmk.gui.globals import config, html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import AjaxPage, page_registry
from cmk.gui.site_config import get_site_config, sitenames
from cmk.gui.watolib.activate_changes import ActivateChanges, ACTIVATION_TIME_PROFILE_SYNC
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.user_profile import push_user_profiles_to_site_transitional_wrapper


def user_profile_async_replication_page(back_url: str) -> None:
    sites = list(user.authorized_login_sites().keys())
    user_profile_async_replication_dialog(sites=sites, back_url=back_url)

    html.footer()


def user_profile_async_replication_dialog(sites: Sequence[SiteId], back_url: str) -> None:
    html.p(
        _(
            "In order to activate your changes available on all remote sites, your user profile needs "
            "to be replicated to the remote sites. This is done on this page now. Each site "
            "is being represented by a single image which is first shown gray and then fills "
            "to green during synchronisation."
        )
    )

    html.h3(_("Replication States"))
    html.open_div(id_="profile_repl")
    num_replsites = 0
    for site_id in sites:
        site = config.sites[site_id]
        if "secret" not in site:
            status_txt = _("Not logged in.")
            start_sync = False
            icon = "repl_locked"
        else:
            status_txt = _("Waiting for replication to start")
            start_sync = True
            icon = "repl_pending"

        html.open_div(class_="site", id_="site-%s" % site_id)
        html.div("", title=status_txt, class_=["icon", "repl_status", icon])
        if start_sync:
            changes_manager = ActivateChanges()
            changes_manager.load()
            estimated_duration = changes_manager.get_activation_time(
                site_id, ACTIVATION_TIME_PROFILE_SYNC, 2.0
            )
            html.javascript(
                "cmk.profile_replication.start(%s, %d, %s);"
                % (
                    json.dumps(site_id),
                    int(estimated_duration * 1000.0),
                    json.dumps(_("Replication in progress")),
                )
            )
            num_replsites += 1
        else:
            _add_profile_replication_change(site_id, status_txt)
        html.span(site.get("alias", site_id))

        html.close_div()

    html.javascript(
        "cmk.profile_replication.prepare(%d, %s);\n" % (num_replsites, json.dumps(back_url))
    )

    html.close_div()


def _add_profile_replication_change(site_id: SiteId, result: Union[bool, str]) -> None:
    """Add pending change entry to make sync possible later for admins"""
    add_change(
        "edit-users",
        _("Profile changed (sync failed: %s)") % result,
        sites=[site_id],
        need_restart=False,
    )


@page_registry.register_page("wato_ajax_profile_repl")
class ModeAjaxProfileReplication(AjaxPage):
    """AJAX handler for asynchronous replication of user profiles (changed passwords)"""

    def page(self):
        ajax_request = self.webapi_request()

        site_id_val = ajax_request.get("site")
        if not site_id_val:
            raise MKUserError(None, "The site_id is missing")
        site_id = site_id_val
        if site_id not in sitenames():
            raise MKUserError(None, _("The requested site does not exist"))

        status = (
            cmk.gui.sites.states()
            .get(site_id, cmk.gui.sites.SiteStatus({}))
            .get("state", "unknown")
        )
        if status == "dead":
            raise MKGeneralException(_("The site is marked as dead. Not trying to replicate."))

        site = get_site_config(site_id)
        assert user.id is not None
        result = self._synchronize_profile(site_id, site, user.id)

        if result is not True:
            assert result is not False
            _add_profile_replication_change(site_id, result)
            raise MKGeneralException(result)

        return _("Replication completed successfully.")

    def _synchronize_profile(
        self, site_id: SiteId, site: SiteConfiguration, user_id: UserId
    ) -> Union[bool, str]:
        users = userdb.load_users(lock=False)
        if user_id not in users:
            raise MKUserError(None, _("The requested user does not exist"))

        start = time.time()
        result = push_user_profiles_to_site_transitional_wrapper(site, {user_id: users[user_id]})

        duration = time.time() - start
        ActivateChanges().update_activation_time(site_id, ACTIVATION_TIME_PROFILE_SYNC, duration)
        return result
