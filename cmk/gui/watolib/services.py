#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import ast
import dataclasses
import enum
import hashlib
import json
import sys
import time
from collections.abc import Container, Iterator, Mapping, MutableMapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import assert_never, Final, Literal, NamedTuple

from pydantic import BaseModel

from cmk.ccc.store import ObjectStore, TextSerializer
from cmk.ccc.version import __version__, Version

from cmk.utils.hostaddress import HostName
from cmk.utils.labels import HostLabel, HostLabelValueDict
from cmk.utils.object_diff import make_diff_text
from cmk.utils.servicename import Item, ServiceName

from cmk.automations.results import (
    SerializedResult,
    ServiceDiscoveryPreviewResult,
    SetAutochecksInput,
)

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.discovery import AutocheckEntry, CheckPreviewEntry

import cmk.gui.watolib.changes as _changes
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobStatusSpec,
    JobStatusStates,
    JobTarget,
)
from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.site_config import get_site_config, site_is_local
from cmk.gui.watolib.activate_changes import sync_changes_before_remote_automation
from cmk.gui.watolib.automations import do_remote_automation
from cmk.gui.watolib.check_mk_automations import (
    local_discovery,
    local_discovery_preview,
    set_autochecks_v2,
    update_host_labels,
)
from cmk.gui.watolib.config_domain_name import (
    config_domain_registry,
    generate_hosts_to_update_settings,
)
from cmk.gui.watolib.config_domain_name import (
    CORE as CORE_DOMAIN,
)
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.gui.watolib.rulesets import EnabledDisabledServicesEditor
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
    MONITORED: Literal["unchanged"] = "unchanged"
    CHANGED: Literal["changed"] = "changed"
    VANISHED: Literal["vanished"] = "vanished"
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
    def is_discovered(cls, table_source: str) -> bool:
        return table_source in [
            cls.UNDECIDED,
            cls.CHANGED,
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
    ['""', '"stop"', '"fix_all"', '"refresh"', '"tabula_rasa"', '"single_update"', '"bulk_update"', '"update_host_labels"', '"update_services"', '"update_service_labels"', '"update_discovery_parameters"', '"single_update_service_properties"']
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
    UPDATE_SERVICE_LABELS = "update_service_labels"
    UPDATE_DISCOVERY_PARAMETERS = "update_discovery_parameters"
    SINGLE_UPDATE_SERVICE_PROPERTIES = "single_update_service_properties"


class UpdateType(enum.Enum):
    "States that an individual service can be changed to by clicking a button"

    UNDECIDED = "new"
    MONITORED = "unchanged"
    IGNORED = "ignored"
    REMOVED = "removed"


class DiscoveryResult(NamedTuple):
    job_status: dict
    check_table_created: int
    check_table: Sequence[CheckPreviewEntry]
    nodes_check_table: Mapping[HostName, Sequence[CheckPreviewEntry]]
    host_labels: Mapping[str, HostLabelValueDict]
    new_labels: Mapping[str, HostLabelValueDict]
    vanished_labels: Mapping[str, HostLabelValueDict]
    changed_labels: Mapping[str, HostLabelValueDict]
    labels_by_host: Mapping[HostName, Sequence[HostLabel]]
    sources: Mapping[str, tuple[int, str]]

    def serialize(self, for_cmk_version: Version) -> str:
        if for_cmk_version < Version.from_str("2.4.0b1"):
            return repr(
                (
                    self.job_status,
                    self.check_table_created,
                    [dataclasses.astuple(cpe) for cpe in self.check_table],
                    self.host_labels,
                    self.new_labels,
                    self.vanished_labels,
                    self.changed_labels,
                    {
                        str(host_name): [label.serialize() for label in host_labels]
                        for host_name, host_labels in self.labels_by_host.items()
                    },
                    self.sources,
                )
            )
        return repr(
            (
                self.job_status,
                self.check_table_created,
                [dataclasses.astuple(cpe) for cpe in self.check_table],
                {
                    h: [dataclasses.astuple(cpe) for cpe in entries]
                    for h, entries in self.nodes_check_table.items()
                },
                self.host_labels,
                self.new_labels,
                self.vanished_labels,
                self.changed_labels,
                {
                    str(host_name): [label.serialize() for label in host_labels]
                    for host_name, host_labels in self.labels_by_host.items()
                },
                self.sources,
            )
        )

    @classmethod
    def deserialize(cls, raw: str) -> DiscoveryResult:
        (
            job_status,
            check_table_created,
            raw_check_table,
            raw_nodes_check_table,
            host_labels,
            new_labels,
            vanished_labels,
            changed_labels,
            raw_labels_by_host,
            sources,
        ) = ast.literal_eval(raw)
        return cls(
            job_status,
            check_table_created,
            [CheckPreviewEntry(*cpe) for cpe in raw_check_table],
            {
                h: [CheckPreviewEntry(*cpe) for cpe in entries]
                for h, entries in raw_nodes_check_table.items()
            },
            host_labels,
            new_labels,
            vanished_labels,
            changed_labels,
            {
                HostName(raw_host_name): [
                    HostLabel.deserialize(raw_label) for raw_label in raw_host_labels
                ]
                for raw_host_name, raw_host_labels in raw_labels_by_host.items()
            },
            sources,
        )

    def is_active(self) -> bool:
        return bool(self.job_status["is_active"])


class DiscoveryOptions(NamedTuple):
    action: DiscoveryAction
    show_checkboxes: bool
    show_parameters: bool
    show_discovered_labels: bool
    show_plugin_names: bool
    ignore_errors: bool


class Discovery:
    def __init__(
        self,
        host: Host,
        action: DiscoveryAction,
        *,
        update_target: str | None,
        update_source: str | None = None,
        selected_services: Container[tuple[str, Item]],
    ) -> None:
        self._host = host
        self._action = action
        self._update_source = update_source
        self._update_target = update_target
        self._selected_services = selected_services

    def do_discovery(self, discovery_result: DiscoveryResult, target_host_name: HostName) -> None:
        changed_target_services: MutableMapping[ServiceName, AutocheckEntry] = {}
        changed_nodes_services: MutableMapping[
            HostName, MutableMapping[ServiceName, AutocheckEntry]
        ] = {}
        unchanged_target_services: MutableMapping[ServiceName, AutocheckEntry] = {}
        unchanged_nodes_services: MutableMapping[
            HostName, MutableMapping[ServiceName, AutocheckEntry]
        ] = {}
        remove_disabled_rule: set[str] = set()
        add_disabled_rule: set[str] = set()
        saved_services: set[str] = set()
        apply_changes: bool = False

        for autochecks_host_name, check_table in self._get_effective_check_tables(
            discovery_result, target_host_name
        ).items():
            unchanged_services: MutableMapping[ServiceName, AutocheckEntry] = {}
            changed_services: MutableMapping[ServiceName, AutocheckEntry] = {}
            for entry in check_table:
                key = ServiceName(entry.description)
                table_target = self._get_table_target(entry)
                self._verify_permissions(table_target, entry)
                unchanged_value, changed_value = self._get_autochecks_values(table_target, entry)

                if entry.check_source != table_target:
                    apply_changes = True

                _apply_state_change(
                    entry.check_source,
                    table_target,
                    key,
                    changed_value,
                    entry.description,
                    changed_services,
                    saved_services,
                    add_disabled_rule,
                    remove_disabled_rule,
                )

                # Vanished services have to be added here because of audit log entries.
                # Otherwise, on each change all vanished services would lead to an
                # "added" entry, also on remove of a vanished service
                if entry.check_source in [
                    DiscoveryState.MONITORED,
                    DiscoveryState.CHANGED,
                    DiscoveryState.IGNORED,
                    DiscoveryState.VANISHED,
                ]:
                    unchanged_services[key] = unchanged_value

            if target_host_name == autochecks_host_name:
                unchanged_target_services = unchanged_services
                changed_target_services = changed_services
            else:
                unchanged_nodes_services[autochecks_host_name] = unchanged_services
                changed_nodes_services[autochecks_host_name] = changed_services

        if apply_changes:
            need_sync = False
            if remove_disabled_rule or add_disabled_rule:
                add_disabled_rule = add_disabled_rule - remove_disabled_rule - saved_services
                EnabledDisabledServicesEditor(self._host).save_host_service_enable_disable_rules(
                    remove_disabled_rule, add_disabled_rule
                )
                need_sync = True
            self._save_services(
                target_host_name,
                SetAutochecksInput(
                    target_host_name, unchanged_target_services, unchanged_nodes_services
                ),
                SetAutochecksInput(
                    target_host_name, changed_target_services, changed_nodes_services
                ),
                need_sync,
            )

    @staticmethod
    def _verify_permissions(table_target: str, entry: CheckPreviewEntry) -> None:
        if entry.check_source != table_target:
            match table_target:
                case DiscoveryState.UNDECIDED:
                    user.need_permission("wato.service_discovery_to_undecided")
                case (
                    DiscoveryState.MONITORED
                    | DiscoveryState.CHANGED
                    | DiscoveryState.CLUSTERED_NEW
                    | DiscoveryState.CLUSTERED_OLD
                ):
                    user.need_permission("wato.service_discovery_to_monitored")
                case DiscoveryState.IGNORED:
                    user.need_permission("wato.service_discovery_to_ignored")
                case DiscoveryState.REMOVED:
                    user.need_permission("wato.service_discovery_to_removed")

    def _get_autochecks_values(
        self, table_target: str, entry: CheckPreviewEntry
    ) -> tuple[AutocheckEntry, AutocheckEntry]:
        unchanged_autochecks_value = AutocheckEntry(
            CheckPluginName(entry.check_plugin_name),
            entry.item,
            entry.old_discovered_parameters,
            entry.old_labels,
        )
        if entry.check_source != table_target:
            match table_target:
                case (
                    DiscoveryState.MONITORED
                    | DiscoveryState.CHANGED
                    | DiscoveryState.CLUSTERED_NEW
                    | DiscoveryState.CLUSTERED_OLD
                ):
                    # adjust the values in case the corresponding action is called.
                    return unchanged_autochecks_value, AutocheckEntry(
                        CheckPluginName(entry.check_plugin_name),
                        entry.item,
                        (
                            entry.new_discovered_parameters
                            if self._action
                            in (
                                DiscoveryAction.FIX_ALL,
                                DiscoveryAction.UPDATE_DISCOVERY_PARAMETERS,
                                DiscoveryAction.SINGLE_UPDATE_SERVICE_PROPERTIES,
                            )
                            else entry.old_discovered_parameters
                        ),
                        (
                            entry.new_labels
                            if self._action
                            in (
                                DiscoveryAction.FIX_ALL,
                                DiscoveryAction.UPDATE_SERVICE_LABELS,
                                DiscoveryAction.SINGLE_UPDATE_SERVICE_PROPERTIES,
                            )
                            else entry.old_labels
                        ),
                    )
        return unchanged_autochecks_value, unchanged_autochecks_value

    def _save_services(
        self,
        affected_host_name: HostName,
        old_autochecks: SetAutochecksInput,
        autochecks_table: SetAutochecksInput,
        need_sync: bool,
    ) -> None:
        message = _("Saved check configuration of host '%s' with %d services") % (
            affected_host_name,
            len(autochecks_table.target_services),
        )
        _changes.add_service_change(
            action_name="set-autochecks",
            text=message,
            object_ref=self._host.object_ref(),
            domains=[config_domain_registry[CORE_DOMAIN]],
            domain_settings={CORE_DOMAIN: generate_hosts_to_update_settings([self._host.name()])},
            site_id=self._host.site_id(),
            need_sync=need_sync,
            diff_text=make_diff_text(
                _make_host_audit_log_object(old_autochecks),
                _make_host_audit_log_object(autochecks_table),
            ),
        )
        set_autochecks_v2(
            self._host.site_id(),
            autochecks_table,
        )

    def _get_table_target(self, entry: CheckPreviewEntry) -> str:
        if self._action == DiscoveryAction.FIX_ALL or (
            self._action == DiscoveryAction.UPDATE_SERVICES
            and (entry.check_plugin_name, entry.item) in self._selected_services
        ):
            if entry.check_source == DiscoveryState.VANISHED:
                return DiscoveryState.REMOVED
            if entry.check_source == DiscoveryState.IGNORED:
                return DiscoveryState.IGNORED
            # entry.check_source in [DiscoveryState.MONITORED, DiscoveryState.UNDECIDED]
            return DiscoveryState.MONITORED

        if self._action == DiscoveryAction.UPDATE_SERVICE_LABELS and self._update_target:
            if entry.check_source == DiscoveryState.IGNORED:
                return DiscoveryState.IGNORED
            return self._update_target

        if self._action == DiscoveryAction.UPDATE_DISCOVERY_PARAMETERS and self._update_target:
            if entry.check_source == DiscoveryState.IGNORED:
                return DiscoveryState.IGNORED
            return self._update_target

        if not self._update_target:
            return entry.check_source

        if self._action == DiscoveryAction.BULK_UPDATE:
            # actions that apply to monitored services are also applied to changed services,
            # since these are a subset of monitored services, but are classified differently.
            if entry.check_source != self._update_source and not (
                entry.check_source == DiscoveryState.CHANGED
                and self._update_source == DiscoveryState.MONITORED
            ):
                return entry.check_source

            if (entry.check_plugin_name, entry.item) in self._selected_services:
                return self._update_target

        if self._action in [
            DiscoveryAction.SINGLE_UPDATE,
            DiscoveryAction.SINGLE_UPDATE_SERVICE_PROPERTIES,
        ]:
            if (entry.check_plugin_name, entry.item) in self._selected_services:
                return self._update_target

        return entry.check_source

    @staticmethod
    def _get_effective_check_tables(
        discovery_result: DiscoveryResult, target_host_name: HostName
    ) -> Mapping[HostName, Sequence[CheckPreviewEntry]]:
        def _entry_key(entry: CheckPreviewEntry) -> tuple[str, Item]:
            return entry.check_plugin_name, entry.item

        effective_check_tables: Mapping[HostName, list[CheckPreviewEntry]] = {
            **{target_host_name: list(discovery_result.check_table)},
            **{node_host_name: [] for node_host_name in discovery_result.nodes_check_table.keys()},
        }
        cluster_entries_lookup = {
            _entry_key(cluster_entry) for cluster_entry in discovery_result.check_table
        }

        # Only relevant for clusters. Find the affected check tables on the nodes and run
        # all the discovery actions on the nodes as well.
        for host_name, check_table in discovery_result.nodes_check_table.items():
            table_entries = {_entry_key(e): e for e in check_table}
            effective_check_tables[host_name].extend(
                [
                    table_entries[key]
                    for key in cluster_entries_lookup.intersection(set(table_entries.keys()))
                ]
            )
        return effective_check_tables


@contextmanager
def _service_discovery_context(host: Host) -> Iterator[None]:
    user.need_permission("wato.services")

    # no try/finally here.
    yield

    if not host.locked():
        host.clear_discovery_failed()


def perform_fix_all(
    discovery_result: DiscoveryResult,
    *,
    host: Host,
    raise_errors: bool,
) -> DiscoveryResult:
    """
    Handle fix all ('Accept All' on UI) discovery action
    """
    with _service_discovery_context(host):
        _perform_update_host_labels(discovery_result.labels_by_host)
        Discovery(
            host,
            DiscoveryAction.FIX_ALL,
            update_target=None,
            update_source=None,
            selected_services=(),  # does not matter in case of "FIX_ALL"
        ).do_discovery(discovery_result, host.name())
        discovery_result = get_check_table(host, DiscoveryAction.FIX_ALL, raise_errors=raise_errors)
    return discovery_result


def perform_host_label_discovery(
    action: DiscoveryAction,
    discovery_result: DiscoveryResult,
    *,
    host: Host,
    raise_errors: bool,
) -> DiscoveryResult:
    """Handle update host labels discovery action"""
    with _service_discovery_context(host):
        _perform_update_host_labels(discovery_result.labels_by_host)
        discovery_result = get_check_table(host, action, raise_errors=raise_errors)
    return discovery_result


def perform_service_discovery(
    action: DiscoveryAction,
    discovery_result: DiscoveryResult,
    update_source: str | None,
    update_target: str | None,
    *,
    host: Host,
    selected_services: Container[tuple[str, Item]],
    raise_errors: bool,
) -> DiscoveryResult:
    """
    Handle discovery action for Update Services, Single Update & Bulk Update
    """
    with _service_discovery_context(host):
        Discovery(
            host,
            action,
            update_target=update_target,
            update_source=update_source,
            selected_services=selected_services,
        ).do_discovery(discovery_result, host.name())
        discovery_result = get_check_table(host, action, raise_errors=raise_errors)
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
        case DiscoveryAction.SINGLE_UPDATE | DiscoveryAction.SINGLE_UPDATE_SERVICE_PROPERTIES:
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
        case DiscoveryAction.UPDATE_SERVICE_LABELS:
            return user.may("wato.services")
        case DiscoveryAction.UPDATE_DISCOVERY_PARAMETERS:
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
    action: DiscoveryAction,
    host: Host,
    previous_discovery_result: DiscoveryResult | None,
    raise_errors: bool,
) -> DiscoveryResult:
    return (
        get_check_table(host, action, raise_errors=raise_errors)
        if previous_discovery_result is None or previous_discovery_result.is_active()
        else previous_discovery_result
    )


