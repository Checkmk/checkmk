#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from datetime import datetime, UTC
from pathlib import Path

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.prism.agent_based.prism_protection_policies import (
    check_protection_policy,
    DEFAULT_PARAMS,
    discovery_prism_protection_policies,
    Params,
    parse_prism_protection_policies_v4,
    Replication,
)

# The 2 policies a Prism Central 7.5 lab (anonymised) owns, as the v4 agent writes them: none
# protects a VM.
RECORDED_SECTION: StringTable = [
    [
        (
            Path(__file__).parents[1]
            / "special_agent"
            / "v4_fixtures"
            / "section_prism_protection_policies_v4.json"
        ).read_text()
    ]
]

NOW = datetime(2026, 11, 11, 16, 0, tzinfo=UTC)
# The item of _policy() and of the recorded policy "cross-cluster"
HOURLY = "hourly (00000001)"
CROSS_CLUSTER = "cross-cluster (228d134a)"
LOCAL = {"label": "pc-a", "domainManagerExtId": "pc-a-id", "isPrimary": True}
REMOTE = {"label": "pc-c", "domainManagerExtId": "pc-c-id", "isPrimary": False}
HOUR = 3600.0


def _policy(
    vms: list[dict[str, object]],
    name: str = "hourly",
    ext_id: str = "11111111-aaaa-bbbb-cccc-000000000001",
    locations: tuple[dict[str, object], ...] = (LOCAL, REMOTE),
) -> dict[str, object]:
    return {
        "extId": ext_id,
        "name": name,
        "replicationLocations": list(locations),
        "replicationConfigurations": [
            {
                "sourceLocationLabel": "pc-a",
                "remoteLocationLabel": "pc-c",
                "schedule": {
                    "recoveryPointObjectiveTimeSeconds": 3600,
                    "retention": {"local": 2, "remote": 2},
                },
            }
        ],
        "vms": vms,
    }


def _section(*policies: dict[str, object]) -> StringTable:
    return [[json.dumps(list(policies))]]


def _run_check(
    item: str,
    string_table: StringTable,
    params: Params,
    value_store: dict[str, object] | None,
) -> CheckResult:
    return check_protection_policy(
        item,
        params,
        parse_prism_protection_policies_v4(string_table),
        {} if value_store is None else value_store,
        NOW.timestamp(),
    )


def _check(
    item: str,
    string_table: StringTable,
    params: Params = DEFAULT_PARAMS,
    value_store: dict[str, object] | None = None,
) -> list[Result]:
    return [
        result
        for result in _run_check(item, string_table, params, value_store)
        if isinstance(result, Result)
    ]


def _metrics(
    item: str,
    string_table: StringTable,
    params: Params = DEFAULT_PARAMS,
) -> list[Metric]:
    return [
        metric
        for metric in _run_check(item, string_table, params, None)
        if isinstance(metric, Metric)
    ]


def _vm(name: str, newest: str | None) -> dict[str, object]:
    vm: dict[str, object] = {"extId": f"id-{name}", "name": name}
    if newest is not None:
        vm["newestRecoveryPoint"] = newest
    return vm


def test_every_recorded_policy_gets_a_service() -> None:
    assert list(
        discovery_prism_protection_policies(parse_prism_protection_policies_v4(RECORDED_SECTION))
    ) == [Service(item="pts-pp (c589036a)"), Service(item=CROSS_CLUSTER)]


def test_lab_policy_without_vms_is_ok() -> None:
    assert _check(CROSS_CLUSTER, RECORDED_SECTION) == [
        Result(state=State.OK, summary="RPO: 1 hour 0 minutes"),
        Result(state=State.OK, summary="Protected VMs: 0"),
        Result(state=State.OK, notice="Remote locations: pc-c-1"),
        Result(state=State.OK, notice="Retention pc-a: 1 recovery point locally"),
        Result(
            state=State.OK,
            notice="Retention pc-a -> pc-c-1: 1 recovery point locally, 1 recovery point remotely",
        ),
    ]


