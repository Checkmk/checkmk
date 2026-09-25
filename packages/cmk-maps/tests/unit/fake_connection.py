#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Fake connection returning deterministic sample data — test double only.

Not shipped in the daemon: exercises the connection-agnostic logic (folder-tree
assembly, state resolution) against a real :class:`ConnectionBase` implementation
without a live Livestatus socket."""

from __future__ import annotations

import math
import time as _time
from typing import override

from cmk.maps.backend.connections.base import (
    ConnectionBase,
    FolderInfo,
    FolderTreeData,
    FolderTreeHostRow,
    MetricHistoryResult,
    ServiceMatchRow,
    ServiceRow,
    TopologyRow,
)
from cmk.maps.backend.schemas.state import ObjectState, ServicesSummary

_HOST_STATES = ["UP", "DOWN", "UNREACHABLE"]
_SERVICE_STATES = ["OK", "WARNING", "CRITICAL", "UNKNOWN"]

_DEMO_HOSTS = ["localhost", "router01", "switch01", "fileserver", "mailserver"]
# Deterministic folder + site placement, shared by get_folder_tree and the
# service search so a match lands in the same folder/site as the host tree.
_DEMO_HOST_PLACEMENT: dict[str, tuple[str, str]] = {
    "localhost": ("datacenters/muc", "central"),
    "fileserver": ("datacenters/muc", "central"),
    "mailserver": ("datacenters/fra", "remote_fra"),
    "router01": ("network", "central"),
    "switch01": ("network", "remote_fra"),
}
_DEMO_SERVICES = [
    "HTTP",
    "PING",
    "Disk /",
    "Memory",
    "CPU Load",
    "CPU utilization",
    "SSH",
    "Interface eth0",
    "Temperature",
    "DB Connections",
]

# Pin demo hosts UP so a child can't be UNREACHABLE under an UP parent and the
# demo stays internally consistent.
_PINNED_HOST_STATES: dict[str, str] = dict.fromkeys(_DEMO_HOSTS, "UP")

# Cells the static showcase map points at, pinned so the demo doesn't depend
# on hash lottery.
_PINNED_SERVICE_STATES: dict[tuple[str, str], tuple[str, str]] = {
    ("fileserver", "Disk /"): ("WARNING", "used=82%;80;90;0;100"),
    ("localhost", "CPU utilization"): ("OK", "util=42%;80;90;0;100"),
    ("localhost", "Memory"): ("OK", "used=64%;80;90;0;100"),
    ("localhost", "HTTP"): ("CRITICAL", "time=4500ms;1000;3000;0;5000"),
    ("switch01", "Temperature"): ("OK", "temp=58C;65;80;0;100"),
    ("localhost", "PING"): ("OK", "rta=0.4ms;200;500;0; pl=0%;20;60;0;100"),
    ("router01", "PING"): ("OK", "rta=1.2ms;200;500;0; pl=0%;20;60;0;100"),
    ("switch01", "PING"): ("OK", "rta=0.8ms;200;500;0; pl=0%;20;60;0;100"),
}


def _classify_service(service: str) -> str:
    """Map a service description to a category key used by the demo helpers."""
    su = service.upper()
    if "CPU utilization" in service:
        return "cpu_util"
    if "CPU" in service or "Load" in service or "load" in service:
        return "cpu_load"
    if "Memory" in service or "Mem" in service:
        return "memory"
    if "Disk" in service:
        return "disk"
    if "HTTP" in service:
        return "http"
    if "PING" in su:
        return "ping"
    if "Interface" in service:
        return "interface"
    if "Temperature" in service or "Temp" in service:
        return "temperature"
    if "Connection" in service or "Conn" in service:
        return "connections"
    if su == "SSH":
        return "ssh"
    return ""


def _generate_perfdata(host: str, service: str) -> str:
    val = abs(hash(f"{host}:{service}val")) % 91 + 5
    cat = _classify_service(service)
    if cat == "cpu_util":
        return f"util={val}%;80;90;0;100"
    if cat == "cpu_load":
        load = round(val / 25.0, 2)
        return f"load1={load};5.0;10.0;0; load5={load};5.0;10.0;0; load15={load};5.0;10.0;0"
    if cat in ("memory", "disk"):
        return f"used={val}%;80;90;0;100"
    if cat == "http":
        ms = abs(hash(f"{host}:{service}ms")) % 2000 + 50
        return f"time={ms}ms;1000;3000;0;5000"
    if cat == "ping":
        rta = abs(hash(f"{host}:{service}rta")) % 200 + 1
        return f"rta={rta}.0ms;200;500;0; pl=0%;20;60;0;100"
    if cat == "interface":
        in_bps = abs(hash(f"{host}:{service}in")) % 95_000_000 + 5_000_000
        out_bps = abs(hash(f"{host}:{service}out")) % 95_000_000 + 5_000_000
        return (
            f"in={in_bps}B/s;100000000;120000000;0;125000000 "
            f"out={out_bps}B/s;100000000;120000000;0;125000000"
        )
    if cat == "temperature":
        temp = abs(hash(f"{host}:{service}temp")) % 60 + 25
        return f"temp={temp}C;65;80;0;100"
    if cat == "connections":
        conn = abs(hash(f"{host}:{service}conn")) % 150 + 10
        return f"conn={conn};80;100;0;200"
    return ""


def _format_metric(perf: str, label: str) -> str | None:
    for part in perf.split():
        if "=" in part and part.split("=", 1)[0] == label:
            tail = part.split("=", 1)[1]
            num = ""
            for ch in tail:
                if ch.isdigit() or ch in ".-":
                    num += ch
                else:
                    break
            return num or None
    return None


def _generate_output(service: str, state: str, perf: str) -> str:
    cat = _classify_service(service)
    if cat == "cpu_util":
        v = _format_metric(perf, "util") or "?"
        return f"CPU utilization: {v}% (warn/crit at 80/90%)"
    if cat == "cpu_load":
        v = _format_metric(perf, "load1") or "?"
        return f"15 min load {v} at 4 Cores"
    if cat == "memory":
        v = _format_metric(perf, "used") or "?"
        return f"RAM: {v}% used (warn/crit at 80/90%)"
    if cat == "disk":
        v = _format_metric(perf, "used") or "?"
        return f"{service}: {v}% used (warn/crit at 80/90%)"
    if cat == "http":
        v = _format_metric(perf, "time") or "?"
        prefix = "HTTP OK" if state == "OK" else f"HTTP {state}"
        return f"{prefix}: HTTP/1.1 200 OK - {v} ms response time"
    if cat == "ping":
        rta = _format_metric(perf, "rta") or "?"
        if state == "OK":
            return f"PING ok - Packet loss = 0%, RTA = {rta} ms"
        return f"PING {state} - elevated RTA = {rta} ms"
    if cat == "interface":
        in_v = _format_metric(perf, "in")
        out_v = _format_metric(perf, "out")
        if in_v and out_v:
            in_mb = round(int(in_v) / 1_000_000, 1)
            out_mb = round(int(out_v) / 1_000_000, 1)
            return f"[eth0] (up) speed 1 Gbit/s, in: {in_mb} MB/s, out: {out_mb} MB/s"
        return "[eth0] (up) speed 1 Gbit/s"
    if cat == "temperature":
        v = _format_metric(perf, "temp") or "?"
        return f"Temperature: {v}°C (warn/crit at 65/80°C)"
    if cat == "connections":
        v = _format_metric(perf, "conn") or "?"
        return f"{v} active connections (warn/crit at 80/100)"
    if cat == "ssh":
        return "SSH OK - OpenSSH 8.9p1, port 22 reachable" if state == "OK" else f"SSH {state}"
    return f"{service}: {state}"


# Per-category time-series spec for synthetic graphs.
# Each entry: (label, phase, unit, scale). `scale` lifts the 0..1 base signal
# into a realistic value range so axes don't auto-format tiny floats with
# bogus SI suffixes (e.g. 0.5 ms rendered as "1.2G").
_CATEGORY_METRIC_DEFS: dict[str, list[tuple[str, float, str, float]]] = {
    "cpu_load": [("load1", 0.0, "", 1.0), ("load5", 1.0, "", 1.0), ("load15", 2.0, "", 1.0)],
    "memory": [("used", 0.0, "%", 100.0)],
    "disk": [("used", 0.0, "%", 100.0)],
    "http": [("time", 0.0, "ms", 1000.0)],
    "ping": [("rta", 0.0, "ms", 100.0), ("pl", math.pi, "%", 5.0)],
    "interface": [("in", 0.0, "B/s", 1e8), ("out", math.pi, "B/s", 1e8)],
    "temperature": [("temp", 0.0, "C", 80.0)],
    "connections": [("conn", 0.0, "", 150.0)],
}
_DEFAULT_METRIC_DEFS: list[tuple[str, float, str, float]] = [("value", 0.0, "", 1.0)]


def _apply_demo_timing(state: ObjectState, seed_str: str, *, max_age: int) -> None:
    """Deterministic timing/attempt fields so the demo map exercises tooltip paths."""
    now = _time.time()
    seed = abs(hash(seed_str))
    last_check = now - (seed % 60)
    state.last_check = last_check
    state.next_check = last_check + 60
    state.last_state_change = now - (seed % max_age + 60)
    state.state_type = "HARD"
    state.current_attempt = 1
    state.max_attempts = 3


def _apply_demo_host_metadata(state: ObjectState, hostname: str) -> None:
    state.alias = f"alias-{hostname}"
    state.address = f"192.0.2.{abs(hash(hostname)) % 250 + 1}"
    _apply_demo_timing(state, hostname, max_age=14400)


def _apply_demo_service_metadata(state: ObjectState, host: str, service: str) -> None:
    _apply_demo_timing(state, f"{host}:{service}", max_age=7200)


class FakeConnection(ConnectionBase):
    """Returns deterministic demo states for testing."""

    connection_id = "test"

    @override
    async def get_host_state(self, hostname: str) -> ObjectState:
        state = _PINNED_HOST_STATES.get(hostname, _HOST_STATES[hash(hostname) % len(_HOST_STATES)])
        if state == "UP":
            output = f"Packet received - PING ok: {hostname} reachable"
        elif state == "DOWN":
            output = f"CRITICAL - {hostname} is DOWN (no ICMP echo reply)"
        else:
            output = f"UNREACHABLE - parent host has no route to {hostname}"
        result = ObjectState(
            object_id="",
            type="host",
            state=state,
            output=output,
            acknowledged=False,
            in_downtime=False,
        )
        _apply_demo_host_metadata(result, hostname)
        return result

    @override
    async def get_service_state(self, host: str, service: str) -> ObjectState:
        pinned = _PINNED_SERVICE_STATES.get((host, service))
        if pinned is not None:
            state, perf_data = pinned
        else:
            state = _SERVICE_STATES[hash(f"{host}:{service}") % len(_SERVICE_STATES)]
            perf_data = _generate_perfdata(host, service)
        output = _generate_output(service, state, perf_data)
        result = ObjectState(
            object_id="",
            type="service",
            state=state,
            output=output,
            perf_data=perf_data,
            acknowledged=False,
            in_downtime=False,
        )
        _apply_demo_service_metadata(result, host, service)
        return result

    @override
    async def get_services_summary(self, hostnames: list[str]) -> dict[str, ServicesSummary]:
        # Compute a deterministic summary per host from the demo service set
        # without going through the per-service get_host_services path, which
        # would do _DEMO_SERVICES queries per host.
        result: dict[str, ServicesSummary] = {}
        for host in hostnames:
            summary = ServicesSummary()
            for svc in _DEMO_SERVICES:
                pinned = _PINNED_SERVICE_STATES.get((host, svc))
                state = (
                    pinned[0]
                    if pinned is not None
                    else _SERVICE_STATES[hash(f"{host}:{svc}") % len(_SERVICE_STATES)]
                )
                if state == "OK":
                    summary.ok += 1
                elif state == "WARNING":
                    summary.warning += 1
                elif state == "CRITICAL":
                    summary.critical += 1
                elif state == "UNKNOWN":
                    summary.unknown += 1
                elif state == "PENDING":
                    summary.pending += 1
            result[host] = summary
        return result

    @override
    async def get_hostgroup_states(self, group: str) -> ObjectState:
        idx = hash(group) % len(_HOST_STATES)
        state = _HOST_STATES[idx]
        return ObjectState(
            object_id="",
            type="hostgroup",
            state=state,
            output=f"Hostgroup {group}: {state}",
        )

    @override
    async def get_servicegroup_states(self, group: str) -> ObjectState:
        idx = hash(group) % len(_SERVICE_STATES)
        state = _SERVICE_STATES[idx]
        return ObjectState(
            object_id="",
            type="servicegroup",
            state=state,
            output=f"Servicegroup {group}: {state}",
        )

    @override
    async def get_group_members(self, group_type: str, group_name: str) -> list[str]:
        if group_type in ("all_services", "servicegroup"):
            return [f"{h};{s}" for h in _DEMO_HOSTS for s in _DEMO_SERVICES]
        return list(_DEMO_HOSTS)

    @override
    async def get_folder_tree(
        self, *, only_hard: bool = False, sites: list[str] | None = None
    ) -> FolderTreeData:
        # Deterministic demo tree: nested folders, two empty folders
        # (staging/decommissioned) and hosts spread across two sites.
        folders: list[FolderInfo] = [
            {"path": "", "title": "Main"},
            {"path": "datacenters", "title": "Datacenters"},
            {"path": "datacenters/muc", "title": "Munich"},
            {"path": "datacenters/fra", "title": "Frankfurt"},
            {"path": "network", "title": "Network"},
            {"path": "staging", "title": "Staging"},
            {"path": "decommissioned", "title": "Decommissioned"},
        ]
        placement = _DEMO_HOST_PLACEMENT
        summaries = await self.get_services_summary(list(placement))
        hosts: list[FolderTreeHostRow] = []
        for name, (folder, site) in placement.items():
            if sites and site not in sites:
                continue
            hosts.append(
                {
                    "host_name": name,
                    "folder_path": folder,
                    "state": _PINNED_HOST_STATES.get(name, "UP"),
                    "output": f"OK - {name} reachable",
                    "site_id": site,
                    "services_summary": summaries.get(name),
                }
            )
        return FolderTreeData(folders=list(folders), hosts=hosts)

    @override
    async def get_topology(self) -> list[TopologyRow]:
        topology: list[tuple[str, list[str], str, str]] = [
            ("router01", [], "UP", ""),
            ("switch01", ["router01"], "UP", ""),
            ("localhost", ["router01"], "UP", ""),
            ("fileserver", ["switch01"], "DOWN", "Connection refused"),
            ("mailserver", ["switch01"], "UP", ""),
        ]
        names = [n for n, _, _, _ in topology]
        summaries = await self.get_services_summary(names)
        rows: list[TopologyRow] = []
        now = _time.time()
        for name, parents, state, output in topology:
            seed = abs(hash(name))
            last_check = now - (seed % 60)
            row: TopologyRow = {
                "name": name,
                "parents": parents,
                "state": state,
                "output": output,
                "alias": f"alias-{name}",
                "address": f"192.0.2.{seed % 250 + 1}",
                "acknowledged": False,
                "in_downtime": False,
                "notifications_enabled": True,
                "active_checks_enabled": True,
                "last_check": last_check,
                "next_check": last_check + 60,
                "last_state_change": now - (seed % 14400 + 60),
                "state_type": "HARD",
                "current_attempt": 1,
                "max_attempts": 3,
                "services_summary": summaries.get(name),
            }
            rows.append(row)
        return rows

    @override
    async def get_host_services(self, hostname: str, only_hard: bool = False) -> list[ServiceRow]:
        result: list[ServiceRow] = []
        for svc in _DEMO_SERVICES:
            state = await self.get_service_state(hostname, svc)
            result.append(ServiceRow(name=svc, state=state.state, output=state.output))
        return result

    @override
    async def search_services(
        self,
        *,
        host_terms: list[str],
        service_terms: list[str],
        any_terms: list[str],
        limit: int,
        only_hard: bool = False,
    ) -> list[ServiceMatchRow]:
        svc_lc = [t.lower() for t in service_terms]
        host_lc = [t.lower() for t in host_terms]
        any_lc = [t.lower() for t in any_terms]
        if not (svc_lc or host_lc or any_lc):
            return []
        out: list[ServiceMatchRow] = []
        for host in _DEMO_HOSTS:
            hl = host.lower()
            if not all(t in hl for t in host_lc):
                continue
            for svc in _DEMO_SERVICES:
                sl = svc.lower()
                if not all(t in sl for t in svc_lc):
                    continue
                if not all(t in hl or t in sl for t in any_lc):
                    continue
                state = await self.get_service_state(host, svc)
                out.append(
                    ServiceMatchRow(
                        host_name=host,
                        name=svc,
                        state=state.state,
                        output=state.output,
                        acknowledged=state.acknowledged,
                        in_downtime=state.in_downtime,
                        last_state_change=state.last_state_change,
                        site_id=_DEMO_HOST_PLACEMENT.get(host, ("", "local"))[1],
                    )
                )
                if len(out) > limit:
                    return out
        return out

    @override
    async def get_metric_history(
        self,
        host: str,
        service: str | None,
        start: int,
        end: int,
    ) -> MetricHistoryResult:
        """Generate synthetic time-varying metric history for development."""
        svc_key = f"{host}:{service or ''}"
        base_val = (abs(hash(f"{svc_key}val")) % 60 + 20) / 100  # 0.2 – 0.8

        step = max(60, (end - start) // 60)
        num_points = (end - start) // step

        cat = _classify_service(service or "")
        metric_defs = _CATEGORY_METRIC_DEFS.get(cat, _DEFAULT_METRIC_DEFS)

        series: dict[str, list[tuple[float, float, str]]] = {}
        titles: dict[str, str] = {}
        for label, phase, unit, scale in metric_defs:
            amplitude = base_val * 0.3
            points: list[tuple[float, float, str]] = []
            for j in range(num_points):
                ts = float(start + j * step)
                wave = math.sin(ts / 600 + phase) * amplitude
                trend = math.sin(ts / 3600) * amplitude * 0.5
                noise = ((hash(f"{ts:.0f}{label}") % 200) - 100) / 10000
                raw = max(0.0, base_val + wave + trend + noise)
                value = round(raw * scale, 4)
                points.append((ts, value, unit))
            series[label] = points
            titles[label] = " ".join(w.capitalize() for w in label.split("_"))

        return MetricHistoryResult(series=series, titles=titles)

    @override
    async def is_available(self) -> bool:
        return True