def _perform_update_host_labels(labels_by_nodes: Mapping[HostName, Sequence[HostLabel]]) -> None:
    for host_name, host_labels in labels_by_nodes.items():
        if (host := Host.host(host_name)) is None:
            raise ValueError(f"no such host: {host_name!r}")

        message = _("Updated discovered host labels of '%s' with %d labels") % (
            host_name,
            len(host_labels),
        )
        _changes.add_service_change(
            "update-host-labels",
            message,
            host.object_ref(),
            [config_domain_registry[CORE_DOMAIN]],
            {CORE_DOMAIN: generate_hosts_to_update_settings([host.name()])},
            host.site_id(),
        )
        update_host_labels(
            host.site_id(),
            host.name(),
            host_labels,
        )


def _apply_state_change(
    table_source: str,
    table_target: str,
    key: ServiceName,
    value: AutocheckEntry,
    descr: str,
    autochecks_to_save: MutableMapping[ServiceName, AutocheckEntry],
    saved_services: set[str],
    add_disabled_rule: set[str],
    remove_disabled_rule: set[str],
) -> None:
    match table_source:
        case DiscoveryState.UNDECIDED:
            _case_undecided(
                table_target,
                key,
                value,
                descr,
                autochecks_to_save,
                saved_services,
                add_disabled_rule,
            )

        case DiscoveryState.VANISHED:
            _case_vanished(
                table_target,
                key,
                value,
                descr,
                autochecks_to_save,
                saved_services,
                add_disabled_rule,
            )

        case DiscoveryState.MONITORED:
            _case_monitored(
                table_target,
                key,
                value,
                descr,
                autochecks_to_save,
                saved_services,
                add_disabled_rule,
            )

        case DiscoveryState.CHANGED:
            _case_changed(
                table_target,
                key,
                value,
                descr,
                autochecks_to_save,
                saved_services,
                add_disabled_rule,
            )

        case DiscoveryState.IGNORED:
            _case_ignored(
                table_target,
                key,
                value,
                descr,
                autochecks_to_save,
                saved_services,
                add_disabled_rule,
                remove_disabled_rule,
            )

        case (
            DiscoveryState.CLUSTERED_NEW
            | DiscoveryState.CLUSTERED_OLD
            | DiscoveryState.CLUSTERED_VANISHED
            | DiscoveryState.CLUSTERED_IGNORED
        ):
            _case_clustered(
                key,
                value,
                descr,
                autochecks_to_save,
                saved_services,
            )


