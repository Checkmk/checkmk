#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import dataclasses
import enum
import json
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from hashlib import sha256
from typing import Any, assert_never, Literal, NamedTuple, TypedDict

from mypy_extensions import NamedArg

import cmk.utils.rulesets.ruleset_matcher as ruleset_matcher
from cmk.utils.object_diff import make_diff_text
from cmk.utils.type_defs import HostOrServiceConditions, Item

from cmk.automations.results import (
    CheckPreviewEntry,
    ServiceDiscoveryPreviewResult,
    SetAutochecksTable,
)

import cmk.gui.watolib.changes as _changes
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    job_registry,
    JobStatusStates,
)
from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.site_config import get_site_config, site_is_local
from cmk.gui.watolib.activate_changes import sync_changes_before_remote_automation
from cmk.gui.watolib.automations import do_remote_automation
from cmk.gui.watolib.check_mk_automations import (
    discovery,
    discovery_preview,
    get_services_labels,
    set_autochecks,
    update_host_labels,
)
from cmk.gui.watolib.hosts_and_folders import CREFolder, CREHost
from cmk.gui.watolib.rulesets import (
    AllRulesets,
    Rule,
    RuleConditions,
    Ruleset,
    service_description_to_condition,
)
from cmk.gui.watolib.utils import may_edit_ruleset


# Would rather use an Enum for this, but this information is exported to javascript
# using JSON and Enum is not serializable
# TODO In the future cleanup check_source (passive/active/custom/legacy) and
# check_state:
# - passive: new/vanished/old/ignored/removed
# - active/custom/legacy: old/ignored
class DiscoveryState:
    # not sure why `Literal` this is needed explicitly.
    # Should be gone once we use `StrEnum`
    UNDECIDED: Literal["new"] = "new"
    VANISHED: Literal["vanished"] = "vanished"
    MONITORED: Literal["old"] = "old"
    IGNORED: Literal["ignored"] = "ignored"
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

    @classmethod
    def is_discovered(cls, table_source) -> bool:  # type: ignore[no-untyped-def]
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


class DiscoveryAction(enum.StrEnum):
    """This is exported to javascript, so it has to be json serializable

    >>> import json
    >>> [json.dumps(a) for a in DiscoveryAction]
    ['""', '"stop"', '"fix_all"', '"refresh"', '"tabula_rasa"', '"single_update"', '"bulk_update"', '"update_host_labels"', '"update_services"']
    """

    NONE = ""  # corresponds to Full Scan in WATO
    STOP = "stop"
    FIX_ALL = "fix_all"
    REFRESH = "refresh"
    TABULA_RASA = "tabula_rasa"
    SINGLE_UPDATE = "single_update"
    BULK_UPDATE = "bulk_update"
    UPDATE_HOST_LABELS = "update_host_labels"
    UPDATE_SERVICES = "update_services"


class UpdateType(enum.Enum):
    "States that an individual service can be changed to by clicking a button"
    UNDECIDED = "new"
    MONITORED = "old"
    IGNORED = "ignored"
    REMOVED = "removed"


class DiscoveryResult(NamedTuple):
    job_status: dict
    check_table_created: int
    check_table: Sequence[CheckPreviewEntry]
    host_labels: dict
    new_labels: dict
    vanished_labels: dict
    changed_labels: dict
    sources: Mapping[str, tuple[int, str]]

    def serialize(self) -> str:
        return repr(
            (
                self.job_status,
                self.check_table_created,
                [dataclasses.astuple(cpe) for cpe in self.check_table],
                self.host_labels,
                self.new_labels,
                self.vanished_labels,
                self.changed_labels,
                self.sources,
            )
        )

    @classmethod
    def deserialize(cls, raw: str) -> "DiscoveryResult":
        job_status, check_table_created, raw_check_table, *rest = ast.literal_eval(raw)
        return cls(
            job_status,
            check_table_created,
            [CheckPreviewEntry(*cpe) for cpe in raw_check_table],
            *rest,
        )


class DiscoveryOptions(NamedTuple):
    action: DiscoveryAction
    show_checkboxes: bool
    show_parameters: bool
    show_discovered_labels: bool
    show_plugin_names: bool
    ignore_errors: bool


