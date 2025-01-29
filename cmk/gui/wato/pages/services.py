#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for services and discovery"""

import dataclasses
import json
import pprint
import traceback
from collections.abc import Collection, Container, Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict
from typing import Any, Literal, NamedTuple

from livestatus import SiteId

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site
from cmk.ccc.version import __version__, Version

import cmk.utils.render
from cmk.utils.check_utils import worst_service_state
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.hostaddress import HostName
from cmk.utils.html import get_html_state_marker
from cmk.utils.labels import HostLabelValueDict, Labels
from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.servicename import Item
from cmk.utils.statename import short_service_state_name

from cmk.checkengine.discovery import CheckPreviewEntry

from cmk.gui.background_job import JobStatusStates
from cmk.gui.breadcrumb import Breadcrumb, make_main_menu_breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, ungettext
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_display_options_dropdown,
    make_javascript_action,
    make_javascript_link,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuRenderer,
    PageMenuTopic,
)
from cmk.gui.page_menu_entry import disable_page_menu_entry, enable_page_menu_entry
from cmk.gui.pages import AjaxPage, PageRegistry, PageResult
from cmk.gui.site_config import sitenames
from cmk.gui.table import Foldable, Table, table_element
from cmk.gui.type_defs import HTTPVariables, PermissionName
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.popups import MethodAjax
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import DocReference
from cmk.gui.view_utils import format_plugin_output, LabelRenderType, render_labels
from cmk.gui.wato.pages.hosts import ModeEditHost
from cmk.gui.watolib.activate_changes import ActivateChanges, get_pending_changes_tooltip
from cmk.gui.watolib.audit_log_url import make_object_audit_log_url
from cmk.gui.watolib.automation_commands import AutomationCommand, AutomationCommandRegistry
from cmk.gui.watolib.automations import cmk_version_of_remote_automation_source
from cmk.gui.watolib.check_mk_automations import active_check
from cmk.gui.watolib.hosts_and_folders import (
    folder_from_request,
    folder_preserving_link,
    folder_tree,
    Host,
)
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.gui.watolib.rulespecs import rulespec_registry
from cmk.gui.watolib.services import (
    checkbox_id,
    checkbox_service,
    DiscoveryAction,
    DiscoveryOptions,
    DiscoveryResult,
    DiscoveryState,
    execute_discovery_job,
    get_check_table,
    has_discovery_action_specific_permissions,
    has_modification_specific_permissions,
    initial_discovery_result,
    perform_fix_all,
    perform_host_label_discovery,
    perform_service_discovery,
    ServiceDiscoveryBackgroundJob,
    UpdateType,
)
from cmk.gui.watolib.utils import may_edit_ruleset, mk_repr

from ._status_links import make_host_status_link

AjaxDiscoveryRequest = dict[str, Any]


class TableGroupEntry(NamedTuple):
    table_group: str
    show_bulk_actions: bool
    title: str
    help_text: str


def register(
    page_registry: PageRegistry,
    mode_registry: ModeRegistry,
    automation_command_registry: AutomationCommandRegistry,
) -> None:
    page_registry.register_page("ajax_service_discovery")(ModeAjaxServiceDiscovery)
    page_registry.register_page_handler(
        "ajax_popup_service_action_menu", ajax_popup_service_action_menu
    )
    page_registry.register_page("wato_ajax_execute_check")(ModeAjaxExecuteCheck)
    mode_registry.register(ModeDiscovery)
    automation_command_registry.register(AutomationServiceDiscoveryJob)
    automation_command_registry.register(AutomationServiceDiscoveryJobSnapshot)


class ModeDiscovery(WatoMode):
    """This mode is the entry point to the discovery page.

    It renders the static containter elements for the discovery page and optionally
    starts a the discovery data update process. Additional processing is done by
    ModeAjaxServiceDiscovery()
    """

    @classmethod
    def name(cls) -> str:
        return "inventory"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEditHost

    def _from_vars(self) -> None:
        self._host = folder_from_request(
            request.var("folder"), request.get_ascii_input("host")
        ).load_host(request.get_validated_type_input_mandatory(HostName, "host"))

        self._host.permissions.need_permission("read")

        action = DiscoveryAction.NONE
        if user.may("wato.services"):
            show_checkboxes = user.discovery_checkboxes
            if request.var("_scan") == "1":
                action = DiscoveryAction.REFRESH
        else:
            show_checkboxes = False

        show_parameters = user.parameter_column
        show_discovered_labels = user.discovery_show_discovered_labels
        show_plugin_names = user.discovery_show_plugin_names

        self._options = DiscoveryOptions(
            action=action,
            show_checkboxes=show_checkboxes,
            show_parameters=show_parameters,
            show_discovered_labels=show_discovered_labels,
            show_plugin_names=show_plugin_names,
            # Continue discovery even when one discovery function raises an exception. The detail
            # output will show which discovery function failed. This is better than failing the
            # whole discovery.
            ignore_errors=True,
        )

    def title(self) -> str:
        return _("Services of host %s") % self._host.name()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return service_page_menu(breadcrumb, self._host, self._options)

    def page(self) -> None:
        # This is needed to make the discovery page show the help toggle
        # button. The help texts on this page are only added dynamically via
        # AJAX.
        html.enable_help_toggle()
        self._container("datasources")
        self._container("fixall", True)
        self._async_progress_msg_container()
        self._container("service", True)
        html.javascript(
            "cmk.service_discovery.start(%s, %s, %s)"
            % (
                json.dumps(self._host.name()),
                json.dumps(self._host.folder().path()),
                json.dumps(self._options._asdict()),
            )
        )

    def _container(self, name: str, hidden: bool = False) -> None:
        html.open_div(id_=f"{name}_container", style=("display:none" if hidden else ""))
        html.close_div()

    def _async_progress_msg_container(self) -> None:
        html.open_div(id_="async_progress_msg")
        html.show_message(_("Loading. This may take a few seconds."))
        html.close_div()


class _AutomationServiceDiscoveryRequest(NamedTuple):
    host_name: HostName
    action: DiscoveryAction
    raise_errors: bool


class AutomationServiceDiscoveryJobSnapshot(AutomationCommand[HostName]):
    """Fetch the service discovery background job snapshot on a remote site"""

    def command_name(self) -> str:
        return "service-discovery-job-snapshot"

    def get_request(self) -> HostName:
        return request.get_validated_type_input_mandatory(HostName, "hostname")

    def execute(self, api_request: HostName) -> str:
        job = ServiceDiscoveryBackgroundJob(api_request)
        job_snapshot = asdict(job.get_status_snapshot())
        if "status" in job_snapshot:
            # additional conversion due to pydantic usage for status only
            job_snapshot["status"] = json.loads(job_snapshot["status"].json())
        return json.dumps(job_snapshot)


class AutomationServiceDiscoveryJob(AutomationCommand[_AutomationServiceDiscoveryRequest]):
    """Is called by _get_check_table() to execute the background job on a remote site"""

    def command_name(self) -> str:
        return "service-discovery-job"

    def get_request(self) -> _AutomationServiceDiscoveryRequest:
        host_name = request.get_validated_type_input_mandatory(HostName, "host_name")
        options = json.loads(request.get_ascii_input_mandatory("options"))
        action = DiscoveryAction(options["action"])
        raise_errors = not options["ignore_errors"]

        self._check_permissions(host_name)

        return _AutomationServiceDiscoveryRequest(
            host_name=host_name, action=action, raise_errors=raise_errors
        )

    def _check_permissions(self, host_name: HostName) -> None:
        user.need_permission("wato.hosts")

        host = Host.host(host_name)
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

    def execute(self, api_request: _AutomationServiceDiscoveryRequest) -> str:
        central_version = cmk_version_of_remote_automation_source(request)
        return execute_discovery_job(
            api_request.host_name,
            api_request.action,
            raise_errors=api_request.raise_errors,
        ).serialize(central_version)


