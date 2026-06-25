#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from dataclasses import dataclass
from typing import TypedDict

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    LevelsT,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.graylog.lib import deserialize_and_merge_json, handle_iso_utc_to_localtimestamp

# <<<graylog_license>>>
# {"status": [{"violated": true,"expired": false,"expiration_upcoming":
# false,"expired_since": "PT0S","expires_in": "PT550H17.849S","trial":
# true,"license": {"version": 2,"id":
# "*********************************","issuer": "Graylog, Inc.","subject":
# "/license/enterprise","audience": {"company": "MYCOMPANY","name":
# "****************************","email":
# "*******************************"},"issue_date":
# "2019-09-23T05:00:00Z","expiration_date":
# "2019-10-24T04:59:59Z","not_before_date": "2019-09-23T05:00:00Z","trial":
# true,"enterprise": {"cluster_ids":
# ["***********************************************"],"number_of_nodes":
# 2147483647,"require_remote_check": true,"allowed_remote_check_failures":
# 120,"traffic_limit": 5368709120,"traffic_check_range":
# "PT720H","allowed_traffic_violations": 5,"expiration_warning_range":
# "PT240H"},"expired": false},"traffic_exceeded": false,"cluster_not_covered":
# false,"nodes_exceeded": false,"remote_checks_failed": true,"valid": false}]}


class LicenseParams(TypedDict):
    no_enterprise: int
    expired: int
    violated: int
    valid: int
    traffic_exceeded: int
    cluster_not_covered: int
    nodes_exceeded: int
    remote_checks_failed: int
    expiration: LevelsT[float]


@dataclass(frozen=True)
class Enterprise:
    require_remote_check: bool | None
    traffic_limit: float | None


@dataclass(frozen=True)
class License:
    subject: str | None
    trial: bool | None
    expiration_date: str | None
    enterprise: Enterprise


@dataclass(frozen=True)
class LicenseState:
    expired: bool | None
    violated: bool | None
    valid: bool | None
    traffic_exceeded: bool | None
    cluster_not_covered: bool | None
    nodes_exceeded: bool | None
    remote_checks_failed: bool | None
    license: License | None


@dataclass(frozen=True)
class Section:
    # None means the "status" key was absent from the agent output, an empty
    # list means there is no enterprise license installed.
    states: list[LicenseState] | None


def _parse_enterprise(value: object) -> Enterprise:
    match value:
        case {
            "require_remote_check": bool() | None as require_remote_check,
            "traffic_limit": int() | float() | None as traffic_limit,
        }:
            return Enterprise(
                require_remote_check=require_remote_check, traffic_limit=traffic_limit
            )
        case {"require_remote_check": bool() | None as require_remote_check}:
            return Enterprise(require_remote_check=require_remote_check, traffic_limit=None)
        case _:
            return Enterprise(require_remote_check=None, traffic_limit=None)


def _parse_license(value: object) -> License | None:
    match value:
        case {
            "subject": str() | None as subject,
            "trial": bool() | None as trial,
            "expiration_date": str() | None as expiration_date,
            **rest,
        }:
            return License(
                subject=subject,
                trial=trial,
                expiration_date=expiration_date,
                enterprise=_parse_enterprise(rest.get("enterprise")),
            )
        case _:
            return None


def _parse_license_state(entry: object) -> LicenseState:
    match entry:
        case {
            "expired": bool() | None as expired,
            "violated": bool() | None as violated,
            "valid": bool() | None as valid,
            "traffic_exceeded": bool() | None as traffic_exceeded,
            "cluster_not_covered": bool() | None as cluster_not_covered,
            "nodes_exceeded": bool() | None as nodes_exceeded,
            "remote_checks_failed": bool() | None as remote_checks_failed,
            **rest,
        }:
            return LicenseState(
                expired=expired,
                violated=violated,
                valid=valid,
                traffic_exceeded=traffic_exceeded,
                cluster_not_covered=cluster_not_covered,
                nodes_exceeded=nodes_exceeded,
                remote_checks_failed=remote_checks_failed,
                license=_parse_license(rest.get("license")),
            )
        case _:
            return LicenseState(
                expired=None,
                violated=None,
                valid=None,
                traffic_exceeded=None,
                cluster_not_covered=None,
                nodes_exceeded=None,
                remote_checks_failed=None,
                license=None,
            )


def parse_graylog_license(string_table: StringTable) -> Section:
    match deserialize_and_merge_json(string_table).get("status"):
        case list() as states_raw:
            return Section(states=[_parse_license_state(entry) for entry in states_raw])
        case _:
            return Section(states=None)


def discover_graylog_license(section: Section) -> DiscoveryResult:
    if section.states is not None:
        yield Service()


def check_graylog_license(params: LicenseParams, section: Section) -> CheckResult:
    if section.states is None:
        return

    # if no enterprise licence could be found
    if not section.states:
        yield Result(
            state=State(params["no_enterprise"]),
            summary="No enterprise license found",
        )
        return

    state = section.states[0]

    for value, expected, infotext, fail_state in [
        (state.expired, False, "Is expired", params["expired"]),
        (state.violated, False, "Is violated", params["violated"]),
        (state.valid, True, "Is valid", params["valid"]),
        (state.traffic_exceeded, False, "Traffic is exceeded", params["traffic_exceeded"]),
        (state.cluster_not_covered, False, "Cluster is not covered", params["cluster_not_covered"]),
        (state.nodes_exceeded, False, "Nodes exceeded", params["nodes_exceeded"]),
        (state.remote_checks_failed, False, "Remote checks failed", params["remote_checks_failed"]),
    ]:
        if value is not None:
            yield Result(
                state=State.OK if value == expected else State(fail_state),
                summary=f"{infotext}: {_yes_no(value)}",
            )

    if (license_info := state.license) is None:
        return

    if license_info.enterprise.traffic_limit is not None:
        yield Result(
            state=State.OK,
            summary=f"Traffic limit: {render.bytes(license_info.enterprise.traffic_limit)}",
        )

    if license_info.expiration_date is not None:
        timestamp = handle_iso_utc_to_localtimestamp(license_info.expiration_date)
        time_to_expiration = int(timestamp) - time.time()
        yield from check_levels(
            value=time_to_expiration,
            levels_lower=params["expiration"],
            render_func=render.time_offset,
            label="Expires in",
        )

    if license_info.subject is not None:
        yield Result(state=State.OK, summary=f"Subject: {license_info.subject}")

    if license_info.trial is not None:
        yield Result(state=State.OK, summary=f"Trial: {_yes_no(license_info.trial)}")

    if license_info.enterprise.require_remote_check is not None:
        yield Result(
            state=State.OK,
            summary=f"Requires remote checks: {_yes_no(license_info.enterprise.require_remote_check)}",
        )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


agent_section_graylog_license = AgentSection(
    name="graylog_license",
    parse_function=parse_graylog_license,
)


check_plugin_graylog_license = CheckPlugin(
    name="graylog_license",
    service_name="Graylog License",
    discovery_function=discover_graylog_license,
    check_function=check_graylog_license,
    check_ruleset_name="graylog_license",
    check_default_parameters={
        "no_enterprise": 0,
        "valid": 2,
        "cluster_not_covered": 1,
        "traffic_exceeded": 1,
        "violated": 2,
        "nodes_exceeded": 1,
        "expired": 2,
        "remote_checks_failed": 1,
        "expiration": ("no_levels", None),
    },
)