def _case_undecided(
    table_target: str,
    key: ServiceName,
    value: AutocheckEntry,
    descr: str,
    autochecks_to_save: MutableMapping[ServiceName, AutocheckEntry],
    saved_services: set[str],
    add_disabled_rule: set[str],
) -> None:
    if table_target == DiscoveryState.MONITORED:
        autochecks_to_save[key] = value
        saved_services.add(descr)
    elif table_target == DiscoveryState.IGNORED:
        add_disabled_rule.add(descr)


def _case_vanished(
    table_target: str,
    key: ServiceName,
    value: AutocheckEntry,
    descr: str,
    autochecks_to_save: MutableMapping[ServiceName, AutocheckEntry],
    saved_services: set[str],
    add_disabled_rule: set[str],
) -> None:
    if table_target == DiscoveryState.REMOVED:
        return
    if table_target == DiscoveryState.IGNORED:
        add_disabled_rule.add(descr)
        autochecks_to_save[key] = value
    else:
        autochecks_to_save[key] = value
        saved_services.add(descr)


def _case_monitored(
    table_target: str,
    key: ServiceName,
    value: AutocheckEntry,
    descr: str,
    autochecks_to_save: MutableMapping[ServiceName, AutocheckEntry],
    saved_services: set[str],
    add_disabled_rule: set[str],
) -> None:
    if table_target in [
        DiscoveryState.MONITORED,
        DiscoveryState.IGNORED,
    ]:
        autochecks_to_save[key] = value

    if table_target == DiscoveryState.IGNORED:
        add_disabled_rule.add(descr)
    else:
        saved_services.add(descr)


