#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tier 1b -- quarantine for transition cells whose behaviour is known to be wrong.

Specified in ``packages/cmk-check-engine/docs/SERVICE_DISCOVERY_BEHAVIOUR_MATRIX.md`` §7.

Every row of ``_DIVERGENCES`` below yields **two** tests from one data row:

* ``test_intended_outcome`` asserts what §11.2 says the cell must produce. It is marked
  ``xfail(strict=True)``, so it is a tripwire: the moment the behaviour is fixed, the test XPASSes
  and the suite goes red until the row is deleted.
* ``test_current_outcome`` asserts what the code does today. It is the guardrail that holds until
  the ticket lands, and it is what stops the fix from happening by accident.

Neither test asserts that today's behaviour is *correct*: the pair, read together, says "this is
what happens, this is what should happen, here is the ticket". When a ticket lands, delete its row
-- both tests go with it.

``strict=True`` is spelled out on purpose. ``pyproject.toml`` sets ``xfail_strict`` in a bare
``[pytest]`` table, which pytest does not read from ``pyproject.toml`` (it reads
``[tool.pytest.ini_options]``), so the repository default is non-strict and an XPASS would pass
silently -- defeating the entire mechanism.
"""

import dataclasses
from collections.abc import Callable, Sequence

import pytest

from cmk.checkengine.discovery import CheckPreviewEntry
from cmk.gui.openapi.api_endpoints.service_discovery._utils import SERVICE_DISCOVERY_PHASES
from cmk.gui.watolib.services import DiscoveryAction, DiscoveryState, DiscoveryTransition
from cmk.utils.everythingtype import EVERYTHING
from tests.unit.cmk.gui.watolib.discovery_matrix import (
    Command,
    COMMAND_TARGETS,
    compute,
    DESCRIPTION,
    disabled_plus_unrelated_change,
    NO_TRANSITION,
    OLD_LABELS,
    OLD_PARAMS,
    Outcome,
    run_cell,
    SHARED_DESCRIPTION,
    TCP_PLUGIN,
    two_plugins_one_description,
)

REJECTED = None
"""§11.2a: the cell must not be handled at all -- the request is malformed and is refused.

Expressed as `None` because a rejection has no outcome. The `xfail` test asserts that the call
raises; today none of these raise, which is the divergence.
"""


@dataclasses.dataclass(frozen=True)
class Divergence:
    """One cell where today's behaviour contradicts §11.2."""

    id: str
    source: str
    command: Command
    target: str
    intended: Outcome | None
    current: Outcome
    ticket: str
    action: DiscoveryAction = DiscoveryAction.SINGLE_UPDATE


