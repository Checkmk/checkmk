#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Useful: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-w32t/123072f7-8031-4e17-b1ae-f1c04348332e

# Example output from agent (but note all strings and numbers are localized):
# <<<w32time_peers:sep(0)>>>
# #Peers: 2
#
# Peer: time.cloudflare.com
# State: Active
# Time Remaining: 29.4847157s
# Mode: 3 (Client)
# Stratum: 3 (secondary reference - syncd by (S)NTP)
# PeerPoll Interval: 17 (out of valid range)
# HostPoll Interval: 6 (64s)
# Last Successful Sync Time: 9/15/2025 12:05:55 AM
# LastSyncError: 0x00000000 (Succeeded)
# LastSyncErrorMsgId: 0x00000000 (Succeeded)
# AuthTypeMsgId: 0x0000005A (NoAuth )
# Resolve Attempts: 0
# ValidDataCounter: 1
# Reachability: 3
#
# Peer: time.facebook.com
# State: Active
# Time Remaining: 29.4945835s
# Mode: 3 (Client)
# Stratum: 1 (primary reference - syncd by radio clock)
# PeerPoll Interval: 17 (out of valid range)
# HostPoll Interval: 6 (64s)
# Last Successful Sync Time: 9/15/2025 12:05:55 AM
# LastSyncError: 0x00000000 (Succeeded)
# LastSyncErrorMsgId: 0x00000000 (Succeeded)
# AuthTypeMsgId: 0x0000005A (NoAuth )
# Resolve Attempts: 0
# ValidDataCounter: 1
# Reachability: 3


import time
from collections.abc import Iterable, MutableMapping, Sequence
from dataclasses import dataclass
from itertools import count
from typing import Literal, NotRequired, Self, TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    LevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)

from .w32time_lib import before_parens, in_parens, parse_float, parse_hex, parse_int


class DiscoveryParams(TypedDict):
    mode: Literal["summary", "single", "both", "neither"]


DEFAULT_DISCOVERY_PARAMS = DiscoveryParams(
    mode="summary",
)


class Params(TypedDict):
    reachability_consecutive_failures: LevelsT[int]
    reachability_total_failures: LevelsT[int]
    peer_never_synced_state: int
    peer_never_synced_levels: LevelsT[float]
    stratum: LevelsT[int]
    universal: NotRequired[bool]


DEFAULT_PARAMS = Params(
    reachability_consecutive_failures=("no_levels", None),
    reachability_total_failures=("no_levels", None),
    peer_never_synced_state=int(State.OK),
    peer_never_synced_levels=("fixed", (10 * 60.0, 30 * 60.0)),  # 10 minutes, 30 minutes
    stratum=("fixed", (5, 5)),
)


DEFAULT_SUMMARY_PARAMS: Params = {
    "universal": False,
    **DEFAULT_PARAMS,
}


@dataclass(frozen=True, kw_only=True)
class Reachability:
    total_failures: int
    consecutive_failures: int
    total_attempts: int

    @classmethod
    def from_raw(cls, raw_reachability: int, resolve_attempts: int) -> Self:
        if raw_reachability == 0:
            # In this case, we can't determine total attempts, because 0b0 == 0b00 == 0b00000000 == 0
            # so fall back to resolve_attempts instead.
            #
            # This lets someone still configure a meaningful "I want to alert after 3 failures", despite
            # the reachability only indicating one.
            return cls(
                total_failures=resolve_attempts,
                consecutive_failures=resolve_attempts,
                total_attempts=resolve_attempts,
            )
        # Given an integer representing reachability (an 8 bit shift register in NTP parlance),
        # compute how many failures have been seen in the last 8 connection attempts, and how many
        # have been recent, consecutive failures.
        #
        # There are surely faster ways to do this (with bit twiddling) than string manipulation,
        # but the binary representation will be <= 8 digits, so this will still be fast, and it's
        # more clear.
        binary = bin(raw_reachability)[2:]  # cut off the "0b" prefix
        consecutive_failures = len(binary) - len(binary.rstrip("0"))
        total_failures = binary.count("0")
        total_attempts = len(binary)
        return cls(
            total_failures=total_failures,
            consecutive_failures=consecutive_failures,
            total_attempts=total_attempts,
        )


