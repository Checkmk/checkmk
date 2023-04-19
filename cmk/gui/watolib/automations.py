#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This code section deals with the interaction of Checkmk base code. It is
used for doing inventory, showing the services of a host, deletion of a host
and similar things."""

from __future__ import annotations

import ast
import logging
import re
import subprocess
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from io import BytesIO
from pathlib import Path
from typing import NamedTuple

import requests
import urllib3

from livestatus import SiteConfiguration, SiteId

import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.licensing.handler import LicenseState
from cmk.utils.licensing.registry import get_license_state
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import PhaseOneResult, UserId

from cmk.automations.results import result_type_registry, SerializedResult

import cmk.gui.hooks as hooks
import cmk.gui.utils.escaping as escaping
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    job_registry,
    JobStatusSpec,
)
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.site_config import get_site_config
from cmk.gui.utils.urls import urlencode_vars
from cmk.gui.watolib.automation_commands import automation_command_registry, AutomationCommand
from cmk.gui.watolib.utils import mk_repr

auto_logger = logger.getChild("automations")

# Disable python warnings in background job output or logs like "Unverified
# HTTPS request is being made". We warn the user using analyze configuration.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MKAutomationException(MKGeneralException):
    pass


def cmk_version_of_remote_automation_source() -> cmk_version.Version:
    # The header is sent by Checkmk as of 2.0.0p1. In case it is missing, assume we are too old.
    return cmk_version.Version(request.headers.get("x-checkmk-version", "1.6.0p1"))


def check_mk_local_automation_serialized(
    *,
    command: str,
    args: Sequence[str] | None = None,
    indata: object = "",
    stdin_data: str | None = None,
    timeout: int | None = None,
) -> tuple[Sequence[str], SerializedResult]:
    if args is None:
        args = []
    new_args = list(args)

    if stdin_data is None:
        stdin_data = repr(indata)

    if timeout:
        new_args = ["--timeout", "%d" % timeout] + new_args

    cmd = ["check_mk"]

    if auto_logger.isEnabledFor(logging.DEBUG):
        cmd.append("-vv")
    elif auto_logger.isEnabledFor(VERBOSE):
        cmd.append("-v")

    cmd += ["--automation", command] + new_args

    if command in ["restart", "reload"]:
        call_hook_pre_activate_changes()

    # This debug output makes problems when doing bulk inventory, because
    # it garbles the non-HTML response output
    # if config.debug:
    #     html.write_text("<div class=message>Running <tt>%s</tt></div>\n" % subprocess.list2cmdline(cmd))
    auto_logger.info("RUN: %s" % subprocess.list2cmdline(cmd))
    auto_logger.info("STDIN: %r" % stdin_data)

    try:
        completed_process = subprocess.run(
            cmd,
            capture_output=True,
            close_fds=True,
            encoding="utf-8",
            input=stdin_data,
            check=False,
        )
    except Exception as e:
        raise local_automation_failure(command=command, cmdline=cmd, exc=e)

    auto_logger.info("FINISHED: %d" % completed_process.returncode)
    auto_logger.debug("OUTPUT: %r" % completed_process.stdout)

    if completed_process.stderr:
        auto_logger.warning(
            "'%s' returned '%s'"
            % (
                " ".join(cmd),
                completed_process.stderr,
            )
        )
    if completed_process.returncode:
        auto_logger.error(
            "Error running %r (exit code %d)"
            % (
                subprocess.list2cmdline(cmd),
                completed_process.returncode,
            )
        )
        raise local_automation_failure(
            command=command,
            cmdline=cmd,
            code=completed_process.returncode,
            out=completed_process.stdout,
            err=completed_process.stderr,
        )

    # On successful "restart" command execute the activate changes hook
    if command in ["restart", "reload"]:
        call_hook_activate_changes()

    return cmd, SerializedResult(completed_process.stdout)


def local_automation_failure(
    command: str,
    cmdline: Iterable[str],
    code: int | None = None,
    out: str | None = None,
    err: str | None = None,
    exc: Exception | None = None,
) -> MKGeneralException:
    call = subprocess.list2cmdline(cmdline) if active_config.debug else command
    msg = "Error running automation call <tt>%s</tt>" % call
    if code:
        msg += " (exit code %d)" % code
    if out:
        msg += ", output: <pre>%s</pre>" % _hilite_errors(out)
    if err:
        msg += ", error: <pre>%s</pre>" % _hilite_errors(err)
    if exc:
        msg += ": %s" % exc
    return MKGeneralException(msg)


def _hilite_errors(outdata: str) -> str:
    return re.sub("\nError: *([^\n]*)", "\n<div class=err><b>Error:</b> \\1</div>", outdata)


def check_mk_remote_automation_serialized(
    *,
    site_id: SiteId,
    command: str,
    args: Sequence[str] | None,
    indata: object,
    stdin_data: str | None = None,
    timeout: int | None = None,
    sync: Callable[[SiteId], None],
    non_blocking_http: bool = False,
) -> SerializedResult:
    site = get_site_config(site_id)
    if "secret" not in site:
        raise MKGeneralException(
            _('Cannot connect to site "%s": The site is not logged in') % site.get("alias", site_id)
        )

    if not site.get("replication"):
        raise MKGeneralException(
            _('Cannot connect to site "%s": The replication is disabled')
            % site.get("alias", site_id)
        )

    sync(site_id)

    if non_blocking_http:
        # This will start a background job process on the remote site to execute the automation
        # asynchronously. It then polls the remote site, waiting for completion of the job.
        return _do_check_mk_remote_automation_in_background_job_serialized(
            site_id, CheckmkAutomationRequest(command, args, indata, stdin_data, timeout)
        )

    # Synchronous execution of the actual remote command in a single blocking HTTP request
    return SerializedResult(
        _do_remote_automation_serialized(
            site=get_site_config(site_id),
            command="checkmk-automation",
            vars_=[
                ("automation", command),  # The Checkmk automation command
                ("arguments", mk_repr(args).decode("ascii")),  # The arguments for the command
                ("indata", mk_repr(indata).decode("ascii")),  # The input data
                ("stdin_data", mk_repr(stdin_data).decode("ascii")),  # The input data for stdin
                ("timeout", mk_repr(timeout).decode("ascii")),  # The timeout
            ],
        )
    )


# This hook is executed when one applies the pending configuration changes
# from wato but BEFORE the nagios restart is executed.
#
# It can be used to create custom input files for nagios/Checkmk.
#
# The registered hooks are called with a dictionary as parameter which
# holds all available with the hostnames as keys and the attributes of
# the hosts as values.
def call_hook_pre_activate_changes() -> None:
    if hooks.registered("pre-activate-changes"):
        # TODO: Cleanup this local import
        import cmk.gui.watolib.hosts_and_folders  # pylint: disable=redefined-outer-name

        hooks.call("pre-activate-changes", cmk.gui.watolib.hosts_and_folders.collect_all_hosts())


# This hook is executed when one applies the pending configuration changes
# from wato.
#
# But it is only excecuted when there is at least one function
# registered for this host.
#
# The registered hooks are called with a dictionary as parameter which
# holds all available with the hostnames as keys and the attributes of
# the hosts as values.
def call_hook_activate_changes() -> None:
    if hooks.registered("activate-changes"):
        # TODO: Cleanup this local import
        import cmk.gui.watolib.hosts_and_folders  # pylint: disable=redefined-outer-name

        hooks.call("activate-changes", cmk.gui.watolib.hosts_and_folders.collect_all_hosts())


def _do_remote_automation_serialized(
    *,
    site: SiteConfiguration,
    command: str,
    vars_: Sequence[tuple[str, str]],
    files: Mapping[str, BytesIO] | None = None,
    timeout: float | None = None,
) -> str:
    auto_logger.info("RUN [%s]: %s", site, command)
    auto_logger.debug("VARS: %r", vars_)

    base_url = site["multisiteurl"]
    secret = site.get("secret")
    if not secret:
        raise MKAutomationException(_("You are not logged into the remote site."))

    url = base_url + "automation.py?" + urlencode_vars([("command", command)])

    post_data = dict(vars_)
    post_data.update(
        {
            "secret": secret,
            "debug": "1" if active_config.debug else "",
        }
    )

    response = get_url(
        url, site.get("insecure", False), data=post_data, files=files, timeout=timeout
    )

    auto_logger.debug("RESPONSE: %r", response)

    if not response:
        raise MKAutomationException(_("Empty output from remote site."))

    return response


def execute_phase1_result(site_id: SiteId, connection_id: str) -> PhaseOneResult:
    command_args = [
        ("request_format", "python"),
        (
            "request",
            repr({"action": "get_phase1_result", "kwargs": {"connection_id": connection_id}}),
        ),
    ]
    return ast.literal_eval(
        str(
            do_remote_automation(
                site=get_site_config(site_id), command="execute-dcd-command", vars_=command_args
            )
        )
    )


def do_remote_automation(
    site: SiteConfiguration,
    command: str,
    vars_: Sequence[tuple[str, str]],
    files: Mapping[str, BytesIO] | None = None,
    timeout: float | None = None,
) -> object:
    serialized_response = _do_remote_automation_serialized(
        site=site,
        command=command,
        vars_=vars_,
        files=files,
        timeout=timeout,
    )
    try:
        return ast.literal_eval(serialized_response)
    except SyntaxError:
        # The remote site will send non-Python data in case of an error.
        raise MKAutomationException(
            "%s: <pre>%s</pre>"
            % (
                _("Got invalid data"),
                serialized_response,
            )
        )


def get_url_raw(
    url: str,
    insecure: bool,
    auth: tuple[str, str] | None = None,
    data: Mapping[str, str] | None = None,
    files: Mapping[str, BytesIO] | None = None,
    timeout: float | None = None,
) -> requests.Response:
    response = requests.post(
        url,
        data=data,
        verify=not insecure,
        auth=auth,
        files=files,
        timeout=timeout,
        headers={
            "x-checkmk-version": cmk_version.__version__,
            "x-checkmk-edition": cmk_version.edition().short,
            "x-checkmk-license-state": get_license_state().readable,
        },
    )

    response.encoding = "utf-8"  # Always decode with utf-8

    if response.status_code == 401:
        raise MKUserError("_passwd", _("Authentication failed. Invalid login/password."))

    if response.status_code == 503 and "Site Not Started" in response.text:
        raise MKUserError(None, _("Site is not running"))

    if response.status_code != 200:
        raise MKUserError(None, _("HTTP Error - %d: %s") % (response.status_code, response.text))

    _verify_compatibility(response)

    return response


def _verify_compatibility(response: requests.Response) -> None:
    """Ensure we are compatible with the remote site

    In distributed setups the sync from a newer major version central site to an older central site
    is not allowed. Since 2.1.0 the remote site is performing most of the validations. But in case
    the newer site is the central site and the remote site is the older, e.g. 2.1.0 to 2.0.0, there
    is no validation logic on the remote site. To ensure the validation is also performed in this
    case, we execute the validation logic also in the central site when receiving the answer to the
    remote call before processing it's content.

    Since 2.0.0p13 the remote site answers with x-checkmk-version, x-checkmk-edition headers.
    """
    central_version = cmk_version.__version__
    central_edition_short = cmk_version.edition().short

    remote_version = response.headers.get("x-checkmk-version", "")
    remote_edition_short = response.headers.get("x-checkmk-edition", "")
    remote_license_state = parse_license_state(response.headers.get("x-checkmk-license-state", ""))

    if not remote_version or not remote_edition_short:
        return  # No validation

    if not isinstance(
        compatibility := compatible_with_central_site(
            central_version,
            central_edition_short,
            remote_version,
            remote_edition_short,
            remote_license_state,
        ),
        cmk_version.VersionsCompatible,
    ):
        raise MKGeneralException(
            make_incompatible_info(
                central_version,
                central_edition_short,
                remote_version,
                remote_edition_short,
                remote_license_state,
                compatibility,
            )
        )


def parse_license_state(raw_license_state: str) -> LicenseState | None:
    try:
        return LicenseState[raw_license_state]
    except KeyError:
        return None


def make_incompatible_info(
    central_version: str,
    central_edition_short: str,
    remote_version: str,
    remote_edition_short: str,
    remote_license_state: LicenseState | None,
    compatibility: (
        cmk_version.VersionsIncompatible | EditionsIncompatible | LicenseStateIncompatible
    ),
) -> str:
    return _("The central (%s) and remote site (%s) are not compatible. Reason: %s") % (
        _make_central_site_version_info(central_version, central_edition_short),
        make_remote_site_version_info(remote_version, remote_edition_short, remote_license_state),
        compatibility,
    )


def _make_central_site_version_info(
    central_version: str,
    central_edition_short: str,
) -> str:
    return _("Version: %s, Edition: %s") % (central_version, central_edition_short)


def make_remote_site_version_info(
    remote_version: str,
    remote_edition_short: str,
    remote_license_state: LicenseState | None,
) -> str:
    return _("Version: %s, Edition: %s, License state: %s") % (
        remote_version,
        remote_edition_short,
        remote_license_state.readable if remote_license_state else _("unknown"),
    )


def get_url(
    url: str,
    insecure: bool,
    auth: tuple[str, str] | None = None,
    data: Mapping[str, str] | None = None,
    files: Mapping[str, BytesIO] | None = None,
    timeout: float | None = None,
) -> str:
    return get_url_raw(url, insecure, auth, data, files, timeout).text


def get_url_json(
    url: str,
    insecure: bool,
    auth: tuple[str, str] | None = None,
    data: Mapping[str, str] | None = None,
    files: Mapping[str, BytesIO] | None = None,
    timeout: float | None = None,
) -> object:
    return get_url_raw(url, insecure, auth, data, files, timeout).json()


def do_site_login(site: SiteConfiguration, name: UserId, password: str) -> str:
    if not name:
        raise MKUserError("_name", _("Please specify your administrator login on the remote site."))
    if not password:
        raise MKUserError("_passwd", _("Please specify your password."))

    # Trying basic auth AND form based auth to ensure the site login works.
    # Adding _ajaxid makes the web service fail silently with an HTTP code and
    # not output HTML code for an error screen.
    url = site["multisiteurl"] + "login.py"
    post_data = {
        "_login": "1",
        "_username": name,
        "_password": password,
        "_origtarget": "automation_login.py?_version=%s&_edition_short=%s"
        % (cmk_version.__version__, cmk_version.edition().short),
        "_plain_error": "1",
    }
    response = get_url(
        url, site.get("insecure", False), auth=(name, password), data=post_data
    ).strip()
    if "<html>" in response.lower():
        message = _(
            "Authentication to web service failed.<br>Message:<br>%s"
        ) % escaping.strip_tags(escaping.strip_scripts(response))
        if active_config.debug:
            message += "<br>" + _("Automation URL:") + " <tt>%s</tt><br>" % url
        raise MKAutomationException(message)
    if not response:
        raise MKAutomationException(_("Empty response from web service"))
    try:
        eval_response = ast.literal_eval(response)
    except SyntaxError:
        raise MKAutomationException(response)
    if isinstance(eval_response, dict):
        if cmk_version.is_managed_edition() and eval_response["edition_short"] != "cme":
            raise MKUserError(
                None,
                _(
                    "The Checkmk Managed Services Edition can only "
                    "be connected with other sites using the CME."
                ),
            )
        return eval_response["login_secret"]
    return eval_response


class CheckmkAutomationRequest(NamedTuple):
    command: str
    args: Sequence[str] | None
    indata: object
    stdin_data: str | None
    timeout: int | None


RemoteAutomationGetStatusResponseRaw = tuple[dict[str, object], str]


class CheckmkAutomationGetStatusResponse(NamedTuple):
    job_status: JobStatusSpec
    result: str


# There are already at least two custom background jobs that are wrapping remote automation
# calls but have been implemented individually. Does it make sense to refactor them to use this?
# - Service discovery of a single host (cmk.gui.wato.pages.services._get_check_table)
# - Fetch agent / SNMP output (cmk.gui.wato.pages.fetch_agent_output.FetchAgentOutputBackgroundJob)
def _do_check_mk_remote_automation_in_background_job_serialized(
    site_id: SiteId, automation_request: CheckmkAutomationRequest
) -> SerializedResult:
    """Execute the automation in a background job on the remote site

    It starts the background job using one call. It then polls the remote site, waiting for
    completion of the job."""
    site_config = get_site_config(site_id)

    job_id = _start_remote_automation_job(site_config, automation_request)

    auto_logger.info("Waiting for job completion")
    result = None
    while True:
        raw_response = do_remote_automation(
            site_config,
            "checkmk-remote-automation-get-status",
            [
                ("request", repr(job_id)),
            ],
        )
        assert isinstance(raw_response, tuple)
        response = CheckmkAutomationGetStatusResponse(
            JobStatusSpec.parse_obj(raw_response[0]),
            raw_response[1],
        )
        auto_logger.debug("Job status: %r", response)

        if not response.job_status.is_active:
            result = response.result
            auto_logger.debug("Job is not active anymore. Return the result: %s", result)
            break

    assert isinstance(result, str)

    return SerializedResult(result)


def _start_remote_automation_job(
    site_config: SiteConfiguration, automation_request: CheckmkAutomationRequest
) -> str:
    auto_logger.info("Starting remote automation in background job")
    job_id = str(
        do_remote_automation(
            site_config,
            "checkmk-remote-automation-start",
            [
                ("request", repr(tuple(automation_request))),
            ],
        )
    )

    auto_logger.info("Started background job: %s", job_id)
    return job_id


@automation_command_registry.register
class AutomationCheckmkAutomationStart(AutomationCommand):
    """Called by do_remote_automation_in_background_job to execute the background job on a remote site"""

    def command_name(self) -> str:
        return "checkmk-remote-automation-start"

    def get_request(self) -> CheckmkAutomationRequest:
        return CheckmkAutomationRequest(
            *ast.literal_eval(request.get_ascii_input_mandatory("request"))
        )

    def execute(self, api_request: CheckmkAutomationRequest) -> str:
        job = CheckmkAutomationBackgroundJob(api_request=api_request)
        job.start(lambda job_interface: job.execute_automation(job_interface, api_request))
        return job.get_job_id()


@automation_command_registry.register
class AutomationCheckmkAutomationGetStatus(AutomationCommand):
    """Called by do_remote_automation_in_background_job to get the background job state from on a
    remote site"""

    def command_name(self) -> str:
        return "checkmk-remote-automation-get-status"

    def get_request(self) -> str:
        return ast.literal_eval(request.get_ascii_input_mandatory("request"))

    @staticmethod
    def _load_result(path: Path) -> str:
        return store.load_text_from_file(path)

    def execute(self, api_request: str) -> RemoteAutomationGetStatusResponseRaw:
        job_id = api_request
        job = CheckmkAutomationBackgroundJob(job_id)
        response = CheckmkAutomationGetStatusResponse(
            job_status=job.get_status_snapshot().status,
            result=self._load_result(Path(job.get_work_dir()) / "result.mk"),
        )
        return dict(response[0]), response[1]


@job_registry.register
class CheckmkAutomationBackgroundJob(BackgroundJob):
    """The background job is always executed on the site where the host is located on"""

    job_prefix = "automation-"

    @classmethod
    def gui_title(cls) -> str:
        return _("Checkmk automation")

    def __init__(
        self, job_id: str | None = None, api_request: CheckmkAutomationRequest | None = None
    ) -> None:
        if job_id is not None:
            # Loading an existing job
            super().__init__(job_id=job_id)
            return

        assert api_request is not None

        # A new job is started
        automation_id = str(uuid.uuid4())
        super().__init__(
            f"{self.job_prefix}{api_request.command}-{automation_id}",
            InitialStatusArgs(
                title=_("Checkmk automation %s %s") % (api_request.command, automation_id),
            ),
        )

    @staticmethod
    def _store_result(
        *,
        path: Path,
        serialized_result: SerializedResult,
        automation_cmd: str,
        cmdline_cmd: Iterable[str],
    ) -> None:
        try:
            store.save_text_to_file(
                path,
                result_type_registry[automation_cmd]
                .deserialize(serialized_result)
                .serialize(cmk_version_of_remote_automation_source()),
            )
        except SyntaxError as e:
            raise local_automation_failure(
                command=automation_cmd,
                cmdline=cmdline_cmd,
                out=serialized_result,
                exc=e,
            )

    def execute_automation(
        self,
        job_interface: BackgroundProcessInterface,
        api_request: CheckmkAutomationRequest,
    ) -> None:
        self._logger.info("Starting automation: %s", api_request.command)
        self._logger.debug(api_request)
        cmdline_cmd, serialized_result = check_mk_local_automation_serialized(
            command=api_request.command,
            args=api_request.args,
            indata=api_request.indata,
            stdin_data=api_request.stdin_data,
            timeout=api_request.timeout,
        )
        # This file will be read by the get-status request
        self._store_result(
            path=Path(job_interface.get_work_dir()) / "result.mk",
            serialized_result=serialized_result,
            automation_cmd=api_request.command,
            cmdline_cmd=cmdline_cmd,
        )
        job_interface.send_result_message(_("Finished."))


class LicenseStateIncompatible:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    def __str__(self) -> str:
        return self._reason


class EditionsIncompatible:
    def __init__(self, reason: str) -> None:
        self._reason = reason

    def __str__(self) -> str:
        return self._reason


def compatible_with_central_site(
    central_version: str,
    central_edition_short: str,
    remote_version: str,
    remote_edition_short: str,
    remote_license_state: LicenseState | None,
) -> (
    cmk_version.VersionsCompatible
    | cmk_version.VersionsIncompatible
    | EditionsIncompatible
    | LicenseStateIncompatible
):
    """Whether or not a remote site version and edition is compatible with the central site

    The version check is handled by the version utils, the edition check is handled here.

    >>> c = compatible_with_central_site

    C*E != CME is not allowed

    >>> str(c("2.2.0p1", "cce", "2.2.0p1", "cce", LicenseState.FREE))
    'Remote site in license state free is not allowed'
    >>> str(c("2.0.0p3", "cee", "2.0.0p3", "cme", LicenseState.LICENSED))
    'Mix of CME and non-CME is not supported.'
    >>> str(c("2.0.0p3", "cme", "2.0.0p3", "cee", LicenseState.LICENSED))
    'Mix of CME and non-CME is not supported.'
    >>> str(c("2.0.0p3", "cre", "2.0.0p3", "cme", LicenseState.LICENSED))
    'Mix of CME and non-CME is not supported.'
    >>> str(c("2.0.0p3", "cme", "2.0.0p3", "cre", LicenseState.LICENSED))
    'Mix of CME and non-CME is not supported.'
    >>> isinstance(c("2.0.0p3", "cme", "2.0.0p3", "cme", LicenseState.LICENSED), cmk_version.VersionsCompatible)
    True
    """
    if remote_license_state is LicenseState.FREE:
        return LicenseStateIncompatible(
            "Remote site in license state %s is not allowed" % remote_license_state.readable
        )

    # Pre 2.0.0p1 did not sent x-checkmk-* headers -> Not compabile
    if not all(
        (
            central_edition_short,
            central_version,
            remote_edition_short,
            remote_version,
        )
    ):
        return cmk_version.VersionsIncompatible("Central or remote site are below 2.0.0p1.")

    if (central_edition_short == "cme") is not (remote_edition_short == "cme"):
        return EditionsIncompatible("Mix of CME and non-CME is not supported.")

    return cmk_version.versions_compatible(
        cmk_version.Version(central_version),
        cmk_version.Version(remote_version),
    )
