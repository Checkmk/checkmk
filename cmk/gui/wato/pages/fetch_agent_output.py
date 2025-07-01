#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import ast
from pathlib import Path

from pydantic import BaseModel

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException, MKTimeout
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import omd_site, SiteId

from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobRegistry,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobStatusSpec,
    JobTarget,
)
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import active_config, Config
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.gui_background_job import ActionHandler, JobRenderer
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html, HTMLGenerator
from cmk.gui.http import ContentDispositionType, request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import Page, PageEndpoint, PageRegistry
from cmk.gui.theme import make_theme
from cmk.gui.utils.escaping import escape_attribute
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.view_breadcrumbs import make_host_breadcrumb
from cmk.gui.watolib.automation_commands import AutomationCommand, AutomationCommandRegistry
from cmk.gui.watolib.automations import (
    AnnotatedHostName,
    do_remote_automation,
    LocalAutomationConfig,
    make_automation_config,
    RemoteAutomationConfig,
)
from cmk.gui.watolib.check_mk_automations import get_agent_output
from cmk.gui.watolib.hosts_and_folders import folder_from_request, Host
from cmk.gui.watolib.mode import mode_url


def register(
    page_registry: PageRegistry,
    automation_command_registry: AutomationCommandRegistry,
    job_registry: BackgroundJobRegistry,
) -> None:
    page_registry.register(PageEndpoint("fetch_agent_output", PageFetchAgentOutput))
    page_registry.register(PageEndpoint("download_agent_output", PageDownloadAgentOutput))
    automation_command_registry.register(AutomationFetchAgentOutputStart)
    automation_command_registry.register(AutomationFetchAgentOutputGetStatus)
    automation_command_registry.register(AutomationFetchAgentOutputGetFile)
    job_registry.register(FetchAgentOutputBackgroundJob)


# .
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
#       wato.py? The only reason is because the Setup automation is used. Move
#       to better location.


class FetchAgentOutputRequest:
    def __init__(self, host: Host, agent_type: str) -> None:
        self.host = host
        self.agent_type = agent_type

    @classmethod
    def deserialize(cls, serialized: dict[str, str]) -> "FetchAgentOutputRequest":
        host_name = serialized["host_name"]
        host = Host.host(HostName(host_name))
        if host is None:
            raise MKGeneralException(
                _(
                    "Host %s does not exist on remote site %s. This "
                    "may be caused by a failed configuration synchronization. Have a look at "
                    'the <a href="wato.py?folder=&mode=changelog">activate changes page</a> '
                    "for further information."
                )
                % (host_name, omd_site())
            )
        host.permissions.need_permission("read")

        return cls(host, serialized["agent_type"])

    def serialize(self) -> dict[str, str]:
        return {
            "host_name": self.host.name(),
            "agent_type": self.agent_type,
        }


# TODO: Better use AjaxPage.handle_page() for standard AJAX call error handling. This
# would need larger refactoring of the generic html.popup_trigger() mechanism.
class AgentOutputPage(Page, abc.ABC):
    def __init__(self) -> None:
        super().__init__()
        self._from_vars()

    def _from_vars(self) -> None:
        user.need_permission("wato.download_agent_output")

        host_name = request.var("host")
        if not host_name:
            raise MKGeneralException(_("The host is missing."))

        ty = request.var("type")
        if ty not in ["walk", "agent"]:
            raise MKGeneralException(_("Invalid type specified."))

        self._back_url = request.get_url_input("back_url", deflt="") or None

        host = folder_from_request(request.var("folder"), host_name).host(HostName(host_name))
        if not host:
            raise MKGeneralException(
                _('Host is not managed by Setup. Click <a href="%s">here</a> to go back.')
                % escape_attribute(self._back_url)
            )
        host.permissions.need_permission("read")

        self._request = FetchAgentOutputRequest(host=host, agent_type=ty)

    @staticmethod
    def file_name(site_id: SiteId, host_name: HostName, agent_type: str) -> str:
        return f"{site_id}-{host_name}-{agent_type}.txt"


