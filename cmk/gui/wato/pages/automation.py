#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""These functions implement a web service with that a master can call
automation functions on slaves,"""

import traceback

import cmk
import cmk.utils.store as store
import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.userdb as userdb

from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.log import logger
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKAuthException, MKGeneralException


@page_registry.register_page("automation_login")
class ModeAutomationLogin(AjaxPage):
    """Is executed by the central Check_MK site during creation of the WATO master/slave sync to

    When the page method is execute a remote (master) site has successfully
    logged in using valid credentials of an administrative user. The login is
    done be exchanging a login secret. If such a secret is not yet present it
    is created on the fly."""

    # TODO: Better use AjaxPage.handle_page() for standard AJAX call error handling. This
    # would need larger refactoring of the generic html.popup_trigger() mechanism.
    def handle_page(self):
        self.page()

    def page(self):
        if not config.user.may("wato.automation"):
            raise MKAuthException(_("This account has no permission for automation."))

        html.set_output_format("python")

        if not html.request.has_var("_version"):
            # Be compatible to calls from sites using versions before 1.5.0p10.
            # Deprecate with 1.7 by throwing an exception in this situation.
            response = _get_login_secret(create_on_demand=True)
        else:
            response = {
                "version": cmk.__version__,
                "edition_short": cmk.edition_short(),
                "login_secret": _get_login_secret(create_on_demand=True),
            }
        html.write_html(repr(response))


@page_registry.register_page("noauth:automation")
class ModeAutomation(AjaxPage):
    """Executes the requested automation call

    This page is accessible without regular login. The request is authenticated using the given
    login secret that has previously been exchanged during "site login" (see above).
    """

    def __init__(self):
        super(ModeAutomation, self).__init__()

        # The automation page is accessed unauthenticated. After leaving the index.py area
        # into the page handler we always want to have a user context initialized to keep
        # the code free from special cases (if no user logged in, then...). So fake the
        # logged in user here.
        config.set_super_user()

    def _from_vars(self):
        self._authenticate()
        self._command = html.request.var("command")

    def _authenticate(self):
        secret = html.request.var("secret")

        if not secret:
            raise MKAuthException(_("Missing secret for automation command."))

        if secret != _get_login_secret():
            raise MKAuthException(_("Invalid automation secret."))

    # TODO: Better use AjaxPage.handle_page() for standard AJAX call error handling. This
    # would need larger refactoring of the generic html.popup_trigger() mechanism.
    def handle_page(self):
        self.page()

    def page(self):
        # To prevent mixups in written files we use the same lock here as for
        # the normal WATO page processing. This might not be needed for some
        # special automation requests, like inventory e.g., but to keep it simple,
        # we request the lock in all cases.
        with watolib.lock_checkmk_configuration():
            watolib.init_wato_datastructures(with_wato_lock=False)

            # TODO: Refactor these two calls to also use the automation_command_registry
            if self._command == "checkmk-automation":
                self._execute_cmk_automation()
                return

            elif self._command == "push-profile":
                self._execute_push_profile()
                return

            try:
                automation_command = watolib.automation_command_registry[self._command]
            except KeyError:
                raise MKGeneralException(_("Invalid automation command: %s.") % self._command)

            self._execute_automation_command(automation_command)

    def _execute_cmk_automation(self):
        cmk_command = html.request.var("automation")
        args = watolib.mk_eval(html.request.var("arguments"))
        indata = watolib.mk_eval(html.request.var("indata"))
        stdin_data = watolib.mk_eval(html.request.var("stdin_data"))
        timeout = watolib.mk_eval(html.request.var("timeout"))
        result = watolib.check_mk_local_automation(cmk_command, args, indata, stdin_data, timeout)
        # Don't use write_text() here (not needed, because no HTML document is rendered)
        html.write(repr(result))

    def _execute_push_profile(self):
        try:
            # Don't use write_text() here (not needed, because no HTML document is rendered)
            html.write(watolib.mk_repr(self._automation_push_profile()))
        except Exception as e:
            logger.exception()
            if config.debug:
                raise
            html.write_text(_("Internal automation error: %s\n%s") % (e, traceback.format_exc()))

    def _automation_push_profile(self):
        site_id = html.request.var("siteid")
        if not site_id:
            raise MKGeneralException(_("Missing variable siteid"))

        user_id = html.request.var("user_id")
        if not user_id:
            raise MKGeneralException(_("Missing variable user_id"))

        our_id = config.omd_site()

        if our_id is not None and our_id != site_id:
            raise MKGeneralException(
                _("Site ID mismatch. Our ID is '%s', but you are saying we are '%s'.") %
                (our_id, site_id))

        profile = html.request.var("profile")
        if not profile:
            raise MKGeneralException(_('Invalid call: The profile is missing.'))

        users = userdb.load_users(lock=True)
        profile = watolib.mk_eval(profile)
        users[user_id] = profile
        userdb.save_users(users)

        return True

    def _execute_automation_command(self, automation_command):
        try:
            # Don't use write_text() here (not needed, because no HTML document is rendered)
            automation = automation_command()
            html.write(repr(automation.execute(automation.get_request())))
        except Exception as e:
            logger.exception()
            if config.debug:
                raise
            html.write_text(_("Internal automation error: %s\n%s") % \
                            (e, traceback.format_exc()))


def _get_login_secret(create_on_demand=False):
    path = cmk.utils.paths.var_dir + "/wato/automation_secret.mk"

    secret = store.load_data_from_file(path)
    if secret is not None:
        return secret

    if not create_on_demand:
        return None

    secret = cmk.gui.utils.get_random_string(32)
    store.save_data_to_file(path, secret)
    return secret
