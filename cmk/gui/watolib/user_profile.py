#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from typing import NamedTuple

import cmk.gui.config as config
import cmk.gui.userdb as userdb
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.globals import html
from cmk.gui.watolib.automation_commands import (
    AutomationCommand,
    automation_command_registry,
)
from cmk.gui.watolib.automations import (
    MKAutomationException,
    do_remote_automation,
    get_url,
)
from cmk.gui.watolib.utils import (
    mk_eval,
    mk_repr,
)


def push_user_profiles_to_site_transitional_wrapper(site, user_profiles):
    try:
        return push_user_profiles_to_site(site, user_profiles)
    except MKAutomationException as e:
        if "Invalid automation command: push-profiles" in "%s" % e:
            failed_info = []
            for user_id, user in user_profiles.items():
                result = _legacy_push_user_profile_to_site(site, user_id, user)
                if result != True:
                    failed_info.append(result)

            if failed_info:
                return "\n".join(failed_info)
            return True
        else:
            raise


def _legacy_push_user_profile_to_site(site, user_id, profile):
    url = site["multisiteurl"] + "automation.py?" + html.urlencode_vars([
        ("command", "push-profile"),
        ("secret", site["secret"]),
        ("siteid", site['id']),
        ("debug", config.debug and "1" or ""),
    ])

    response = get_url(url,
                       site.get('insecure', False),
                       data={
                           'user_id': user_id,
                           'profile': mk_repr(profile),
                       },
                       timeout=60)

    if not response:
        raise MKAutomationException(_("Empty output from remote site."))

    try:
        response = mk_eval(response)
    except Exception:
        # The remote site will send non-Python data in case of an error.
        raise MKAutomationException("%s: <pre>%s</pre>" % (_("Got invalid data"), response))
    return response


def push_user_profiles_to_site(site, user_profiles):
    return do_remote_automation(site,
                                "push-profiles", [("profiles", repr(user_profiles))],
                                timeout=60)


PushUserProfilesRequest = NamedTuple("PushUserProfilesRequest", [("user_profiles", dict)])


@automation_command_registry.register
class PushUserProfilesToSite(AutomationCommand):
    def command_name(self):
        return "push-profiles"

    def get_request(self):
        return PushUserProfilesRequest(ast.literal_eval(html.request.var("profiles")))

    def execute(self, request):
        user_profiles = request.user_profiles

        if not user_profiles:
            raise MKGeneralException(_('Invalid call: No profiles set.'))

        users = userdb.load_users(lock=True)
        for user_id, profile in user_profiles.items():
            users[user_id] = profile
        userdb.save_users(users)
        return True
