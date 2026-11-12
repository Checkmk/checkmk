#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Protection policies of Prism Central, as written by the v4 agent

v4 can't read protection domains, so this replaces prism_protection_domains for the v4 agent.
"""

import time
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Literal, NamedTuple, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    FixedLevelsT,
    get_value_store,
    NoLevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.prism.v4_models import (
    AutoRollupRetentionDetails,
    ProtectedVm,
    ProtectionPolicies,
    ProtectionPolicy,
    ReplicationConfiguration,
)

Section = Mapping[str, ProtectionPolicy]


class Params(TypedDict):
    # The age of a VM's newest recovery point, as a multiple of the policy's RPO
    recovery_point_age: FixedLevelsT[float] | NoLevelsT


DEFAULT_PARAMS = Params(recovery_point_age=("fixed", (1.5, 2.0)))

FORGET_GONE_VMS_AFTER = 24 * 3600.0

_ROLLUP_UNITS = {
    "HOURLY": "hour",
    "DAILY": "day",
    "WEEKLY": "week",
    "MONTHLY": "month",
    "YEARLY": "year",
}


def parse_prism_protection_policies(string_table: StringTable) -> Section:
    if not string_table:
        return {}
    policies = ProtectionPolicies.model_validate_json(string_table[0][0]).root
    # Policy names need not be unique. The end of the ID keeps the item of a policy stable when
    # another policy of the same name is added.
    return {f"{policy.name} ({policy.ext_id[-8:]})": policy for policy in policies}


agent_section_prism_protection_policies = AgentSection(
    name="prism_protection_policies",
    parse_function=parse_prism_protection_policies,
)


def discovery_prism_protection_policies(section: Section) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def _active_configurations(policy: ProtectionPolicy) -> list[ReplicationConfiguration]:
    """The configurations that apply while the VMs run at the primary location. A policy lists
    the way back (target to source) too, it only applies after a failover."""
    primaries = {location.label for location in policy.replication_locations if location.is_primary}
    return [
        configuration
        for configuration in policy.replication_configurations
        if not primaries or configuration.source_location_label in primaries
    ]


def _rpo_seconds(rpos: Sequence[int]) -> int | None:
    """The shortest RPO of the schedules with recovery points. An RPO of 0 is synchronous
    replication."""
    return min((rpo for rpo in rpos if rpo > 0), default=None)


def _remote_locations(configurations: Sequence[ReplicationConfiguration]) -> list[str]:
    return sorted(
        {
            configuration.remote_location_label
            for configuration in configurations
            if configuration.remote_location_label is not None
        }
    )


def _render_retention(retention: int | AutoRollupRetentionDetails) -> str:
    if isinstance(retention, int):
        return f"{retention} recovery point{'' if retention == 1 else 's'}"
    if (unit := _ROLLUP_UNITS.get(retention.snapshot_interval_type)) is None:
        return f"{retention.frequency} x {retention.snapshot_interval_type}"
    return f"{retention.frequency} {unit}{'' if retention.frequency == 1 else 's'}"


def _retention_result(configuration: ReplicationConfiguration) -> Result | None:
    if (retention := configuration.schedule.retention) is None or retention.local is None:
        return None
    if configuration.remote_location_label is None:
        locations = configuration.source_location_label
        kept = f"{_render_retention(retention.local)} locally"
    else:
        locations = (
            f"{configuration.source_location_label} -> {configuration.remote_location_label}"
        )
        kept = f"{_render_retention(retention.local)} locally" + (
            "" if retention.remote is None else f", {_render_retention(retention.remote)} remotely"
        )
    return Result(state=State.OK, notice=f"Retention {locations}: {kept}")


class _RecoveryPointAge(NamedTuple):
    seconds: float
    # listed: the newest recovery point Prism Central lists for the VM
    # remembered: none listed any more, the age counts from the last one the check saw
    # first_seen: the check never saw a recovery point, the age counts from when it first saw the VM
    source: Literal["listed", "remembered", "first_seen"]


_AGE_LABELS = {
    "listed": "{vm}: newest recovery point",
    "remembered": "{vm}: last recovery point (no longer listed in Prism Central)",
    "first_seen": "{vm}: without recovery point since first seen",
}


class _RememberedVm(TypedDict, total=False):
    """What the check remembers about one VM, as timestamps"""

    # Only while the VM has no recovery point
    first_seen: float
    newest_recovery_point: float
    last_seen: float


# By extId of the VM
type _RememberedVms = dict[str, _RememberedVm]


def _remembered_vms(value_store: MutableMapping[str, object]) -> _RememberedVms:
    """What the check remembers per VM, by its extId, under one key that is always set: Checkmk
    only writes a value store that isn't empty, so forgetting the last VM must still leave a key"""
    vms = value_store.get("vms")
    if not isinstance(vms, dict):
        vms = value_store["vms"] = {}
    return vms