@dataclass(frozen=True, kw_only=True)
class QueryPeers:
    peer: str  # peer name *as reported by Windows* (can be empty!)
    # state: str  # i18n, useless
    time_remaining: float
    stratum: int
    last_successful_sync_time: str  # Can't parse due to i18n, but useful for summary and (null)
    # This is localized, but sometimes the only useful error message.
    last_sync_error_str: str
    last_sync_error_msg: str | None
    raw_reachability: int
    reachability: Reachability

    @classmethod
    def from_peer_lines(cls, peer_lines: Sequence[str]) -> Self:
        _validate_peer_parse(peer_lines)
        resolve_attempts = parse_int(peer_lines[11])
        raw_reachability = parse_int(peer_lines[13])
        reachability = Reachability.from_raw(raw_reachability, resolve_attempts)
        return cls(
            peer=peer_lines[0],
            time_remaining=parse_float(peer_lines[2]),
            stratum=parse_int(before_parens(peer_lines[4])),
            last_successful_sync_time=peer_lines[7],
            last_sync_error_str=in_parens(peer_lines[8]).strip(),
            last_sync_error_msg=_error_msg_id_to_str(parse_hex(before_parens(peer_lines[9]))),
            raw_reachability=raw_reachability,
            reachability=reachability,
        )


def _error_msg_id_to_str(msg_id: int) -> str | None:
    """
    Roughly map error message ids to a string, per the table here:
    https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-w32t/bb576d39-587b-484a-86a4-e1d378cf9497#Appendix_A_29
    """
    match msg_id:
        case 0:
            return None
        case 0x0000005C:
            return "The peer is unreachable."
        case 0x0000005E:
            return "Duplicate timestamps were received from peer"
        case 0x0000005F:
            return "Message was received out of order"
        case 0x00000060:
            return "Peer is not synchronized or reachability was lost"
        case 0x00000061:
            return "Round-trip delay was too large"
        case 0x00000062:
            return "Packet was not authenticated"
        case 0x00000063:
            return "Peer is not synchronized"
        case 0x00000064:
            return "Peer stratum is less than host stratum"
        case 0x00000065:
            return "Unreasonable root delay or root dispersion"
        case 0x00000070:
            return "Peer is unresolved"
        case _:
            return "Unknown error"


def _validate_peer_parse(peer_lines: Sequence[str]) -> None:
    """
    During parsing, each peer is expected to have exactly 14 lines.
    If this is never not the case, it means something failed to parse correctly
    or the output format changed or was somehow different than we've seen
    before. In that case, we error out so we can get a crash report and fix it.
    """
    line_count = len(peer_lines)
    if line_count == 14:
        return
    problem = "more" if line_count > 14 else "less"
    raise ValueError(f"Peer parsed to {problem} than 14 lines: {peer_lines!r}")


def parse_w32time_peers(string_table: StringTable) -> dict[str, QueryPeers]:
    peers = {}

    # In some (broken?) setups, the peer name can be empty!
    # In this case, we itemize it as something like "(unnamed peer 1)"
    # We store the (empty) peer name in the QueryPeers object so we can later
    # check that field (in the check functions) and act on it.
    nameless_peers_counter = count(1)

    def save_peer(peer_lines: list[str]) -> None:
        query_peers = QueryPeers.from_peer_lines(peer_lines)
        itemized_name = peer_lines[0] or f"(unnamed peer {next(nameless_peers_counter)})"

        # NOTE: We drop duplicate peer entries even though they can appear in
        # the output. Normally, a duplicate will appear in the situation where a
        # peer is configured by hostname, it has multiple DNS records which are
        # *not* NTP servers. In this case, a record exists for each DNS entry.
        # In properly configured pools and servers, only one entry will appear
        # for each, so we assume this green path here, for better or worse.
        peers[itemized_name] = query_peers

    peer_lines: list[str] = []
    for row in string_table[2:]:  # Skip the peer count line, and the first separator
        line = " ".join(row)
        if line == "---":  # If we get this, it means a new peer is starting - save the previous one
            save_peer(peer_lines)
            peer_lines = []
        elif ":" not in line:
            continue
        else:
            value = line.split(":", 1)
            peer_lines.append(value[1].strip())

    # At the very end, we don't get a final "---" so we have to add the last peer
    # explicitly, if there are any lines left over
    if peer_lines:
        save_peer(peer_lines)

    return peers


agent_section_w32time_peers = AgentSection(
    name="w32time_peers",
    parse_function=parse_w32time_peers,
)


def discover_w32time_peers(
    params: DiscoveryParams,
    section: dict[str, QueryPeers],
) -> DiscoveryResult:
    if params["mode"] in ("neither", "summary"):
        return

    for peer, data in section.items():
        yield Service(item=peer)