class ModeAjaxServiceDiscovery(AjaxPage):
    def page(self) -> PageResult:
        check_csrf_token()
        user.need_permission("wato.hosts")

        api_request: AjaxDiscoveryRequest = self.webapi_request()
        request.del_var("request")  # Do not add this to URLs constructed later
        update_target = (
            None if (raw := api_request.get("update_target", None)) is None else UpdateType(raw)
        )
        update_source = api_request.get("update_source", None)
        api_request.setdefault("update_services", [])
        update_services = api_request.get("update_services", [])

        # Make Folder() be able to detect the current folder correctly
        request.set_var("folder", api_request["folder_path"])

        folder = folder_tree().folder(api_request["folder_path"])
        host = folder.host(api_request["host_name"])
        if not host:
            raise MKUserError("host", _("You called this page with an invalid host name."))
        host.permissions.need_permission("read")

        discovery_options = DiscoveryOptions(
            **api_request["discovery_options"]
        )  # FIXME: this violates typing.
        # Reuse the discovery result already known to the GUI or fetch a new one?
        previous_discovery_result = (
            DiscoveryResult.deserialize(raw)
            if (raw := api_request.get("discovery_result"))
            else None
        )

        # If the user has the wrong permissions, then we still return a discovery result
        # which is different from the REST API behavior.
        if not has_discovery_action_specific_permissions(discovery_options.action, update_target):
            discovery_options = discovery_options._replace(action=DiscoveryAction.NONE)

        discovery_result = self._perform_discovery_action(
            action=discovery_options.action,
            host=host,
            previous_discovery_result=previous_discovery_result,
            update_source=update_source,
            update_target=None if update_target is None else update_target.value,
            selected_services=self._resolve_selected_services(
                update_services, discovery_options.show_checkboxes
            ),
            raise_errors=not discovery_options.ignore_errors,
        )
        if self._sources_failed_on_first_attempt(previous_discovery_result, discovery_result):
            discovery_result = discovery_result._replace(
                check_table=(),
                nodes_check_table={},
                host_labels={},
                new_labels={},
                vanished_labels={},
                changed_labels={},
            )

        if not discovery_result.check_table_created and previous_discovery_result:
            discovery_result = previous_discovery_result._replace(
                job_status=discovery_result.job_status
            )

        show_checkboxes = user.discovery_checkboxes
        if show_checkboxes != discovery_options.show_checkboxes:
            user.discovery_checkboxes = discovery_options.show_checkboxes
        show_parameters = user.parameter_column
        if show_parameters != discovery_options.show_parameters:
            user.parameter_column = discovery_options.show_parameters
        show_discovered_labels = user.discovery_show_discovered_labels
        if show_discovered_labels != discovery_options.show_discovered_labels:
            user.discovery_show_discovered_labels = discovery_options.show_discovered_labels
        show_plugin_names = user.discovery_show_plugin_names
        if show_plugin_names != discovery_options.show_plugin_names:
            user.discovery_show_plugin_names = discovery_options.show_plugin_names

        renderer = DiscoveryPageRenderer(
            host,
            discovery_options,
        )
        page_code = renderer.render(discovery_result, api_request)
        datasources_code = renderer.render_datasources(discovery_result.sources)
        fix_all_code = renderer.render_fix_all(discovery_result)

        # Clean the requested action after performing it
        performed_action = discovery_options.action
        discovery_options = discovery_options._replace(action=DiscoveryAction.NONE)
        message = (
            self._get_status_message(previous_discovery_result, discovery_result, performed_action)
            if discovery_result.sources
            else None
        )

        return {
            "is_finished": not discovery_result.is_active(),
            "job_state": discovery_result.job_status["state"],
            "message": message,
            "body": page_code,
            "datasources": datasources_code,
            "fixall": fix_all_code,
            "page_menu": self._get_page_menu(discovery_options, host),
            "pending_changes_info": ActivateChanges().get_pending_changes_info().message,
            "pending_changes_tooltip": get_pending_changes_tooltip(),
            "discovery_options": discovery_options._asdict(),
            "discovery_result": discovery_result.serialize(Version.from_str(__version__)),
        }

    def _perform_discovery_action(
        self,
        action: DiscoveryAction,
        host: Host,
        previous_discovery_result: DiscoveryResult | None,
        update_source: str | None,
        update_target: str | None,
        selected_services: Container[tuple[str, Item]],
        *,
        raise_errors: bool,
    ) -> DiscoveryResult:
        if action == DiscoveryAction.NONE or not transactions.check_transaction():
            return initial_discovery_result(
                action,
                host,
                previous_discovery_result,
                raise_errors=raise_errors,
            )

        if action in (
            DiscoveryAction.REFRESH,
            DiscoveryAction.TABULA_RASA,
            DiscoveryAction.STOP,
        ):
            return get_check_table(host, action, raise_errors=raise_errors)

        discovery_result = initial_discovery_result(
            action, host, previous_discovery_result, raise_errors=raise_errors
        )

        match action:
            case DiscoveryAction.FIX_ALL:
                discovery_result = perform_fix_all(
                    discovery_result=discovery_result,
                    host=host,
                    raise_errors=raise_errors,
                )
            case DiscoveryAction.UPDATE_HOST_LABELS:
                discovery_result = perform_host_label_discovery(
                    action=action,
                    discovery_result=discovery_result,
                    host=host,
                    raise_errors=raise_errors,
                )
            case (
                DiscoveryAction.SINGLE_UPDATE
                | DiscoveryAction.BULK_UPDATE
                | DiscoveryAction.UPDATE_SERVICES
                | DiscoveryAction.UPDATE_SERVICE_LABELS
                | DiscoveryAction.UPDATE_DISCOVERY_PARAMETERS
                | DiscoveryAction.SINGLE_UPDATE_SERVICE_PROPERTIES
            ):
                discovery_result = perform_service_discovery(
                    action=action,
                    discovery_result=discovery_result,
                    update_source=update_source,
                    update_target=update_target,
                    host=host,
                    selected_services=selected_services,
                    raise_errors=raise_errors,
                )
            case DiscoveryAction.UPDATE_SERVICES:
                discovery_result = perform_service_discovery(
                    action=action,
                    discovery_result=discovery_result,
                    update_source=None,
                    update_target=None,
                    host=host,
                    selected_services=selected_services,
                    raise_errors=raise_errors,
                )
            case _:
                raise MKUserError("discovery", f"Unknown discovery action: {action}")

        return discovery_result

    @staticmethod
    def _resolve_selected_services(
        update_services: list[str], checkboxes_where_avaliable: bool
    ) -> Container[tuple[str, Item]]:
        if update_services:
            return {checkbox_service(e) for e in update_services}
        # empty list can mean everything or nothing.
        return () if checkboxes_where_avaliable else EVERYTHING

    def _get_page_menu(self, discovery_options: DiscoveryOptions, host: Host) -> str:
        """Render the page menu contents to reflect contect changes

        The page menu needs to be updated, just like the body of the page. We previously tried an
        incremental approach (render the page menu once and update it's elements later during each
        refresh), but it was a lot more complex to realize and resulted in inconsistencies. This is
        the simpler solution and less error prone.
        """
        page_menu = service_page_menu(self._get_discovery_breadcrumb(host), host, discovery_options)
        with output_funnel.plugged():
            PageMenuRenderer().show(
                page_menu, hide_suggestions=not user.get_tree_state("suggestions", "all", True)
            )
            return output_funnel.drain()

    def _get_discovery_breadcrumb(self, host: Host) -> Breadcrumb:
        with request.stashed_vars():
            request.set_var("host", host.name())
            mode = ModeDiscovery()
            return make_main_menu_breadcrumb(mode.main_menu()) + mode.breadcrumb()

    def _get_status_message(
        self,
        previous_discovery_result: DiscoveryResult | None,
        discovery_result: DiscoveryResult,
        performed_action: DiscoveryAction,
    ) -> str:
        if performed_action is DiscoveryAction.UPDATE_HOST_LABELS:
            return _("The discovered host labels have been updated.")

        cmk_check_entries = [
            e for e in discovery_result.check_table if DiscoveryState.is_discovered(e.check_source)
        ]

        if discovery_result.job_status["state"] == JobStatusStates.INITIALIZED:
            if discovery_result.is_active():
                return _("Initializing discovery...")
            if not cmk_check_entries:
                return _("No discovery information available. Please perform a rescan.")
            return _(
                "No fresh discovery information available. Using latest cached information. "
                "Please perform a rescan in case you want to discover the current state."
            )

        job_title = discovery_result.job_status.get("title", _("Service discovery"))
        duration_txt = cmk.utils.render.Age(discovery_result.job_status["duration"])
        finished_time = (
            discovery_result.job_status["started"] + discovery_result.job_status["duration"]
        )
        finished_txt = cmk.utils.render.date_and_time(finished_time)

        if discovery_result.job_status["state"] == JobStatusStates.RUNNING:
            return _("%s running for %s") % (job_title, duration_txt)

        if discovery_result.job_status["state"] == JobStatusStates.EXCEPTION:
            return _(
                "%s failed after %s: %s (see <tt>var/log/web.log</tt> for further information)"
            ) % (
                job_title,
                duration_txt,
                "\n".join(discovery_result.job_status["loginfo"]["JobException"]),
            )

        messages = []
        if self._sources_failed_on_first_attempt(previous_discovery_result, discovery_result):
            messages.append(
                _("The problems above might be caused by missing caches. Please trigger a rescan.")
            )

        if discovery_result.job_status["state"] == JobStatusStates.STOPPED:
            messages.append(
                _("%s was stopped after %s at %s.") % (job_title, duration_txt, finished_txt)
            )

        progress_update_log = discovery_result.job_status["loginfo"]["JobProgressUpdate"]
        warnings = [f"<br>{line}" for line in progress_update_log if line.startswith("WARNING")]

        if discovery_result.job_status["state"] == JobStatusStates.FINISHED and not warnings:
            return " ".join(messages)

        messages.extend(warnings)

        with output_funnel.plugged():
            with foldable_container(
                treename="service_discovery",
                id_="options",
                isopen=False,
                title=_("Job details"),
                indent=False,
            ):
                html.open_div(class_="log_output", style="height: 400px;", id_="progress_log")
                html.pre("\n".join(progress_update_log))
                html.close_div()
            messages.append(output_funnel.drain())

        return " ".join(messages)

    @staticmethod
    def _sources_failed_on_first_attempt(
        previous: DiscoveryResult | None,
        current: DiscoveryResult,
    ) -> bool:
        """Only consider CRIT sources failed"""
        return previous is None and any(source[0] == 2 for source in current.sources.values())