def _recovery_point_age(
    vm: ProtectedVm,
    now: float,
    remembered: _RememberedVm,
) -> _RecoveryPointAge:
    """The age of the newest recovery point Prism Central lists for the VM. If it lists none,
    e.g. because they all expired, the age counts from the last one the check saw, so the alert
    doesn't clear when nothing is left to restore. A VM that never had a recovery point counts
    from when the check first saw it."""
    if vm.newest_recovery_point is not None:
        newest = vm.newest_recovery_point.timestamp()
        remembered["newest_recovery_point"] = newest
        remembered.pop("first_seen", None)
        return _RecoveryPointAge(max(0.0, now - newest), source="listed")
    if (newest_seen := remembered.get("newest_recovery_point")) is not None:
        return _RecoveryPointAge(max(0.0, now - newest_seen), source="remembered")
    first_seen = remembered.setdefault("first_seen", now)
    return _RecoveryPointAge(max(0.0, now - first_seen), source="first_seen")


def _forget_gone_vms(
    policy: ProtectionPolicy,
    now: float,
    value_store: MutableMapping[str, object],
) -> _RememberedVms:
    """Drop what the check remembers about VMs that have left the policy, so the value store
    doesn't keep growing. A VM is only dropped once it has been missing for
    FORGET_GONE_VMS_AFTER (24 h): a VM missing from a single run, e.g. because Prism Central's
    VM list was incomplete, keeps its first-seen time and newest recovery point."""
    vms = _remembered_vms(value_store)
    for vm in policy.vms:
        vms.setdefault(vm.ext_id, {})["last_seen"] = now
    for ext_id in [
        ext_id
        for ext_id, remembered in vms.items()
        if now - remembered.get("last_seen", 0.0) >= FORGET_GONE_VMS_AFTER
    ]:
        del vms[ext_id]
    value_store["vms"] = vms
    return vms


def check_protection_policy(
    item: str,
    params: Params,
    section: Section,
    value_store: MutableMapping[str, object],
    now: float,
) -> CheckResult:
    """The check with its value store and the current time given"""
    if (policy := section.get(item)) is None:
        return
    configurations = _active_configurations(policy)
    rpos = [
        configuration.schedule.recovery_point_objective_time_seconds
        for configuration in configurations
    ]
    rpo = _rpo_seconds(rpos)
    synchronous = 0 in rpos
    if rpo is None:
        rpo_text = "0 (synchronous replication)" if synchronous else "unknown"
    else:
        rpo_text = render.timespan(rpo) + (" (and synchronous replication)" if synchronous else "")
    yield Result(state=State.OK, summary=f"RPO: {rpo_text}")
    yield Result(state=State.OK, summary=f"Protected VMs: {len(policy.vms)}")
    remotes = _remote_locations(configurations)
    yield Result(
        state=State.OK,
        notice=f"Remote locations: {', '.join(remotes) if remotes else 'none'}",
    )
    for configuration in configurations:
        if (result := _retention_result(configuration)) is not None:
            yield result

    match params["recovery_point_age"]:
        case ("fixed", (warn, crit)) if rpo is not None:
            age_levels: FixedLevelsT[float] | None = (
                "fixed",
                (warn * rpo, crit * rpo),
            )
        case _:
            age_levels = None
    remembered_vms = _forget_gone_vms(policy, now, value_store)
    for vm in sorted(policy.vms, key=lambda vm: vm.name):
        if vm.recovery_point_unknown:
            yield Result(
                state=State.UNKNOWN, summary=f"{vm.name}: recovery point could not be fetched"
            )
            continue
        # A VM without any recovery point gets the same levels, counted from when the check
        # first saw it. Nutanix takes the first recovery point when it starts protecting a VM.
        age = _recovery_point_age(vm, now, remembered_vms[vm.ext_id])
        yield from check_levels(
            age.seconds,
            levels_upper=age_levels,
            render_func=render.timespan,
            label=_AGE_LABELS[age.source].format(vm=vm.name),
            notice_only=True,
        )


def check_prism_protection_policies(item: str, params: Params, section: Section) -> CheckResult:
    yield from check_protection_policy(item, params, section, get_value_store(), time.time())


check_plugin_prism_protection_policies = CheckPlugin(
    name="prism_protection_policies",
    service_name="NTNX Data Protection %s",
    sections=["prism_protection_policies"],
    discovery_function=discovery_prism_protection_policies,
    check_function=check_prism_protection_policies,
    check_default_parameters=DEFAULT_PARAMS,
    check_ruleset_name="prism_protection_policies",
)
