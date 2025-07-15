#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Execute an automation call in a background job running on a remote site."""

from __future__ import annotations

import ast
import uuid
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

from pydantic import BaseModel

from cmk.ccc import store  # Some braindead "unit" test monkeypatch this like hell :-/
from cmk.ccc.hostaddress import HostName

from cmk.automations.results import result_type_registry, SerializedResult

from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobRegistry,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobTarget,
)
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import (
    check_mk_local_automation_serialized,
    CheckmkAutomationGetStatusResponse,
    CheckmkAutomationRequest,
    cmk_version_of_remote_automation_source,
    get_local_automation_failure_message,
    MKAutomationException,
    RemoteAutomationGetStatusResponseRaw,
)
from cmk.gui.watolib.host_attributes import CollectedHostAttributes
from cmk.gui.watolib.hosts_and_folders import collect_all_hosts

from .automation_commands import AutomationCommandRegistry


def register(
    job_registry: BackgroundJobRegistry,
    automation_command_registry: AutomationCommandRegistry,
) -> None:
    job_registry.register(CheckmkAutomationBackgroundJob)
    automation_command_registry.register(AutomationCheckmkAutomationGetStatus)
    automation_command_registry.register(AutomationCheckmkAutomationStart)


class AutomationCheckmkAutomationStart(AutomationCommand[CheckmkAutomationRequest]):
    """Called by do_remote_automation_in_background_job to execute the background job on a remote site"""

    def command_name(self) -> str:
        return "checkmk-remote-automation-start"

    def get_request(self) -> CheckmkAutomationRequest:
        return CheckmkAutomationRequest(
            *ast.literal_eval(request.get_ascii_input_mandatory("request"))
        )

    def execute(self, api_request: CheckmkAutomationRequest) -> str:
        automation_id = str(uuid.uuid4())
        job_id = f"{CheckmkAutomationBackgroundJob.job_prefix}{api_request.command}-{automation_id}"
        job = CheckmkAutomationBackgroundJob(job_id)
        if (
            result := job.start(
                JobTarget(
                    callable=checkmk_automation_job_entry_point,
                    args=CheckmkAutomationJobArgs(job_id=job_id, api_request=api_request),
                ),
                InitialStatusArgs(
                    title=_("Checkmk automation %s %s") % (api_request.command, automation_id),
                    user=str(user.id) if user.id else None,
                ),
            )
        ).is_error():
            raise result.error

        return job.get_job_id()


class CheckmkAutomationJobArgs(BaseModel, frozen=True):
    job_id: str
    api_request: CheckmkAutomationRequest


def checkmk_automation_job_entry_point(
    job_interface: BackgroundProcessInterface,
    args: CheckmkAutomationJobArgs,
) -> None:
    job = CheckmkAutomationBackgroundJob(args.job_id)
    job.execute_automation(job_interface, args.api_request, collect_all_hosts)


class AutomationCheckmkAutomationGetStatus(AutomationCommand[str]):
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


class CheckmkAutomationBackgroundJob(BackgroundJob):
    """The background job is always executed on the site where the host is located on"""

    job_prefix = "automation-"

    @classmethod
    def gui_title(cls) -> str:
        return _("Checkmk automation")

    @staticmethod
    def _store_result(
        *,
        path: Path,
        serialized_result: SerializedResult,
        automation_cmd: str,
        cmdline_cmd: Iterable[str],
        debug: bool,
    ) -> None:
        try:
            store.save_text_to_file(
                path,
                result_type_registry[automation_cmd]
                .deserialize(serialized_result)
                .serialize(cmk_version_of_remote_automation_source(request)),
            )
        except SyntaxError as e:
            msg = get_local_automation_failure_message(
                command=automation_cmd,
                cmdline=cmdline_cmd,
                out=serialized_result,
                exc=e,
                debug=debug,
            )
            raise MKAutomationException(msg)

    def execute_automation(
        self,
        job_interface: BackgroundProcessInterface,
        api_request: CheckmkAutomationRequest,
        collect_all_hosts: Callable[[], Mapping[HostName, CollectedHostAttributes]],
    ) -> None:
        with job_interface.gui_context():
            self._execute_automation(job_interface, api_request, collect_all_hosts)

    def _execute_automation(
        self,
        job_interface: BackgroundProcessInterface,
        api_request: CheckmkAutomationRequest,
        collect_all_hosts: Callable[[], Mapping[HostName, CollectedHostAttributes]],
    ) -> None:
        self._logger.info("Starting automation: %s", api_request.command)
        self._logger.debug(api_request)
        cmdline_cmd, serialized_result = check_mk_local_automation_serialized(
            command=api_request.command,
            args=api_request.args,
            indata=api_request.indata,
            stdin_data=api_request.stdin_data,
            timeout=api_request.timeout,
            debug=api_request.debug,
            collect_all_hosts=collect_all_hosts,
        )
        # This file will be read by the get-status request
        self._store_result(
            path=Path(job_interface.get_work_dir()) / "result.mk",
            serialized_result=serialized_result,
            automation_cmd=api_request.command,
            cmdline_cmd=cmdline_cmd,
            debug=api_request.debug,
        )
        job_interface.send_result_message(_("Finished."))