class PageFetchAgentOutput(AgentOutputPage):
    def page(self, config: Config) -> None:
        title = self._title()
        make_header(html, title, self._breadcrumb(title))

        self._action()

        automation_config = make_automation_config(config.sites[self._request.host.site_id()])
        if request.has_var("_start"):
            self._start_fetch(automation_config, debug=config.debug)
        self._show_status(automation_config, debug=config.debug)

        html.footer()

    def _title(self) -> str:
        return _("%s: Download agent output") % self._request.host.name()

    def _breadcrumb(self, title: str) -> Breadcrumb:
        breadcrumb = make_host_breadcrumb(self._request.host.name())
        breadcrumb.append(
            BreadcrumbItem(
                title=title,
                url="javascript:document.location.reload(false)",
            )
        )
        return breadcrumb

    def _action(self) -> None:
        if not transactions.transaction_valid():
            return

        action_handler = ActionHandler(self._breadcrumb(self._title()))

        if action_handler.handle_actions() and action_handler.did_delete_job():
            raise HTTPRedirect(
                makeuri_contextless(
                    request,
                    [
                        ("host", self._request.host.name()),
                        ("type", self._request.agent_type),
                        ("back_url", self._back_url),
                    ],
                )
            )

    def _show_status(
        self, automation_config: LocalAutomationConfig | RemoteAutomationConfig, *, debug: bool
    ) -> None:
        job_status = self._get_job_status(automation_config, debug=debug)

        html.h3(_("Job status"))
        if job_status.is_active:
            html.immediate_browser_redirect(0.8, makeuri(request, []))

        job = FetchAgentOutputBackgroundJob.from_api_request(self._request)
        JobRenderer.show_job_details(job.get_job_id(), job_status, job.may_stop(), job.may_delete())

    def _start_fetch(
        self, automation_config: LocalAutomationConfig | RemoteAutomationConfig, *, debug: bool
    ) -> None:
        """Start the job on the site the host is monitored by"""
        if isinstance(automation_config, LocalAutomationConfig):
            start_fetch_agent_job(self._request)
            return

        do_remote_automation(
            automation_config,
            "fetch-agent-output-start",
            [
                ("request", repr(self._request.serialize())),
            ],
            debug=debug,
        )

    def _get_job_status(
        self, automation_config: LocalAutomationConfig | RemoteAutomationConfig, *, debug: bool
    ) -> JobStatusSpec:
        if isinstance(automation_config, LocalAutomationConfig):
            return get_fetch_agent_job_status(self._request)

        return JobStatusSpec.model_validate(
            do_remote_automation(
                automation_config,
                "fetch-agent-output-get-status",
                [
                    ("request", repr(self._request.serialize())),
                ],
                debug=debug,
            )
        )


class ABCAutomationFetchAgentOutput(AutomationCommand[FetchAgentOutputRequest]):
    def get_request(self) -> FetchAgentOutputRequest:
        user.need_permission("wato.download_agent_output")

        ascii_input = request.get_ascii_input("request")
        if ascii_input is None:
            raise MKUserError("request", _('The parameter "%s" is missing.') % "request")
        return FetchAgentOutputRequest.deserialize(ast.literal_eval(ascii_input))


class AutomationFetchAgentOutputStart(ABCAutomationFetchAgentOutput):
    """Is called by AgentOutputPage._start_fetch() to execute the background job on a remote site"""

    def command_name(self) -> str:
        return "fetch-agent-output-start"

    def execute(self, api_request: FetchAgentOutputRequest) -> None:
        start_fetch_agent_job(api_request)


def start_fetch_agent_job(api_request: FetchAgentOutputRequest) -> None:
    job = FetchAgentOutputBackgroundJob.from_api_request(api_request)
    if (
        result := job.start(
            JobTarget(
                callable=fetch_agent_output_entry_point,
                args=FetchAgentOutputJobArgs(
                    site_id=api_request.host.site_id(),
                    host_name=api_request.host.name(),
                    agent_type=api_request.agent_type,
                ),
            ),
            InitialStatusArgs(
                title=_("Fetching %s of %s / %s")
                % (
                    api_request.agent_type,
                    api_request.host.site_id(),
                    api_request.host.name(),
                ),
                user=str(user.id) if user.id else None,
            ),
        )
    ).is_error():
        raise MKUserError(None, str(result.error))


class AutomationFetchAgentOutputGetStatus(ABCAutomationFetchAgentOutput):
    """Is called by AgentOutputPage._get_job_status() to execute the background job on a remote site"""

    def command_name(self) -> str:
        return "fetch-agent-output-get-status"

    def execute(self, api_request: FetchAgentOutputRequest) -> dict:
        return dict(get_fetch_agent_job_status(api_request))


def get_fetch_agent_job_status(api_request: FetchAgentOutputRequest) -> JobStatusSpec:
    job = FetchAgentOutputBackgroundJob.from_api_request(api_request)
    return job.get_status_snapshot().status


class FetchAgentOutputJobArgs(BaseModel, frozen=True):
    site_id: SiteId
    host_name: AnnotatedHostName
    agent_type: str


def fetch_agent_output_entry_point(
    job_interface: BackgroundProcessInterface, args: FetchAgentOutputJobArgs
) -> None:
    FetchAgentOutputBackgroundJob(args.site_id, args.host_name, args.agent_type).fetch_agent_output(
        job_interface
    )