class DiscoveryPageRenderer:
    def __init__(self, host: Host, options: DiscoveryOptions) -> None:
        super().__init__()
        self._host = host
        self._options = options

    def render(self, discovery_result: DiscoveryResult, api_request: dict) -> str:
        with output_funnel.plugged():
            self._toggle_action_page_menu_entries(discovery_result)
            enable_page_menu_entry(html, "inline_help")
            self._show_discovered_host_labels(discovery_result)
            self._show_discovery_details(discovery_result, api_request)
            return output_funnel.drain()

    def render_fix_all(self, discovery_result: DiscoveryResult) -> str:
        with output_funnel.plugged():
            self._show_fix_all(discovery_result)
            return output_funnel.drain()

    def render_datasources(self, sources: Mapping[str, tuple[int, str]]) -> str | None:
        if not sources:
            return None

        states = [s for s, _output in sources.values()]
        overall_state = worst_service_state(*states, default=0)

        with output_funnel.plugged():
            # Colored overall state field
            html.open_div(class_="state_bar state%s" % overall_state)
            html.open_span()
            match overall_state:
                case 0:
                    html.icon("check")
                case 1:
                    html.icon("host_svc_problems_dark")
                case 2 | 3:
                    html.icon("host_svc_problems")
            html.close_span()
            html.close_div()

            # Output per data source
            html.open_div(class_="message_container")
            if overall_state == 0:
                html.h2(_("All datasources are OK"))
            else:
                num_problem_states: int = len([s for s in states if s != 0])
                html.h2(
                    ungettext(
                        "Problems with %d datasource detected",
                        "Problems with %d datasources detected",
                        num_problem_states,
                    )
                    % num_problem_states
                )

            html.open_table()
            for state, output in sources.values():
                html.open_tr()
                html.open_td()
                html.write_html(HTML.without_escaping(get_html_state_marker(state)))
                html.close_td()
                # Make sure not to show long output
                html.td(
                    format_plugin_output(
                        output.split("\n", 1)[0].replace(" ", ": ", 1),
                        request=request,
                    )
                )
                html.close_tr()
            html.close_table()

            html.close_div()

            return output_funnel.drain()

    def _show_discovered_host_labels(self, discovery_result: DiscoveryResult) -> None:
        if not discovery_result.host_labels and not discovery_result.vanished_labels:
            return None

        with table_element(
            table_id="host_labels",
            title=_("Discovered host labels (%s)") % len(discovery_result.host_labels),
            css="data",
            searchable=False,
            limit=False,
            sortable=False,
            foldable=Foldable.FOLDABLE_STATELESS,
            omit_update_header=False,
        ) as table:
            return self._render_host_labels(
                table,
                discovery_result,
            )

    def _render_host_labels(self, table: Table, discovery_result: DiscoveryResult) -> None:
        active_host_labels: dict[str, HostLabelValueDict] = {}
        changed_host_labels: dict[str, HostLabelValueDict] = {}

        for label_id, label in discovery_result.host_labels.items():
            # For visualization of the changed host labels the old value and the new value
            # of the host label are used the values are separated with an arrow (\u279c)
            if label_id in discovery_result.changed_labels:
                changed_host_labels.setdefault(
                    label_id,
                    {
                        "value": "{} \u279c {}".format(
                            discovery_result.changed_labels[label_id]["value"], label["value"]
                        ),
                        "plugin_name": label["plugin_name"],
                    },
                )
            if label_id not in {
                **discovery_result.new_labels,
                **discovery_result.vanished_labels,
                **discovery_result.changed_labels,
            }:
                active_host_labels.setdefault(label_id, label)

        self._create_host_label_row(
            table,
            discovery_result.new_labels,
            _("New"),
        )
        self._create_host_label_row(
            table,
            discovery_result.vanished_labels,
            _("Vanished"),
        )
        self._create_host_label_row(
            table,
            changed_host_labels,
            _("Changed"),
        )
        self._create_host_label_row(
            table,
            active_host_labels,
            _("Active"),
        )

    def _create_host_label_row(
        self, table: Table, host_labels: Mapping[str, HostLabelValueDict], text: str
    ) -> None:
        if not host_labels:
            return

        table.row()
        table.cell(_("Status"), text, css=["labelstate"])

        if not self._options.show_plugin_names:
            labels_html = render_labels(
                {label_id: label["value"] for label_id, label in host_labels.items()},
                "host",
                with_links=False,
                label_sources={label_id: "discovered" for label_id in host_labels.keys()},
                request=request,
            )
            table.cell(_("Host labels"), labels_html, css=["expanding"])
            return

        plugin_names = HTML.empty()
        labels_html = HTML.empty()
        for label_id, label in host_labels.items():
            plugin_names += HTMLWriter.render_p(label["plugin_name"])
            labels_html += render_labels(
                {label_id: label["value"]},
                "host",
                with_links=False,
                label_sources={label_id: "discovered"},
                request=request,
            )

        table.cell(_("Host labels"), labels_html, css=["expanding"])
        table.cell(_("Check plug-in"), plugin_names, css=["plugins"])
        return

    def _show_discovery_details(self, discovery_result: DiscoveryResult, api_request: dict) -> None:
        if not discovery_result.check_table:
            if not discovery_result.is_active() and self._host.is_cluster():
                self._show_empty_cluster_hint()
            return

        # We currently don't get correct information from cmk.base (the data sources). Better
        # don't display this until we have the information.
        # html.write_text_permissive("Using discovery information from %s" % cmk.utils.render.date_and_time(
        #    discovery_result.check_table_created))

        by_group = self._group_check_table_by_state(discovery_result.check_table)
        for entry in self._ordered_table_groups():
            checks = by_group.get(entry.table_group, [])
            if not checks:
                continue

            with html.form_context(
                "checks_%s" % entry.table_group, method="POST", action="wato.py"
            ):
                with table_element(
                    table_id="checks_%s" % entry.table_group,
                    title=f"{entry.title} ({len(checks)})",
                    css="data",
                    searchable=False,
                    limit=False,
                    sortable=False,
                    foldable=Foldable.FOLDABLE_STATELESS,
                    omit_update_header=False,
                    help=entry.help_text,
                    isopen=entry.table_group
                    not in (
                        DiscoveryState.CLUSTERED_NEW,
                        DiscoveryState.CLUSTERED_OLD,
                        DiscoveryState.CLUSTERED_VANISHED,
                    ),
                ) as table:
                    for check in sorted(checks, key=lambda e: e.description.lower()):
                        self._show_check_row(
                            table, discovery_result, api_request, check, entry.show_bulk_actions
                        )

                if entry.show_bulk_actions:
                    self._toggle_bulk_action_page_menu_entries(entry.table_group)
                html.hidden_fields()

    @staticmethod
    def _show_empty_cluster_hint() -> None:
        html.br()
        url = folder_preserving_link([("mode", "edit_ruleset"), ("varname", "clustered_services")])
        html.show_message(
            _(
                "Could not find any service for your cluster. You first need to "
                "specify which services of your nodes shal be added to the "
                'cluster. This is done using the <a href="%s">%s</a> ruleset.'
            )
            % (url, _("Clustered services"))
        )

    def _group_check_table_by_state(
        self, check_table: Iterable[CheckPreviewEntry]
    ) -> Mapping[str, Sequence[CheckPreviewEntry]]:
        by_group: dict[str, list[CheckPreviewEntry]] = {}
        for entry in check_table:
            by_group.setdefault(entry.check_source, []).append(entry)
        return by_group

    def _render_fix_all_element(self, title: str, count: int, href: str) -> None:
        html.open_li()
        html.open_a(href=href)
        html.span(title)
        html.span(str(count), class_="changed" if count else "")
        html.close_a()
        html.close_li()

    def _show_fix_all(self, discovery_result: DiscoveryResult) -> None:
        if not discovery_result:
            return

        if not user.may("wato.services"):
            return

        undecided_services = 0
        vanished_services = 0
        changed_services = 0
        new_host_labels = len(discovery_result.new_labels)
        vanished_host_labels = len(discovery_result.vanished_labels)
        changed_host_labels = len(discovery_result.changed_labels)

        for service in discovery_result.check_table:
            if service.check_source == DiscoveryState.CHANGED:
                changed_services += 1
            if service.check_source == DiscoveryState.UNDECIDED:
                undecided_services += 1
            if service.check_source == DiscoveryState.VANISHED:
                vanished_services += 1

        if all(
            v == 0
            for v in [
                changed_services,
                undecided_services,
                vanished_services,
                new_host_labels,
                vanished_host_labels,
                changed_host_labels,
            ]
        ):
            return

        html.icon("fixall", _("Service discovery details"))

        html.open_ul()
        self._render_fix_all_element(
            ungettext("Changed service: ", "Changed services: ", changed_services),
            changed_services,
            "#tree.table.checks_changed",
        )
        self._render_fix_all_element(
            ungettext("Undecided service: ", "Undecided services: ", undecided_services),
            undecided_services,
            "#tree.table.checks_new",
        )
        self._render_fix_all_element(
            ungettext("Vanished service: ", "Vanished services: ", vanished_services),
            vanished_services,
            "#tree.table.checks_vanished",
        )
        self._render_fix_all_element(
            ungettext("New host label: ", "New host labels: ", new_host_labels),
            new_host_labels,
            "#tree.table.host_labels",
        )
        self._render_fix_all_element(
            ungettext("Vanished host label: ", "Vanished host labels: ", new_host_labels),
            vanished_host_labels,
            "#tree.table.host_labels",
        )
        self._render_fix_all_element(
            ungettext("Changed host label: ", "Changed host labels: ", new_host_labels),
            changed_host_labels,
            "#tree.table.host_labels",
        )
        html.close_ul()

        if any(
            [
                changed_services,
                undecided_services,
                vanished_services,
                new_host_labels,
                vanished_host_labels,
                changed_host_labels,
            ]
        ):
            enable_page_menu_entry(html, "fixall")
        else:
            disable_page_menu_entry(html, "fixall")

    def _toggle_action_page_menu_entries(self, discovery_result: DiscoveryResult) -> None:
        if not user.may("wato.services"):
            return

        has_changed_services = any(
            check.check_source == DiscoveryState.CHANGED for check in discovery_result.check_table
        )
        has_changes = any(
            check.check_source
            in (DiscoveryState.UNDECIDED, DiscoveryState.VANISHED, DiscoveryState.CHANGED)
            for check in discovery_result.check_table
        )
        had_services_before = any(
            check.check_source in (DiscoveryState.MONITORED, DiscoveryState.VANISHED)
            for check in discovery_result.check_table
        )

        if discovery_result.is_active():
            enable_page_menu_entry(html, "stop")
            return

        disable_page_menu_entry(html, "stop")
        enable_page_menu_entry(html, "refresh")

        if (
            has_changes
            and user.may("wato.service_discovery_to_monitored")
            and user.may("wato.service_discovery_to_removed")
        ):
            enable_page_menu_entry(html, "fix_all")

        if (
            had_services_before
            and user.may("wato.service_discovery_to_undecided")
            and user.may("wato.service_discovery_to_monitored")
            and user.may("wato.service_discovery_to_ignored")
            and user.may("wato.service_discovery_to_removed")
        ):
            enable_page_menu_entry(html, "tabula_rasa")

        if has_changed_services:
            enable_page_menu_entry(html, "update_service_labels")
            enable_page_menu_entry(html, "update_discovery_parameters")

        if discovery_result.host_labels:
            enable_page_menu_entry(html, "update_host_labels")

        if had_services_before:
            enable_page_menu_entry(html, "show_checkboxes")
            enable_page_menu_entry(html, "show_parameters")
            enable_page_menu_entry(html, "show_discovered_labels")
            enable_page_menu_entry(html, "show_plugin_names")

    def _toggle_bulk_action_page_menu_entries(self, table_source: str) -> None:
        if not user.may("wato.services"):
            return

        match table_source:
            case DiscoveryState.MONITORED:
                if has_modification_specific_permissions(UpdateType.UNDECIDED):
                    self._enable_bulk_button(table_source, DiscoveryState.UNDECIDED)
                if has_modification_specific_permissions(UpdateType.IGNORED):
                    self._enable_bulk_button(table_source, DiscoveryState.IGNORED)

            case DiscoveryState.IGNORED:
                if may_edit_ruleset("ignored_services"):
                    if has_modification_specific_permissions(UpdateType.MONITORED):
                        self._enable_bulk_button(table_source, DiscoveryState.MONITORED)
                    if has_modification_specific_permissions(UpdateType.UNDECIDED):
                        self._enable_bulk_button(table_source, DiscoveryState.UNDECIDED)

            case DiscoveryState.VANISHED:
                if has_modification_specific_permissions(UpdateType.REMOVED):
                    self._enable_bulk_button(table_source, DiscoveryState.REMOVED)
                if has_modification_specific_permissions(UpdateType.IGNORED):
                    self._enable_bulk_button(table_source, DiscoveryState.IGNORED)

            case DiscoveryState.UNDECIDED:
                if has_modification_specific_permissions(UpdateType.MONITORED):
                    self._enable_bulk_button(table_source, DiscoveryState.MONITORED)
                if has_modification_specific_permissions(UpdateType.IGNORED):
                    self._enable_bulk_button(table_source, DiscoveryState.IGNORED)

    def _enable_bulk_button(self, source: str, target: str) -> None:
        enable_page_menu_entry(html, f"bulk_{source}_{target}")

    def _show_check_row(
        self,
        table: Table,
        discovery_result: DiscoveryResult,
        api_request: dict,
        entry: CheckPreviewEntry,
        show_bulk_actions: bool,
    ) -> None:
        statename = "" if entry.state is None else short_service_state_name(entry.state, "")
        if statename == "":
            statename = short_service_state_name(-1)
            stateclass = "state svcstate statep"
            table.row(css=["data"], state=0)
        else:
            assert entry.state is not None
            stateclass = f"state svcstate state{entry.state}"
            table.row(css=["data"], state=entry.state)

        self._show_bulk_checkbox(
            table,
            discovery_result,
            api_request,
            entry.check_plugin_name,
            entry.item,
            show_bulk_actions,
        )
        self._show_actions(table, discovery_result, entry)

        table.cell(
            _("State"),
            HTMLWriter.render_span(statename, class_=["state_rounded_fill"]),
            css=[stateclass],
        )
        table.cell(_("Service"), entry.description, css=["service"])
        table.cell(_("Summary"), css=["expanding"])
        self._show_status_detail(entry)

        if entry.check_source in [DiscoveryState.ACTIVE, DiscoveryState.ACTIVE_IGNORED]:
            ctype = "check_" + entry.check_plugin_name
        else:
            ctype = entry.check_plugin_name
        manpage_url = folder_preserving_link([("mode", "check_manpage"), ("check_type", ctype)])

        if self._options.show_parameters:
            table.cell(_("Check parameters"), css=["expanding"])
            self._show_check_parameters(entry)

        unchanged_labels: Labels = {}
        changed_labels: Labels = {}
        added_labels: Labels = {}
        removed_labels: Labels = {}
        if entry.check_source == DiscoveryState.CHANGED:
            unchanged_labels, changed_labels, added_labels, removed_labels = (
                self._calculate_changes(entry.old_labels, entry.new_labels)
            )
            _unchanged_parameters, changed_parameters, added_parameters, removed_parameters = (
                self._calculate_changes(
                    entry.old_discovered_parameters, entry.new_discovered_parameters
                )
            )

            table.cell(_("Discovered changes"))
            self._show_discovered_changes(
                changed_labels,
                added_labels,
                removed_labels,
                changed_parameters,
                added_parameters,
                removed_parameters,
            )

        if self._options.show_discovered_labels:
            table.cell(
                _("Previously discovered")
                if entry.check_source == DiscoveryState.CHANGED
                else _("Discovered service labels")
            )
            self._show_discovered_labels(entry.old_labels)

            if entry.check_source == DiscoveryState.CHANGED:
                table.cell(_("Newly discovered"))
                self._show_discovered_labels(unchanged_labels)
                self._show_discovered_labels(changed_labels, override_label_render_type="changed")
                self._show_discovered_labels(added_labels, override_label_render_type="added")
                self._show_discovered_labels(removed_labels, override_label_render_type="removed")

        if self._options.show_plugin_names:
            table.cell(
                _("Check plug-in"),
                HTMLWriter.render_a(content=ctype, href=manpage_url),
                css=["plugins"],
            )

    @staticmethod
    def _calculate_changes(
        old: Mapping[str, Any], new: Mapping[str, Any]
    ) -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
        unchanged = {}
        changed = {}
        added = {}
        removed = {}
        for key, value in new.items():
            if key in old and value == old[key]:
                unchanged[key] = value
            if key in old and value != old[key]:
                changed[key] = value
            if key not in old:
                added[key] = value
        for key, value in old.items():
            if key not in new:
                removed[key] = value
        return unchanged, changed, added, removed

    def _show_discovered_changes(
        self,
        changed_labels: Labels,
        added_labels: Labels,
        removed_labels: Labels,
        changed_parameters: Mapping[str, Any],
        added_parameters: Mapping[str, Any],
        removed_parameters: Mapping[str, Any],
    ) -> None:
        if changed_labels:
            html.p(
                ungettext("%d changed label", "%d changed labels", len(changed_labels))
                % len(changed_labels)
            )
        if added_labels:
            html.p(
                ungettext("%d new label", "%d new labels", len(added_labels)) % len(added_labels)
            )
        if removed_labels:
            html.p(
                ungettext("%d removed label", "%d removed labels", len(removed_labels))
                % len(removed_labels)
            )
        if changed_parameters:
            html.p(
                ungettext(
                    "%d discovery parameter changed",
                    "%d discovery parameters changed",
                    len(changed_parameters),
                )
                % len(changed_parameters)
            )
        if added_parameters:
            html.p(
                ungettext(
                    "%d discovery parameter added",
                    "%d discovery parameters added",
                    len(added_parameters),
                )
                % len(added_parameters)
            )
        if removed_parameters:
            html.p(
                ungettext(
                    "%d discovery parameter removed",
                    "%d discovery parameters removed",
                    len(removed_parameters),
                )
                % len(removed_parameters)
            )

    def _show_status_detail(self, entry: CheckPreviewEntry) -> None:
        if entry.check_source not in [
            DiscoveryState.CUSTOM,
            DiscoveryState.ACTIVE,
            DiscoveryState.CUSTOM_IGNORED,
            DiscoveryState.ACTIVE_IGNORED,
        ]:
            # Do not show long output
            output, *_details = entry.output.split("\n", 1)
            if output:
                html.write_html(
                    format_plugin_output(
                        output,
                        request=request,
                        shall_escape=active_config.escape_plugin_output,
                    )
                )
            return

        div_id = f"activecheck_{entry.description}"
        html.div(html.render_icon("reload", cssclass="reloading"), id_=div_id)
        html.javascript(
            "cmk.service_discovery.register_delayed_active_check(%s, %s, %s, %s, %s, %s);"
            % (
                json.dumps(self._host.site_id() or ""),
                json.dumps(self._host.folder().path()),
                json.dumps(self._host.name()),
                json.dumps(entry.check_plugin_name),
                json.dumps(entry.item),
                json.dumps(div_id),
            )
        )

    def _show_check_parameters(self, entry: CheckPreviewEntry) -> None:
        varname = self._get_ruleset_name(entry)
        if not varname or varname not in rulespec_registry:
            return

        params = entry.effective_parameters
        if not params:
            # Avoid error message in this case.
            # For instance: Ruleset requires a key, but discovered parameters are empty.
            return

        rulespec = rulespec_registry[varname]
        try:
            if isinstance(params, dict) and "tp_computed_params" in params:
                html.write_text_permissive(
                    _("Timespecific parameters computed at %s")
                    % cmk.utils.render.date_and_time(params["tp_computed_params"]["computed_at"])
                )
                html.br()
                params = params["tp_computed_params"]["params"]
            rulespec.valuespec.validate_datatype(params, "")
            rulespec.valuespec.validate_value(params, "")
            paramtext = rulespec.valuespec.value_to_html(params)
            html.write_html(HTML.with_escaping(paramtext))
        except Exception as e:
            if active_config.debug:
                err = traceback.format_exc()
            else:
                err = "%s" % e
            paramtext = "<b>{}</b>: {}<br>".format(_("Invalid check parameter"), err)
            paramtext += "{}: <tt>{}</tt><br>".format(_("Variable"), varname)
            paramtext += _("Parameters:")
            paramtext += "<pre>%s</pre>" % (pprint.pformat(params))
            html.write_text_permissive(paramtext)

    def _show_discovered_labels(
        self,
        service_labels: Labels,
        override_label_render_type: LabelRenderType | None = None,
    ) -> None:
        label_code = render_labels(
            service_labels,
            "service",
            with_links=False,
            label_sources={k: "discovered" for k in service_labels.keys()},
            override_label_render_type=override_label_render_type,
            request=request,
        )
        html.write_html(label_code)

    def _show_bulk_checkbox(
        self,
        table: Table,
        discovery_result: DiscoveryResult,
        api_request: dict,
        check_type: str,
        item: Item,
        show_bulk_actions: bool,
    ) -> None:
        if not self._options.show_checkboxes or not user.may("wato.services"):
            return

        if not show_bulk_actions:
            table.cell(css=["checkbox"])
            return

        css_classes = ["service_checkbox"]
        if discovery_result.is_active():
            css_classes.append("disabled")

        table.cell(
            html.render_input(
                "_toggle_group",
                type_="button",
                class_="checkgroup",
                onclick="cmk.selection.toggle_group_rows(this);",
                value="X",
            ),
            sortable=False,
            css=["checkbox"],
        )
        name = checkbox_id(check_type, item)
        checked = (
            self._options.action == DiscoveryAction.BULK_UPDATE
            and name in api_request["update_services"]
        )
        html.checkbox(varname=name, deflt=checked, class_=css_classes)

    def _show_actions(
        self,
        table: Table,
        discovery_result: DiscoveryResult,
        entry: CheckPreviewEntry,
    ) -> None:
        table.cell(css=["buttons"])
        if not user.may("wato.services"):
            html.empty_icon()
            html.empty_icon()
            html.empty_icon()
            html.empty_icon()
            return

        button_classes = ["service_button"]
        if discovery_result.is_active():
            button_classes.append("disabled")

        checkbox_name = checkbox_id(entry.check_plugin_name, entry.item)

        num_buttons = 0
        match entry.check_source:
            case DiscoveryState.CHANGED:
                if has_modification_specific_permissions(UpdateType.MONITORED):
                    html.icon_button(
                        url="",
                        title=_("Accept service properties"),
                        icon="accept",
                        class_=button_classes,
                        onclick=_start_js_call(
                            self._host,
                            self._options._replace(
                                action=DiscoveryAction.SINGLE_UPDATE_SERVICE_PROPERTIES
                            ),
                            request_vars={
                                "update_target": DiscoveryState.MONITORED,
                                "update_source": DiscoveryState.CHANGED,
                                "update_services": [checkbox_name],
                            },
                        ),
                    )
                    num_buttons += 1
                    if has_modification_specific_permissions(UpdateType.UNDECIDED):
                        num_buttons += self._icon_button(
                            DiscoveryState.MONITORED,
                            checkbox_name,
                            DiscoveryState.UNDECIDED,
                            "undecided",
                            button_classes,
                        )
                    if has_modification_specific_permissions(UpdateType.IGNORED):
                        num_buttons += self._icon_button(
                            DiscoveryState.MONITORED,
                            checkbox_name,
                            DiscoveryState.IGNORED,
                            "disabled",
                            button_classes,
                        )

            case DiscoveryState.MONITORED:
                if has_modification_specific_permissions(UpdateType.UNDECIDED):
                    num_buttons += self._icon_button(
                        DiscoveryState.MONITORED,
                        checkbox_name,
                        DiscoveryState.UNDECIDED,
                        "undecided",
                        button_classes,
                    )
                if has_modification_specific_permissions(UpdateType.IGNORED):
                    num_buttons += self._icon_button(
                        DiscoveryState.MONITORED,
                        checkbox_name,
                        DiscoveryState.IGNORED,
                        "disabled",
                        button_classes,
                    )

            case DiscoveryState.IGNORED:
                if may_edit_ruleset("ignored_services") and has_modification_specific_permissions(
                    UpdateType.MONITORED
                ):
                    num_buttons += self._icon_button(
                        DiscoveryState.IGNORED,
                        checkbox_name,
                        DiscoveryState.MONITORED,
                        "monitored",
                        button_classes,
                    )
                if has_modification_specific_permissions(UpdateType.IGNORED):
                    num_buttons += self._icon_button(
                        DiscoveryState.IGNORED,
                        checkbox_name,
                        DiscoveryState.UNDECIDED,
                        "undecided",
                        button_classes,
                    )
                    num_buttons += self._disabled_services_button(entry.description)

            case DiscoveryState.VANISHED:
                if has_modification_specific_permissions(UpdateType.REMOVED):
                    num_buttons += self._icon_button_removed(
                        entry.check_source, checkbox_name, button_classes
                    )

                if has_modification_specific_permissions(UpdateType.IGNORED):
                    num_buttons += self._icon_button(
                        DiscoveryState.VANISHED,
                        checkbox_name,
                        DiscoveryState.IGNORED,
                        "disabled",
                        button_classes,
                    )

            case DiscoveryState.UNDECIDED:
                if has_modification_specific_permissions(UpdateType.MONITORED):
                    num_buttons += self._icon_button(
                        DiscoveryState.UNDECIDED,
                        checkbox_name,
                        DiscoveryState.MONITORED,
                        "monitored",
                        button_classes,
                    )
                if has_modification_specific_permissions(UpdateType.IGNORED):
                    num_buttons += self._icon_button(
                        DiscoveryState.UNDECIDED,
                        checkbox_name,
                        DiscoveryState.IGNORED,
                        "disabled",
                        button_classes,
                    )

        while num_buttons < 2:
            html.empty_icon()
            num_buttons += 1

        if entry.check_source not in [
            DiscoveryState.UNDECIDED,
            DiscoveryState.IGNORED,
            DiscoveryState.CHANGED,
        ] and user.may("wato.rulesets"):
            num_buttons += self.rulesets_button(entry.description, self._host.name())
            num_buttons += self.check_parameters_button(entry, self._host.name())

        if entry.check_source == DiscoveryState.CHANGED:
            url_vars: HTTPVariables = [
                ("checkboxname", checkbox_name),
                ("hostname", self._host.name()),
                ("entry", json.dumps(dataclasses.astuple(entry))),
            ]
            html.popup_trigger(
                html.render_icon("menu", _("More options"), cssclass="iconbutton"),
                f"service_action_menu_{checkbox_name}",
                MethodAjax(endpoint="service_action_menu", url_vars=url_vars),
            )
            num_buttons += 1

        while num_buttons < 4:
            html.empty_icon()
            num_buttons += 1

    def _icon_button(
        self,
        table_source: Literal["new", "unchanged", "ignored", "vanished"],
        checkbox_name: str,
        table_target: Literal["new", "unchanged", "ignored"],
        descr_target: Literal["undecided", "monitored", "disabled"],
        button_classes: list[str],
    ) -> Literal[1]:
        options = self._options._replace(action=DiscoveryAction.SINGLE_UPDATE)
        html.icon_button(
            url="",
            title=_("Move to %s services") % descr_target,
            icon="service_to_%s" % descr_target,
            class_=button_classes,
            onclick=_start_js_call(
                self._host,
                options,
                request_vars={
                    "update_target": table_target,
                    "update_source": table_source,
                    "update_services": [checkbox_name],
                },
            ),
        )
        return 1

    def _icon_button_removed(
        self, table_source: Literal["vanished"], checkbox_name: str, button_classes: list[str]
    ) -> Literal[1]:
        options = self._options._replace(action=DiscoveryAction.SINGLE_UPDATE)
        html.icon_button(
            url="",
            title=_("Remove service"),
            icon="service_to_removed",
            class_=button_classes,
            onclick=_start_js_call(
                self._host,
                options,
                request_vars={
                    "update_target": DiscoveryState.REMOVED,
                    "update_source": table_source,
                    "update_services": [checkbox_name],
                },
            ),
        )
        return 1

    @classmethod
    def rulesets_button(cls, descr: str, hostname: str) -> Literal[1]:
        # Link to list of all rulesets affecting this service
        html.icon_button(
            cls.rulesets_button_link(descr, hostname),
            _("View and edit the parameters for this service"),
            "rulesets",
        )
        return 1

    @classmethod
    def rulesets_button_link(cls, descr: str, hostname: str) -> str:
        return folder_preserving_link(
            [
                ("mode", "object_parameters"),
                ("host", hostname),
                ("service", descr),
            ]
        )

    @classmethod
    def check_parameters_button(cls, entry: CheckPreviewEntry, hostname: str) -> Literal[0, 1]:
        if not entry.ruleset_name:
            return 0
        url = cls.check_parameters_button_link(entry, hostname)
        if not url:
            return 0
        html.icon_button(
            url, _("Edit and analyze the check parameters of this service"), "check_parameters"
        )
        return 1

    @classmethod
    def check_parameters_button_link(cls, entry: CheckPreviewEntry, hostname: str) -> str | None:
        if entry.check_source == DiscoveryState.MANUAL:
            return folder_preserving_link(
                [
                    ("mode", "edit_ruleset"),
                    ("varname", RuleGroup.StaticChecks(entry.ruleset_name)),
                    ("host", hostname),
                ]
            )
        ruleset_name = cls._get_ruleset_name(entry)
        if ruleset_name is None:
            return None

        return folder_preserving_link(
            [
                ("mode", "edit_ruleset"),
                ("varname", ruleset_name),
                ("host", hostname),
                (
                    "item",
                    mk_repr(entry.item).decode(),
                ),
                (
                    "service",
                    mk_repr(entry.description).decode(),
                ),
            ]
        )

    def _disabled_services_button(self, descr: str) -> Literal[1]:
        html.icon_button(
            folder_preserving_link(
                [
                    ("mode", "edit_ruleset"),
                    ("varname", "ignored_services"),
                    ("host", self._host.name()),
                    (
                        "item",
                        mk_repr(descr).decode(),
                    ),
                ]
            ),
            _("Edit and analyze the disabled services rules"),
            "rulesets",
        )
        return 1

    @classmethod
    def _get_ruleset_name(cls, entry: CheckPreviewEntry) -> str | None:
        if entry.ruleset_name == "logwatch":
            return "logwatch_rules"
        if entry.ruleset_name:
            return RuleGroup.CheckgroupParameters(entry.ruleset_name)
        if entry.check_source in [DiscoveryState.ACTIVE, DiscoveryState.ACTIVE_IGNORED]:
            return RuleGroup.ActiveChecks(entry.check_plugin_name)
        return None

    @staticmethod
    def _ordered_table_groups() -> list[TableGroupEntry]:
        return [
            TableGroupEntry(
                table_group=DiscoveryState.UNDECIDED,
                show_bulk_actions=True,
                title=_("Undecided services - currently not monitored"),
                help_text=_(
                    "These services have been found by the service discovery but are not yet added "
                    "to the monitoring. You should either decide to monitor them or to permanently "
                    "disable them. If you are sure that they are just transitional, just leave them "
                    "until they vanish."
                ),
            ),
            TableGroupEntry(
                DiscoveryState.VANISHED,
                show_bulk_actions=True,
                title=_("Vanished services - monitored, but no longer exist"),
                help_text=_(
                    "These services had been added to the monitoring by a previous discovery "
                    "but the actual items that are monitored are not present anymore. This might "
                    "be due to a real failure. In that case you should leave them in the monitoring. "
                    "If the actually monitored things are really not relevant for the monitoring "
                    "anymore then you should remove them in order to avoid UNKNOWN services in the "
                    "monitoring."
                ),
            ),
            TableGroupEntry(
                DiscoveryState.CLUSTERED_VANISHED,
                show_bulk_actions=False,
                title=_("Vanished clustered services - located on cluster host"),
                help_text=_(
                    "These services are mapped to a cluster host by a rule in one of the rulesets "
                    "<i>%s</i> or <i>%s</i>."
                )
                % (
                    _("Clustered services"),
                    _("Clustered services for overlapping clusters"),
                )
                + " "
                + _(
                    "They have been found on this host previously, but have now disappeared. "
                    "Note that they may still be monitored on the cluster."
                ),
            ),
            TableGroupEntry(
                DiscoveryState.CHANGED,
                show_bulk_actions=True,
                title=_("Changed services"),
                help_text=_(
                    "These services have been discovered and a change from the currently monitored "
                    "state has been detected."
                ),
            ),
            TableGroupEntry(
                DiscoveryState.MONITORED,
                show_bulk_actions=True,
                title=_("Monitored services"),
                help_text=_(
                    "These services have been found by the discovery and are currently being "
                    "monitored. No changes have been made to these services."
                ),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.IGNORED,
                show_bulk_actions=True,
                title=_("Disabled services"),
                help_text=_(
                    "These services are being discovered but have been disabled by creating a rule "
                    "in the rule set <i>Disabled services</i> or <i>Disabled checks</i>."
                ),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.ACTIVE,
                show_bulk_actions=False,
                title=_("Active checks"),
                help_text=_(
                    "These services do not use the Checkmk agent or Checkmk-SNMP engine but actively "
                    "call classical check plug-ins. They have been added by a rule in the section "
                    "<i>Active checks</i> or implicitly by Checkmk."
                ),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.MANUAL,
                show_bulk_actions=False,
                title=_("Enforced services"),
                help_text=_(
                    "These services have not been found by the discovery but have been added "
                    "manually by a Setup rule <i>Enforced services</i>."
                ),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.CUSTOM,
                show_bulk_actions=False,
                title=_("Custom checks - defined via rule"),
                help_text=_(
                    "These services do not use the Checkmk agent or Checkmk-SNMP engine but actively "
                    "call a classical check plug-in that you have installed yourself."
                ),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.CLUSTERED_OLD,
                show_bulk_actions=False,
                title=_("Monitored clustered services - located on cluster host"),
                help_text=_(
                    "These services are mapped to a cluster host by a rule in one of the rulesets "
                    "<i>%s</i> or <i>%s</i>."
                )
                % (
                    _("Clustered services"),
                    _("Clustered services for overlapping clusters"),
                ),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.CLUSTERED_NEW,
                show_bulk_actions=False,
                title=_("Undecided clustered services"),
                help_text=_(
                    "These services are mapped to a cluster host by a rule in one of the rulesets "
                    "<i>%s</i> or <i>%s</i>."
                )
                % (
                    _("Clustered services"),
                    _("Clustered services for overlapping clusters"),
                )
                + " "
                + _("They appear to be new to this node, but may still be already monitored."),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.CLUSTERED_IGNORED,
                show_bulk_actions=False,
                title=_("Disabled clustered services - located on cluster host"),
                help_text=_(
                    "These services have been found on this host and have been mapped to "
                    "a cluster host by a rule in the set <i>Clustered services</i> but disabled via "
                    "<i>Disabled services</i> or <i>Disabled checks</i>."
                ),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.ACTIVE_IGNORED,
                show_bulk_actions=False,
                title=_("Disabled active checks"),
                help_text=_(
                    "These services do not use the Checkmk agent or Checkmk-SNMP engine but actively "
                    "call classical check plug-ins. They have been added by a rule in the section "
                    "<i>Active checks</i> or implicitely by Checkmk. "
                    "These services have been disabled by creating a rule in the rule set "
                    "<i>Disabled services</i> oder <i>Disabled checks</i>."
                ),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.CUSTOM_IGNORED,
                show_bulk_actions=False,
                title=_("Disabled custom checks - defined via rule"),
                help_text=_(
                    "These services do not use the Checkmk agent or Checkmk-SNMP engine but actively "
                    "call a classical check plug-in that you have installed yourself. "
                    "These services have been disabled by creating a rule in the rule set "
                    "<i>Disabled services</i> oder <i>Disabled checks</i>."
                ),
            ),
        ]


