#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from collections.abc import Sequence
from datetime import datetime
from logging import Logger
from typing import override

from pydantic import BaseModel

from cmk.gui.background_job.job import (
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobTarget,
)
from cmk.gui.config import active_config, Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger as gui_logger
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import (
    CustomUserAttrSpec,
    UserSpec,
)
from cmk.gui.utils.roles import UserPermissions, UserPermissionSerializableConfig
from cmk.web.utils.urls import makeuri_contextless

from ._connections import active_connections
from ._connector import LoadUsersFunction, SaveUsersFunction
from ._user_attribute import get_user_attributes, UserAttribute
from ._user_sync_config import user_sync_config
from .store import general_userdb_job, load_users, save_users


def execute_userdb_job(config: Config) -> None:
    """This function is called by the GUI cron job once a minute.

    Errors are logged to var/log/web.log."""
    if user_sync_config() is None:
        # Automatic user attribute synchronization is disabled for this site.
        return

    job = UserSyncBackgroundJob()

    if not job.shall_start():
        gui_logger.debug("Job shall not start")
        return

    if (
        result := job.start(
            JobTarget(
                callable=sync_entry_point,
                args=UserSyncArgs(
                    add_to_changelog=False,
                    enforce_sync=False,
                    custom_user_attributes=config.wato_user_attrs,
                    default_user_profile=config.default_user_profile,
                    user_permission_config=UserPermissionSerializableConfig.from_global_config(
                        config
                    ),
                ),
            ),
            InitialStatusArgs(
                title=job.gui_title(),
                stoppable=False,
                user=str(user.id) if user.id else None,
            ),
        )
    ).is_error():
        gui_logger.error("Error starting user sync job: %(error)s", {"error": result.error})


class UserSyncArgs(BaseModel, frozen=True):
    add_to_changelog: bool
    enforce_sync: bool
    custom_user_attributes: Sequence[CustomUserAttrSpec]
    default_user_profile: UserSpec
    user_permission_config: UserPermissionSerializableConfig


def sync_entry_point(job_interface: BackgroundProcessInterface, args: UserSyncArgs) -> None:
    UserSyncBackgroundJob().do_sync(
        job_interface,
        args,
        load_users_func=load_users,
        save_users_func=save_users,
    )


def ajax_sync(ctx: PageContext) -> None:
    try:
        job = UserSyncBackgroundJob()
        if (
            result := job.start(
                JobTarget(
                    callable=sync_entry_point,
                    args=UserSyncArgs(
                        add_to_changelog=False,
                        enforce_sync=True,
                        custom_user_attributes=ctx.config.wato_user_attrs,
                        default_user_profile=ctx.config.default_user_profile,
                        user_permission_config=UserPermissionSerializableConfig.from_global_config(
                            ctx.config
                        ),
                    ),
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
        if ctx.config.debug:
            raise
        response.set_data("ERROR %s\n" % e)


class UserSyncBackgroundJob(BackgroundJob):
    job_prefix = "user_sync"

    @classmethod
    @override
    def gui_title(cls) -> str:
        return _("User synchronization")

    def __init__(self) -> None:
        super().__init__(self.job_prefix)

    @override
    def _back_url(self) -> str:
        return makeuri_contextless(request, [("mode", "users")], filename="wato.py")

    def shall_start(self) -> bool:
        """Some basic preliminary check to decide quickly whether to start the job"""
        return any(
            connection.sync_is_needed()
            for _connection_id, connection in active_connections(active_config.user_connections)
        )

    def do_sync(
        self,
        job_interface: BackgroundProcessInterface,
        args: UserSyncArgs,
        load_users_func: LoadUsersFunction,
        save_users_func: SaveUsersFunction,
    ) -> None:
        logger = job_interface.get_logger()
        with job_interface.gui_context(
            UserPermissions.from_serialized_config(args.user_permission_config, permission_registry)
        ):
            logger.info(_("Synchronization started..."))
            if self._execute_sync_action(
                logger,
                args.add_to_changelog,
                args.enforce_sync,
                get_user_attributes(args.custom_user_attributes),
                load_users_func,
                save_users_func,
                args.default_user_profile,
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
        user_attributes: Sequence[tuple[str, UserAttribute]],
        load_users_func: LoadUsersFunction,
        save_users_func: SaveUsersFunction,
        default_user_profile: UserSpec,
        now: datetime,
    ) -> bool:
        for connection_id, connection in active_connections(active_config.user_connections):
            try:
                if not enforce_sync and not connection.sync_is_needed():
                    continue

                logger.info(
                    _("[%(connection_id)s] Starting sync for connection"),
                    {"connection_id": connection_id},
                )
                connection.do_sync(
                    add_to_changelog=add_to_changelog,
                    only_username=None,
                    user_attributes=user_attributes,
                    load_users_func=load_users_func,
                    save_users_func=save_users_func,
                    default_user_profile=default_user_profile,
                )
                logger.info(
                    _("[%(connection_id)s] Finished sync for connection"),
                    {"connection_id": connection_id},
                )
            except Exception:
                logger.exception(
                    _("[%(connection_id)s] exception"), {"connection_id": connection_id}
                )
                gui_logger.error(
                    "Exception (%(connection_id)s, userdb_job): %(traceback)s",
                    {"connection_id": connection_id, "traceback": traceback.format_exc()},
                )

        logger.info(_("Finalizing synchronization"))
        general_userdb_job(user_attributes, now)
        return True
