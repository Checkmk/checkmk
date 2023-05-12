#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import tarfile
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils.diagnostics import (
    CheckmkFileInfo,
    CheckmkFileSensitivity,
    DiagnosticsParameters,
    get_checkmk_config_files_map,
    get_checkmk_core_files_map,
    get_checkmk_file_description,
    get_checkmk_file_info,
    get_checkmk_file_sensitivity_for_humans,
    get_checkmk_log_files_map,
    OPT_CHECKMK_CONFIG_FILES,
    OPT_CHECKMK_LOG_FILES,
    OPT_CHECKMK_OVERVIEW,
    OPT_COMP_BUSINESS_INTELLIGENCE,
    OPT_COMP_CMC,
    OPT_COMP_GLOBAL_SETTINGS,
    OPT_COMP_HOSTS_AND_FOLDERS,
    OPT_COMP_NOTIFICATIONS,
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
    serialize_wato_parameters,
)

import cmk.gui.config as config
import cmk.gui.gui_background_job as gui_background_job
from cmk.gui.background_job import BackgroundProcessInterface
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKUserError
from cmk.gui.globals import html
from cmk.gui.globals import request as global_request
from cmk.gui.i18n import _
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import Page, page_registry
from cmk.gui.plugins.wato import mode_registry, redirect, WatoMode
from cmk.gui.type_defs import ActionResult
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DualListChoice,
    FixedValue,
    ValueSpec,
)
from cmk.gui.watolib import automation_command_registry, AutomationCommand, do_remote_automation
from cmk.gui.watolib.automations import check_mk_automation
from cmk.gui.watolib.wato_background_job import WatoBackgroundJob