class ModeAjaxExecuteCheck(AjaxPage):
    def _from_vars(self) -> None:
        self._site = SiteId(request.get_ascii_input_mandatory("site"))
        if self._site not in sitenames():
            raise MKUserError("site", _("You called this page with an invalid site."))

        self._host_name = request.get_validated_type_input_mandatory(HostName, "host")
        self._host = folder_from_request(request.var("folder"), self._host_name).host(
            self._host_name
        )
        if not self._host:
            raise MKUserError("host", _("You called this page with an invalid host name."))
        self._host.permissions.need_permission("read")

        # TODO: Validate
        self._check_type = request.get_ascii_input_mandatory("checktype")
        # TODO: Validate
        self._item = request.get_str_input_mandatory("item")

    def page(self) -> PageResult:
        check_csrf_token()
        try:
            active_check_result = active_check(
                self._site,
                self._host_name,
                self._check_type,
                self._item,
            )
            state = 3 if active_check_result.state is None else active_check_result.state
            output = active_check_result.output
        except Exception as e:
            state = 3
            output = "%s" % e

        return {
            "state": state,
            "state_name": short_service_state_name(state, "UNKN"),
            "output": output,
        }


def service_page_menu(breadcrumb: Breadcrumb, host: Host, options: DiscoveryOptions) -> PageMenu:
    menu = PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name="actions",
                title=_("Actions"),
                topics=[
                    PageMenuTopic(
                        title=_("Discovery"),
                        entries=list(_page_menu_service_configuration_entries(host, options)),
                    ),
                    PageMenuTopic(
                        title=_("On selected services"),
                        entries=list(_page_menu_selected_services_entries(host, options)),
                    ),
                    PageMenuTopic(
                        title=_("Host labels"),
                        entries=list(_page_menu_host_labels_entries(host, options)),
                    ),
                ],
            ),
            PageMenuDropdown(
                name="host",
                title=_("Host"),
                topics=[
                    PageMenuTopic(
                        title=_("For this host"),
                        entries=list(_page_menu_host_entries(host)),
                    ),
                ],
            ),
            PageMenuDropdown(
                name="settings",
                title=_("Settings"),
                topics=[
                    PageMenuTopic(
                        title=_("Settings"),
                        entries=list(_page_menu_settings_entries(host)),
                    ),
                ],
            ),
        ],
        breadcrumb=breadcrumb,
    )

    _extend_display_dropdown(menu, host, options)
    _extend_help_dropdown(menu)
    return menu


