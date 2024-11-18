#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
from datetime import datetime, timedelta
from logging import Logger
from pathlib import Path

import cmk.utils.paths

from cmk.gui.background_job import BackgroundJob, BackgroundProcessInterface, InitialStatusArgs
from cmk.gui.i18n import _
from cmk.gui.log import logger as gui_logger

from ..logged_in import user
from .store import load_users


def execute_user_profile_cleanup_job() -> None:
    """This function is called by the GUI cron job once a minute.

    Errors are logged to var/log/web.log."""
    job = UserProfileCleanupBackgroundJob()
    if job.is_active():
        gui_logger.debug("Job is already running: Skipping this time")
        return

    job.start(
        job.do_execute,
        InitialStatusArgs(
            title=job.gui_title(),
            lock_wato=False,
            stoppable=False,
            user=str(user.id) if user.id else None,
        ),
    )


class UserProfileCleanupBackgroundJob(BackgroundJob):
    job_prefix = "user_profile_cleanup"

    @staticmethod
    def last_run_path() -> Path:
        return Path(cmk.utils.paths.var_dir, "wato", "last_user_profile_cleanup.mk")

    @classmethod
    def gui_title(cls) -> str:
        return _("User profile cleanup")

    def __init__(self) -> None:
        super().__init__(self.job_prefix)

    def do_execute(self, job_interface: BackgroundProcessInterface) -> None:
        with job_interface.gui_context():
            try:
                cleanup_abandoned_profiles(self._logger, datetime.now(), timedelta(days=30))
                job_interface.send_result_message(_("Job finished"))
            finally:
                UserProfileCleanupBackgroundJob.last_run_path().touch(exist_ok=True)


def cleanup_abandoned_profiles(logger: Logger, now: datetime, max_age: timedelta) -> None:
    """Cleanup abandoned profile directories

    The cleanup is done like this:

    - Load the userdb to get the list of locally existing users
    - Iterate over all use profile directories and find all directories that don't belong to an
      existing user
    - For each of these directories find the most recent written file
    - In case the most recent written file is older than max_age days delete the profile directory
    - Create an audit log entry for each removed directory
    """
    users = set(load_users().keys())
    if not users:
        logger.warning("Found no users. Be careful and not cleaning up anything.")
        return

    profile_base_dir = cmk.utils.paths.profile_dir
    # Some files like ldap_*_sync_time.mk can be placed in
    # ~/var/check_mk/web, causing error entries in web.log while trying to
    # delete a dir
    profiles = {
        profile_dir.name for profile_dir in profile_base_dir.iterdir() if profile_dir.is_dir()
    }

    abandoned_profiles = sorted(profiles - users)
    if not abandoned_profiles:
        logger.debug("Found no abandoned profile.")
        return

    logger.info("Found %d abandoned profiles", len(abandoned_profiles))
    logger.debug("Profiles: %s", ", ".join(abandoned_profiles))

    for profile_name in abandoned_profiles:
        profile_dir = profile_base_dir / profile_name
        last_mtime = datetime.fromtimestamp(
            max((p.stat().st_mtime for p in profile_dir.glob("*.mk")), default=0.0)
        )
        if now - last_mtime > max_age:
            try:
                logger.info("Removing abandoned profile directory: %s", profile_name)
                shutil.rmtree(profile_dir)
            except OSError:
                logger.debug("Could not delete %s", profile_dir, exc_info=True)
