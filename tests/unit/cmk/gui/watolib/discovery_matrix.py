#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared scaffolding for the service-discovery transition matrix.

The matrix is specified in ``packages/cmk-check-engine/docs/SERVICE_DISCOVERY_BEHAVIOUR_MATRIX.md``:
§11.2 states which ``(state, command)`` pairs are meaningful and what each must produce, §11.2a
states which pairs must be rejected, and §7 splits the tests into a conformance tier
(``test_discovery_transition_matrix.py``) and a quarantine tier
(``test_discovery_transition_quarantine.py``).

Everything here is pure. ``Discovery.compute_discovery_transition`` is a function of a
``DiscoveryResult``, so no mocking is involved. Assertions are made on ``DiscoveryTransition``
fields only -- never on ``_get_table_target``, ``_apply_state_change`` or other private helpers --
so that this tier survives the rewrite it exists to protect.
"""

import dataclasses
import enum
from collections.abc import Container, Mapping, Sequence

from cmk.ccc.hostaddress import HostName
from cmk.checkengine.discovery import CheckPreviewEntry
from cmk.checkengine.plugins import AutocheckEntry, CheckPluginName
from cmk.gui.watolib.services import (
    Discovery,
    DiscoveryAction,
    DiscoveryResult,
    DiscoveryState,
    DiscoveryTransition,
)
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.servicename import Item

HOST = HostName("test-host")
PLUGIN = "dummy_plugin"
DESCRIPTION = "My service"
SERVICE: tuple[str, Item] = (PLUGIN, None)

OLD_PARAMS: Mapping[str, object] = {"p": "old"}
NEW_PARAMS: Mapping[str, object] = {"p": "new"}
OLD_LABELS: Mapping[str, str] = {"l": "old"}
NEW_LABELS: Mapping[str, str] = {"l": "new"}


class Command(enum.StrEnum):
    """The three commands of §11.1.

    Discovery can write exactly two things -- the autochecks entry and the disabled-services
    rule -- and one of the four combinations is forbidden by the §4 invariant, which leaves
    three commands. Today's ``table_target`` strings are their spelling, and ``drop`` has two
    of them: ``new`` ("forget") and ``removed`` ("remove") differ only in the label the UI
    picks from the row, not in what they write (§11.3).
    """

    MONITOR = "monitor"
    DISABLE = "disable"
    DROP = "drop"


COMMAND_TARGETS: Mapping[Command, tuple[str, ...]] = {
    Command.MONITOR: (DiscoveryState.MONITORED,),
    Command.DISABLE: (DiscoveryState.IGNORED,),
    Command.DROP: (DiscoveryState.UNDECIDED, DiscoveryState.REMOVED),
}

PERMISSION_BY_TARGET: Mapping[str, str] = {
    DiscoveryState.UNDECIDED: "wato.service_discovery_to_undecided",
    DiscoveryState.MONITORED: "wato.service_discovery_to_monitored",
    DiscoveryState.IGNORED: "wato.service_discovery_to_ignored",
    DiscoveryState.REMOVED: "wato.service_discovery_to_removed",
}


def make_entry(
    check_source: str,
    *,
    plugin: str = PLUGIN,
    item: Item = None,
    description: str = DESCRIPTION,
    old_params: Mapping[str, object] = OLD_PARAMS,
    new_params: Mapping[str, object] = NEW_PARAMS,
    old_labels: Mapping[str, str] = OLD_LABELS,
    new_labels: Mapping[str, str] = NEW_LABELS,
    found_on_nodes: Sequence[HostName] = (),
) -> CheckPreviewEntry:
    """A preview entry carrying only the fields the transition reads.

    Old and new values differ by default, so that "which values were written" is observable in
    every cell rather than only in the ones that set them up explicitly.
    """
    return CheckPreviewEntry(
        check_source=check_source,
        check_plugin_name=plugin,
        ruleset_name=None,
        discovery_ruleset_name=None,
        item=item,
        old_discovered_parameters=old_params,
        new_discovered_parameters=new_params,
        effective_parameters={},
        description=description,
        state=0,
        output="",
        metrics=[],
        old_labels=old_labels,
        new_labels=new_labels,
        found_on_nodes=list(found_on_nodes),
    )


def make_result(
    check_table: Sequence[CheckPreviewEntry],
    nodes_check_table: Mapping[HostName, Sequence[CheckPreviewEntry]] | None = None,
) -> DiscoveryResult:
    return DiscoveryResult(
        job_status={},
        check_table_created=0,
        check_table=check_table,
        nodes_check_table={} if nodes_check_table is None else nodes_check_table,
        host_labels={},
        new_labels={},
        vanished_labels={},
        changed_labels={},
        labels_by_host={},
        sources=[],
        config_warnings=(),
    )


def compute(
    *,
    action: DiscoveryAction,
    update_target: str | None,
    update_source: str | None = None,
    selected_services: Container[tuple[str, Item]] = (SERVICE,),
    check_table: Sequence[CheckPreviewEntry],
    nodes_check_table: Mapping[HostName, Sequence[CheckPreviewEntry]] | None = None,
    target_host_name: HostName = HOST,
) -> tuple[DiscoveryTransition | None, tuple[str, ...]]:
    """Run the transition and report it together with the permissions it demanded."""
    demanded: list[str] = []
    transition = Discovery(
        host=object(),  # type: ignore[arg-type] # not reached by compute_discovery_transition
        action=action,
        update_target=update_target,
        update_source=update_source,
        selected_services=selected_services,
        user_need_permission=demanded.append,
    ).compute_discovery_transition(make_result(check_table, nodes_check_table), target_host_name)
    return transition, tuple(demanded)


@dataclasses.dataclass(frozen=True)
class Outcome:
    """What one ``(state, command)`` cell does to the single service under test.

    ``params`` and ``labels`` are ``None`` when no autochecks entry is written, which is what
    distinguishes "not stored" from "stored with the old values".
    """

    computed: bool
    in_autochecks: bool
    params: Mapping[str, object] | None = None
    labels: Mapping[str, str] | None = None
    add_disabled: frozenset[str] = frozenset()
    remove_disabled: frozenset[str] = frozenset()
    need_sync: bool = False
    permissions: tuple[str, ...] = ()


NO_TRANSITION = Outcome(computed=False, in_autochecks=False)


def run_cell(
    source: str,
    target: str,
    *,
    action: DiscoveryAction = DiscoveryAction.SINGLE_UPDATE,
    update_source: str | None = None,
) -> Outcome:
    """Apply ``target`` to a single service in state ``source`` and project the result."""
    transition, permissions = compute(
        action=action,
        update_target=target,
        update_source=update_source,
        selected_services=EVERYTHING if action is DiscoveryAction.UPDATE_SERVICES else (SERVICE,),
        check_table=[make_entry(source)],
    )
    if transition is None:
        return Outcome(computed=False, in_autochecks=False, permissions=permissions)

    written = transition.new_autochecks.target_services.get(DESCRIPTION)
    return Outcome(
        computed=True,
        in_autochecks=written is not None,
        params=None if written is None else written.parameters,
        labels=None if written is None else written.service_labels,
        add_disabled=frozenset(transition.add_disabled_rule),
        remove_disabled=frozenset(transition.remove_disabled_rule),
        need_sync=transition.need_sync,
        permissions=permissions,
    )


def autocheck(
    params: Mapping[str, object] = OLD_PARAMS,
    labels: Mapping[str, str] = OLD_LABELS,
    *,
    item: Item = None,
    plugin: str = PLUGIN,
) -> AutocheckEntry:
    return AutocheckEntry(CheckPluginName(plugin), item, params, labels)


def disabled_plus_unrelated_change() -> list[CheckPreviewEntry]:
    """One already-disabled service, plus an unrelated service being accepted.

    The disabled row is the whole subject: `_case_ignored` puts its description into
    `saved_services` **and** into `add_disabled_rule`, which is what the subtraction then has to
    resolve. The second row has a different description and exists only to make `apply_changes`
    true -- without a row that actually changes, no transition is computed at all.
    """
    return [
        make_entry(DiscoveryState.IGNORED),
        make_entry(DiscoveryState.UNDECIDED, item="other", description="Other service"),
    ]


#: Two plugins rendering one description. Werk 6708's example is `CPU utilization`, produced by
#: both an SNMP-based and a TCP-based plugin; werk 19062 restates the premise as "Different check
#: plugins may have the same service description".
SHARED_DESCRIPTION = "CPU utilization"
SNMP_PLUGIN = "cpu_utilization_snmp"
TCP_PLUGIN = "cpu_utilization_tcp"


def two_plugins_one_description() -> list[CheckPreviewEntry]:
    """One description from two plugins, one of them disabled by a *Disabled checks* rule.

    The configuration the `add_disabled_rule` subtraction term exists for, and the reproduction
    from werks 6708 and 19062: a *Disabled checks* rule names the SNMP plugin, so its service is
    classified `ignored`, while the TCP plugin's identically-described service is discovered
    normally. Writing a *Disabled services* rule for the first would suppress the second too --
    werk 6708's *"As a side effect, the TCP based CPU utilization check was disabled as well"*.

    **Which ruleset does the disabling is the whole point.** A *Disabled services* rule cannot
    produce this state: `ignore_service` matches on host + description, so it matches both rows or
    neither. Only `ignore_plugin`, which matches on the plugin name
    (`ConfigCache.check_plugin_ignored`), can single one of them out.

    Shared between the conformance tier (where the guard holds) and the quarantine tier (where a
    selection of `EVERYTHING` collapses it), because the divergence is only visible by running the
    *same* table down both paths.
    """
    return [
        make_entry(DiscoveryState.IGNORED, plugin=SNMP_PLUGIN, description=SHARED_DESCRIPTION),
        make_entry(DiscoveryState.UNDECIDED, plugin=TCP_PLUGIN, description=SHARED_DESCRIPTION),
    ]
