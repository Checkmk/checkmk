#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tier 1a -- conformance tests for the service-discovery transition matrix.

Specified in ``packages/cmk-check-engine/docs/SERVICE_DISCOVERY_BEHAVIOUR_MATRIX.md`` §7.

These are the cells where today's behaviour already matches the intended semantics of §11.2.
They are the actual regression guardrail for CMK-32255 / CMK-37497 and must stay green through
every phase of the rewrite. **The expected values below are §11.2's, not a transcript of the
code**: a cell that disagrees with §11.2 does not belong here, it belongs in the quarantine tier
(``test_discovery_transition_quarantine.py``) with a ticket reference.
"""

from collections.abc import Callable, Container, Mapping, Sequence
from typing import get_args

import pytest

from cmk.ccc.hostaddress import HostName

# `Transition` is the check engine's *private* vocabulary of row states. It is imported here on
# purpose: `test_removed_is_not_a_source_state` asserts a claim that spans the boundary -- that the
# GUI's `DiscoveryState` contains a value no classifier on the other side can produce -- and there
# is no public spelling of that vocabulary to assert against.
from cmk.checkengine.discovery._autodiscovery import Transition
from cmk.gui.watolib import services as services_module
from cmk.gui.watolib.services import (
    DiscoveryAction,
    DiscoveryState,
    has_discovery_action_specific_permissions,
    UpdateType,
)
from cmk.utils.everythingtype import EVERYTHING
from tests.unit.cmk.gui.watolib.discovery_matrix import (
    autocheck,
    Command,
    COMMAND_TARGETS,
    compute,
    DESCRIPTION,
    disabled_plus_unrelated_change,
    make_entry,
    NEW_LABELS,
    NEW_PARAMS,
    NO_TRANSITION,
    OLD_LABELS,
    OLD_PARAMS,
    Outcome,
    PERMISSION_BY_TARGET,
    PLUGIN,
    run_cell,
    SHARED_DESCRIPTION,
    TCP_PLUGIN,
    two_plugins_one_description,
)

# --------------------------------------------------------------------------------------------
# T1a.1 / T1a.3 -- the meaningful cells of §11.2 that are already correct today
#
# Of the ten meaningful (state, command) pairs, eight have at least one realisation that agrees
# with §11.2 and are pinned here. `changed + monitor`, `ignored + drop` and `vanished + drop` are
# correct in one realisation only -- the other one is quarantined (T1b.8, T1b.6, T1b.5). The two
# remaining pairs, `unchanged + disable` and `changed + disable`, have no correct realisation at
# all and live entirely in the quarantine tier (T1b.1, T1b.2).
# --------------------------------------------------------------------------------------------

_MEANINGFUL_CELLS: Sequence[tuple[str, Command, str, DiscoveryAction, Outcome]] = (
    # source, command, target ("the label"), action, expected outcome per §11.2
    (
        DiscoveryState.UNDECIDED,
        Command.MONITOR,
        DiscoveryState.MONITORED,
        DiscoveryAction.SINGLE_UPDATE,
        Outcome(
            computed=True,
            in_autochecks=True,
            params=OLD_PARAMS,
            labels=OLD_LABELS,
            permissions=("wato.service_discovery_to_monitored",),
        ),
    ),
    (
        DiscoveryState.UNDECIDED,
        Command.DISABLE,
        DiscoveryState.IGNORED,
        DiscoveryAction.SINGLE_UPDATE,
        Outcome(
            computed=True,
            in_autochecks=False,
            add_disabled=frozenset({DESCRIPTION}),
            need_sync=True,
            permissions=("wato.service_discovery_to_ignored",),
        ),
    ),
    (
        DiscoveryState.MONITORED,
        Command.DROP,
        DiscoveryState.UNDECIDED,
        DiscoveryAction.SINGLE_UPDATE,
        Outcome(
            computed=True,
            in_autochecks=False,
            permissions=("wato.service_discovery_to_undecided",),
        ),
    ),
    (
        DiscoveryState.CHANGED,
        Command.DROP,
        DiscoveryState.UNDECIDED,
        DiscoveryAction.SINGLE_UPDATE,
        Outcome(
            computed=True,
            in_autochecks=False,
            permissions=("wato.service_discovery_to_undecided",),
        ),
    ),
    (
        DiscoveryState.IGNORED,
        Command.MONITOR,
        DiscoveryState.MONITORED,
        DiscoveryAction.SINGLE_UPDATE,
        Outcome(
            computed=True,
            in_autochecks=True,
            params=OLD_PARAMS,
            labels=OLD_LABELS,
            remove_disabled=frozenset({DESCRIPTION}),
            need_sync=True,
            permissions=("wato.service_discovery_to_monitored",),
        ),
    ),
    # `changed + monitor` with `adopt={parameters, labels}` -- the realisation
    # `SINGLE_UPDATE_SERVICE_PROPERTIES` provides. The `adopt=∅` realisation (`SINGLE_UPDATE`,
    # `BULK_UPDATE`) is a *no-op*, not a wrong write (§11.1, A3-F1); it is quarantined as T1b.8
    # because today it is executed as a change.
    (
        DiscoveryState.CHANGED,
        Command.MONITOR,
        DiscoveryState.MONITORED,
        DiscoveryAction.SINGLE_UPDATE_SERVICE_PROPERTIES,
        Outcome(
            computed=True,
            in_autochecks=True,
            params=NEW_PARAMS,
            labels=NEW_LABELS,
            permissions=("wato.service_discovery_to_monitored",),
        ),
    ),
    # `ignored + drop` must drop the rule. Correct via the `new` label only; the `removed` label
    # leaves the rule in place and is quarantined as T1b.6.
    (
        DiscoveryState.IGNORED,
        Command.DROP,
        DiscoveryState.UNDECIDED,
        DiscoveryAction.SINGLE_UPDATE,
        Outcome(
            computed=True,
            in_autochecks=False,
            remove_disabled=frozenset({DESCRIPTION}),
            need_sync=True,
            permissions=("wato.service_discovery_to_undecided",),
        ),
    ),
    # `vanished + drop` is the only operation a vanished row admits at all (§11.2a rule 4).
    # Correct via the `removed` label only; the `new` label keeps the entry (T1b.5).
    (
        DiscoveryState.VANISHED,
        Command.DROP,
        DiscoveryState.REMOVED,
        DiscoveryAction.SINGLE_UPDATE,
        Outcome(
            computed=True,
            in_autochecks=False,
            permissions=("wato.service_discovery_to_removed",),
        ),
    ),
)


@pytest.mark.parametrize(
    "source, command, target, action, expected",
    _MEANINGFUL_CELLS,
    ids=[f"{source}+{command}({target})" for source, command, target, _a, _e in _MEANINGFUL_CELLS],
)
def test_meaningful_cell_outcome(
    source: str,
    command: Command,
    target: str,
    action: DiscoveryAction,
    expected: Outcome,
) -> None:
    """§11.2: what each meaningful (state, command) pair writes, and what it demands.

    The permission is part of the outcome on purpose (T1a.3): a cell that stops demanding one is
    an authorization regression, and one that starts demanding a different one has changed
    meaning.
    """
    assert target in COMMAND_TARGETS[command]
    assert run_cell(source, target, action=action) == expected


# --------------------------------------------------------------------------------------------
# T1a.2 -- the three no-op cells
# --------------------------------------------------------------------------------------------

_NO_OP_CELLS: Sequence[tuple[str, Command, str]] = (
    (DiscoveryState.UNDECIDED, Command.DROP, DiscoveryState.UNDECIDED),
    (DiscoveryState.MONITORED, Command.MONITOR, DiscoveryState.MONITORED),
    (DiscoveryState.IGNORED, Command.DISABLE, DiscoveryState.IGNORED),
)


@pytest.mark.parametrize(
    "source, command, target",
    _NO_OP_CELLS,
    ids=[f"{source}+{command}" for source, command, _t in _NO_OP_CELLS],
)
def test_no_op_cells_yield_no_transition(source: str, command: Command, target: str) -> None:
    """§11.2: asking for the state a row is already in must do nothing at all.

    No transition, therefore no autochecks write, no rule change and no permission demanded.
    This is the idempotency the REST `PUT` contract needs.
    """
    assert target in COMMAND_TARGETS[command]
    assert run_cell(source, target) == NO_TRANSITION


# --------------------------------------------------------------------------------------------
# T1a.4 -- the source states §2.1 claims are unreachable
#
# Only `removed` is testable here: it is unreachable because the check engine's `Transition`
# vocabulary does not contain it, which is a static, cross-boundary fact. `clustered_ignored` is
# unreachable for a different reason -- no *classifier* emits it, which is a property of
# `_node_service_source` and is pinned where that function lives, in
# `packages/cmk-check-engine/tests/cmk/checkengine/discovery/test__autodiscovery.py`. Its
# behaviour as a `table_target` is characterization of a defect and lives in the quarantine tier.
# --------------------------------------------------------------------------------------------


def test_removed_is_not_a_source_state() -> None:
    """`removed` is a command, not an observation: no classifier can produce it as a row state.

    §2.1. It is spelled as a `DiscoveryState` member anyway, which is what makes the 15-value
    enum a mixture of one verb and fourteen nouns (§10.12).
    """
    producible = {arg for literal in get_args(Transition) for arg in get_args(literal)}
    assert DiscoveryState.REMOVED not in producible
    assert DiscoveryState.MONITORED in producible, "sanity: row states are spelled the same here"


# --------------------------------------------------------------------------------------------
# T1a.6 -- value adoption per action (§5, A3-F1)
# --------------------------------------------------------------------------------------------

_ADOPTING_ACTIONS: Sequence[tuple[DiscoveryAction, Mapping[str, object], Mapping[str, str]]] = (
    (DiscoveryAction.SINGLE_UPDATE, OLD_PARAMS, OLD_LABELS),
    (DiscoveryAction.BULK_UPDATE, OLD_PARAMS, OLD_LABELS),
    (DiscoveryAction.UPDATE_SERVICES, OLD_PARAMS, OLD_LABELS),
    (DiscoveryAction.UPDATE_SERVICE_LABELS, OLD_PARAMS, NEW_LABELS),
    (DiscoveryAction.UPDATE_DISCOVERY_PARAMETERS, NEW_PARAMS, OLD_LABELS),
    (DiscoveryAction.SINGLE_UPDATE_SERVICE_PROPERTIES, NEW_PARAMS, NEW_LABELS),
    (DiscoveryAction.FIX_ALL, NEW_PARAMS, NEW_LABELS),
)


@pytest.mark.parametrize(
    "action, expected_params, expected_labels",
    _ADOPTING_ACTIONS,
    ids=[str(action) for action, _p, _l in _ADOPTING_ACTIONS],
)
def test_value_adoption_matrix(
    action: DiscoveryAction,
    expected_params: Mapping[str, object],
    expected_labels: Mapping[str, str],
) -> None:
    """§5: which action adopts which facet of a `changed` service.

    Parameters and labels are adopted independently, so the four combinations are all reachable
    and all intended -- `FIX_ALL` takes both, the two `UPDATE_*` actions take one each, and the
    per-service actions take neither. (Whether plain `monitor` *should* adopt is the divergence
    quarantined as T1b.8; that it currently does not is what this pins.)
    """
    entry = make_entry(
        DiscoveryState.CHANGED,
        old_params=OLD_PARAMS,
        new_params=NEW_PARAMS,
        old_labels=OLD_LABELS,
        new_labels=NEW_LABELS,
    )
    transition, _permissions = compute(
        action=action,
        update_target=None if action is DiscoveryAction.FIX_ALL else DiscoveryState.MONITORED,
        update_source=DiscoveryState.CHANGED,
        selected_services=EVERYTHING,
        check_table=[entry],
    )
    assert transition is not None
    assert transition.new_autochecks.target_services == {
        DESCRIPTION: autocheck(expected_params, expected_labels)
    }


# --------------------------------------------------------------------------------------------
# T1a.7 -- the disabled-rule arithmetic of §4.2
# --------------------------------------------------------------------------------------------


def test_already_disabled_service_is_cancelled_out_of_the_rule_delta() -> None:
    """§4.2: `add_disabled_rule - remove_disabled_rule - (saved_services - selected_services)`.

    An already-disabled service that stays disabled must not produce a rule write. Omitting the
    cancellation would push every disabled service of the host into `add_disabled_rule` on each
    save, which costs one rule-match automation per service (CMK-26792).

    This is `FIX_ALL`, which passes `selected_services=()` and therefore gets the subtraction
    right. The other two accept-everything paths pass `EVERYTHING` and do not -- quarantined as
    T1b.12.
    """
    transition, _permissions = compute(
        action=DiscoveryAction.FIX_ALL,
        update_target=None,
        selected_services=(),
        check_table=disabled_plus_unrelated_change(),
    )
    assert transition is not None
    assert transition.add_disabled_rule == set()
    # `need_sync` is computed from the *pre*-subtraction sets, so it stays True for an empty rule
    # delta -- and sets `force_sync=True` on the pending change while the rule editor no-ops.
    assert transition.need_sync is True


def test_no_disabled_rule_is_written_for_a_service_disabled_by_a_disabled_checks_rule() -> None:
    """§4.2, caveat 1 — werk 6708: the guard protects the other plugin's service.

    Accepting everything must not write an `ignored_services` rule for a service that a *Disabled
    checks* rule disabled, because that rule matches on description and would take the
    identically-described sibling with it.
    """
    transition, _permissions = compute(
        action=DiscoveryAction.FIX_ALL,
        update_target=None,
        selected_services=(),
        check_table=two_plugins_one_description(),
    )
    assert transition is not None
    assert transition.add_disabled_rule == set()
    # Autochecks are keyed by *description*, so only one of the two can occupy the slot: the
    # accepted one, with the values `FIX_ALL` adopts.
    assert transition.new_autochecks.target_services == {
        SHARED_DESCRIPTION: autocheck(NEW_PARAMS, NEW_LABELS, plugin=TCP_PLUGIN)
    }


def test_explicitly_selected_service_is_disabled_despite_the_shared_description() -> None:
    """§4.2, caveat 2 — werk 19062: *"the service selected by the user gets excluded"*.

    Werk 6708's guard went too far: it also swallowed rules the user had explicitly asked for, so
    services could not be disabled from the discovery page at all. The selection is what
    distinguishes this case from the previous one -- the user asked for the TCP plugin's service,
    so its description is in `selected_services`, the subtrahend is empty, and the rule is written.
    """
    transition, _permissions = compute(
        action=DiscoveryAction.SINGLE_UPDATE,
        update_target=DiscoveryState.IGNORED,
        selected_services=((TCP_PLUGIN, None),),
        check_table=two_plugins_one_description(),
    )
    assert transition is not None
    assert transition.add_disabled_rule == {SHARED_DESCRIPTION}
    assert transition.need_sync is True
    # Neither row is written: the §4 invariant (a disabled service is never in the autochecks
    # file) holds on this path, unlike the `unchanged + disable` path quarantined as T1b.1.
    assert transition.new_autochecks.target_services == {}


# --------------------------------------------------------------------------------------------
# T1a.8 -- the shape of `old_autochecks` (§4.2)
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source, in_old",
    [
        (DiscoveryState.MONITORED, True),
        (DiscoveryState.CHANGED, True),
        (DiscoveryState.IGNORED, True),
        (DiscoveryState.VANISHED, True),
        (DiscoveryState.UNDECIDED, False),
    ],
)
def test_old_autochecks_audit_shape(source: str, in_old: bool) -> None:
    """§4.2: `old_autochecks` is the audit-log "before" picture, built with the *old* values.

    It holds the four sources that were already in the autochecks file plus the disabled one --
    an `ignored` service appears in the "before" side of the diff even though it is not in the
    file -- and never the undecided source, which had no "before" to show.

    The service under test is left alone (it is not selected, so its target is its own source);
    a second, unrelated service is what makes the transition happen at all.
    """
    trigger = make_entry(DiscoveryState.UNDECIDED, item="trigger", description="Trigger")
    transition, _permissions = compute(
        action=DiscoveryAction.SINGLE_UPDATE,
        update_target=DiscoveryState.MONITORED,
        selected_services=((PLUGIN, "trigger"),),
        check_table=[make_entry(source), trigger],
    )
    assert transition is not None
    assert (DESCRIPTION in transition.old_autochecks.target_services) is in_old
    if in_old:
        assert transition.old_autochecks.target_services[DESCRIPTION] == autocheck(
            OLD_PARAMS, OLD_LABELS
        )


# --------------------------------------------------------------------------------------------
# T1a.9 -- cluster node tables (`_get_effective_check_tables`)
# --------------------------------------------------------------------------------------------

NODE1 = HostName("node1")
NODE2 = HostName("node2")
CLUSTER = HostName("mycluster")


def test_stale_node_entry_is_dropped_when_the_service_moved_to_another_node() -> None:
    """Failover: the service ran on node1, is now discovered on node2, node1's entry is stale.

    `_should_be_kept` drops node1's entry because `found_on_nodes` is non-empty and does not
    contain node1. **The trigger is this node's absence from that list, not the other node's
    presence in it** -- when the service runs on both, both entries are kept (the companion test
    below). The code's stated reason for dropping is parameter precedence: node1's older
    discovered parameters must not overwrite node2's newer ones on the cluster.
    """
    transition, _permissions = compute(
        action=DiscoveryAction.FIX_ALL,
        update_target=None,
        selected_services=(),
        check_table=[
            make_entry(DiscoveryState.CHANGED, new_params=NEW_PARAMS, found_on_nodes=[NODE2])
        ],
        nodes_check_table={
            NODE1: [make_entry(DiscoveryState.CLUSTERED_VANISHED)],
            NODE2: [make_entry(DiscoveryState.CLUSTERED_OLD, found_on_nodes=[NODE2])],
        },
        target_host_name=CLUSTER,
    )
    assert transition is not None
    assert transition.new_autochecks.nodes_services[NODE1] == {}
    assert DESCRIPTION in transition.new_autochecks.nodes_services[NODE2]


def test_node_entries_are_kept_when_the_service_is_found_on_both_nodes() -> None:
    """Presence on another node is not by itself a reason to drop anything.

    A service genuinely running on both nodes is found on both, so `found_on_nodes` lists both and
    every node keeps its entry. This is the case that separates "dropped because it is elsewhere"
    from "dropped because it is no longer here": an implementation that evicted on the former would
    pass the failover test above and fail this one.
    """
    transition, _permissions = compute(
        action=DiscoveryAction.FIX_ALL,
        update_target=None,
        selected_services=(),
        check_table=[
            make_entry(DiscoveryState.CHANGED, new_params=NEW_PARAMS, found_on_nodes=[NODE1, NODE2])
        ],
        nodes_check_table={
            NODE1: [make_entry(DiscoveryState.CLUSTERED_OLD, found_on_nodes=[NODE1, NODE2])],
            NODE2: [make_entry(DiscoveryState.CLUSTERED_OLD, found_on_nodes=[NODE1, NODE2])],
        },
        target_host_name=CLUSTER,
    )
    assert transition is not None
    assert DESCRIPTION in transition.new_autochecks.nodes_services[NODE1]
    assert DESCRIPTION in transition.new_autochecks.nodes_services[NODE2]


def test_node_entry_is_kept_when_the_service_is_found_on_no_node() -> None:
    """The service vanished everywhere: in node1's autochecks, found by this scan on no node.

    That is the only classification consistent with `found_on_nodes=[]` -- a service the scan
    finds nowhere is `vanished` on the cluster and `clustered_vanished` on the node, not
    `clustered_old`. `_should_be_kept` returns True for the empty list so that the node's entry
    survives the rebuild; otherwise the user would watch vanished services disappear on their own
    instead of being offered for removal on the cluster page.
    """
    transition, _permissions = compute(
        action=DiscoveryAction.FIX_ALL,
        update_target=None,
        selected_services=(),
        check_table=[make_entry(DiscoveryState.VANISHED, found_on_nodes=[])],
        nodes_check_table={NODE1: [make_entry(DiscoveryState.CLUSTERED_VANISHED)]},
        target_host_name=CLUSTER,
    )
    assert transition is not None
    assert DESCRIPTION in transition.new_autochecks.nodes_services[NODE1]


def test_node_entry_unknown_on_the_cluster_is_dropped() -> None:
    """A node entry with no counterpart in the cluster table is not clustered at all.

    `_should_be_kept` reaches this through the `KeyError` branch -- the lookup is by
    `(check_plugin_name, item)`, so `found_on_nodes` is never consulted. The node keeps its own
    clustered entry and loses only the one the cluster does not know about.
    """
    transition, _permissions = compute(
        action=DiscoveryAction.FIX_ALL,
        update_target=None,
        selected_services=(),
        check_table=[
            make_entry(DiscoveryState.CHANGED, new_params=NEW_PARAMS, found_on_nodes=[NODE1])
        ],
        nodes_check_table={
            NODE1: [
                make_entry(DiscoveryState.CLUSTERED_OLD, found_on_nodes=[NODE1]),
                make_entry(DiscoveryState.CLUSTERED_OLD, item="other", description="Other"),
            ]
        },
        target_host_name=CLUSTER,
    )
    assert transition is not None
    assert set(transition.new_autochecks.nodes_services[NODE1]) == {DESCRIPTION}


# --------------------------------------------------------------------------------------------
# T1a.5 -- totality: no enum value may exist without a verdict
# --------------------------------------------------------------------------------------------

_SOURCES_WITH_A_VERDICT = {
    # the five row states of §11.2
    DiscoveryState.UNDECIDED,
    DiscoveryState.MONITORED,
    DiscoveryState.CHANGED,
    DiscoveryState.IGNORED,
    DiscoveryState.VANISHED,
}
_SOURCES_NOT_ELIGIBLE = {
    # §11.2a rule 2: not discovery-managed, no autochecks entry to write
    DiscoveryState.MANUAL,
    DiscoveryState.ACTIVE,
    DiscoveryState.CUSTOM,
    DiscoveryState.ACTIVE_IGNORED,
    DiscoveryState.CUSTOM_IGNORED,
    # §11.2a rule 3: owned by the cluster, nothing to decide on the node
    DiscoveryState.CLUSTERED_NEW,
    DiscoveryState.CLUSTERED_OLD,
    DiscoveryState.CLUSTERED_VANISHED,
}
_SOURCES_UNREACHABLE = {
    DiscoveryState.REMOVED,  # a command, never an observation
    DiscoveryState.CLUSTERED_IGNORED,  # no producer since 692c918bf86 (§10.13)
}


def test_every_discovery_state_has_a_verdict() -> None:
    """§7 T1a.5: adding a `DiscoveryState` without deciding what it means must fail here.

    The three sets are the ones §11 recognises: rows that admit commands, rows that must be
    rejected outright, and values that no classifier produces.
    """
    declared = {value for name, value in vars(DiscoveryState).items() if name.isupper()}
    assert declared == _SOURCES_WITH_A_VERDICT | _SOURCES_NOT_ELIGIBLE | _SOURCES_UNREACHABLE


#: The actions this module's transition machinery serves. The partition is by *code path*, not by
#: effect: `TABULA_RASA` changes services too, but through `local_discovery` (§A3-F2 below), so it
#: cannot appear in the transition-computing set no matter how much it writes.
_ACTIONS_COMPUTING_A_TRANSITION = {
    DiscoveryAction.FIX_ALL,
    DiscoveryAction.SINGLE_UPDATE,
    DiscoveryAction.BULK_UPDATE,
    DiscoveryAction.UPDATE_SERVICES,
    DiscoveryAction.UPDATE_SERVICE_LABELS,
    DiscoveryAction.UPDATE_DISCOVERY_PARAMETERS,
    DiscoveryAction.SINGLE_UPDATE_SERVICE_PROPERTIES,
}
_ACTIONS_NOT_COMPUTING_A_TRANSITION = {
    # Read-only: `NONE` renders the cached preview, `STOP` cancels the job, `REFRESH` re-fetches
    # from the host and recomputes the preview without writing anything (its pre-gate is plain
    # `wato.services`, `services.py:802`, and it adds no pending change).
    DiscoveryAction.NONE,
    DiscoveryAction.STOP,
    DiscoveryAction.REFRESH,
    # Writes host labels, not services.
    DiscoveryAction.UPDATE_HOST_LABELS,
    # **Writes services** -- `_perform_automatic_refresh` calls `local_discovery` with all five
    # `DiscoverySettings` flags set, so it adds, removes and re-parameterises services and adds a
    # `refresh-autochecks` pending change (`services.py:1196`). It is here because that is a
    # *second write path* that never reaches `compute_discovery_transition`, which is A3-F2 and the
    # reason §6.3 proposes decomposing it into the primitives the transition already has.
    DiscoveryAction.TABULA_RASA,
}


def test_every_discovery_action_is_on_one_side_of_the_transition_boundary() -> None:
    """§2.2: 7 of the 12 actions reach `compute_discovery_transition`; the other 5 do not.

    Adding an action without deciding which side it is on must fail here. Note the boundary is
    "does it compute a transition", which is **not** the same as "does it change services": see
    `TABULA_RASA` above.
    """
    assert set(DiscoveryAction) == (
        _ACTIONS_COMPUTING_A_TRANSITION | _ACTIONS_NOT_COMPUTING_A_TRANSITION
    )


@pytest.mark.parametrize("action", sorted(_ACTIONS_NOT_COMPUTING_A_TRANSITION))
def test_actions_outside_the_transition_machinery_compute_no_transition(
    action: DiscoveryAction,
) -> None:
    """Whatever else these five do, they must not produce a `DiscoveryTransition` (§6)."""
    transition, permissions = compute(
        action=action,
        update_target=DiscoveryState.MONITORED,
        check_table=[make_entry(source) for source in sorted(_SOURCES_WITH_A_VERDICT)],
    )
    assert transition is None
    assert permissions == ()


# --------------------------------------------------------------------------------------------
# T1a.10 -- the per-action pre-gate (§5.1)
# --------------------------------------------------------------------------------------------

_TO_MONITORED = "wato.service_discovery_to_monitored"
_TO_UNDECIDED = "wato.service_discovery_to_undecided"
_TO_REMOVED = "wato.service_discovery_to_removed"
_TO_IGNORED = "wato.service_discovery_to_ignored"
_SERVICES = "wato.services"

#: action -> the permissions `has_discovery_action_specific_permissions` demands for it (§5.1).
_PRE_GATE: Mapping[DiscoveryAction, frozenset[str]] = {
    DiscoveryAction.NONE: frozenset({_SERVICES}),
    DiscoveryAction.STOP: frozenset({_SERVICES}),
    DiscoveryAction.REFRESH: frozenset({_SERVICES}),
    DiscoveryAction.UPDATE_HOST_LABELS: frozenset({_SERVICES}),
    DiscoveryAction.UPDATE_SERVICE_LABELS: frozenset({_SERVICES}),
    DiscoveryAction.UPDATE_DISCOVERY_PARAMETERS: frozenset({_SERVICES}),
    DiscoveryAction.UPDATE_SERVICES: frozenset({_SERVICES}),
    DiscoveryAction.FIX_ALL: frozenset({_TO_MONITORED, _TO_REMOVED}),
    DiscoveryAction.BULK_UPDATE: frozenset({_TO_MONITORED, _TO_REMOVED}),
    DiscoveryAction.TABULA_RASA: frozenset({_TO_UNDECIDED, _TO_MONITORED, _TO_REMOVED}),
}


class _FakeUser:
    def __init__(self, granted: Container[str]) -> None:
        self._granted = granted

    def may(self, permission: str) -> bool:
        return permission in self._granted


@pytest.fixture(name="grant")
def fixture_grant(monkeypatch: pytest.MonkeyPatch) -> Callable[[Container[str]], None]:
    """Replace the request-local user with one that grants exactly the given permissions."""

    def _grant(granted: Container[str]) -> None:
        monkeypatch.setattr(services_module, "user", _FakeUser(granted))
        monkeypatch.setattr(services_module, "may_edit_ruleset", lambda name: name in granted)

    return _grant


@pytest.mark.parametrize("action, demanded", sorted(_PRE_GATE.items()))
def test_action_pre_gate_demands_exactly_its_permission_set(
    action: DiscoveryAction,
    demanded: frozenset[str],
    grant: Callable[[Container[str]], None],
) -> None:
    """§5.1: granting the full set passes, and dropping any one member fails.

    "Dropping any one member fails" is the part worth testing: an `all(...)` that silently loses a
    term still passes a test that only ever grants everything.
    """
    grant(demanded)
    assert has_discovery_action_specific_permissions(action, None) is True

    for withheld in demanded:
        grant(demanded - {withheld})
        assert has_discovery_action_specific_permissions(action, None) is False, (
            f"{action} still passed without {withheld}"
        )


@pytest.mark.parametrize(
    "update_target, demanded",
    [
        (UpdateType.MONITORED, frozenset({_TO_MONITORED})),
        (UpdateType.UNDECIDED, frozenset({_TO_UNDECIDED})),
        (UpdateType.REMOVED, frozenset({_TO_REMOVED})),
        # The only target that additionally needs the ruleset permission: disabling a service
        # writes an `ignored_services` rule.
        (UpdateType.IGNORED, frozenset({_TO_IGNORED, "ignored_services"})),
    ],
)
@pytest.mark.parametrize(
    "action", [DiscoveryAction.SINGLE_UPDATE, DiscoveryAction.SINGLE_UPDATE_SERVICE_PROPERTIES]
)
def test_single_update_pre_gate_delegates_to_the_target(
    action: DiscoveryAction,
    update_target: UpdateType,
    demanded: frozenset[str],
    grant: Callable[[Container[str]], None],
) -> None:
    """§5.1: the two single-update actions gate on the *target*, not on the action."""
    grant(demanded)
    assert has_discovery_action_specific_permissions(action, update_target) is True

    for withheld in demanded:
        grant(demanded - {withheld})
        assert has_discovery_action_specific_permissions(action, update_target) is False


@pytest.mark.parametrize(
    "action", [DiscoveryAction.SINGLE_UPDATE, DiscoveryAction.SINGLE_UPDATE_SERVICE_PROPERTIES]
)
def test_single_update_without_a_target_is_refused(
    action: DiscoveryAction, grant: Callable[[Container[str]], None]
) -> None:
    """A single update with no target cannot be authorized -- there is nothing to authorize."""
    grant({_TO_MONITORED, _TO_UNDECIDED, _TO_REMOVED, _TO_IGNORED, _SERVICES, "ignored_services"})
    assert has_discovery_action_specific_permissions(action, None) is False


def test_pre_gate_is_total_over_the_action_enum() -> None:
    """`has_discovery_action_specific_permissions` ends in `assert_never`, so every action is
    covered -- but only the enum knows that. This pins the table above against the enum."""
    assert set(_PRE_GATE) | {
        DiscoveryAction.SINGLE_UPDATE,
        DiscoveryAction.SINGLE_UPDATE_SERVICE_PROPERTIES,
    } == set(DiscoveryAction)


def test_command_targets_cover_the_permission_table() -> None:
    """Every target a command can be spelled as demands exactly one permission (§5.1)."""
    spellings = {target for targets in COMMAND_TARGETS.values() for target in targets}
    assert spellings == set(PERMISSION_BY_TARGET)


# --------------------------------------------------------------------------------------------
# T1a.11 -- the selector: which rows an action reaches at all (§5)
#
# Everything above says what happens to a row a command reaches. This says which rows it reaches.
# `_get_table_target` applies three filters before any handler runs, and each of them is
# invisible to a table whose every row it admits -- so every case below carries a row the action
# must leave alone.
# --------------------------------------------------------------------------------------------

#: A second row, so that "the action ran at all" and "this row was reached" stay distinguishable.
OTHER_ITEM = "other"
OTHER_DESCRIPTION = "Other service"

_DROPPED = Outcome(computed=True, in_autochecks=False, permissions=(_TO_UNDECIDED,))

_BULK_SOURCE_FILTER: Sequence[tuple[str, str, Outcome]] = (
    # row state, the `update_source` the caller filters on, outcome
    #
    # `changed` is a subset of `monitored`: the row is in the autochecks file, it merely holds
    # different values than the last scan found. A bulk action on monitored services reaches it.
    (DiscoveryState.CHANGED, DiscoveryState.MONITORED, _DROPPED),
    # The plain equality that carve-out is an exception to.
    (DiscoveryState.MONITORED, DiscoveryState.MONITORED, _DROPPED),
    # The subset relation is one-directional: a bulk action on *changed* services must not reach
    # an unchanged one. Nothing separates a symmetric implementation from a correct one without
    # this row.
    (DiscoveryState.MONITORED, DiscoveryState.CHANGED, NO_TRANSITION),
    # An unrelated row state is untouched, which is the filter's ordinary job.
    (DiscoveryState.VANISHED, DiscoveryState.MONITORED, NO_TRANSITION),
)


@pytest.mark.parametrize(
    "source, update_source, expected",
    _BULK_SOURCE_FILTER,
    ids=[f"{source}-under-{filtered_on}" for source, filtered_on, _e in _BULK_SOURCE_FILTER],
)
def test_bulk_update_reaches_exactly_the_rows_of_its_update_source(
    source: str, update_source: str, expected: Outcome
) -> None:
    """`BULK_UPDATE` is the one action that selects rows by state rather than by selection.

    The command here is `drop`, so a row the filter admits loses its autochecks entry while a row
    it rejects produces no transition at all -- the two outcomes are as far apart as they get,
    which is what makes "was this row reached" observable rather than inferred.
    """
    assert (
        run_cell(
            source,
            DiscoveryState.UNDECIDED,
            action=DiscoveryAction.BULK_UPDATE,
            update_source=update_source,
        )
        == expected
    )


#: The four actions that consult `selected_services`, with the `update_source` / `update_target`
#: their real call sites transmit (`wato/pages/services.py:647`, `execute_service_discovery.py`).
_SELECTION_HONOURING_ACTIONS: Sequence[tuple[DiscoveryAction, str | None, str | None]] = (
    (DiscoveryAction.UPDATE_SERVICES, None, None),
    (DiscoveryAction.BULK_UPDATE, DiscoveryState.UNDECIDED, DiscoveryState.MONITORED),
    (DiscoveryAction.SINGLE_UPDATE, None, DiscoveryState.MONITORED),
    (DiscoveryAction.SINGLE_UPDATE_SERVICE_PROPERTIES, None, DiscoveryState.MONITORED),
)


@pytest.mark.parametrize(
    "action, update_source, update_target",
    _SELECTION_HONOURING_ACTIONS,
    ids=[str(action) for action, _s, _t in _SELECTION_HONOURING_ACTIONS],
)
def test_an_unselected_row_is_left_alone(
    action: DiscoveryAction, update_source: str | None, update_target: str | None
) -> None:
    """§5: an action that consults the selection must reach nothing outside it.

    Both rows are undecided, so both are eligible and the selection is the only thing separating
    them. Accepting the unselected one would put a service into monitoring that nobody asked for,
    on a page whose entire interface is the checkboxes.

    `FIX_ALL` and the two `UPDATE_*` value actions are deliberately absent: they are whole-table
    actions that never consult the selection, which is intended (A1-F2 — the host-wide scope is
    the design, the missing `update_source` filter is the defect, §10.5).
    """
    transition, _permissions = compute(
        action=action,
        update_source=update_source,
        update_target=update_target,
        selected_services=((PLUGIN, None),),
        check_table=[
            make_entry(DiscoveryState.UNDECIDED),
            make_entry(DiscoveryState.UNDECIDED, item=OTHER_ITEM, description=OTHER_DESCRIPTION),
        ],
    )
    assert transition is not None
    assert set(transition.new_autochecks.target_services) == {DESCRIPTION}


@pytest.mark.parametrize(
    "action, expected_params, expected_labels",
    [
        (DiscoveryAction.UPDATE_SERVICE_LABELS, OLD_PARAMS, NEW_LABELS),
        (DiscoveryAction.UPDATE_DISCOVERY_PARAMETERS, NEW_PARAMS, OLD_LABELS),
    ],
    ids=["update_service_labels", "update_discovery_parameters"],
)
def test_a_whole_table_value_update_leaves_a_disabled_service_disabled(
    action: DiscoveryAction,
    expected_params: Mapping[str, object],
    expected_labels: Mapping[str, str],
) -> None:
    """Werk 17711 / CMK-22272: *"used to move disabled services to monitored services … no longer"*.

    The `IGNORED` carve-out in both branches is that werk's entire diff, and it is the only thing
    standing between these two actions and a re-enabled service: they retarget **every** row on
    the host to `update_target` (A1-F2), so without the carve-out "Update service labels" silently
    accepts every disabled service on the host back into monitoring.

    The changed row is what the action is *for*; its adopted values are asserted alongside so that
    "the disabled row was skipped" cannot be satisfied by the action not running.
    """
    transition, _permissions = compute(
        action=action,
        update_source=DiscoveryState.CHANGED,
        update_target=DiscoveryState.MONITORED,
        selected_services=(),
        check_table=[
            make_entry(DiscoveryState.IGNORED),
            make_entry(DiscoveryState.CHANGED, item=OTHER_ITEM, description=OTHER_DESCRIPTION),
        ],
    )
    assert transition is not None
    # The disabled service is neither written back into the autochecks file ...
    assert set(transition.new_autochecks.target_services) == {OTHER_DESCRIPTION}
    # ... nor stripped of the rule that disables it.
    assert transition.remove_disabled_rule == set()
    assert transition.new_autochecks.target_services[OTHER_DESCRIPTION] == autocheck(
        expected_params, expected_labels, item=OTHER_ITEM
    )
