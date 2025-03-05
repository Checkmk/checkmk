#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import time
from collections.abc import Mapping, Sequence
from typing import Any, Literal

import cmk.gui.utils as utils
from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.site_config import get_site_config
from cmk.gui.type_defs import ColumnName, ColumnSpec, Row
from cmk.gui.valuespec import Dictionary, DropdownChoice
from cmk.gui.view_utils import get_labels

from ..painter.v0.helpers import get_tag_groups
from ..painter.v1.helpers import get_perfdata_nth_value
from .base import ParameterizedSorter, Sorter
from .helpers import (
    cmp_custom_variable,
    cmp_insensitive_string,
    cmp_ip_address,
    cmp_num_split,
    cmp_service_name_equiv,
    cmp_simple_number,
    cmp_simple_string,
    cmp_string_list,
    compare_ips,
)
from .registry import declare_1to1_sorter, declare_simple_sorter, SorterRegistry


def register_sorters(registry: SorterRegistry) -> None:
    registry.register(SorterSvcstate)
    registry.register(SorterHoststate)
    registry.register(SorterSiteHost)
    registry.register(SorterHostName)
    registry.register(SorterSitealias)
    registry.register(SorterHost)
    registry.register(SorterServiceTags)
    registry.register(SorterHostLabels)
    registry.register(SorterServiceLabels)
    registry.register(SorterServicelevel)
    registry.register(SorterSvcPerfVal01)
    registry.register(SorterSvcPerfVal02)
    registry.register(SorterSvcPerfVal03)
    registry.register(SorterSvcPerfVal04)
    registry.register(SorterSvcPerfVal05)
    registry.register(SorterSvcPerfVal06)
    registry.register(SorterSvcPerfVal07)
    registry.register(SorterSvcPerfVal08)
    registry.register(SorterSvcPerfVal09)
    registry.register(SorterSvcPerfVal10)
    registry.register(SorterCustomHostVariable)
    registry.register(SorterHostIpv4Address)
    registry.register(SorterHostIpv6Address)
    registry.register(SorterHostIpAddresses)
    registry.register(SorterNumProblems)

    declare_simple_sorter(
        "svcdescr", _("Service description"), "service_description", cmp_service_name
    )
    declare_simple_sorter(
        "svcdispname",
        _("Service alternative display name"),
        "service_display_name",
        cmp_simple_string,
    )
    declare_simple_sorter("svcoutput", _("Summary"), "service_plugin_output", cmp_simple_string)
    declare_simple_sorter(
        "svc_long_plugin_output",
        _("Long output of check plugin"),
        "service_long_plugin_output",
        cmp_simple_string,
    )
    declare_simple_sorter("site", _("Site"), "site", cmp_simple_string)
    declare_simple_sorter(
        "stateage", _("Service state age"), "service_last_state_change", cmp_simple_number
    )
    declare_simple_sorter(
        "servicegroup", _("Service group"), "servicegroup_alias", cmp_simple_string
    )
    declare_simple_sorter("hostgroup", _("Host group"), "hostgroup_alias", cmp_simple_string)

    # Alerts
    declare_1to1_sorter("alert_stats_crit", cmp_simple_number, reverse=True)
    declare_1to1_sorter("alert_stats_unknown", cmp_simple_number, reverse=True)
    declare_1to1_sorter("alert_stats_warn", cmp_simple_number, reverse=True)
    declare_1to1_sorter("alert_stats_problem", cmp_simple_number, reverse=True)

    # Service
    declare_1to1_sorter("svc_check_command", cmp_simple_string)
    declare_1to1_sorter("svc_contacts", cmp_string_list)
    declare_1to1_sorter("svc_contact_groups", cmp_string_list)
    declare_1to1_sorter("svc_check_age", cmp_simple_number, col_num=1)
    declare_1to1_sorter("svc_next_check", cmp_simple_number, reverse=True)
    declare_1to1_sorter("svc_next_notification", cmp_simple_number, reverse=True)
    declare_1to1_sorter("svc_last_notification", cmp_simple_number)
    declare_1to1_sorter("svc_check_latency", cmp_simple_number)
    declare_1to1_sorter("svc_check_duration", cmp_simple_number)
    declare_1to1_sorter("svc_attempt", cmp_simple_number)
    declare_1to1_sorter("svc_check_type", cmp_simple_number)
    declare_1to1_sorter("svc_in_downtime", cmp_simple_number)
    declare_1to1_sorter("svc_in_notifper", cmp_simple_number)
    declare_1to1_sorter("svc_notifper", cmp_simple_string)
    declare_1to1_sorter("svc_flapping", cmp_simple_number)
    declare_1to1_sorter("svc_notifications_enabled", cmp_simple_number)
    declare_1to1_sorter("svc_is_active", cmp_simple_number)
    declare_1to1_sorter("svc_group_memberlist", cmp_string_list)
    declare_1to1_sorter("svc_acknowledged", cmp_simple_number)
    declare_1to1_sorter("svc_staleness", cmp_simple_number)
    declare_1to1_sorter("svc_servicelevel", cmp_simple_number)

    # Host
    declare_1to1_sorter("alias", cmp_num_split)
    declare_1to1_sorter("host_address", cmp_ip_address)
    declare_1to1_sorter("host_address_family", cmp_simple_number)
    declare_1to1_sorter("host_plugin_output", cmp_simple_string)
    declare_1to1_sorter("host_perf_data", cmp_simple_string)
    declare_1to1_sorter("host_check_command", cmp_simple_string)
    declare_1to1_sorter("host_state_age", cmp_simple_number, col_num=1)
    declare_1to1_sorter("host_check_age", cmp_simple_number, col_num=1)
    declare_1to1_sorter("host_next_check", cmp_simple_number, reverse=True)
    declare_1to1_sorter("host_next_notification", cmp_simple_number, reverse=True)
    declare_1to1_sorter("host_last_notification", cmp_simple_number)
    declare_1to1_sorter("host_check_latency", cmp_simple_number)
    declare_1to1_sorter("host_check_duration", cmp_simple_number)
    declare_1to1_sorter("host_attempt", cmp_simple_number)
    declare_1to1_sorter("host_check_type", cmp_simple_number)
    declare_1to1_sorter("host_in_notifper", cmp_simple_number)
    declare_1to1_sorter("host_notifper", cmp_simple_string)
    declare_1to1_sorter("host_flapping", cmp_simple_number)
    declare_1to1_sorter("host_is_active", cmp_simple_number)
    declare_1to1_sorter("host_in_downtime", cmp_simple_number)
    declare_1to1_sorter("host_acknowledged", cmp_simple_number)
    declare_1to1_sorter("num_services", cmp_simple_number)
    declare_1to1_sorter("num_services_ok", cmp_simple_number)
    declare_1to1_sorter("num_services_warn", cmp_simple_number)
    declare_1to1_sorter("num_services_crit", cmp_simple_number)
    declare_1to1_sorter("num_services_unknown", cmp_simple_number)
    declare_1to1_sorter("num_services_pending", cmp_simple_number)
    declare_1to1_sorter("host_parents", cmp_string_list)
    declare_1to1_sorter("host_childs", cmp_string_list)
    declare_1to1_sorter("host_group_memberlist", cmp_string_list)
    declare_1to1_sorter("host_contacts", cmp_string_list)
    declare_1to1_sorter("host_contact_groups", cmp_string_list)
    declare_1to1_sorter("host_servicelevel", cmp_simple_number)

    # Host group
    declare_1to1_sorter("hg_num_services", cmp_simple_number)
    declare_1to1_sorter("hg_num_services_ok", cmp_simple_number)
    declare_1to1_sorter("hg_num_services_warn", cmp_simple_number)
    declare_1to1_sorter("hg_num_services_crit", cmp_simple_number)
    declare_1to1_sorter("hg_num_services_unknown", cmp_simple_number)
    declare_1to1_sorter("hg_num_services_pending", cmp_simple_number)
    declare_1to1_sorter("hg_num_hosts_up", cmp_simple_number)
    declare_1to1_sorter("hg_num_hosts_down", cmp_simple_number)
    declare_1to1_sorter("hg_num_hosts_unreach", cmp_simple_number)
    declare_1to1_sorter("hg_num_hosts_pending", cmp_simple_number)
    declare_1to1_sorter("hg_name", cmp_simple_string)
    declare_1to1_sorter("hg_alias", cmp_simple_string)

    # Service group
    declare_1to1_sorter("sg_num_services", cmp_simple_number)
    declare_1to1_sorter("sg_num_services_ok", cmp_simple_number)
    declare_1to1_sorter("sg_num_services_warn", cmp_simple_number)
    declare_1to1_sorter("sg_num_services_crit", cmp_simple_number)
    declare_1to1_sorter("sg_num_services_unknown", cmp_simple_number)
    declare_1to1_sorter("sg_num_services_pending", cmp_simple_number)
    declare_1to1_sorter("sg_name", cmp_simple_string)
    declare_1to1_sorter("sg_alias", cmp_simple_string)

    # Comments
    declare_1to1_sorter("comment_id", cmp_simple_number)
    declare_1to1_sorter("comment_author", cmp_simple_string)
    declare_1to1_sorter("comment_comment", cmp_simple_string)
    declare_1to1_sorter("comment_time", cmp_simple_number)
    declare_1to1_sorter("comment_expires", cmp_simple_number, reverse=True)
    declare_1to1_sorter("comment_what", cmp_simple_number)
    declare_simple_sorter("comment_type", _("Comment type"), "comment_type", cmp_simple_number)

    # Downtimes
    declare_1to1_sorter("downtime_id", cmp_simple_number)
    declare_1to1_sorter("downtime_author", cmp_simple_string)
    declare_1to1_sorter("downtime_comment", cmp_simple_string)
    declare_1to1_sorter("downtime_fixed", cmp_simple_number)
    declare_1to1_sorter("downtime_type", cmp_simple_number)
    declare_simple_sorter(
        "downtime_what", _("Downtime for host/service"), "downtime_is_service", cmp_simple_number
    )
    declare_simple_sorter(
        "downtime_start_time", _("Downtime start"), "downtime_start_time", cmp_simple_number
    )
    declare_simple_sorter(
        "downtime_end_time", _("Downtime end"), "downtime_end_time", cmp_simple_number
    )
    declare_simple_sorter(
        "downtime_entry_time", _("Downtime entry time"), "downtime_entry_time", cmp_simple_number
    )

    # Log
    declare_1to1_sorter("log_plugin_output", cmp_simple_string)
    declare_1to1_sorter("log_attempt", cmp_simple_string)
    declare_1to1_sorter("log_state_type", cmp_simple_string)
    declare_1to1_sorter("log_state_info", cmp_simple_string)
    declare_1to1_sorter("log_type", cmp_simple_string)
    declare_1to1_sorter("log_contact_name", cmp_simple_string)
    declare_1to1_sorter("log_time", cmp_simple_number)
    declare_1to1_sorter("log_lineno", cmp_simple_number)

    declare_1to1_sorter("log_what", cmp_log_what)

    declare_1to1_sorter("log_date", cmp_date)

    # Alert statistics
    declare_simple_sorter(
        "alerts_ok", _("Number of recoveries"), "log_alerts_ok", cmp_simple_number
    )
    declare_simple_sorter(
        "alerts_warn", _("Number of warnings"), "log_alerts_warn", cmp_simple_number
    )
    declare_simple_sorter(
        "alerts_crit", _("Number of critical alerts"), "log_alerts_crit", cmp_simple_number
    )
    declare_simple_sorter(
        "alerts_unknown", _("Number of unknown alerts"), "log_alerts_unknown", cmp_simple_number
    )
    declare_simple_sorter(
        "alerts_problem", _("Number of problem alerts"), "log_alerts_problem", cmp_simple_number
    )

    # Aggregations
    declare_simple_sorter("aggr_name", _("Aggregation name"), "aggr_name", cmp_simple_string)
    declare_simple_sorter("aggr_group", _("Aggregation group"), "aggr_group", cmp_simple_string)

    # Crash reports
    declare_simple_sorter("crash_time", _("Crash time"), "crash_time", cmp_simple_number)