class StartDiscoveryRequest(NamedTuple):
    host: CREHost
    folder: CREFolder
    options: DiscoveryOptions


class DiscoveryInfo(TypedDict):
    update_source: str | None
    update_target: str | None
    update_services: Sequence[str]


class Discovery:
    def __init__(  # type: ignore[no-untyped-def]
        self,
        host,
        discovery_options,
        update_target: str | None,
        update_services: list[str],
        update_source: str | None = None,
    ) -> None:
        self._host = host
        self._options = discovery_options
        self._discovery_info: DiscoveryInfo = {
            "update_source": update_source,
            "update_target": update_target,
            "update_services": update_services,  # list of service hash
        }

    def execute_discovery(self, discovery_result=None):
        if discovery_result is None:
            discovery_result = get_check_table(
                StartDiscoveryRequest(self._host, self._host.folder(), self._options)
            )
        self.do_discovery(discovery_result)

    def do_discovery(self, discovery_result: DiscoveryResult):  # type: ignore[no-untyped-def]
        old_autochecks: SetAutochecksTable = {}
        autochecks_to_save: SetAutochecksTable = {}
        remove_disabled_rule: set[str] = set()
        add_disabled_rule: set[str] = set()
        saved_services: set[str] = set()
        apply_changes: bool = False

        for entry in discovery_result.check_table:
            # Versions >2.0b2 always provide a found on nodes information
            # If this information is missing (fallback value is None), the remote system runs on an older version

            table_target = self._get_table_target(entry)
            key = entry.check_plugin_name, entry.item
            value = (
                entry.description,
                entry.discovered_parameters,
                entry.labels,
                entry.found_on_nodes,
            )

            if entry.check_source != table_target:
                if table_target == DiscoveryState.UNDECIDED:
                    user.need_permission("wato.service_discovery_to_undecided")
                elif table_target in [
                    DiscoveryState.MONITORED,
                    DiscoveryState.CLUSTERED_NEW,
                    DiscoveryState.CLUSTERED_OLD,
                ]:
                    user.need_permission("wato.service_discovery_to_undecided")
                elif table_target == DiscoveryState.IGNORED:
                    user.need_permission("wato.service_discovery_to_ignored")
                elif table_target == DiscoveryState.REMOVED:
                    user.need_permission("wato.service_discovery_to_removed")

                apply_changes = True

            _apply_state_change(
                entry.check_source,
                table_target,
                key,
                value,
                entry.description,
                autochecks_to_save,
                saved_services,
                add_disabled_rule,
                remove_disabled_rule,
            )

            # Vanished services have to be added here because of audit log entries.
            # Otherwise, on each change all vanished services would lead to an
            # "added" entry, also on remove of a vanished service
            if entry.check_source in [
                DiscoveryState.MONITORED,
                DiscoveryState.IGNORED,
                DiscoveryState.VANISHED,
            ]:
                old_autochecks[key] = value

        if apply_changes:
            need_sync = False
            if remove_disabled_rule or add_disabled_rule:
                add_disabled_rule = add_disabled_rule - remove_disabled_rule - saved_services
                self._save_host_service_enable_disable_rules(
                    remove_disabled_rule, add_disabled_rule
                )
                need_sync = True
            self._save_services(
                old_autochecks,
                autochecks_to_save,
                need_sync,
            )

    def _save_services(
        self, old_autochecks: SetAutochecksTable, checks: SetAutochecksTable, need_sync: bool
    ) -> None:
        message = _("Saved check configuration of host '%s' with %d services") % (
            self._host.name(),
            len(checks),
        )
        _changes.add_service_change(
            action_name="set-autochecks",
            text=message,
            object_ref=self._host.object_ref(),
            site_id=self._host.site_id(),
            need_sync=need_sync,
            diff_text=make_diff_text(
                _make_host_audit_log_object(old_autochecks), _make_host_audit_log_object(checks)
            ),
        )

        set_autochecks(
            self._host.site_id(),
            self._host.name(),
            checks,
        )

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

        rulesets = AllRulesets.load_all_rulesets()

        try:
            ruleset = rulesets.get("ignored_services")
        except KeyError:
            ruleset = Ruleset(
                "ignored_services", ruleset_matcher.get_tag_to_group_map(active_config.tags)
            )

        modified_folders = []

        service_patterns: HostOrServiceConditions = [
            service_description_to_condition(s) for s in services
        ]
        modified_folders += self._remove_from_rule_of_host(
            ruleset, service_patterns, value=not value
        )

        # Check whether or not the service still needs a host specific setting after removing
        # the host specific setting above and remove all services from the service list
        # that are fine without an additional change.
        services_labels = get_services_labels(self._host.site_id(), self._host.name(), services)
        for service in list(services):
            service_labels = services_labels.labels[service]
            value_without_host_rule, _ = ruleset.analyse_ruleset(
                self._host.name(),
                service,
                service,
                service_labels=service_labels,
            )
            if (
                not value and value_without_host_rule in [None, False]
            ) or value == value_without_host_rule:
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

    def _update_rule_of_host(
        self, ruleset: Ruleset, service_patterns: HostOrServiceConditions, value: Any
    ) -> list[CREFolder]:
        folder = self._host.folder()
        rule = self._get_rule_of_host(ruleset, value)

        if rule:
            for service_condition in service_patterns:
                if service_condition not in rule.conditions.service_description:
                    rule.conditions.service_description.append(service_condition)

        elif service_patterns:
            rule = Rule.from_ruleset_defaults(folder, ruleset)

            # mypy is wrong here vor some reason:
            # Invalid index type "str" for "Union[Dict[str, str], str]"; expected type "Union[int, slice]"  [index]
            conditions = RuleConditions(
                folder.path(),
                host_name=[self._host.name()],
                service_description=sorted(service_patterns, key=lambda x: x["$regex"]),
            )
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

    def _get_table_target(self, entry: CheckPreviewEntry):  # type: ignore[no-untyped-def]
        if self._options.action == DiscoveryAction.FIX_ALL or (
            self._options.action == DiscoveryAction.UPDATE_SERVICES
            and self._service_is_checked(entry.check_plugin_name, entry.item)
        ):
            if entry.check_source == DiscoveryState.VANISHED:
                return DiscoveryState.REMOVED
            if entry.check_source == DiscoveryState.IGNORED:
                return DiscoveryState.IGNORED
            # entry.check_source in [DiscoveryState.MONITORED, DiscoveryState.UNDECIDED]
            return DiscoveryState.MONITORED

        update_target = self._discovery_info["update_target"]
        if not update_target:
            return entry.check_source

        if self._options.action == DiscoveryAction.BULK_UPDATE:
            if entry.check_source != self._discovery_info["update_source"]:
                return entry.check_source

            if not self._options.show_checkboxes:
                return update_target

            if (
                checkbox_id(entry.check_plugin_name, entry.item)
                in self._discovery_info["update_services"]
            ):
                return update_target

        if self._options.action == DiscoveryAction.SINGLE_UPDATE:
            varname = checkbox_id(entry.check_plugin_name, entry.item)
            if varname in self._discovery_info["update_services"]:
                return update_target

        return entry.check_source

    def _service_is_checked(self, check_type, item):
        return (
            not self._options.show_checkboxes
            or checkbox_id(check_type, item) in self._discovery_info["update_services"]
        )