def _page_menu_host_entries(host: Host) -> Iterator[PageMenuEntry]:
    yield PageMenuEntry(
        title=_("Properties"),
        icon_name="edit",
        item=make_simple_link(
            folder_preserving_link([("mode", "edit_host"), ("host", host.name())])
        ),
    )

    if not host.is_cluster():
        yield PageMenuEntry(
            title=_("Test connection"),
            icon_name="analysis",
            item=make_simple_link(
                folder_preserving_link([("mode", "diag_host"), ("host", host.name())])
            ),
        )

    if user.may("wato.rulesets"):
        yield PageMenuEntry(
            title=_("Effective parameters"),
            icon_name="rulesets",
            item=make_simple_link(
                folder_preserving_link([("mode", "object_parameters"), ("host", host.name())])
            ),
        )

    yield make_host_status_link(host_name=host.name(), view_name="hoststatus")

    if user.may("wato.auditlog"):
        yield PageMenuEntry(
            title=_("Audit log"),
            icon_name="auditlog",
            item=make_simple_link(make_object_audit_log_url(host.object_ref())),
        )


def _page_menu_settings_entries(host: Host) -> Iterator[PageMenuEntry]:
    if not user.may("wato.rulesets"):
        return

    if host.is_cluster():
        yield PageMenuEntry(
            title=_("Clustered services"),
            icon_name="rulesets",
            item=make_simple_link(
                folder_preserving_link(
                    [("mode", "edit_ruleset"), ("varname", "clustered_services")]
                )
            ),
        )

    yield PageMenuEntry(
        title=_("Disabled services"),
        icon_name={
            "icon": "services",
            "emblem": "disable",
        },
        item=make_simple_link(
            folder_preserving_link([("mode", "edit_ruleset"), ("varname", "ignored_services")])
        ),
    )

    yield PageMenuEntry(
        title=_("Disabled checks"),
        icon_name={
            "icon": "check_plugins",
            "emblem": "disable",
        },
        item=make_simple_link(
            folder_preserving_link([("mode", "edit_ruleset"), ("varname", "ignored_checks")])
        ),
    )


