#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import ast
import os
from typing import Dict
from pathlib import Path

import cmk.utils.store as store

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.gui_background_job as gui_background_job
import cmk.gui.background_job as background_job

from cmk.gui.globals import html, request as global_request
from cmk.gui.i18n import _
from cmk.gui.pages import page_registry, Page
from cmk.gui.escaping import escape_attribute
from cmk.gui.exceptions import MKGeneralException, HTTPRedirect, MKUserError
from cmk.gui.plugins.views.utils import make_host_breadcrumb
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.watolib import (
    automation_command_registry,
    AutomationCommand,
)
from cmk.gui.utils.urls import makeuri, makeuri_contextless

#.
#   .--Agent-Output--------------------------------------------------------.
#   |     _                    _         ___        _               _      |
#   |    / \   __ _  ___ _ __ | |_      / _ \ _   _| |_ _ __  _   _| |_    |
#   |   / _ \ / _` |/ _ \ '_ \| __|____| | | | | | | __| '_ \| | | | __|   |
#   |  / ___ \ (_| |  __/ | | | ||_____| |_| | |_| | |_| |_) | |_| | |_    |
#   | /_/   \_\__, |\___|_| |_|\__|     \___/ \__,_|\__| .__/ \__,_|\__|   |
#   |         |___/                                    |_|                 |
#   +----------------------------------------------------------------------+
#   | Page for downloading the current agent output / SNMP walk of a host  |
#   '----------------------------------------------------------------------'
# TODO: This feature is used exclusively from the GUI. Why is the code in
#       wato.py? The only reason is because the WATO automation is used. Move
#       to better location.


class FetchAgentOutputRequest:
    def __init__(self, host: watolib.CREHost, agent_type: str) -> None:
        self.host = host
        self.agent_type = agent_type

    @classmethod
    def deserialize(cls, serialized: Dict[str, str]) -> 'FetchAgentOutputRequest':
        host_name = serialized["host_name"]
        host = watolib.Host.host(host_name)
        if host is None:
            raise MKGeneralException(
                _("Host %s does not exist on remote site %s. This "
                  "may be caused by a failed configuration synchronization. Have a look at "
                  "the <a href=\"wato.py?folder=&mode=changelog\">activate changes page</a> "
                  "for further information.") % (host_name, config.omd_site()))
        host.need_permission("read")

        return cls(host, serialized["agent_type"])

    def serialize(self) -> Dict[str, str]:
        return {
            "host_name": self.host.name(),
            "agent_type": self.agent_type,
        }


# TODO: Better use AjaxPage.handle_page() for standard AJAX call error handling. This
# would need larger refactoring of the generic html.popup_trigger() mechanism.
class AgentOutputPage(Page, metaclass=abc.ABCMeta):
    def __init__(self) -> None:
        super(AgentOutputPage, self).__init__()
        self._from_vars()

    def _from_vars(self) -> None:
        config.user.need_permission("wato.download_agent_output")

        host_name = html.request.var("host")
        if not host_name:
            raise MKGeneralException(_("The host is missing."))

        ty = html.request.var("type")
        if ty not in ["walk", "agent"]:
            raise MKGeneralException(_("Invalid type specified."))

        self._back_url = html.get_url_input("back_url", deflt="") or None

        watolib.init_wato_datastructures(with_wato_lock=True)

        host = watolib.Folder.current().host(host_name)
        if not host:
            raise MKGeneralException(
                _("Host is not managed by WATO. "
                  "Click <a href=\"%s\">here</a> to go back.") % escape_attribute(self._back_url))
        host.need_permission("read")

        self._request = FetchAgentOutputRequest(host=host, agent_type=ty)

    @staticmethod
    def file_name(request: FetchAgentOutputRequest) -> str:
        return "%s-%s-%s.txt" % (request.host.site_id(), request.host.name(), request.agent_type)


@page_registry.register_page("fetch_agent_output")
class PageFetchAgentOutput(AgentOutputPage):
    def page(self) -> None:
        title = self._title()
        html.header(title, self._breadcrumb(title))

        self._action()

        if html.request.has_var("_start"):
            self._start_fetch()
        self._show_status()

        html.footer()

    def _title(self) -> str:
        return _("%s: Download agent output") % self._request.host.name()

    def _breadcrumb(self, title: str) -> Breadcrumb:
        breadcrumb = make_host_breadcrumb(self._request.host.name())
        breadcrumb.append(
            BreadcrumbItem(
                title=title,
                url="javascript:document.location.reload(false)",
            ))
        return breadcrumb

    def _action(self) -> None:
        if not html.transaction_valid():
            return

        action_handler = gui_background_job.ActionHandler(self._breadcrumb(self._title()))

        if action_handler.handle_actions() and action_handler.did_delete_job():
            raise HTTPRedirect(
                makeuri_contextless(
                    global_request,
                    [
                        ("host", self._request.host.name()),
                        ("type", self._request.agent_type),
                        ("back_url", self._back_url),
                    ],
                ))

    def _show_status(self) -> None:
        job_status = self._get_job_status()

        html.h3(_("Job status"))
        if job_status["is_active"]:
            html.immediate_browser_redirect(0.8, makeuri(global_request, []))

        job = FetchAgentOutputBackgroundJob(self._request)
        gui_background_job.JobRenderer.show_job_details(job.get_job_id(), job_status)

    def _start_fetch(self) -> None:
        """Start the job on the site the host is monitored by"""
        if config.site_is_local(self._request.host.site_id()):
            start_fetch_agent_job(self._request)
            return

        watolib.do_remote_automation(config.site(self._request.host.site_id()),
                                     "fetch-agent-output-start", [
                                         ("request", repr(self._request.serialize())),
                                     ])

    def _get_job_status(self) -> Dict:
        if config.site_is_local(self._request.host.site_id()):
            return get_fetch_agent_job_status(self._request)

        return watolib.do_remote_automation(config.site(self._request.host.site_id()),
                                            "fetch-agent-output-get-status", [
                                                ("request", repr(self._request.serialize())),
                                            ])


