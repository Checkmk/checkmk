#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from collections.abc import Callable
from datetime import datetime
from logging import Logger

from pydantic import BaseModel

from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobTarget,
)
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger as gui_logger
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.type_defs import Users
from cmk.gui.utils.urls import makeuri_contextless

from ..logged_in import user
from ._connections import active_connections
from ._user_sync_config import user_sync_config
from .store import general_userdb_job, load_users, save_users


def execute_userdb_job() -> None:
    """This function is called by the GUI cron job once a minute.

    Errors are logged to var/log/web.log."""
    if not _userdb_sync_job_enabled():
        return

    job = UserSyncBackgroundJob()

    if not job.shall_start():
        gui_logger.debug("Job shall not start")
        return

    if (
        result := job.start(
            JobTarget(
                callable=sync_entry_point,
                args=UserSyncArgs(add_to_changelog=False, enforce_sync=False),
            ),
            InitialStatusArgs(
                title=job.gui_title(),
                stoppable=False,
                user=str(user.id) if user.id else None,
            ),
        )
    ).is_error():
        gui_logger.error("Error starting user sync job: %s", result.error)


class UserSyncArgs(BaseModel, frozen=True):
    add_to_changelog: bool
    enforce_sync: bool


def sync_entry_point(job_interface: BackgroundProcessInterface, args: UserSyncArgs) -> None:
    UserSyncBackgroundJob().do_sync(
        job_interface, args, load_users_func=load_users, save_users_func=save_users
    )


def _userdb_sync_job_enabled() -> bool:
    cfg = user_sync_config()

    if cfg is None:
        return False  # not enabled at all

    if cfg == "master" and is_wato_slave_site():
        return False

    return True


def ajax_sync() -> None:
    try:
        job = UserSyncBackgroundJob()
        if (
            result := job.start(
                JobTarget(
                    callable=sync_entry_point,
                    args=UserSyncArgs(add_to_changelog=False, enforce_sync=True),
                ),
                InitialStatusArgs(
                    title=job.gui_title(),
                    stoppable=False,
                    user=str(user.id) if user.id else None,
                ),
            )
        ).is_error():
            raise MKUserError(None, str(result.error))
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

    def shall_start(self) -> bool:
        """Some basic preliminary check to decide quickly whether to start the job"""
        return any(
            connection.sync_is_needed() for _connection_id, connection in active_connections()
        )

    def do_sync(
        self,
        job_interface: BackgroundProcessInterface,
        args: UserSyncArgs,
        load_users_func: Callable[[bool], Users],
        save_users_func: Callable[[Users, datetime], None],
    ) -> None:
        logger = job_interface.get_logger()
        with job_interface.gui_context():
            logger.info(_("Synchronization started..."))
            if self._execute_sync_action(
                logger,
                args.add_to_changelog,
                args.enforce_sync,
                load_users_func,
                save_users_func,
                datetime.now(),
            ):
                job_interface.send_result_message(
                    _("The user synchronization completed successfully.")
                )
            else:
                job_interface.send_exception(_("The user synchronization failed."))

    def _execute_sync_action(
        self,
        logger: Logger,
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

                logger.info(_("[%s] Starting sync for connection") % connection_id)
                connection.do_sync(
                    add_to_changelog=add_to_changelog,
                    only_username=None,
                    load_users_func=load_users,
                    save_users_func=save_users,
                )
                logger.info(_("[%s] Finished sync for connection") % connection_id)
            except Exception as e:
                logger.error(_("[%s] Exception: %s") % (connection_id, e))
                gui_logger.error(
                    "Exception (%s, userdb_job): %s", connection_id, traceback.format_exc()
                )

        logger.info(_("Finalizing synchronization"))
        general_userdb_job(now)
        return True
