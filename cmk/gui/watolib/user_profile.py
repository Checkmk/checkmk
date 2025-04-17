#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import time
from collections.abc import Mapping
from datetime import datetime
from multiprocessing import TimeoutError as mp_TimeoutError
from multiprocessing.pool import ThreadPool
from typing import Any, cast, Literal, NamedTuple

from livestatus import SiteConfiguration

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import SiteId

from cmk.utils.user import UserId

from cmk.gui import sites, userdb
from cmk.gui.config import active_config
from cmk.gui.exceptions import RequestTimeout
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import save_user_file
from cmk.gui.site_config import (
    get_login_slave_sites,
    get_site_config,
    is_replication_enabled,
    is_wato_slave_site,
)
from cmk.gui.type_defs import UserSpec, VisualTypeName
from cmk.gui.utils.request_context import copy_request_context
from cmk.gui.utils.urls import urlencode_vars
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import do_remote_automation, get_url, MKAutomationException
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.utils import mk_eval, mk_repr

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


def _synchronize_profiles_to_sites(logger, profiles_to_synchronize):
    if not profiles_to_synchronize:
        return

    remote_sites = [
        (site_id, get_site_config(active_config, site_id)) for site_id in get_login_slave_sites()
    ]

    logger.info(
        "Credentials changed for %s. Trying to sync to %d sites"
        % (", ".join(profiles_to_synchronize.keys()), len(remote_sites))
    )

    states = sites.states()

    pool = ThreadPool()
    jobs = []
    for site_id, site in remote_sites:
        jobs.append(
            pool.apply_async(
                copy_request_context(_sychronize_profile_worker),
                (states, site_id, site, profiles_to_synchronize),
            )
        )

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
                    add_user=False,
                    sites=[result.site_id],
                    need_restart=False,
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
    states: sites.SiteStates,
    site_id: SiteId,
    site: SiteConfiguration,
    profiles_to_synchronize: dict[UserId, Any],
) -> SynchronizationResult:
    if not is_replication_enabled(site):
        return SynchronizationResult(site_id, disabled=True)

    if site.get("disabled"):
        return SynchronizationResult(site_id, disabled=True)

    status = states.get(site_id, {}).get("state", "unknown")
    if status == "dead":
        return SynchronizationResult(
            site_id, error_text=_("Site %s is dead") % site_id, failed=True
        )

    try:
        result = push_user_profiles_to_site_transitional_wrapper(site, profiles_to_synchronize)
        if result is not True:
            return SynchronizationResult(site_id, error_text=result, failed=True)
        return SynchronizationResult(site_id, succeeded=True)
    except RequestTimeout:
        # This function is currently only used by the background job
        # which does not have any request timeout set, just in case...
        raise
    except Exception as e:
        return SynchronizationResult(site_id, error_text="%s" % e, failed=True)


# TODO: Why is the logger handed over here? The sync job could simply gather it's own
def handle_ldap_sync_finished(logger, profiles_to_synchronize, changes):
    _synchronize_profiles_to_sites(logger, profiles_to_synchronize)

    if changes and active_config.wato_enabled and not is_wato_slave_site():
        add_change(action_name="edit-users", text="<br>".join(changes), add_user=False)


def push_user_profiles_to_site_transitional_wrapper(
    site: SiteConfiguration,
    user_profiles: Mapping[UserId, UserSpec],
    visuals: Mapping[UserId, Mapping[VisualTypeName, Any]] | None = None,
) -> Literal[True] | str:
    try:
        return push_user_profiles_to_site(site, user_profiles, visuals)
    except MKAutomationException as e:
        if "Invalid automation command: push-profiles" in "%s" % e:
            failed_info = []
            for user_id, user in user_profiles.items():
                result = _legacy_push_user_profile_to_site(site, user_id, user)
                if result is not True:
                    failed_info.append(result)

            if failed_info:
                return "\n".join(failed_info)
            return True
        raise


def _legacy_push_user_profile_to_site(site, user_id, profile):
    url = (
        site["multisiteurl"]
        + "automation.py?"
        + urlencode_vars(
            [
                ("command", "push-profile"),
                ("secret", site["secret"]),
                ("siteid", site["id"]),
                ("debug", active_config.debug and "1" or ""),
            ]
        )
    )

    response = get_url(
        url,
        site.get("insecure", False),
        data={
            "user_id": user_id,
            "profile": mk_repr(profile).decode("ascii"),
        },
        timeout=60,
    )

    if not response:
        raise MKAutomationException(_("Empty output from remote site."))

    try:
        response = mk_eval(response)
    except Exception:
        # The remote site will send non-Python data in case of an error.
        raise MKAutomationException("{}: <pre>{}</pre>".format(_("Got invalid data"), response))
    return response


def push_user_profiles_to_site(
    site: SiteConfiguration,
    user_profiles: Mapping[UserId, UserSpec],
    visuals: Mapping[UserId, Mapping[VisualTypeName, Any]] | None = None,
) -> Literal[True]:
    def _serialize(user_profiles: Mapping[UserId, UserSpec]) -> Mapping[UserId, UserSpec]:
        """Do not synchronize user session information"""
        return {
            user_id: cast(UserSpec, {k: v for k, v in profile.items() if k != "session_info"})
            for user_id, profile in user_profiles.items()
        }

    do_remote_automation(
        site,
        "push-profiles",
        [("profiles", repr(_serialize(user_profiles))), ("visuals", repr(visuals))],
        timeout=60,
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