def service_discovery_call(  # type: ignore[no-untyped-def]
    perform_action_call: Callable[
        [DiscoveryOptions, DiscoveryResult, NamedArg(CREHost, "host")],
        DiscoveryResult,
    ]
    | Callable[
        [
            DiscoveryOptions,
            DiscoveryResult,
            list[str],
            str | None,
            str | None,
            NamedArg(CREHost, "host"),
        ],
        DiscoveryResult,
    ]
):
    def decorate(*args, **kwargs) -> DiscoveryResult:  # type: ignore[no-untyped-def]
        user.need_permission("wato.services")
        result = perform_action_call(*args, **kwargs)
        host: CREHost = kwargs["host"]
        if not host.locked():
            host.clear_discovery_failed()
        return result

    return decorate


@service_discovery_call
def perform_fix_all(
    discovery_options: DiscoveryOptions,
    discovery_result: DiscoveryResult,
    *,
    host: CREHost,
) -> DiscoveryResult:
    """
    Handle fix all ('Accept All' on UI) discovery action
    """
    _perform_update_host_labels(host, discovery_result.host_labels)
    Discovery(
        host,
        discovery_options,
        update_target=None,
        update_services=[],
        update_source=None,
    ).do_discovery(discovery_result)
    discovery_result = get_check_table(
        StartDiscoveryRequest(host, host.folder(), discovery_options)
    )
    return discovery_result


