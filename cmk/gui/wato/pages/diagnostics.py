#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="explicit-override"

import json
import os
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path
from typing import Any, Final, NamedTuple, override

from pydantic import BaseModel

import cmk.utils.paths
from cmk.ccc.site import SiteId
from cmk.diagnostics.engine import (
    DumpSelection,
    load_diagnostics_plugins,
    resolve_selection,
    topic_id,
)
from cmk.diagnostics.internal import (
    DiagnosticsPlugin,
    Sensitivity,
    Topic,
)
from cmk.gui.background_job.job import (
    BackgroundJob,
    BackgroundJobRegistry,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobTarget,
)
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.exceptions import HTTPRedirect, MKAuthException, MKUserError
from cmk.gui.htmllib.html import html, HTMLGenerator
from cmk.gui.http import ContentDispositionType, Request, request, response
from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.log import logger
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
    DocReferenceUtm,
    makeuri,
    makeuri_contextless,
)
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
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
from cmk.gui.watolib.check_mk_automations import create_diagnostics_dump_v2
from cmk.gui.watolib.mode import ModeRegistry, redirect, WatoMode
from cmk.utils.automation_config import LocalAutomationConfig, RemoteAutomationConfig

timeout_default = 110

_THRESHOLDS: Final[Mapping[str, Sensitivity | None]] = {
    "off": None,
    "low": Sensitivity.LOW,
    "medium": Sensitivity.MEDIUM,
    "high": Sensitivity.HIGH,
}

_SENSITIVITY_MARKERS: Final[Mapping[Sensitivity, str]] = {
    Sensitivity.LOW: "L",
    Sensitivity.MEDIUM: "M",
    Sensitivity.HIGH: "H",
}


def register(
    page_registry: PageRegistry,
    mode_registry: ModeRegistry,
    automation_command_registry: AutomationCommandRegistry,
    job_registry: BackgroundJobRegistry,
) -> None:
    page_registry.register(
        PageEndpoint(
            "download_diagnostics_dump",
            PageDownloadDiagnosticsDump(cmk.utils.paths.diagnostics_dir),
        )
    )
    mode_registry.register(ModeDiagnostics)
    automation_command_registry.register(AutomationDiagnosticsDumpGetFile)
    automation_command_registry.register(AutomationDiagnosticsDumpOsWalk)
    job_registry.register(DiagnosticsDumpBackgroundJob)


def _load_plugin_catalogue() -> Sequence[DiagnosticsPlugin]:
    """The support diagnostics plugins available on this site"""
    discovered = load_diagnostics_plugins(raise_errors=False)
    for error in discovered.errors:
        logger.error(error)
    return list(discovered.plugins.values())


def _selectable_topics(plugins: Sequence[DiagnosticsPlugin]) -> Sequence[Topic]:
    """The topics offering a threshold choice, i.e. those with selectable plugins

    Topics whose plugins are all collected anyway get no dropdown.

    Raises:
        ValueError: if two topics sanitize to the same form element id.
    """
    topics = sorted(
        {plugin.topic for plugin in plugins if not plugin.always},
        key=lambda topic: topic.localize(str),
    )
    if len({topic_id(topic) for topic in topics}) != len(topics):
        raise ValueError("Diagnostics topics with colliding form element ids")
    return topics


class _DiagnosticsParameters(NamedTuple):
    site: SiteId
    timeout: int
    plugins: Sequence[str]
    checkmk_server_host: str


