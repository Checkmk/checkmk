#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from datetime import datetime, tzinfo, UTC
from typing import Any, NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    render,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib import sap_hana

# Black magic alert: could return None in some cases, but the offset seems to be
# magically calculated based on local systemtime...
LOCAL_TIMEZONE = datetime.now(tz=UTC).astimezone().tzinfo


class Backup(NamedTuple):
    end_time: datetime | None = None
    state_name: str | None = None
    comment: str | None = None
    message: str | None = None

    def is_empty(self) -> bool:
        return all(value is None for value in self)


Section = Mapping[str, Backup]


def _backup_timestamp(backup_time_readable: str, tz: tzinfo | None) -> datetime | None:
    """
    >>> from datetime import datetime, timedelta, timezone

    >>> _backup_timestamp("", timezone.utc) is None
    True
    >>> _backup_timestamp("???", timezone.utc) is None
    True

    >>> _backup_timestamp("2022-05-20 08:00:00", timezone.utc)
    datetime.datetime(2022, 5, 20, 8, 0, tzinfo=datetime.timezone.utc)

    >>> _backup_timestamp("2022-05-20 08:00:00", timezone(timedelta(seconds=7200), 'CEST'))
    datetime.datetime(2022, 5, 20, 8, 0, tzinfo=datetime.timezone(datetime.timedelta(seconds=7200), 'CEST'))
    """

    try:
        return datetime.strptime(backup_time_readable, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
    except ValueError:
        return None


def _parse_sap_hana_backup(string_table: StringTable, timezone_info: tzinfo | None) -> Section:
    parsed: dict[str, Backup] = {}
    for sid_instance, lines in sap_hana.parse_sap_hana(string_table).items():
        if len(lines) == 0:
            parsed[sid_instance] = Backup()
        for line in lines:
            if len(line) < 5:
                continue

            parsed.setdefault(
                f"{sid_instance} - {line[0]}",
                Backup(
                    end_time=_backup_timestamp(line[1].rsplit(".", 1)[0], timezone_info),
                    state_name=line[2],
                    comment=line[3],
                    message=line[4],
                ),
            )
    return parsed


def parse_sap_hana_backup(string_table: StringTable) -> Section:
    # This is maintained for pre-fix compatibility reasons, to avoid
    # forcing users to roll out the agent plug-in. The implementation
    # works in cases when the monitoring server and SAP Hana server are
    # in the same timezone.
    return _parse_sap_hana_backup(string_table, LOCAL_TIMEZONE)


def parse_sap_hana_backup_v2(string_table: StringTable) -> Section:
    return _parse_sap_hana_backup(string_table, UTC)


agent_section_sap_hana_backup = AgentSection(
    name="sap_hana_backup",
    parse_function=parse_sap_hana_backup,
)

agent_section_sap_hana_backup_v2 = AgentSection(
    name="sap_hana_backup_v2",
    parsed_section_name="sap_hana_backup",
    parse_function=parse_sap_hana_backup_v2,
)


def discovery_sap_hana_backup(section: Section) -> DiscoveryResult:
    for sid in section:
        yield Service(item=sid)


def check_sap_hana_backup(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    data = section.get(item)
    if not data or data.is_empty():
        raise IgnoreResultsError("Login into database failed.")

    if not data.state_name:
        yield Result(state=State.WARN, summary="No backup found")
        return

    if data.state_name == "failed":
        cur_state = State.CRIT
    elif data.state_name in ["cancel pending", "canceled"]:
        cur_state = State.WARN
    elif data.state_name in ["ok", "successful", "running"]:
        cur_state = State.OK
    else:
        cur_state = State.UNKNOWN
    yield Result(state=cur_state, summary="Status: %s" % data.state_name)

    if data.end_time is not None:
        yield Result(
            state=State.OK, summary="Last: %s" % render.datetime(data.end_time.timestamp())
        )
        yield from check_levels_v1(
            (datetime.now(tz=UTC) - data.end_time).total_seconds(),
            metric_name="backup_age",
            levels_upper=params["backup_age"],
            render_func=render.timespan,
            label="Age",
        )

    if data.comment:
        yield Result(state=State.OK, summary="Comment: %s" % data.comment)

    if data.message:
        yield Result(state=State.OK, summary="Message: %s" % data.message)


def cluster_check_sap_hana_backup(
    item: str,
    params: Mapping[str, Any],
    section: Mapping[str, Section | None],
) -> CheckResult:
    # TODO: This is *not* a real cluster check. We do not evaluate the different node results with
    # each other, but this was the behaviour before the migration to the new Check API.
    yield Result(state=State.OK, summary="Nodes: %s" % ", ".join(section.keys()))
    for node_section in [s for s in section.values() if s is not None]:
        if item in node_section:
            yield from check_sap_hana_backup(item, params, node_section)
            return
    # If the item is not found in the section, then the service should be reported as stale
    # SUP-10479
    raise IgnoreResultsError("Login into database failed.")


check_plugin_sap_hana_backup = CheckPlugin(
    name="sap_hana_backup",
    service_name="SAP HANA Backup %s",
    discovery_function=discovery_sap_hana_backup,
    check_default_parameters={"backup_age": (24 * 60 * 60, 2 * 24 * 60 * 60)},
    check_ruleset_name="sap_hana_backup",
    check_function=check_sap_hana_backup,
    cluster_check_function=cluster_check_sap_hana_backup,
)