_DIVERGENCES: Sequence[Divergence] = (
    Divergence(
        # T1b.1
        id="unchanged+disable",
        source=DiscoveryState.MONITORED,
        command=Command.DISABLE,
        target=DiscoveryState.IGNORED,
        intended=Outcome(
            computed=True,
            in_autochecks=False,
            add_disabled=frozenset({DESCRIPTION}),
            need_sync=True,
            permissions=("wato.service_discovery_to_ignored",),
        ),
        current=Outcome(
            computed=True,
            in_autochecks=True,
            params=OLD_PARAMS,
            labels=OLD_LABELS,
            add_disabled=frozenset({DESCRIPTION}),
            need_sync=True,
            permissions=("wato.service_discovery_to_ignored",),
        ),
        ticket="CMK-38587 (§10.1) -- werk 19800 fixed the `ignored` and `clustered_*` sources "
        "only, so a monitored service disabled from the GUI still ends up in the autochecks file, "
        "which is the residue werk 19801 exists to remove",
    ),
    Divergence(
        # T1b.2
        id="changed+disable",
        source=DiscoveryState.CHANGED,
        command=Command.DISABLE,
        target=DiscoveryState.IGNORED,
        intended=Outcome(
            computed=True,
            in_autochecks=False,
            add_disabled=frozenset({DESCRIPTION}),
            need_sync=True,
            permissions=("wato.service_discovery_to_ignored",),
        ),
        current=Outcome(
            computed=True,
            in_autochecks=True,
            params=OLD_PARAMS,
            labels=OLD_LABELS,
            add_disabled=frozenset({DESCRIPTION}),
            need_sync=True,
            permissions=("wato.service_discovery_to_ignored",),
        ),
        ticket="CMK-38587 (§10.1) -- same gap as `unchanged + disable`, reached through "
        "`_case_changed`",
    ),
    Divergence(
        # T1b.3
        id="vanished+disable",
        source=DiscoveryState.VANISHED,
        command=Command.DISABLE,
        target=DiscoveryState.IGNORED,
        intended=REJECTED,
        current=Outcome(
            computed=True,
            in_autochecks=True,
            params=OLD_PARAMS,
            labels=OLD_LABELS,
            add_disabled=frozenset({DESCRIPTION}),
            need_sync=True,
            permissions=("wato.service_discovery_to_ignored",),
        ),
        ticket="CMK-38592 (§10.16) -- a not-discovered service cannot become `ignored`: the "
        "classifier never produces that state for it, so the write creates an autochecks entry "
        "plus a matching rule, which is residue no discovery run can clean up",
    ),
    Divergence(
        # T1b.4
        id="vanished+monitor",
        source=DiscoveryState.VANISHED,
        command=Command.MONITOR,
        target=DiscoveryState.MONITORED,
        intended=REJECTED,
        current=Outcome(
            computed=True,
            in_autochecks=True,
            params=OLD_PARAMS,
            labels=OLD_LABELS,
            permissions=("wato.service_discovery_to_monitored",),
        ),
        ticket="CMK-38592 (§10.16) -- monitoring a service that is not there yields a stale check "
        "that re-vanishes on the next scan",
    ),
    Divergence(
        # T1b.5
        id="vanished+drop(new)",
        source=DiscoveryState.VANISHED,
        command=Command.DROP,
        target=DiscoveryState.UNDECIDED,
        intended=Outcome(
            computed=True,
            in_autochecks=False,
            permissions=("wato.service_discovery_to_undecided",),
        ),
        current=Outcome(
            computed=True,
            in_autochecks=True,
            params=OLD_PARAMS,
            labels=OLD_LABELS,
            permissions=("wato.service_discovery_to_undecided",),
        ),
        ticket="CMK-38592 (§10.16) -- `drop` is one command with two labels (§11.3), so both "
        "spellings must clean up; `_case_vanished`'s catch-all `else` keeps the service for every "
        "target except `removed`",
    ),
    Divergence(
        # T1b.6
        id="ignored+drop(removed)",
        source=DiscoveryState.IGNORED,
        command=Command.DROP,
        target=DiscoveryState.REMOVED,
        intended=Outcome(
            computed=True,
            in_autochecks=False,
            remove_disabled=frozenset({DESCRIPTION}),
            need_sync=True,
            permissions=("wato.service_discovery_to_removed",),
        ),
        current=Outcome(
            computed=True,
            in_autochecks=False,
            permissions=("wato.service_discovery_to_removed",),
        ),
        ticket="CMK-38592 (§11.3) -- the same command via the other label leaves the "
        "disabled-services rule in place, so the service reappears as `ignored` instead of `new`",
    ),
    Divergence(
        # T1b.8 (T1b.7 needs no transition and is asserted separately below)
        id="changed+monitor(adopt=none)",
        source=DiscoveryState.CHANGED,
        command=Command.MONITOR,
        target=DiscoveryState.MONITORED,
        # Not "adopts the new values": `SINGLE_UPDATE` is `monitor(adopt=∅)`, and for that the old
        # values are the *correct* ones to write (§11.1, A3-F1 -- adoption is a parameter of
        # `monitor`, not a command). Writing nothing at all is correct, because there is nothing
        # to change: the entry already holds those values.
        intended=NO_TRANSITION,
        current=Outcome(
            computed=True,
            in_autochecks=True,
            params=OLD_PARAMS,
            labels=OLD_LABELS,
            permissions=("wato.service_discovery_to_monitored",),
        ),
        ticket="CMK-38589 (A3-F1 residue, §10.8 family) -- `monitor(adopt=∅)` on a `changed` row "
        "is a no-op, but `apply_changes` compares `check_source != table_target`, i.e. the "
        "observation changedunchangedvalue-identical write, `to_monitored` demanded, pending "
        "change, host-wide autochecks rebuild",
    ),
)


