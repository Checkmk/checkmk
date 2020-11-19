#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Optional, List, Tuple

import cmk.utils.paths
from cmk.utils.diagnostics import (
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
    OPT_CHECKMK_OVERVIEW,
    OPT_CHECKMK_CONFIG_FILES,
    OPT_COMP_GLOBAL_SETTINGS,
    OPT_COMP_HOSTS_AND_FOLDERS,
    OPT_COMP_NOTIFICATIONS,
    DiagnosticsParameters,
    serialize_wato_parameters,
    get_checkmk_config_files_map,
    get_checkmk_log_files_map,
    CheckmkFileInfo,
    CheckmkFileSensitivity,
    get_checkmk_file_sensitivity_for_humans,
    get_checkmk_file_info,
)
import cmk.utils.version as cmk_version

from cmk.gui.i18n import _
from cmk.gui.globals import html, request as global_request
from cmk.gui.exceptions import (
    HTTPRedirect,)
import cmk.gui.config as config
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    Filename,
    FixedValue,
    ValueSpec,
    CascadingDropdown,
    CascadingDropdownChoice,
    DualListChoice,
    ListOf,
)
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    make_simple_link,
    make_simple_form_page_menu,
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
from cmk.gui.plugins.wato import (
    WatoMode,
    ActionResult,
    mode_registry,
    redirect,
)
from cmk.gui.pages import page_registry, Page

from cmk.gui.utils.urls import makeuri, makeuri_contextless

_CHECKMK_FILES_NOTE = _("<br>Note: Some files may contain highly sensitive data like"
                        " passwords. These files are marked with '!'."
                        " Other files may include IP adresses, hostnames, usernames,"
                        " mail adresses or phone numbers and are marked with '?'."
                        " Files with '-' are not classified yet.")


