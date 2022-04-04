#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import time
from typing import List, Optional, Tuple, TYPE_CHECKING

import cmk.gui.utils as utils
from cmk.gui.globals import config
from cmk.gui.i18n import _
from cmk.gui.plugins.views.utils import (
    cmp_custom_variable,
    cmp_insensitive_string,
    cmp_ip_address,
    cmp_num_split,
    cmp_service_name_equiv,
    cmp_simple_number,
    cmp_simple_string,
    cmp_string_list,
    compare_ips,
    declare_1to1_sorter,
    declare_simple_sorter,
    DerivedColumnsSorter,
    get_perfdata_nth_value,
    get_tag_groups,
    Sorter,
    sorter_registry,
)
from cmk.gui.site_config import get_site_config
from cmk.gui.type_defs import Row
from cmk.gui.valuespec import Dictionary, DropdownChoice, ValueSpec
from cmk.gui.view_utils import get_labels

if TYPE_CHECKING:
    from cmk.gui.views import View


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


@sorter_registry.register
class SorterSvcstate(Sorter):
    @property
    def ident(self):
        return "svcstate"

    @property
    def title(self):
        return _("Service state")

    @property
    def columns(self):
        return ["service_state", "service_has_been_checked"]

    def cmp(self, r1, r2):
        return (cmp_state_equiv(r1) > cmp_state_equiv(r2)) - (
            cmp_state_equiv(r1) < cmp_state_equiv(r2)
        )


@sorter_registry.register
class SorterHoststate(Sorter):
    @property
    def ident(self):
        return "hoststate"

    @property
    def title(self):
        return _("Host state")

    @property
    def columns(self):
        return ["host_state", "host_has_been_checked"]

    def cmp(self, r1, r2):
        return (cmp_host_state_equiv(r1) > cmp_host_state_equiv(r2)) - (
            cmp_host_state_equiv(r1) < cmp_host_state_equiv(r2)
        )


@sorter_registry.register
class SorterSiteHost(Sorter):
    @property
    def ident(self):
        return "site_host"

    @property
    def title(self):
        return _("Host site and name")

    @property
    def columns(self):
        return ["site", "host_name"]

    def cmp(self, r1, r2):
        return (r1["site"] > r2["site"]) - (r1["site"] < r2["site"]) or cmp_num_split(
            "host_name", r1, r2
        )


@sorter_registry.register
class SorterHostName(Sorter):
    @property
    def ident(self):
        return "host_name"

    @property
    def title(self):
        return _("Host name")

    @property
    def columns(self):
        return ["host_name"]

    def cmp(self, r1, r2):
        return cmp_num_split("host_name", r1, r2)


@sorter_registry.register
class SorterSitealias(Sorter):
    @property
    def ident(self):
        return "sitealias"

    @property
    def title(self):
        return _("Site Alias")

    @property
    def columns(self):
        return ["site"]

    def cmp(self, r1, r2):
        return (get_site_config(r1["site"])["alias"] > get_site_config(r2["site"])["alias"]) - (
            get_site_config(r1["site"])["alias"] < get_site_config(r2["site"])["alias"]
        )


class ABCTagSorter(Sorter, abc.ABC):
    @property
    @abc.abstractmethod
    def object_type(self):
        raise NotImplementedError()

    def cmp(self, r1, r2):
        tag_groups_1 = sorted(get_tag_groups(r1, self.object_type).items())
        tag_groups_2 = sorted(get_tag_groups(r2, self.object_type).items())
        return (tag_groups_1 > tag_groups_2) - (tag_groups_1 < tag_groups_2)


@sorter_registry.register
class SorterHost(ABCTagSorter):
    @property
    def object_type(self):
        return "host"

    @property
    def ident(self):
        return "host"

    @property
    def title(self):
        return _("Host Tags")

    @property
    def columns(self):
        return ["host_tags"]


@sorter_registry.register
class SorterServiceTags(ABCTagSorter):
    @property
    def object_type(self):
        return "service"

    @property
    def ident(self):
        return "service_tags"

    @property
    def title(self):
        return _("Tags")

    @property
    def columns(self):
        return ["service_tags"]


class ABCLabelSorter(Sorter, abc.ABC):
    @property
    @abc.abstractmethod
    def object_type(self):
        raise NotImplementedError()

    def cmp(self, r1, r2):
        labels_1 = sorted(get_labels(r1, self.object_type).items())
        labels_2 = sorted(get_labels(r2, self.object_type).items())
        return (labels_1 > labels_2) - (labels_1 < labels_2)


@sorter_registry.register
class SorterHostLabels(ABCTagSorter):
    @property
    def object_type(self):
        return "host"

    @property
    def ident(self):
        return "host_labels"

    @property
    def title(self):
        return _("Host labels")

    @property
    def columns(self):
        return ["host_labels"]


@sorter_registry.register
class SorterServiceLabels(ABCTagSorter):
    @property
    def object_type(self):
        return "service"

    @property
    def ident(self):
        return "service_labels"

    @property
    def title(self):
        return _("Service labels")

    @property
    def columns(self):
        return ["service_labels"]


@sorter_registry.register
class SorterServicelevel(Sorter):
    @property
    def ident(self):
        return "servicelevel"

    @property
    def title(self):
        return _("Servicelevel")

    @property
    def columns(self):
        return ["custom_variables"]

    def cmp(self, r1, r2):
        return cmp_custom_variable(r1, r2, "EC_SL", cmp_simple_number)


