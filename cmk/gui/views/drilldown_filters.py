#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The filters a drill-down may carry, each valued from the clicked row."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from cmk.gui.data_source import ABCDataSource
from cmk.gui.monitor.hosts import folder_path_from_filename
from cmk.gui.type_defs import ColumnName, ContextualLinkTargetType, FilterHTTPVariables, FilterName
from cmk.gui.utils.labels import filter_http_vars_for_simple_label_group
from cmk.gui.visuals.filter import filter_registry

type RowValues = Mapping[ColumnName, object]

# The hosts of one folder share their file, and a view may have thousands of rows.
_folder_path = lru_cache(maxsize=1024)(folder_path_from_filename)


_HOSTGROUP_PROBLEMS: Mapping[str, ColumnName] = {
    "hostgroups_having_hosts_down": "hostgroup_num_hosts_down",
    "hostgroups_having_hosts_unreach": "hostgroup_num_hosts_unreach",
    "hostgroups_having_hosts_pending": "hostgroup_num_hosts_pending",
    "hostgroups_having_services_warn": "hostgroup_num_services_warn",
    "hostgroups_having_services_crit": "hostgroup_num_services_crit",
    "hostgroups_having_services_pending": "hostgroup_num_services_pending",
    "hostgroups_having_services_unknown": "hostgroup_num_services_unknown",
}


@dataclass(frozen=True)
class RowFilter:
    """`variables` returns None when the row has no value; keys name the labels, tag groups or
    aux tags."""

    columns: Sequence[ColumnName]
    variables: Callable[[RowValues, Sequence[str]], FilterHTTPVariables | None]


def drilldown_filters(
    data_source: ABCDataSource, target_type: ContextualLinkTargetType
) -> list[FilterName]:
    return [
        filter_name
        for filter_name in ROW_FILTERS
        if (filter_ := filter_registry.get(filter_name)) is not None
        and filter_.available()
        and filter_.info in data_source.infos
        # A dashboard's context takes only host and service filters.
        and (target_type == "views" or filter_.info in ("host", "service"))
        # A Stats query counts log entries per object, so a log filter would split its counts.
        and not (filter_.info == "log" and "Stats:" in data_source.add_headers)
    ]


def _value(row: RowValues, column: ColumnName) -> str | None:
    value = row.get(column)
    return None if value is None or value == "" else str(value)