@mode_registry.register
class ModeDiagnostics(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "diagnostics"

    @classmethod
    def permissions(cls) -> List[str]:
        return ["diagnostics"]

    def _from_vars(self) -> None:
        self._checkmk_config_files_map = get_checkmk_config_files_map()
        self._checkmk_log_files_map = get_checkmk_log_files_map()
        self._collect_dump = bool(html.request.get_ascii_input("_collect_dump"))
        self._diagnostics_parameters = self._get_diagnostics_parameters()
        self._job = DiagnosticsDumpBackgroundJob()

    def _get_diagnostics_parameters(self) -> Optional[DiagnosticsParameters]:
        if self._collect_dump:
            return self._vs_diagnostics().from_html_vars("diagnostics")
        return None

    def title(self) -> str:
        return _("Support diagnostics")

    def page_menu(self, breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(breadcrumb,
                                          form_name="diagnostics",
                                          button_name="_collect_dump",
                                          save_title=_("Collect dump"))
        menu.dropdowns.insert(
            1,
            PageMenuDropdown(
                name="related",
                title=_("Related"),
                topics=[
                    PageMenuTopic(
                        title=_("Setup"),
                        entries=[
                            PageMenuEntry(
                                title=_("Analyze configuration"),
                                icon_name="analyze_config",
                                item=make_simple_link("wato.py?mode=analyze_config"),
                            ),
                        ],
                    ),
                ],
            ))
        return menu

    def action(self) -> ActionResult:
        if not html.check_transaction():
            return None

        if self._job.is_active() or self._diagnostics_parameters is None:
            return redirect(self._job.detail_url())

        self._job.set_function(self._job.do_execute, self._diagnostics_parameters)
        self._job.start()

        return redirect(self._job.detail_url())

    def page(self) -> None:
        job_status_snapshot = self._job.get_status_snapshot()
        if job_status_snapshot.is_active():
            raise HTTPRedirect(self._job.detail_url())

        html.begin_form("diagnostics", method="POST")

        vs_diagnostics = self._vs_diagnostics()
        vs_diagnostics.render_input("diagnostics", {})

        html.hidden_fields()
        html.end_form()

    def _vs_diagnostics(self) -> Dictionary:
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
                ("comp_specific",
                 ListOf(
                     title=_("Component specific information"),
                     valuespec=CascadingDropdown(choices=self._get_component_specific_choices()),
                 )),
            ],
            optional_keys=False,
        )

    def _get_optional_information_elements(self) -> List[Tuple[str, ValueSpec]]:
        elements: List[Tuple[str, ValueSpec]] = [
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
            (OPT_CHECKMK_CONFIG_FILES,
             self._get_component_specific_checkmk_files_choices(
                 "Checkmk Configuration files",
                 [(f, get_checkmk_file_info(f)) for f in self._checkmk_config_files_map])),
        ]

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

    def _get_component_specific_choices(self) -> List[CascadingDropdownChoice]:
        elements: List[CascadingDropdownChoice] = [
            (OPT_COMP_GLOBAL_SETTINGS, _("Global Settings"),
             Dictionary(
                 help=_("Configuration files ('*.mk' or '*.conf') from etc/check_mk.%s" %
                        _CHECKMK_FILES_NOTE),
                 elements=self._get_component_specific_checkmk_files_elements(
                     OPT_COMP_GLOBAL_SETTINGS),
                 default_keys=["config_files"],
             )),
            (OPT_COMP_HOSTS_AND_FOLDERS, _("Hosts and Folders"),
             Dictionary(
                 help=_("Configuration files ('*.mk' or '*.conf') from etc/check_mk.%s" %
                        _CHECKMK_FILES_NOTE),
                 elements=self._get_component_specific_checkmk_files_elements(
                     OPT_COMP_HOSTS_AND_FOLDERS),
                 default_keys=["config_files"],
             )),
            (OPT_COMP_NOTIFICATIONS, _("Notifications"),
             Dictionary(
                 help=_("Configuration files ('*.mk' or '*.conf') from etc/check_mk"
                        " or log files ('*.log' or '*.state') from var/log.%s" %
                        _CHECKMK_FILES_NOTE),
                 elements=self._get_component_specific_checkmk_files_elements(
                     OPT_COMP_NOTIFICATIONS),
                 default_keys=["config_files"],
             )),
        ]
        return elements

    def _get_component_specific_checkmk_files_elements(
        self,
        component,
    ) -> List[Tuple[str, ValueSpec]]:
        elements = []
        config_files = [(f, fi)
                        for f in self._checkmk_config_files_map
                        for fi in [get_checkmk_file_info(f, component)]
                        if component in fi.components]
        if config_files:
            elements.append(
                ("config_files",
                 self._get_component_specific_checkmk_files_choices("Configuration files",
                                                                    config_files)))

        log_files = [(f, fi)
                     for f in self._checkmk_log_files_map
                     for fi in [get_checkmk_file_info(f, component)]
                     if component in fi.components]
        if log_files:
            elements.append(
                ("log_files",
                 self._get_component_specific_checkmk_files_choices("Log files", log_files)))
        return elements

    def _get_component_specific_checkmk_files_choices(
        self,
        title: str,
        checkmk_files: List[Tuple[str, CheckmkFileInfo]],
    ) -> ValueSpec:
        high_sensitive_files = []
        sensitive_files = []
        insensitive_files = []
        for rel_filepath, file_info in checkmk_files:
            if file_info.sensitivity == CheckmkFileSensitivity.high_sensitive:
                high_sensitive_files.append((rel_filepath, file_info))
            elif file_info.sensitivity == CheckmkFileSensitivity.sensitive:
                sensitive_files.append((rel_filepath, file_info))
            else:
                insensitive_files.append((rel_filepath, file_info))

        sorted_files = sorted(high_sensitive_files + sensitive_files + insensitive_files,
                              key=lambda t: t[0])
        sorted_non_high_sensitive_files = sorted(sensitive_files + insensitive_files,
                                                 key=lambda t: t[0])
        sorted_insensitive_files = sorted(insensitive_files, key=lambda t: t[0])
        return CascadingDropdown(
            title=_(title),
            choices=[
                ("all", _("Pack all files"),
                 FixedValue(
                     [f for f, fi in sorted_files],
                     totext=self._list_of_files_to_text(sorted_files),
                 )),
                ("non_high_sensitive", _("Pack sensitive and insensitive files"),
                 FixedValue(
                     [f for f, fi in sorted_non_high_sensitive_files],
                     totext=self._list_of_files_to_text(sorted_non_high_sensitive_files),
                 )),
                ("insensitive", _("Pack only insensitive files"),
                 FixedValue(
                     [f for f, fi in sorted_insensitive_files],
                     totext=self._list_of_files_to_text(sorted_insensitive_files),
                 )),
                ("explicit_list_of_files", _("Explicit list of files"),
                 DualListChoice(
                     choices=self._list_of_files_choices(sorted_files),
                     size=80,
                     rows=10,
                 )),
            ],
            default_value="non_high_sensitive",
        )

    def _list_of_files_to_text(self, list_of_files: List[Tuple[str, CheckmkFileInfo]]) -> str:
        return "<br>%s" % ",<br>".join([
            get_checkmk_file_sensitivity_for_humans(rel_filepath, file_info)
            for rel_filepath, file_info in list_of_files
        ])

    def _list_of_files_choices(
        self,
        files: List[Tuple[str, CheckmkFileInfo]],
    ) -> List[Tuple[str, str]]:
        return [(rel_filepath, get_checkmk_file_sensitivity_for_humans(rel_filepath, file_info))
                for rel_filepath, file_info in files]