class ModeDiagnostics(WatoMode[object]):
    @classmethod
    def name(cls) -> str:
        return "diagnostics"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["diagnostics"]

    def _from_vars(self) -> None:
        self._site = request.var("select_site_p_site")
        self._collect_dump = bool(request.get_ascii_input("_collect_dump"))
        self._diagnostics_parameters = self._get_diagnostics_parameters()
        self._job = DiagnosticsDumpBackgroundJob()

    def _get_diagnostics_parameters(self) -> _DiagnosticsParameters | None:
        if self._site is None or not self._collect_dump:
            return None

        plugins = _load_plugin_catalogue()
        params = self._vs_diagnostics(plugins).from_html_vars("diagnostics")
        thresholds = {
            topic: _THRESHOLDS[params[topic_id(topic)]] for topic in _selectable_topics(plugins)
        }
        return _DiagnosticsParameters(
            site=SiteId(self._site),
            timeout=params.get("timing", {}).get("timeout", timeout_default),
            plugins=resolve_selection(plugins, thresholds),
            checkmk_server_host=str(params.get("checkmk_server_host") or ""),
        )

    def title(self) -> str:
        return _("Support diagnostics")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        if not request.has_var("site"):
            menu = make_simple_form_page_menu(
                _("Site"),
                breadcrumb,
                form_name="select_site",
                button_name="_do_select",
                save_title=_("Select"),
            )

        else:
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
            site = request.get_str_input_mandatory("select_site_p_site")
            request.set_var("site", site)
            return None

        if self._job.is_active() or self._diagnostics_parameters is None:
            return redirect(self._job.detail_url())

        params = self._diagnostics_parameters
        site_config = config.sites[params.site]
        automation_config = make_automation_config(site_config)
        if (
            result := self._job.start(
                JobTarget(
                    callable=diagnostics_dump_entry_point,
                    args=DiagnosticsDumpArgs(
                        site=params.site,
                        plugins=list(params.plugins),
                        checkmk_server_host=params.checkmk_server_host,
                        timeout=params.timeout,
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
        if self._job.is_active():
            # Job is already running, don't give the user the chance to start another one.
            raise HTTPRedirect(self._job.detail_url())

        if not request.has_var("site"):
            with html.form_context("select_site", method="POST"):
                self._vs_select_site().render_input("select_site", None)
                html.hidden_fields()
        else:
            with html.form_context("diagnostics", method="POST"):
                self._vs_diagnostics(_load_plugin_catalogue()).render_input("diagnostics", None)
                html.hidden_fields()

    def _vs_select_site(self) -> Dictionary:
        return Dictionary(
            title=_("Select site"),
            render="form",
            help=_(
                "Select the site to create a dump for. The actual contents of the dump can be"
                " selected in the next screen."
            ),
            elements=[
                (
                    "site",
                    SetupSiteChoice(
                        title=_("Select site"),
                        encode_value=False,
                    ),
                ),
            ],
            optional_keys=False,
        )

    def _vs_site(self) -> tuple[str, FixedValue[str | None]]:
        return (
            "site",
            FixedValue(
                value=self._site,
                title=_("Site"),
                totext=self._site,
                help=_("The site to create a dump for."),
            ),
        )

    def _vs_timing(self) -> tuple[str, Dictionary]:
        return (
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
                                "site. See the %(user_manual)s."
                            )
                            % {
                                "user_manual": html.render_a(
                                    "user manual",
                                    href=doc_reference_url(
                                        user.language,
                                        DocReferenceUtm(
                                            campaign="inline_help",
                                            content="setup.diagnostics",
                                        ),
                                        DocReference.DIAGNOSTICS_CLI,
                                    ),
                                    target="_blank",
                                )
                            },
                            default_value=timeout_default,
                            minvalue=60,
                            unit=_("seconds"),
                        ),
                    ),
                ],
            ),
        )

    def _vs_checkmk_server_host(self) -> tuple[str, MonitoredHostname]:
        return (
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
        )

    def _vs_always_included_element(
        self, plugins: Sequence[DiagnosticsPlugin]
    ) -> Sequence[tuple[str, ValueSpec[Any]]]:
        always_descriptions = sorted(
            plugin.description.localize(translate_to_current_language)
            for plugin in plugins
            if plugin.always
        )
        if not always_descriptions:
            return []
        return [
            (
                "always",
                FixedValue(
                    value=True,
                    title=_("Always included"),
                    totext="<br>".join(always_descriptions),
                    help=_(
                        "This general information is part of every support diagnostics dump."
                        " It contains no sensitive data and cannot be deselected."
                    ),
                ),
            )
        ]

    def _vs_topic_elements(
        self, plugins: Sequence[DiagnosticsPlugin]
    ) -> Sequence[tuple[str, ValueSpec[Any]]]:
        plugins_by_topic: dict[Topic, list[DiagnosticsPlugin]] = {}
        for plugin in plugins:
            if not plugin.always:
                plugins_by_topic.setdefault(plugin.topic, []).append(plugin)

        return [
            (
                topic_id(topic),
                DropdownChoice(
                    choices=[
                        ("off", _("Off")),
                        ("low", _("Low sensitivity only")),
                        ("medium", _("Low and medium sensitivity")),
                        ("high", _("All including highly sensitive data")),
                    ],
                    title=topic.localize(translate_to_current_language),
                    help=self._topic_help(plugins_by_topic[topic]),
                    default_value="medium",
                ),
            )
            for topic in _selectable_topics(plugins)
        ]

    def _topic_help(self, topic_plugins: Sequence[DiagnosticsPlugin]) -> str:
        plugin_list = "".join(
            "<li>(%s) %s</li>"
            % (
                _SENSITIVITY_MARKERS[plugin.sensitivity],
                plugin.description.localize(translate_to_current_language),
            )
            for plugin in sorted(topic_plugins, key=lambda p: (p.sensitivity.value, p.name))
        )
        return _("The sensitivity threshold selects what is included:<ul>%(plugin_list)s</ul>") % {
            "plugin_list": plugin_list,
        }

    def _vs_diagnostics(self, plugins: Sequence[DiagnosticsPlugin]) -> Dictionary:
        elements: list[tuple[str, ValueSpec[Any]]] = [
            self._vs_site(),
            self._vs_timing(),
            self._vs_checkmk_server_host(),
            *self._vs_always_included_element(plugins),
            *self._vs_topic_elements(plugins),
        ]

        return Dictionary(
            title=_("Collect diagnostic dump"),
            render="form",
            help=_(
                "The data provided by the support diagnostics is grouped into topics. For each"
                " topic, select up to which sensitivity level data is included:<ul>"
                "<li>L (Low): Operational data; no sensitive information is expected.</li>"
                "<li>M (Medium): May include IP addresses, host names, usernames, mail"
                " addresses or phone numbers.</li>"
                "<li>H (High): May include highly sensitive data like passwords, API keys or"
                " secrets.</li></ul>"
                "<b>Note</b>: These classifications may differ from your organization's specific"
                " data security classifications. We recommend reviewing the dump prior to"
                " sharing."
            ),
            elements=elements,
            optional_keys=False,
        )


