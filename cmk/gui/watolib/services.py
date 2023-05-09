#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import os
import time
import sys
from hashlib import sha256
from typing import Tuple, List, NamedTuple, Set, Dict, Any

import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher
from cmk.gui.sites import states, SiteStatus
from cmk.gui.watolib.utils import is_pre_17_remote_site
from cmk.utils.type_defs import SetAutochecksTable

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.gui_background_job as gui_background_job

from cmk.gui.i18n import _
from cmk.gui.background_job import BackgroundProcessInterface, JobStatusStates
from cmk.gui.watolib.wato_background_job import WatoBackgroundJob
from cmk.gui.watolib.rulesets import RuleConditions, service_description_to_condition

from cmk.gui.watolib.automations import (
    sync_changes_before_remote_automation,
    check_mk_automation,
    execute_automation_discovery,
)


# Would rather use an Enum for this, but this information is exported to javascript
# using JSON and Enum is not serializable
#TODO In the future cleanup check_source (passive/active/custom/legacy) and
# check_state:
# - passive: new/vanished/old/ignored/removed
# - active/custom/legacy: old/ignored
class DiscoveryState:
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
class DiscoveryAction:
    NONE = ""  # corresponds to Full Scan in WATO
    STOP = "stop"
    SCAN = "scan"
    FIX_ALL = "fix_all"
    REFRESH = "refresh"  # corresponds to Tabula Rasa in WATO
    SINGLE_UPDATE = "single_update"
    BULK_UPDATE = "bulk_update"
    UPDATE_HOST_LABELS = "update_host_labels"
    UPDATE_SERVICES = "update_services"


CheckTableEntry = Tuple  # TODO: Improve this type
CheckTable = List[CheckTableEntry]  # TODO: Improve this type

DiscoveryResult = NamedTuple("DiscoveryResult", [
    ("job_status", dict),
    ("check_table_created", int),
    ("check_table", CheckTable),
    ("host_labels", dict),
    ("new_labels", dict),
    ("vanished_labels", dict),
    ("changed_labels", dict),
])

DiscoveryOptions = NamedTuple("DiscoveryOptions", [
    ("action", str),
    ("show_checkboxes", bool),
    ("show_parameters", bool),
    ("show_discovered_labels", bool),
    ("show_plugin_names", bool),
    ("ignore_errors", bool),
])

StartDiscoveryRequest = NamedTuple("StartDiscoveryRequest", [
    ("host", watolib.CREHost),
    ("folder", watolib.CREFolder),
    ("options", DiscoveryOptions),
])