def _extend_display_dropdown(menu: PageMenu, host: Host, options: DiscoveryOptions) -> None:
    display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())
    display_dropdown.topics.insert(
        0,
        PageMenuTopic(
            title=_("Details"),
            entries=[
                _page_menu_entry_show_checkboxes(host, options),
                _page_menu_entry_show_parameters(host, options),
                _page_menu_entry_show_discovered_labels(host, options),
                _page_menu_entry_show_plugin_names(host, options),
            ],
        ),
    )


def _extend_help_dropdown(menu: PageMenu) -> None:
    menu.add_doc_reference(_("Beginner's guide: Configuring services"), DocReference.INTRO_SERVICES)
    menu.add_doc_reference(_("Understanding and configuring services"), DocReference.WATO_SERVICES)


def _page_menu_entry_show_parameters(host: Host, options: DiscoveryOptions) -> PageMenuEntry:
    return PageMenuEntry(
        title=_("Show check parameters"),
        icon_name="toggle_on" if options.show_parameters else "toggle_off",
        item=make_simple_link(
            _checkbox_js_url(
                host,
                options._replace(show_parameters=not options.show_parameters),
            )
        ),
        name="show_parameters",
        css_classes=["toggle"],
    )


def _page_menu_entry_show_checkboxes(host: Host, options: DiscoveryOptions) -> PageMenuEntry:
    return PageMenuEntry(
        title=_("Show checkboxes"),
        icon_name="toggle_on" if options.show_checkboxes else "toggle_off",
        item=make_simple_link(
            _checkbox_js_url(
                host,
                options._replace(show_checkboxes=not options.show_checkboxes),
            )
        ),
        name="show_checkboxes",
        css_classes=["toggle"],
    )