class DiagnosticsDumpArgs(BaseModel, frozen=True):
    site: SiteId
    plugins: list[str]
    checkmk_server_host: str
    timeout: int
    automation_config: LocalAutomationConfig | RemoteAutomationConfig
    user_permission_config: UserPermissionSerializableConfig
    debug: bool


def diagnostics_dump_entry_point(
    job_interface: BackgroundProcessInterface, args: DiagnosticsDumpArgs
) -> None:
    DiagnosticsDumpBackgroundJob().do_execute(job_interface, args)


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
        self, job_interface: BackgroundProcessInterface, args: DiagnosticsDumpArgs
    ) -> None:
        with job_interface.gui_context(
            UserPermissions.from_serialized_config(args.user_permission_config, permission_registry)
        ):
            self._do_execute(job_interface, args)

    def _do_execute(
        self, job_interface: BackgroundProcessInterface, args: DiagnosticsDumpArgs
    ) -> None:
        job_interface.send_progress_update(_("Diagnostics dump started..."))

        result = create_diagnostics_dump_v2(
            args.automation_config,
            DumpSelection(
                plugins=args.plugins,
                checkmk_server_host=args.checkmk_server_host,
            ).serialize(),
            args.timeout,
            debug=args.debug,
        )

        job_interface.send_progress_update(result.output)

        if result.tarfile_created:
            tarfile_path = result.tarfile_path
            # The dump is created on the selected site; the download page fetches
            # it from there via the diagnostics-dump-get-file automation.
            download_url = makeuri_contextless(
                request,
                [
                    ("site", args.site),
                    ("tarfile_name", str(Path(tarfile_path).name)),
                    ("timeout", args.timeout),
                ],
                filename="download_diagnostics_dump.py",
            )

            job_interface.send_progress_update(
                _("Dump file: %(tarfile_path)s") % {"tarfile_path": tarfile_path}
            )
            job_interface.send_result_message(
                _("%(icon_button)s Retrieve created dump file")
                % {
                    "icon_button": HTMLGenerator.render_icon_button(
                        url=download_url,
                        title=_("Download"),
                        icon=StaticIcon(IconNames.diagnostics_dump_file),
                        theme=make_theme(validate_choices=False),
                    )
                }
            )

        else:
            job_interface.send_result_message(_("Creating dump file failed"))


class PageDownloadDiagnosticsDump(Page):
    def __init__(self, diagnostics_dir: Path) -> None:
        super().__init__()
        self._diagnostics_dir = diagnostics_dir

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
            automation_config=make_automation_config(ctx.config.sites[site_id]),
            diagnostics_dir=self._diagnostics_dir,
            tarfile_name=tarfile_name,
            timeout=timeout,
            debug=ctx.config.debug,
        )

        response.set_content_type("application/x-tgz")
        response.set_content_disposition(ContentDispositionType.ATTACHMENT, tarfile_name)
        response.set_data(file_content)


# TODO(3.1): delete — serves older central sites that build explicit file
# lists remotely. The form of this version no longer walks any files.
class AutomationDiagnosticsDumpOsWalk(AutomationCommand[str]):
    def command_name(self) -> str:
        return "diagnostics-dump-os-walk"

    def execute(self, api_request: str) -> str:
        return json.dumps(list(os.walk(api_request)))

    def get_request(self, config: Config, request: Request) -> str:
        return request.get_ascii_input_mandatory("folder")


class AutomationDiagnosticsDumpGetFile(AutomationCommand[str]):
    # NOTE: AutomationCommandRegistry currently still contains types, not instances, so
    # we can have no argument here. When this has been fixed, we can pass the diagnostics
    # directory at registration time!
    def __init__(self) -> None:
        super().__init__()
        self._diagnostics_dir = cmk.utils.paths.diagnostics_dir

    def command_name(self) -> str:
        return "diagnostics-dump-get-file"

    def execute(self, api_request: str) -> bytes:
        return _get_local_diagnostics_dump_file(
            diagnostics_dir=self._diagnostics_dir, tarfile_name=api_request
        )

    def get_request(self, config: Config, request: Request) -> str:
        return request.get_ascii_input_mandatory("tarfile_name")


def _get_diagnostics_dump_file(
    *,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    diagnostics_dir: Path,
    tarfile_name: str,
    timeout: int,
    debug: bool,
) -> bytes:
    if isinstance(automation_config, LocalAutomationConfig):
        return _get_local_diagnostics_dump_file(
            diagnostics_dir=diagnostics_dir, tarfile_name=tarfile_name
        )

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


def _get_local_diagnostics_dump_file(*, diagnostics_dir: Path, tarfile_name: str) -> bytes:
    _validate_diagnostics_dump_tarfile_name(tarfile_name)
    tarfile_path = diagnostics_dir / tarfile_name
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
