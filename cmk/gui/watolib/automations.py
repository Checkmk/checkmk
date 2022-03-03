#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This code section deals with the interaction of Check_MK base code. It is
used for doing inventory, showing the services of a host, deletion of a host
and similar things."""

import ast
import os
import re
import subprocess
import time
import uuid
from typing import Tuple, Dict, Any, Optional, NamedTuple, Sequence

import urllib3  # type: ignore[import]
import requests
import logging
from six import ensure_str

from livestatus import SiteId, SiteConfiguration

from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import AutomationDiscoveryResponse, DiscoveryResult
import cmk.utils.store as store
import cmk.utils.version as cmk_version

from cmk.gui.globals import html
import cmk.gui.config as config
import cmk.gui.hooks as hooks
from cmk.gui.utils.url_encoder import URLEncoder
from cmk.gui.i18n import _
from cmk.gui.log import logger
import cmk.gui.escaping as escaping
from cmk.gui.watolib.sites import SiteManagementFactory
from cmk.gui.watolib.utils import mk_repr
from cmk.gui.background_job import BackgroundProcessInterface
import cmk.gui.gui_background_job as gui_background_job
from cmk.gui.exceptions import MKGeneralException, MKUserError
from cmk.gui.watolib.automation_commands import AutomationCommand, automation_command_registry
from cmk.gui.watolib.wato_background_job import WatoBackgroundJob

auto_logger = logger.getChild("automations")

# Disable python warnings in background job output or logs like "Unverified
# HTTPS request is being made". We warn the user using analyze configuration.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MKAutomationException(MKGeneralException):
    pass


def check_mk_automation(siteid: SiteId,
                        command: str,
                        args: Optional[Sequence[str]] = None,
                        indata: Any = "",
                        stdin_data: Optional[str] = None,
                        timeout: Optional[int] = None,
                        sync: bool = True,
                        non_blocking_http: bool = False) -> Any:
    if args is None:
        args = []

    if not siteid or config.site_is_local(siteid):
        return check_mk_local_automation(command, args, indata, stdin_data, timeout)

    return check_mk_remote_automation(
        site_id=siteid,
        command=command,
        args=args,
        indata=indata,
        stdin_data=stdin_data,
        timeout=timeout,
        sync=sync,
        non_blocking_http=non_blocking_http,
    )


def check_mk_local_automation(command: str,
                              args: Optional[Sequence[str]] = None,
                              indata: Any = "",
                              stdin_data: Optional[str] = None,
                              timeout: Optional[int] = None) -> Any:
    if args is None:
        args = []
    new_args = [ensure_str(a) for a in args]

    if stdin_data is None:
        stdin_data = repr(indata)

    if timeout:
        new_args = ["--timeout", "%d" % timeout] + new_args

    cmd = ['check_mk']

    if auto_logger.isEnabledFor(logging.DEBUG):
        cmd.append("-vv")
    elif auto_logger.isEnabledFor(VERBOSE):
        cmd.append("-v")

    cmd += ['--automation', command] + new_args

    if command in ['restart', 'reload']:
        call_hook_pre_activate_changes()

    cmd = [ensure_str(a) for a in cmd]

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
        raise _local_automation_failure(command=command, cmdline=cmd, exc=e)

    auto_logger.info("FINISHED: %d" % completed_process.returncode)
    auto_logger.debug("OUTPUT: %r" % completed_process.stdout)

    if completed_process.stderr:
        auto_logger.warning("'%s' returned '%s'" % (
            " ".join(cmd),
            completed_process.stderr,
        ))
    if completed_process.returncode:
        auto_logger.error("Error running %r (exit code %d)" % (
            subprocess.list2cmdline(cmd),
            completed_process.returncode,
        ))
        raise _local_automation_failure(
            command=command,
            cmdline=cmd,
            code=completed_process.returncode,
            out=completed_process.stdout,
            err=completed_process.stderr,
        )

    # On successful "restart" command execute the activate changes hook
    if command in ['restart', 'reload']:
        call_hook_activate_changes()

    try:
        return ast.literal_eval(completed_process.stdout)
    except SyntaxError as e:
        raise _local_automation_failure(command=command,
                                        cmdline=cmd,
                                        out=completed_process.stdout,
                                        exc=e)


def _local_automation_failure(command, cmdline, code=None, out=None, err=None, exc=None):
    call = subprocess.list2cmdline(cmdline) if config.debug else command
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


def check_mk_remote_automation(site_id: SiteId,
                               command: str,
                               args: Optional[Sequence[str]],
                               indata: Any,
                               stdin_data: Optional[str] = None,
                               timeout: Optional[int] = None,
                               sync: bool = True,
                               non_blocking_http: bool = False) -> Any:
    site = config.site(site_id)
    if "secret" not in site:
        raise MKGeneralException(
            _("Cannot connect to site \"%s\": The site is not logged in") %
            site.get("alias", site_id))

    if not site.get("replication"):
        raise MKGeneralException(
            _("Cannot connect to site \"%s\": The replication is disabled") %
            site.get("alias", site_id))

    if sync:
        sync_changes_before_remote_automation(site_id)

    if non_blocking_http:
        # This will start a background job process on the remote site to execute the automation
        # asynchronously. It then polls the remote site, waiting for completion of the job.
        return _do_check_mk_remote_automation_in_background_job(
            site_id, CheckmkAutomationRequest(command, args, indata, stdin_data, timeout))

    # Synchronous execution of the actual remote command in a single blocking HTTP request
    return do_remote_automation(
        config.site(site_id),
        "checkmk-automation",
        [
            ("automation", command),  # The Checkmk automation command
            ("arguments", mk_repr(args)),  # The arguments for the command
            ("indata", mk_repr(indata)),  # The input data
            ("stdin_data", mk_repr(stdin_data)),  # The input data for stdin
            ("timeout", mk_repr(timeout)),  # The timeout
        ])


# If the site is not up-to-date, synchronize it first.
def sync_changes_before_remote_automation(site_id):
    # TODO: Cleanup this local import
    import cmk.gui.watolib.activate_changes  # pylint: disable=redefined-outer-name
    manager = cmk.gui.watolib.activate_changes.ActivateChangesManager()
    manager.load()

    if not manager.is_sync_needed(site_id):
        return

    logger.info("Syncing %s", site_id)

    manager.start([site_id], activate_foreign=True, prevent_activate=True)

    # Wait maximum 30 seconds for sync to finish
    timeout = 30.0
    while manager.is_running() and timeout > 0.0:
        time.sleep(0.5)
        timeout -= 0.5

    state = manager.get_site_state(site_id)
    if state and state["_state"] != "success":
        logger.error(_("Remote automation tried to sync pending changes but failed: %s"),
                     state.get("_status_details"))


# This hook is executed when one applies the pending configuration changes
# from wato but BEFORE the nagios restart is executed.
#
# It can be used to create custom input files for nagios/Checkmk.
#
# The registered hooks are called with a dictionary as parameter which
# holds all available with the hostnames as keys and the attributes of
# the hosts as values.
def call_hook_pre_activate_changes():
    if hooks.registered('pre-activate-changes'):
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
    if hooks.registered('activate-changes'):
        # TODO: Cleanup this local import
        import cmk.gui.watolib.hosts_and_folders  # pylint: disable=redefined-outer-name
        hooks.call("activate-changes", cmk.gui.watolib.hosts_and_folders.collect_all_hosts())


def do_remote_automation(site, command, vars_, files=None, timeout=None):
    auto_logger.info("RUN [%s]: %s", site, command)
    auto_logger.debug("VARS: %r", vars_)

    base_url = site["multisiteurl"]
    secret = site.get("secret")
    if not secret:
        raise MKAutomationException(_("You are not logged into the remote site."))

    url = (base_url + "automation.py?" + URLEncoder().urlencode_vars([("command", command)]))

    post_data = dict(vars_)
    post_data.update({
        "secret": secret,
        "debug": "1" if config.debug else "",
    })

    response = get_url(url,
                       site.get('insecure', False),
                       data=post_data,
                       files=files,
                       timeout=timeout)

    auto_logger.debug("RESPONSE: %r", response)

    if not response:
        raise MKAutomationException(_("Empty output from remote site."))

    try:
        response = ast.literal_eval(response)
    except SyntaxError:
        # The remote site will send non-Python data in case of an error.
        raise MKAutomationException("%s: <pre>%s</pre>" % (_("Got invalid data"), response))

    return response


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
            "x-checkmk-edition": cmk_version.edition_short(),
        },
    )

    response.encoding = "utf-8"  # Always decode with utf-8

    if response.status_code == 401:
        raise MKUserError("_passwd", _("Authentication failed. Invalid login/password."))

    if response.status_code == 503 and "Site Not Started" in response.text:
        raise MKUserError(None, _("Site is not running"))

    if response.status_code != 200:
        raise MKUserError(None, _("HTTP Error - %d: %s") % (response.status_code, response.text))

    return response


def get_url(url, insecure, auth=None, data=None, files=None, timeout=None):
    return get_url_raw(url, insecure, auth, data, files, timeout).text


def get_url_json(url, insecure, auth=None, data=None, files=None, timeout=None):
    return get_url_raw(url, insecure, auth, data, files, timeout).json()


def do_site_login(site_id, name, password):
    sites = SiteManagementFactory().factory().load_sites()
    site = sites[site_id]
    if not name:
        raise MKUserError("_name", _("Please specify your administrator login on the remote site."))
    if not password:
        raise MKUserError("_passwd", _("Please specify your password."))

    # Trying basic auth AND form based auth to ensure the site login works.
    # Adding _ajaxid makes the web service fail silently with an HTTP code and
    # not output HTML code for an error screen.
    url = site["multisiteurl"] + 'login.py'
    post_data = {
        '_login': '1',
        '_username': name,
        '_password': password,
        '_origtarget': 'automation_login.py?_version=%s&_edition_short=%s' %
                       (cmk_version.__version__, cmk_version.edition_short()),
        '_plain_error': '1',
    }
    response = get_url(url, site.get('insecure', False), auth=(name, password),
                       data=post_data).strip()
    if '<html>' in response.lower():
        message = _("Authentication to web service failed.<br>Message:<br>%s") % \
                  escaping.strip_tags(escaping.strip_scripts(response))
        if config.debug:
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
                _("The Check_MK Managed Services Edition can only "
                  "be connected with other sites using the CME."))
        return eval_response["login_secret"]
    return eval_response


CheckmkAutomationRequest = NamedTuple("CheckmkAutomationRequest", [
    ("command", str),
    ("args", Optional[Sequence[str]]),
    ("indata", Any),
    ("stdin_data", Optional[str]),
    ("timeout", Optional[int]),
])

CheckmkAutomationGetStatusResponse = NamedTuple("CheckmkAutomationGetStatusResponse", [
    ("job_status", Dict[str, Any]),
    ("result", Any),
])


# There are already at least two custom background jobs that are wrapping remote automation
# calls but have been implemented individually. Does it make sense to refactor them to use this?
# - Service discovery of a single host (cmk.gui.wato.pages.services._get_check_table)
# - Fetch agent / SNMP output (cmk.gui.wato.pages.fetch_agent_output.FetchAgentOutputBackgroundJob)
def _do_check_mk_remote_automation_in_background_job(
        site_id: SiteId, automation_request: CheckmkAutomationRequest) -> Any:
    """Execute the automation in a background job on the remote site

    It starts the background job using one call. It then polls the remote site, waiting for
    completion of the job."""
    site_config = config.site(site_id)

    job_id = _start_remote_automation_job(site_config, automation_request)

    auto_logger.info("Waiting for job completion")
    result = None
    while True:
        raw_response = do_remote_automation(site_config, "checkmk-remote-automation-get-status", [
            ("request", repr(job_id)),
        ])
        response = CheckmkAutomationGetStatusResponse(*raw_response)
        auto_logger.debug("Job status: %r", response)

        if not response.job_status["is_active"]:
            result = response.result
            auto_logger.debug("Job is not active anymore. Return the result: %s", result)
            break

    return result


def _start_remote_automation_job(site_config: SiteConfiguration,
                                 automation_request: CheckmkAutomationRequest) -> str:
    auto_logger.info("Starting remote automation in background job")
    job_id = do_remote_automation(site_config, "checkmk-remote-automation-start", [
        ("request", repr(tuple(automation_request))),
    ])

    auto_logger.info("Started background job: %s", job_id)
    return job_id


@automation_command_registry.register
class AutomationCheckmkAutomationStart(AutomationCommand):
    """Called by do_remote_automation_in_background_job to execute the background job on a remote site"""
    def command_name(self) -> str:
        return "checkmk-remote-automation-start"

    def get_request(self) -> CheckmkAutomationRequest:
        return CheckmkAutomationRequest(
            *ast.literal_eval(html.request.get_ascii_input_mandatory("request")))

    def execute(self, request: CheckmkAutomationRequest) -> Tuple:
        job = CheckmkAutomationBackgroundJob(request=request)
        job.set_function(job.execute_automation, request=request)
        job.start()
        return job.get_job_id()


@automation_command_registry.register
class AutomationCheckmkAutomationGetStatus(AutomationCommand):
    """Called by do_remote_automation_in_background_job to get the background job state from on a
    remote site"""
    def command_name(self) -> str:
        return "checkmk-remote-automation-get-status"

    def get_request(self) -> str:
        return ast.literal_eval(html.request.get_ascii_input_mandatory("request"))

    def execute(self, request: str) -> Tuple:
        job_id = request
        job = CheckmkAutomationBackgroundJob(job_id)
        job_status = job.get_status_snapshot().get_status_as_dict()[job.get_job_id()]

        result_file_path = os.path.join(job.get_work_dir(), "result.mk")
        result = store.load_object_from_file(result_file_path, default=None)

        return tuple(CheckmkAutomationGetStatusResponse(job_status=job_status, result=result))


@gui_background_job.job_registry.register
class CheckmkAutomationBackgroundJob(WatoBackgroundJob):
    """The background job is always executed on the site where the host is located on"""
    job_prefix = "automation-"

    @classmethod
    def gui_title(cls) -> str:
        return _("Checkmk automation")

    def __init__(self,
                 job_id: Optional[str] = None,
                 request: Optional[CheckmkAutomationRequest] = None) -> None:
        if job_id is not None:
            # Loading an existing job
            super(CheckmkAutomationBackgroundJob, self).__init__(job_id=job_id)
            return

        assert request is not None

        # A new job is started
        automation_id = str(uuid.uuid4())
        super(CheckmkAutomationBackgroundJob, self).__init__(
            job_id="%s%s-%s" % (self.job_prefix, request.command, automation_id),
            title=_("Checkmk automation %s %s") % (request.command, automation_id),
        )

    def execute_automation(self, job_interface: BackgroundProcessInterface,
                           request: CheckmkAutomationRequest) -> None:
        self._logger.info("Starting automation: %s", request.command)
        self._logger.debug(request)

        result = check_mk_local_automation(request.command, request.args, request.indata,
                                           request.stdin_data, request.timeout)

        # This file will be read by the get-status request
        result_file_path = os.path.join(job_interface.get_work_dir(), "result.mk")
        store.save_object_to_file(result_file_path, result)

        job_interface.send_result_message(_("Finished."))


def execute_automation_discovery(*,
                                 site_id: SiteId,
                                 args: Sequence[str],
                                 timeout=None,
                                 non_blocking_http=False) -> AutomationDiscoveryResponse:
    raw_response = check_mk_automation(site_id,
                                       "inventory",
                                       args,
                                       timeout=timeout,
                                       non_blocking_http=True)
    # This automation may be executed agains 1.6 remote sites. Be compatible to old structure
    # (counts, failed_hosts).
    if isinstance(raw_response, tuple) and len(raw_response) == 2:
        results = {
            hostname: DiscoveryResult(
                self_new=v[0],
                self_removed=v[1],
                self_kept=v[2],
                self_total=v[3],
                self_new_host_labels=v[4],
                self_total_host_labels=v[5],
            ) for hostname, v in raw_response[0].items()
        }

        for hostname, error_text in raw_response[1].items():
            results[hostname].error_text = error_text

        return AutomationDiscoveryResponse(results=results)
    if isinstance(raw_response, dict):
        return AutomationDiscoveryResponse.deserialize(raw_response)
    raise NotImplementedError()
