#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Modes for services and discovery"""

import ast
import os
import json
import traceback
import time
import pprint
import sys
import re
from hashlib import sha256
from typing import NamedTuple, Text, List, Optional  # pylint: disable=unused-import

import cmk
import cmk.utils.store
from cmk.utils.defines import short_service_state_name
import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher

import cmk.gui.config as config
import cmk.gui.watolib as watolib
from cmk.gui.table import table_element
from cmk.gui.background_job import BackgroundProcessInterface, JobStatusStates  # pylint: disable=unused-import
from cmk.gui.gui_background_job import job_registry

from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError, MKGeneralException

from cmk.gui.watolib import (
    automation_command_registry,
    AutomationCommand,
)
from cmk.gui.watolib.automations import (
    sync_changes_before_remote_automation,
    check_mk_automation,
)
from cmk.gui.watolib.rulespecs import rulespec_registry
from cmk.gui.watolib.rulesets import RuleConditions

from cmk.gui.plugins.wato import (
    host_status_button,
    global_buttons,
    may_edit_ruleset,
    mode_registry,
    WatoMode,
    WatoBackgroundJob,
)

from cmk.gui.plugins.wato.utils.context_buttons import changelog_button

DiscoveryResult = NamedTuple("DiscoveryResult", [
    ("job_status", dict),
    ("check_table_created", int),
    ("check_table", list),
])


# Would rather use an Enum for this, but this information is exported to javascript
# using JSON and Enum is not serializable
#TODO In the future cleanup check_source (passive/active/custom/legacy) and
# check_state:
# - passive: new/vanished/old/ignored/removed
# - active/custom/legacy: old/ignored
class DiscoveryState(object):
    UNDECIDED = "new"
    VANISHED = "vanished"
    MONITORED = "old"
    IGNORED = "ignored"
    REMOVED = "removed"

    MANUAL = "manual"
    ACTIVE = "active"
    CUSTOM = "custom"
    CLUSTERED_OLD = "clustered_old"
    CLUSTERED_NEW = "clustered_new"
    CLUSTERED_VANISHED = "clustered_vanished"
    CLUSTERED_IGNORED = "clustered_ignored"
    ACTIVE_IGNORED = "active_ignored"
    CUSTOM_IGNORED = "custom_ignored"
    # TODO: Were removed in 1.6 from base. Keeping this for
    # compatibility with older remote sites. Remove with 1.7.
    LEGACY = "legacy"
    LEGACY_IGNORED = "legacy_ignored"

    @classmethod
    def is_discovered(cls, table_source):
        return table_source in [
            cls.UNDECIDED,
            cls.VANISHED,
            cls.MONITORED,
            cls.IGNORED,
            cls.REMOVED,
            cls.CLUSTERED_OLD,
            cls.CLUSTERED_NEW,
            cls.CLUSTERED_VANISHED,
            cls.CLUSTERED_IGNORED,
        ]


# Would rather use an Enum for this, but this information is exported to javascript
# using JSON and Enum is not serializable
class DiscoveryAction(object):
    NONE = ""
    STOP = "stop"
    SCAN = "scan"
    FIX_ALL = "fix_all"
    REFRESH = "refresh"
    SINGLE_UPDATE = "single_update"
    BULK_UPDATE = "bulk_update"


DiscoveryOptions = NamedTuple("DiscoveryOptions", [
    ("action", str),
    ("show_checkboxes", bool),
    ("show_parameters", bool),
    ("show_discovered_labels", bool),
    ("ignore_errors", bool),
])

StartDiscoveryRequest = NamedTuple("StartDiscoveryRequest", [
    ("host", watolib.Host),
    ("folder", watolib.Folder),
    ("options", DiscoveryOptions),
])

TableGroupEntry = NamedTuple("TableGroupEntry", [
    ("table_group", str),
    ("show_bulk_actions", bool),
    ("title", Text),
    ("help_text", Text),
])


@mode_registry.register
class ModeDiscovery(WatoMode):
    """This mode is the entry point to the discovery page.

    It renders the static containter elements for the discovery page and optionally
    starts a the discovery data update process. Additional processing is done by
    ModeAjaxServiceDiscovery()
    """
    @classmethod
    def name(cls):
        return "inventory"

    @classmethod
    def permissions(cls):
        return ["hosts"]

    def _from_vars(self):
        self._host = watolib.Folder.current().host(html.get_ascii_input("host"))
        if not self._host:
            raise MKUserError("host", _("You called this page with an invalid host name."))

        self._host.need_permission("read")

        action = DiscoveryAction.NONE
        if config.user.may("wato.services"):
            show_checkboxes = config.user.load_file("discovery_checkboxes", False)
            if html.request.var("_scan") == "1":
                action = DiscoveryAction.SCAN
        else:
            show_checkboxes = False

        show_parameters = not config.user.load_file("parameter_column", False)
        show_discovered_labels = not config.user.load_file("discovery_show_discovered_labels",
                                                           False)

        self._options = DiscoveryOptions(
            action=action,
            show_checkboxes=show_checkboxes,
            show_parameters=show_parameters,
            show_discovered_labels=show_discovered_labels,
            ignore_errors=bool(html.request.var("ignoreerrors")),
        )

    def title(self):
        return _("Services of host %s") % self._host.name()

    def buttons(self):
        global_buttons()
        html.context_button(_("Folder"), watolib.folder_preserving_link([("mode", "folder")]),
                            "back")

        host_status_button(self._host.name(), "host")

        html.context_button(
            _("Properties"),
            watolib.folder_preserving_link([("mode", "edit_host"), ("host", self._host.name())]),
            "edit")

        if config.user.may('wato.rulesets'):
            html.context_button(
                _("Parameters"),
                watolib.folder_preserving_link([("mode", "object_parameters"),
                                                ("host", self._host.name())]), "rulesets")
            if self._host.is_cluster():
                html.context_button(
                    _("Clustered services"),
                    watolib.folder_preserving_link([("mode", "edit_ruleset"),
                                                    ("varname", "clustered_services")]), "rulesets")

        if not self._host.is_cluster():
            html.context_button(
                _("Diagnostic"),
                watolib.folder_preserving_link([("mode", "diag_host"),
                                                ("host", self._host.name())]), "diagnose")

        html.context_button(
            _("Disabled services"),
            watolib.folder_preserving_link([("mode", "edit_ruleset"),
                                            ("varname", "ignored_services")]), "disabled_service")

        html.context_button(
            _("Disabled checks"),
            watolib.folder_preserving_link([("mode", "edit_ruleset"),
                                            ("varname", "ignored_checks")]), "check_parameters")

    def page(self):
        # This is needed to make the discovery page show the help toggle
        # button. The help texts on this page are only added dynamically via
        # AJAX.
        html.enable_help_toggle()
        self._async_progress_msg_container()
        self._service_container()
        html.javascript("cmk.service_discovery.start(%s, %s, %s)" %
                        (json.dumps(self._host.name()), json.dumps(
                            self._host.folder().path()), json.dumps(self._options._asdict())))

    def _async_progress_msg_container(self):
        html.open_div(id_="async_progress_msg")
        html.show_info(_("Loading..."))
        html.close_div()

    def _service_container(self):
        html.open_div(id_="service_container", style="display:none")
        html.close_div()


