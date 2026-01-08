#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="type-arg"

import json
import os
import tarfile
import uuid
from collections.abc import Collection, Iterator, Sequence
from pathlib import Path
from typing import override

from pydantic import BaseModel

import cmk.ccc.version as cmk_version
import cmk.utils.paths
from cmk.automations.results import CreateDiagnosticsDumpResult
from cmk.ccc.archive import CheckmkTarArchive
from cmk.ccc.site import omd_site, SiteId
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobRegistry,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobTarget,
)
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config, Config
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKUserError
from cmk.gui.htmllib.html import html, HTMLGenerator
from cmk.gui.http import ContentDispositionType, Request, request, response
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
from cmk.gui.pages import Page, PageContext, PageEndpoint, PageRegistry
from cmk.gui.permissions import permission_registry
from cmk.gui.theme import make_theme
from cmk.gui.type_defs import ActionResult, IconNames, PermissionName, StaticIcon
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.roles import UserPermissions, UserPermissionSerializableConfig
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    doc_reference_url,
    DocReference,
    makeuri,
    makeuri_contextless,
)
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
from cmk.gui.watolib.automation_commands import (
    AutomationCommand,
    AutomationCommandRegistry,
)
from cmk.gui.watolib.automations import (
    do_remote_automation,
    make_automation_config,
)
from cmk.gui.watolib.check_mk_automations import create_diagnostics_dump
from cmk.gui.watolib.mode import ModeRegistry, redirect, WatoMode
from cmk.utils.automation_config import LocalAutomationConfig, RemoteAutomationConfig
from cmk.utils.diagnostics import (
    CheckmkFileInfo,
    CheckmkFileSensitivity,
    CheckmkFilesMap,
    DiagnosticsParameters,
    FILE_MAP_CONFIG,
    FILE_MAP_CORE,
    FILE_MAP_LICENSING,
    FILE_MAP_LOG,
    get_checkmk_file_description,
    get_checkmk_file_info,
    get_checkmk_file_sensitivity_for_humans,
    OPT_APACHE_CONFIG,
    OPT_BI_RUNTIME_DATA,
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
    OSWalk,
    serialize_wato_parameters,
)

_FILE_MAPS = [
    FILE_MAP_CONFIG,
    FILE_MAP_CORE,
    FILE_MAP_LICENSING,
    FILE_MAP_LOG,
]

_CHECKMK_FILES_NOTE = _(
    "<br><b>Note</b>: Some files may contain highly sensitive data like"
    " passwords. These files are marked with 'H'."
    " Other files may include IP addresses, host names, usernames,"
    " mail addresses or phone numbers and are marked with 'M'."
)

timeout_default = 110


def register(
    page_registry: PageRegistry,
    mode_registry: ModeRegistry,
    automation_command_registry: AutomationCommandRegistry,
    job_registry: BackgroundJobRegistry,
) -> None:
    page_registry.register(PageEndpoint("download_diagnostics_dump", PageDownloadDiagnosticsDump()))
    mode_registry.register(ModeDiagnostics)
    automation_command_registry.register(AutomationDiagnosticsDumpGetFile)
    automation_command_registry.register(AutomationDiagnosticsDumpOsWalk)
    job_registry.register(DiagnosticsDumpBackgroundJob)