def cmp_service_name(column, r1, r2):
    return (cmp_service_name_equiv(r1[column]) > cmp_service_name_equiv(r2[column])) - (
        cmp_service_name_equiv(r1[column]) < cmp_service_name_equiv(r2[column])
    ) or cmp_num_split(column, r1, r2)


#                      name                      title                              column                       sortfunction
declare_simple_sorter("svcdescr", _("Service description"), "service_description", cmp_service_name)
declare_simple_sorter(
    "svcdispname", _("Service alternative display name"), "service_display_name", cmp_simple_string
)
declare_simple_sorter(
    "svcoutput", _("Service plugin output"), "service_plugin_output", cmp_simple_string
)
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
declare_simple_sorter("servicegroup", _("Service group"), "servicegroup_alias", cmp_simple_string)
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


class PerfValSorter(Sorter):
    _num = 0

    @property
    def ident(self):
        return "svc_perf_val%02d" % self._num

    @property
    def title(self):
        return _("Service performance data - value number %02d") % self._num

    @property
    def columns(self):
        return ["service_perf_data"]

    def cmp(self, r1, r2):
        v1 = utils.savefloat(get_perfdata_nth_value(r1, self._num - 1, True))
        v2 = utils.savefloat(get_perfdata_nth_value(r2, self._num - 1, True))
        return (v1 > v2) - (v1 < v2)


@sorter_registry.register
class SorterSvcPerfVal01(PerfValSorter):
    _num = 1


@sorter_registry.register
class SorterSvcPerfVal02(PerfValSorter):
    _num = 2


@sorter_registry.register
class SorterSvcPerfVal03(PerfValSorter):
    _num = 3


@sorter_registry.register
class SorterSvcPerfVal04(PerfValSorter):
    _num = 4


@sorter_registry.register
class SorterSvcPerfVal05(PerfValSorter):
    _num = 5


@sorter_registry.register
class SorterSvcPerfVal06(PerfValSorter):
    _num = 6


@sorter_registry.register
class SorterSvcPerfVal07(PerfValSorter):
    _num = 7


@sorter_registry.register
class SorterSvcPerfVal08(PerfValSorter):
    _num = 8


@sorter_registry.register
class SorterSvcPerfVal09(PerfValSorter):
    _num = 9


@sorter_registry.register
class SorterSvcPerfVal10(PerfValSorter):
    _num = 10


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


@sorter_registry.register
class SorterCustomHostVariable(DerivedColumnsSorter):
    _variable_name: Optional[str] = None

    @property
    def ident(self) -> str:
        return "host_custom_variable"

    @property
    def title(self) -> str:
        return _("Host custom attribute")

    @property
    def columns(self) -> List[str]:
        return ["host_custom_variable_names", "host_custom_variable_values"]

    def derived_columns(self, view: "View", uuid: Optional[str]) -> None:
        self._variable_name = uuid

    def get_parameters(self) -> Optional[ValueSpec]:
        choices: List[Tuple[str, str]] = []
        for attr_spec in config.wato_host_attrs:
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

    def cmp(self, r1: Row, r2: Row) -> int:
        if self._variable_name is None:
            return 0
        variable_name = self._variable_name.upper()  # outwit mypy

        def _get_value(row: Row) -> str:
            try:
                index = row["host_custom_variable_names"].index(variable_name)
            except ValueError:
                return ""
            return row["host_custom_variable_values"][index]

        return cmp_insensitive_string(_get_value(r1), _get_value(r2))


@sorter_registry.register
class SorterHostIpv4Address(Sorter):
    @property
    def ident(self):
        return "host_ipv4_address"

    @property
    def title(self):
        return _("Host IPv4 address")

    @property
    def columns(self):
        return ["host_custom_variable_names", "host_custom_variable_values"]

    def cmp(self, r1, r2):
        def get_address(row):
            custom_vars = dict(
                zip(row["host_custom_variable_names"], row["host_custom_variable_values"])
            )
            return custom_vars.get("ADDRESS_4", "")

        return compare_ips(get_address(r1), get_address(r2))


@sorter_registry.register
class SorterNumProblems(Sorter):
    @property
    def ident(self):
        return "num_problems"

    @property
    def title(self):
        return _("Number of problems")

    @property
    def columns(self):
        return ["host_num_services", "host_num_services_ok", "host_num_services_pending"]

    def cmp(self, r1, r2):
        return (
            r1["host_num_services"] - r1["host_num_services_ok"] - r1["host_num_services_pending"]
            > r2["host_num_services"] - r2["host_num_services_ok"] - r2["host_num_services_pending"]
        ) - (
            r1["host_num_services"] - r1["host_num_services_ok"] - r1["host_num_services_pending"]
            < r2["host_num_services"] - r2["host_num_services_ok"] - r2["host_num_services_pending"]
        )


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


def cmp_log_what(col, a, b):
    return (log_what(a[col]) > log_what(b[col])) - (log_what(a[col]) < log_what(b[col]))


def log_what(t):
    if "HOST" in t:
        return 1
    if "SERVICE" in t or "SVC" in t:
        return 2
    return 0


declare_1to1_sorter("log_what", cmp_log_what)


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


declare_1to1_sorter("log_date", cmp_date)

# Alert statistics
declare_simple_sorter("alerts_ok", _("Number of recoveries"), "log_alerts_ok", cmp_simple_number)
declare_simple_sorter("alerts_warn", _("Number of warnings"), "log_alerts_warn", cmp_simple_number)
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