def cmp_state_equiv(r):
    if r["service_has_been_checked"] == 0:
        return -1
    s = r["service_state"]
    if s <= 1:
        return s
    return 5 - s  # swap crit and unknown


def cmp_host_state_equiv(r):
    if r["host_has_been_checked"] == 0:
        return -1
    s = r["host_state"]
    if s == 0:
        return 0
    return 2 - s  # swap down und unreachable


class SorterSvcstate(Sorter):
    @property
    def ident(self) -> str:
        return "svcstate"

    @property
    def title(self) -> str:
        return _("Service state")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_state", "service_has_been_checked"]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        return (cmp_state_equiv(r1) > cmp_state_equiv(r2)) - (
            cmp_state_equiv(r1) < cmp_state_equiv(r2)
        )


class SorterHoststate(Sorter):
    @property
    def ident(self) -> str:
        return "hoststate"

    @property
    def title(self) -> str:
        return _("Host state")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_state", "host_has_been_checked"]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        return (cmp_host_state_equiv(r1) > cmp_host_state_equiv(r2)) - (
            cmp_host_state_equiv(r1) < cmp_host_state_equiv(r2)
        )


class SorterSiteHost(Sorter):
    @property
    def ident(self) -> str:
        return "site_host"

    @property
    def title(self) -> str:
        return _("Host site and name")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["site", "host_name"]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        return (r1["site"] > r2["site"]) - (r1["site"] < r2["site"]) or cmp_num_split(
            "host_name", r1, r2
        )


