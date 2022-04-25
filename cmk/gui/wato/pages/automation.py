#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""These functions implement a web service with that a master can call
automation functions on slaves,"""

import traceback
from contextlib import nullcontext
from datetime import datetime
from typing import Iterable

import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.site import omd_site
from cmk.utils.type_defs import UserId

from cmk.automations.results import result_type_registry, SerializedResult

import cmk.gui.userdb as userdb
import cmk.gui.utils
import cmk.gui.watolib as watolib
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKGeneralException
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import SuperUserContext, user
from cmk.gui.pages import AjaxPage, page_registry
from cmk.gui.watolib.automations import compatible_with_central_site


@page_registry.register_page("automation_login")
class ModeAutomationLogin(AjaxPage):
    """Is executed by the central Checkmk site to get the site secret of the remote site

    When the page method is execute a remote (central) site has successfully
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
        _set_version_headers()

        # Parameter was added with 1.5.0p10
        if not request.has_var("_version"):
            raise MKGeneralException(_("Your central site is incompatible with this remote site"))

        # - _version and _edition_short were added with 1.5.0p10 to the login call only
        # - x-checkmk-version and x-checkmk-edition were added with 2.0.0p1
        # Prefer the headers and fall back to the request variables for now.
        central_version = (
            request.headers["x-checkmk-version"]
            if "x-checkmk-version" in request.headers
            else request.get_ascii_input_mandatory("_version")
        )
        central_edition_short = (
            request.headers["x-checkmk-edition"]
            if "x-checkmk-edition" in request.headers
            else request.get_ascii_input_mandatory("_edition_short")
        )

        if not compatible_with_central_site(
            central_version,
            central_edition_short,
            cmk_version.__version__,
            cmk_version.edition().short,
        ):
            raise MKGeneralException(
                _(
                    "Your central site (Version: %s, Edition: %s) is incompatible with this "
                    "remote site (Version: %s, Edition: %s)"
                )
                % (
                    central_version,
                    central_edition_short,
                    cmk_version.__version__,
                    cmk_version.edition().short,
                )
            )

        response.set_data(
            repr(
                {
                    "version": cmk_version.__version__,
                    "edition_short": cmk_version.edition().short,
                    "login_secret": _get_login_secret(create_on_demand=True),
                }
            )
        )


@page_registry.register_page("noauth:automation")
class ModeAutomation(AjaxPage):
    """Executes the requested automation call

    This page is accessible without regular login. The request is authenticated using the given
    login secret that has previously been exchanged during "site login" (see above).
    """

    def _from_vars(self):
        self._authenticate()
        _set_version_headers()
        self._verify_compatibility()
        self._command = request.get_str_input_mandatory("command")

    def _authenticate(self):
        secret = request.var("secret")

        if not secret:
            raise MKAuthException(_("Missing secret for automation command."))

        if secret != _get_login_secret():
            raise MKAuthException(_("Invalid automation secret."))

    def _verify_compatibility(self) -> None:
        central_version = request.headers.get("x-checkmk-version", "")
        central_edition_short = request.headers.get("x-checkmk-edition", "")
        if not compatible_with_central_site(
            central_version,
            central_edition_short,
            cmk_version.__version__,
            cmk_version.edition().short,
        ):
            raise MKGeneralException(
                _(
                    "Your central site (Version: %s, Edition: %s) is incompatible with this "
                    "remote site (Version: %s, Edition: %s)"
                )
                % (
                    central_version,
                    central_edition_short,
                    cmk_version.__version__,
                    cmk_version.edition().short,
                )
            )

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
        lock_config = not (
            self._command == "checkmk-automation"
            and request.get_str_input_mandatory("automation") == "active-check"
        )
        with store.lock_checkmk_configuration() if lock_config else nullcontext():
            self._execute_automation()

    def _execute_automation(self):
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

    @staticmethod
    def _format_cmk_automation_result(
        *,
        serialized_result: SerializedResult,
        cmk_command: str,
        cmdline_cmd: Iterable[str],
    ) -> str:
        try:
            return (
                repr(result_type_registry[cmk_command].deserialize(serialized_result).to_pre_21())
                if watolib.remote_automation_call_came_from_pre21()
                else serialized_result
            )
        except SyntaxError as e:
            raise watolib.local_automation_failure(
                command=cmk_command,
                cmdline=cmdline_cmd,
                out=serialized_result,
                exc=e,
            )

    def _execute_cmk_automation(self):
        cmk_command = request.get_str_input_mandatory("automation")
        args = watolib.mk_eval(request.get_str_input_mandatory("arguments"))
        indata = watolib.mk_eval(request.get_str_input_mandatory("indata"))
        stdin_data = watolib.mk_eval(request.get_str_input_mandatory("stdin_data"))
        timeout = watolib.mk_eval(request.get_str_input_mandatory("timeout"))
        cmdline_cmd, serialized_result = watolib.check_mk_local_automation_serialized(
            command=cmk_command,
            args=args,
            indata=indata,
            stdin_data=stdin_data,
            timeout=timeout,
        )
        # Don't use write_text() here (not needed, because no HTML document is rendered)
        response.set_data(
            self._format_cmk_automation_result(
                serialized_result=SerializedResult(serialized_result),
                cmk_command=cmk_command,
                cmdline_cmd=cmdline_cmd,
            )
        )

    def _execute_push_profile(self):
        try:
            response.set_data(str(watolib.mk_repr(self._automation_push_profile())))
        except Exception as e:
            logger.exception("error pushing profile")
            if active_config.debug:
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
        userdb.save_users(users, datetime.now())

        return True

    def _execute_automation_command(self, automation_command):
        try:
            # Don't use write_text() here (not needed, because no HTML document is rendered)
            automation = automation_command()
            response.set_data(repr(automation.execute(automation.get_request())))
        except Exception as e:
            logger.exception("error executing automation command")
            if active_config.debug:
                raise
            response.set_data(_("Internal automation error: %s\n%s") % (e, traceback.format_exc()))


def _set_version_headers() -> None:
    """Add the x-checkmk-version, x-checkmk-edition headers to the HTTP response

    Has been added with 2.0.0p13.
    """
    response.headers["x-checkmk-version"] = cmk_version.__version__
    response.headers["x-checkmk-edition"] = cmk_version.edition().short


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