def _run(divergence: Divergence) -> Outcome:
    # The same guard `test_meaningful_cell_outcome` puts on the conformance cells: `target` is a
    # *spelling* of `command` (§11.3), and a row whose two disagree describes a cell that does not
    # exist. Asserted here rather than in the tests, because both of them funnel through this.
    assert divergence.target in COMMAND_TARGETS[divergence.command], (
        f"{divergence.id}: {divergence.target!r} is not a spelling of {divergence.command}"
    )
    return run_cell(divergence.source, divergence.target, action=divergence.action)


@pytest.mark.parametrize(
    "divergence",
    [pytest.param(d, marks=pytest.mark.xfail(strict=True, reason=d.ticket)) for d in _DIVERGENCES],
    ids=[d.id for d in _DIVERGENCES],
)
def test_intended_outcome(divergence: Divergence) -> None:
    """§11.2: what this cell must produce. Expected to fail until the ticket lands.

    `strict=True`: when the fix lands this XPASSes and the suite goes red, which is the signal to
    delete the row from `_DIVERGENCES` -- and with it the paired characterization test below.
    """
    if divergence.intended is REJECTED:
        with pytest.raises(Exception):  # noqa: B017  # the rejection type is not decided yet
            _run(divergence)
    else:
        assert _run(divergence) == divergence.intended


@pytest.mark.parametrize("divergence", _DIVERGENCES, ids=[d.id for d in _DIVERGENCES])
def test_current_outcome(divergence: Divergence) -> None:
    """What this cell does today. Not an endorsement -- see the paired test above."""
    assert _run(divergence) == divergence.current


# --------------------------------------------------------------------------------------------
# T1b.7 -- `removed` on a service that was never in the autochecks file
# --------------------------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="CMK-38592 (§11.3) -- `removed` is the label `drop` takes on a *vanished* row. On an "
    "undecided row it is the wrong label and must be refused, rather than being accepted as a "
    "no-op that demands a permission",
)
def test_removed_on_an_undecided_service_is_rejected() -> None:
    with pytest.raises(Exception):  # noqa: B017  # the rejection type is not decided yet
        run_cell(DiscoveryState.UNDECIDED, DiscoveryState.REMOVED)


def test_removed_on_an_undecided_service_is_a_permission_demanding_no_op() -> None:
    """Today: nothing is written, but `wato.service_discovery_to_removed` is demanded anyway.

    The transition is computed (the target differs from the source, so `apply_changes` is set),
    which means the host's autochecks are rewritten for a change that does not exist.
    """
    assert run_cell(DiscoveryState.UNDECIDED, DiscoveryState.REMOVED) == Outcome(
        computed=True,
        in_autochecks=False,
        permissions=("wato.service_discovery_to_removed",),
    )


# --------------------------------------------------------------------------------------------
# T1b.9 / T1b.10 -- rows that admit no operation at all (§11.2a rules 2 and 3)
# --------------------------------------------------------------------------------------------

_NOT_ELIGIBLE_SOURCES = (
    DiscoveryState.MANUAL,
    DiscoveryState.ACTIVE,
    DiscoveryState.CUSTOM,
    DiscoveryState.ACTIVE_IGNORED,
    DiscoveryState.CUSTOM_IGNORED,
    DiscoveryState.CLUSTERED_NEW,
    DiscoveryState.CLUSTERED_OLD,
    DiscoveryState.CLUSTERED_VANISHED,
)