class SorterHostName(Sorter):
    @property
    def ident(self) -> str:
        return "host_name"

    @property
    def title(self) -> str:
        return _("Host name")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_name"]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        return cmp_num_split("host_name", r1, r2)


class SorterSitealias(Sorter):
    @property
    def ident(self) -> str:
        return "sitealias"

    @property
    def title(self) -> str:
        return _("Site Alias")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["site"]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        return (get_site_config(r1["site"])["alias"] > get_site_config(r2["site"])["alias"]) - (
            get_site_config(r1["site"])["alias"] < get_site_config(r2["site"])["alias"]
        )


class ABCTagSorter(Sorter, abc.ABC):
    @property
    @abc.abstractmethod
    def object_type(self):
        raise NotImplementedError()

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        tag_groups_1 = sorted(get_tag_groups(r1, self.object_type).items())
        tag_groups_2 = sorted(get_tag_groups(r2, self.object_type).items())
        return (tag_groups_1 > tag_groups_2) - (tag_groups_1 < tag_groups_2)


class SorterHost(ABCTagSorter):
    @property
    def object_type(self):
        return "host"

    @property
    def ident(self) -> str:
        return "host"

    @property
    def title(self) -> str:
        return _("Host Tags")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_tags"]


class SorterServiceTags(ABCTagSorter):
    @property
    def object_type(self):
        return "service"

    @property
    def ident(self) -> str:
        return "service_tags"

    @property
    def title(self) -> str:
        return _("Tags")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_tags"]