def test_the_way_back_of_a_policy_is_ignored() -> None:
    """Only the schedules from the primary location apply while the VMs run there"""
    policy = _policy([_vm("app", "2026-11-11T14:00:00Z")])
    policy["replicationConfigurations"] = [
        {
            "sourceLocationLabel": source,
            "remoteLocationLabel": remote,
            "schedule": {"recoveryPointObjectiveTimeSeconds": rpo},
        }
        for source, remote, rpo in (("pc-a", "pc-c", 4 * 3600), ("pc-c", "pc-a", 3600))
    ]

    results = _check(HOURLY, _section(policy))

    assert (results[0], results[2], results[-1].state) == (
        Result(state=State.OK, summary="RPO: 4 hours 0 minutes"),
        Result(state=State.OK, notice="Remote locations: pc-c"),
        State.OK,
    )


def test_vm_with_an_unknown_recovery_point_is_unknown() -> None:
    results = _check(
        HOURLY,
        _section(
            _policy(
                [
                    _vm("app", "2026-11-11T15:30:00Z"),
                    {"extId": "id-db", "name": "db", "recoveryPointUnknown": True},
                ]
            )
        ),
    )

    assert results[-2:] == [
        Result(state=State.OK, notice="app: newest recovery point: 30 minutes 0 seconds"),
        Result(state=State.UNKNOWN, summary="db: recovery point could not be fetched"),
    ]


def test_auto_rollup_retention_shows_the_period() -> None:
    policy = _policy([])
    policy["replicationConfigurations"] = [
        {
            "sourceLocationLabel": "pc-a",
            "remoteLocationLabel": "pc-c",
            "schedule": {
                "recoveryPointObjectiveTimeSeconds": 3600,
                "retention": {
                    "local": {"snapshotIntervalType": "WEEKLY", "frequency": 4},
                    "remote": {"snapshotIntervalType": "DAILY", "frequency": 1},
                },
            },
        }
    ]

    assert _check(HOURLY, _section(policy))[3] == Result(
        state=State.OK, notice="Retention pc-a -> pc-c: 4 weeks locally, 1 day remotely"
    )


def test_vm_recovery_points_are_checked_against_the_rpo() -> None:
    results = _check(
        HOURLY,
        _section(
            _policy(
                [
                    _vm("fresh", "2026-11-11T15:30:00Z"),
                    _vm("late", "2026-11-11T14:15:00Z"),
                    _vm("stale", "2026-11-11T13:00:00Z"),
                ]
            )
        ),
    )

    assert results[4:] == [
        Result(state=State.OK, notice="fresh: newest recovery point: 30 minutes 0 seconds"),
        Result(
            state=State.WARN,
            summary=(
                "late: newest recovery point: 1 hour 45 minutes "
                "(warn/crit at 1 hour 30 minutes/2 hours 0 minutes)"
            ),
        ),
        Result(
            state=State.CRIT,
            summary=(
                "stale: newest recovery point: 3 hours 0 minutes "
                "(warn/crit at 1 hour 30 minutes/2 hours 0 minutes)"
            ),
        ),
    ]


def test_age_levels_can_be_switched_off() -> None:
    results = _check(
        HOURLY,
        _section(_policy([_vm("stale", "2026-11-10T16:00:00Z")])),
        Params(
            recovery_point_age=("no_levels", None),
            replication_states=DEFAULT_PARAMS["replication_states"],
            replication_paused=DEFAULT_PARAMS["replication_paused"],
        ),
    )

    assert results[-1] == Result(
        state=State.OK, notice="stale: newest recovery point: 1 day 0 hours"
    )


def test_vm_without_recovery_point_is_ok_when_first_seen() -> None:
    assert _check(HOURLY, _section(_policy([_vm("new", None)])))[-1] == Result(
        state=State.OK, notice="new: without recovery point since first seen: 0 seconds"
    )


def test_vm_without_recovery_point_gets_the_age_levels_from_when_it_was_first_seen() -> None:
    store: dict[str, object] = {"vms": {"id-new": {"first_seen": NOW.timestamp() - 1.75 * HOUR}}}

    assert _check(HOURLY, _section(_policy([_vm("new", None)])), value_store=store)[-1] == Result(
        state=State.WARN,
        summary=(
            "new: without recovery point since first seen: 1 hour 45 minutes "
            "(warn/crit at 1 hour 30 minutes/2 hours 0 minutes)"
        ),
    )