def _get_check_table(request):
    # type: (StartDiscoveryRequest) -> DiscoveryResult
    """Gathers the check table using a background job

    Cares about handling local / remote sites using an automation call. In both cases
    the ServiceDiscoveryBackgroundJob is executed to care about collecting the check
    table asynchronously. In case of a remote site the chain is:

    Starting from central site:

    _get_check_table()
          |
          v
    automation service-discovery-job-discover
          |
          v
    to remote site
          |
          v
    AutomationServiceDiscoveryJob().execute()
          |
          v
    _get_check_table()
    """
    if request.options.action == DiscoveryAction.REFRESH:
        watolib.add_service_change(
            request.host, "refresh-autochecks",
            _("Refreshed check configuration of host '%s'") % request.host.name())

    if config.site_is_local(request.host.site_id()):
        return execute_discovery_job(request)

    discovery_result = _get_check_table_from_remote(request)
    discovery_result.check_table = _add_missing_service_labels(discovery_result.check_table)
    return discovery_result


# 1.6.0b4 introduced the service labels column which might be missing when
# fetching information from remote sites.
def _add_missing_service_labels(check_table):
    return [(e + ({},) if len(e) < 11 else e) for e in check_table]


def _get_check_table_from_remote(request):
    """Gathers the check table from a remote site

    Cares about pre 1.6 sites that does not support the new service-discovery-job API call.
    Falling back to the previously existing try-inventry and inventory automation calls.
    """
    try:
        sync_changes_before_remote_automation(request.host.site_id())

        return DiscoveryResult(*ast.literal_eval(
            watolib.do_remote_automation(config.site(request.host.site_id()),
                                         "service-discovery-job", [
                                             ("host_name", request.host.name()),
                                             ("options", json.dumps(request.options._asdict())),
                                         ])))
    except watolib.MKAutomationException as e:
        if "Invalid automation command: service-discovery-job" not in "%s" % e:
            raise

        # Compatibility for pre 1.6 remote sites.
        # TODO: Replace with helpful exception in 1.7.
        if request.options.action == DiscoveryAction.REFRESH:
            _counts, _failed_hosts = check_mk_automation(
                request.host.site_id(), "inventory",
                ["@scan", "refresh", request.host.name()])

        if request.options.action == DiscoveryAction.SCAN:
            options = ["@scan"]
        else:
            options = ["@noscan"]

        if not request.options.ignore_errors:
            options.append("@raiseerrors")

        options.append(request.host.name())

        check_table = check_mk_automation(request.host.site_id(), "try-inventory", options)

        return DiscoveryResult(
            job_status={
                "is_active": False,
                "state": JobStatusStates.INITIALIZED,
            },
            check_table=check_table,
            check_table_created=time.time(),
        )


@automation_command_registry.register
class AutomationServiceDiscoveryJob(AutomationCommand):
    """Is called by _get_check_table() to execute the background job on a remote site"""
    def command_name(self):
        return "service-discovery-job"

    def get_request(self):
        # type: () -> StartDiscoveryRequest
        config.user.need_permission("wato.hosts")

        host_name = html.get_ascii_input("host_name")
        if host_name is None:
            raise MKGeneralException(_("Host is missing"))
        host = watolib.Host.host(host_name)
        if host is None:
            raise MKGeneralException(
                _("Host %s does not exist on remote site %s. This "
                  "may be caused by a failed configuration synchronization. Have a look at "
                  "the <a href=\"wato.py?folder=&mode=changelog\">activate changes page</a> "
                  "for further information.") % (host_name, config.omd_site()))
        host.need_permission("read")

        options = json.loads(html.get_ascii_input("options"))
        return StartDiscoveryRequest(host=host,
                                     folder=host.folder(),
                                     options=DiscoveryOptions(**options))

    def execute(self, request):
        # type: (StartDiscoveryRequest) -> str
        return repr(tuple(execute_discovery_job(request)))


def execute_discovery_job(request):
    # type: (StartDiscoveryRequest) -> DiscoveryResult
    """Either execute the discovery job to scan the host or return the discovery result
    based on the currently cached data"""
    job = ServiceDiscoveryBackgroundJob(request.host.name())

    if not job.is_active() and request.options.action in [
            DiscoveryAction.SCAN, DiscoveryAction.REFRESH
    ]:
        job.set_function(job.discover, request)
        job.start()

    if job.is_active() and request.options.action == DiscoveryAction.STOP:
        job.stop()

    r = job.get_result(request)
    return r


@job_registry.register
class ServiceDiscoveryBackgroundJob(WatoBackgroundJob):
    """The background job is always executed on the site where the host is located on"""
    job_prefix = "service_discovery"
    housekeeping_max_age_sec = 86400  # 1 day
    housekeeping_max_count = 20

    @classmethod
    def gui_title(cls):
        return _("Service discovery")

    def __init__(self, host_name):
        # type: (str) -> None
        job_id = "%s-%s" % (self.job_prefix, host_name)
        kwargs = {
            "title": _("Service discovery"),
            "stoppable": True,
            "host_name": host_name,
        }
        last_job_status = WatoBackgroundJob(job_id).get_status()
        if "duration" in last_job_status:
            kwargs["estimated_duration"] = last_job_status["duration"]

        super(ServiceDiscoveryBackgroundJob, self).__init__(job_id, **kwargs)

    def discover(self, request, job_interface):
        # type: (StartDiscoveryRequest, BackgroundProcessInterface) -> None
        """Target function of the background job"""
        print "Starting job..."
        if request.options.action == DiscoveryAction.SCAN:
            self._jobstatus.update_status({"title": _("Full scan")})
            self._perform_service_scan(request)

        elif request.options.action == DiscoveryAction.REFRESH:
            self._jobstatus.update_status({"title": _("Automatic refresh")})
            self._perform_automatic_refresh(request)

        else:
            raise NotImplementedError()
        print "Completed."

    def _perform_service_scan(self, request):
        """The try-inventory automation refreshes the Check_MK internal cache and makes the new
        information available to the next try-inventory call made by get_result()."""
        result = check_mk_automation(request.host.site_id(), "try-inventory",
                                     self._get_automation_options(request))
        sys.stdout.write(result["output"])

    def _perform_automatic_refresh(self, request):
        _counts, _failed_hosts = check_mk_automation(
            request.host.site_id(), "inventory",
            ["@scan", "refresh", request.host.name()])
        # In distributed sites this must not add a change on the remote site. We need to build
        # the way back to the central site and show the information there.
        #count_added, _count_removed, _count_kept, _count_new = counts[request.host.name()]
        #message = _("Refreshed check configuration of host '%s' with %d services") % \
        #            (request.host.name(), count_added)
        #watolib.add_service_change(request.host, "refresh-autochecks", message)

    def _get_automation_options(self, request):
        # type: (StartDiscoveryRequest) -> List[str]
        if request.options.action == DiscoveryAction.SCAN:
            options = ["@scan"]
        else:
            options = ["@noscan"]

        if not request.options.ignore_errors:
            options.append("@raiseerrors")

        options.append(request.host.name())

        return options

    def get_result(self, request):
        # tupe: (StartDiscoveryRequest) -> DiscoveryResult
        """Executed from the outer world to report about the job state"""
        job_status = self.get_status()
        job_status["is_active"] = self.is_active()

        # TODO: Use the correct time. This is difficult because cmk_base does not have a single
        # time for all data of a host. The data sources should be able to provide this information
        # somehow.
        check_table_created = time.time()
        result = check_mk_automation(
            request.host.site_id(), "try-inventory",
            ["@noscan", "@raiseerrors", request.host.name()])

        return DiscoveryResult(
            job_status=job_status,
            check_table_created=check_table_created,
            check_table=result["check_table"],
        )

    def _check_table_file_path(self):
        return os.path.join(self.get_work_dir(), "check_table.mk")