class ABCLabelSorter(Sorter, abc.ABC):
    @property
    @abc.abstractmethod
    def object_type(self):
        raise NotImplementedError()

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        labels_1 = sorted(get_labels(r1, self.object_type).items())
        labels_2 = sorted(get_labels(r2, self.object_type).items())
        return (labels_1 > labels_2) - (labels_1 < labels_2)


class SorterHostLabels(ABCLabelSorter):
    @property
    def object_type(self):
        return "host"

    @property
    def ident(self) -> str:
        return "host_labels"

    @property
    def title(self) -> str:
        return _("Host labels")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_labels"]


class SorterServiceLabels(ABCLabelSorter):
    @property
    def object_type(self):
        return "service"

    @property
    def ident(self) -> str:
        return "service_labels"

    @property
    def title(self) -> str:
        return _("Service labels")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_labels"]


class SorterServicelevel(Sorter):
    @property
    def ident(self) -> str:
        return "servicelevel"

    @property
    def title(self) -> str:
        return _("Servicelevel")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["custom_variables"]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        return cmp_custom_variable(r1, r2, "EC_SL", cmp_simple_number)


def cmp_service_name(column, r1, r2):
    return (cmp_service_name_equiv(r1[column]) > cmp_service_name_equiv(r2[column])) - (
        cmp_service_name_equiv(r1[column]) < cmp_service_name_equiv(r2[column])
    ) or cmp_num_split(column, r1, r2)


class PerfValSorter(Sorter):
    _num = 0

    @property
    def ident(self) -> str:
        return "svc_perf_val%02d" % self._num

    @property
    def title(self) -> str:
        return _("Service performance data - value number %02d") % self._num

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_perf_data"]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        v1 = utils.savefloat(get_perfdata_nth_value(r1, self._num - 1, True))
        v2 = utils.savefloat(get_perfdata_nth_value(r2, self._num - 1, True))
        return (v1 > v2) - (v1 < v2)


class SorterSvcPerfVal01(PerfValSorter):
    _num = 1


class SorterSvcPerfVal02(PerfValSorter):
    _num = 2


class SorterSvcPerfVal03(PerfValSorter):
    _num = 3


class SorterSvcPerfVal04(PerfValSorter):
    _num = 4


class SorterSvcPerfVal05(PerfValSorter):
    _num = 5


class SorterSvcPerfVal06(PerfValSorter):
    _num = 6


class SorterSvcPerfVal07(PerfValSorter):
    _num = 7


class SorterSvcPerfVal08(PerfValSorter):
    _num = 8


class SorterSvcPerfVal09(PerfValSorter):
    _num = 9