def test_remembered_recovery_point_counts_when_the_agent_no_longer_reports_it() -> None:
    store: dict[str, object] = {
        "vms": {"id-old": {"newest_recovery_point": NOW.timestamp() - 3 * HOUR}}
    }

    assert _check(HOURLY, _section(_policy([_vm("old", None)])), value_store=store)[-1] == Result(
        state=State.CRIT,
        summary=(
            "old: last recovery point (no longer listed in Prism Central): 3 hours 0 minutes "
            "(warn/crit at 1 hour 30 minutes/2 hours 0 minutes)"
        ),
    )


def test_listed_recovery_point_counts_even_if_a_later_one_was_seen_before() -> None:
    """The later one was deleted: the age counts from the newest one that still exists"""
    store: dict[str, object] = {
        "vms": {"id-app": {"newest_recovery_point": NOW.timestamp() - 1 * HOUR}}
    }

    assert _check(
        HOURLY, _section(_policy([_vm("app", "2026-11-11T14:00:00Z")])), value_store=store
    )[-1] == Result(
        state=State.CRIT,
        summary=(
            "app: newest recovery point: 2 hours 0 minutes "
            "(warn/crit at 1 hour 30 minutes/2 hours 0 minutes)"
        ),
    )


def test_vms_gone_from_the_policy_for_a_day_are_forgotten() -> None:
    store: dict[str, object] = {
        "vms": {
            "id-gone": {
                "first_seen": NOW.timestamp() - 25 * HOUR,
                "last_seen": NOW.timestamp() - 24 * HOUR,
            }
        }
    }

    _check(HOURLY, _section(_policy([_vm("kept", "2026-11-11T15:30:00Z")])), value_store=store)

    assert store == {
        "vms": {
            "id-kept": {
                "newest_recovery_point": NOW.timestamp() - 0.5 * HOUR,
                "last_seen": NOW.timestamp(),
            }
        }
    }


def test_forgetting_the_last_vm_leaves_a_value_store_that_is_not_empty() -> None:
    """Checkmk only writes a value store that isn't empty: an empty one would keep the old
    values on disk"""
    store: dict[str, object] = {
        "vms": {
            "id-gone": {
                "first_seen": NOW.timestamp() - 25 * HOUR,
                "last_seen": NOW.timestamp() - 24 * HOUR,
            }
        }
    }

    _check(HOURLY, _section(_policy([])), value_store=store)

    assert store == {"vms": {}}


def test_vm_missing_from_one_run_keeps_its_grace_period() -> None:
    store: dict[str, object] = {}
    list(
        check_protection_policy(
            HOURLY,
            DEFAULT_PARAMS,
            parse_prism_protection_policies_v4(_section(_policy([_vm("new", None)]))),
            store,
            NOW.timestamp() - 1.75 * HOUR,
        )
    )
    _check(HOURLY, _section(_policy([])), value_store=store)

    assert (
        _check(HOURLY, _section(_policy([_vm("new", None)])), value_store=store)[-1].state
        == State.WARN
    )


def test_every_item_ends_with_the_end_of_the_policy_id() -> None:
    section = parse_prism_protection_policies_v4(
        _section(
            _policy([], name="daily", ext_id="aaaaaaaa-0000-0000-0000-000000000001"),
            _policy([], name="daily", ext_id="bbbbbbbb-0000-0000-0000-000000000002"),
            _policy([], name="weekly", ext_id="cccccccc-0000-0000-0000-000000000003"),
        )
    )

    assert list(section) == ["daily (00000001)", "daily (00000002)", "weekly (00000003)"]


def _with_rpos(*rpos: int) -> dict[str, object]:
    policy = _policy([_vm("stale", "2026-11-11T13:00:00Z")])
    policy["replicationConfigurations"] = [
        {
            "sourceLocationLabel": "pc-a",
            "remoteLocationLabel": f"pc-{index}",
            "schedule": {"recoveryPointObjectiveTimeSeconds": rpo},
        }
        for index, rpo in enumerate(rpos)
    ]
    return policy


def test_synchronous_replication_keeps_the_levels_of_the_other_schedules() -> None:
    results = _check(HOURLY, _section(_with_rpos(0, 3600)))

    assert (results[0], results[-1].state) == (
        Result(state=State.OK, summary="RPO: 1 hour 0 minutes (and synchronous replication)"),
        State.CRIT,
    )


def test_synchronous_replication_only_has_no_age_levels() -> None:
    results = _check(HOURLY, _section(_with_rpos(0)))

    assert (results[0], results[-1]) == (
        Result(state=State.OK, summary="RPO: 0 (synchronous replication)"),
        Result(state=State.OK, notice="stale: newest recovery point: 3 hours 0 minutes"),
    )


