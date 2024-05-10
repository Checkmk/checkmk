#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from collections.abc import Callable
from datetime import datetime
from typing import Literal

from livestatus import SiteId

from cmk.utils.site import omd_site

from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobAlreadyRunning,
    BackgroundProcessInterface,
    InitialStatusArgs,
)
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger as gui_logger
from cmk.gui.site_config import get_site_config, is_wato_slave_site, site_is_local
from cmk.gui.type_defs import Users
from cmk.gui.utils.urls import makeuri_contextless

from ..logged_in import user
from ._connections import active_connections
from .store import general_userdb_job, load_users, save_users

UserSyncConfig = Literal["all", "master"] | tuple[Literal["list"], list[str]] | None


def execute_userdb_job() -> None:
    """This function is called by the GUI cron job once a minute.

    Errors are logged to var/log/web.log."""
    if not _userdb_sync_job_enabled():
        return

    job = UserSyncBackgroundJob()
    if job.is_active():
        gui_logger.debug("Another synchronization job is already running: Skipping this sync")
        return

    job.start(
        lambda job_interface: job.do_sync(
            job_interface=job_interface,
            add_to_changelog=False,
            enforce_sync=False,
            load_users_func=load_users,
            save_users_func=save_users,
        ),
        InitialStatusArgs(
            title=job.gui_title(),
            stoppable=False,
            user=str(user.id) if user.id else None,
        ),
    )


def _userdb_sync_job_enabled() -> bool:
    cfg = user_sync_config()

    if cfg is None:
        return False  # not enabled at all

    if cfg == "master" and is_wato_slave_site():
        return False

    return True


def user_sync_config() -> UserSyncConfig:
    # use global option as default for reading legacy options and on remote site
    # for reading the value set by the Setup master site
    default_cfg = user_sync_default_config(omd_site())
    return get_site_config(active_config, omd_site()).get("user_sync", default_cfg)


# Legacy option config.userdb_automatic_sync defaulted to "master".
# Can be: None: (no sync), "all": all sites sync, "master": only master site sync
# Take that option into account for compatibility reasons.
# For remote sites in distributed setups, the default is to do no sync.
def user_sync_default_config(site_name: SiteId) -> UserSyncConfig:
    global_user_sync = _transform_userdb_automatic_sync(active_config.userdb_automatic_sync)
    if global_user_sync == "master":
        if site_is_local(active_config, site_name) and not is_wato_slave_site():
            user_sync_default: UserSyncConfig = "all"
        else:
            user_sync_default = None
    else:
        user_sync_default = global_user_sync

    return user_sync_default


# Old vs:
# ListChoice(
#    title = _('Automatic User Synchronization'),
#    help  = _('By default the users are synchronized automatically in several situations. '
#              'The sync is started when opening the "Users" page in configuration and '
#              'during each page rendering. Each connector can then specify if it wants to perform '
#              'any actions. For example the LDAP connector will start the sync once the cached user '
#              'information are too old.'),
#    default_value = [ 'wato_users', 'page', 'wato_pre_activate_changes', 'wato_snapshot_pushed' ],
#    choices       = [
#        ('page',                      _('During regular page processing')),
#        ('wato_users',                _('When opening the users\' configuration page')),
#        ('wato_pre_activate_changes', _('Before activating the changed configuration')),
#        ('wato_snapshot_pushed',      _('On a remote site, when it receives a new configuration')),
#    ],
#    allow_empty   = True,
# ),
def _transform_userdb_automatic_sync(val):
    if val == []:
        # legacy compat - disabled
        return None

    if isinstance(val, list) and val:
        # legacy compat - all connections
        return "all"

    return val


def ajax_sync() -> None:
    try:
        job = UserSyncBackgroundJob()
        try:
            job.start(
                lambda job_interface: job.do_sync(
                    job_interface=job_interface,
                    add_to_changelog=False,
                    enforce_sync=True,
                    load_users_func=load_users,
                    save_users_func=save_users,
                ),
                InitialStatusArgs(
                    title=job.gui_title(),
                    stoppable=False,
                    user=str(user.id) if user.id else None,
                ),
            )
        except BackgroundJobAlreadyRunning as e:
            raise MKUserError(None, _("Another user synchronization is already running: %s") % e)
        response.set_data("OK Started synchronization\n")
    except Exception as e:
        gui_logger.exception("error synchronizing user DB")
        if active_config.debug:
            raise
        response.set_data("ERROR %s\n" % e)


class UserSyncBackgroundJob(BackgroundJob):
    job_prefix = "user_sync"

    @classmethod
    def gui_title(cls) -> str:
        return _("User synchronization")

    def __init__(self) -> None:
        super().__init__(self.job_prefix)

    def _back_url(self) -> str:
        return makeuri_contextless(request, [("mode", "users")], filename="wato.py")

    def do_sync(
        self,
        job_interface: BackgroundProcessInterface,
        add_to_changelog: bool,
        enforce_sync: bool,
        load_users_func: Callable[[bool], Users],
        save_users_func: Callable[[Users, datetime], None],
    ) -> None:
        job_interface.send_progress_update(_("Synchronization started..."))
        if self._execute_sync_action(
            job_interface,
            add_to_changelog,
            enforce_sync,
            load_users_func,
            save_users_func,
            datetime.now(),
        ):
            job_interface.send_result_message(_("The user synchronization completed successfully."))
        else:
            job_interface.send_exception(_("The user synchronization failed."))

    def _execute_sync_action(
        self,
        job_interface: BackgroundProcessInterface,
        add_to_changelog: bool,
        enforce_sync: bool,
        load_users_func: Callable[[bool], Users],
        save_users_func: Callable[[Users, datetime], None],
        now: datetime,
    ) -> bool:
        for connection_id, connection in active_connections():
            try:
                if not enforce_sync and not connection.sync_is_needed():
                    continue

                job_interface.send_progress_update(
                    _("[%s] Starting sync for connection") % connection_id
                )
                connection.do_sync(
                    add_to_changelog=add_to_changelog,
                    only_username=None,
                    load_users_func=load_users,
                    save_users_func=save_users,
                )
                job_interface.send_progress_update(
                    _("[%s] Finished sync for connection") % connection_id
                )
            except Exception as e:
                job_interface.send_exception(_("[%s] Exception: %s") % (connection_id, e))
                gui_logger.error(
                    "Exception (%s, userdb_job): %s", connection_id, traceback.format_exc()
                )

        job_interface.send_progress_update(_("Finalizing synchronization"))
        general_userdb_job(now)
        return True
