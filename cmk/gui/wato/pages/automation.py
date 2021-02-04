#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""These functions implement a web service with that a master can call
automation functions on slaves,"""

import traceback

from six import ensure_str

import cmk.utils.version as cmk_version
import cmk.utils.store as store
import cmk.utils.paths
from cmk.utils.type_defs import UserId

import cmk.gui.utils
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
        self._handle_exc(self.page)

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
                "version": cmk_version.__version__,
                "edition_short": cmk_version.edition_short(),
                "login_secret": _get_login_secret(create_on_demand=True),
            }

        html.write(repr(response))


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
        self._command = html.request.get_str_input_mandatory("command")

    def _authenticate(self):
        secret = html.request.var("secret")

        if not secret:
            raise MKAuthException(_("Missing secret for automation command."))

        if secret != _get_login_secret():
            raise MKAuthException(_("Invalid automation secret."))

    # TODO: Better use AjaxPage.handle_page() for standard AJAX call error handling. This
    # would need larger refactoring of the generic html.popup_trigger() mechanism.
    def handle_page(self):
        self._handle_exc(self.page)

    def page(self):
        # To prevent mixups in written files we use the same lock here as for
        # the normal WATO page processing. This might not be needed for some
        # special automation requests, like inventory e.g., but to keep it simple,
        # we request the lock in all cases.
        with store.lock_checkmk_configuration():
            watolib.init_wato_datastructures(with_wato_lock=False)
            # TODO: Refactor these two calls to also use the automation_command_registry
            if self._command == "checkmk-automation":
                self._execute_cmk_automation()
                return
            if self._command == "push-profile":
                self._execute_push_profile()
                return
            try:
                automation_command = watolib.automation_command_registry[self._command]
            except KeyError:
                raise MKGeneralException(_("Invalid automation command: %s.") % self._command)
            self._execute_automation_command(automation_command)

    def _execute_cmk_automation(self):
        cmk_command = html.request.get_str_input_mandatory("automation")
        args = watolib.mk_eval(html.request.get_str_input_mandatory("arguments"))
        indata = watolib.mk_eval(html.request.get_str_input_mandatory("indata"))
        stdin_data = watolib.mk_eval(html.request.get_str_input_mandatory("stdin_data"))
        timeout = watolib.mk_eval(html.request.get_str_input_mandatory("timeout"))
        result = watolib.check_mk_local_automation(cmk_command, args, indata, stdin_data, timeout)
        # Don't use write_text() here (not needed, because no HTML document is rendered)
        html.write(repr(result))

    def _execute_push_profile(self):
        try:
            # Don't use write_text() here (not needed, because no HTML document is rendered)
            html.write(ensure_str(watolib.mk_repr(self._automation_push_profile())))
        except Exception as e:
            logger.exception("error pushing profile")
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
        users[UserId(user_id)] = watolib.mk_eval(profile)
        userdb.save_users(users)

        return True

    def _execute_automation_command(self, automation_command):
        try:
            # Don't use write_text() here (not needed, because no HTML document is rendered)
            automation = automation_command()
            html.write(repr(automation.execute(automation.get_request())))
        except Exception as e:
            logger.exception("error executing automation command")
            if config.debug:
                raise
            html.write_text(_("Internal automation error: %s\n%s") % (e, traceback.format_exc()))


def _get_login_secret(create_on_demand=False):
    path = cmk.utils.paths.var_dir + "/wato/automation_secret.mk"

    secret = store.load_object_from_file(path)
    if secret is not None:
        return secret

    if not create_on_demand:
        return None

    secret = cmk.gui.utils.get_random_string(32)
    store.save_object_to_file(path, secret)
    return secret
