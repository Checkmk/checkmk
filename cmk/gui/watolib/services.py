#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="exhaustive-match"

# mypy: disable-error-code="type-arg"

from __future__ import annotations

import ast
import dataclasses
import enum
import hashlib
import json
import sys
import time
from collections.abc import (
    Callable,
    Container,
    Iterator,
    Mapping,
    MutableMapping,
    Sequence,
)
from contextlib import contextmanager
from pathlib import Path
from typing import assert_never, Final, Literal, NamedTuple

from pydantic import BaseModel

import cmk.gui.watolib.changes as _changes
from cmk.automations.results import (
    SerializedResult,
    ServiceDiscoveryPreviewResult,
    SetAutochecksInput,
)
from cmk.ccc.hostaddress import HostName
from cmk.ccc.store import ObjectStore, TextSerializer
from cmk.ccc.version import __version__, Version
from cmk.checkengine.discovery import CheckPreviewEntry, DiscoverySettings
from cmk.checkengine.plugins import AutocheckEntry, CheckPluginName
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobStatusSpec,
    JobStatusStates,
    JobTarget,
)
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions, UserPermissionSerializableConfig
from cmk.gui.watolib.activate_changes import sync_changes_before_remote_automation
from cmk.gui.watolib.automations import (
    AnnotatedHostName,
    do_remote_automation,
)
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
from cmk.gui.watolib.rulesets import EnabledDisabledServicesEditor, may_edit_ruleset
from cmk.utils.automation_config import LocalAutomationConfig, RemoteAutomationConfig
from cmk.utils.labels import HostLabel, HostLabelValueDict
from cmk.utils.object_diff import make_diff_text
from cmk.utils.servicename import Item, ServiceName


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
    ACTIVE_IGNORED = "ignored_active"
    CUSTOM_IGNORED = "ignored_custom"

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
    """This is exported to javascript, so it has to be json serializable"""

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
    config_warnings: Sequence[str]

    def serialize(self, for_cmk_version: Version) -> str:
        raw_tuple = (
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
            self.config_warnings,
        )
        if for_cmk_version < Version.from_str("2.5.0b1"):
            return repr(raw_tuple[:10])
        return repr(raw_tuple)

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
            config_warnings,
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
            config_warnings,
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


@dataclasses.dataclass(frozen=True)
class DiscoveryTransition:
    """Describes the computed transition of the discovery state"""

    need_sync: bool
    remove_disabled_rule: set[str]
    add_disabled_rule: set[str]
    old_autochecks: SetAutochecksInput
    new_autochecks: SetAutochecksInput