@gui_background_job.job_registry.register
class DiagnosticsDumpBackgroundJob(WatoBackgroundJob):
    job_prefix = "diagnostics_dump"

    @classmethod
    def gui_title(cls) -> str:
        return _("Diagnostics dump")

    def __init__(self) -> None:
        super(DiagnosticsDumpBackgroundJob, self).__init__(
            self.job_prefix,
            title=self.gui_title(),
            lock_wato=False,
            stoppable=False,
        )

    def _back_url(self) -> str:
        return makeuri(global_request, [])

    def do_execute(self, diagnostics_parameters: DiagnosticsParameters,
                   job_interface: BackgroundProcessInterface) -> None:
        job_interface.send_progress_update(_("Diagnostics dump started..."))

        site = diagnostics_parameters["site"]
        timeout = html.request.request_timeout - 2
        result = check_mk_automation(site,
                                     "create-diagnostics-dump",
                                     args=serialize_wato_parameters(diagnostics_parameters),
                                     timeout=timeout,
                                     non_blocking_http=True)

        job_interface.send_progress_update(result["output"])

        if result["tarfile_created"]:
            tarfile_path = result['tarfile_path']
            download_url = makeuri_contextless(
                global_request,
                [("site", site), ("tarfile_name", str(Path(tarfile_path)))],
                filename="download_diagnostics_dump.py",
            )
            button = html.render_icon_button(download_url, _("Download"), "diagnostics_dump_file")

            job_interface.send_progress_update(_("Dump file: %s") % tarfile_path)
            job_interface.send_result_message(_("%s Creating dump file successfully") % button)

        else:
            job_interface.send_result_message(_("Creating dump file failed"))


@page_registry.register_page("download_diagnostics_dump")
class PageDownloadDiagnosticsDump(Page):
    def page(self) -> None:
        site = html.request.get_ascii_input_mandatory("site")
        tarfile_name = html.request.get_ascii_input_mandatory("tarfile_name")
        Filename().validate_value(tarfile_name, "tarfile_name")
        file_content = self._get_diagnostics_dump_file(site, tarfile_name)

        html.set_output_format("x-tgz")
        html.response.headers["Content-Disposition"] = "Attachment; filename=%s" % tarfile_name
        html.write_binary(file_content)

    def _get_diagnostics_dump_file(self, site: str, tarfile_name: str) -> bytes:
        if config.site_is_local(site):
            return _get_diagnostics_dump_file(tarfile_name)

        return do_remote_automation(config.site(site), "diagnostics-dump-get-file", [
            ("tarfile_name", tarfile_name),
        ])


@automation_command_registry.register
class AutomationDiagnosticsDumpGetFile(AutomationCommand):
    def command_name(self) -> str:
        return "diagnostics-dump-get-file"

    def execute(self, request: str) -> bytes:
        return _get_diagnostics_dump_file(request)

    def get_request(self) -> str:
        tarfile_name = html.request.get_ascii_input_mandatory("tarfile_name")
        Filename().validate_value(tarfile_name, "tarfile_name")
        return tarfile_name


def _get_diagnostics_dump_file(tarfile_name: str) -> bytes:
    with cmk.utils.paths.diagnostics_dir.joinpath(tarfile_name).open("rb") as f:
        return f.read()