class Discovery:
    def __init__(self, host, discovery_options, request):
        self._host = host
        self._options = discovery_options
        self._discovery_info = {
            "update_source": request.get("update_source"),
            "update_target": request["update_target"],
            "update_services":
                request.get("update_services", [])  # list of service hash
        }

    def execute_discovery(self, discovery_result=None):
        if discovery_result is None:
            discovery_result = get_check_table(
                StartDiscoveryRequest(self._host, self._host.folder(), self._options))
        self.do_discovery(discovery_result)

    def do_discovery(self, discovery_result):
        old_autochecks: SetAutochecksTable = {}
        autochecks_to_save: SetAutochecksTable = {}
        remove_disabled_rule, add_disabled_rule, saved_services = set(), set(), set()
        apply_changes = False

        for (table_source, check_type, _checkgroup, item, discovered_params, _check_params, descr,
             _state, _output, _perfdata, service_labels,
             found_on_nodes) in discovery_result.check_table:
            # Versions >2.0b2 always provide a found on nodes information
            # If this information is missing (fallback value is None), the remote system runs on an older version

            table_target = self._get_table_target(table_source, check_type, item)
            key = check_type, item
            value = descr, discovered_params, service_labels, found_on_nodes

            if table_source in [DiscoveryState.MONITORED, DiscoveryState.IGNORED]:
                old_autochecks[key] = value

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
                    autochecks_to_save[key] = value
                    saved_services.add(descr)
                elif table_target == DiscoveryState.IGNORED:
                    add_disabled_rule.add(descr)

            elif table_source == DiscoveryState.VANISHED:
                if table_target == DiscoveryState.REMOVED:
                    pass
                elif table_target == DiscoveryState.IGNORED:
                    add_disabled_rule.add(descr)
                    autochecks_to_save[key] = value
                else:
                    autochecks_to_save[key] = value
                    saved_services.add(descr)

            elif table_source == DiscoveryState.MONITORED:
                if table_target in [
                        DiscoveryState.MONITORED,
                        DiscoveryState.IGNORED,
                ]:
                    autochecks_to_save[key] = value

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
                    autochecks_to_save[key] = value
                    saved_services.add(descr)
                if table_target == DiscoveryState.IGNORED:
                    add_disabled_rule.add(descr)

            elif table_source in [
                    DiscoveryState.CLUSTERED_NEW,
                    DiscoveryState.CLUSTERED_OLD,
            ]:
                autochecks_to_save[key] = value
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
                autochecks_to_save[key] = value
                saved_services.add(descr)

        if apply_changes:
            need_sync = False
            if remove_disabled_rule or add_disabled_rule:
                add_disabled_rule = add_disabled_rule - remove_disabled_rule - saved_services
                self._save_host_service_enable_disable_rules(remove_disabled_rule,
                                                             add_disabled_rule)
                need_sync = True
            self._save_services(
                old_autochecks,
                autochecks_to_save,
                need_sync,
            )

    def _save_services(self, old_autochecks: SetAutochecksTable, checks: SetAutochecksTable,
                       need_sync: bool) -> None:
        message = _("Saved check configuration of host '%s' with %d services") % (self._host.name(),
                                                                                  len(checks))
        watolib.add_service_change(
            host=self._host,
            action_name="set-autochecks",
            text=message,
            need_sync=need_sync,
            diff_text=watolib.make_diff_text(_make_host_audit_log_object(old_autochecks),
                                             _make_host_audit_log_object(checks)),
        )

        site_id = self._host.site_id()
        site_status = states().get(site_id, SiteStatus({}))
        if is_pre_17_remote_site(site_status):
            check_mk_automation(site_id, "set-autochecks", [self._host.name()],
                                {x: y[1:3] for x, y in checks.items()})
        else:
            check_mk_automation(site_id, "set-autochecks", [self._host.name()], checks)

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

        rulesets = watolib.AllRulesets()
        rulesets.load()

        try:
            ruleset = rulesets.get("ignored_services")
        except KeyError:
            ruleset = watolib.Ruleset("ignored_services",
                                      ruleset_matcher.get_tag_to_group_map(config.tags))

        modified_folders = []

        service_patterns = [service_description_to_condition(s) for s in services]
        modified_folders += self._remove_from_rule_of_host(ruleset,
                                                           service_patterns,
                                                           value=not value)

        # Check whether or not the service still needs a host specific setting after removing
        # the host specific setting above and remove all services from the service list
        # that are fine without an additional change.
        for service in list(services):
            value_without_host_rule = ruleset.analyse_ruleset(self._host.name(), service,
                                                              service)[0]
            if (not value and value_without_host_rule in [None, False]) \
               or value == value_without_host_rule:
                services.remove(service)

        service_patterns = [service_description_to_condition(s) for s in services]
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

    def _update_rule_of_host(self, ruleset: watolib.Ruleset, service_patterns: List[Dict[str, str]],
                             value: Any) -> List[watolib.CREFolder]:
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
            # mypy is wrong here vor some reason:
            # Invalid index type "str" for "Union[Dict[str, str], str]"; expected type "Union[int, slice]"  [index]
            conditions.service_description = sorted(
                service_patterns, key=lambda x: x["$regex"])  # type: ignore[index]
            rule.update_conditions(conditions)

            rule.value = value
            ruleset.prepend_rule(folder, rule)

        if rule:
            return [rule.folder]
        return []

    def _get_rule_of_host(self, ruleset, value):
        for _folder, _index, rule in ruleset.get_rules():
            if rule.is_disabled():
                continue

            if rule.is_discovery_rule_of(self._host) and rule.value == value:
                return rule
        return None

    def _get_table_target(self, table_source, check_type, item):
        if self._options.action == DiscoveryAction.FIX_ALL or (
                self._options.action == DiscoveryAction.UPDATE_SERVICES and
                self._service_is_checked(check_type, item)):
            if table_source == DiscoveryState.VANISHED:
                return DiscoveryState.REMOVED
            if table_source == DiscoveryState.IGNORED:
                return DiscoveryState.IGNORED
            #table_source in [DiscoveryState.MONITORED, DiscoveryState.UNDECIDED]
            return DiscoveryState.MONITORED

        update_target = self._discovery_info["update_target"]
        if not update_target:
            return table_source

        if self._options.action == DiscoveryAction.BULK_UPDATE:
            if table_source != self._discovery_info["update_source"]:
                return table_source

            if not self._options.show_checkboxes:
                return update_target

            if checkbox_id(check_type, item) in self._discovery_info["update_services"]:
                return update_target

        if self._options.action == DiscoveryAction.SINGLE_UPDATE:
            varname = checkbox_id(check_type, item)
            if varname in self._discovery_info["update_services"]:
                return update_target

        return table_source

    def _service_is_checked(self, check_type, item):
        return not self._options.show_checkboxes or checkbox_id(
            check_type, item) in self._discovery_info["update_services"]


