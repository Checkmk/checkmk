#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This code section deals with the interaction of Check_MK base code. It is
used for doing inventory, showing the services of a host, deletion of a host
and similar things."""

import ast
import logging
import re
import subprocess
import uuid
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Literal,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
)

import requests
import urllib3  # type: ignore[import]

from livestatus import SiteConfiguration, SiteId

import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import UserId
from cmk.utils.version import base_version_parts, is_daily_build_of_master, parse_check_mk_version

from cmk.automations.results import result_type_registry, SerializedResult

import cmk.gui.gui_background_job as gui_background_job
import cmk.gui.hooks as hooks
import cmk.gui.utils.escaping as escaping
from cmk.gui.background_job import BackgroundProcessInterface
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKGeneralException, MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.site_config import get_site_config
from cmk.gui.utils.urls import urlencode_vars
from cmk.gui.watolib.automation_commands import automation_command_registry, AutomationCommand
from cmk.gui.watolib.utils import mk_repr
from cmk.gui.watolib.wato_background_job import WatoBackgroundJob

auto_logger = logger.getChild("automations")

# Disable python warnings in background job output or logs like "Unverified
# HTTPS request is being made". We warn the user using analyze configuration.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MKAutomationException(MKGeneralException):
    pass


def remote_automation_call_came_from_pre21() -> bool:
    # The header is sent by Checkmk as of 2.0.0p1. In case it is missing, assume we are too old.
    if not (remote_version := request.headers.get("x-checkmk-version")):
        return True
    return parse_check_mk_version(remote_version) < parse_check_mk_version("2.1.0i1")


def check_mk_local_automation_serialized(
    *,
    command: str,
    args: Optional[Sequence[str]] = None,
    indata: Any = "",
    stdin_data: Optional[str] = None,
    timeout: Optional[int] = None,
) -> Tuple[Sequence[str], SerializedResult]:
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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
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
    command,
    cmdline,
    code=None,
    out=None,
    err=None,
    exc=None,
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


def _hilite_errors(outdata):
    return re.sub("\nError: *([^\n]*)", "\n<div class=err><b>Error:</b> \\1</div>", outdata)


def check_mk_remote_automation_serialized(
    *,
    site_id: SiteId,
    command: str,
    args: Optional[Sequence[str]],
    indata: Any,
    stdin_data: Optional[str] = None,
    timeout: Optional[int] = None,
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
                ("arguments", mk_repr(args)),  # The arguments for the command
                ("indata", mk_repr(indata)),  # The input data
                ("stdin_data", mk_repr(stdin_data)),  # The input data for stdin
                ("timeout", mk_repr(timeout)),  # The timeout
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
def call_hook_pre_activate_changes():
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
def call_hook_activate_changes():
    if hooks.registered("activate-changes"):
        # TODO: Cleanup this local import
        import cmk.gui.watolib.hosts_and_folders  # pylint: disable=redefined-outer-name

        hooks.call("activate-changes", cmk.gui.watolib.hosts_and_folders.collect_all_hosts())


def _do_remote_automation_serialized(
    *,
    site,
    command,
    vars_,
    files=None,
    timeout=None,
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


class PiggybackHostsConnectorAttributes(TypedDict):
    hosts: Sequence[str]
    tmpfs_initialization_time: int


class ExecutionStepAttributes(TypedDict):
    _name: str
    _title: str
    _time_initialized: float
    _time_started: float
    _time_completed: float
    _log_entries: Sequence[str]
    phase: Literal[0, 1, 2]
    status: Literal[0, 1]
    message: str


class ExecutionStep(TypedDict):
    class_name: Literal["ExecutionStep"]
    attributes: ExecutionStepAttributes


class ExecutionStatusAttributes(TypedDict):
    _steps: Sequence[ExecutionStep]
    _finished: bool
    _time_initialized: float
    _time_completed: float


class ExecutionStatus(TypedDict):
    class_name: Literal["ExecutionStatus"]
    attributes: ExecutionStatusAttributes


class ConnectorObject(TypedDict):
    # Literal["PiggybackHosts"]
    class_name: str  # TODO: replace str type with Literal
    # attributes of new connector objects should be listed here
    attributes: Union[PiggybackHostsConnectorAttributes, dict]


class PhaseOneAttributes(TypedDict):
    connector_object: ConnectorObject
    status: ExecutionStatus


class PhaseOneResult(TypedDict):
    class_name: Literal["Phase1Result"]
    attributes: PhaseOneAttributes


def execute_phase1_result(site_id: SiteId, connection_id: str) -> PhaseOneResult:
    command_args = {
        "request_format": "python",
        "request": repr(
            {"action": "get_phase1_result", "kwargs": {"connection_id": connection_id}}
        ),
    }
    return do_remote_automation(
        site=get_site_config(site_id), command="execute-dcd-command", vars_=command_args
    )


def do_remote_automation(site, command, vars_, files=None, timeout=None) -> Any:
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


def get_url_raw(url, insecure, auth=None, data=None, files=None, timeout=None):
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

    if not remote_version or not remote_edition_short:
        return  # No validation

    if not compatible_with_central_site(
        central_version, central_edition_short, remote_version, remote_edition_short
    ):
        raise MKGeneralException(
            _(
                "The central (Version: %s, Edition: %s) and remote site "
                "(Version: %s, Edition: %s) are not compatible"
            )
            % (
                central_version,
                central_edition_short,
                remote_version,
                remote_edition_short,
            )
        )


def get_url(url, insecure, auth=None, data=None, files=None, timeout=None):
    return get_url_raw(url, insecure, auth, data, files, timeout).text


def get_url_json(url, insecure, auth=None, data=None, files=None, timeout=None):
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
                    "The Check_MK Managed Services Edition can only "
                    "be connected with other sites using the CME."
                ),
            )
        return eval_response["login_secret"]
    return eval_response


class CheckmkAutomationRequest(NamedTuple):
    command: str
    args: Optional[Sequence[str]]
    indata: Any
    stdin_data: Optional[str]
    timeout: Optional[int]


class CheckmkAutomationGetStatusResponse(NamedTuple):
    job_status: Dict[str, Any]
    # object occurs in case of a remote automation call from a pre-2.1 central site
    result: Union[object, str]


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
        response = CheckmkAutomationGetStatusResponse(*raw_response)
        auto_logger.debug("Job status: %r", response)

        if not response.job_status["is_active"]:
            result = response.result
            auto_logger.debug("Job is not active anymore. Return the result: %s", result)
            break

    assert isinstance(result, str)

    return SerializedResult(result)


def _start_remote_automation_job(
    site_config: SiteConfiguration, automation_request: CheckmkAutomationRequest
) -> str:
    auto_logger.info("Starting remote automation in background job")
    job_id = do_remote_automation(
        site_config,
        "checkmk-remote-automation-start",
        [
            ("request", repr(tuple(automation_request))),
        ],
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

    def execute(self, api_request: CheckmkAutomationRequest) -> Tuple:
        job = CheckmkAutomationBackgroundJob(api_request=api_request)
        job.set_function(job.execute_automation, api_request=api_request)
        job.start()
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
    def _load_result(path: Path) -> Union[str, object]:
        if remote_automation_call_came_from_pre21():
            return store.load_object_from_file(path, default=None)
        return store.load_text_from_file(path)

    def execute(self, api_request: str) -> Tuple:
        job_id = api_request
        job = CheckmkAutomationBackgroundJob(job_id)
        return tuple(
            CheckmkAutomationGetStatusResponse(
                job_status=job.get_status_snapshot().get_status_as_dict()[job.get_job_id()],
                result=self._load_result(Path(job.get_work_dir()) / "result.mk"),
            )
        )


@gui_background_job.job_registry.register
class CheckmkAutomationBackgroundJob(WatoBackgroundJob):
    """The background job is always executed on the site where the host is located on"""

    job_prefix = "automation-"

    @classmethod
    def gui_title(cls) -> str:
        return _("Checkmk automation")

    def __init__(
        self, job_id: Optional[str] = None, api_request: Optional[CheckmkAutomationRequest] = None
    ) -> None:
        if job_id is not None:
            # Loading an existing job
            super().__init__(job_id=job_id)
            return

        assert api_request is not None

        # A new job is started
        automation_id = str(uuid.uuid4())
        super().__init__(
            job_id="%s%s-%s" % (self.job_prefix, api_request.command, automation_id),
            title=_("Checkmk automation %s %s") % (api_request.command, automation_id),
        )

    @staticmethod
    def _store_result(
        *,
        path: Path,
        serialized_result: SerializedResult,
        automation_cmd: str,
        cmdline_cmd: Iterable[str],
    ) -> None:
        if remote_automation_call_came_from_pre21():
            try:
                store.save_object_to_file(
                    path,
                    result_type_registry[automation_cmd].deserialize(serialized_result).to_pre_21(),
                )
            except SyntaxError as e:
                raise local_automation_failure(
                    command=automation_cmd,
                    cmdline=cmdline_cmd,
                    out=serialized_result,
                    exc=e,
                )
        else:
            store.save_text_to_file(
                path,
                serialized_result,
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


def compatible_with_central_site(
    central_version: str, central_edition_short: str, remote_version: str, remote_edition_short: str
) -> bool:
    """Whether or not a remote site version and edition is compatible with the central site

    >>> c = compatible_with_central_site

    Nightly build of master branch is always compatible as we don't know which major version it
    belongs to. It's also not that important to validate this case.

    >>> c("2.0.0i1", "cee", "2021.12.13", "cee")
    True
    >>> c("2021.12.13", "cee", "2.0.0i1", "cee")
    True
    >>> c("2021.12.13", "cee", "2022.01.01", "cee")
    True
    >>> c("2022.01.01", "cee", "2021.12.13", "cee")
    True

    Nightly branch builds e.g. 2.0.0-2022.01.01 are treated as 2.0.0.

    >>> c("2.0.0-2022.01.01", "cee", "2.0.0p3", "cee")
    True
    >>> c("2.0.0p3", "cee", "2.0.0-2022.01.01", "cee")
    True

    Same major is allowed

    >>> c("2.0.0i1", "cee", "2.0.0p3", "cee")
    True
    >>> c("2.0.0p3", "cee", "2.0.0i1", "cee")
    True
    >>> c("2.0.0p3", "cme", "2.0.0p3", "cme")
    True

    C*E != CME is not allowed

    >>> c("2.0.0p3", "cee", "2.0.0p3", "cme")
    False
    >>> c("2.0.0p3", "cme", "2.0.0p3", "cee")
    False
    >>> c("2.0.0p3", "cre", "2.0.0p3", "cme")
    False
    >>> c("2.0.0p3", "cme", "2.0.0p3", "cre")
    False

    Prev major to new is allowed #1

    >>> c("1.6.0i1", "cee", "2.0.0", "cee")
    True
    >>> c("1.6.0p23", "cee", "2.0.0", "cee")
    True
    >>> c("2.0.0p12", "cee", "2.1.0i1", "cee")
    True

    Prepre major to new not allowed

    >>> c("1.6.0p1", "cee", "2.1.0p3", "cee")
    False
    >>> c("1.6.0p1", "cee", "2.1.0b1", "cee")
    False
    >>> c("1.5.0i1", "cee", "2.0.0", "cee")
    False
    >>> c("1.4.0", "cee", "2.0.0", "cee")
    False

    New major to old not allowed

    >>> c("2.0.0", "cee", "1.6.0p1", "cee")
    False
    >>> c("2.1.0", "cee", "2.0.0b1", "cee")
    False
    """
    # Pre 2.0.0p1 did not sent x-checkmk-* headers -> Not compabile
    if (
        not central_edition_short
        or not central_version
        or not remote_edition_short
        or not remote_version
    ):
        return False

    if (central_edition_short == "cme" and remote_edition_short != "cme") or (
        remote_edition_short == "cme" and central_edition_short != "cme"
    ):
        return False

    # Daily builds of the master branch (format: YYYY.MM.DD) are always treated to be compatbile
    if is_daily_build_of_master(central_version) or is_daily_build_of_master(remote_version):
        return True

    central_parts = base_version_parts(central_version)
    remote_parts = base_version_parts(remote_version)

    # Same major version is allowed
    if central_parts == remote_parts:
        return True

    # Newer major to older is not allowed
    if central_parts > remote_parts:
        return False

    # Now we need to detect the previous and pre-previous major version.
    # How can we do it without explicitly listing all version numbers?
    #
    # What version changes did we have?
    #
    # - Long ago we increased only the 3rd number which is not done anymore
    # - Until 1.6.0 we only increased the 2nd number
    # - With 2.0.0 we once increased the 1st number
    # - With 2.1.0 we will again only increase the 2nd number
    # - Increasing of the 1st number may happen again
    #
    # Seems we need to handle these cases for:
    #
    # - Steps in 1st number with reset of 2nd number can happen
    # - Steps in 2nd number can happen
    # - 3rd number and suffixes can completely be ignored for now
    #
    # We could implement a simple logic like this:
    #
    # - 1st number +1, newer 2nd is 0 -> it is uncertain which was the
    #                                    last release. We need an explicit
    #                                    lookup table for this situation.
    # - 1st number +2                      -> preprev major
    # - Equal 1st number and 2nd number +1 -> prev major
    # - Equal 1st number and 2nd number +2 -> preprev major
    #
    # Seems to be sufficient for now.
    #
    # Obviously, this only works as long as we keep the current version scheme.

    if remote_parts[0] - central_parts[0] > 1:
        return False  # preprev 1st number

    last_major_releases = {
        1: (1, 6, 0),
    }

    if remote_parts[0] - central_parts[0] == 1 and remote_parts[1] == 0:
        if last_major_releases[central_parts[0]] == central_parts:
            return True  # prev major (e.g. last 1.x.0 before 2.0.0)
        return False  # preprev 1st number

    if remote_parts[0] == central_parts[0]:
        if remote_parts[1] - central_parts[1] > 1:
            return False  # preprev in 2nd number
        if remote_parts[1] - central_parts[1] == 1:
            return True  # prev in 2nd number, ignoring 3rd

    # Everything else is incompatible
    return False