class Discovery:
    def __init__(
        self,
        host: Host,
        action: DiscoveryAction,
        *,
        update_target: str | None,
        update_source: str | None = None,
        selected_services: Container[tuple[str, Item]],
        user_need_permission: Callable[[str], None],
    ) -> None:
        self._host = host
        self._action = action
        self._update_source = update_source
        self._update_target = update_target
        self._selected_services = selected_services
        self.user_need_permission: Final = user_need_permission

    def _get_selected_descriptions(
        self, discovery_result: DiscoveryResult, hostname: HostName
    ) -> Iterator[str]:
        for nodename, check_table in self._get_effective_check_tables(
            discovery_result, hostname
        ).items():
            for entry in check_table:
                if (entry.check_plugin_name, entry.item) in self._selected_services:
                    yield entry.description

    def do_discovery(
        self,
        discovery_result: DiscoveryResult,
        target_host_name: HostName,
        *,
        automation_config: LocalAutomationConfig | RemoteAutomationConfig,
        pprint_value: bool,
        debug: bool,
        use_git: bool,
    ) -> None:
        if (
            transition := self.compute_discovery_transition(discovery_result, target_host_name)
        ) is None:
            return

        if transition.need_sync:
            self._save_host_service_enable_disable_rules(
                transition.remove_disabled_rule,
                transition.add_disabled_rule,
                automation_config=automation_config,
                pprint_value=pprint_value,
                debug=debug,
                use_git=use_git,
            )

        self._save_services(
            target_host_name,
            transition.old_autochecks,
            transition.new_autochecks,
            need_sync=transition.need_sync,
            automation_config=automation_config,
            debug=debug,
            use_git=use_git,
        )

    def compute_discovery_transition(
        self, discovery_result: DiscoveryResult, target_host_name: HostName
    ) -> DiscoveryTransition | None:
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
        selected_services: set[str] = set()
        apply_changes: bool = False

        for autochecks_host_name, check_table in self._get_effective_check_tables(
            discovery_result, target_host_name
        ).items():
            unchanged_services: MutableMapping[ServiceName, AutocheckEntry] = {}
            changed_services: MutableMapping[ServiceName, AutocheckEntry] = {}
            selected_services |= set(
                self._get_selected_descriptions(discovery_result, autochecks_host_name)
            )
            for entry in check_table:
                key = ServiceName(entry.description)
                table_target = self._get_table_target(entry)
                self._verify_permissions(table_target, entry)
                unchanged_value, changed_value = self._get_autochecks_values(table_target, entry)

                if entry.check_source != table_target:
                    apply_changes = True

                _apply_state_change(
                    table_source=entry.check_source,
                    table_target=table_target,
                    key=key,
                    value=changed_value,
                    descr=entry.description,
                    autochecks_to_save=changed_services,
                    saved_services=saved_services,
                    add_disabled_rule=add_disabled_rule,
                    remove_disabled_rule=remove_disabled_rule,
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

        if not apply_changes:
            return None

        return DiscoveryTransition(
            need_sync=bool(
                remove_disabled_rule or add_disabled_rule
            ),  # Watch out! Can't be derived form the next two!
            remove_disabled_rule=remove_disabled_rule,
            # Caveats for duplicate service descriptions:
            # 1. If a plugin is disabled, we don't want to create "disabled services" rules for its services.
            # 2. If a user wants to disable a service, the "disabled services" rule must be created.
            add_disabled_rule=(
                add_disabled_rule - remove_disabled_rule - (saved_services - selected_services)
            ),
            old_autochecks=SetAutochecksInput(
                target_host_name, unchanged_target_services, unchanged_nodes_services
            ),
            new_autochecks=SetAutochecksInput(
                target_host_name, changed_target_services, changed_nodes_services
            ),
        )

    def _save_host_service_enable_disable_rules(
        self,
        remove_disabled_rule: set[str],
        add_disabled_rule: set[str],
        *,
        automation_config: LocalAutomationConfig | RemoteAutomationConfig,
        pprint_value: bool,
        debug: bool,
        use_git: bool,
    ) -> None:
        EnabledDisabledServicesEditor(self._host).save_host_service_enable_disable_rules(
            remove_disabled_rule,
            add_disabled_rule,
            automation_config=automation_config,
            pprint_value=pprint_value,
            debug=debug,
            use_git=use_git,
        )

    def _verify_permissions(self, table_target: str, entry: CheckPreviewEntry) -> None:
        if entry.check_source != table_target:
            match table_target:
                case DiscoveryState.UNDECIDED:
                    self.user_need_permission("wato.service_discovery_to_undecided")
                case (
                    DiscoveryState.MONITORED
                    | DiscoveryState.CHANGED
                    | DiscoveryState.CLUSTERED_NEW
                    | DiscoveryState.CLUSTERED_OLD
                ):
                    self.user_need_permission("wato.service_discovery_to_monitored")
                case DiscoveryState.IGNORED:
                    self.user_need_permission("wato.service_discovery_to_ignored")
                case DiscoveryState.REMOVED:
                    self.user_need_permission("wato.service_discovery_to_removed")

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
        *,
        need_sync: bool,
        automation_config: LocalAutomationConfig | RemoteAutomationConfig,
        debug: bool,
        use_git: bool,
    ) -> None:
        message = _("Saved check configuration of host '%s' with %d services") % (
            affected_host_name,
            len(autochecks_table.target_services),
        )
        self._add_service_change(
            message, need_sync, old_autochecks, autochecks_table, use_git=use_git
        )
        set_autochecks_v2(automation_config, autochecks_table, debug=debug)

    def _add_service_change(
        self,
        message: str,
        need_sync: bool,
        old_autochecks: SetAutochecksInput,
        autochecks_table: SetAutochecksInput,
        *,
        use_git: bool,
    ) -> None:
        _changes.add_service_change(
            action_name="set-autochecks",
            text=message,
            user_id=user.id,
            object_ref=self._host.object_ref(),
            domains=[config_domain_registry[CORE_DOMAIN]],
            domain_settings={CORE_DOMAIN: generate_hosts_to_update_settings([self._host.name()])},
            site_id=self._host.site_id(),
            need_sync=need_sync,
            diff_text=make_diff_text(
                _make_host_audit_log_object(old_autochecks),
                _make_host_audit_log_object(autochecks_table),
            ),
            use_git=use_git,
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

        cluster_entries_nodes = {
            _entry_key(cluster_entry): cluster_entry.found_on_nodes
            for cluster_entry in discovery_result.check_table
        }

        def _should_be_kept(node_name: HostName, entry: CheckPreviewEntry) -> bool:
            try:
                found_on_nodes = cluster_entries_nodes[_entry_key(entry)]
            except KeyError:
                return False  # not clustered at all -> not of interest here.
            if found_on_nodes:
                # The service is found on some nodes.
                # We need to drop it from all other nodes, so that the newly
                # discovered parameters can not be overwritten by other, older
                # discovered parameters (and labels, respectively).
                return node_name in found_on_nodes
            # The service is not found on any node.
            # Me must not remove it, otherwise the user will experience "vanished"
            # services being silently dropped.
            return True

        return {
            target_host_name: discovery_result.check_table,
            # Only relevant for clusters. Find the affected check tables on the nodes and run
            # all the discovery actions on the nodes as well.
            **{
                node_name: [entry for entry in check_table if _should_be_kept(node_name, entry)]
                for node_name, check_table in discovery_result.nodes_check_table.items()
            },
        }


@contextmanager
def _service_discovery_context(host: Host, *, pprint_value: bool) -> Iterator[None]:
    user.need_permission("wato.services")

    # no try/finally here.
    yield

    if not host.locked():
        host.clear_discovery_failed(pprint_value=pprint_value)


def perform_fix_all(
    discovery_result: DiscoveryResult,
    *,
    host: Host,
    raise_errors: bool,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    user_permission_config: UserPermissionSerializableConfig,
    pprint_value: bool,
    debug: bool,
    use_git: bool,
) -> DiscoveryResult:
    """
    Handle fix all ('Accept All' on UI) discovery action
    """
    with _service_discovery_context(host, pprint_value=pprint_value):
        _perform_update_host_labels(
            discovery_result.labels_by_host,
            automation_config=automation_config,
            debug=debug,
            use_git=use_git,
        )
        Discovery(
            host,
            DiscoveryAction.FIX_ALL,
            update_target=None,
            update_source=None,
            selected_services=(),  # does not matter in case of "FIX_ALL"
            user_need_permission=user.need_permission,
        ).do_discovery(
            discovery_result,
            host.name(),
            automation_config=automation_config,
            pprint_value=pprint_value,
            debug=debug,
            use_git=use_git,
        )
        discovery_result = get_check_table(
            host,
            DiscoveryAction.FIX_ALL,
            automation_config=automation_config,
            user_permission_config=user_permission_config,
            raise_errors=raise_errors,
            debug=debug,
            use_git=use_git,
        )
    return discovery_result


def perform_host_label_discovery(
    action: DiscoveryAction,
    discovery_result: DiscoveryResult,
    *,
    host: Host,
    raise_errors: bool,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    user_permission_config: UserPermissionSerializableConfig,
    pprint_value: bool,
    debug: bool,
    use_git: bool,
) -> DiscoveryResult:
    """Handle update host labels discovery action"""
    with _service_discovery_context(host, pprint_value=pprint_value):
        _perform_update_host_labels(
            discovery_result.labels_by_host,
            automation_config=automation_config,
            debug=debug,
            use_git=use_git,
        )
        discovery_result = get_check_table(
            host,
            action,
            automation_config=automation_config,
            user_permission_config=user_permission_config,
            raise_errors=raise_errors,
            debug=debug,
            use_git=use_git,
        )
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
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    user_permission_config: UserPermissionSerializableConfig,
    pprint_value: bool,
    debug: bool,
    use_git: bool,
) -> DiscoveryResult:
    """
    Handle discovery action for Update Services, Single Update & Bulk Update
    """
    with _service_discovery_context(host, pprint_value=pprint_value):
        Discovery(
            host,
            action,
            update_target=update_target,
            update_source=update_source,
            selected_services=selected_services,
            user_need_permission=user.need_permission,
        ).do_discovery(
            discovery_result,
            host.name(),
            automation_config=automation_config,
            pprint_value=pprint_value,
            debug=debug,
            use_git=use_git,
        )
        discovery_result = get_check_table(
            host,
            action,
            automation_config=automation_config,
            user_permission_config=user_permission_config,
            raise_errors=raise_errors,
            debug=debug,
            use_git=use_git,
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
    *,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    user_permission_config: UserPermissionSerializableConfig,
    raise_errors: bool,
    debug: bool,
    use_git: bool,
) -> DiscoveryResult:
    return (
        get_check_table(
            host,
            action,
            automation_config=automation_config,
            user_permission_config=user_permission_config,
            raise_errors=raise_errors,
            debug=debug,
            use_git=use_git,
        )
        if previous_discovery_result is None or previous_discovery_result.is_active()
        else previous_discovery_result
    )