@page_registry.register_page("ajax_service_discovery")
class ModeAjaxServiceDiscovery(AjaxPage):
    def page(self):
        watolib.init_wato_datastructures(with_wato_lock=True)

        config.user.need_permission("wato.hosts")

        request = self.webapi_request()
        html.request.del_var("request")  # Do not add this to URLs constructed later
        request.setdefault("update_target", None)
        request.setdefault("update_source", None)
        request.setdefault("update_services", [])

        # Make Folder() be able to detect the current folder correctly
        html.request.set_var("folder", request["folder_path"])

        folder = watolib.Folder.folder(request["folder_path"])
        self._host = folder.host(request["host_name"])
        if not self._host:
            raise MKUserError("host", _("You called this page with an invalid host name."))
        self._host.need_permission("read")

        self._options = self._get_discovery_options(request)

        # Reuse the discovery result already known to the GUI or fetch a new one?
        previous_discovery_result = DiscoveryResult(*ast.literal_eval(request["discovery_result"])) \
                                        if request.get("discovery_result") else None

        if self._use_previous_discovery_result(request, previous_discovery_result):
            discovery_result = previous_discovery_result
        else:
            discovery_result = self._get_check_table()

        job_actions = [
            DiscoveryAction.NONE,
            DiscoveryAction.SCAN,
            DiscoveryAction.REFRESH,
            DiscoveryAction.STOP,
        ]

        if self._options.action not in job_actions \
           and html.check_transaction():
            discovery_result = self._handle_action(discovery_result, request)

        # Clean the requested action after performing it
        self._options = self._options._replace(action=DiscoveryAction.NONE)

        self._update_persisted_discovery_options()

        renderer = DiscoveryPageRenderer(
            self._host,
            self._options,
        )
        page_code = renderer.render(discovery_result, request)

        return {
            "is_finished": not self._is_active(discovery_result),
            "job_state": discovery_result.job_status["state"],
            "message": self._get_status_message(discovery_result),
            "body": page_code,
            "changes_button": self._render_changelog_button(),
            "discovery_options": self._options._asdict(),
            "discovery_result": repr(tuple(discovery_result)),
        }

    def _get_status_message(self, discovery_result):
        # type: (DiscoveryResult) -> Optional[Text]
        if discovery_result.job_status["state"] == JobStatusStates.INITIALIZED:
            if self._is_active(discovery_result):
                return _("Initializing discovery...")
            return _("No discovery information available. Please perform a full scan.")

        job_title = discovery_result.job_status.get("title", _("Service discovery"))
        duration_txt = cmk.utils.render.Age(discovery_result.job_status["duration"])
        finished_time = discovery_result.job_status["started"] + discovery_result.job_status[
            "duration"]
        finished_txt = cmk.utils.render.date_and_time(finished_time)

        if discovery_result.job_status["state"] == JobStatusStates.RUNNING:
            return _("%s running for %s") % (job_title, duration_txt)

        if discovery_result.job_status["state"] == JobStatusStates.EXCEPTION:
            return _("%s failed after %s: %s (see <tt>var/log/web.log</tt> for further information)") % \
                                (job_title, duration_txt, "\n".join(discovery_result.job_status["loginfo"]["JobException"]))

        messages = []
        if discovery_result.job_status["state"] == JobStatusStates.STOPPED:
            messages.append(
                _("%s was stopped after %s at %s.") % (job_title, duration_txt, finished_txt))

        elif discovery_result.job_status["state"] == JobStatusStates.FINISHED:
            messages.append(
                _("%s finished after %s at %s.") % (job_title, duration_txt, finished_txt))

        cmk_check_entries = [
            e for e in discovery_result.check_table if DiscoveryState.is_discovered(e[0])
        ]
        if cmk_check_entries:
            no_data = all(e[7] == 3 and e[8] == "Received no data" for e in cmk_check_entries)
            if no_data:
                messages.append(_("No data for discovery available. Please perform a full scan."))
        else:
            messages.append(_("Found no services yet. To retry please execute a full scan."))

        with html.plugged():
            html.begin_foldable_container(treename="service_discovery",
                                          id_="options",
                                          isopen=False,
                                          title=_("Job details"),
                                          indent=False)
            html.open_div(class_="log_output", style="height: 400px;", id_="progress_log")
            html.pre("\n".join(discovery_result.job_status["loginfo"]["JobProgressUpdate"]))
            html.close_div()
            html.end_foldable_container()
            messages.append(html.drain())

        if messages:
            return " ".join(messages)

        return None

    def _render_changelog_button(self):
        with html.plugged():
            changelog_button()
            return html.drain()

    def _get_discovery_options(self, request):
        # type: (dict) -> DiscoveryOptions
        options = DiscoveryOptions(**request["discovery_options"])

        # Refuse action requests in case the user is not permitted
        if options.action != DiscoveryAction.NONE and not config.user.may("wato.services"):
            options = options._replace(action=DiscoveryAction.NONE)

        if options.action != DiscoveryAction.REFRESH and not \
            (config.user.may("wato.service_discovery_to_undecided")
            and config.user.may("wato.service_discovery_to_monitored")
            and config.user.may("wato.service_discovery_to_ignored")
            and config.user.may("wato.service_discovery_to_removed")):
            options = options._replace(action=DiscoveryAction.NONE)

        return options

    def _use_previous_discovery_result(self, request, previous_discovery_result):
        if not previous_discovery_result:
            return False

        if self._options.action in [DiscoveryAction.REFRESH, DiscoveryAction.SCAN,
                                    DiscoveryAction.STOP] \
            and html.transaction_manager.check_transaction():
            return False

        if self._is_active(previous_discovery_result):
            return False

        return True

    def _is_active(self, discovery_result):
        return discovery_result.job_status["is_active"]

    def _get_check_table(self):
        # type: () -> DiscoveryResult
        return _get_check_table(
            StartDiscoveryRequest(self._host, self._host.folder(), self._options))

    def _update_persisted_discovery_options(self):
        show_checkboxes = config.user.load_file("discovery_checkboxes", False)
        if show_checkboxes != self._options.show_checkboxes:
            config.user.save_file("discovery_checkboxes", self._options.show_checkboxes)

        show_parameters = not config.user.load_file("parameter_column", False)
        if show_parameters != self._options.show_parameters:
            config.user.save_file("parameter_column", not self._options.show_parameters)

        show_discovered_labels = not config.user.load_file("discovery_show_discovered_labels",
                                                           False)
        if show_discovered_labels != self._options.show_discovered_labels:
            config.user.save_file("discovery_show_discovered_labels",
                                  not self._options.show_discovered_labels)

    def _handle_action(self, discovery_result, request):
        # type: (DiscoveryResult, dict) -> DiscoveryResult
        config.user.need_permission("wato.services")

        if self._options.action in [
                DiscoveryAction.SINGLE_UPDATE,
                DiscoveryAction.BULK_UPDATE,
                DiscoveryAction.FIX_ALL,
        ]:
            self._do_discovery(discovery_result, request)
            # did discovery! update the check table
            discovery_result = self._get_check_table()

        if not self._host.locked():
            self._host.clear_discovery_failed()

        return discovery_result

    def _do_discovery(self, discovery_result, request):
        autochecks_to_save, remove_disabled_rule, add_disabled_rule, saved_services = {}, set(
        ), set(), set()
        apply_changes = False
        for table_source, check_type, _checkgroup, item, paramstring, _params, \
            descr, _state, _output, _perfdata, service_labels in discovery_result.check_table:

            table_target = self._get_table_target(request, table_source, check_type, item)

            if table_source != table_target:
                if table_target == DiscoveryState.UNDECIDED:
                    config.user.need_permission("wato.service_discovery_to_undecided")
                elif table_target in [
                        DiscoveryState.MONITORED,
                        DiscoveryState.CLUSTERED_NEW,
                        DiscoveryState.CLUSTERED_OLD,
                ]:
                    config.user.need_permission("wato.service_discovery_to_undecided")
                elif table_target == DiscoveryState.IGNORED:
                    config.user.need_permission("wato.service_discovery_to_ignored")
                elif table_target == DiscoveryState.REMOVED:
                    config.user.need_permission("wato.service_discovery_to_removed")

                apply_changes = True

            if table_source == DiscoveryState.UNDECIDED:
                if table_target == DiscoveryState.MONITORED:
                    autochecks_to_save[(check_type, item)] = (paramstring, service_labels)
                    saved_services.add(descr)
                elif table_target == DiscoveryState.IGNORED:
                    add_disabled_rule.add(descr)

            elif table_source == DiscoveryState.VANISHED:
                if table_target != DiscoveryState.REMOVED:
                    autochecks_to_save[(check_type, item)] = (paramstring, service_labels)
                    saved_services.add(descr)
                if table_target == DiscoveryState.IGNORED:
                    add_disabled_rule.add(descr)

            elif table_source == DiscoveryState.MONITORED:
                if table_target in [
                        DiscoveryState.MONITORED,
                        DiscoveryState.IGNORED,
                ]:
                    autochecks_to_save[(check_type, item)] = (paramstring, service_labels)

                if table_target == DiscoveryState.IGNORED:
                    add_disabled_rule.add(descr)
                else:
                    saved_services.add(descr)

            elif table_source == DiscoveryState.IGNORED:
                if table_target in [
                        DiscoveryState.MONITORED,
                        DiscoveryState.UNDECIDED,
                        DiscoveryState.VANISHED,
                ]:
                    remove_disabled_rule.add(descr)
                if table_target in [
                        DiscoveryState.MONITORED,
                        DiscoveryState.IGNORED,
                ]:
                    autochecks_to_save[(check_type, item)] = (paramstring, service_labels)
                    saved_services.add(descr)
                if table_target == DiscoveryState.IGNORED:
                    add_disabled_rule.add(descr)

            elif table_source in [
                    DiscoveryState.CLUSTERED_NEW,
                    DiscoveryState.CLUSTERED_OLD,
            ]:
                autochecks_to_save[(check_type, item)] = (paramstring, service_labels)
                saved_services.add(descr)

            elif table_source in [
                    DiscoveryState.CLUSTERED_VANISHED,
                    DiscoveryState.CLUSTERED_IGNORED,
            ]:
                # We keep vanished clustered services on the node with the following reason:
                # If a service is mapped to a cluster then there are already operations
                # for adding, removing, etc. of this service on the cluster. Therefore we
                # do not allow any operation for this clustered service on the related node.
                # We just display the clustered service state (OLD, NEW, VANISHED).
                autochecks_to_save[(check_type, item)] = (paramstring, service_labels)
                saved_services.add(descr)

        if apply_changes:
            need_sync = False
            if remove_disabled_rule or add_disabled_rule:
                add_disabled_rule = add_disabled_rule - remove_disabled_rule - saved_services
                self._save_host_service_enable_disable_rules(remove_disabled_rule,
                                                             add_disabled_rule)
                need_sync = True
            self._save_services(autochecks_to_save, need_sync)

    def _save_services(self, checks, need_sync):
        message = _("Saved check configuration of host '%s' with %d services") % \
                    (self._host.name(), len(checks))
        watolib.add_service_change(self._host, "set-autochecks", message, need_sync=need_sync)
        check_mk_automation(self._host.site_id(), "set-autochecks", [self._host.name()], checks)

    def _save_host_service_enable_disable_rules(self, to_enable, to_disable):
        self._save_service_enable_disable_rules(to_enable, value=False)
        self._save_service_enable_disable_rules(to_disable, value=True)

    # Load all disabled services rules from the folder, then check whether or not there is a
    # rule for that host and check whether or not it currently disabled the services in question.
    # if so, remove them and save the rule again.
    # Then check whether or not the services are still disabled (by other rules). If so, search
    # for an existing host dedicated negative rule that enables services. Modify this or create
    # a new rule to override the disabling of other rules.
    #
    # Do the same vice versa for disabling services.
    def _save_service_enable_disable_rules(self, services, value):
        if not services:
            return

        def _compile_patterns(services):
            return [{"$regex": "%s$" % re.escape(s)} for s in services]

        rulesets = watolib.AllRulesets()
        rulesets.load()

        try:
            ruleset = rulesets.get("ignored_services")
        except KeyError:
            ruleset = watolib.Ruleset("ignored_services",
                                      ruleset_matcher.get_tag_to_group_map(config.tags))

        modified_folders = []

        service_patterns = _compile_patterns(services)
        modified_folders += self._remove_from_rule_of_host(ruleset,
                                                           service_patterns,
                                                           value=not value)

        # Check whether or not the service still needs a host specific setting after removing
        # the host specific setting above and remove all services from the service list
        # that are fine without an additional change.
        for service in list(services):
            value_without_host_rule = ruleset.analyse_ruleset(self._host.name(), service)[0]
            if (not value and value_without_host_rule in [None, False]) \
               or value == value_without_host_rule:
                services.remove(service)

        service_patterns = _compile_patterns(services)
        modified_folders += self._update_rule_of_host(ruleset, service_patterns, value=value)

        for folder in modified_folders:
            rulesets.save_folder(folder)

    def _remove_from_rule_of_host(self, ruleset, service_patterns, value):
        other_rule = self._get_rule_of_host(ruleset, value)
        if other_rule and isinstance(other_rule.conditions.service_description, list):
            for service_condition in service_patterns:
                if service_condition in other_rule.conditions.service_description:
                    other_rule.conditions.service_description.remove(service_condition)

            if not other_rule.conditions.service_description:
                ruleset.delete_rule(other_rule)

            return [other_rule.folder]

        return []

    def _update_rule_of_host(self, ruleset, service_patterns, value):
        folder = self._host.folder()
        rule = self._get_rule_of_host(ruleset, value)

        if rule:
            for service_condition in service_patterns:
                if service_condition not in rule.conditions.service_description:
                    rule.conditions.service_description.append(service_condition)

        elif service_patterns:
            rule = watolib.Rule.create(folder, ruleset)

            conditions = RuleConditions(folder.path())
            conditions.host_name = [self._host.name()]
            conditions.service_description = sorted(service_patterns)
            rule.update_conditions(conditions)

            rule.value = value
            ruleset.prepend_rule(folder, rule)

        if rule:
            return [rule.folder]
        return []

    def _get_rule_of_host(self, ruleset, value):
        for _folder, _index, rule in ruleset.get_rules():
            if rule.is_discovery_rule_of(self._host) and rule.value == value:
                return rule
        return None

    def _get_table_target(self, request, table_source, check_type, item):
        if self._options.action == DiscoveryAction.FIX_ALL:
            if table_source == DiscoveryState.VANISHED:
                return DiscoveryState.REMOVED
            elif table_source == DiscoveryState.IGNORED:
                return DiscoveryState.IGNORED
            #table_source in [DiscoveryState.MONITORED, DiscoveryState.UNDECIDED]
            return DiscoveryState.MONITORED

        update_target = request["update_target"]
        if not update_target:
            return table_source  # should never happen

        if self._options.action == DiscoveryAction.BULK_UPDATE:
            if table_source != request["update_source"]:
                return table_source

            if not self._options.show_checkboxes:
                return update_target

            if DiscoveryPageRenderer.checkbox_name(check_type, item) in request["update_services"]:
                return update_target

        if self._options.action == DiscoveryAction.SINGLE_UPDATE:
            varname = DiscoveryPageRenderer.checkbox_name(check_type, item)
            if varname in request["update_services"]:
                return update_target

        return table_source