def _make_host_audit_log_object(checks: SetAutochecksTable) -> Set[str]:
    """The resulting object is used for building object diffs"""
    return {v[0] for v in checks.values()}


def checkbox_id(check_type, item):
    """Generate HTML variable for service

    This needs to be unique for each host. Since this text is used as
    variable name, it must not contain any umlauts or other special characters that
    are disallowed by html.parse_field_storage(). Since item may contain such
    chars, we need to use some encoded form of it. Simple escaping/encoding like we
    use for values of variables is not enough here.

    Examples:

        >>> checkbox_id("df", "/opt/omd/sites/testering/tmp")
        '0735e04becbc2f9481ea8e0b54f1aa512d0b04e036cdfac5cc72238f6b39aaeb'

    Returns:
        A string representing the service checkbox

    """

    key = u"%s_%s" % (check_type, item)
    return sha256(key.encode('utf-8')).hexdigest()


def get_check_table(discovery_request: StartDiscoveryRequest) -> DiscoveryResult:
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
    if discovery_request.options.action == DiscoveryAction.REFRESH:
        watolib.add_service_change(
            discovery_request.host, "refresh-autochecks",
            _("Refreshed check configuration of host '%s'") % discovery_request.host.name())

    if config.site_is_local(discovery_request.host.site_id()):
        return execute_discovery_job(discovery_request)

    discovery_result = _get_check_table_from_remote(discovery_request)
    discovery_result = _add_missing_discovery_result_fields(discovery_result)
    return discovery_result


def execute_discovery_job(request: StartDiscoveryRequest) -> DiscoveryResult:
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


def _add_missing_discovery_result_fields(discovery_result: DiscoveryResult) -> DiscoveryResult:
    # 1.6.0b4 introduced the service labels column which might be missing when
    # fetching information from remote sites.
    d = discovery_result._asdict()
    d["check_table"] = [(e + ({},) if len(e) < 11 else e) for e in d["check_table"]]

    # 2.0.0b2 introduced the found_on_nodes info
    d["check_table"] = [(e + (None,) if len(e) < 12 else e) for e in d["check_table"]]

    return DiscoveryResult(**d)


def _deserialize_remote_result(raw_result: str) -> DiscoveryResult:
    remote_result = ast.literal_eval(raw_result)

    if isinstance(remote_result, tuple):
        # Previous to 2.0.0p1 the remote call returned
        # a) a tuple
        # b) did not know about the new_labels, vanished_labels and changed_labels
        return DiscoveryResult(
            job_status=remote_result[0],
            check_table_created=remote_result[1],
            check_table=remote_result[2],
            host_labels=remote_result[3],
            new_labels={},
            vanished_labels={},
            changed_labels={},
        )

    assert isinstance(remote_result, dict)
    return DiscoveryResult(**remote_result)


def _get_check_table_from_remote(request):
    """Gathers the check table from a remote site

    Cares about pre 1.6 sites that does not support the new service-discovery-job API call.
    Falling back to the previously existing try-inventry and inventory automation calls.
    """
    try:
        sync_changes_before_remote_automation(request.host.site_id())

        return _deserialize_remote_result(
            watolib.do_remote_automation(config.site(request.host.site_id()),
                                         "service-discovery-job", [
                                             ("host_name", request.host.name()),
                                             ("options", json.dumps(request.options._asdict())),
                                         ]))
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
            check_table_created=int(time.time()),
            host_labels={},
            new_labels={},
            vanished_labels={},
            changed_labels={},
        )