@service_discovery_call
def perform_host_label_discovery(
    discovery_options: DiscoveryOptions,
    discovery_result: DiscoveryResult,
    *,
    host: CREHost,
) -> DiscoveryResult:
    """Handle update host labels discovery action"""
    _perform_update_host_labels(host, discovery_result.host_labels)
    discovery_result = get_check_table(
        StartDiscoveryRequest(host, host.folder(), discovery_options)
    )
    return discovery_result


@service_discovery_call
def perform_service_discovery(
    discovery_options: DiscoveryOptions,
    discovery_result: DiscoveryResult,
    update_services: list[str],
    update_source: str | None,
    update_target: str | None,
    *,
    host: CREHost,
) -> DiscoveryResult:
    """
    Handle discovery action for Update Services, Single Update & Bulk Update
    """
    Discovery(
        host,
        discovery_options,
        update_target=update_target,
        update_services=update_services,
        update_source=update_source,
    ).do_discovery(discovery_result)
    discovery_result = get_check_table(
        StartDiscoveryRequest(host, host.folder(), discovery_options)
    )
    return discovery_result


def has_discovery_action_specific_permissions(
    intended_discovery_action: DiscoveryAction, update_target: UpdateType | None
) -> bool:
    def may_all(*permissions: str) -> bool:
        return all(user.may(p) for p in permissions)

    # not sure if the function even gets called for all of these.
    match intended_discovery_action:
        case DiscoveryAction.NONE:
            return user.may("wato.services")
        case DiscoveryAction.STOP:
            return user.may("wato.services")
        case DiscoveryAction.TABULA_RASA:
            return may_all(
                "wato.service_discovery_to_undecided",
                "wato.service_discovery_to_monitored",
                "wato.service_discovery_to_removed",
            )
        case DiscoveryAction.FIX_ALL:
            return may_all(
                "wato.service_discovery_to_monitored",
                "wato.service_discovery_to_removed",
            )
        case DiscoveryAction.REFRESH:
            return user.may("wato.services")
        case DiscoveryAction.SINGLE_UPDATE:
            if update_target is None:
                # This should never happen.
                # The typing possibilities are currently so limited that I don't see a better solution.
                # We only get here via the REST API, which does not allow SINGLE_UPDATES.
                return False
            return has_modification_specific_permissions(update_target)
        case DiscoveryAction.BULK_UPDATE:
            return may_all(
                "wato.service_discovery_to_monitored",
                "wato.service_discovery_to_removed",
            )
        case DiscoveryAction.UPDATE_HOST_LABELS:
            return user.may("wato.services")
        case DiscoveryAction.UPDATE_SERVICES:
            return user.may("wato.services")

    assert_never(intended_discovery_action)


def has_modification_specific_permissions(update_target: UpdateType) -> bool:
    match update_target:
        case UpdateType.MONITORED:
            return user.may("wato.service_discovery_to_monitored")
        case UpdateType.UNDECIDED:
            return user.may("wato.service_discovery_to_undecided")
        case UpdateType.REMOVED:
            return user.may("wato.service_discovery_to_removed")
        case UpdateType.IGNORED:
            return user.may("wato.service_discovery_to_ignored") and may_edit_ruleset(
                "ignored_services"
            )
    assert_never(update_target)