def _case_changed(
    table_target: str,
    key: ServiceName,
    value: AutocheckEntry,
    descr: str,
    autochecks_to_save: MutableMapping[ServiceName, AutocheckEntry],
    saved_services: set[str],
    add_disabled_rule: set[str],
) -> None:
    if table_target in [
        DiscoveryState.MONITORED,
        DiscoveryState.IGNORED,
        DiscoveryState.CHANGED,
    ]:
        autochecks_to_save[key] = value

    if table_target == DiscoveryState.IGNORED:
        add_disabled_rule.add(descr)
    else:
        saved_services.add(descr)


def _case_ignored(
    table_target: str,
    key: ServiceName,
    value: AutocheckEntry,
    descr: str,
    autochecks_to_save: MutableMapping[ServiceName, AutocheckEntry],
    saved_services: set[str],
    add_disabled_rule: set[str],
    remove_disabled_rule: set[str],
) -> None:
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


def _case_clustered(
    key: ServiceName,
    value: AutocheckEntry,
    descr: str,
    autochecks_to_save: MutableMapping[ServiceName, AutocheckEntry],
    saved_services: set[str],
) -> None:
    # We keep VANISHED clustered services on the node with the following reason:
    # If a service is mapped to a cluster then there are already operations
    # for adding, removing, etc. of this service on the cluster. Therefore we
    # do not allow any operation for this clustered service on the related node.
    # We just display the clustered service state (OLD, NEW, VANISHED).
    autochecks_to_save[key] = value
    saved_services.add(descr)


