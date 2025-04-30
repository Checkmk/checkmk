#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence

from cmk.ccc.site import SiteId

from cmk.gui.config import active_config
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.watolib.activate_changes import ActivateChanges, ACTIVATION_TIME_PROFILE_SYNC
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.users import get_enabled_remote_sites_for_logged_in_user


def user_profile_async_replication_page(back_url: str) -> None:
    user_profile_async_replication_dialog(
        sites=list(get_enabled_remote_sites_for_logged_in_user(user)), back_url=back_url
    )
    html.footer()


def user_profile_async_replication_dialog(sites: Sequence[SiteId], back_url: str) -> None:
    if not sites:
        return

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
        site = active_config.sites[site_id]
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
                site_id, ACTIVATION_TIME_PROFILE_SYNC
            )
            if estimated_duration is None:
                estimated_duration = 2.0
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
            add_profile_replication_change(site_id, status_txt)
        html.span(site.get("alias", site_id))

        html.close_div()

    html.javascript(
        "cmk.profile_replication.prepare(%d, %s);\n" % (num_replsites, json.dumps(back_url))
    )

    html.close_div()


def add_profile_replication_change(site_id: SiteId, result: bool | str) -> None:
    """Add pending change entry to make sync possible later for admins"""
    add_change(
        action_name="edit-users",
        text=_l("Profile changed (sync failed: %s)") % result,
        user_id=user.id,
        sites=[site_id],
        need_restart=False,
        use_git=active_config.wato_use_git,
    )