@gui_background_job.job_registry.register
class ServiceDiscoveryBackgroundJob(WatoBackgroundJob):
    """The background job is always executed on the site where the host is located on"""
    job_prefix = "service_discovery"
    housekeeping_max_age_sec = 86400  # 1 day
    housekeeping_max_count = 20

    @classmethod
    def gui_title(cls):
        return _("Service discovery")

    def __init__(self, host_name: str) -> None:
        job_id = "%s-%s" % (self.job_prefix, host_name)
        last_job_status = WatoBackgroundJob(job_id).get_status()

        super(ServiceDiscoveryBackgroundJob, self).__init__(
            job_id,
            title=_("Service discovery"),
            stoppable=True,
            host_name=host_name,
            estimated_duration=last_job_status.get("duration"),
        )
        self._pre_try_discovery: Tuple[int, Dict] = (0, {})

    def discover(self, request: StartDiscoveryRequest,
                 job_interface: BackgroundProcessInterface) -> None:
        """Target function of the background job"""
        print("Starting job...")
        self._pre_try_discovery = self._get_try_discovery(request)

        if request.options.action == DiscoveryAction.SCAN:
            self._jobstatus.update_status({"title": _("Full scan")})
            self._perform_service_scan(request)

        elif request.options.action == DiscoveryAction.REFRESH:
            self._jobstatus.update_status({"title": _("Automatic refresh")})
            self._perform_automatic_refresh(request)

        else:
            raise NotImplementedError()
        print("Completed.")

    def _perform_service_scan(self, request):
        """The try-inventory automation refreshes the Check_MK internal cache and makes the new
        information available to the next try-inventory call made by get_result()."""
        result = check_mk_automation(request.host.site_id(), "try-inventory",
                                     self._get_automation_options(request))
        sys.stdout.write(result["output"])

    def _perform_automatic_refresh(self, request):
        # TODO: In distributed sites this must not add a change on the remote site. We need to build
        # the way back to the central site and show the information there.
        execute_automation_discovery(site_id=request.host.site_id(),
                                     args=["@scan", "refresh",
                                           request.host.name()])
        #count_added, _count_removed, _count_kept, _count_new = counts[request.host.name()]
        #message = _("Refreshed check configuration of host '%s' with %d services") % \
        #            (request.host.name(), count_added)
        #watolib.add_service_change(request.host, "refresh-autochecks", message)

    def _get_automation_options(self, request: StartDiscoveryRequest) -> List[str]:
        if request.options.action == DiscoveryAction.SCAN:
            options = ["@scan"]
        else:
            options = ["@noscan"]

        if not request.options.ignore_errors:
            options.append("@raiseerrors")

        options.append(request.host.name())

        return options

    def get_result(self, request: StartDiscoveryRequest) -> DiscoveryResult:
        """Executed from the outer world to report about the job state"""
        job_status = self.get_status()
        job_status["is_active"] = self.is_active()

        if job_status['is_active']:
            check_table_created, result = self._pre_try_discovery
        else:
            check_table_created, result = self._get_try_discovery(request)
            if job_status['state'] == JobStatusStates.EXCEPTION:
                job_status.update(self._cleaned_up_status(job_status))

        return DiscoveryResult(
            job_status=job_status,
            check_table_created=check_table_created,
            check_table=result.get("check_table", []),
            host_labels=result.get("host_labels", {}),
            new_labels=result.get("new_labels", {}),
            vanished_labels=result.get("vanished_labels", {}),
            changed_labels=result.get("changed_labels", {}),
        )

    @staticmethod
    def _get_try_discovery(request: StartDiscoveryRequest) -> Tuple[int, Dict]:
        # TODO: Use the correct time. This is difficult because cmk.base does not have a single
        # time for all data of a host. The data sources should be able to provide this information
        # somehow.
        return (
            int(time.time()),
            check_mk_automation(
                request.host.site_id(),
                "try-inventory",
                ["@noscan", request.host.name()],
            ),
        )

    @staticmethod
    def _cleaned_up_status(job_status):
        # There might be an exception when calling above 'check_mk_automation'. For example
        # this may happen if a hostname is not resolvable. Then if the error is fixed, ie.
        # configuring an IP address of this host, and the discovery is started again, we put
        # the cached/last job exception into the current job progress update instead of displaying
        # the error in a CRIT message box again.
        return {
            'state': JobStatusStates.FINISHED,
            'loginfo': {
                'JobProgressUpdate': ['%s:' % _('Last progress update')] +
                                     job_status['loginfo']['JobProgressUpdate'] +
                                     ["%s:" % _('Last exception')] +
                                     job_status['loginfo']['JobException'],
                'JobException': [],
                'JobResult': job_status['loginfo']['JobResult'],
            }
        }

    def _check_table_file_path(self):
        return os.path.join(self.get_work_dir(), "check_table.mk")