_CHECKMK_FILES_NOTE = _("<br>Note: Some files may contain highly sensitive data like"
                        " passwords. These files are marked with 'H'."
                        " Other files may include IP adresses, hostnames, usernames,"
                        " mail adresses or phone numbers and are marked with 'M'.")


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
        self._checkmk_core_files_map = get_checkmk_core_files_map()
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
        menu = make_simple_form_page_menu(_("Diagnostics"),
                                          breadcrumb,
                                          form_name="diagnostics",
                                          button_name="_collect_dump",
                                          save_title=_("Collect diagnostics"))
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
            help="File Descriptions:<br>%s" %
            "<br>".join([" - %s: %s" % (f, d) for (f, d) in get_checkmk_file_description()]),
            elements=[
                ("site",
                 FixedValue(
                     value=True,
                     title=_("Site"),
                     totext=config.omd_site(),
                     help=_("Collect diagnostics data from the local site."),
                 )),
                ("general",
                 FixedValue(True,
                            title=_("General information"),
                            totext=_("Collect information about OS and Checkmk version"),
                            help=_("Collect information about OS, Checkmk version and edition, "
                                   "Time, Core, Python version and paths, Architecture"))),
                ("opt_info",
                 Dictionary(
                     title=_("Optional general information"),
                     elements=self._get_optional_information_elements(),
                 )),
                ("comp_specific",
                 Dictionary(
                     title=_("Component specific information"),
                     elements=self._get_component_specific_elements(),
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
            (OPT_CHECKMK_LOG_FILES,
             self._get_component_specific_checkmk_files_choices(
                 "Checkmk Log files",
                 [(f, get_checkmk_file_info(f)) for f in self._checkmk_log_files_map])),
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

    def _get_component_specific_elements(self) -> List[Tuple[str, ValueSpec]]:
        elements: List[Tuple[str, ValueSpec]] = [
            (OPT_COMP_GLOBAL_SETTINGS,
             Dictionary(
                 title=_("Global Settings"),
                 help=_("Configuration files ('*.mk' or '*.conf') from etc/check_mk.%s" %
                        _CHECKMK_FILES_NOTE),
                 elements=self._get_component_specific_checkmk_files_elements(
                     OPT_COMP_GLOBAL_SETTINGS),
                 default_keys=["config_files"],
             )),
            (OPT_COMP_HOSTS_AND_FOLDERS,
             Dictionary(
                 title=_("Hosts and Folders"),
                 help=_("Configuration files ('*.mk' or '*.conf') from etc/check_mk.%s" %
                        _CHECKMK_FILES_NOTE),
                 elements=self._get_component_specific_checkmk_files_elements(
                     OPT_COMP_HOSTS_AND_FOLDERS),
                 default_keys=["config_files"],
             )),
            (OPT_COMP_NOTIFICATIONS,
             Dictionary(
                 title=_("Notifications"),
                 help=_("Configuration files ('*.mk' or '*.conf') from etc/check_mk"
                        " or log files ('*.log' or '*.state') from var/log.%s" %
                        _CHECKMK_FILES_NOTE),
                 elements=self._get_component_specific_checkmk_files_elements(
                     OPT_COMP_NOTIFICATIONS),
                 default_keys=["config_files"],
             )),
            (OPT_COMP_BUSINESS_INTELLIGENCE,
             Dictionary(
                 title=_("Business Intelligence"),
                 help=_("Configuration files ('*.bi') from etc/check_mk.%s" % _CHECKMK_FILES_NOTE),
                 elements=self._get_component_specific_checkmk_files_elements(
                     OPT_COMP_BUSINESS_INTELLIGENCE),
                 default_keys=["config_files"],
             )),
        ]

        if not cmk_version.is_raw_edition():
            elements.append((
                OPT_COMP_CMC,
                Dictionary(
                    title=_("CMC (Checkmk Microcore)"),
                    help=_("Core files (config, state and history) from var/check_mk/core.%s") %
                    _CHECKMK_FILES_NOTE,
                    elements=self._get_component_specific_checkmk_files_elements(OPT_COMP_CMC,),
                    default_keys=["core_files"],
                ),
            ))
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
            elements.append((
                "config_files",
                self._get_component_specific_checkmk_files_choices(_("Configuration files"),
                                                                   config_files),
            ))

        core_files = [(f, fi)
                      for f in self._checkmk_core_files_map
                      for fi in [get_checkmk_file_info(f, component)]
                      if component in fi.components]
        if core_files:
            elements.append((
                "core_files",
                self._get_component_specific_checkmk_files_choices(_("Core files"), core_files),
            ))

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
            sorted=False,
            choices=[
                ("all", _("Pack all files: High, Medium, Low sensitivity"),
                 FixedValue(
                     [f for f, fi in sorted_files],
                     totext=self._list_of_files_to_text(sorted_files),
                 )),
                ("non_high_sensitive", _("Pack only Medium and Low sensitivity files"),
                 FixedValue(
                     [f for f, fi in sorted_non_high_sensitive_files],
                     totext=self._list_of_files_to_text(sorted_non_high_sensitive_files),
                 )),
                ("insensitive", _("Pack only Low sensitivity files"),
                 FixedValue(
                     [f for f, fi in sorted_insensitive_files],
                     totext=self._list_of_files_to_text(sorted_insensitive_files),
                 )),
                ("explicit_list_of_files", _("Select individual files from list"),
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

        chunks = serialize_wato_parameters(diagnostics_parameters)

        site = diagnostics_parameters["site"]
        timeout = html.request.request_timeout - 2
        results = []
        for chunk in chunks:
            results.append(
                check_mk_automation(
                    site,
                    "create-diagnostics-dump",
                    args=chunk,
                    timeout=timeout,
                    non_blocking_http=True,
                ))

        if len(results) > 1:
            result = _merge_results(results)
        elif len(results) == 1:
            result = results[0]
        else:
            job_interface.send_result_message(_("Got no result to create dump file"))
            return

        job_interface.send_progress_update(result["output"])

        if result["tarfile_created"]:
            tarfile_path = result['tarfile_path']
            download_url = makeuri_contextless(
                global_request,
                [("site", site), ("tarfile_name", str(Path(tarfile_path).name))],
                filename="download_diagnostics_dump.py",
            )
            button = html.render_icon_button(download_url, _("Download"), "diagnostics_dump_file")

            job_interface.send_progress_update(_("Dump file: %s") % tarfile_path)
            job_interface.send_result_message(_("%s Retrieve created dump file") % button)

        else:
            job_interface.send_result_message(_("Creating dump file failed"))


def _merge_results(results):
    output: str = ""
    tarfile_created: bool = False
    tarfile_paths: List[str] = []
    for result in results:
        output += result["output"]
        if result["tarfile_created"]:
            tarfile_created = True
            tarfile_paths.append(result["tarfile_path"])

    return {
        "output": output,
        "tarfile_created": tarfile_created,
        "tarfile_path": _join_sub_tars(tarfile_paths),
    }


def _join_sub_tars(tarfile_paths: List[str]) -> str:
    tarfile_path = str(
        cmk.utils.paths.diagnostics_dir.joinpath("sddump_%s" %
                                                 str(uuid.uuid4())).with_suffix(".tar.gz"))
    with tarfile.open(name=tarfile_path, mode='w:gz') as dest:
        for filepath in tarfile_paths:
            with tarfile.open(name=filepath, mode='r:gz') as sub_tar:
                sub_tar_members = [m for m in sub_tar.getmembers() if m.name != ""]
                dest_members = [m.name for m in dest.getmembers() if m.name != ""]
                for member in sub_tar_members:
                    if member.name not in dest_members:
                        dest.addfile(member, sub_tar.extractfile(member))
    return tarfile_path


@page_registry.register_page("download_diagnostics_dump")
class PageDownloadDiagnosticsDump(Page):
    def page(self) -> None:
        if not config.user.may("wato.diagnostics"):
            raise MKAuthException(
                _("Sorry, you lack the permission for downloading diagnostics dumps."))

        site = html.request.get_ascii_input_mandatory("site")
        tarfile_name = html.request.get_ascii_input_mandatory("tarfile_name")
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
        return html.request.get_ascii_input_mandatory("tarfile_name")


def _get_diagnostics_dump_file(tarfile_name: str) -> bytes:
    _validate_diagnostics_dump_tarfile_name(tarfile_name)
    tarfile_path = cmk.utils.paths.diagnostics_dir.joinpath(tarfile_name)
    with tarfile_path.open("rb") as f:
        return f.read()


def _validate_diagnostics_dump_tarfile_name(tarfile_name: str) -> None:
    # Prevent downloading files like 'tarfile_name=../../../../../../../../../../etc/passwd'
    if Path(tarfile_name).parent != Path('.'):
        raise MKUserError("_diagnostics_dump_file", _("Invalid file name for tarfile_name given."))