def _make_host_audit_log_object(
    autochecks_table: SetAutochecksInput,
) -> list[tuple[HostName, set[str]]]:
    """The resulting object is used for building object diffs"""

    return [
        (
            autochecks_table.discovered_host,
            set(autochecks_table.target_services.keys()),
        )
    ] + [
        (autochecks_host_name, set(checks.keys()))
        for autochecks_host_name, checks in autochecks_table.nodes_services.items()
    ]


def checkbox_id(check_type: str, item: Item) -> str:
    """Generate HTML variable for service

    This needs to be unique for each host. Since this text is used as
    variable name, it must not contain any umlauts or other special characters that
    are disallowed by html.parse_field_storage(). Since item may contain such
    chars, we need to use some encoded form of it. Simple escaping/encoding like we
    use for values of variables is not enough here.

    Examples:

        >>> checkbox_id("df", "/opt/omd/sites/testering/tmp")
        '64663a2f6f70742f6f6d642f73697465732f746573746572696e672f746d70'

    Returns:
        A string representing the service checkbox

    """
    return f"{check_type}:{item or ''}".encode().hex()


def checkbox_service(checkbox_id_value: str) -> tuple[str, Item]:
    """Invert checkbox_id

    Examples:

        >>> checkbox_service(checkbox_id("uptime", None))
        ('uptime', None)
        >>> checkbox_service(checkbox_id("df", "/"))
        ('df', '/')

    """
    check_name, item_str = bytes.fromhex(checkbox_id_value).decode("utf8").split(":", 1)
    return check_name, item_str or None