def test_policy_without_vms_has_no_age_metric() -> None:
    assert _metrics(CROSS_CLUSTER, RECORDED_SECTION) == [Metric("prism_protection_policy_vms", 0)]


def test_number_of_protected_vms_is_a_metric() -> None:
    metrics = _metrics(HOURLY, _section(_policy([_vm("app", None), _vm("db", None)])))

    assert metrics[0] == Metric("prism_protection_policy_vms", 2)


def test_highest_recovery_point_age_is_a_metric_with_the_age_levels() -> None:
    metrics = _metrics(
        HOURLY,
        _section(
            _policy([_vm("fresh", "2026-11-11T15:30:00Z"), _vm("stale", "2026-11-11T13:00:00Z")])
        ),
    )

    assert metrics[-1] == Metric("backup_age", 3 * HOUR, levels=(1.5 * HOUR, 2 * HOUR))


def test_age_metric_has_no_levels_when_they_are_switched_off() -> None:
    metrics = _metrics(
        HOURLY,
        _section(_policy([_vm("stale", "2026-11-11T13:00:00Z")])),
        Params(
            recovery_point_age=("no_levels", None),
            replication_states=DEFAULT_PARAMS["replication_states"],
            replication_paused=DEFAULT_PARAMS["replication_paused"],
        ),
    )

    assert metrics[-1] == Metric("backup_age", 3 * HOUR)


def test_vm_with_an_unknown_recovery_point_is_left_out_of_the_age_metric() -> None:
    metrics = _metrics(
        HOURLY,
        _section(
            _policy(
                [
                    _vm("app", "2026-11-11T15:30:00Z"),
                    {"extId": "id-db", "name": "db", "recoveryPointUnknown": True},
                ]
            )
        ),
    )

    assert metrics[-1] == Metric("backup_age", 0.5 * HOUR, levels=(1.5 * HOUR, 2 * HOUR))


def test_policy_whose_recovery_points_are_all_unknown_has_no_age_metric() -> None:
    metrics = _metrics(
        HOURLY,
        _section(_policy([{"extId": "id-db", "name": "db", "recoveryPointUnknown": True}])),
    )

    assert metrics == [Metric("prism_protection_policy_vms", 1)]


def test_empty_section_discovers_nothing() -> None:
    assert list(discovery_prism_protection_policies(parse_prism_protection_policies_v4([]))) == []


def _replicated_vm(*replications: tuple[str, str], name: str = "app") -> dict[str, object]:
    return {
        **_vm(name, "2026-11-11T15:30:00Z"),
        "replications": [{"target": target, "status": status} for target, status in replications],
    }


def test_replication_states_of_a_vm_are_shown_per_remote_location() -> None:
    results = _check(
        HOURLY,
        _section(
            _policy(
                [
                    _replicated_vm(
                        ("pc-c", "IN_SYNC"),
                        ("pc-d", "SYNCING"),
                        ("pc-e", "OUT_OF_SYNC"),
                        ("pc-f", "$UNKNOWN"),
                    )
                ]
            )
        ),
    )

    assert results[-4:] == [
        Result(
            state=State.WARN,
            summary="Replication to pc-e: 1 VM out of sync",
            details="Replication to pc-e: 1 VM out of sync\napp",
        ),
        Result(
            state=State.UNKNOWN,
            summary="Replication to pc-f: 1 VM $UNKNOWN",
            details="Replication to pc-f: 1 VM $UNKNOWN\napp",
        ),
        Result(state=State.OK, notice="app: replication to pc-c: in sync"),
        Result(state=State.OK, notice="app: replication to pc-d: syncing"),
    ]


def test_parse_translates_the_replication_status() -> None:
    section = parse_prism_protection_policies_v4(
        _section(_policy([_replicated_vm(("pc-c", "OUT_OF_SYNC"), ("pc-f", "$UNKNOWN"))]))
    )

    assert section[HOURLY].replications == [
        Replication("app", "pc-c", "out_of_sync", "out of sync"),
        Replication("app", "pc-f", None, "$UNKNOWN"),
    ]