def initial_discovery_result(
    discovery_options: DiscoveryOptions,
    host: CREHost,
    previous_discovery_result: DiscoveryResult | None,
) -> DiscoveryResult:
    if _use_previous_discovery_result(previous_discovery_result):
        assert previous_discovery_result is not None
        return previous_discovery_result

    return get_check_table(StartDiscoveryRequest(host, host.folder(), discovery_options))


def _use_previous_discovery_result(previous_discovery_result: DiscoveryResult | None) -> bool:
    if not previous_discovery_result:
        return False

    if has_active_job(previous_discovery_result):
        return False

    return True


def _perform_update_host_labels(host, host_labels):
    message = _("Updated discovered host labels of '%s' with %d labels") % (
        host.name(),
        len(host_labels),
    )
    _changes.add_service_change(
        "update-host-labels",
        message,
        host.object_ref(),
        host.site_id(),
    )
    update_host_labels(
        host.site_id(),
        host.name(),
        host_labels,
    )


def _apply_state_change(  # type: ignore[no-untyped-def] # pylint: disable=too-many-branches
    table_source: str,
    table_target: str,
    key: tuple[Any, Any],
    value: tuple[Any, Any, Any, Any],
    descr: str,
    autochecks_to_save: SetAutochecksTable,
    saved_services: set[str],
    add_disabled_rule: set[str],
    remove_disabled_rule: set[str],
):
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
        DiscoveryState.CLUSTERED_VANISHED,
        DiscoveryState.CLUSTERED_IGNORED,
    ]:
        # We keep VANISHED clustered services on the node with the following reason:
        # If a service is mapped to a cluster then there are already operations
        # for adding, removing, etc. of this service on the cluster. Therefore we
        # do not allow any operation for this clustered service on the related node.
        # We just display the clustered service state (OLD, NEW, VANISHED).
        autochecks_to_save[key] = value
        saved_services.add(descr)


def _make_host_audit_log_object(checks: SetAutochecksTable) -> set[str]:
    """The resulting object is used for building object diffs"""
    return {v[0] for v in checks.values()}


def checkbox_id(check_type: str, item: Item) -> str:
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

    key = f"{check_type}_{item}"
    return sha256(key.encode("utf-8")).hexdigest()


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
    if discovery_request.options.action == DiscoveryAction.TABULA_RASA:
        _changes.add_service_change(
            "refresh-autochecks",
            _("Refreshed check configuration of host '%s'") % discovery_request.host.name(),
            discovery_request.host.object_ref(),
            discovery_request.host.site_id(),
        )

    if site_is_local(discovery_request.host.site_id()):
        return execute_discovery_job(discovery_request)

    sync_changes_before_remote_automation(discovery_request.host.site_id())

    return DiscoveryResult.deserialize(
        str(
            do_remote_automation(
                get_site_config(discovery_request.host.site_id()),
                "service-discovery-job",
                [
                    ("host_name", discovery_request.host.name()),
                    ("options", json.dumps(discovery_request.options._asdict())),
                ],
            )
        )
    )


def execute_discovery_job(api_request: StartDiscoveryRequest) -> DiscoveryResult:
    """Either execute the discovery job to scan the host or return the discovery result
    based on the currently cached data"""
    job = ServiceDiscoveryBackgroundJob(api_request.host.name())

    if not job.is_active() and api_request.options.action in [
        DiscoveryAction.REFRESH,
        DiscoveryAction.TABULA_RASA,
    ]:
        job.start(lambda job_interface: job.discover(api_request, job_interface))

    if job.is_active() and api_request.options.action == DiscoveryAction.STOP:
        job.stop()

    return job.get_result(api_request)


