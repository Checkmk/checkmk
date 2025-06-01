#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import time
from collections.abc import Mapping, Sequence
from datetime import datetime
from logging import Logger
from multiprocessing import TimeoutError as mp_TimeoutError
from multiprocessing.pool import ThreadPool
from typing import Any, cast, Literal, NamedTuple

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId

from cmk.gui import sites, userdb
from cmk.gui.config import active_config
from cmk.gui.exceptions import RequestTimeout
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import save_user_file
from cmk.gui.site_config import (
    get_login_slave_sites,
    is_wato_slave_site,
)
from cmk.gui.sites import SiteStatus
from cmk.gui.type_defs import UserSpec, VisualTypeName
from cmk.gui.utils.request_context import copy_request_context
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import (
    do_remote_automation,
    RemoteAutomationConfig,
)
from cmk.gui.watolib.changes import add_change

# In case the sync is done on the master of a distributed setup the auth serial
# is increased on the master, but not on the slaves. The user can not access the
# slave sites anymore with the master sites cookie since the serials differ. In
# case the slave sites sync with LDAP on their own this issue will be repaired after
# the next LDAP sync on the slave, but in case the slaves do not sync, this problem
# will be repaired automagically once an admin performs the next Setup sync for
# another reason.
# Now, to solve this issue, we issue a user profile sync in case the password has
# been changed. We do this only when only the password has changed.
# Hopefully we have no large bulks of users changing their passwords at the same
# time. In this case the implementation does not scale well. We would need to
# change this to some kind of profile bulk sync per site.


class SynchronizationResult:
    def __init__(
        self,
        site_id: SiteId,
        error_text: str | None = None,
        disabled: bool = False,
        succeeded: bool = False,
        failed: bool = False,
    ) -> None:
        self.site_id = site_id
        self.error_text = error_text
        self.failed = failed
        self.disabled = disabled
        self.succeeded = succeeded


def _synchronize_profiles_to_sites(
    logger: Logger, profiles_to_synchronize: dict[UserId, UserSpec], debug: bool
) -> None:
    if not profiles_to_synchronize:
        return

    remote_sites = [(site_id, active_config.sites[site_id]) for site_id in get_login_slave_sites()]

    logger.info(
        "Credentials changed for %s. Trying to sync to %d sites"
        % (", ".join(profiles_to_synchronize.keys()), len(remote_sites))
    )

    states = sites.states()

    pool = ThreadPool()
    jobs = [
        pool.apply_async(
            copy_request_context(_sychronize_profile_worker),
            (
                states.get(site_id, {}),
                RemoteAutomationConfig.from_site_config(site_config),
                profiles_to_synchronize,
                debug,
            ),
        )
        for site_id, site_config in remote_sites
    ]

    results = []
    start_time = time.time()
    while time.time() - start_time < 30:
        for job in jobs[:]:
            try:
                results.append(job.get(timeout=0.5))
                jobs.remove(job)
            except mp_TimeoutError:
                pass
        if not jobs:
            break

    contacted_sites = {x[0] for x in remote_sites}
    working_sites = {result.site_id for result in results}
    for site_id in contacted_sites - working_sites:
        results.append(
            SynchronizationResult(
                site_id, error_text=_("No response from update thread"), failed=True
            )
        )

    for result in results:
        if result.error_text:
            logger.info(f"  FAILED [{result.site_id}]: {result.error_text}")
            if active_config.wato_enabled:
                add_change(
                    action_name="edit-users",
                    text=_l("Password changed (sync failed: %s)") % result.error_text,
                    user_id=None,
                    sites=[result.site_id],
                    need_restart=False,
                    use_git=active_config.wato_use_git,
                )

    pool.terminate()
    pool.join()

    num_failed = sum(1 for result in results if result.failed)
    num_disabled = sum(1 for result in results if result.disabled)
    num_succeeded = sum(1 for result in results if result.succeeded)
    logger.info(
        "  Disabled: %d, Succeeded: %d, Failed: %d" % (num_disabled, num_succeeded, num_failed)
    )