def discover_w32time_peers_summary(
    params: DiscoveryParams,
    section: dict[str, QueryPeers],
) -> DiscoveryResult:
    if params["mode"] in ("neither", "single") or not section:
        return

    yield Service()


def _never_synced_vs_key(peer_name: str) -> str:
    return f"{peer_name}:last_successful_sync_time_null"


def _last_successful_sync_time(
    peer: QueryPeers,
    state_if_null: State,
    peer_never_synced_levels: LevelsT[float] | None,
    now: float,
    value_store: MutableMapping[str, object],
    notice_only: bool = False,
) -> Iterable[Result]:
    """
    The value of "Last Successful Sync Time" is internationalized and cannot
    normally be parsed. However testing shows that when it is "(null)" that
    string is consistent across languages.

    When it is "(null)" it means that the peer has not synced yet. As far as we
    are concerned, the state of the peer is genuinely unknown: for example,
    w32time could have just started and the peer didn't sync yet.

    It being "(null)" on its own is not necessarily cause for alarm (thus we let
    the user select the default state in this condition). But it *staying* as
    "(null)" for a long time could indicate a legitimate issue. So we also allow
    the user to set levels for how long the peer can stay in "(null)" before we
    alert.
    """
    vs_key = _never_synced_vs_key(peer.peer)
    if peer.last_successful_sync_time == "(null)":
        first_seen = value_store.setdefault(vs_key, now)
        if not isinstance(first_seen, int | float):
            # Nothing else writes this key, so this should not happen. Recover
            # by restarting the grace period instead of crashing.
            first_seen = now
            value_store[vs_key] = first_seen
        elapsed = now - first_seen
        for result in check_levels(
            value=elapsed,
            render_func=render.timespan,
            label="Peer has not synced yet, time in this state",
            levels_upper=peer_never_synced_levels,
            notice_only=notice_only,
        ):
            if not isinstance(result, Result):
                continue  # mypy
            state = state_if_null if result.state is State.OK else result.state
            if notice_only:
                yield Result(state=state, notice=result.details)
            else:
                yield Result(state=state, summary=result.details)
        return

    # Not "(null)" (anymore): clear any recorded first-seen timestamp.
    value_store.pop(vs_key, None)

    text = f"Last successful sync time: {peer.last_successful_sync_time}"
    if notice_only:
        yield Result(state=State.OK, notice=text)
    else:
        yield Result(state=State.OK, summary=text)


def _reachability_summary(peer: QueryPeers) -> str:
    # If there are 8 here, we probably cut off earlier attempts since the reachability
    # is a bit-shift register. So add the word "last" to indicate that.
    # If raw_reachability is 0, we fell back to Resolve Attempts.
    return (
        f"({peer.reachability.total_attempts} attempts)"
        if peer.raw_reachability == 0 or peer.reachability.total_attempts < 8
        else f"(last {peer.reachability.total_attempts} attempts)"
    )


def _reachability_total_failures(peer: QueryPeers, levels: LevelsT[int] | None) -> Iterable[Result]:
    result = check_levels(
        value=peer.reachability.total_failures,
        render_func=str,
        notice_only=True,
        label=f"Total failures {_reachability_summary(peer)}",
        levels_upper=levels,
    )
    yield from (r for r in result if isinstance(r, Result))  # for mypy's sake


def _reachability_consecutive_failures(
    peer: QueryPeers, levels: LevelsT[int] | None
) -> Iterable[Result]:
    result = check_levels(
        value=peer.reachability.consecutive_failures,
        render_func=str,
        notice_only=True,
        label=f"Consecutive failures {_reachability_summary(peer)}",
        levels_upper=levels,
    )
    yield from (r for r in result if isinstance(r, Result))  # for mypy's sake


def _last_sync_failure(peer: QueryPeers, notice_only: bool = False) -> Iterable[Result]:
    # These error codes seem to be for the last sync attempt (only)
    # https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-w32t/28e3c644-cb9d-4925-8c80-288f6339d9e0
    if peer.reachability.consecutive_failures != 0:
        if peer.last_sync_error_msg is not None:
            summary = f"Last sync error: {peer.last_sync_error_msg}"
            # We use state OK here because we're just doing this to display more information
            # in the summary, *not* for alerting which is handled above.
            if notice_only:
                yield Result(state=State.OK, notice=summary)
            else:
                yield Result(state=State.OK, summary=summary)

        # This seems separate and maybe more general than the one above?
        # This is not very well documented and we're just relying on the w32tm representation
        # of the error code, here. It's likely localized, too, which is non-ideal. :(
        notice = f"Details from w32tm: {peer.last_sync_error_str}"
        yield Result(state=State.OK, notice=notice)


