#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tier 1c -- total characterization of the ``(source, target)`` grid.

This replaces ``test_do_discovery.py``, whose driver used
``itertools.combinations_with_replacement`` and therefore asserted **unordered** pairs: 120 of the
225 ordered combinations, chosen by the declaration order of ``DiscoveryState``'s attributes. Its
``known_results.get(pair, empty_result)`` lookup meant every pair the generator never produced was
silently compared against "nothing happens" -- and the 105 missing cells were not the boring ones.
Every "accept" and every "re-enable" transition was in the untested half, which is the direct
explanation for the werk 19800 gap surviving (behaviour matrix §7.0, A2-F2).

The sweep here is total: 15 sources x 15 targets, no gaps and no dead expectations, split into the
two regions CMK-38588 (§10.3) draws. A ``target`` is either one of the four commands a caller may
ask for (``COMMAND_TARGETS``), in which case the cell computes a transition, or one of the eleven
other ``DiscoveryState`` values, in which case ``Discovery`` refuses it outright -- no ``_case_*``
handler writes for it, so accepting one would delete the service in the name of moving it. The two
regions are asserted separately below.

It is **characterization, not conformance** -- it states what the code does today so that a rewrite
cannot change any cell by accident. Which of the transition-computing cells are *wrong* is decided
in ``test_discovery_transition_matrix.py`` (§11.2's meaningful cells, which must pass) and
``test_discovery_transition_quarantine.py`` (the divergences, each paired with a strict-xfail on
the intended outcome and a ticket).

The expectations are written as **data**: one ``HandlerSpec`` per source, naming the target sets
that make it write the autochecks entry or touch the disabled-services rule. That is behaviour
matrix §4's Matrix A2 transcribed, and it is deliberately not a re-implementation of the dispatch
-- a spec that has to be edited to accommodate a change is a spec that noticed the change.
"""

import dataclasses
import itertools
from collections.abc import Sequence

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.watolib.services import COMMAND_TARGETS, DiscoveryState
from tests.unit.cmk.gui.watolib.discovery_matrix import (
    DESCRIPTION,
    NO_TRANSITION,
    OLD_LABELS,
    OLD_PARAMS,
    Outcome,
    PERMISSION_BY_TARGET,
    run_cell,
)

ALL_STATES: Sequence[str] = tuple(
    sorted({value for name, value in vars(DiscoveryState).items() if name.isupper()})
)

#: The four targets a caller may ask for (§11.1), and the other eleven, which `Discovery` refuses.
#: Derived from `COMMAND_TARGETS` so that adding a `DiscoveryState` puts it on the refused side
#: until someone decides it is a command -- it cannot silently join the accepted grid.
_COMMAND_TARGETS: Sequence[str] = tuple(sorted(COMMAND_TARGETS))
_NON_COMMAND_TARGETS: Sequence[str] = tuple(t for t in ALL_STATES if t not in COMMAND_TARGETS)


@dataclasses.dataclass(frozen=True)
class HandlerSpec:
    """What the handler for one source state does, per command target (§4, Matrix A2)."""

    writes: frozenset[str]
    """Command targets for which the autochecks entry is (re)written. Anything else drops it: the
    transition rebuilds the file from scratch, so "no handler wrote it" means "deleted" (§1)."""

    adds_rule: frozenset[str] = frozenset()
    removes_rule: frozenset[str] = frozenset()


#: The command targets only: every `HandlerSpec` set below is a subset of these, because a
#: non-command target never reaches a handler at all.
_EVERY_TARGET = frozenset(_COMMAND_TARGETS)

_SPECS: dict[str, HandlerSpec] = {
    # `_case_undecided`: the service is not in the file yet, so only `monitored` puts it there.
    DiscoveryState.UNDECIDED: HandlerSpec(
        writes=frozenset({DiscoveryState.MONITORED}),
        adds_rule=frozenset({DiscoveryState.IGNORED}),
    ),
    # `_case_vanished`: `removed` is the only target that cleans up; the other three commands fall
    # into the catch-all `else` and keep the service (A2-F4).
    DiscoveryState.VANISHED: HandlerSpec(
        writes=_EVERY_TARGET - {DiscoveryState.REMOVED},
        adds_rule=frozenset({DiscoveryState.IGNORED}),
    ),
    # `_case_monitored`: keeps the entry for `monitored` and -- the werk 19800 gap -- `ignored`.
    DiscoveryState.MONITORED: HandlerSpec(
        writes=frozenset({DiscoveryState.MONITORED, DiscoveryState.IGNORED}),
        adds_rule=frozenset({DiscoveryState.IGNORED}),
    ),
    # `_case_changed`: as `_case_monitored`. `changed` itself is not a command, so the self-target
    # that wrote the old values back is now refused before the handler runs.
    DiscoveryState.CHANGED: HandlerSpec(
        writes=frozenset({DiscoveryState.MONITORED, DiscoveryState.IGNORED}),
        adds_rule=frozenset({DiscoveryState.IGNORED}),
    ),
    # `_case_ignored`: the only handler that removes a rule. A disabled service is never written
    # to the autochecks file (werk 19801 / CMK-33299) except when it is being re-enabled.
    DiscoveryState.IGNORED: HandlerSpec(
        writes=frozenset({DiscoveryState.MONITORED}),
        adds_rule=frozenset({DiscoveryState.IGNORED}),
        removes_rule=frozenset(
            {DiscoveryState.MONITORED, DiscoveryState.UNDECIDED, DiscoveryState.VANISHED}
        ),
    ),
    # `_case_clustered`: preserve-by-rewrite for every command but `ignored`, which drops the
    # node's entry and adds no rule -- un-monitoring the service on the cluster (§10.17).
    **{
        clustered: HandlerSpec(writes=_EVERY_TARGET - {DiscoveryState.IGNORED})
        for clustered in (
            DiscoveryState.CLUSTERED_NEW,
            DiscoveryState.CLUSTERED_OLD,
            DiscoveryState.CLUSTERED_VANISHED,
            DiscoveryState.CLUSTERED_IGNORED,
        )
    },
    # No arm in `_apply_state_change`: nothing happens, which is harmless only because these
    # services have no autochecks entry to lose (§11.2a rule 2). `removed` is here because it is
    # a command, not a state a classifier can produce (§2.1).
    **{
        ineligible: HandlerSpec(writes=frozenset())
        for ineligible in (
            DiscoveryState.MANUAL,
            DiscoveryState.ACTIVE,
            DiscoveryState.CUSTOM,
            DiscoveryState.ACTIVE_IGNORED,
            DiscoveryState.CUSTOM_IGNORED,
            DiscoveryState.REMOVED,
        )
    },
}


def _expected(source: str, target: str) -> Outcome:
    """The outcome the specs above predict for one cell whose target is a command."""
    if source == target:
        # Nothing differs, so `apply_changes` is never set and no transition is computed at all.
        return NO_TRANSITION

    spec = _SPECS[source]
    writes = target in spec.writes
    adds = frozenset({DESCRIPTION}) if target in spec.adds_rule else frozenset()
    removes = frozenset({DESCRIPTION}) if target in spec.removes_rule else frozenset()
    permission = PERMISSION_BY_TARGET.get(target)
    return Outcome(
        computed=True,
        in_autochecks=writes,
        # `SINGLE_UPDATE` adopts neither facet, so a written entry always carries the old values
        # (§5, A3-F1). Adoption per action is pinned by `test_value_adoption_matrix`.
        params=OLD_PARAMS if writes else None,
        labels=OLD_LABELS if writes else None,
        add_disabled=adds,
        remove_disabled=removes,
        need_sync=bool(adds or removes),
        permissions=() if permission is None else (permission,),
    )


def test_the_sweep_covers_every_declared_state() -> None:
    """A `DiscoveryState` value added without a `HandlerSpec` must fail here, not go untested."""
    assert set(_SPECS) == set(ALL_STATES)
    assert len(ALL_STATES) == 15


def test_the_grid_is_split_into_four_commands_and_eleven_refused_targets() -> None:
    """§10.3's arithmetic: the two regions the tests below partition the target axis into."""
    assert len(_COMMAND_TARGETS) == 4
    assert len(_NON_COMMAND_TARGETS) == 11
    assert set(_COMMAND_TARGETS) | set(_NON_COMMAND_TARGETS) == set(ALL_STATES)


@pytest.mark.parametrize(
    "source, target",
    list(itertools.product(ALL_STATES, _COMMAND_TARGETS)),
    ids=str,
)
def test_transition_cell(source: str, target: str) -> None:
    """All 15 x 4 command cells, each asserted -- none defaulted."""
    assert run_cell(source, target) == _expected(source, target)


@pytest.mark.parametrize(
    "source, target",
    list(itertools.product(ALL_STATES, _NON_COMMAND_TARGETS)),
    ids=str,
)
def test_non_command_target_is_refused(source: str, target: str) -> None:
    """§10.3 / CMK-38588: a target that is not a command is refused for every source, rather than
    silently deleting the service (or, from a `vanished` row, silently keeping it)."""
    with pytest.raises(MKGeneralException):
        run_cell(source, target)


def test_the_command_targets_from_a_monitored_service_demand_their_permission() -> None:
    """§5.1: moving a monitored service to any of the other three commands demands exactly the
    permission that command maps to; moving it to `monitored` is a no-op and demands nothing.

    The counterpart of the removed §10.3 characterization: it used to be that nine of fifteen
    targets deleted a monitored service demanding nothing at all. Those nine are now refused, so
    the only targets left to demand anything are the commands, and each demands its own permission.
    """
    demanded = {
        target: run_cell(DiscoveryState.MONITORED, target).permissions
        for target in _COMMAND_TARGETS
    }
    assert demanded == {
        DiscoveryState.MONITORED: (),
        DiscoveryState.UNDECIDED: (PERMISSION_BY_TARGET[DiscoveryState.UNDECIDED],),
        DiscoveryState.IGNORED: (PERMISSION_BY_TARGET[DiscoveryState.IGNORED],),
        DiscoveryState.REMOVED: (PERMISSION_BY_TARGET[DiscoveryState.REMOVED],),
    }