def _text(variable: str, column: ColumnName) -> RowFilter:
    def variables(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
        return None if (value := _value(row, column)) is None else {variable: value}

    return RowFilter(columns=[column], variables=variables)


def _checked_option(prefix: str, column: ColumnName) -> RowFilter:
    def variables(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
        return None if (value := _value(row, column)) is None else {f"{prefix}{value}": "on"}

    return RowFilter(columns=[column], variables=variables)


def _single_item(variable: str, column: ColumnName) -> RowFilter:
    def variables(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
        match row.get(column):
            case [str(value)]:
                return {variable: value}
            case _:
                return None

    return RowFilter(columns=[column], variables=variables)


def _state(prefix: str, object_type: Literal["host", "service"]) -> RowFilter:
    name = "host_name" if object_type == "host" else "service_description"
    state, has_been_checked = f"{object_type}_state", f"{object_type}_has_been_checked"

    def variables(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
        # A missing object comes with empty defaults, which would read as pending.
        if _value(row, name) is None or state not in row or has_been_checked not in row:
            return None
        if row[has_been_checked] != 1:
            return {f"{prefix}p": "on"}
        return {f"{prefix}{int(str(row[state]))}": "on"}

    return RowFilter(columns=[name, state, has_been_checked], variables=variables)


def _folder(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
    if (filename := _value(row, "host_filename")) is None or (
        folder := _folder_path(filename)
    ) is None:
        return None
    return {"wato_folder": folder}


def _labels(object_type: Literal["host", "service"]) -> RowFilter:
    column = f"{object_type}_labels"

    def variables(row: RowValues, keys: Sequence[str]) -> FilterHTTPVariables | None:
        labels = row.get(column)
        if not keys or not isinstance(labels, Mapping) or any(key not in labels for key in keys):
            return None
        return filter_http_vars_for_simple_label_group(
            [f"{key}:{labels[key]}" for key in keys], object_type
        )

    return RowFilter(columns=[column], variables=variables)


def _tags(object_type: Literal["host", "service"]) -> RowFilter:
    column = f"{object_type}_tags"

    def variables(row: RowValues, keys: Sequence[str]) -> FilterHTTPVariables | None:
        tags = row.get(column)
        if not keys or not isinstance(tags, Mapping) or any(group not in tags for group in keys):
            return None
        variables: dict[str, str] = {}
        for index, group in enumerate(keys):
            variables[f"{object_type}_tag_{index}_grp"] = group
            variables[f"{object_type}_tag_{index}_op"] = "is"
            variables[f"{object_type}_tag_{index}_val"] = str(tags[group])
        return variables

    return RowFilter(columns=[column], variables=variables)


def _aux_tags(row: RowValues, keys: Sequence[str]) -> FilterHTTPVariables | None:
    # An auxiliary tag sits among the host's tags with itself as its group.
    tags = row.get("host_tags")
    if (
        not keys
        or not isinstance(tags, Mapping)
        or any(tags.get(aux_tag) != aux_tag for aux_tag in keys)
    ):
        return None
    return {f"host_auxtags_{index}": aux_tag for index, aux_tag in enumerate(keys)}


def _log_contact_name(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
    # The column lists the notified contacts separated by commas.
    if (contacts := _value(row, "log_contact_name")) is None or "," in contacts:
        return None
    return {"log_contact_name": contacts}


def _log_state(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
    if (log_type := _value(row, "log_type")) is None or (state := _value(row, "log_state")) is None:
        return None
    if "SERVICE " in log_type:
        return {f"logst_s{state}": "on"}
    if "HOST " in log_type:
        return {f"logst_h{state}": "on"}
    return None


def _bi_state(prefix: str, column: ColumnName) -> RowFilter:
    def variables(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
        if column not in row:
            return None
        match row[column]:
            case {"state": int(state)}:
                return {f"{prefix}_filled": "1", f"{prefix}{state}": "on"}
            # Only the assumed-state filter has an option for an unset state.
            case None if prefix == "bias":
                return {f"{prefix}_filled": "1", f"{prefix}n": "on"}
            case _:
                return None

    return RowFilter(columns=[column], variables=variables)


def _event_contact_group(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
    column = (
        "event_contact_groups"
        if row.get("event_contact_groups_precedence") == "rule"
        else "host_contact_groups"
    )
    match row.get(column):
        case [str(group)]:
            return {"optevent_effective_contact_group": group}
        case _:
            return None


def _event_host_in_downtime(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
    match row.get("event_host_in_downtime"):
        case int(in_downtime):
            return {"is_event_host_in_downtime": "1" if in_downtime else "0"}
        case _:
            return None


def _hostgroup_problems(row: RowValues, _keys: Sequence[str]) -> FilterHTTPVariables | None:
    problems = {
        variable: "on"
        for variable, column in _HOSTGROUP_PROBLEMS.items()
        if isinstance(count := row.get(column), int) and count > 0
    }
    return problems or None


ROW_FILTERS: Mapping[FilterName, RowFilter] = {
    "siteopt": _text("site", "site"),
    "wato_folder": RowFilter(columns=["host_filename"], variables=_folder),
    "host": _text("host", "host_name"),
    "hoststate": _state("hst", "host"),
    "opthostgroup": _single_item("opthost_group", "host_groups"),
    "host_labels": _labels("host"),
    "host_tags": _tags("host"),
    "host_auxtags": RowFilter(columns=["host_tags"], variables=_aux_tags),
    "service": _text("service", "service_description"),
    "svcstate": _state("st", "service"),
    "optservicegroup": _single_item("optservice_group", "service_groups"),
    "service_labels": _labels("service"),
    "service_tags": _tags("service"),
    "log_class": _checked_option("logclass", "log_class"),
    "log_contact_name": RowFilter(columns=["log_contact_name"], variables=_log_contact_name),
    "log_state": RowFilter(columns=["log_type", "log_state"], variables=_log_state),
    "customer": _text("customer", "customer_id"),
    "aggr_state": _bi_state("birs", "aggr_state"),
    "aggr_name": _text("aggr_name", "aggr_name"),
    "aggr_assumed_state": _bi_state("bias", "aggr_assumed_state"),
    "aggr_effective_state": _bi_state("bies", "aggr_effective_state"),
    # Not aggr_group_tree, which matches paths only: a row's group may be a plain name.
    "aggr_group": _text("aggr_group", "aggr_group"),
    "optevent_effective_contactgroup": RowFilter(
        columns=["event_contact_groups", "event_contact_groups_precedence", "host_contact_groups"],
        variables=_event_contact_group,
    ),
    "event_id": _text("event_id", "event_id"),
    "event_host_in_downtime": RowFilter(
        columns=["event_host_in_downtime"], variables=_event_host_in_downtime
    ),
    "event_host": _text("event_host", "event_host"),
    "event_rule_id": _text("event_rule_id", "event_rule_id"),
    "event_phase": _checked_option("event_phase_", "event_phase"),
    "event_state": _checked_option("event_state_", "event_state"),
    "event_facility": _text("event_facility", "event_facility"),
    "event_priority": _checked_option("event_priority_", "event_priority"),
    "history_what": _checked_option("history_what_", "history_what"),
    "hostgroup": _text("hostgroup", "hostgroup_name"),
    "hostsgroups_having_problems": RowFilter(
        columns=list(_HOSTGROUP_PROBLEMS.values()), variables=_hostgroup_problems
    ),
    "servicegroupname": _text("servicegroup_name", "servicegroup_name"),
    "servicegroup": _text("servicegroup", "servicegroup_name"),
}