def get_check_table(host: Host, action: DiscoveryAction, *, raise_errors: bool) -> DiscoveryResult:
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
    if action == DiscoveryAction.TABULA_RASA:
        _changes.add_service_change(
            "refresh-autochecks",
            _("Refreshed check configuration of host '%s'") % host.name(),
            host.object_ref(),
            [config_domain_registry[CORE_DOMAIN]],
            {CORE_DOMAIN: generate_hosts_to_update_settings([host.name()])},
            host.site_id(),
        )

    if site_is_local(active_config, host.site_id()):
        return execute_discovery_job(
            host.name(),
            action,
            raise_errors=raise_errors,
        )

    sync_changes_before_remote_automation(host.site_id())

    return DiscoveryResult.deserialize(
        str(
            do_remote_automation(
                get_site_config(active_config, host.site_id()),
                "service-discovery-job",
                [
                    ("host_name", host.name()),
                    ("options", json.dumps({"ignore_errors": not raise_errors, "action": action})),
                ],
            )
        )
    )


class ServiceDiscoveryJobArgs(BaseModel, frozen=True):
    host_name: HostName
    action: DiscoveryAction
    raise_errors: bool


def discovery_job_entry_point(
    job_interface: BackgroundProcessInterface,
    args: ServiceDiscoveryJobArgs,
) -> None:
    job = ServiceDiscoveryBackgroundJob(args.host_name)
    with job_interface.gui_context():
        job.discover(args.action, raise_errors=args.raise_errors)