@pytest.mark.parametrize("source", _NOT_ELIGIBLE_SOURCES)
@pytest.mark.xfail(
    strict=True,
    reason="CMK-38589 (§10.8) / CMK-38593 (§10.17) -- a row whose origin is not `discovered`, or "
    "whose effective host is a cluster, admits no command at all: there is no autochecks entry the "
    "node may write",
)
def test_ineligible_row_rejects_every_command(source: str) -> None:
    for target in (DiscoveryState.MONITORED, DiscoveryState.IGNORED, DiscoveryState.UNDECIDED):
        with pytest.raises(Exception):  # noqa: B017  # the rejection type is not decided yet
            run_cell(source, target)


def test_clustered_row_disabled_from_the_node_drops_the_entry_without_a_rule() -> None:
    """§10.17: the one clustered cell that does real harm.

    Cluster services are gathered from the nodes' autochecks filtered by `effective_host`, so
    dropping the node's entry removes the service from the **cluster's** monitoring -- with no
    rule recording the decision and nothing on the cluster's page to explain it.
    """
    assert run_cell(DiscoveryState.CLUSTERED_OLD, DiscoveryState.IGNORED) == Outcome(
        computed=True,
        in_autochecks=False,
        permissions=("wato.service_discovery_to_ignored",),
    )


@pytest.mark.parametrize("source", _NOT_ELIGIBLE_SOURCES)
def test_ineligible_row_is_rewritten_instead_of_rejected(source: str) -> None:
    """Today: an ineligible row is handled rather than refused, and forces a host-wide rewrite.

    A `clustered_*` row is written back unchanged; a row whose origin is not `discovered` reaches
    no handler at all, so nothing is written -- harmless only because such a service has no
    autochecks entry to lose. Either way `apply_changes` is set, which produces a `set-autochecks`
    pending change and an automation round trip for a host where nothing changed (§10.8, the
    `FIX_ALL` noise pattern).
    """
    outcome = run_cell(source, DiscoveryState.MONITORED)
    assert outcome.computed is True
    assert outcome.in_autochecks is source.startswith("clustered_")
    assert outcome.add_disabled == frozenset()
    assert outcome.remove_disabled == frozenset()


# --------------------------------------------------------------------------------------------
# T1b.11 -- targets that are not commands at all (§10.3)
# --------------------------------------------------------------------------------------------

#: The four phases that name a command (§11.1). Spelled as REST phase keys because that is the
#: vocabulary §10.3 is about: `SERVICE_DISCOVERY_PHASES` is what the endpoint accepts, and its
#: values are what reach `update_target`.
_COMMAND_PHASES = frozenset({"monitored", "undecided", "ignored", "removed"})

#: Every other phase, as the target string the endpoint hands to `Discovery`. Derived rather than
#: listed, so that adding a phase without deciding what it means fails here.
#:
#: Two of them are **not** `DiscoveryState` values at all: `legacy` and `legacy_ignored` map to
#: bare strings, which is why this list has 13 entries where the `DiscoveryState` enum would give
#: 11. They are the sharpest instance of the defect -- a target no handler and no permission arm
#: has ever heard of -- so the wider vocabulary is the right one to count here.
_NON_COMMAND_TARGETS = tuple(
    sorted(
        target for phase, target in SERVICE_DISCOVERY_PHASES.items() if phase not in _COMMAND_PHASES
    )
)


def test_the_non_command_targets_are_every_phase_but_the_four_commands() -> None:
    """§10.3's "13 of 17": the arithmetic the two tests below depend on."""
    assert len(SERVICE_DISCOVERY_PHASES) == 17
    assert set(SERVICE_DISCOVERY_PHASES) > _COMMAND_PHASES
    assert len(_NON_COMMAND_TARGETS) == 13


@pytest.mark.parametrize("target", _NON_COMMAND_TARGETS)
@pytest.mark.xfail(
    strict=True,
    reason="CMK-38588 (§10.3) -- only `monitor`, `disable` and `drop` are commands; every other "
    "value names a state the caller cannot ask for and must be refused with a 400",
)
def test_non_command_target_is_rejected(target: str) -> None:
    with pytest.raises(Exception):  # noqa: B017  # the rejection type is not decided yet
        run_cell(DiscoveryState.MONITORED, target)