def _stratum(
    peer: QueryPeers, levels: LevelsT[int] | None, notice_only: bool = False
) -> Iterable[Result]:
    result = check_levels(
        value=peer.stratum,
        render_func=str,
        label="Stratum",
        levels_upper=levels,
        notice_only=notice_only,
    )
    yield from (r for r in result if isinstance(r, Result))  # for mypy's sake


def _next_poll(peer: QueryPeers, notice_only: bool = False) -> Iterable[Result]:
    result = check_levels(
        value=peer.time_remaining,
        render_func=render.timespan,
        label="Next poll in",
        notice_only=notice_only,
    )
    yield from (r for r in result if isinstance(r, Result))  # for mypy's sake


def _check_w32time_peers(
    item: str,
    params: Params,
    section: dict[str, QueryPeers],
    now: float,
    value_store: MutableMapping[str, object],
) -> CheckResult:
    if item not in section:
        return

    peer = section[item]

    if peer.peer == "":
        # Windows reported a peer with no name, likely due to a bad
        # configuration w.r.t NT5DS. In this case, the metrics are always all
        # 0, so there is nothing useful to report.
        yield Result(state=State.WARN, summary="Peer with no name found!")
        return

    yield from _last_successful_sync_time(
        peer,
        State(params["peer_never_synced_state"]),
        params["peer_never_synced_levels"],
        now,
        value_store,
    )

    yield from _reachability_total_failures(peer, params.get("reachability_total_failures"))
    yield from _reachability_consecutive_failures(
        peer, params.get("reachability_consecutive_failures")
    )
    yield from _last_sync_failure(peer)
    yield from _stratum(peer, params.get("stratum"))
    yield from _next_poll(peer)


def check_w32time_peers(
    item: str,
    params: Params,
    section: dict[str, QueryPeers],
) -> CheckResult:
    yield from _check_w32time_peers(
        item, params, section, now=time.time(), value_store=get_value_store()
    )