def execute_discovery_job(
    host_name: HostName,
    action: DiscoveryAction,
    *,
    raise_errors: bool,
) -> DiscoveryResult:
    """Either execute the discovery job to scan the host or return the discovery result
    based on the currently cached data"""
    job = ServiceDiscoveryBackgroundJob(host_name)

    if not job.is_active() and action in [
        DiscoveryAction.REFRESH,
        DiscoveryAction.TABULA_RASA,
    ]:
        if (
            result := job.start(
                JobTarget(
                    callable=discovery_job_entry_point,
                    args=ServiceDiscoveryJobArgs(
                        host_name=host_name,
                        action=action,
                        raise_errors=raise_errors,
                    ),
                ),
                InitialStatusArgs(
                    title=_("Service discovery"),
                    stoppable=True,
                    host_name=str(host_name),
                    estimated_duration=job.get_status().duration,
                    user=str(user.id) if user.id else None,
                ),
            )
        ).is_error():
            raise result.error

    if job.is_active() and action == DiscoveryAction.STOP:
        job.stop()

    return job.get_result()


class ServiceDiscoveryBackgroundJob(BackgroundJob):
    """The background job is always executed on the site where the host is located on"""

    job_prefix = "service_discovery"
    housekeeping_max_age_sec = 86400  # 1 day
    housekeeping_max_count = 20

    @classmethod
    def gui_title(cls) -> str:
        return _("Service discovery")

    def __init__(self, host_name: HostName) -> None:
        host_name_hash = hashlib.sha256(host_name.encode("utf-8")).hexdigest()
        super().__init__(f"{self.job_prefix}-{host_name[:20]}-{host_name_hash}")
        self.host_name: Final = host_name

        self._preview_store = ObjectStore(
            Path(self.get_work_dir(), "check_table.mk"), serializer=TextSerializer()
        )
        self._pre_discovery_preview = (
            0,
            ServiceDiscoveryPreviewResult(
                output="",
                check_table=[],
                nodes_check_table={},
                host_labels={},
                new_labels={},
                vanished_labels={},
                changed_labels={},
                source_results={},
                labels_by_host={},
            ),
        )

    def _store_last_preview(self, result: ServiceDiscoveryPreviewResult) -> None:
        self._preview_store.write_obj(result.serialize(Version.from_str(__version__)))

    def _load_last_preview(self) -> tuple[int, ServiceDiscoveryPreviewResult] | None:
        try:
            return (
                int(self._preview_store.path.stat().st_mtime),
                ServiceDiscoveryPreviewResult.deserialize(
                    SerializedResult(self._preview_store.read_obj(default=""))
                ),
            )
        except (FileNotFoundError, ValueError):
            return None
        finally:
            self._preview_store.path.unlink(missing_ok=True)

    def discover(self, action: DiscoveryAction, *, raise_errors: bool) -> None:
        """Target function of the background job"""
        sys.stdout.write("Starting job...\n")
        self._pre_discovery_preview = self._get_discovery_preview()

        if action == DiscoveryAction.REFRESH:
            self._jobstatus_store.update({"title": _("Refresh")})
            self._perform_service_scan(raise_errors=raise_errors)

        elif action == DiscoveryAction.TABULA_RASA:
            self._jobstatus_store.update({"title": _("Tabula rasa")})
            self._perform_automatic_refresh()

        else:
            raise NotImplementedError()
        sys.stdout.write("Completed.\n")

    def _perform_service_scan(self, *, raise_errors: bool) -> None:
        """The service-discovery-preview automation refreshes the Checkmk internal cache and makes
        the new information available to the next service-discovery-preview call made by get_result().
        """
        result = local_discovery_preview(
            self.host_name,
            prevent_fetching=False,
            raise_errors=raise_errors,
        )
        self._store_last_preview(result)
        sys.stdout.write(result.output)

    def _perform_automatic_refresh(self) -> None:
        # TODO: In distributed sites this must not add a change on the remote site. We need to build
        # the way back to the central site and show the information there.
        local_discovery(
            "refresh",
            [self.host_name],
            scan=True,
            raise_errors=False,
            non_blocking_http=True,
        )
        # count_added, _count_removed, _count_kept, _count_new = counts[api_request.host.name()]
        # message = _("Refreshed check configuration of host '%s' with %d services") % \
        #            (api_request.host.name(), count_added)
        # _changes.add_service_change(api_request.host, "refresh-autochecks", message)

    def get_result(self) -> DiscoveryResult:
        """Executed from the outer world to report about the job state"""
        job_status = self.get_status()
        job_status.is_active = self.is_active()
        if not job_status.is_active:
            if job_status.state == JobStatusStates.EXCEPTION:
                job_status = self._cleaned_up_status(job_status)

        if job_status.is_active:
            check_table_created, result = self._pre_discovery_preview
        elif (last_result := self._load_last_preview()) is not None:
            check_table_created, result = last_result
        else:
            check_table_created, result = self._get_discovery_preview()

        return DiscoveryResult(
            job_status=dict(job_status),
            check_table_created=check_table_created,
            check_table=result.check_table,
            nodes_check_table=result.nodes_check_table,
            host_labels=result.host_labels,
            new_labels=result.new_labels,
            vanished_labels=result.vanished_labels,
            changed_labels=result.changed_labels,
            labels_by_host=result.labels_by_host,
            sources=result.source_results,
        )

    def _get_discovery_preview(self) -> tuple[int, ServiceDiscoveryPreviewResult]:
        return (
            int(time.time()),
            local_discovery_preview(self.host_name, prevent_fetching=False, raise_errors=False),
        )

    @staticmethod
    def _cleaned_up_status(job_status: JobStatusSpec) -> JobStatusSpec:
        # There might be an exception when calling above 'check_mk_automation'. For example
        # this may happen if a hostname is not resolvable. Then if the error is fixed, ie.
        # configuring an IP address of this host, and the discovery is started again, we put
        # the cached/last job exception into the current job progress update instead of displaying
        # the error in a CRIT message box again.
        new_loginfo = {
            "JobProgressUpdate": [
                "%s:" % _("Last progress update"),
                *job_status.loginfo["JobProgressUpdate"],
                "%s:" % _("Last exception"),
                *job_status.loginfo["JobException"],
            ],
            "JobException": [],
            "JobResult": job_status.loginfo["JobResult"],
        }
        return job_status.model_copy(
            update={"state": JobStatusStates.FINISHED, "loginfo": new_loginfo},
            deep=True,  # not sure, better play it safe.
        )
