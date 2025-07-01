#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""These functions implement a web service with that a master can call
automation functions on slaves,"""

import secrets
import traceback
from collections.abc import Iterable
from contextlib import nullcontext
from datetime import datetime

import cmk.ccc.version as cmk_version
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site
from cmk.ccc.user import UserId

import cmk.utils.paths
from cmk.utils.local_secrets import DistributedSetupSecret
from cmk.utils.paths import configuration_lockfile

from cmk.automations.results import result_type_registry, SerializedResult

import cmk.gui.utils
import cmk.gui.watolib.utils as watolib_utils
from cmk.gui import userdb
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.pages import AjaxPage, PageEndpoint, PageRegistry, PageResult
from cmk.gui.session import SuperUserContext
from cmk.gui.watolib.automation_commands import automation_command_registry, AutomationCommand
from cmk.gui.watolib.automations import (
    check_mk_local_automation_serialized,
    cmk_version_of_remote_automation_source,
    get_local_automation_failure_message,
    LastKnownCentralSiteVersion,
    LastKnownCentralSiteVersionStore,
    MKAutomationException,
    verify_request_compatibility,
)
from cmk.gui.watolib.hosts_and_folders import collect_all_hosts

from cmk import trace
from cmk.crypto.password import Password

tracer = trace.get_tracer()


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("automation_login", PageAutomationLogin))
    page_registry.register(PageEndpoint("noauth:automation", PageAutomation))


def _store_central_site_info() -> None:
    central_version = request.headers.get("x-checkmk-version", request.get_ascii_input("_version"))

    if central_version is None:
        return

    try:
        LastKnownCentralSiteVersionStore().write_obj(
            LastKnownCentralSiteVersion(version_str=central_version)
        )
    except ValueError:
        # The call to _store_central_site_info is after the compatibility call, therefore we should
        # be fine
        logger.exception("Error writing central site info to disk")
        raise


class PageAutomationLogin(AjaxPage):
    """Is executed by the central Checkmk site to get the site secret of the remote site

    When the page method is execute a remote (central) site has successfully
    logged in using valid credentials of an administrative user. The login is
    done be exchanging a login secret. If such a secret is not yet present it
    is created on the fly."""

    # TODO: Better use AjaxPage.handle_page() for standard AJAX call error handling. This
    # would need larger refactoring of the generic html.popup_trigger() mechanism.
    def handle_page(self, config: Config) -> None:
        self._handle_exc(config, self.page)

    @tracer.instrument("PageAutomationLogin.page")
    def page(self, config: Config) -> PageResult:
        if not user.may("wato.automation"):
            raise MKAuthException(_("This account has no permission for automation."))

        response.set_content_type("text/plain")
        _set_version_headers()

        # Parameter was added with 1.5.0p10
        if not request.has_var("_version"):
            raise MKGeneralException(_("Your central site is incompatible with this remote site"))

        # allow login even with incompatible license, otherwise we cannot distribute license
        # information to make remote sites compatible
        verify_request_compatibility(ignore_license_compatibility=True)

        response.set_data(
            repr(
                {
                    "version": cmk_version.__version__,
                    "edition_short": cmk_version.edition(cmk.utils.paths.omd_root).short,
                    "login_secret": DistributedSetupSecret().read_or_create().raw,
                }
            )
        )
        return None


class PageAutomation(AjaxPage):
    """Executes the requested automation call

    This page is accessible without regular login. The request is authenticated using the given
    login secret that has previously been exchanged during "site login" (see above).
    """

    def _from_vars(self) -> None:
        self._authenticate()
        _set_version_headers()
        self._command = request.get_str_input_mandatory("command")
        # licensing information has to be distributed before checking for compatibility
        # to deal with remote sites in license state "free"
        verify_request_compatibility(
            ignore_license_compatibility=self._command == "distribute-verification-response"
        )
        _store_central_site_info()

    @staticmethod
    def _authenticate() -> None:
        secret = request.get_validated_type_input(Password, "secret")
        if not secret:
            raise MKAuthException(_("Missing secret for automation command."))

        if not DistributedSetupSecret().compare(secret):
            raise MKAuthException(_("Invalid automation secret."))

    # TODO: Better use AjaxPage.handle_page() for standard AJAX call error handling. This
    # would need larger refactoring of the generic html.popup_trigger() mechanism.
    def handle_page(self, config: Config) -> None:
        # The automation page is accessed unauthenticated. After leaving the index.py area
        # into the page handler we always want to have a user context initialized to keep
        # the code free from special cases (if no user logged in, then...). So fake the
        # logged in user here.
        with SuperUserContext():
            self._handle_exc(config, self.page)

    @tracer.instrument("PageAutomation.page")
    def page(self, config: Config) -> PageResult:
        # To prevent mixups in written files we use the same lock here as for
        # the normal Setup page processing. This might not be needed for some
        # special automation requests, like inventory e.g., but to keep it simple,
        # we request the lock in all cases.
        lock_config = not (
            self._command == "checkmk-automation"
            and request.get_str_input_mandatory("automation") == "active-check"
        )
        with (
            store.lock_checkmk_configuration(configuration_lockfile)
            if lock_config
            else nullcontext()
        ):
            self._execute_automation(debug=config.debug)
        return None

    def _execute_automation(self, *, debug: bool) -> None:
        with tracer.span(f"_execute_automation[{self._command}]"):
            # TODO: Refactor these two calls to also use the automation_command_registry
            if self._command == "checkmk-automation":
                self._execute_cmk_automation(debug=debug)
                return
            if self._command == "push-profile":
                self._execute_push_profile(debug=debug)
                return
            try:
                automation_command = automation_command_registry[self._command]
            except KeyError:
                raise MKGeneralException(_("Invalid automation command: %s.") % self._command)
            self._execute_automation_command(automation_command, debug=debug)

    @staticmethod
    def _format_cmk_automation_result(
        *,
        serialized_result: SerializedResult,
        cmk_command: str,
        cmdline_cmd: Iterable[str],
        debug: bool,
    ) -> SerializedResult:
        try:
            return (
                result_type_registry[cmk_command]
                .deserialize(serialized_result)
                .serialize(cmk_version_of_remote_automation_source(request))
            )
        except SyntaxError as e:
            msg = get_local_automation_failure_message(
                command=cmk_command,
                cmdline=cmdline_cmd,
                out=serialized_result,
                exc=e,
                debug=debug,
            )
            raise MKAutomationException(msg)

    def _execute_cmk_automation(self, *, debug: bool) -> None:
        cmk_command = request.get_str_input_mandatory("automation")
        args = watolib_utils.mk_eval(request.get_str_input_mandatory("arguments"))
        indata = watolib_utils.mk_eval(request.get_str_input_mandatory("indata"))
        stdin_data = watolib_utils.mk_eval(request.get_str_input_mandatory("stdin_data"))
        timeout = watolib_utils.mk_eval(request.get_str_input_mandatory("timeout"))
        cmdline_cmd, serialized_result = check_mk_local_automation_serialized(
            command=cmk_command,
            args=args,
            indata=indata,
            stdin_data=stdin_data,
            timeout=timeout,
            debug=debug,
            collect_all_hosts=collect_all_hosts,
        )
        # Don't use write_text() here (not needed, because no HTML document is rendered)
        response.set_data(
            self._format_cmk_automation_result(
                serialized_result=SerializedResult(serialized_result),
                cmk_command=cmk_command,
                cmdline_cmd=cmdline_cmd,
                debug=debug,
            )
        )

    def _execute_push_profile(self, *, debug: bool) -> None:
        try:
            response.set_data(str(watolib_utils.mk_repr(self._automation_push_profile())))
        except Exception as e:
            logger.exception("error pushing profile")
            if debug:
                raise
            response.set_data(_("Internal automation error: %s\n%s") % (e, traceback.format_exc()))

    def _automation_push_profile(self) -> bool:
        site_id = request.var("siteid")
        if not site_id:
            raise MKGeneralException(_("Missing variable siteid"))

        user_id = request.get_validated_type_input(UserId, "user_id")
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
        users[user_id] = watolib_utils.mk_eval(profile)
        userdb.save_users(users, datetime.now())

        return True

    def _execute_automation_command(
        self, automation_command: type[AutomationCommand], *, debug: bool
    ) -> None:
        try:
            # Don't use write_text() here (not needed, because no HTML document is rendered)
            automation = automation_command()
            response.set_data(repr(automation.execute(automation.get_request())))
        except Exception as e:
            logger.exception("error executing automation command")
            if debug:
                raise
            response.set_data(_("Internal automation error: %s\n%s") % (e, traceback.format_exc()))


def _set_version_headers() -> None:
    """Add the x-checkmk-version, x-checkmk-edition headers to the HTTP response

    Has been added with 2.0.0p13.
    """
    response.headers["x-checkmk-version"] = cmk_version.__version__
    response.headers["x-checkmk-edition"] = cmk_version.edition(cmk.utils.paths.omd_root).short


def _get_login_secret(create_on_demand: bool = False) -> str | None:
    path = cmk.utils.paths.var_dir / "wato/automation_secret.mk"

    secret = store.load_object_from_file(path, default=None)
    if secret is not None:
        return secret

    if not create_on_demand:
        return None

    # Note: This will make a secret and base64 encode it, so we'll end up with 43 chars for our
    #       32 bytes. It would be better to store the raw secret bytes and encode when needed.
    secret = secrets.token_urlsafe(32)
    store.save_object_to_file(path, secret)
    return secret
