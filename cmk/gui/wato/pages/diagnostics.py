#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import tarfile
import uuid
from collections.abc import Collection, Iterator
from pathlib import Path

from livestatus import SiteId

import cmk.utils.paths
import cmk.utils.version as cmk_version
from cmk.utils.diagnostics import (
    CheckmkFileInfo,
    CheckmkFileSensitivity,
    CheckmkFilesMap,
    DiagnosticsParameters,
    get_checkmk_config_files_map,
    get_checkmk_core_files_map,
    get_checkmk_file_description,
    get_checkmk_file_info,
    get_checkmk_file_sensitivity_for_humans,
    get_checkmk_licensing_files_map,
    get_checkmk_log_files_map,
    OPT_CHECKMK_CONFIG_FILES,
    OPT_CHECKMK_CRASH_REPORTS,
    OPT_CHECKMK_LOG_FILES,
    OPT_CHECKMK_OVERVIEW,
    OPT_COMP_BUSINESS_INTELLIGENCE,
    OPT_COMP_CMC,
    OPT_COMP_GLOBAL_SETTINGS,
    OPT_COMP_HOSTS_AND_FOLDERS,
    OPT_COMP_LICENSING,
    OPT_COMP_NOTIFICATIONS,
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
    serialize_wato_parameters,
)
from cmk.utils.site import omd_site

from cmk.automations.results import CreateDiagnosticsDumpResult

from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    job_registry,
)
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import Page, page_registry
from cmk.gui.plugins.wato.utils import mode_registry, redirect, WatoMode
from cmk.gui.site_config import get_site_config, site_is_local
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import doc_reference_url, DocReference, makeuri, makeuri_contextless
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DualListChoice,
    FixedValue,
    Integer,
    MonitoredHostname,
    SetupSiteChoice,
    ValueSpec,
)
from cmk.gui.watolib.automation_commands import automation_command_registry, AutomationCommand
from cmk.gui.watolib.automations import do_remote_automation
from cmk.gui.watolib.check_mk_automations import create_diagnostics_dump

_CHECKMK_FILES_NOTE = _(
    "<br>Note: Some files may contain highly sensitive data like"
    " passwords. These files are marked with 'H'."
    " Other files may include IP adresses, hostnames, usernames,"
    " mail adresses or phone numbers and are marked with 'M'."
)

timeout_default = 110