def _perform_update_host_labels(
    labels_by_nodes: Mapping[HostName, Sequence[HostLabel]],
    *,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    debug: bool,
    use_git: bool,
) -> None:
    for host_name, host_labels in labels_by_nodes.items():
        if (host := Host.host(host_name)) is None:
            raise ValueError(f"no such host: {host_name!r}")

        message = _("Updated discovered host labels of '%s' with %d labels") % (
            host_name,
            len(host_labels),
        )
        _changes.add_service_change(
            action_name="update-host-labels",
            text=message,
            user_id=user.id,
            object_ref=host.object_ref(),
            domains=[config_domain_registry[CORE_DOMAIN]],
            domain_settings={CORE_DOMAIN: generate_hosts_to_update_settings([host.name()])},
            site_id=host.site_id(),
            use_git=use_git,
        )
        update_host_labels(automation_config, host.name(), host_labels, debug=debug)


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
                table_target,
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
    table_target: str,
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
    # But if the user wants to disable the service on the host, this is what we do.
    # Ideally, there would be no service discovery on the cluster hosts at all.
    if table_target != "ignored":
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


def get_check_table(
    host: Host,
    action: DiscoveryAction,
    *,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    user_permission_config: UserPermissionSerializableConfig,
    raise_errors: bool,
    debug: bool,
    use_git: bool,
) -> DiscoveryResult:
    """Gathers the check table using a background job

    Cares about handling local / remote sites using an automation call. In both cases
    the ServiceDiscoveryBackgroundJob is executed to care about collecting the check
    table asynchronously. In case of a remote site the chain is:

    Starting from central site:

    get_check_table()
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
    get_check_table()
    """
    if action == DiscoveryAction.TABULA_RASA:
        _changes.add_service_change(
            action_name="refresh-autochecks",
            text=_("Refreshed check configuration of host '%s'") % host.name(),
            user_id=user.id,
            object_ref=host.object_ref(),
            domains=[config_domain_registry[CORE_DOMAIN]],
            domain_settings={CORE_DOMAIN: generate_hosts_to_update_settings([host.name()])},
            site_id=host.site_id(),
            use_git=use_git,
        )

    if isinstance(automation_config, LocalAutomationConfig):
        return execute_discovery_job(
            host.name(),
            action,
            user_permission_config=user_permission_config,
            raise_errors=raise_errors,
            debug=debug,
        )

    sync_changes_before_remote_automation(host.site_id(), debug)

    return DiscoveryResult.deserialize(
        str(
            do_remote_automation(
                automation_config,
                "service-discovery-job",
                [
                    ("host_name", host.name()),
                    (
                        "options",
                        json.dumps(
                            {
                                "ignore_errors": not raise_errors,
                                "action": action,
                                "debug": debug,
                            }
                        ),
                    ),
                ],
                debug=debug,
            )
        )
    )


