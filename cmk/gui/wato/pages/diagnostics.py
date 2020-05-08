#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

if sys.version_info[0] >= 3:
    from pathlib import Path
else:
    from pathlib2 import Path  # pylint: disable=import-error

from typing import (  # pylint: disable=unused-import
    Text, List, Optional,
)
#TODO included in typing since Python >= 3.8
from typing_extensions import TypedDict

import cmk.utils.paths
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import (
    HTTPRedirect,)
import cmk.gui.config as config
from cmk.gui.valuespec import (  # pylint: disable=unused-import
    Dictionary, DropdownChoice, Filename, FixedValue, ListChoice, ValueSpec,
)
import cmk.gui.gui_background_job as gui_background_job
from cmk.gui.background_job import BackgroundProcessInterface  # pylint: disable=unused-import
from cmk.gui.watolib import (
    AutomationCommand,
    automation_command_registry,
    do_remote_automation,
)
from cmk.gui.watolib.wato_background_job import WatoBackgroundJob
from cmk.gui.watolib.automations import check_mk_automation
from cmk.gui.plugins.wato.utils.context_buttons import home_button
from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
)
from cmk.gui.pages import page_registry, Page

DiagnosticsParams = TypedDict("DiagnosticsParams", {
    "site": str,
    "general": None,
    "opt_info": List,
})


@mode_registry.register
class ModeDiagnostics(WatoMode):
    @classmethod
    def name(cls):
        # type: () -> str
        return "diagnostics"

    @classmethod
    def permissions(cls):
        # type : () -> List[str]
        return ["diagnostics"]

    def _from_vars(self):
        # type: () -> None
        self._start = bool(html.request.get_ascii_input("_start"))
        self._diagnostics_params = self._get_diagnostics_params()
        self._job = DiagnosticsDumpBackgroundJob()

    def _get_diagnostics_params(self):
        # type: () -> Optional[DiagnosticsParams]
        if self._start:
            return self._vs_diagnostics().from_html_vars("diagnostics")
        return None

    def title(self):
        # type: () -> Text
        return _("Diagnostics")

    def buttons(self):
        # type: () -> None
        home_button()

    def action(self):
        # type: () -> None
        if not html.check_transaction():
            return

        if self._job.is_active() or self._diagnostics_params is None:
            raise HTTPRedirect(self._job.detail_url())

        self._job.set_function(self._job.do_execute, self._diagnostics_params)
        self._job.start()

        raise HTTPRedirect(self._job.detail_url())

    def page(self):
        # type: () -> None
        job_status_snapshot = self._job.get_status_snapshot()
        if job_status_snapshot.is_active():
            raise HTTPRedirect(self._job.detail_url())

        html.begin_form("diagnostics", method="POST")

        vs_diagnostics = self._vs_diagnostics()
        vs_diagnostics.render_input("diagnostics", {})

        html.button("_start", _("Start"))
        html.hidden_fields()
        html.end_form()

    def _vs_diagnostics(self):
        # type: () -> ValueSpec
        return Dictionary(
            title=_("Collect diagnostic dump"),
            render="form",
            elements=[
                ("site", DropdownChoice(
                    title=_("Site"),
                    choices=config.get_wato_site_choices(),
                )),
                ("general",
                 FixedValue(None,
                            totext=_("Collect information about OS and Checkmk version"),
                            title=_("General information"))),
                ("opt_info", ListChoice(
                    title=_("Optional information"),
                    choices=[],
                )),
            ],
            optional_keys=False,
        )


@gui_background_job.job_registry.register
class DiagnosticsDumpBackgroundJob(WatoBackgroundJob):
    job_prefix = "diagnostics_dump"

    @classmethod
    def gui_title(cls):
        # type: () -> Text
        return _("Diagnostics dump")

    def __init__(self):
        # type: () -> None
        super(DiagnosticsDumpBackgroundJob, self).__init__(
            self.job_prefix,
            title=self.gui_title(),
            lock_wato=False,
            stoppable=False,
        )

    def _back_url(self):
        # type: () -> str
        return html.makeuri([])

    def do_execute(self, diagnostics_params, job_interface):
        # type: (DiagnosticsParams, BackgroundProcessInterface) -> None
        job_interface.send_progress_update(_("Diagnostics dump started..."))

        site = diagnostics_params["site"]
        timeout = html.request.request_timeout - 2
        result = check_mk_automation(site,
                                     "create-diagnostics-dump",
                                     timeout=timeout,
                                     non_blocking_http=True)

        job_interface.send_progress_update(result["output"])

        tarfile_path = result['tarfile_path']
        download_url = html.makeuri_contextless([("site", site),
                                                 ("tarfile_name", str(Path(tarfile_path)))],
                                                "download_diagnostics_dump.py")
        button = html.render_icon_button(download_url, _("Download"), "diagnostics_dump_file")

        job_interface.send_progress_update(_("Dump file: %s") % tarfile_path)
        job_interface.send_result_message(_("%s Creating dump file successfully") % button)


@page_registry.register_page("download_diagnostics_dump")
class PageDownloadDiagnosticsDump(Page):
    def page(self):
        # type: () -> None
        site = html.request.get_ascii_input_mandatory("site")
        tarfile_name = html.request.get_ascii_input_mandatory("tarfile_name")
        Filename().validate_value(tarfile_name, "tarfile_name")
        file_content = self._get_diagnostics_dump_file(site, tarfile_name)

        html.set_output_format("x-tgz")
        html.response.headers["Content-Disposition"] = "Attachment; filename=%s" % tarfile_name
        html.write_binary(file_content)

    def _get_diagnostics_dump_file(self, site, tarfile_name):
        # type: (str, str) -> bytes
        if config.site_is_local(site):
            return _get_diagnostics_dump_file(tarfile_name)

        return do_remote_automation(config.site(site), "diagnostics-dump-get-file", [
            ("tarfile_name", tarfile_name),
        ])


@automation_command_registry.register
class AutomationDiagnosticsDumpGetFile(AutomationCommand):
    def command_name(self):
        # type: () -> str
        return "diagnostics-dump-get-file"

    def execute(self, request):
        # type: (str) -> bytes
        return _get_diagnostics_dump_file(request)

    def get_request(self):
        # type: () -> str
        tarfile_name = html.request.get_ascii_input_mandatory("tarfile_name")
        Filename().validate_value(tarfile_name, "tarfile_name")
        return tarfile_name


def _get_diagnostics_dump_file(tarfile_name):
    # type: (str) -> bytes
    with cmk.utils.paths.diagnostics_dir.joinpath(tarfile_name).open("rb") as f:
        return f.read()