@job_registry.register
class ServiceDiscoveryBackgroundJob(BackgroundJob):
    """The background job is always executed on the site where the host is located on"""

    job_prefix = "service_discovery"
    housekeeping_max_age_sec = 86400  # 1 day
    housekeeping_max_count = 20

    @classmethod
    def gui_title(cls) -> str:
        return _("Service discovery")

    def __init__(self, host_name: str) -> None:
        super().__init__(
            f"{self.job_prefix}-{host_name}",
            InitialStatusArgs(
                title=_("Service discovery"),
                stoppable=True,
                host_name=host_name,
                estimated_duration=BackgroundJob(self.job_prefix).get_status().duration,
            ),
        )
        self._pre_discovery_preview = (
            0,
            ServiceDiscoveryPreviewResult(
                output="",
                check_table=[],
                host_labels={},
                new_labels={},
                vanished_labels={},
                changed_labels={},
                source_results={},
            ),
        )

    def discover(
        self, api_request: StartDiscoveryRequest, job_interface: BackgroundProcessInterface
    ) -> None:
        """Target function of the background job"""
        print("Starting job...")
        self._pre_discovery_preview = self._get_discovery_preview(api_request)

        if api_request.options.action == DiscoveryAction.REFRESH:
            self._jobstatus_store.update({"title": _("Refresh")})
            self._perform_service_scan(api_request)

        elif api_request.options.action == DiscoveryAction.TABULA_RASA:
            self._jobstatus_store.update({"title": _("Tabula rasa")})
            self._perform_automatic_refresh(api_request)

        else:
            raise NotImplementedError()
        print("Completed.")

    def _perform_service_scan(self, api_request: StartDiscoveryRequest) -> None:
        """The try-inventory automation refreshes the Checkmk internal cache and makes the new
        information available to the next try-inventory call made by get_result()."""
        sys.stdout.write(
            discovery_preview(
                api_request.host.site_id(),
                api_request.host.name(),
                prevent_fetching=False,
                raise_errors=not api_request.options.ignore_errors,
            ).output
        )

    def _perform_automatic_refresh(self, api_request: StartDiscoveryRequest) -> None:
        # TODO: In distributed sites this must not add a change on the remote site. We need to build
        # the way back to the central site and show the information there.
        discovery(
            api_request.host.site_id(),
            "refresh",
            [api_request.host.name()],
            scan=True,
            raise_errors=False,  # why is api_request ignored here?
            non_blocking_http=True,
        )
        # count_added, _count_removed, _count_kept, _count_new = counts[api_request.host.name()]
        # message = _("Refreshed check configuration of host '%s' with %d services") % \
        #            (api_request.host.name(), count_added)
        # _changes.add_service_change(api_request.host, "refresh-autochecks", message)

    def get_result(self, api_request: StartDiscoveryRequest) -> DiscoveryResult:
        """Executed from the outer world to report about the job state"""
        job_status = dict(self.get_status())
        job_status["is_active"] = self.is_active()

        if job_status["is_active"]:
            check_table_created, result = self._pre_discovery_preview
        else:
            check_table_created, result = self._get_discovery_preview(api_request)
            if job_status["state"] == JobStatusStates.EXCEPTION:
                job_status.update(self._cleaned_up_status(job_status))

        return DiscoveryResult(
            job_status=job_status,
            check_table_created=check_table_created,
            check_table=result.check_table,
            host_labels=result.host_labels,
            new_labels=result.new_labels,
            vanished_labels=result.vanished_labels,
            changed_labels=result.changed_labels,
            sources=result.source_results,
        )

    @staticmethod
    def _get_discovery_preview(
        api_request: StartDiscoveryRequest,
    ) -> tuple[int, ServiceDiscoveryPreviewResult]:
        # TODO: Use the correct time. This is difficult because cmk.base does not have a single
        # time for all data of a host. The data sources should be able to provide this information
        # somehow.
        return (
            int(time.time()),
            discovery_preview(
                api_request.host.site_id(),
                api_request.host.name(),
                prevent_fetching=True,
                raise_errors=False,  # why is api_request ignored here?
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
            "state": JobStatusStates.FINISHED,
            "loginfo": {
                "JobProgressUpdate": ["%s:" % _("Last progress update")]
                + job_status["loginfo"]["JobProgressUpdate"]
                + ["%s:" % _("Last exception")]
                + job_status["loginfo"]["JobException"],
                "JobException": [],
                "JobResult": job_status["loginfo"]["JobResult"],
            },
        }

    def _check_table_file_path(self):
        return os.path.join(self.get_work_dir(), "check_table.mk")


def has_active_job(discovery_result: DiscoveryResult) -> bool:
    return discovery_result.job_status["is_active"]