def _check_w32time_peers_summary(
    params: Params,
    section: dict[str, QueryPeers],
    now: float,
    value_store: MutableMapping[str, object],
) -> CheckResult:
    """
    A singular summary check service which encapsulates all Windows Time Service
    peers into one service.

    The levels for reachability (total), reachability (consecutive), and stratum
    are applied to all peers.

    The check can be configured to alert if ALL peers are non-OK (i.e. they go
    WARN or CRIT or UNKN), or to alert if ANY peer is non-OK.

    In the code, we call the "ALL peers must be non-OK to alert" mode
    "universal" mode since (∀peer. peer is failed) vs "existential mode" where
    (∃peer. peer is failed).
    """

    peer_count = len(section)

    # Drop never-synced timestamps of peers that no longer exist, so removed
    # peers do not accumulate in the value store forever.
    known_keys = {_never_synced_vs_key(peer.peer) for peer in section.values()}
    for stale_key in [
        key
        for key in value_store
        if key.endswith(":last_successful_sync_time_null") and key not in known_keys
    ]:
        value_store.pop(stale_key)

    def emit_possibly_suppressed(
        peername: str,
        results: list[Result],
        suppressing: bool,
    ) -> Iterable[Result]:
        for result in results:
            # Prefix with hostname so the summary line identifies the peer when this result is
            # non-OK. For OK results, details takes precedence and the hostname is intentionally
            # omitted; the preceding "\nPeer: {name}" line provides the grouping context.
            notice = f"{peername}: {result.details}"
            details = result.details
            if result.state is not State.OK and suppressing:
                details += " (alerts suppressed)"

            state = State.OK if suppressing else result.state
            yield Result(state=state, notice=notice, details=details)

    # Keyed on peer name
    reachability_total_failures_results: dict[str, list[Result]] = {}
    reachability_consecutive_failures_results: dict[str, list[Result]] = {}
    stratum_results: dict[str, list[Result]] = {}
    never_synced_results: dict[str, list[Result]] = {}

    # So we can count how many peers have at least one non-ok result.
    non_ok_peers: set[str] = set()
    # We do not suppress alerts in this case, we need to know if we should hide
    # that message or not, so track missing-name peers.
    missing_name_peers = 0

    # State for peers which have never synced and have not yet tripped the
    # levels check (it must be in a "bad" state for a while before we alert).
    never_synced_state = State(params["peer_never_synced_state"])

    # We need to calculate the results of these checks before we yield any
    # Results because this is the only way we know if we need to suppress alerts
    # or not.
    #
    # We store the results keyed on host so we can yield them for the correct
    # host later, and if there are any failures, we note that, so we can track
    # how many peers have failed in total.
    alertable_checks = [
        (
            _reachability_total_failures,
            "reachability_total_failures",
            reachability_total_failures_results,
        ),
        (
            _reachability_consecutive_failures,
            "reachability_consecutive_failures",
            reachability_consecutive_failures_results,
        ),
        (
            lambda peers, levels: _stratum(peers, levels, True),
            "stratum",
            stratum_results,
        ),
        (
            lambda peer, levels: _last_successful_sync_time(
                peer,
                never_synced_state,
                peer_never_synced_levels=levels,
                now=now,
                value_store=value_store,
                notice_only=True,
            ),
            "peer_never_synced_levels",
            never_synced_results,
        ),
    ]
    for name, peer in section.items():
        if peer.peer == "":
            # We handle this separately when yielding, so skip checks
            # but add it to the list of non-ok peers so the failed count shows it
            non_ok_peers.add(name)
            missing_name_peers += 1
            continue

        for check_fn, param, results_dict in alertable_checks:
            results = list(check_fn(peer, params.get(param)))
            results_dict[name] = results
            if any(result.state is not State.OK for result in results):
                non_ok_peers.add(name)

    peer_or_peers = "peer" if peer_count == 1 else "peers"
    yield Result(state=State.OK, summary=f"Found {peer_count} {peer_or_peers}")

    # If we're in "universal" mode, but not every peer has failed, then by
    # by definition, we are suppressing alerts.
    #
    # missing_name_peers is counted separately from non_ok_peers for 2 reasons:
    #   1. Because we want to be able to aggregate it and say "N peers with
    #      no name found!"
    #   2. Because we want to alert on it independently of non_ok_peers. It
    #      effectively overrides the suppression logic; if a peer has no name,
    #      we always alert on it.
    suppressing = (
        params.get("universal", False)
        and len(non_ok_peers) != peer_count
        and missing_name_peers == 0
    )

    failed_summary = f"Failed: {len(non_ok_peers)}"
    if suppressing and non_ok_peers:
        failed_summary += " (alerts suppressed)"
    yield Result(state=State.OK, summary=failed_summary)

    if missing_name_peers:
        # Windows reported a peer with no name, likely due to a bad
        # configuration w.r.t NT5DS.
        peer_or_peers = "peer" if missing_name_peers == 1 else "peers"
        yield Result(
            state=State.WARN, summary=f"{missing_name_peers} {peer_or_peers} with no name found!"
        )

    for name, peer in section.items():
        if peer.peer == "":
            # Handled above. Skip metrics, everything is 0 in this case anyway
            continue

        yield Result(state=State.OK, notice=f"\nPeer: {name}")
        yield from emit_possibly_suppressed(name, never_synced_results[name], suppressing)
        yield from emit_possibly_suppressed(
            name, reachability_total_failures_results[name], suppressing
        )
        yield from emit_possibly_suppressed(
            name, reachability_consecutive_failures_results[name], suppressing
        )
        yield from _last_sync_failure(peer, notice_only=True)
        yield from emit_possibly_suppressed(name, stratum_results[name], suppressing)
        yield from _next_poll(peer, notice_only=True)


def check_w32time_peers_summary(
    params: Params,
    section: dict[str, QueryPeers],
) -> CheckResult:
    yield from _check_w32time_peers_summary(
        params,
        section,
        now=time.time(),
        value_store=get_value_store(),
    )


check_plugin_w32time_peers = CheckPlugin(
    name="w32time_peers",
    service_name="Windows time service peer %s",
    discovery_function=discover_w32time_peers,
    discovery_default_parameters=DEFAULT_DISCOVERY_PARAMS,
    discovery_ruleset_name="ntp_discovery",
    check_ruleset_name="w32time_peers",
    check_default_parameters=DEFAULT_PARAMS,
    check_function=check_w32time_peers,
)


check_plugin_w32time_peers_summary = CheckPlugin(
    name="w32time_peers_summary",
    service_name="Windows time service peers",
    sections=["w32time_peers"],
    discovery_function=discover_w32time_peers_summary,
    discovery_default_parameters=DEFAULT_DISCOVERY_PARAMS,
    discovery_ruleset_name="ntp_discovery",
    check_ruleset_name="w32time_peers_summary",
    check_default_parameters=DEFAULT_SUMMARY_PARAMS,
    check_function=check_w32time_peers_summary,
)