class ABCAutomationFetchAgentOutput(AutomationCommand, metaclass=abc.ABCMeta):
    def get_request(self) -> FetchAgentOutputRequest:
        config.user.need_permission("wato.download_agent_output")

        ascii_input = html.request.get_ascii_input("request")
        if ascii_input is None:
            raise MKUserError("request", _("The parameter \"%s\" is missing.") % "request")
        return FetchAgentOutputRequest.deserialize(ast.literal_eval(ascii_input))


@automation_command_registry.register
class AutomationFetchAgentOutputStart(ABCAutomationFetchAgentOutput):
    """Is called by AgentOutputPage._start_fetch() to execute the background job on a remote site"""
    def command_name(self) -> str:
        return "fetch-agent-output-start"

    def execute(self, request: FetchAgentOutputRequest) -> None:
        start_fetch_agent_job(request)


def start_fetch_agent_job(request):
    job = FetchAgentOutputBackgroundJob(request)
    try:
        job.start()
    except background_job.BackgroundJobAlreadyRunning:
        pass


@automation_command_registry.register
class AutomationFetchAgentOutputGetStatus(ABCAutomationFetchAgentOutput):
    """Is called by AgentOutputPage._get_job_status() to execute the background job on a remote site"""
    def command_name(self):
        return "fetch-agent-output-get-status"

    def execute(self, request: FetchAgentOutputRequest) -> Dict:
        return get_fetch_agent_job_status(request)


def get_fetch_agent_job_status(request: FetchAgentOutputRequest) -> Dict:
    job = FetchAgentOutputBackgroundJob(request)
    return job.get_status_snapshot().get_status_as_dict()[job.get_job_id()]


@gui_background_job.job_registry.register
class FetchAgentOutputBackgroundJob(watolib.WatoBackgroundJob):
    """The background job is always executed on the site where the host is located on"""
    job_prefix = "agent-output-"

    @classmethod
    def gui_title(cls) -> str:
        return _("Fetch agent output")

    def __init__(self, request: FetchAgentOutputRequest) -> None:
        self._request = request

        host = self._request.host
        job_id = "%s%s-%s-%s" % (self.job_prefix, host.site_id(), host.name(),
                                 self._request.agent_type)
        title = _("Fetching %s of %s / %s") % (self._request.agent_type, host.site_id(),
                                               host.name())
        super(FetchAgentOutputBackgroundJob, self).__init__(job_id, title=title)

        self.set_function(self._fetch_agent_output)

    def _fetch_agent_output(self, job_interface):
        job_interface.send_progress_update(_("Fetching '%s'...") % self._request.agent_type)

        success, output, agent_data = watolib.check_mk_automation(
            self._request.host.site_id(), "get-agent-output",
            [self._request.host.name(), self._request.agent_type])

        if not success:
            job_interface.send_progress_update(_("Failed: %s") % output)

        preview_filepath = os.path.join(job_interface.get_work_dir(),
                                        AgentOutputPage.file_name(self._request))
        store.save_file(preview_filepath, agent_data)

        download_url = makeuri_contextless(
            global_request,
            [("host", self._request.host.name()), ("type", self._request.agent_type)],
            filename="download_agent_output.py",
        )

        button = html.render_icon_button(download_url, _("Download"), "agent_output")
        job_interface.send_progress_update(_("Finished. Click on the icon to download the data."))
        job_interface.send_result_message(_("%s Finished.") % button)


@page_registry.register_page("download_agent_output")
class PageDownloadAgentOutput(AgentOutputPage):
    def page(self) -> None:
        file_name = self.file_name(self._request)
        file_content = self._get_agent_output_file()

        html.set_output_format("text")
        html.response.headers["Content-Disposition"] = "Attachment; filename=%s" % file_name
        html.write_binary(file_content)

    def _get_agent_output_file(self) -> bytes:
        if config.site_is_local(self._request.host.site_id()):
            return get_fetch_agent_output_file(self._request)

        return watolib.do_remote_automation(config.site(self._request.host.site_id()),
                                            "fetch-agent-output-get-file", [
                                                ("request", repr(self._request.serialize())),
                                            ])


@automation_command_registry.register
class AutomationFetchAgentOutputGetFile(ABCAutomationFetchAgentOutput):
    def command_name(self) -> str:
        return "fetch-agent-output-get-file"

    def execute(self, request: FetchAgentOutputRequest) -> bytes:
        return get_fetch_agent_output_file(request)


def get_fetch_agent_output_file(request: FetchAgentOutputRequest) -> bytes:
    job = FetchAgentOutputBackgroundJob(request)
    filepath = Path(job.get_work_dir(), AgentOutputPage.file_name(request))
    # The agent output need to be treated as binary data since each agent section can have an
    # individual encoding
    with filepath.open("rb") as f:
        return f.read()