#: The three non-command targets `_verify_permissions` happens to have an arm for. The other
#: ten delete the service without demanding anything at all.
_NON_COMMAND_TARGETS_DEMANDING_A_PERMISSION = {
    DiscoveryState.CHANGED,
    DiscoveryState.CLUSTERED_NEW,
    DiscoveryState.CLUSTERED_OLD,
}


@pytest.mark.parametrize("target", _NON_COMMAND_TARGETS)
def test_non_command_target_silently_deletes_the_service(target: str) -> None:
    """Today: a monitored service is dropped from the autochecks file, and 10 of the 13 targets
    demand no permission to do it.

    `compute_discovery_transition` rebuilds the autochecks from scratch, so a target no handler
    writes for is a deletion, not a no-op (§1). The three targets that do demand a permission
    demand `to_monitored`, which is the permission for keeping the service -- not for deleting
    it.
    """
    outcome = run_cell(DiscoveryState.MONITORED, target)
    assert outcome.computed is True
    assert outcome.in_autochecks is False
    assert outcome.permissions == (
        ("wato.service_discovery_to_monitored",)
        if target in _NON_COMMAND_TARGETS_DEMANDING_A_PERMISSION
        else ()
    )


# --------------------------------------------------------------------------------------------
# T1b.12 -- a selection of `EVERYTHING` collapses werk 6708's guard (R-F1 / §10.11)
# --------------------------------------------------------------------------------------------
#
# `selected_services` does two unrelated jobs. It decides which rows a command may touch
# (`_get_table_target:549` for `UPDATE_SERVICES`, `:580` for `BULK_UPDATE`, `:590` for the two
# `SINGLE_UPDATE*`), and it is the subtrahend of the `add_disabled_rule` guard (`:405`). A
# whole-table action has to pass `EVERYTHING` for the first job, and the second job then reads
# that as "the user named every one of these services as a service to disable" -- which is what
# werk 19062's carve-out is for, and which no whole-table action ever means.
#
# None of the three call sites that pass `EVERYTHING` is a disable request: their `update_target`
# is `unchanged`, `removed` and `unchanged` respectively (`execute_service_discovery.py:124`,
# `:140`, `:192`). The one REST path that *can* disable passes the single service it was given
# (`update_service_phase.py:104`), so the carve-out is properly served there and needs no help
# from the sentinel.

#: The two whole-table paths that accept services into monitoring. `FIX_ALL` is the third, and it
#: is the reference: it reaches the identical targets on both tables below while passing `()`,
#: which is why the divergence is attributable to the selection alone.
_ACCEPT_EVERYTHING_PATHS = (
    pytest.param(
        DiscoveryAction.UPDATE_SERVICES,
        None,
        None,
        id="gui-accept-whole-table",
    ),
    pytest.param(
        DiscoveryAction.BULK_UPDATE,
        DiscoveryState.UNDECIDED,
        DiscoveryState.MONITORED,
        id="rest-mode-new",
    ),
)

#: Both tables carry one disabled row whose description must not be written to a rule, and one
#: row being accepted so that a transition is computed at all. They differ only in the blast
#: radius: on the first the spurious rule is redundant with whatever already disabled the
#: service, on the second it disables a second service that nothing had disabled.
_GUARDED_TABLES = (
    pytest.param(disabled_plus_unrelated_change, DESCRIPTION, id="unique-description"),
    pytest.param(two_plugins_one_description, SHARED_DESCRIPTION, id="shared-description"),
)


def _accept_everything(
    action: DiscoveryAction,
    update_source: str | None,
    update_target: str | None,
    table: Callable[[], list[CheckPreviewEntry]],
) -> DiscoveryTransition:
    transition, _permissions = compute(
        action=action,
        update_source=update_source,
        update_target=update_target,
        selected_services=EVERYTHING,
        check_table=table(),
    )
    assert transition is not None
    return transition


