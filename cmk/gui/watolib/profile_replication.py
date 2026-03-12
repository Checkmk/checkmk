#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Background job for replicating user profiles to remote sites"""

import logging
import re
import time
from collections.abc import Mapping
from typing import Any, cast, get_args, override

from pydantic import BaseModel

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui import userdb
from cmk.gui.background_job.job import (
    AlreadyRunningError,
    BackgroundJob,
    BackgroundJobRegistry,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobTarget,
)
from cmk.gui.config import active_config, Config
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import AnnotatedUserId, VisualTypeName
from cmk.gui.utils.roles import UserPermissions, UserPermissionSerializableConfig
from cmk.gui.watolib.activate_changes import ACTIVATION_TIME_PROFILE_SYNC, update_activation_time
from cmk.gui.watolib.automations import remote_automation_config_from_site_config
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.user_profile import push_user_profiles_to_site_transitional_wrapper
from cmk.gui.watolib.users import get_enabled_remote_sites_for_logged_in_user
from cmk.utils.automation_config import RemoteAutomationConfig


def _load_raw_visuals_of_a_user(
    what: VisualTypeName,
    user_id: UserId,
) -> dict[str, dict[str, Any]]:
    path = cmk.utils.paths.profile_dir / user_id / f"user_{what}.mk"
    return cast(
        dict[str, dict[str, Any]],
        store.try_load_file_from_pickle_cache(
            path, default={}, temp_dir=cmk.utils.paths.tmp_dir, root_dir=cmk.utils.paths.omd_root
        ),
    )


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


class ProfileReplicationArgs(BaseModel, frozen=True):
    user_id: AnnotatedUserId
    automation_configs: Mapping[SiteId, RemoteAutomationConfig]
    back_url: str
    user_permission_config: UserPermissionSerializableConfig
    debug: bool


def profile_replication_entry_point(
    job_interface: BackgroundProcessInterface, args: ProfileReplicationArgs
) -> None:
    # A ProfileReplicationBackgroundJob instance is constructed here to satisfy the
    # BackgroundJob.do_execute() interface, which is an instance method. The instance
    # state (back_url, job ID) is not used inside the subprocess — only the execute
    # logic matters.
    ProfileReplicationBackgroundJob(back_url=args.back_url, user_id=args.user_id).do_execute(
        args, job_interface
    )


class ProfileReplicationBackgroundJob(BackgroundJob):
    job_prefix = "profile-replication"

    @classmethod
    def gui_title(cls) -> str:
        return _("Profile replication")

    def __init__(self, back_url: str, user_id: UserId) -> None:
        self._back_url_value = back_url
        sanitized_user_id = re.sub(r"[^-0-9a-zA-Z_.]", "-", str(user_id))
        super().__init__(f"{self.job_prefix}-{sanitized_user_id}")

    @override
    def _back_url(self) -> str:
        return self._back_url_value

    def do_execute(
        self,
        args: ProfileReplicationArgs,
        job_interface: BackgroundProcessInterface,
    ) -> None:
        with job_interface.gui_context(
            UserPermissions.from_serialized_config(args.user_permission_config, permission_registry)
        ):
            self._do_execute(args, job_interface)

    def _do_execute(
        self,
        args: ProfileReplicationArgs,
        job_interface: BackgroundProcessInterface,
    ) -> None:
        users = userdb.load_users(lock=False)
        if args.user_id not in users:
            job_interface.send_result_message(_("The requested user does not exist"))
            return

        visuals_of_user = {
            what: _load_raw_visuals_of_a_user(what, args.user_id)
            for what in get_args(VisualTypeName)
        }

        num_sites = len(args.automation_configs)
        for idx, (site_id, automation_config) in enumerate(args.automation_configs.items(), 1):
            job_interface.send_progress_update(
                _("[%d/%d] Replicating to site %s...") % (idx, num_sites, site_id)
            )
            start = time.time()
            try:
                result = push_user_profiles_to_site_transitional_wrapper(
                    automation_config,
                    {args.user_id: users[args.user_id]},
                    {args.user_id: visuals_of_user},
                    debug=args.debug,
                )
            except Exception as e:
                duration = time.time() - start
                add_profile_replication_change(site_id, str(e))
                job_interface.send_progress_update(_("Replication to %s failed: %s") % (site_id, e))
                continue
            duration = time.time() - start
            update_activation_time(site_id, ACTIVATION_TIME_PROFILE_SYNC, duration)

            if result is not True:
                add_profile_replication_change(site_id, result)
                job_interface.send_progress_update(
                    _("Replication to %s failed: %s") % (site_id, result)
                )
            else:
                job_interface.send_progress_update(
                    _("Replication to %s successful (%.1fs)") % (site_id, duration)
                )

        job_interface.send_result_message(_("Profile replication completed"))


def register(job_registry: BackgroundJobRegistry) -> None:
    job_registry.register(ProfileReplicationBackgroundJob)


def start_profile_replication_job(back_url: str, *, config: Config) -> None:
    """Start a background job to replicate the current user's profile to all remote sites.

    If replication fails for a site, a pending change is recorded so an admin can sync later.
    If a job for this user is already running, the existing job continues.
    """
    remote_sites = get_enabled_remote_sites_for_logged_in_user(user, config.sites)
    if not remote_sites:
        return

    automation_configs: dict[SiteId, RemoteAutomationConfig] = {}
    for site_id, site_config in remote_sites.items():
        if "secret" not in site_config:
            add_profile_replication_change(site_id, _("Not logged in."))
            continue
        automation_configs[site_id] = remote_automation_config_from_site_config(site_config)

    if not automation_configs:
        logging.getLogger(__name__).debug(
            "Skipping profile replication for %s: no remote sites with automation secret", user.id
        )
        return

    assert user.id is not None
    job = ProfileReplicationBackgroundJob(back_url=back_url, user_id=user.id)
    start_result = job.start(
        JobTarget(
            callable=profile_replication_entry_point,
            args=ProfileReplicationArgs(
                user_id=user.id,
                automation_configs=automation_configs,
                back_url=back_url,
                user_permission_config=UserPermissionSerializableConfig.from_global_config(config),
                debug=config.debug,
            ),
        ),
        InitialStatusArgs(
            title=job.gui_title(),
            stoppable=False,
            user=str(user.id),
        ),
    )
    if start_result.is_error() and not isinstance(start_result.error, AlreadyRunningError):
        raise start_result.error