@mode_registry.register
class ModeDiagnostics(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "diagnostics"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["diagnostics"]

    def _from_vars(self) -> None:
        self._checkmk_config_files_map = get_checkmk_config_files_map()
        self._checkmk_core_files_map = get_checkmk_core_files_map()
        self._checkmk_licensing_files_map = get_checkmk_licensing_files_map()
        self._checkmk_log_files_map = get_checkmk_log_files_map()
        self._collect_dump = bool(request.get_ascii_input("_collect_dump"))
        self._diagnostics_parameters = self._get_diagnostics_parameters()
        self._job = DiagnosticsDumpBackgroundJob()

    def _get_diagnostics_parameters(self) -> DiagnosticsParameters | None:
        if self._collect_dump:
            params = self._vs_diagnostics().from_html_vars("diagnostics")
            return {
                "site": params["site"],
                "timeout": params.get("timing", {}).get("timeout", timeout_default),
                "general": params["general"],
                "opt_info": params["opt_info"],
                "comp_specific": params["comp_specific"],
                "checkmk_server_host": params["checkmk_server_host"],
            }
        return None

    def title(self) -> str:
        return _("Support diagnostics")

    def page_menu(self, breadcrumb) -> PageMenu:  # type:ignore[no-untyped-def]
        menu = make_simple_form_page_menu(
            _("Diagnostics"),
            breadcrumb,
            form_name="diagnostics",
            button_name="_collect_dump",
            save_title=_("Collect diagnostics"),
        )
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
            ),
        )
        menu.add_doc_reference(self.title(), DocReference[self.name().upper()])
        return menu

    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return None

        if self._job.is_active() or self._diagnostics_parameters is None:
            return redirect(self._job.detail_url())

        params = self._diagnostics_parameters
        assert params is not None
        self._job.start(lambda job_interface: self._job.do_execute(params, job_interface))

        return redirect(self._job.detail_url())

    def page(self) -> None:
        if self._job.is_active():
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
            help="File Descriptions:<br>%s"
            % "<br>".join([f" - {f}: {d}" for (f, d) in get_checkmk_file_description()]),
            elements=[
                (
                    "site",
                    SetupSiteChoice(),
                ),
                # TODO: provide the possibility to chose multiple sites
                # (
                #    "sites",
                #    CascadingDropdown(
                #        title="Sites",
                #        sorted=False,
                #        help="",
                #        choices=[
                #            (
                #                "all",
                #                _("Collect diagnostics data from all sites"),
                #                FixedValue(
                #                    [s for s, si in get_activation_site_choices()],
                #                    totext="<br>".join([si for s, si in get_activation_site_choices()])
                #                ),
                #            ),
                #            (
                #                "local",
                #                _("Collect diagnostics data from local site only"),
                #                FixedValue(
                #                    [omd_site()],
                #                    #totext="%s - %s" % site_choices(omd_site())
                #                    totext=[si for s, si in get_activation_site_choices() if s == omd_site()][0]
                #                ),
                #            ),
                #            (
                #                "explicit_list_of_sites",
                #                _("Select individual sites from list"),
                #                DualListChoice(
                #                    choices=get_activation_site_choices(),
                #                    size=80,
                #                    rows=10,
                #                ),
                #            ),
                #        ],
                #        default_value="local",
                #    )
                # ),
                (
                    "timing",
                    Dictionary(
                        title=_("Timeout"),
                        elements=[
                            (
                                "timeout",
                                Integer(
                                    title=_(
                                        "If exceeded, an Exception will appear. "
                                        "In extraordinary cases, consider calling "
                                        "Support Diagnostics from command line "
                                        "(see inline help)."
                                    ),
                                    help=_(
                                        "The timeout in seconds when gathering the support "
                                        "diagnostics data. The default is 110 seconds. When "
                                        "very large files are collected, it's also possible to "
                                        "call the support diagnostics from the command line "
                                        "using the command 'cmk --create-diagnostics-dump' with "
                                        "appropriate parameters in the context of the affected "
                                        "site. See the %s."
                                    )
                                    % html.render_a(
                                        "user manual",
                                        href=doc_reference_url(DocReference.DIAGNOSTICS_CLI),
                                        target="_blank",
                                    ),
                                    default_value=timeout_default,
                                    minvalue=60,
                                    unit=_("seconds"),
                                ),
                            ),
                        ],
                    ),
                ),
                (
                    "checkmk_server_host",
                    MonitoredHostname(
                        title=_("Checkmk server host"),
                        help=_(
                            "Some of the diagnostics data needs to be collected from the host "
                            "that represents the Checkmk server of the related site. "
                            "In case your Checkmk server is not monitored by itself, but from "
                            "a different site (which is actually recommended), please enter "
                            "the name of that host here."
                        ),
                    ),
                ),
                (
                    "general",
                    FixedValue(
                        value=True,
                        title=_("General information"),
                        totext=_("Collect information about OS and Checkmk version"),
                        help=_(
                            "Collect information about OS, Checkmk version and edition, "
                            "Time, Core, Python version and paths, Architecture"
                        ),
                    ),
                ),
                (
                    "opt_info",
                    Dictionary(
                        title=_("Optional general information"),
                        elements=self._get_optional_information_elements(),
                        default_keys=[
                            OPT_LOCAL_FILES,
                            OPT_OMD_CONFIG,
                            OPT_CHECKMK_OVERVIEW,
                            OPT_CHECKMK_CRASH_REPORTS,
                            OPT_CHECKMK_LOG_FILES,
                            OPT_CHECKMK_CONFIG_FILES,
                            OPT_PERFORMANCE_GRAPHS,
                        ],
                    ),
                ),
                (
                    "comp_specific",
                    Dictionary(
                        title=_("Component specific information"),
                        elements=self._get_component_specific_elements(),
                        default_keys=[
                            OPT_COMP_BUSINESS_INTELLIGENCE,
                            OPT_COMP_CMC,
                            OPT_COMP_LICENSING,
                        ],
                    ),
                ),
            ],
            optional_keys=False,
        )

    def _get_optional_information_elements(self) -> list[tuple[str, ValueSpec]]:
        elements: list[tuple[str, ValueSpec]] = [
            (
                OPT_LOCAL_FILES,
                FixedValue(
                    value=True,
                    totext="",
                    title=_("Local Files and MKPs"),
                    help=_(
                        "List of installed, unpacked, optional files below OMD_ROOT/local. "
                        "This also includes information about installed MKPs."
                    ),
                ),
            ),
            (
                OPT_OMD_CONFIG,
                FixedValue(
                    value=True,
                    totext="",
                    title=_("OMD Config"),
                    help=_(
                        "Apache mode and TCP address and port, Core, "
                        "Liveproxy daemon and livestatus TCP mode, "
                        "Event daemon config, Multiste authorisation, "
                        "NSCA mode, TMP filesystem mode"
                    ),
                ),
            ),
            (
                OPT_CHECKMK_OVERVIEW,
                FixedValue(
                    value=True,
                    totext="",
                    title=_("Checkmk Overview"),
                    help=_(
                        "Checkmk Agent, Number, version and edition of sites, Cluster host; "
                        "Number of hosts, services, CMK Helper, Live Helper, "
                        "Helper usage; State of daemons: Apache, Core, Crontag, "
                        "DCD, Liveproxyd, MKEventd, MKNotifyd, RRDCached "
                        "(Agent plugin mk_inventory needs to be installed)"
                    ),
                ),
            ),
            (
                OPT_CHECKMK_CRASH_REPORTS,
                FixedValue(
                    value=True,
                    totext="",
                    title=_("Crash Reports"),
                    help=_(
                        "The latest crash reports"
                        "<br>Note: Some crash reports may contain sensitive data like"
                        "host names or user names."
                    ),
                ),
            ),
            (
                OPT_CHECKMK_LOG_FILES,
                self._get_component_specific_checkmk_files_choices(
                    _("Checkmk Log files"),
                    [(f, get_checkmk_file_info(f)) for f in self._checkmk_log_files_map],
                ),
            ),
            (
                OPT_CHECKMK_CONFIG_FILES,
                self._get_component_specific_checkmk_files_choices(
                    _("Checkmk Configuration files"),
                    [(f, get_checkmk_file_info(f)) for f in self._checkmk_config_files_map],
                ),
            ),
        ]

        if not cmk_version.is_raw_edition():
            elements.append(
                (
                    OPT_PERFORMANCE_GRAPHS,
                    FixedValue(
                        value=True,
                        totext="",
                        title=_("Performance Graphs of Checkmk Server"),
                        help=_(
                            "CPU load and utilization, Number of threads, Kernel Performance, "
                            "OMD, Filesystem, Apache Status, TCP Connections of the time ranges "
                            "25 hours and 35 days"
                        ),
                    ),
                )
            )

        return elements

    def _get_component_specific_elements(self) -> list[tuple[str, ValueSpec]]:
        elements: list[tuple[str, ValueSpec]] = [
            (
                OPT_COMP_GLOBAL_SETTINGS,
                Dictionary(
                    title=_("Global Settings"),
                    help=_("Configuration files ('*.mk' or '*.conf') from etc/check_mk.%s")
                    % _CHECKMK_FILES_NOTE,
                    elements=self._get_component_specific_checkmk_files_elements(
                        OPT_COMP_GLOBAL_SETTINGS
                    ),
                    default_keys=["config_files"],
                ),
            ),
            (
                OPT_COMP_HOSTS_AND_FOLDERS,
                Dictionary(
                    title=_("Hosts and Folders"),
                    help=_("Configuration files ('*.mk' or '*.conf') from etc/check_mk.%s")
                    % _CHECKMK_FILES_NOTE,
                    elements=self._get_component_specific_checkmk_files_elements(
                        OPT_COMP_HOSTS_AND_FOLDERS
                    ),
                    default_keys=["config_files"],
                ),
            ),
            (
                OPT_COMP_NOTIFICATIONS,
                Dictionary(
                    title=_("Notifications"),
                    help=_(
                        "Configuration files ('*.mk' or '*.conf') from etc/check_mk"
                        " or log files ('*.log' or '*.state') from var/log.%s"
                    )
                    % _CHECKMK_FILES_NOTE,
                    elements=self._get_component_specific_checkmk_files_elements(
                        OPT_COMP_NOTIFICATIONS
                    ),
                    default_keys=["config_files"],
                ),
            ),
            (
                OPT_COMP_BUSINESS_INTELLIGENCE,
                Dictionary(
                    title=_("Business Intelligence"),
                    help=_("Configuration files ('*.mk' or '*.conf') from etc/check_mk.%s")
                    % _CHECKMK_FILES_NOTE,
                    elements=self._get_component_specific_checkmk_files_elements(
                        OPT_COMP_BUSINESS_INTELLIGENCE,
                    ),
                    default_keys=["config_files"],
                ),
            ),
        ]

        if not cmk_version.is_raw_edition():
            elements.append(
                (
                    OPT_COMP_CMC,
                    Dictionary(
                        title=_("CMC (Checkmk Microcore)"),
                        help=_("Core files (config, state and history) from var/check_mk/core.%s")
                        % _CHECKMK_FILES_NOTE,
                        elements=self._get_component_specific_checkmk_files_elements(
                            OPT_COMP_CMC,
                        ),
                        default_keys=["core_files"],
                    ),
                )
            )
            elements.append(
                (
                    OPT_COMP_LICENSING,
                    Dictionary(
                        title=_("Licensing Information"),
                        help=_(
                            "Licensing files from var/check_mk/licensing, etc/check_mk,"
                            " var/check_mk/core and var/log/licensing.log.%s"
                        )
                        % _CHECKMK_FILES_NOTE,
                        elements=self._get_component_specific_checkmk_files_elements(
                            OPT_COMP_LICENSING,
                        ),
                        default_keys=["licensing_files", "log_files", "config_files"],
                    ),
                )
            )
        return elements

    def _get_cs_elements_for(
        self, component: str, element_id: str, element_title: str, files_map: CheckmkFilesMap
    ) -> Iterator[tuple[str, ValueSpec]]:
        files = [
            (f, fi)
            for f in files_map
            for fi in [get_checkmk_file_info(f, component)]
            if component in fi.components
        ]

        if not files:
            return

        yield (
            element_id,
            self._get_component_specific_checkmk_files_choices(element_title, files),
        )

    def _get_component_specific_checkmk_files_elements(
        self, component: str
    ) -> list[tuple[str, ValueSpec]]:
        elements: list[tuple[str, ValueSpec]] = []
        for filetype in [
            ("config_files", _("Configuration files"), self._checkmk_config_files_map),
            ("core_files", _("Core files"), self._checkmk_core_files_map),
            ("licensing_files", _("Licensing files"), self._checkmk_licensing_files_map),
            ("log_files", _("Log files"), self._checkmk_log_files_map),
        ]:
            element_id, element_title, files_map = filetype
            for cs_element in self._get_cs_elements_for(
                component,
                element_id,
                element_title,
                files_map,
            ):
                elements.append(cs_element)

        return elements

    def _get_component_specific_checkmk_files_choices(
        self,
        title: str,
        checkmk_files: list[tuple[str, CheckmkFileInfo]],
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

        sorted_files = sorted(
            high_sensitive_files + sensitive_files + insensitive_files, key=lambda t: t[0]
        )
        sorted_non_high_sensitive_files = sorted(
            sensitive_files + insensitive_files, key=lambda t: t[0]
        )
        sorted_insensitive_files = sorted(insensitive_files, key=lambda t: t[0])

        return CascadingDropdown(
            title=title,
            sorted=False,
            choices=[
                (
                    "all",
                    _("Pack all files: High, Medium, Low sensitivity"),
                    FixedValue(
                        value=[f for f, fi in sorted_files],
                        totext=self._list_of_files_to_text(sorted_files),
                    ),
                ),
                (
                    "non_high_sensitive",
                    _("Pack only Medium and Low sensitivity files"),
                    FixedValue(
                        value=[f for f, fi in sorted_non_high_sensitive_files],
                        totext=self._list_of_files_to_text(sorted_non_high_sensitive_files),
                    ),
                ),
                (
                    "insensitive",
                    _("Pack only Low sensitivity files"),
                    FixedValue(
                        value=[f for f, fi in sorted_insensitive_files],
                        totext=self._list_of_files_to_text(sorted_insensitive_files),
                    ),
                ),
                (
                    "explicit_list_of_files",
                    _("Select individual files from list"),
                    DualListChoice(
                        choices=self._list_of_files_choices(sorted_files),
                        size=80,
                        rows=10,
                    ),
                ),
            ],
            default_value="non_high_sensitive",
        )

    def _list_of_files_to_text(self, list_of_files: list[tuple[str, CheckmkFileInfo]]) -> str:
        return "<br>%s" % ",<br>".join(
            [
                get_checkmk_file_sensitivity_for_humans(rel_filepath, file_info)
                for rel_filepath, file_info in list_of_files
            ]
        )

    def _list_of_files_choices(
        self,
        files: list[tuple[str, CheckmkFileInfo]],
    ) -> list[tuple[str, str]]:
        return [
            (rel_filepath, get_checkmk_file_sensitivity_for_humans(rel_filepath, file_info))
            for rel_filepath, file_info in files
        ]


@job_registry.register
class DiagnosticsDumpBackgroundJob(BackgroundJob):
    job_prefix = "diagnostics_dump"

    @classmethod
    def gui_title(cls) -> str:
        return _("Diagnostics dump")

    def __init__(self) -> None:
        super().__init__(
            self.job_prefix,
            InitialStatusArgs(
                title=self.gui_title(),
                lock_wato=False,
                stoppable=False,
            ),
        )

    def _back_url(self) -> str:
        return makeuri(request, [])

    def do_execute(
        self,
        diagnostics_parameters: DiagnosticsParameters,
        job_interface: BackgroundProcessInterface,
    ) -> None:
        job_interface.send_progress_update(_("Diagnostics dump started..."))

        chunks = serialize_wato_parameters(diagnostics_parameters)

        # TODO: Currently, selecting multiple sites is not possible.
        # sites = diagnostics_parameters["sites"][1]
        site = diagnostics_parameters["site"]

        results = []
        for chunk in chunks:
            chunk_result = create_diagnostics_dump(
                site,
                chunk,
                diagnostics_parameters["timeout"],
            )
            results.append(chunk_result)

        # for site in sites:
        #    for chunk in chunks:

        #        chunk_result = create_diagnostics_dump(
        #            site,
        #            chunk,
        #            timeout,
        #        )
        #        results.append(chunk_result)

        if len(results) > 1:
            result = _merge_results(site, results, diagnostics_parameters["timeout"])
            # The remote tarfiles will be downloaded and the link will point to the local site.
            download_site_id = omd_site()
        elif len(results) == 1:
            result = results[0]
            # When there is only one chunk, the download link will point to the remote site.
            download_site_id = site
        else:
            job_interface.send_result_message(_("Got no result to create dump file"))
            return

        job_interface.send_progress_update(result.output)

        if result.tarfile_created:
            tarfile_path = result.tarfile_path
            download_url = makeuri_contextless(
                request,
                [
                    ("site", download_site_id),
                    ("tarfile_name", str(Path(tarfile_path).name)),
                    ("timeout", diagnostics_parameters["timeout"]),
                ],
                filename="download_diagnostics_dump.py",
            )
            button = html.render_icon_button(download_url, _("Download"), "diagnostics_dump_file")

            job_interface.send_progress_update(_("Dump file: %s") % tarfile_path)
            job_interface.send_result_message(_("%s Retrieve created dump file") % button)

        else:
            job_interface.send_result_message(_("Creating dump file failed"))


def _merge_results(
    site: SiteId, results: list[CreateDiagnosticsDumpResult], timeout: int
) -> CreateDiagnosticsDumpResult:
    output: str = ""
    tarfile_created: bool = False
    tarfile_paths: list[str] = []
    for result in results:
        output += result.output
        if result.tarfile_created:
            tarfile_created = True
            if site_is_local(site):
                tarfile_localpath = result.tarfile_path
            else:
                tarfile_localpath = _get_tarfile_from_remotesite(
                    SiteId(site),
                    Path(result.tarfile_path).name,
                    timeout,
                )
            tarfile_paths.append(tarfile_localpath)

    return CreateDiagnosticsDumpResult(
        output=output,
        tarfile_created=tarfile_created,
        tarfile_path=_join_sub_tars(tarfile_paths),
    )


def _get_tarfile_from_remotesite(site: SiteId, tarfile_name: str, timeout: int) -> str:
    cmk.utils.paths.diagnostics_dir.mkdir(parents=True, exist_ok=True)
    tarfile_localpath = _create_file_path()
    with open(tarfile_localpath, "wb") as file:
        file.write(_get_diagnostics_dump_file(site, tarfile_name, timeout))
    return tarfile_localpath


def _join_sub_tars(tarfile_paths: list[str]) -> str:
    tarfile_path = _create_file_path()
    with tarfile.open(name=tarfile_path, mode="w:gz") as dest:
        for filepath in tarfile_paths:
            with tarfile.open(name=filepath, mode="r:gz") as sub_tar:
                sub_tar_members = [m for m in sub_tar.getmembers() if m.name != ""]
                dest_members = [m.name for m in dest.getmembers() if m.name != ""]
                for member in sub_tar_members:
                    if member.name not in dest_members:
                        dest.addfile(member, sub_tar.extractfile(member))
    return tarfile_path


def _create_file_path() -> str:
    return str(
        cmk.utils.paths.diagnostics_dir.joinpath("sddump_" + str(uuid.uuid4())).with_suffix(
            ".tar.gz"
        )
    )


@page_registry.register_page("download_diagnostics_dump")
class PageDownloadDiagnosticsDump(Page):
    def page(self) -> None:
        if not user.may("wato.diagnostics"):
            raise MKAuthException(
                _("Sorry, you lack the permission for downloading diagnostics dumps.")
            )

        site = SiteId(request.get_ascii_input_mandatory("site"))
        tarfile_name = request.get_ascii_input_mandatory("tarfile_name")
        timeout = request.get_integer_input_mandatory("timeout")
        file_content = _get_diagnostics_dump_file(site, tarfile_name, timeout)

        response.set_content_type("application/x-tgz")
        response.headers["Content-Disposition"] = "Attachment; filename=%s" % tarfile_name
        response.set_data(file_content)


@automation_command_registry.register
class AutomationDiagnosticsDumpGetFile(AutomationCommand):
    def command_name(self) -> str:
        return "diagnostics-dump-get-file"

    def execute(self, api_request: str) -> bytes:
        return _get_local_diagnostics_dump_file(api_request)

    def get_request(self) -> str:
        return request.get_ascii_input_mandatory("tarfile_name")


def _get_diagnostics_dump_file(site: SiteId, tarfile_name: str, timeout: int) -> bytes:
    if site_is_local(site):
        return _get_local_diagnostics_dump_file(tarfile_name)

    raw_response = do_remote_automation(
        get_site_config(site),
        "diagnostics-dump-get-file",
        [
            ("tarfile_name", tarfile_name),
        ],
        timeout=timeout,
    )
    assert isinstance(raw_response, bytes)
    return raw_response


def _get_local_diagnostics_dump_file(tarfile_name: str) -> bytes:
    _validate_diagnostics_dump_tarfile_name(tarfile_name)
    tarfile_path = cmk.utils.paths.diagnostics_dir.joinpath(tarfile_name)
    with tarfile_path.open("rb") as f:
        return f.read()


def _validate_diagnostics_dump_tarfile_name(tarfile_name: str) -> None:
    # Prevent downloading files like 'tarfile_name=../../../../../../../../../../etc/passwd'
    if Path(tarfile_name).parent != Path("."):
        raise MKUserError("_diagnostics_dump_file", _("Invalid file name for tarfile_name given."))