class DiscoveryPageRenderer(object):
    @staticmethod
    def checkbox_name(check_type, item):
        """This function returns the HTTP variable name to use for a service

        This needs to be unique for each host. Since this text is used as
        variable name, it must not contain any umlauts or other special characters that
        are disallowed by html.parse_field_storage(). Since item may contain such
        chars, we need to use some encoded form of it. Simple escaping/encoding like we
        use for values of variables is not enough here.
        """
        key = u"%s_%s" % (check_type, item)
        return sha256(key.encode('utf-8')).hexdigest()

    def __init__(self, host, options):
        # type: (watolib.Host, DiscoveryOptions) -> None
        super(DiscoveryPageRenderer, self).__init__()
        self._host = host
        self._options = options

    def render(self, discovery_result, request):
        # type: (DiscoveryResult, dict) -> None
        with html.plugged():
            self._show_discovery_details(discovery_result, request)
            return html.drain()

    def _show_discovery_details(self, discovery_result, request):
        # type: (DiscoveryResult, dict) -> None
        if not discovery_result.check_table and self._is_active(discovery_result):
            html.show_info(_("Discovered no service yet."))
            return

        if not discovery_result.check_table and self._host.is_cluster():
            url = watolib.folder_preserving_link([("mode", "edit_ruleset"),
                                                  ("varname", "clustered_services")])
            html.show_info(
                _("Could not find any service for your cluster. You first need to "
                  "specify which services of your nodes shal be added to the "
                  "cluster. This is done using the <a href=\"%s\">%s</a> ruleset.") %
                (url, _("Clustered services")))
            return

        self._show_action_buttons(discovery_result)

        if not discovery_result.check_table:
            return

        # We currently don't get correct information from cmk_base (the data sources). Better
        # don't display this until we have the information.
        #html.write("Using discovery information from %s" % cmk.utils.render.date_and_time(
        #    discovery_result.check_table_created))

        by_group = self._group_check_table_by_state(discovery_result.check_table)
        for entry in self._ordered_table_groups():
            checks = by_group.get(entry.table_group, [])
            if not checks:
                continue

            html.begin_form("checks_%s" % entry.table_group, method="POST", action="wato.py")
            with table_element(css="data", searchable=False, limit=None, sortable=False) as table:
                table.groupheader(self._get_group_header(entry))

                if entry.show_bulk_actions and len(checks) > 10:
                    self._show_bulk_actions(table,
                                            discovery_result,
                                            entry.table_group,
                                            collect_headers=False)

                for check in sorted(checks, key=lambda c: c[6].lower()):
                    self._show_check_row(table, discovery_result, request, check,
                                         entry.show_bulk_actions)

                if entry.show_bulk_actions:
                    self._show_bulk_actions(table,
                                            discovery_result,
                                            entry.table_group,
                                            collect_headers="finished")
            html.hidden_fields()
            html.end_form()

    def _is_active(self, discovery_result):
        return discovery_result.job_status["is_active"]

    def _get_group_header(self, entry):
        map_icons = {
            DiscoveryState.UNDECIDED: "undecided",
            DiscoveryState.MONITORED: "monitored",
            DiscoveryState.IGNORED: "disabled"
        }

        group_header = ""
        if entry.table_group in map_icons:
            group_header += html.render_icon("%s_service" % map_icons[entry.table_group]) + " "
        group_header += entry.title

        return group_header + html.render_help(entry.help_text)

    def _group_check_table_by_state(self, check_table):
        by_group = {}
        for entry in check_table:
            by_group.setdefault(entry[0], []).append(entry)
        return by_group

    def _show_action_buttons(self, discovery_result):
        # type: (DiscoveryResult) -> None
        if not config.user.may("wato.services"):
            return

        fixall = 0
        already_has_services = False
        for check in discovery_result.check_table:
            if check[0] in [DiscoveryState.MONITORED, DiscoveryState.VANISHED]:
                already_has_services = True
            if check[0] in [DiscoveryState.UNDECIDED, DiscoveryState.VANISHED]:
                fixall += 1

        # TODO: Add correct permission checking
        if fixall >= 1:
            fix_all_options = self._options._replace(action=DiscoveryAction.FIX_ALL)
            html.jsbutton(
                "fix_all",
                _("Fix all missing/vanished"),
                self._start_js_call(fix_all_options),
                disabled=self._is_active(discovery_result),
            )

        if already_has_services \
            and config.user.may("wato.service_discovery_to_undecided") \
            and config.user.may("wato.service_discovery_to_monitored") \
            and config.user.may("wato.service_discovery_to_ignored") \
            and config.user.may("wato.service_discovery_to_removed"):
            refresh_options = self._options._replace(action=DiscoveryAction.REFRESH)
            html.jsbutton(
                "refresh",
                _("Automatic refresh (tabula rasa)"),
                self._start_js_call(refresh_options),
                disabled=self._is_active(discovery_result),
            )

        scan_options = self._options._replace(action=DiscoveryAction.SCAN)
        html.jsbutton(
            "scan",
            _("Full scan"),
            self._start_js_call(scan_options),
            disabled=self._is_active(discovery_result),
        )

        if already_has_services:
            self._show_checkbox_button(discovery_result)
            self._show_parameters_button(discovery_result)
            self._show_discovered_labels_button(discovery_result)

        if self._is_active(discovery_result):
            stop_options = self._options._replace(action=DiscoveryAction.STOP)
            html.jsbutton(
                "stop",
                _("Stop job"),
                self._start_js_call(stop_options),
            )

    def _show_checkbox_button(self, discovery_result):
        # type: (DiscoveryResult) -> None
        if not self._options.show_checkboxes:
            checkbox_options = self._options._replace(show_checkboxes=True)
            checkbox_title = _('Show checkboxes')
        else:
            checkbox_options = self._options._replace(show_checkboxes=False)
            checkbox_title = _('Hide checkboxes')

        html.jsbutton(
            "show_checkboxes",
            checkbox_title,
            self._start_js_call(checkbox_options),
            disabled=self._is_active(discovery_result),
        )

    def _show_parameters_button(self, discovery_result):
        # type: (DiscoveryResult) -> None
        if self._options.show_parameters:
            params_options = self._options._replace(show_parameters=False)
            params_title = _("Hide check parameters")
        else:
            params_options = self._options._replace(show_parameters=True)
            params_title = _("Show check parameters")

        html.jsbutton(
            "show_parameters",
            params_title,
            self._start_js_call(params_options),
            disabled=self._is_active(discovery_result),
        )

    def _show_discovered_labels_button(self, discovery_result):
        # type: (DiscoveryResult) -> None
        if self._options.show_discovered_labels:
            params_options = self._options._replace(show_discovered_labels=False)
            params_title = _("Hide discovered labels")
        else:
            params_options = self._options._replace(show_discovered_labels=True)
            params_title = _("Show discovered labels")

        html.jsbutton(
            "show_discovered_labels",
            params_title,
            self._start_js_call(params_options),
            disabled=self._is_active(discovery_result),
        )

    def _start_js_call(self, options, request_vars=None):
        # type: (DiscoveryOptions, dict) -> str
        return "cmk.service_discovery.start(%s, %s, %s, %s, %s)" % (
            json.dumps(self._host.name()),
            json.dumps(self._host.folder().path()),
            json.dumps(options._asdict()),
            json.dumps(html.transaction_manager.get()),
            json.dumps(request_vars),
        )

    def _show_bulk_actions(self, table, discovery_result, table_source, collect_headers):
        if not config.user.may("wato.services"):
            return

        table.row(collect_headers=collect_headers, fixed=True)
        table.cell(css="bulkactions service_discovery", colspan=self._bulk_action_colspan())

        if table_source == DiscoveryState.MONITORED:
            if config.user.may("wato.service_discovery_to_undecided"):
                self._bulk_button(discovery_result, table_source, DiscoveryState.UNDECIDED,
                                  _("Undecided"))
            if config.user.may("wato.service_discovery_to_ignored"):
                self._bulk_button(discovery_result, table_source, DiscoveryState.IGNORED,
                                  _("Disable"))

        elif table_source == DiscoveryState.IGNORED:
            if config.user.may("wato.service_discovery_to_monitored"):
                self._bulk_button(discovery_result, table_source, DiscoveryState.MONITORED,
                                  _("Monitor"))
            if config.user.may("wato.service_discovery_to_undecided"):
                self._bulk_button(discovery_result, table_source, DiscoveryState.UNDECIDED,
                                  _("Undecided"))

        elif table_source == DiscoveryState.VANISHED:
            if config.user.may("wato.service_discovery_to_removed"):
                self._bulk_button(discovery_result, table_source, DiscoveryState.REMOVED,
                                  _("Remove"))
            if config.user.may("wato.service_discovery_to_ignored"):
                self._bulk_button(discovery_result, table_source, DiscoveryState.IGNORED,
                                  _("Disable"))

        elif table_source == DiscoveryState.UNDECIDED:
            if config.user.may("wato.service_discovery_to_monitored"):
                self._bulk_button(discovery_result, table_source, DiscoveryState.MONITORED,
                                  _("Monitor"))
            if config.user.may("wato.service_discovery_to_ignored"):
                self._bulk_button(discovery_result, table_source, DiscoveryState.IGNORED,
                                  _("Disable"))

    def _bulk_button(self, discovery_result, source, target, target_label):
        label = _("selected services") if self._options.show_checkboxes else _("all services")
        options = self._options._replace(action=DiscoveryAction.BULK_UPDATE)
        html.jsbutton(
            "_bulk_%s_%s" % (source, target),
            target_label,
            self._start_js_call(options,
                                request_vars={
                                    "update_target": target,
                                    "update_source": source,
                                }),
            title=_("Move %s to %s services") % (label, target),
            disabled=self._is_active(discovery_result),
        )

    def _bulk_action_colspan(self):
        colspan = 5
        if self._options.show_parameters:
            colspan += 1
        if self._options.show_discovered_labels:
            colspan += 1
        if self._options.show_checkboxes:
            colspan += 1
        return colspan

    def _show_check_row(self, table, discovery_result, request, check, show_bulk_actions):
        table_source, check_type, checkgroup, item, _paramstring, params, \
            descr, state, output, _perfdata, service_labels = check

        statename = short_service_state_name(state, "")
        if statename == "":
            statename = short_service_state_name(-1)
            stateclass = "state svcstate statep"
            state = 0  # for tr class
        else:
            stateclass = "state svcstate state%s" % state

        table.row(css="data", state=state)

        self._show_bulk_checkbox(table, discovery_result, request, check_type, item,
                                 show_bulk_actions)
        self._show_actions(table, discovery_result, check)

        table.cell(_("State"), statename, css=stateclass)
        table.cell(_("Service"), html.attrencode(descr))
        table.cell(_("Status detail"))
        self._show_status_detail(table_source, check_type, item, descr, output)

        if table_source in [DiscoveryState.ACTIVE, DiscoveryState.ACTIVE_IGNORED]:
            ctype = "check_" + check_type
        else:
            ctype = check_type
        manpage_url = watolib.folder_preserving_link([("mode", "check_manpage"),
                                                      ("check_type", ctype)])
        table.cell(_("Check plugin"), html.render_a(content=ctype, href=manpage_url))

        if self._options.show_parameters:
            table.cell(_("Check parameters"))
            self._show_check_parameters(table_source, check_type, checkgroup, params)

        if self._options.show_discovered_labels:
            table.cell(_("Discovered labels"))
            self._show_discovered_labels(service_labels)

    def _show_status_detail(self, table_source, check_type, item, descr, output):
        if table_source not in [
                DiscoveryState.CUSTOM,
                DiscoveryState.ACTIVE,
                DiscoveryState.CUSTOM_IGNORED,
                DiscoveryState.ACTIVE_IGNORED,
        ]:
            html.write_text(output)
            return

        div_id = "activecheck_%s" % descr
        html.div(html.render_icon("reload", cssclass="reloading"), id_=div_id)
        html.javascript("cmk.service_discovery.execute_active_check(%s, %s, %s, %s, %s, %s);" % (
            json.dumps(self._host.site_id() or ''),
            json.dumps(self._host.folder().path()),
            json.dumps(self._host.name()),
            json.dumps(check_type),
            json.dumps(item),
            json.dumps(div_id),
        ))

    def _show_check_parameters(self, table_source, check_type, checkgroup, params):
        varname = self._get_ruleset_name(table_source, check_type, checkgroup)
        if not varname or varname not in rulespec_registry:
            return

        rulespec = rulespec_registry[varname]()
        try:
            if isinstance(params, dict) and "tp_computed_params" in params:
                html.write_text(
                    _("Timespecific parameters computed at %s") %
                    cmk.utils.render.date_and_time(params["tp_computed_params"]["computed_at"]))
                html.br()
                params = params["tp_computed_params"]["params"]
            rulespec.valuespec.validate_datatype(params, "")
            rulespec.valuespec.validate_value(params, "")
            paramtext = rulespec.valuespec.value_to_text(params)
            html.write_html(paramtext)
        except Exception as e:
            if config.debug:
                err = traceback.format_exc()
            else:
                err = e
            paramtext = "<b>%s</b>: %s<br>" % (_("Invalid check parameter"), err)
            paramtext += "%s: <tt>%s</tt><br>" % (_("Variable"), varname)
            paramtext += _("Parameters:")
            paramtext += "<pre>%s</pre>" % (pprint.pformat(params))
            html.write_text(paramtext)

    def _show_discovered_labels(self, service_labels):
        label_code = cmk.gui.view_utils.render_labels(
            service_labels,
            "service",
            with_links=False,
            label_sources={k: "discovered" for k in service_labels.keys()})
        html.write(label_code)

    def _show_bulk_checkbox(self, table, discovery_result, request, check_type, item,
                            show_bulk_actions):
        if not self._options.show_checkboxes or not config.user.may("wato.services"):
            return

        if not show_bulk_actions:
            table.cell(css="checkbox")
            return

        css_classes = ["service_checkbox"]
        if self._is_active(discovery_result):
            css_classes.append("disabled")

        table.cell(
            "<input type=button class=checkgroup name=_toggle_group"
            " onclick=\"cmk.selection.toggle_group_rows(this);\" value=\"X\" />",
            sortable=False,
            css="checkbox")
        name = DiscoveryPageRenderer.checkbox_name(check_type, item)
        checked = self._options.action == DiscoveryAction.BULK_UPDATE \
                    and name in request["update_services"]
        html.checkbox(varname=name, deflt=checked, class_=css_classes)

    def _show_actions(self, table, discovery_result, check):
        table.cell(css="buttons")
        if not config.user.may("wato.services"):
            html.empty_icon()
            html.empty_icon()
            html.empty_icon()
            html.empty_icon()
            return

        button_classes = ["service_button"]
        if self._is_active(discovery_result):
            button_classes.append("disabled")

        table_source, check_type, checkgroup, item, _paramstring, _params, \
            descr, _state, _output, _perfdata, _service_labels = check
        checkbox_name = DiscoveryPageRenderer.checkbox_name(check_type, item)

        num_buttons = 0
        if table_source == DiscoveryState.MONITORED:
            if config.user.may("wato.service_discovery_to_undecided"):
                self._icon_button(table_source, checkbox_name, DiscoveryState.UNDECIDED,
                                  "undecided", button_classes)
                num_buttons += 1
            if may_edit_ruleset("ignored_services") \
               and config.user.may("wato.service_discovery_to_ignored"):
                self._icon_button(table_source, checkbox_name, DiscoveryState.IGNORED, "disabled",
                                  button_classes)
                num_buttons += 1

        elif table_source == DiscoveryState.IGNORED:
            if may_edit_ruleset("ignored_services"):
                if config.user.may("wato.service_discovery_to_monitored"):
                    self._icon_button(table_source, checkbox_name, DiscoveryState.MONITORED,
                                      "monitored", button_classes)
                    num_buttons += 1
                if config.user.may("wato.service_discovery_to_ignored"):
                    self._icon_button(table_source, checkbox_name, DiscoveryState.UNDECIDED,
                                      "undecided", button_classes)
                    num_buttons += 1
                self._disabled_services_button(descr)
                num_buttons += 1

        elif table_source == DiscoveryState.VANISHED:
            if config.user.may("wato.service_discovery_to_removed"):
                self._icon_button_removed(table_source, checkbox_name, button_classes)
                num_buttons += 1
            if may_edit_ruleset("ignored_services") \
               and config.user.may("wato.service_discovery_to_ignored"):
                self._icon_button(table_source, checkbox_name, DiscoveryState.IGNORED, "disabled",
                                  button_classes)
                num_buttons += 1

        elif table_source == DiscoveryState.UNDECIDED:
            if config.user.may("wato.service_discovery_to_monitored"):
                self._icon_button(table_source, checkbox_name, DiscoveryState.MONITORED,
                                  "monitored", button_classes)
                num_buttons += 1
            if may_edit_ruleset("ignored_services") \
               and config.user.may("wato.service_discovery_to_ignored"):
                self._icon_button(table_source, checkbox_name, DiscoveryState.IGNORED, "disabled",
                                  button_classes)
                num_buttons += 1

        while num_buttons < 2:
            html.empty_icon()
            num_buttons += 1

        if table_source not in [DiscoveryState.UNDECIDED,
                                DiscoveryState.IGNORED] \
           and config.user.may('wato.rulesets'):
            self._rulesets_button(descr)
            self._check_parameters_button(table_source, check_type, checkgroup, item)
            num_buttons += 2

        while num_buttons < 4:
            html.empty_icon()
            num_buttons += 1

    def _icon_button(self, table_source, checkbox_name, table_target, descr_target, button_classes):
        options = self._options._replace(action=DiscoveryAction.SINGLE_UPDATE)
        html.icon_button(
            url="",
            title=_("Move to %s services") % descr_target,
            icon="service_to_%s" % descr_target,
            class_=button_classes,
            onclick=self._start_js_call(options,
                                        request_vars={
                                            "update_target": table_target,
                                            "update_source": table_source,
                                            "update_services": [checkbox_name],
                                        }),
        )

    def _icon_button_removed(self, table_source, checkbox_name, button_classes):
        options = self._options._replace(action=DiscoveryAction.SINGLE_UPDATE)
        html.icon_button(
            url="",
            title=_("Remove service"),
            icon="service_to_removed",
            class_=button_classes,
            onclick=self._start_js_call(options,
                                        request_vars={
                                            "update_target": DiscoveryState.REMOVED,
                                            "update_source": table_source,
                                            "update_services": [checkbox_name],
                                        }),
        )

    def _rulesets_button(self, descr):
        # Link to list of all rulesets affecting this service
        html.icon_button(
            watolib.folder_preserving_link([
                ("mode", "object_parameters"),
                ("host", self._host.name()),
                ("service", descr),
            ]), _("View and edit the parameters for this service"), "rulesets")

    def _check_parameters_button(self, table_source, check_type, checkgroup, item):
        if table_source == DiscoveryState.MANUAL:
            url = watolib.folder_preserving_link([
                ('mode', 'edit_ruleset'),
                ('varname', "static_checks:" + checkgroup),
                ('host', self._host.name()),
            ])
        else:
            ruleset_name = self._get_ruleset_name(table_source, check_type, checkgroup)
            if ruleset_name is None:
                return

            url = watolib.folder_preserving_link([
                ("mode", "edit_ruleset"),
                ("varname", ruleset_name),
                ("host", self._host.name()),
                ("item", watolib.mk_repr(item)),
            ]),

        html.icon_button(url, _("Edit and analyze the check parameters of this service"),
                         "check_parameters")

    def _disabled_services_button(self, descr):
        html.icon_button(
            watolib.folder_preserving_link([
                ("mode", "edit_ruleset"),
                ("varname", "ignored_services"),
                ("host", self._host.name()),
                ("item", watolib.mk_repr(descr)),
            ]), _("Edit and analyze the disabled services rules"), "rulesets")

    def _get_ruleset_name(self, table_source, check_type, checkgroup):
        if checkgroup == "logwatch":
            return "logwatch_rules"
        elif checkgroup:
            return "checkgroup_parameters:" + checkgroup
        elif table_source in [DiscoveryState.ACTIVE, DiscoveryState.ACTIVE_IGNORED]:
            return "active_checks:" + check_type
        return None

    def _ordered_table_groups(self):
        return [
            TableGroupEntry(
                table_group=DiscoveryState.UNDECIDED,
                show_bulk_actions=True,
                title=_("Undecided services (currently not monitored)"),
                help_text=_(
                    "These services have been found by the service discovery but are not yet added "
                    "to the monitoring. You should either decide to monitor them or to permanently "
                    "disable them. If you are sure that they are just transitional, just leave them "
                    "until they vanish."),
            ),
            TableGroupEntry(
                DiscoveryState.VANISHED,
                show_bulk_actions=True,
                title=_("Vanished services (monitored, but no longer exist)"),
                help_text=_(
                    "These services had been added to the monitoring by a previous discovery "
                    "but the actual items that are monitored are not present anymore. This might "
                    "be due to a real failure. In that case you should leave them in the monitoring. "
                    "If the actually monitored things are really not relevant for the monitoring "
                    "anymore then you should remove them in order to avoid UNKNOWN services in the "
                    "monitoring."),
            ),
            TableGroupEntry(
                DiscoveryState.CLUSTERED_VANISHED,
                show_bulk_actions=False,
                title=_("Vanished clustered services (located on cluster host)"),
                help_text=_(
                    "These services have been found on this host and have been mapped to "
                    "a cluster host by a rule in the set <i>Clustered services</i> but disappeared "
                    "from this host."),
            ),
            TableGroupEntry(
                DiscoveryState.MONITORED,
                show_bulk_actions=True,
                title=_("Monitored services"),
                help_text=_(
                    "These services had been found by a discovery and are currently configured "
                    "to be monitored."),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.IGNORED,
                show_bulk_actions=True,
                title=_("Disabled services"),
                help_text=_(
                    "These services are being discovered but have been disabled by creating a rule "
                    "in the rule set <i>Disabled services</i> or <i>Disabled checks</i>."),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.ACTIVE,
                show_bulk_actions=False,
                title=_("Active checks"),
                help_text=_(
                    "These services do not use the Check_MK agent or Check_MK-SNMP engine but actively "
                    "call classical check plugins. They have been added by a rule in the section "
                    "<i>Active checks</i> or implicitely by Check_MK."),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.MANUAL,
                show_bulk_actions=False,
                title=_("Manual checks"),
                help_text=_(
                    "These services have not been found by the discovery but have been added "
                    "manually by a rule in the WATO module <i>Manual checks</i>."),
            ),
            # TODO: Were removed in 1.6 from base. Keeping this for
            # compatibility with older remote sites. Remove with 1.7.
            TableGroupEntry(
                table_group=DiscoveryState.LEGACY,
                show_bulk_actions=False,
                title=_("Legacy services (defined in main.mk)"),
                help_text=_(
                    "These services have been configured by the deprecated variable <tt>legacy_checks</tt> "
                    "in <tt>main.mk</tt> or a similar configuration file."),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.CUSTOM,
                show_bulk_actions=False,
                title=_("Custom checks (defined via rule)"),
                help_text=_(
                    "These services do not use the Check_MK agent or Check_MK-SNMP engine but actively "
                    "call a classical check plugin, that you have installed yourself."),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.CLUSTERED_OLD,
                show_bulk_actions=False,
                title=_("Monitored clustered services (located on cluster host)"),
                help_text=_("These services have been found on this host but have been mapped to "
                            "a cluster host by a rule in the set <i>Clustered services</i>."),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.CLUSTERED_NEW,
                show_bulk_actions=False,
                title=_("Undecided clustered services"),
                help_text=_(
                    "These services have been found on this host and have been mapped to "
                    "a cluster host by a rule in the set <i>Clustered services</i>, but are not "
                    "yet added to the active monitoring. Please either add them or permanently disable "
                    "them."),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.CLUSTERED_IGNORED,
                show_bulk_actions=False,
                title=_("Disabled clustered services (located on cluster host)"),
                help_text=_(
                    "These services have been found on this host and have been mapped to "
                    "a cluster host by a rule in the set <i>Clustered services</i> but disabled via "
                    "<i>Disabled services</i> or <i>Disabled checks</i>."),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.ACTIVE_IGNORED,
                show_bulk_actions=False,
                title=_("Disabled active checks"),
                help_text=_(
                    "These services do not use the Check_MK agent or Check_MK-SNMP engine but actively "
                    "call classical check plugins. They have been added by a rule in the section "
                    "<i>Active checks</i> or implicitely by Check_MK. "
                    "These services have been disabled by creating a rule in the rule set "
                    "<i>Disabled services</i> oder <i>Disabled checks</i>."),
            ),
            TableGroupEntry(
                table_group=DiscoveryState.CUSTOM_IGNORED,
                show_bulk_actions=False,
                title=_("Disabled custom checks (defined via rule)"),
                help_text=_(
                    "These services do not use the Check_MK agent or Check_MK-SNMP engine but actively "
                    "call a classical check plugin, that you have installed yourself. "
                    "These services have been disabled by creating a rule in the rule set "
                    "<i>Disabled services</i> oder <i>Disabled checks</i>."),
            ),
            # TODO: Were removed in 1.6 from base. Keeping this for
            # compatibility with older remote sites. Remove with 1.7.
            TableGroupEntry(
                table_group=DiscoveryState.LEGACY_IGNORED,
                show_bulk_actions=False,
                title=_("Disabled legacy services (defined in main.mk)"),
                help_text=_(
                    "These services have been configured by the deprecated variable <tt>legacy_checks</tt> "
                    "in <tt>main.mk</tt> or a similar configuration file. "
                    "These services have been disabled by creating a rule in the rule set "
                    "<i>Disabled services</i> oder <i>Disabled checks</i>."),
            ),
        ]


@page_registry.register_page("wato_ajax_execute_check")
class ModeAjaxExecuteCheck(AjaxPage):
    def _from_vars(self):
        self._site = html.get_ascii_input("site")
        if self._site not in config.sitenames():
            raise MKUserError("site", _("You called this page with an invalid site."))

        self._host_name = html.get_ascii_input("host")
        self._host = watolib.Folder.current().host(self._host_name)
        if not self._host:
            raise MKUserError("host", _("You called this page with an invalid host name."))
        self._host.need_permission("read")

        # TODO: Validate
        self._check_type = html.get_ascii_input("checktype")
        # TODO: Validate
        self._item = html.request.var("item")

    def page(self):
        watolib.init_wato_datastructures(with_wato_lock=True)
        try:
            state, output = check_mk_automation(self._site,
                                                "active-check",
                                                [self._host_name, self._check_type, self._item],
                                                sync=False)
        except Exception as e:
            state = 3
            output = "%s" % e

        return {
            "state": state,
            "state_name": short_service_state_name(state, "UNKN"),
            "output": output,
        }