@pytest.mark.parametrize("action, update_source, update_target", _ACCEPT_EVERYTHING_PATHS)
@pytest.mark.parametrize("table, _disabled_description", _GUARDED_TABLES)
@pytest.mark.xfail(
    strict=True,
    reason="CMK-38590 (§10.11) -- `EVERYTHING` means 'this action applies to the whole table', not "
    "'the user named these services as services to disable'. Reading it as the latter defeats werk "
    "6708's guard on every whole-table save",
)
def test_accepting_every_service_writes_the_same_rules_as_fix_all(
    action: DiscoveryAction,
    update_source: str | None,
    update_target: str | None,
    table: Callable[[], list[CheckPreviewEntry]],
    _disabled_description: str,
) -> None:
    """§4.2: the three accept-everything paths must agree on the rule delta.

    Asserted against `FIX_ALL` rather than against a literal, because `FIX_ALL` is not merely
    correct here -- it is the same operation. It reaches the same target for every row of both
    tables, so any difference in the result is the selection's doing and nothing else.
    """
    reference, _permissions = compute(
        action=DiscoveryAction.FIX_ALL,
        update_target=None,
        selected_services=(),
        check_table=table(),
    )
    assert reference is not None
    transition = _accept_everything(action, update_source, update_target, table)

    assert transition.add_disabled_rule == reference.add_disabled_rule == set()


@pytest.mark.parametrize("action, update_source, update_target", _ACCEPT_EVERYTHING_PATHS)
@pytest.mark.parametrize("table, disabled_description", _GUARDED_TABLES)
def test_accepting_every_service_writes_a_rule_for_the_disabled_one(
    action: DiscoveryAction,
    update_source: str | None,
    update_target: str | None,
    table: Callable[[], list[CheckPreviewEntry]],
    disabled_description: str,
) -> None:
    """Today: every whole-table save re-writes a rule for each already-disabled service.

    Idempotent after the first write, but not free: `EnabledDisabledServicesEditor` costs one
    `get_services_labels` automation plus one rule-match per description (CMK-26792), and the
    pending change is created either way because `need_sync` is computed before the subtraction.
    """
    transition = _accept_everything(action, update_source, update_target, table)
    assert transition.add_disabled_rule == {disabled_description}
    assert transition.need_sync is True


@pytest.mark.parametrize("action, update_source, update_target", _ACCEPT_EVERYTHING_PATHS)
def test_accepting_every_service_disables_the_sibling_it_just_accepted(
    action: DiscoveryAction,
    update_source: str | None,
    update_target: str | None,
) -> None:
    """Today: the harmful instantiation -- the accepted service is written *and* suppressed.

    The TCP plugin's service was undecided and nothing disabled it. The save accepts it into the
    autochecks and, in the same transition, writes an `ignored_services` rule for its description
    -- so it reads back as `ignored` on the next scan. The user asked for it to be monitored.

    This also breaks the §4 invariant that a disabled service is never in the autochecks file,
    from the other side than T1b.1 does: there the rule is right and the autochecks entry is
    residue, here the autochecks entry is right and the rule is residue.

    Note the bound on the blast radius: both core config writers reject duplicate service
    descriptions outright -- `duplicate_service_warning` plus `continue` in
    `cmk/base/core/nagios/_create_config.py:683` and `cmk/base/nonfree/cmc/_services.py:331` --
    so if both services were enabled, only one of them would be monitored anyway. What the rule
    costs is a configuration change nobody asked for, on the ruleset page, with a pending change.
    """
    transition = _accept_everything(
        action, update_source, update_target, two_plugins_one_description
    )
    assert transition.add_disabled_rule == {SHARED_DESCRIPTION}
    # Which *values* get written on these two paths is A3's separate question -- neither adopts the
    # new ones (`services.py:Discovery._get_autochecks_values`), which is quarantined as T1b.8.
    # Asserting them here would make this test fail when that is fixed, so only the identity is
    # pinned: the one autochecks slot the shared description has is occupied by the service being
    # suppressed.
    written = transition.new_autochecks.target_services
    assert set(written) == {SHARED_DESCRIPTION}
    assert str(written[SHARED_DESCRIPTION].check_plugin_name) == TCP_PLUGIN
