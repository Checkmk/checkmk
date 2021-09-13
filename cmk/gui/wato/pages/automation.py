#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""These functions implement a web service with that a master can call
automation functions on slaves,"""

import traceback

import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.site import omd_site
from cmk.utils.type_defs import UserId

import cmk.gui.userdb as userdb
import cmk.gui.utils
import cmk.gui.watolib as watolib
from cmk.gui.exceptions import MKAuthException, MKGeneralException
from cmk.gui.globals import config, request, response, user
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.pages import AjaxPage, page_registry
from cmk.gui.utils.logged_in import SuperUserContext


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
        if not user.may("wato.automation"):
            raise MKAuthException(_("This account has no permission for automation."))

        response.set_content_type("text/plain")

        if not request.has_var("_version"):
            # Be compatible to calls from sites using versions before 1.5.0p10.
            # Deprecate with 1.7 by throwing an exception in this situation.
            resp = _get_login_secret(create_on_demand=True)
        else:
            resp = {
                "version": cmk_version.__version__,
                "edition_short": cmk_version.edition_short(),
                "login_secret": _get_login_secret(create_on_demand=True),
            }

        response.set_data(repr(resp))


@page_registry.register_page("noauth:automation")
class ModeAutomation(AjaxPage):
    """Executes the requested automation call

    This page is accessible without regular login. The request is authenticated using the given
    login secret that has previously been exchanged during "site login" (see above).
    """

    def _from_vars(self):
        self._authenticate()
        self._command = request.get_str_input_mandatory("command")

    def _authenticate(self):
        secret = request.var("secret")

        if not secret:
            raise MKAuthException(_("Missing secret for automation command."))

        if secret != _get_login_secret():
            raise MKAuthException(_("Invalid automation secret."))

    # TODO: Better use AjaxPage.handle_page() for standard AJAX call error handling. This
    # would need larger refactoring of the generic html.popup_trigger() mechanism.
    def handle_page(self):
        # The automation page is accessed unauthenticated. After leaving the index.py area
        # into the page handler we always want to have a user context initialized to keep
        # the code free from special cases (if no user logged in, then...). So fake the
        # logged in user here.
        with SuperUserContext():
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
        cmk_command = request.get_str_input_mandatory("automation")
        args = watolib.mk_eval(request.get_str_input_mandatory("arguments"))
        indata = watolib.mk_eval(request.get_str_input_mandatory("indata"))
        stdin_data = watolib.mk_eval(request.get_str_input_mandatory("stdin_data"))
        timeout = watolib.mk_eval(request.get_str_input_mandatory("timeout"))
        result = watolib.check_mk_local_automation(cmk_command, args, indata, stdin_data, timeout)
        # Don't use write_text() here (not needed, because no HTML document is rendered)
        response.set_data(repr(result))

    def _execute_push_profile(self):
        try:
            response.set_data(str(watolib.mk_repr(self._automation_push_profile())))
        except Exception as e:
            logger.exception("error pushing profile")
            if config.debug:
                raise
            response.set_data(_("Internal automation error: %s\n%s") % (e, traceback.format_exc()))

    def _automation_push_profile(self):
        site_id = request.var("siteid")
        if not site_id:
            raise MKGeneralException(_("Missing variable siteid"))

        user_id = request.var("user_id")
        if not user_id:
            raise MKGeneralException(_("Missing variable user_id"))

        our_id = omd_site()

        if our_id is not None and our_id != site_id:
            raise MKGeneralException(
                _("Site ID mismatch. Our ID is '%s', but you are saying we are '%s'.")
                % (our_id, site_id)
            )

        profile = request.var("profile")
        if not profile:
            raise MKGeneralException(_("Invalid call: The profile is missing."))

        users = userdb.load_users(lock=True)
        users[UserId(user_id)] = watolib.mk_eval(profile)
        userdb.save_users(users)

        return True

    def _execute_automation_command(self, automation_command):
        try:
            # Don't use write_text() here (not needed, because no HTML document is rendered)
            automation = automation_command()
            response.set_data(repr(automation.execute(automation.get_request())))
        except Exception as e:
            logger.exception("error executing automation command")
            if config.debug:
                raise
            response.set_data(_("Internal automation error: %s\n%s") % (e, traceback.format_exc()))


def _get_login_secret(create_on_demand=False):
    path = cmk.utils.paths.var_dir + "/wato/automation_secret.mk"

    secret = store.load_object_from_file(path, default=None)
    if secret is not None:
        return secret

    if not create_on_demand:
        return None

    secret = cmk.gui.utils.get_random_string(32)
    store.save_object_to_file(path, secret)
    return secret