def test_vms_out_of_sync_with_a_remote_location_share_one_result() -> None:
    """Out of sync means the schedule is disabled, which affects all its VMs at once"""
    results = _check(
        HOURLY,
        _section(
            _policy(
                [
                    _replicated_vm(("pc-c", "OUT_OF_SYNC"), name="app"),
                    _replicated_vm(("pc-c", "OUT_OF_SYNC"), ("pc-d", "OUT_OF_SYNC"), name="db"),
                    _replicated_vm(("pc-c", "IN_SYNC"), name="web"),
                ]
            )
        ),
    )

    assert results[-3:] == [
        Result(
            state=State.WARN,
            summary="Replication to pc-c: 2 VMs out of sync",
            details="Replication to pc-c: 2 VMs out of sync\napp, db",
        ),
        Result(
            state=State.WARN,
            summary="Replication to pc-d: 1 VM out of sync",
            details="Replication to pc-d: 1 VM out of sync\ndb",
        ),
        Result(state=State.OK, notice="web: replication to pc-c: in sync"),
    ]


def test_replication_states_are_configurable() -> None:
    results = _check(
        HOURLY,
        _section(_policy([_replicated_vm(("pc-c", "SYNCING"))])),
        Params(
            recovery_point_age=("fixed", (1.5, 2.0)),
            replication_states={"in_sync": 0, "syncing": 1, "out_of_sync": 2},
            replication_paused=1,
        ),
    )

    assert results[-1] == Result(
        state=State.WARN,
        summary="Replication to pc-c: 1 VM syncing",
        details="Replication to pc-c: 1 VM syncing\napp",
    )


@pytest.mark.parametrize(
    ["missing", "expected"],
    [
        pytest.param(
            "not_found", "app: not found among Prism Central's protected resources", id="not found"
        ),
        pytest.param("none_reported", "app: no replication state reported", id="none reported"),
        pytest.param("incomplete", "app: replication state incomplete", id="incomplete"),
        pytest.param("new_reason", "app: no replication state (new_reason)", id="unknown reason"),
    ],
)
def test_vm_without_the_replication_state_asked_for_says_why(missing: str, expected: str) -> None:
    vm = {**_vm("app", "2026-11-11T15:30:00Z"), "replications": [], "replicationMissing": missing}

    assert _check(HOURLY, _section(_policy([vm])))[-1] == Result(state=State.OK, notice=expected)


def test_vm_whose_replication_state_was_not_asked_for_has_no_replication_line() -> None:
    results = _check(HOURLY, _section(_policy([_vm("app", "2026-11-11T15:30:00Z")])))

    assert results[-1] == Result(
        state=State.OK, notice="app: newest recovery point: 30 minutes 0 seconds"
    )


def _paused_policy() -> dict[str, object]:
    policy = _policy([])
    policy["replicationConfigurations"] = [
        {
            "sourceLocationLabel": "pc-a",
            "remoteLocationLabel": "pc-c",
            "schedule": {"recoveryPointObjectiveTimeSeconds": 0, "isReplicationPaused": True},
        }
    ]
    return policy


def test_paused_replication_is_warn() -> None:
    assert _check(HOURLY, _section(_paused_policy()))[-1] == Result(
        state=State.WARN, summary="Replication pc-a -> pc-c paused"
    )


def test_state_of_paused_replication_is_configurable() -> None:
    assert _check(
        HOURLY, _section(_paused_policy()), Params(**{**DEFAULT_PARAMS, "replication_paused": 2})
    )[-1] == Result(state=State.CRIT, summary="Replication pc-a -> pc-c paused")


def test_paused_way_back_is_ignored() -> None:
    policy = _paused_policy()
    policy["replicationConfigurations"] = [
        {
            "sourceLocationLabel": "pc-c",
            "remoteLocationLabel": "pc-a",
            "schedule": {"recoveryPointObjectiveTimeSeconds": 0, "isReplicationPaused": True},
        }
    ]

    assert all("paused" not in result.summary for result in _check(HOURLY, _section(policy)))


def test_vms_with_an_unknown_replication_state_share_one_unknown_result() -> None:
    assert _check(
        HOURLY,
        _section(
            _policy(
                [
                    {**_vm(name, "2026-11-11T15:30:00Z"), "replicationUnknown": True}
                    for name in ("app", "db")
                ]
            )
        ),
    )[-1] == Result(
        state=State.UNKNOWN,
        summary="Replication state could not be fetched for 2 VMs",
        details="Replication state could not be fetched for 2 VMs\napp, db",
    )