def _checkbox_js_url(host: Host, options: DiscoveryOptions) -> str:
    return "javascript:%s" % make_javascript_action(_start_js_call(host, options))


def _page_menu_entry_show_discovered_labels(host: Host, options: DiscoveryOptions) -> PageMenuEntry:
    return PageMenuEntry(
        title=_("Show discovered service labels"),
        icon_name="toggle_on" if options.show_discovered_labels else "toggle_off",
        item=make_simple_link(
            _checkbox_js_url(
                host,
                options._replace(show_discovered_labels=not options.show_discovered_labels),
            )
        ),
        name="show_discovered_labels",
        css_classes=["toggle"],
    )


def _page_menu_entry_show_plugin_names(host: Host, options: DiscoveryOptions) -> PageMenuEntry:
    return PageMenuEntry(
        title=_("Show plug-in names"),
        icon_name="toggle_on" if options.show_plugin_names else "toggle_off",
        item=make_simple_link(
            _checkbox_js_url(
                host,
                options._replace(show_plugin_names=not options.show_plugin_names),
            )
        ),
        name="show_plugin_names",
        css_classes=["toggle"],
    )


def _page_menu_service_configuration_entries(
    host: Host, options: DiscoveryOptions
) -> Iterator[PageMenuEntry]:
    yield PageMenuEntry(
        title=_("Accept all"),
        icon_name="accept",
        item=make_javascript_link(
            _start_js_call(
                host,
                options._replace(action=DiscoveryAction.FIX_ALL),
            ),
        ),
        name="fixall",
        is_enabled=False,
        is_shortcut=True,
        css_classes=["action"],
    )

    yield PageMenuEntry(
        title=_("Remove all and find new"),
        icon_name="services_tabula_rasa",
        item=make_javascript_link(
            _start_js_call(host, options._replace(action=DiscoveryAction.TABULA_RASA))
        ),
        name="tabula_rasa",
        is_enabled=False,
        css_classes=["action"],
    )

    yield PageMenuEntry(
        title=_("Rescan"),
        icon_name="services_refresh",
        item=make_javascript_link(
            _start_js_call(host, options._replace(action=DiscoveryAction.REFRESH))
        ),
        name="refresh",
        is_enabled=False,
        is_shortcut=True,
        css_classes=["action"],
    )

    yield PageMenuEntry(
        title=_("Stop job"),
        icon_name="services_stop",
        item=make_javascript_link(
            _start_js_call(host, options._replace(action=DiscoveryAction.STOP))
        ),
        name="stop",
        is_enabled=False,
        css_classes=["action"],
    )