class ModeDiagnostics(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "diagnostics"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["diagnostics"]

    def _from_vars(self) -> None:
        self._site = request.var("site")
        self._checkmk_files_map: dict[str, CheckmkFilesMap] = {}
        for file_map in _FILE_MAPS:
            self._checkmk_files_map[file_map["file_type"]] = file_map["map_generator"](
                file_map["base_folder"],
                file_map["component_folder"],
                _os_walk_of_folder(self._site, file_map["base_folder"], 10),
                self._site,
            )

        self._collect_dump = bool(request.get_ascii_input("_collect_dump"))
        self._diagnostics_parameters = self._get_diagnostics_parameters()
        self._job = DiagnosticsDumpBackgroundJob()

    def _get_diagnostics_parameters(
        self,
    ) -> DiagnosticsParameters | None:
        if self._site is None:
            return None

        if self._collect_dump:
            params = self._vs_diagnostics().from_html_vars("diagnostics")
            return DiagnosticsParameters(
                site=SiteId(self._site),
                general=params["general"],
                timeout=params.get("timing", {}).get("timeout", timeout_default),
                opt_info=params["opt_info"],
                comp_specific=params["comp_specific"],
                checkmk_server_host=params["checkmk_server_host"],
            )

        return None

    def title(self) -> str:
        return _("Support diagnostics")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        if not request.has_var("site"):
            return make_simple_form_page_menu(
                _("Site"),
                breadcrumb,
                form_name="select",
                button_name="_do_select",
                save_title=_("Select"),
            )

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
                                icon_name=StaticIcon(IconNames.analyze_config),
                                item=make_simple_link("wato.py?mode=analyze_config"),
                            ),
                        ],
                    ),
                ],
            ),
        )
        menu.add_doc_reference(self.title(), DocReference[self.name().upper()])
        return menu

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return None

        if request.has_var("_do_select"):
            site = request.get_str_input_mandatory("site")
            request.set_var("site", site)
            return None

        if self._job.is_active() or self._diagnostics_parameters is None:
            return redirect(self._job.detail_url())

        params = self._diagnostics_parameters
        assert params is not None
        site = params["site"]
        site_config = config.sites[site]
        automation_config = make_automation_config(site_config)
        if (
            result := self._job.start(
                JobTarget(
                    callable=diagnostics_dump_entry_point,
                    args=DiagnosticsDumpArgs(
                        params=params,
                        automation_config=automation_config,
                        user_permission_config=UserPermissionSerializableConfig.from_global_config(
                            config
                        ),
                        debug=config.debug,
                    ),
                ),
                InitialStatusArgs(
                    title=self._job.gui_title(),
                    lock_wato=False,
                    stoppable=False,
                    user=str(user.id) if user.id else None,
                ),
            )
        ).is_error():
            raise result.error

        return redirect(self._job.detail_url())

    def page(self, config: Config) -> None:
        if not request.has_var("site"):
            self._select_site_form()
        else:
            if self._job.is_active():
                raise HTTPRedirect(self._job.detail_url())

            with html.form_context("diagnostics", method="POST"):
                vs_diagnostics = self._vs_diagnostics()
                vs_diagnostics.render_input("diagnostics", {})

                html.hidden_fields()

    def _select_site_form(self) -> None:
        with html.form_context("select", method="POST"):
            self._vs_select_site().render_input("site", None)
            html.hidden_fields()

    def _vs_select_site(self) -> SetupSiteChoice:
        return SetupSiteChoice(
            title=_("Select site"),
            encode_value=False,
        )

    def _vs_diagnostics(self) -> Dictionary:
        return Dictionary(
            title=_("Collect diagnostic dump"),
            render="form",
            help=_(
                "Files collected by the Support Diagnostics tool are automatically categorized to"
                " help you identify sensitive data. We recommend reviewing all files prior to"
                " sharing, particularly those in the Unclassified category.<ul>"
                "<li>H (High): Critical security data (e.g., passwords, API keys, secrets).</li>"
                "<li>M (Medium): PII and infrastructure details (e.g., IP addresses, hostnames,"
                " usernames, emails).</li>"
                "<li>L (Low): Operational data; no sensitive information is expected.</li>"
                "<li>U (Unclassified): Files from custom components. These might be 3rd-party"
                " extensions or modifications made by you.</li></ul>"
                "<b>Note</b>: These Classifications may differ from your organization's specific"
                " data security classifications.<br><br>"
                "The following files are created by built-in components:<ul><li>%s</li></ul>"
            )
            % "</li><li>".join(
                [f"{s} {f}: {d}" for (r_s, f, d, s) in get_checkmk_file_description()]
            ),
            elements=[
                (
                    "site",
                    FixedValue(
                        value=self._site,
                        title=_("Site"),
                        totext=self._site,
                        help=_("The site to create a dump for."),
                    ),
                ),
                (
                    "timing",
                    Dictionary(
                        title=_("Timeout"),
                        elements=[
                            (
                                "timeout",
                                Integer(
                                    title=_(
                                        "If exceeded, an exception will appear. "
                                        "In extraordinary cases, consider calling "
                                        "support diagnostics from command line "
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
                            OPT_APACHE_CONFIG,
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
                OPT_APACHE_CONFIG,
                FixedValue(
                    value=True,
                    totext="",
                    title=_("Apache Config"),
                    help=_(
                        "Apache Configuration files in /etc/apache2 or /etc/httpd, "
                        "/opt/omd/apache and $OMD_ROOT/etc/apache.<br>"
                        "<b>Note</b>: This might include information with medium sensitivity (M)."
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
                        "Apache mode and TCP address and port, core, "
                        "Liveproxy daemon and Livestatus TCP mode, "
                        "event daemon config, graphical user interface (GUI) authorization, "
                        "NSCA mode, TMP file system mode. "
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
                        "Checkmk agent, number, version and edition of sites, cluster host; "
                        "number of hosts, services, CMK Helper, Live Helper, "
                        "Helper usage; state of daemons: Apache, Core, Crontab, "
                        "DCD, Liveproxyd, MKEventd, MKNotifyd, RRDCached "
                        "(agent plug-in mk_inventory needs to be installed)"
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
                        "The latest crash reports<br>"
                        "<b>Note</b>: Some crash reports may contain sensitive data like "
                        "host names or usernames."
                    ),
                ),
            ),
            (
                OPT_CHECKMK_LOG_FILES,
                self._get_component_specific_checkmk_files_choices(
                    _("Checkmk Log files"),
                    [
                        (f, get_checkmk_file_info(f))
                        for f in self._checkmk_files_map[FILE_MAP_LOG["file_type"]]
                    ],
                ),
            ),
            (
                OPT_CHECKMK_CONFIG_FILES,
                self._get_component_specific_checkmk_files_choices(
                    _("Checkmk Configuration files"),
                    [
                        (f, get_checkmk_file_info(f))
                        for f in self._checkmk_files_map[FILE_MAP_CONFIG["file_type"]]
                    ],
                ),
            ),
        ]

        if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.COMMUNITY:
            elements.append(
                (
                    OPT_PERFORMANCE_GRAPHS,
                    FixedValue(
                        value=True,
                        totext="",
                        title=_("Time series graphs of Checkmk server"),
                        help=_(
                            "CPU load and utilization, number of threads, Kernel performance, "
                            "OMD, file system, Apache status, TCP connections of the time ranges "
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
                    title=_("Global settings"),
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
                    )
                    + self._get_bi_runtime_data(),
                    default_keys=["config_files"],
                ),
            ),
        ]

        if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.COMMUNITY:
            elements.append(
                (
                    OPT_COMP_CMC,
                    Dictionary(
                        title=_("CMC (Checkmk Micro Core)"),
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

    def _get_bi_runtime_data(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                OPT_BI_RUNTIME_DATA,
                FixedValue(
                    value=True,
                    totext="",
                    title=_("BI runtime data"),
                    help=_(
                        "Cached data from Business Intelligence. "
                        "Contains states, downtimes, acknowledgements and service periods "
                        "for all hosts/services included in a BI aggregation."
                    ),
                ),
            )
        ]

    def _get_cs_elements_for(
        self,
        component: str,
        element_id: str,
        element_title: str,
        files_map: CheckmkFilesMap,
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
            (
                "config_files",
                _("Configuration files"),
                self._checkmk_files_map[FILE_MAP_CONFIG["file_type"]],
            ),
            (
                "core_files",
                _("Core files"),
                self._checkmk_files_map[FILE_MAP_CORE["file_type"]],
            ),
            (
                "licensing_files",
                _("Licensing files"),
                self._checkmk_files_map[FILE_MAP_LICENSING["file_type"]],
            ),
            (
                "log_files",
                _("Log files"),
                self._checkmk_files_map[FILE_MAP_LOG["file_type"]],
            ),
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
        sorted_checkmk_files = sorted(checkmk_files, key=lambda t: t[0])
        high_sensitive_files = [
            f
            for f in sorted_checkmk_files
            if f[1].sensitivity == CheckmkFileSensitivity.high_sensitive
        ]

        sensitive_files = [
            f for f in sorted_checkmk_files if f[1].sensitivity == CheckmkFileSensitivity.sensitive
        ]

        insensitive_files = [
            f
            for f in sorted_checkmk_files
            if f[1].sensitivity == CheckmkFileSensitivity.insensitive
        ]

        uncategorized_files = [
            f for f in sorted_checkmk_files if f[1].sensitivity == CheckmkFileSensitivity.unknown
        ]

        # File lists are sorted by filename and grouped by sensitivity
        sorted_files = (
            high_sensitive_files + sensitive_files + insensitive_files + uncategorized_files
        )
        sorted_non_high_sensitive_files = sensitive_files + insensitive_files
        sorted_insensitive_files = insensitive_files

        return CascadingDropdown(
            title=title,
            sorted=False,
            choices=[
                (
                    "all",
                    _("Pack all files: High, Medium, Low, Unclassified sensitivity"),
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
            (
                rel_filepath,
                get_checkmk_file_sensitivity_for_humans(rel_filepath, file_info),
            )
            for rel_filepath, file_info in files
        ]


class DiagnosticsDumpArgs(BaseModel, frozen=True):
    params: DiagnosticsParameters
    automation_config: LocalAutomationConfig | RemoteAutomationConfig
    user_permission_config: UserPermissionSerializableConfig
    debug: bool


def diagnostics_dump_entry_point(
    job_interface: BackgroundProcessInterface, args: DiagnosticsDumpArgs
) -> None:
    DiagnosticsDumpBackgroundJob().do_execute(
        args.params,
        job_interface,
        automation_config=args.automation_config,
        user_permission_config=args.user_permission_config,
        debug=args.debug,
    )


class DiagnosticsDumpBackgroundJob(BackgroundJob):
    job_prefix = "diagnostics_dump"

    @classmethod
    def gui_title(cls) -> str:
        return _("Diagnostics dump")

    def __init__(self) -> None:
        super().__init__(self.job_prefix)

    def _back_url(self) -> str:
        return makeuri(request, [])

    def do_execute(
        self,
        diagnostics_parameters: DiagnosticsParameters,
        job_interface: BackgroundProcessInterface,
        user_permission_config: UserPermissionSerializableConfig,
        *,
        automation_config: LocalAutomationConfig | RemoteAutomationConfig,
        debug: bool,
    ) -> None:
        with job_interface.gui_context(
            UserPermissions.from_serialized_config(user_permission_config, permission_registry)
        ):
            self._do_execute(
                diagnostics_parameters,
                job_interface,
                automation_config=automation_config,
                debug=debug,
            )

    def _do_execute(
        self,
        diagnostics_parameters: DiagnosticsParameters,
        job_interface: BackgroundProcessInterface,
        *,
        automation_config: LocalAutomationConfig | RemoteAutomationConfig,
        debug: bool,
    ) -> None:
        job_interface.send_progress_update(_("Diagnostics dump started..."))

        chunks = serialize_wato_parameters(diagnostics_parameters)

        site = diagnostics_parameters["site"]
        results = []
        for chunk in chunks:
            chunk_result = create_diagnostics_dump(
                automation_config,
                chunk,
                diagnostics_parameters["timeout"],
                debug=debug,
            )
            results.append(chunk_result)

        if len(results) > 1:
            result = _merge_results(
                automation_config,
                results,
                diagnostics_parameters["timeout"],
                debug=debug,
            )
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

            job_interface.send_progress_update(_("Dump file: %s") % tarfile_path)
            job_interface.send_result_message(
                _("%s Retrieve created dump file")
                % HTMLGenerator.render_icon_button(
                    url=download_url,
                    title=_("Download"),
                    icon=StaticIcon(IconNames.diagnostics_dump_file),
                    theme=make_theme(validate_choices=False),
                )
            )

        else:
            job_interface.send_result_message(_("Creating dump file failed"))


def _merge_results(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    results: Sequence[CreateDiagnosticsDumpResult],
    timeout: int,
    *,
    debug: bool,
) -> CreateDiagnosticsDumpResult:
    output: str = ""
    tarfile_created: bool = False
    tarfile_paths: list[str] = []
    for result in results:
        output += result.output
        if result.tarfile_created:
            tarfile_created = True
            if isinstance(automation_config, LocalAutomationConfig):
                tarfile_localpath = result.tarfile_path
            else:
                tarfile_localpath = _get_tarfile_from_remotesite(
                    automation_config,
                    Path(result.tarfile_path).name,
                    timeout,
                    debug=debug,
                )
            tarfile_paths.append(tarfile_localpath)

    return CreateDiagnosticsDumpResult(
        output=output,
        tarfile_created=tarfile_created,
        tarfile_path=_join_sub_tars(tarfile_paths),
    )


def _get_tarfile_from_remotesite(
    automation_config: RemoteAutomationConfig,
    tarfile_name: str,
    timeout: int,
    *,
    debug: bool,
) -> str:
    cmk.utils.paths.diagnostics_dir.mkdir(parents=True, exist_ok=True)
    tarfile_localpath = _create_file_path()
    with open(tarfile_localpath, "wb") as file:
        file.write(
            _get_diagnostics_dump_file(automation_config, tarfile_name, timeout, debug=debug)
        )
    return tarfile_localpath


def _join_sub_tars(tarfile_paths: Sequence[str]) -> str:
    tarfile_path = _create_file_path()
    with tarfile.open(name=tarfile_path, mode="w:gz") as dest:
        for filepath in tarfile_paths:
            with CheckmkTarArchive.from_path(Path(filepath)) as sub_tar:
                dest_members = [m.name for m in dest.getmembers()]
                for member in sub_tar:
                    if member.name not in dest_members:
                        dest.addfile(member, sub_tar.extractmember(member))
    return tarfile_path


def _create_file_path() -> str:
    return str(
        cmk.utils.paths.diagnostics_dir.joinpath("sddump_" + str(uuid.uuid4())).with_suffix(
            ".tar.gz"
        )
    )


class PageDownloadDiagnosticsDump(Page):
    @override
    def page(self, ctx: PageContext) -> None:
        if not user.may("wato.diagnostics"):
            raise MKAuthException(
                _("Sorry, you lack the permission for downloading diagnostics dumps.")
            )

        site_id = SiteId(request.get_ascii_input_mandatory("site"))
        tarfile_name = request.get_ascii_input_mandatory("tarfile_name")
        timeout = request.get_integer_input_mandatory("timeout")
        _validate_diagnostics_dump_tarfile_name(tarfile_name)

        file_content = _get_diagnostics_dump_file(
            make_automation_config(ctx.config.sites[site_id]),
            tarfile_name,
            timeout,
            debug=ctx.config.debug,
        )

        response.set_content_type("application/x-tgz")
        response.set_content_disposition(ContentDispositionType.ATTACHMENT, tarfile_name)
        response.set_data(file_content)


class AutomationDiagnosticsDumpOsWalk(AutomationCommand[str]):
    def command_name(self) -> str:
        return "diagnostics-dump-os-walk"

    def execute(self, api_request: str) -> str:
        return json.dumps(list(os.walk(api_request)))

    def get_request(self, config: Config, request: Request) -> str:
        return request.get_ascii_input_mandatory("folder")


def _os_walk_of_folder(site: str | None, base_folder: Path, timeout: int) -> OSWalk:
    if not site:
        return list(os.walk(base_folder))

    automation_config = make_automation_config(active_config.sites[SiteId(site)])

    if isinstance(automation_config, LocalAutomationConfig):
        return list(os.walk(base_folder))

    base_folder = Path(str(base_folder).replace(omd_site(), site))
    json_response = do_remote_automation(
        automation_config,
        "diagnostics-dump-os-walk",
        [
            ("folder", str(base_folder)),
        ],
        timeout=timeout,
        debug=active_config.debug,
    )
    assert isinstance(json_response, str)
    return OSWalk(json.loads(json_response))


class AutomationDiagnosticsDumpGetFile(AutomationCommand[str]):
    def command_name(self) -> str:
        return "diagnostics-dump-get-file"

    def execute(self, api_request: str) -> bytes:
        return _get_local_diagnostics_dump_file(api_request)

    def get_request(self, config: Config, request: Request) -> str:
        return request.get_ascii_input_mandatory("tarfile_name")


def _get_diagnostics_dump_file(
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    tarfile_name: str,
    timeout: int,
    *,
    debug: bool,
) -> bytes:
    if isinstance(automation_config, LocalAutomationConfig):
        return _get_local_diagnostics_dump_file(tarfile_name)

    raw_response = do_remote_automation(
        automation_config,
        "diagnostics-dump-get-file",
        [
            ("tarfile_name", tarfile_name),
        ],
        timeout=timeout,
        debug=debug,
    )
    assert isinstance(raw_response, bytes)
    return raw_response


def _get_local_diagnostics_dump_file(tarfile_name: str) -> bytes:
    _validate_diagnostics_dump_tarfile_name(tarfile_name)
    tarfile_path = cmk.utils.paths.diagnostics_dir.joinpath(tarfile_name)
    with tarfile_path.open("rb") as f:
        return f.read()


def _validate_diagnostics_dump_tarfile_name(tarfile_name: str) -> None:
    """security validation

    Prevent downloading files like 'tarfile_name=../../../../../../../../../../etc/passwd'
    >>> _validate_diagnostics_dump_tarfile_name("foo")
    >>> _validate_diagnostics_dump_tarfile_name("../bar/foo")
    Traceback (most recent call last):
        ...
    cmk.gui.exceptions.MKUserError: Invalid file name for tarfile_name given.
    """

    if Path(tarfile_name).parent != Path("."):
        raise MKUserError("_diagnostics_dump_file", _("Invalid file name for tarfile_name given."))
