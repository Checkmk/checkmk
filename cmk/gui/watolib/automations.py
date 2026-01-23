#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This code section deals with the interaction of Checkmk base code. It is
used for doing inventory, showing the services of a host, deletion of a host
and similar things."""

# mypy: disable-error-code="no-any-return"

from __future__ import annotations

import ast
import functools
import json
import os
import re
import subprocess
import time
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, replace
from io import BytesIO
from typing import Annotated, Final, NamedTuple

import requests
import urllib3
from pydantic import BaseModel, field_validator, PlainValidator
from requests import RequestException

from livestatus import SiteConfiguration

import cmk.ccc.version as cmk_version
from cmk import trace
from cmk.automations.automation_executor import AutomationExecutor
from cmk.automations.automation_helper import HelperExecutor
from cmk.automations.automation_subprocess import SubprocessExecutor
from cmk.automations.results import SerializedResult
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import get_omd_config, SiteId
from cmk.ccc.store import RealIo
from cmk.ccc.user import UserId
from cmk.gui import hooks
from cmk.gui.background_job import (
    BackgroundStatusSnapshot,
    JobStatusSpec,
    JobStatusStates,
)
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Request, request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.site_config import is_replication_enabled, site_is_local
from cmk.gui.utils import escaping
from cmk.gui.utils.compatibility import (
    EditionsIncompatible,
    is_distributed_setup_compatible_for_licensing,
    LicenseStateIncompatible,
    LicensingCompatible,
    make_incompatible_info,
)
from cmk.gui.utils.urls import urlencode_vars
from cmk.gui.watolib.host_attributes import CollectedHostAttributes
from cmk.gui.watolib.utils import mk_repr
from cmk.utils import paths
from cmk.utils.automation_config import LocalAutomationConfig, RemoteAutomationConfig
from cmk.utils.licensing.handler import LicenseState
from cmk.utils.licensing.registry import get_license_state

auto_logger = logger.getChild("automations")
tracer = trace.get_tracer()

# Disable python warnings in background job output or logs like "Unverified
# HTTPS request is being made". We warn the user using analyze configuration.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ENV_VARIABLE_FORCE_CLI_INTERFACE: Final[str] = "_CMK_AUTOMATIONS_FORCE_CLI_INTERFACE"


def remote_automation_config_from_site_config(
    site_config: SiteConfiguration,
) -> RemoteAutomationConfig:
    if "secret" not in site_config:
        raise MKGeneralException(
            _('Cannot connect to site "%s": The site is not logged in') % site_config["alias"]
        )

    if not is_replication_enabled(site_config):
        raise MKGeneralException(
            _('Cannot connect to site "%s": The replication is disabled') % site_config["alias"]
        )
    return RemoteAutomationConfig(
        site_id=site_config["id"],
        base_url=site_config["multisiteurl"],
        secret=site_config["secret"],
        insecure=site_config["insecure"],
    )


def make_automation_config(
    site_config: SiteConfiguration,
) -> LocalAutomationConfig | RemoteAutomationConfig:
    return (
        LocalAutomationConfig()
        if site_is_local(site_config)
        else remote_automation_config_from_site_config(site_config)
    )


class MKAutomationException(MKGeneralException):
    pass


def cmk_version_of_remote_automation_source(remote_request: Request) -> cmk_version.Version:
    # The header is sent by Checkmk as of 2.0.0p1. In case it is missing, assume we are too old.
    return cmk_version.Version.from_str(remote_request.headers.get("x-checkmk-version", "1.6.0p1"))


def check_mk_local_automation_serialized(
    *,
    command: str,
    args: Sequence[str] | None = None,
    indata: object = "",
    stdin_data: str | None = None,
    timeout: int | None = None,
    force_cli_interface: bool = False,
    debug: bool,
    collect_all_hosts: Callable[[], Mapping[HostName, CollectedHostAttributes]],
) -> tuple[Sequence[str], SerializedResult]:
    with tracer.span(
        f"local_automation[{command}]",
        attributes={"cmk.automation.args": repr(args)},
    ) as span:
        if args is None:
            args = []

        if stdin_data is None:
            stdin_data = repr(indata)

        if command in ["restart", "reload"]:
            call_hook_pre_activate_changes(collect_all_hosts)

        executor: AutomationExecutor = (
            SubprocessExecutor()
            if force_cli_interface
            or os.environ.get(ENV_VARIABLE_FORCE_CLI_INTERFACE)
            or not _automation_helper_enabled_in_omd_config()
            else HelperExecutor()
        )

        try:
            result = executor.execute(command, args, stdin_data, auto_logger, timeout)
        except Exception as e:
            match e:
                case RequestException(response=response) if response is not None:
                    # Case 1: We got an actual HTTP response from the helper
                    try:
                        data = response.json()
                        error_text = data.get("detail", str(data))
                    except ValueError:
                        error_text = response.text

                    msg = get_local_automation_failure_message(
                        command=command,
                        cmdline=executor.command_description(command, args, logger, timeout),
                        code=response.status_code,
                        err=error_text,
                        debug=debug,
                    )

                case RequestException() | _:
                    # Case 2: Network error (Timeout, DNS, Connection Refused) - No response object
                    msg = get_local_automation_failure_message(
                        command=command,
                        cmdline=executor.command_description(command, args, logger, timeout),
                        exc=e,
                        debug=debug,
                    )

            raise MKAutomationException(msg)

        span.set_attribute("cmk.automation.exit_code", result.exit_code)
        auto_logger.info("FINISHED: %d" % result.exit_code)
        auto_logger.debug("OUTPUT: %r" % result.output)

        if result.exit_code:
            auto_logger.error(
                "Error running %r (exit code %d)" % (result.command_description, result.exit_code)
            )
            msg = get_local_automation_failure_message(
                command=command,
                cmdline=result.command_description,
                code=result.exit_code,
                out=result.output,
                err=result.error,
                debug=debug,
            )

            if result.exit_code == 1:
                raise MKUserError(None, msg)

            raise MKAutomationException(msg)

        # On successful "restart" command execute the activate changes hook
        if command in ["restart", "reload"]:
            call_hook_activate_changes(collect_all_hosts)

        return result.command_description, SerializedResult(result.output)


def get_local_automation_failure_message(
    *,
    command: str,
    cmdline: Iterable[str],
    code: int | None = None,
    out: str | None = None,
    err: str | None = None,
    exc: Exception | None = None,
    debug: bool,
) -> str:
    call = subprocess.list2cmdline(cmdline) if debug else command
    msg = "Error running automation call <tt>%s</tt>" % call
    if code:
        msg += " (exit code %d)" % code
    if out:
        msg += ", output: <pre>%s</pre>" % _hilite_errors(out)
    if err:
        msg += ", error: <pre>%s</pre>" % _hilite_errors(err)
    if exc:
        msg += ": %s" % exc
    return msg


def _hilite_errors(outdata: str) -> str:
    return re.sub("\nError: *([^\n]*)", "\n<div class=err><b>Error:</b> \\1</div>", outdata)


def check_mk_remote_automation_serialized(
    *,
    automation_config: RemoteAutomationConfig,
    command: str,
    args: Sequence[str] | None,
    indata: object,
    stdin_data: str | None = None,
    timeout: int | None = None,
    sync: Callable[[SiteId, bool], None],
    non_blocking_http: bool = False,
    debug: bool,
) -> SerializedResult:
    with tracer.span(
        f"remote_automation[{command}]",
        attributes={
            "cmk.automation.target_site_id": str(automation_config.site_id),
            "cmk.automation.args": repr(args),
        },
    ):
        sync(automation_config.site_id, debug)

        if non_blocking_http:
            # This will start a background job process on the remote site to execute the automation
            # asynchronously. It then polls the remote site, waiting for completion of the job.
            return _do_check_mk_remote_automation_in_background_job_serialized(
                automation_config,
                CheckmkAutomationRequest(command, args, indata, stdin_data, timeout, debug=debug),
                debug=debug,
            )

        # Synchronous execution of the actual remote command in a single blocking HTTP request
        return SerializedResult(
            _do_remote_automation_serialized(
                automation_config=automation_config,
                command="checkmk-automation",
                vars_=[
                    ("automation", command),  # The Checkmk automation command
                    ("arguments", mk_repr(args).decode("ascii")),  # The arguments for the command
                    ("indata", mk_repr(indata).decode("ascii")),  # The input data
                    ("stdin_data", mk_repr(stdin_data).decode("ascii")),  # The input data for stdin
                    ("timeout", mk_repr(timeout).decode("ascii")),  # The timeout
                ],
                files=None,
                timeout=timeout,
                debug=debug,
            )
        )


def call_hook_pre_activate_changes(
    collect_all_hosts: Callable[[], Mapping[HostName, CollectedHostAttributes]],
) -> None:
    """Execute the pre-activate-changes hooks

    This hook is executed when one applies the pending configuration changes
    from wato but BEFORE the nagios restart is executed.

    It can be used to create custom input files for nagios/Checkmk.

    The registered hooks are called with a dictionary as parameter which
    holds all available with the hostnames as keys and the attributes of
    the hosts as values."""
    if hooks.registered("pre-activate-changes"):
        hooks.call("pre-activate-changes", collect_all_hosts)


def call_hook_activate_changes(
    collect_all_hosts: Callable[[], Mapping[HostName, CollectedHostAttributes]],
) -> None:
    """Execute the post activate-changes hooks

    This hook is executed when one applies the pending configuration changes
    from wato.

    But it is only excecuted when there is at least one function
    registered for this host.

    The registered hooks are called with a dictionary as parameter which
    holds all available with the hostnames as keys and the attributes of
    the hosts as values."""
    if hooks.registered("activate-changes"):
        hooks.call("activate-changes", collect_all_hosts)


def _do_remote_automation_serialized(
    *,
    automation_config: RemoteAutomationConfig,
    command: str,
    vars_: Sequence[tuple[str, str]],
    files: Mapping[str, BytesIO] | None,
    timeout: float | None,
    debug: bool,
) -> str:
    auto_logger.info("RUN [%s]: %s", automation_config.site_id or "site id not in config", command)
    auto_logger.debug("Site config: %r", _sanitize_remote_automation_config(automation_config))
    auto_logger.debug("VARS: %r", vars_)

    base_url = automation_config.base_url
    secret = automation_config.secret
    if not secret:
        raise MKAutomationException(_("You are not logged into the remote site."))

    url = base_url + "automation.py?" + urlencode_vars([("command", command)])

    post_data = dict(vars_)
    post_data.update(
        {
            "secret": secret,
            "debug": "1" if debug else "",
        }
    )

    response = get_url(
        url, automation_config.insecure, data=post_data, files=files, timeout=timeout
    )

    auto_logger.debug("RESPONSE: %r", response)

    if not response:
        raise MKAutomationException(_("Empty output from remote site."))

    return response


def _sanitize_remote_automation_config(config: RemoteAutomationConfig) -> dict[str, object]:
    return asdict(replace(config, secret="redacted"))


def fetch_service_discovery_background_job_status(
    automation_config: RemoteAutomationConfig, hostname: str, *, debug: bool
) -> BackgroundStatusSnapshot:
    details = json.loads(
        str(
            do_remote_automation(
                automation_config=automation_config,
                command="service-discovery-job-snapshot",
                vars_=[("hostname", hostname)],
                debug=debug,
            )
        )
    )
    return BackgroundStatusSnapshot(
        job_id=details["job_id"],
        status=JobStatusSpec(**details["status"]),
        exists=details["exists"],
        is_active=details["is_active"],
        has_exception=details["has_exception"],
        acknowledged_by=details["acknowledged_by"],
        may_stop=details["may_stop"],
        may_delete=details["may_delete"],
    )


def do_remote_automation(
    automation_config: RemoteAutomationConfig,
    command: str,
    vars_: Sequence[tuple[str, str]],
    debug: bool,
    files: Mapping[str, BytesIO] | None = None,
    timeout: float | None = None,
) -> object:
    serialized_response = _do_remote_automation_serialized(
        automation_config=automation_config,
        command=command,
        vars_=vars_,
        files=files,
        timeout=timeout,
        debug=debug,
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
    add_headers: dict[str, str] | None = None,
) -> requests.Response:
    headers_ = {
        "x-checkmk-version": cmk_version.__version__,
        "x-checkmk-edition": cmk_version.edition(paths.omd_root).short,
        "x-checkmk-license-state": get_license_state().readable,
    }
    headers_.update(add_headers or {})

    try:
        response = requests.post(
            url,
            data=data,
            verify=not insecure,
            auth=auth,
            files=files,
            timeout=timeout,
            headers=headers_,
        )
    except (ConnectionError, requests.ConnectionError) as e:
        raise MKUserError(None, _("Could not connect to the remote site (%s)") % e)

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
    central_edition_short = cmk_version.edition(paths.omd_root).short
    central_license_state = get_license_state()

    remote_version = response.headers.get("x-checkmk-version", "")
    remote_edition_short = response.headers.get("x-checkmk-edition", "")
    remote_license_state = parse_license_state(response.headers.get("x-checkmk-license-state", ""))

    if not remote_version or not remote_edition_short:
        return  # No validation

    if not isinstance(
        compatibility := _compatible_with_central_site(
            central_version,
            central_edition_short,
            central_license_state,
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
                central_license_state,
                remote_version,
                remote_edition_short,
                remote_license_state,
                compatibility,
            )
        )


def verify_request_compatibility(ignore_license_compatibility: bool) -> None:
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
    central_license_state = parse_license_state(request.headers.get("x-checkmk-license-state", ""))
    remote_version = cmk_version.__version__
    remote_edition_short = cmk_version.edition(paths.omd_root).short
    remote_license_state = get_license_state()

    compatibility = _compatible_with_central_site(
        central_version,
        central_edition_short,
        central_license_state,
        remote_version,
        remote_edition_short,
        remote_license_state,
    )

    if ignore_license_compatibility and isinstance(compatibility, LicenseStateIncompatible):
        return

    if not isinstance(compatibility, cmk_version.VersionsCompatible):
        raise MKGeneralException(
            make_incompatible_info(
                central_version,
                central_edition_short,
                central_license_state,
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


def get_url(
    url: str,
    insecure: bool,
    auth: tuple[str, str] | None = None,
    data: Mapping[str, str] | None = None,
    files: Mapping[str, BytesIO] | None = None,
    timeout: float | None = None,
) -> str:
    return get_url_raw(url, insecure, auth, data, files, timeout).text


def do_site_login(site: SiteConfiguration, name: UserId, password: str, *, debug: bool) -> str:
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
        "_origtarget": f"automation_login.py?_version={cmk_version.__version__}&_edition_short={cmk_version.edition(paths.omd_root).short}",
        "_plain_error": "1",
    }
    response = get_url(
        url, site.get("insecure", False), auth=(name, password), data=post_data
    ).strip()
    if "<html>" in response.lower():
        message = _(
            "Authentication to web service failed.<br>Message:<br>%s"
        ) % escaping.strip_tags(escaping.strip_scripts(response))
        if debug:
            message += "<br>" + _("Automation URL:") + " <tt>%s</tt><br>" % url
        raise MKAutomationException(message)
    if not response:
        raise MKAutomationException(_("Empty response from web service"))
    try:
        eval_response = ast.literal_eval(response)
    except SyntaxError:
        raise MKAutomationException(response)
    if isinstance(eval_response, dict):
        if cmk_version.edition(paths.omd_root) is cmk_version.Edition.ULTIMATEMT and eval_response[
            "edition_short"
        ] not in ["cme", cmk_version.Edition.ULTIMATEMT.short]:
            raise MKUserError(
                None,
                (
                    "Checkmk Ultimate with multi-tenancy can only be connected with other sites"
                    " using Checkmk Ultimate with multi-tenancy."
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
    # Optional value can be removed with 2.6
    debug: bool = False


RemoteAutomationGetStatusResponseRaw = tuple[dict[str, object], str]


class CheckmkAutomationGetStatusResponse(NamedTuple):
    job_status: JobStatusSpec
    result: str


# There are already at least two custom background jobs that are wrapping remote automation
# calls but have been implemented individually. Does it make sense to refactor them to use this?
# - Service discovery of a single host (cmk.gui.wato.pages.services._get_check_table)
# - Fetch agent / SNMP output (cmk.gui.wato.pages.fetch_agent_output.FetchAgentOutputBackgroundJob)
def _do_check_mk_remote_automation_in_background_job_serialized(
    automation_config: RemoteAutomationConfig,
    automation_request: CheckmkAutomationRequest,
    *,
    debug: bool,
) -> SerializedResult:
    """Execute the automation in a background job on the remote site

    It starts the background job using one call. It then polls the remote site, waiting for
    completion of the job."""
    job_id = _start_remote_automation_job(automation_config, automation_request, debug=debug)

    auto_logger.info("Waiting for job completion")
    result = None
    while True:
        raw_response = do_remote_automation(
            automation_config,
            "checkmk-remote-automation-get-status",
            [
                ("request", repr(job_id)),
            ],
            debug=debug,
        )
        assert isinstance(raw_response, tuple)
        response = CheckmkAutomationGetStatusResponse(
            JobStatusSpec.model_validate(raw_response[0]),
            raw_response[1],
        )
        auto_logger.debug("Job status: %r", response)

        if not response.job_status.is_active:
            if response.job_status.state == JobStatusStates.EXCEPTION:
                raise MKAutomationException("\n".join(response.job_status.loginfo["JobException"]))

            result = response.result
            auto_logger.debug("Job is not active anymore. Return the result: %s", result)
            break
        time.sleep(0.25)

    assert isinstance(result, str)

    return SerializedResult(result)


def _start_remote_automation_job(
    automation_config: RemoteAutomationConfig,
    automation_request: CheckmkAutomationRequest,
    *,
    debug: bool,
) -> str:
    auto_logger.info("Starting remote automation in background job")
    job_id = str(
        do_remote_automation(
            automation_config,
            "checkmk-remote-automation-start",
            [
                ("request", repr(tuple(automation_request))),
            ],
            debug=debug,
        )
    )

    auto_logger.info("Started background job: %s", job_id)
    return job_id


def _edition_from_short(edition_str: str) -> cmk_version.Edition:
    # TODO The legacy edition names can be removed with Checkmk 2.6
    match edition_str:
        case "cre" | cmk_version.Edition.COMMUNITY.short:
            return cmk_version.Edition.COMMUNITY
        case "cee" | cmk_version.Edition.PRO.short:
            return cmk_version.Edition.PRO
        case "cce" | cmk_version.Edition.ULTIMATE.short:
            return cmk_version.Edition.ULTIMATE
        case "cme" | cmk_version.Edition.ULTIMATEMT.short:
            return cmk_version.Edition.ULTIMATEMT
        case "cse" | cmk_version.Edition.CLOUD.short:
            return cmk_version.Edition.CLOUD
        case _:
            raise ValueError(edition_str)


def _compatible_with_central_site(
    central_version: str,
    central_edition_short: str,
    central_license_state: LicenseState | None,
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

    >>> c = _compatible_with_central_site

    C*E != CME is not allowed

    >>> str(c("2.2.0p1", "cce", LicenseState.LICENSED, "2.2.0p1", "cce", LicenseState.FREE))
    'Remote site in license state free is not allowed'
    >>> str(c("2.0.0p3", "cee", LicenseState.LICENSED, "2.0.0p3", "cme", LicenseState.LICENSED))
    'Mix of CME and non-CME is not allowed.'
    >>> str(c("2.0.0p3", "cme", LicenseState.LICENSED, "2.0.0p3", "cee", LicenseState.LICENSED))
    'Mix of CME and non-CME is not allowed.'
    >>> str(c("2.0.0p3", "cre", LicenseState.LICENSED, "2.0.0p3", "cme", LicenseState.LICENSED))
    'Mix of CME and non-CME is not allowed.'
    >>> str(c("2.0.0p3", "cme", LicenseState.LICENSED, "2.0.0p3", "cre", LicenseState.LICENSED))
    'Mix of CME and non-CME is not allowed.'
    >>> isinstance(c("2.0.0p3", "cme", LicenseState.LICENSED, "2.0.0p3", "cme", LicenseState.LICENSED), cmk_version.VersionsCompatible)
    True
    """

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

    if not isinstance(
        version_compatibility := cmk_version.versions_compatible(
            cmk_version.Version.from_str(central_version),
            cmk_version.Version.from_str(remote_version),
        ),
        cmk_version.VersionsCompatible,
    ):
        return version_compatibility

    if not isinstance(
        licensing_compatibility := is_distributed_setup_compatible_for_licensing(
            central_edition=_edition_from_short(central_edition_short),
            central_license_state=central_license_state,
            remote_edition=_edition_from_short(remote_edition_short),
            remote_license_state=remote_license_state,
        ),
        LicensingCompatible,
    ):
        return licensing_compatibility

    return cmk_version.VersionsCompatible()