class BulkEntry(NamedTuple):
    is_shortcut: bool
    is_show_more: bool
    source: str
    target: str
    title: str
    explanation: str | None


def _page_menu_selected_services_entries(
    host: Host, options: DiscoveryOptions
) -> Iterator[PageMenuEntry]:
    yield PageMenuEntry(
        title=_("Add missing, remove vanished"),
        icon_name="services_fix_all",
        item=make_javascript_link(
            _start_js_call(host, options._replace(action=DiscoveryAction.UPDATE_SERVICES))
        ),
        name="fix_all",
        is_enabled=False,
        is_shortcut=False,
        css_classes=["action"],
    )

    for entry in [
        BulkEntry(
            True,
            False,
            DiscoveryState.UNDECIDED,
            DiscoveryState.MONITORED,
            _("Monitor undecided services"),
            _("Add all detected but not yet monitored services to the monitoring."),
        ),
        BulkEntry(
            False,
            False,
            DiscoveryState.UNDECIDED,
            DiscoveryState.IGNORED,
            _("Disable undecided services"),
            None,
        ),
        BulkEntry(
            False,
            True,
            DiscoveryState.MONITORED,
            DiscoveryState.UNDECIDED,
            _("Declare monitored services as undecided"),
            None,
        ),
        BulkEntry(
            False,
            True,
            DiscoveryState.MONITORED,
            DiscoveryState.IGNORED,
            _("Disable monitored services"),
            None,
        ),
        BulkEntry(
            False,
            True,
            DiscoveryState.IGNORED,
            DiscoveryState.MONITORED,
            _("Monitor disabled services"),
            None,
        ),
        BulkEntry(
            False,
            True,
            DiscoveryState.IGNORED,
            DiscoveryState.UNDECIDED,
            _("Declare disabled services as undecided"),
            None,
        ),
        BulkEntry(
            True,
            False,
            DiscoveryState.VANISHED,
            DiscoveryState.REMOVED,
            _("Remove vanished services"),
            None,
        ),
        BulkEntry(
            False,
            True,
            DiscoveryState.VANISHED,
            DiscoveryState.IGNORED,
            _("Disable vanished services"),
            None,
        ),
    ]:
        yield PageMenuEntry(
            title=entry.title,
            icon_name="service_to_%s" % entry.target,
            item=make_javascript_link(
                _start_js_call(
                    host,
                    options._replace(action=DiscoveryAction.BULK_UPDATE),
                    request_vars={
                        "update_target": entry.target,
                        "update_source": entry.source,
                    },
                )
            ),
            name=f"bulk_{entry.source}_{entry.target}",
            is_enabled=False,
            is_shortcut=entry.is_shortcut,
            is_show_more=entry.is_show_more,
            css_classes=["action"],
        )
    yield PageMenuEntry(
        title=_("Update service labels"),
        icon_name="update_service_labels",
        item=make_javascript_link(
            _start_js_call(
                host,
                options._replace(action=DiscoveryAction.UPDATE_SERVICE_LABELS),
                request_vars={
                    "update_target": DiscoveryState.MONITORED,
                    "update_source": DiscoveryState.CHANGED,
                },
            )
        ),
        name="update_service_labels",
        is_enabled=False,
        is_shortcut=False,
        css_classes=["action"],
    )
    yield PageMenuEntry(
        title=_("Update discovery parameters"),
        icon_name="update_discovery_parameters",
        item=make_javascript_link(
            _start_js_call(
                host,
                options._replace(action=DiscoveryAction.UPDATE_DISCOVERY_PARAMETERS),
                request_vars={
                    "update_target": DiscoveryState.MONITORED,
                    "update_source": DiscoveryState.CHANGED,
                },
            )
        ),
        name="update_discovery_parameters",
        is_enabled=False,
        is_shortcut=False,
        css_classes=["action"],
    )


def _page_menu_host_labels_entries(
    host: Host, options: DiscoveryOptions
) -> Iterator[PageMenuEntry]:
    yield PageMenuEntry(
        title=_("Update host labels"),
        icon_name="update_host_labels",
        item=make_javascript_link(
            _start_js_call(host, options._replace(action=DiscoveryAction.UPDATE_HOST_LABELS))
        ),
        name="update_host_labels",
        is_enabled=False,
        is_shortcut=False,
        is_suggested=True,
        css_classes=["action"],
    )


def _start_js_call(host: Host, options: DiscoveryOptions, request_vars: dict | None = None) -> str:
    return f"cmk.service_discovery.start({json.dumps(host.name())}, {json.dumps(host.folder().path())}, {json.dumps(options._asdict())}, {json.dumps(transactions.get())}, {json.dumps(request_vars)})"


def ajax_popup_service_action_menu() -> None:
    checkbox_name = request.get_ascii_input_mandatory("checkboxname")
    hostname = request.get_validated_type_input_mandatory(HostName, "hostname")
    entry = CheckPreviewEntry(*json.loads(request.get_ascii_input_mandatory("entry")))
    if checkbox_name is None or hostname is None:
        html.show_error(_("Cannot render dropdown: Missing required information"))
        return

    html.open_a(href=DiscoveryPageRenderer.rulesets_button_link(entry.description, hostname))
    html.icon("rulesets")
    html.write_text_permissive(_("View and edit the parameters for this service"))
    html.close_a()

    check_parameters_url = DiscoveryPageRenderer.check_parameters_button_link(entry, hostname)
    if not check_parameters_url:
        return
    html.open_a(href=check_parameters_url)
    html.icon("check_parameters")
    html.write_text_permissive(_("Edit and analyse the check parameters for this service"))
    html.close_a()