class ServiceDiscoveryJobArgs(BaseModel, frozen=True):
    user_permission_config: UserPermissionSerializableConfig
    host_name: AnnotatedHostName
    action: DiscoveryAction
    raise_errors: bool
    debug: bool


def discovery_job_entry_point(
    job_interface: BackgroundProcessInterface,
    args: ServiceDiscoveryJobArgs,
) -> None:
    job = ServiceDiscoveryBackgroundJob(args.host_name)
    with job_interface.gui_context(
        UserPermissions.from_serialized_config(args.user_permission_config, permission_registry)
    ):
        job.discover(args.action, raise_errors=args.raise_errors, debug=args.debug)


def execute_discovery_job(
    host_name: HostName,
    action: DiscoveryAction,
    *,
    user_permission_config: UserPermissionSerializableConfig,
    raise_errors: bool,
    debug: bool,
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
                        user_permission_config=user_permission_config,
                        raise_errors=raise_errors,
                        debug=debug,
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

    return job.get_result(debug=debug)


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
                config_warnings=[],
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

    def discover(self, action: DiscoveryAction, *, raise_errors: bool, debug: bool) -> None:
        """Target function of the background job"""
        sys.stdout.write("Starting job...\n")
        self._pre_discovery_preview = self._get_discovery_preview(
            prevent_fetching=action not in (DiscoveryAction.TABULA_RASA, DiscoveryAction.REFRESH),
            debug=debug,
        )

        if action == DiscoveryAction.REFRESH:
            self._jobstatus_store.update({"title": _("Refresh")})
            self._perform_service_scan(raise_errors=raise_errors, debug=debug)

        elif action == DiscoveryAction.TABULA_RASA:
            self._jobstatus_store.update({"title": _("Tabula rasa")})
            self._perform_automatic_refresh(debug=debug)

        else:
            raise NotImplementedError()
        sys.stdout.write("Completed.\n")

    def _perform_service_scan(self, *, raise_errors: bool, debug: bool) -> None:
        """The service-discovery-preview automation refreshes the Checkmk internal cache and makes
        the new information available to the next service-discovery-preview call made by get_result().
        """
        result = local_discovery_preview(
            self.host_name,
            prevent_fetching=False,
            raise_errors=raise_errors,
            debug=debug,
        )
        self._store_last_preview(result)
        sys.stdout.write(result.output)

    def _perform_automatic_refresh(self, *, debug: bool) -> None:
        # TODO: In distributed sites this must not add a change on the remote site. We need to build
        # the way back to the central site and show the information there.
        local_discovery(
            DiscoverySettings(
                update_host_labels=True,
                add_new_services=True,
                remove_vanished_services=False,
                update_changed_service_labels=True,
                update_changed_service_parameters=True,
            ),
            [self.host_name],
            scan=True,
            raise_errors=False,
            non_blocking_http=True,
            debug=debug,
        )
        # count_added, _count_removed, _count_kept, _count_new = counts[api_request.host.name()]
        # message = _("Refreshed check configuration of host '%s' with %d services") % \
        #            (api_request.host.name(), count_added)
        # _changes.add_service_change(api_request.host, "refresh-autochecks", message)

    def get_result(self, *, debug: bool) -> DiscoveryResult:
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
            check_table_created, result = self._get_discovery_preview(
                prevent_fetching=True, debug=debug
            )

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
            config_warnings=result.config_warnings,
        )

    def _get_discovery_preview(
        self, *, prevent_fetching: bool, debug: bool
    ) -> tuple[int, ServiceDiscoveryPreviewResult]:
        return (
            int(time.time()),
            local_discovery_preview(
                self.host_name,
                prevent_fetching=prevent_fetching,
                raise_errors=False,
                debug=debug,
            ),
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