class FetchAgentOutputBackgroundJob(BackgroundJob):
    """The background job is always executed on the site where the host is located on"""

    job_prefix = "agent-output-"

    @classmethod
    def from_api_request(
        cls, api_request: FetchAgentOutputRequest
    ) -> "FetchAgentOutputBackgroundJob":
        return cls(api_request.host.site_id(), api_request.host.name(), api_request.agent_type)

    @classmethod
    def gui_title(cls) -> str:
        return _("Fetch agent output")

    def __init__(self, site_id: SiteId, host_name: HostName, agent_type: str) -> None:
        self._site_id = site_id
        self._host_name = host_name
        self._agent_type = agent_type
        job_id = f"{self.job_prefix}{site_id}-{host_name}-{agent_type}"
        super().__init__(job_id)

    def fetch_agent_output(self, job_interface: BackgroundProcessInterface) -> None:
        with job_interface.gui_context():
            self._fetch_agent_output(
                job_interface,
                automation_config=make_automation_config(active_config.sites[self._site_id]),
                debug=active_config.debug,
            )

    def _fetch_agent_output(
        self,
        job_interface: BackgroundProcessInterface,
        *,
        automation_config: LocalAutomationConfig | RemoteAutomationConfig,
        debug: bool,
    ) -> None:
        job_interface.send_progress_update(_("Fetching '%s'...") % self._agent_type)

        agent_output_result = get_agent_output(
            automation_config,
            self._host_name,
            self._agent_type,
            timeout=int(active_config.reschedule_timeout)
            if self._agent_type == "agent"
            else int(active_config.snmp_walk_download_timeout),
            debug=debug,
        )

        if not agent_output_result.success:
            global_setting_name = (
                "reschedule_timeout"
                if self._agent_type == "agent"
                else "snmp_walk_download_timeout"
            )
            job_interface.send_progress_update(
                _("Failed: %s") % agent_output_result.service_details
            )
            if agent_output_result.service_details.find("timed out"):
                url = mode_url("edit_configvar", varname=global_setting_name)
                result = (
                    _("Background job timed out due to the global setting ")
                    + f"'<a href=\"{url}\">{global_setting_name}</a>'. "
                    + _("%s Click on the icon to review.")
                    % HTMLGenerator.render_icon_button(
                        url=url,
                        title=_("Global setting '%s'") % global_setting_name,
                        icon="configuration",
                        theme=make_theme(validate_choices=False),
                    )
                )

                job_interface.send_result_message(result)

                raise MKTimeout
            raise MKGeneralException()

        preview_filepath = Path(job_interface.get_work_dir()) / AgentOutputPage.file_name(
            self._site_id, self._host_name, self._agent_type
        )

        store.save_bytes_to_file(
            preview_filepath,
            agent_output_result.raw_agent_data,
        )

        download_url = makeuri_contextless(
            request,
            [("host", self._host_name), ("type", self._agent_type)],
            filename="download_agent_output.py",
        )

        job_interface.send_progress_update("Job finished.")
        job_interface.send_result_message(
            _("%s Click on the icon to download the agent output.")
            % HTMLGenerator.render_icon_button(
                url=download_url,
                title=_("Download"),
                icon="agent_output",
                theme=make_theme(validate_choices=False),
            )
        )


class PageDownloadAgentOutput(AgentOutputPage):
    def page(self, config: Config) -> None:
        file_name = self.file_name(
            self._request.host.site_id(), self._request.host.name(), self._request.agent_type
        )
        file_content = self._get_agent_output_file(
            automation_config=make_automation_config(
                active_config.sites[self._request.host.site_id()]
            )
        )

        response.set_content_type("text/plain")
        response.set_content_disposition(ContentDispositionType.ATTACHMENT, file_name)
        response.set_data(file_content)

    def _get_agent_output_file(
        self, automation_config: LocalAutomationConfig | RemoteAutomationConfig
    ) -> bytes:
        if isinstance(automation_config, LocalAutomationConfig):
            return get_fetch_agent_output_file(self._request)

        raw_response = do_remote_automation(
            automation_config,
            "fetch-agent-output-get-file",
            [
                ("request", repr(self._request.serialize())),
            ],
            debug=active_config.debug,
        )
        assert isinstance(raw_response, bytes)
        return raw_response


class AutomationFetchAgentOutputGetFile(ABCAutomationFetchAgentOutput):
    def command_name(self) -> str:
        return "fetch-agent-output-get-file"

    def execute(self, api_request: FetchAgentOutputRequest) -> bytes:
        return get_fetch_agent_output_file(api_request)


def get_fetch_agent_output_file(api_request: FetchAgentOutputRequest) -> bytes:
    job = FetchAgentOutputBackgroundJob.from_api_request(api_request)
    filepath = Path(
        job.get_work_dir(),
        AgentOutputPage.file_name(
            api_request.host.site_id(), api_request.host.name(), api_request.agent_type
        ),
    )
    # The agent output need to be treated as binary data since each agent section can have an
    # individual encoding
    with filepath.open("rb") as f:
        return f.read()