class SorterSvcPerfVal10(PerfValSorter):
    _num = 10


class SorterCustomHostVariable(ParameterizedSorter):
    @property
    def ident(self) -> str:
        return "host_custom_variable"

    @property
    def title(self) -> str:
        return _("Host custom attribute")

    @property
    def columns(self) -> list[str]:
        return ["host_custom_variable_names", "host_custom_variable_values"]

    def vs_parameters(self, painters: Sequence[ColumnSpec]) -> Dictionary:
        choices: list[tuple[str, str]] = []
        for attr_spec in active_config.wato_host_attrs:
            choices.append((attr_spec["name"], attr_spec["title"]))
        choices.sort(key=lambda x: x[1])
        return Dictionary(
            elements=[
                (
                    "ident",
                    DropdownChoice(
                        choices=choices,
                        title=_("ID"),
                    ),
                ),
            ],
            title=_("Options"),
            optional_keys=[],
        )

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        assert parameters is not None
        variable_name = parameters["ident"].upper()

        def _get_value(row: Row) -> str:
            try:
                index = row["host_custom_variable_names"].index(variable_name)
            except ValueError:
                return ""
            return row["host_custom_variable_values"][index]

        return cmp_insensitive_string(_get_value(r1), _get_value(r2))


def _sort_host_ip_addresses(
    ip_versions: Sequence[Literal["ipv4", "ipv6"]],
    r1: Row,
    r2: Row,
) -> int:
    def get_address(row: Row, ipv: Literal["ipv4", "ipv6"]) -> str:
        custom_vars = dict(
            zip(row["host_custom_variable_names"], row["host_custom_variable_values"])
        )
        if ipv == "ipv4":
            return custom_vars.get("ADDRESS_4", "")
        return custom_vars.get("ADDRESS_6", "")

    for ipv in ip_versions:
        if (result := compare_ips(get_address(r1, ipv), get_address(r2, ipv), ipv)) != 0:
            return result
    return 0


class SorterHostIpv4Address(Sorter):
    @property
    def ident(self) -> str:
        return "host_ipv4_address"

    @property
    def title(self) -> str:
        return _("Host IPv4 address")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_custom_variable_names", "host_custom_variable_values"]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        return _sort_host_ip_addresses(["ipv4"], r1, r2)


class SorterHostIpv6Address(Sorter):
    @property
    def ident(self) -> str:
        return "host_ipv6_address"

    @property
    def title(self) -> str:
        return _("Host IPv6 address")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_custom_variable_names", "host_custom_variable_values"]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        return _sort_host_ip_addresses(["ipv6"], r1, r2)


class SorterHostIpAddresses(Sorter):
    @property
    def ident(self) -> str:
        return "host_addresses"

    @property
    def title(self) -> str:
        return _("Host addresses (IPv4/IPv6)")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_custom_variable_names", "host_custom_variable_values"]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        return _sort_host_ip_addresses(["ipv4", "ipv6"], r1, r2)


class SorterNumProblems(Sorter):
    @property
    def ident(self) -> str:
        return "num_problems"

    @property
    def title(self) -> str:
        return _("Number of problems")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_num_services", "host_num_services_ok", "host_num_services_pending"]

    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        return (
            r1["host_num_services"] - r1["host_num_services_ok"] - r1["host_num_services_pending"]
            > r2["host_num_services"] - r2["host_num_services_ok"] - r2["host_num_services_pending"]
        ) - (
            r1["host_num_services"] - r1["host_num_services_ok"] - r1["host_num_services_pending"]
            < r2["host_num_services"] - r2["host_num_services_ok"] - r2["host_num_services_pending"]
        )


def cmp_log_what(col, a, b):
    return (log_what(a[col]) > log_what(b[col])) - (log_what(a[col]) < log_what(b[col]))


def log_what(t):
    if "HOST" in t:
        return 1
    if "SERVICE" in t or "SVC" in t:
        return 2
    return 0


def get_day_start_timestamp(t):
    st = time.localtime(int(t))
    start = int(time.mktime(time.struct_time((st[0], st[1], st[2], 0, 0, 0, st[6], st[7], st[8]))))
    end = start + 86399
    return start, end


def cmp_date(column, r1, r2):
    # need to calculate with the timestamp of the day. Using 00:00:00 at the given day.
    # simply calculating with 86400 does not work because of timezone problems
    r1_date = get_day_start_timestamp(r1[column])
    r2_date = get_day_start_timestamp(r2[column])
    return (r2_date > r1_date) - (r2_date < r1_date)
