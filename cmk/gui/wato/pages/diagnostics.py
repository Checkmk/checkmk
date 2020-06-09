#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Optional, List, Tuple

import cmk.utils.paths
from cmk.utils.diagnostics import (
    DiagnosticsParameters,
    serialize_wato_parameters,
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
    OPT_CHECKMK_OVERVIEW,
)
import cmk.utils.version as cmk_version

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import (
    HTTPRedirect,)
import cmk.gui.config as config
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    Filename,
    FixedValue,
    ValueSpec,
)
import cmk.gui.gui_background_job as gui_background_job
from cmk.gui.background_job import BackgroundProcessInterface
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
        self._diagnostics_parameters = self._get_diagnostics_parameters()
        self._job = DiagnosticsDumpBackgroundJob()

    def _get_diagnostics_parameters(self):
        # type: () -> Optional[DiagnosticsParameters]
        if self._start:
            return self._vs_diagnostics().from_html_vars("diagnostics")
        return None

    def title(self):
        # type: () -> str
        return _("Diagnostics")

    def buttons(self):
        # type: () -> None
        home_button()

    def action(self):
        # type: () -> None
        if not html.check_transaction():
            return

        if self._job.is_active() or self._diagnostics_parameters is None:
            raise HTTPRedirect(self._job.detail_url())

        self._job.set_function(self._job.do_execute, self._diagnostics_parameters)
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
        # type: () -> Dictionary
        return Dictionary(
            title=_("Collect diagnostic dump"),
            render="form",
            elements=[
                ("site", DropdownChoice(
                    title=_("Site"),
                    choices=config.get_wato_site_choices(),
                )),
                ("general",
                 FixedValue(True,
                            title=_("General information"),
                            totext=_("Collect information about OS and Checkmk version"),
                            help=_("Collect information about OS, Checkmk version and edition, "
                                   "Time, Core, Python version and paths, Architecture"))),
                ("opt_info",
                 Dictionary(
                     title=_("Optional information"),
                     elements=self._get_optional_information_elements(),
                 )),
            ],
            optional_keys=False,
        )

    def _get_optional_information_elements(self):
        # type: () -> List[Tuple[str, ValueSpec]]
        elements = [
            (OPT_LOCAL_FILES,
             FixedValue(
                 True,
                 totext="",
                 title=_("Local Files"),
                 help=_("List of installed, unpacked, optional files below OMD_ROOT/local. "
                        "This also includes information about installed MKPs."),
             )),
            (OPT_OMD_CONFIG,
             FixedValue(
                 True,
                 totext="",
                 title=_("OMD Config"),
                 help=_("Apache mode and TCP address and port, Core, "
                        "Liveproxy daemon and livestatus TCP mode, "
                        "Event daemon config, Multiste authorisation, "
                        "NSCA mode, TMP filesystem mode"),
             )),
            (OPT_CHECKMK_OVERVIEW,
             FixedValue(
                 True,
                 totext="",
                 title=_("Checkmk Overview"),
                 help=_("Checkmk Agent, Number, version and edition of sites, Cluster host; "
                        "Number of hosts, services, CMK Helper, Live Helper, "
                        "Helper usage; State of daemons: Apache, Core, Crontag, "
                        "DCD, Liveproxyd, MKEventd, MKNotifyd, RRDCached "
                        "(Agent plugin mk_inventory needs to be installed)"),
             )),
        ]  # type: List[Tuple[str, ValueSpec]]

        if not cmk_version.is_raw_edition():
            elements.append(
                (OPT_PERFORMANCE_GRAPHS,
                 FixedValue(
                     True,
                     totext="",
                     title=_("Performance Graphs of Checkmk Server"),
                     help=_("CPU load and utilization, Number of threads, Kernel Performance, "
                            "OMD, Filesystem, Apache Status, TCP Connections of the time ranges "
                            "25 hours and 35 days"),
                 )))
        return elements


@gui_background_job.job_registry.register
class DiagnosticsDumpBackgroundJob(WatoBackgroundJob):
    job_prefix = "diagnostics_dump"

    @classmethod
    def gui_title(cls):
        # type: () -> str
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

    def do_execute(self, diagnostics_parameters, job_interface):
        # type: (DiagnosticsParameters, BackgroundProcessInterface) -> None
        job_interface.send_progress_update(_("Diagnostics dump started..."))

        site = diagnostics_parameters["site"]
        timeout = html.request.request_timeout - 2
        result = check_mk_automation(site,
                                     "create-diagnostics-dump",
                                     args=serialize_wato_parameters(diagnostics_parameters),
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