def _sychronize_profile_worker(
    site_status: SiteStatus,
    automation_config: RemoteAutomationConfig,
    profiles_to_synchronize: dict[UserId, UserSpec],
    debug: bool,
) -> SynchronizationResult:
    if site_status.get("state", "unknown") == "dead":
        return SynchronizationResult(
            automation_config.site_id,
            error_text=_("Site %s is dead") % automation_config.site_id,
            failed=True,
        )

    try:
        result = push_user_profiles_to_site_transitional_wrapper(
            automation_config,
            profiles_to_synchronize,
            None,
            debug=debug,
        )
        if result is not True:
            return SynchronizationResult(automation_config.site_id, error_text=result, failed=True)
        return SynchronizationResult(automation_config.site_id, succeeded=True)
    except RequestTimeout:
        # This function is currently only used by the background job
        # which does not have any request timeout set, just in case...
        raise
    except Exception as e:
        return SynchronizationResult(automation_config.site_id, error_text="%s" % e, failed=True)


# TODO: Why is the logger handed over here? The sync job could simply gather it's own
def handle_ldap_sync_finished(
    logger: Logger,
    profiles_to_synchronize: dict[UserId, UserSpec],
    changes: Sequence[str],
    debug: bool,
) -> None:
    _synchronize_profiles_to_sites(logger, profiles_to_synchronize, debug=debug)

    if changes and active_config.wato_enabled and not is_wato_slave_site():
        add_change(
            action_name="edit-users",
            text="<br>".join(changes),
            user_id=None,
            use_git=active_config.wato_use_git,
        )


def push_user_profiles_to_site_transitional_wrapper(
    automation_config: RemoteAutomationConfig,
    user_profiles: Mapping[UserId, UserSpec],
    visuals: Mapping[UserId, Mapping[VisualTypeName, Any]] | None,
    *,
    debug: bool,
) -> Literal[True] | str:
    return _push_user_profiles_to_site(automation_config, user_profiles, visuals, debug=debug)


def _push_user_profiles_to_site(
    automation_config: RemoteAutomationConfig,
    user_profiles: Mapping[UserId, UserSpec],
    visuals: Mapping[UserId, Mapping[VisualTypeName, Any]] | None,
    debug: bool,
) -> Literal[True]:
    def _serialize(user_profiles: Mapping[UserId, UserSpec]) -> Mapping[UserId, UserSpec]:
        """Do not synchronize user session information"""
        return {
            user_id: cast(UserSpec, {k: v for k, v in profile.items() if k != "session_info"})
            for user_id, profile in user_profiles.items()
        }

    do_remote_automation(
        automation_config,
        "push-profiles",
        [("profiles", repr(_serialize(user_profiles))), ("visuals", repr(visuals))],
        timeout=60,
        debug=debug,
    )
    return True


class PushUserProfilesRequest(NamedTuple):
    user_profiles: Mapping[UserId, UserSpec]
    user_visuals: Mapping[UserId, Mapping[VisualTypeName, Any]] | None


class PushUserProfilesToSite(AutomationCommand[PushUserProfilesRequest]):
    def command_name(self) -> str:
        return "push-profiles"

    def get_request(self) -> PushUserProfilesRequest:
        return PushUserProfilesRequest(
            ast.literal_eval(request.get_str_input_mandatory("profiles")),
            ast.literal_eval(request.get_str_input_mandatory("visuals", None)),
        )

    def execute(self, api_request: PushUserProfilesRequest) -> Literal[True]:
        user_profiles = api_request.user_profiles
        visuals_by_user = api_request.user_visuals

        if not user_profiles:
            raise MKGeneralException(_("Invalid call: No profiles set."))

        users = userdb.load_users(lock=True)
        for user_id, profile in user_profiles.items():
            users[user_id] = profile
        userdb.save_users(users, datetime.now())

        if visuals_by_user:
            for user_id, visuals_by_type in visuals_by_user.items():
                for what, visuals in visuals_by_type.items():
                    if visuals:
                        save_user_file(f"user_{what}", visuals, user_id)

        return True