class LastKnownCentralSiteVersion(BaseModel):
    """information about the central site

    this is currently only used to store the central site info. We need that info in order to
    communicate to the central site e.g. with the updater-registration (CEE freature). There we
    decide on the auth scheme based on that info.

    As of now this can go with 2.5 since then it is certain the central site supports the new
    scheme. In 2.4 we could encounter a 2.3 central site that does not support the new scheme."""

    version_str: str

    @property
    def cmk_version(self) -> cmk_version.Version:
        return cmk_version.Version.from_str(self.version_str)

    @field_validator("version_str")
    @classmethod
    def _validate_version(cls, v: str) -> str:
        # just check if it is parse able...
        cmk_version.Version.from_str(v)
        return v


class LastKnownCentralSiteVersionStore:
    def __init__(self) -> None:
        self._io: Final = RealIo(paths.var_dir / "last_known_site_version.json")

    @contextmanager
    def locked(self) -> Iterator[None]:
        yield from self._io.locked()

    def write_obj(self, obj: LastKnownCentralSiteVersion) -> None:
        return self._io.write(obj.model_dump_json().encode())

    def read_obj(self) -> LastKnownCentralSiteVersion | None:
        return (
            LastKnownCentralSiteVersion.model_validate_json(raw.decode())
            if (raw := self._io.read())
            else None
        )


AnnotatedHostName = Annotated[HostName, PlainValidator(HostName.parse)]


@functools.cache
def _automation_helper_enabled_in_omd_config() -> bool:
    return get_omd_config(paths.omd_root)["CONFIG_AUTOMATION_HELPER"] == "on"
