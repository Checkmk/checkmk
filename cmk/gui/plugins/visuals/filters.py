#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
from typing import Any, Callable, Dict, Iterable, List, Literal, Optional, Tuple, Union

import livestatus

import cmk.utils.version as cmk_version
from cmk.utils.prediction import lq_logic

import cmk.gui.bi as bi
import cmk.gui.mkeventd as mkeventd
import cmk.gui.sites as sites
from cmk.gui.exceptions import MKMissingDataError, MKUserError
from cmk.gui.globals import config, html, request, response, user_errors
from cmk.gui.i18n import _, _l
from cmk.gui.type_defs import Choices, FilterHeader, FilterHTTPVariables, Row, Rows, VisualContext
from cmk.gui.utils.labels import encode_labels_for_livestatus
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.regex import validate_regex
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.valuespec import DualListChoice, Labels

if cmk_version.is_managed_edition():
    from cmk.gui.cme.plugins.visuals.managed import (  # pylint: disable=no-name-in-module
        filter_cme_choices,
        filter_cme_heading_info,
    )

import cmk.gui.legacy_filters as legacy_filters
from cmk.gui.plugins.visuals.utils import (
    display_filter_radiobuttons,
    Filter,
    filter_cre_choices,
    filter_cre_heading_info,
    filter_registry,
    FilterOption,
    FilterTime,
    get_only_sites_from_context,
)


class FilterText(Filter):
    """Filters for substring search, displaying a text input field"""

    def __init__(
        self,
        *,
        ident: str,
        title: Union[str, LazyString],
        sort_index: int,
        info: str,
        legacy_filter: legacy_filters.FilterText,
        show_heading: bool = True,
        description: Union[None, str, LazyString] = None,
        is_show_more: bool = False,
    ):
        self.legacy_filter = legacy_filter

        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=self.legacy_filter.htmlvars,
            link_columns=self.legacy_filter.link_columns,
            description=description,
            is_show_more=is_show_more,
        )
        self._show_heading = show_heading

    def display(self, value: FilterHTTPVariables) -> None:
        current_value = value.get(self.htmlvars[0], "")
        column = self.link_columns[0]

        if column in ["host_name", "service_description"] and not is_mobile(request, response):
            input_type = (
                "monitored_hostname" if column == "host_name" else "monitored_service_description"
            )
            choices = [(current_value, current_value)] if current_value else []
            html.dropdown(
                self.htmlvars[0],
                choices,
                current_value,
                style="width: 250px;",
                class_=["ajax-vals", input_type],
                data_strict="True" if self.legacy_filter.op == "=" else "False",
            )
        else:
            html.text_input(
                self.htmlvars[0], current_value, self.legacy_filter.negateable and "neg" or ""
            )

        if self.legacy_filter.negateable:
            html.open_nobr()
            html.checkbox(
                self.legacy_filter.htmlvars[1],
                bool(value.get(self.legacy_filter.htmlvars[1])),
                label=_("negate"),
            )
            html.close_nobr()

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {self.htmlvars[0]: row[self.legacy_filter.column]}

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        if self._show_heading:
            return value.get(self.legacy_filter.htmlvars[0])
        return None

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.legacy_filter.filter(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.legacy_filter.filter_table(context, rows)


class FilterRegExp(FilterText):
    def validate_value(self, value: FilterHTTPVariables) -> None:
        htmlvar = self.htmlvars[0]
        validate_regex(value.get(htmlvar, ""), htmlvar)


filter_registry.register(
    FilterRegExp(
        ident="hostregex",
        title=_l("Hostname"),
        sort_index=100,
        info="host",
        legacy_filter=legacy_filters.FilterText(
            column="host_name", htmlvar="host_regex", op="~~", negateable=True
        ),
        description=_l("Search field allowing regular expressions and partial matches"),
    )
)

filter_registry.register(
    FilterText(
        ident="host",
        title=_l("Hostname (exact match)"),
        sort_index=101,
        info="host",
        legacy_filter=legacy_filters.FilterText(
            column="host_name", htmlvar="host", op="=", negateable=True
        ),
        description=_l("Exact match, used for linking"),
        is_show_more=True,
    )
)

filter_registry.register(
    FilterText(
        ident="hostalias",
        title=_l("Hostalias"),
        sort_index=102,
        info="host",
        legacy_filter=legacy_filters.FilterText(
            column="host_alias", htmlvar="hostalias", op="~~", negateable=True
        ),
        description=_l("Search field allowing regular expressions and partial matches"),
        is_show_more=True,
    )
)

filter_registry.register(
    FilterRegExp(
        ident="serviceregex",
        title=_l("Service"),
        sort_index=200,
        info="service",
        legacy_filter=legacy_filters.FilterText(
            column="service_description", htmlvar="service_regex", op="~~", negateable=True
        ),
        description=_l("Search field allowing regular expressions and partial matches"),
    )
)

filter_registry.register(
    FilterText(
        ident="service",
        title=_l("Service (exact match)"),
        sort_index=201,
        info="service",
        legacy_filter=legacy_filters.FilterText(
            column="service_description", htmlvar="service", op="="
        ),
        description=_l("Exact match, used for linking"),
        is_show_more=True,
    )
)

filter_registry.register(
    FilterRegExp(
        ident="service_display_name",
        title=_l("Service alternative display name"),
        sort_index=202,
        description=_l("Alternative display name of the service, regex match"),
        info="service",
        legacy_filter=legacy_filters.FilterText(
            column="service_display_name", htmlvar="service_display_name", op="~~"
        ),
        is_show_more=True,
    )
)

filter_registry.register(
    FilterText(
        ident="output",
        title=_l("Summary (Plugin output)"),
        sort_index=202,
        info="service",
        legacy_filter=legacy_filters.FilterText(
            column="service_plugin_output", htmlvar="service_output", op="~~", negateable=True
        ),
    )
)

filter_registry.register(
    FilterText(
        ident="hostnameoralias",
        title=_l("Hostname or Alias"),
        sort_index=102,
        info="host",
        description=_l("Search field allowing regular expressions and partial matches"),
        legacy_filter=legacy_filters.FilterHostnameOrAlias(),
    )
)


class FilterIPAddress(Filter):
    def __init__(
        self,
        *,
        ident: str,
        title: Union[str, LazyString],
        sort_index: int,
        legacy_filter: legacy_filters.FilterIPAddress,
        link_columns: List[str],
        is_show_more: bool = False,
    ):
        self.legacy_filter = legacy_filter
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info="host",
            htmlvars=self.legacy_filter.htmlvars,
            link_columns=link_columns,
            is_show_more=is_show_more,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.text_input(self.htmlvars[0], value.get(self.htmlvars[0], ""))
        html.br()
        display_filter_radiobuttons(
            varname=self.htmlvars[1],
            options=legacy_filters.ip_match_options(),
            default="yes",
            value=value,
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.legacy_filter.filter(value)

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {self.htmlvars[0]: row["host_address"]}

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        return value.get(self.htmlvars[0])


filter_registry.register(
    FilterIPAddress(
        ident="host_address",
        title=_l("Host address (Primary)"),
        sort_index=102,
        link_columns=["host_address"],
        legacy_filter=legacy_filters.FilterIPAddress(
            htmlvars=["host_address", "host_address_prefix"], what="primary"
        ),
        is_show_more=True,
    )
)

filter_registry.register(
    FilterIPAddress(
        ident="host_ipv4_address",
        title=_l("Host address (IPv4)"),
        sort_index=102,
        link_columns=[],
        legacy_filter=legacy_filters.FilterIPAddress(
            htmlvars=["host_ipv4_address", "host_ipv4_address_prefix"], what="ipv4"
        ),
    )
)

filter_registry.register(
    FilterIPAddress(
        ident="host_ipv6_address",
        title=_l("Host address (IPv6)"),
        sort_index=102,
        link_columns=[],
        legacy_filter=legacy_filters.FilterIPAddress(
            htmlvars=["host_ipv6_address", "host_ipv6_address_prefix"], what="ipv6"
        ),
    )
)

filter_registry.register(
    FilterOption(
        ident="address_family",
        title=_l("Host address family (Primary)"),
        sort_index=103,
        info="host",
        legacy_filter=legacy_filters.FilterOption(
            ident="address_family",
            options=legacy_filters.ip_address_family_options(),
            filter_code=legacy_filters.address_family,
        ),
        is_show_more=True,
    )
)


filter_registry.register(
    FilterOption(
        ident="address_families",
        title=_l("Host address families"),
        sort_index=103,
        info="host",
        legacy_filter=legacy_filters.FilterOption(
            ident="address_families",
            options=legacy_filters.ip_address_families_options(),
            filter_code=legacy_filters.address_families,
        ),
        is_show_more=True,
    )
)


class FilterMultigroup(Filter):
    def __init__(
        self,
        *,
        ident: str,
        title: Union[str, LazyString],
        sort_index: int,
        group_type: str,
        legacy_filter: legacy_filters.FilterMultiple,
        description: Union[None, str, LazyString] = None,
        is_show_more: bool = True,
    ):
        self.legacy_filter = legacy_filter
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info=group_type,
            htmlvars=self.legacy_filter.htmlvars,
            link_columns=[],
            description=description,
            is_show_more=is_show_more,
        )
        self.group_type = group_type

    def valuespec(self):
        return DualListChoice(choices=self._options(self.group_type), rows=4, enlarge_active=True)

    @staticmethod
    def _options(group_type):
        return sites.all_groups(group_type)

    def display(self, value: FilterHTTPVariables) -> None:
        html.open_div(class_="multigroup")
        self.valuespec().render_input(self.htmlvars[0], self.legacy_filter.selection(value))
        # TODO: this should be the negate flag not a test of options
        if self._options(self.group_type):
            html.open_nobr()
            html.checkbox(self.htmlvars[1], bool(value.get(self.htmlvars[1])), label=_("negate"))
            html.close_nobr()
        html.close_div()

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.legacy_filter.filter(value)


filter_registry.register(
    FilterMultigroup(
        ident="hostgroups",
        title=_l("Several Host Groups"),
        sort_index=105,
        description=_l("Selection of multiple host groups"),
        group_type="host",
        legacy_filter=legacy_filters.FilterMultiple(ident="hostgroups", column="host_groups"),
    )
)

filter_registry.register(
    FilterMultigroup(
        ident="servicegroups",
        title=_l("Several Service Groups"),
        sort_index=205,
        description=_l("Selection of multiple service groups"),
        group_type="service",
        legacy_filter=legacy_filters.FilterMultiple(ident="servicegroups", column="service_groups"),
    )
)


class FilterGroupCombo(Filter):
    """Selection of a host/service(-contact) group as an attribute of a host or service"""

    # TODO: Rename "what"
    def __init__(
        self,
        *,
        ident: str,
        title: Union[str, LazyString],
        sort_index: int,
        what: str,
        enforce: bool,
        description: Union[None, str, LazyString] = None,
    ) -> None:
        self.enforce = enforce
        self.prefix = "opt" if not self.enforce else ""

        htmlvars = [self.prefix + what + "_group"]
        if not enforce:
            htmlvars.append("neg_" + htmlvars[0])

        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info=what.split("_")[0],
            htmlvars=htmlvars,
            link_columns=[what + "group_name"],
            description=description,
        )
        self.what = what

    def display(self, value: FilterHTTPVariables) -> None:
        html.dropdown(
            self.htmlvars[0],
            self._options(self.what, self.enforce),
            deflt=value.get(self.htmlvars[0], ""),
            ordered=True,
        )
        if not self.enforce:
            html.open_nobr()
            html.checkbox(self.htmlvars[1], bool(value.get(self.htmlvars[1])), label=_("negate"))
            html.close_nobr()

    @staticmethod
    def _options(what, enforce) -> Choices:
        choices: Choices = list(sites.all_groups(what.split("_")[-1]))
        if not enforce:
            empty_choices: Choices = [("", "")]
            choices = empty_choices + choices
        return choices

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        current_value = value.get(self.htmlvars[0])
        if not current_value:
            return ""  # Skip if filter is not being set at all

        col = self.what + "_groups"
        if not self.enforce and value.get(self.htmlvars[1]):
            negate = "!"
        else:
            negate = ""
        return "Filter: %s %s>= %s\n" % (col, negate, livestatus.lqencode(current_value))

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        varname = self.htmlvars[0]
        value = row.get(self.what + "group_name")
        if value:
            s = {varname: value}
            if not self.enforce:
                negvar = self.htmlvars[1]
                if request.var(negvar):  # This violates the idea of originating from row
                    s[negvar] = request.var(negvar)
            return s
        return {}

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        if current_value := value.get(self.htmlvars[0]):
            table = self.what.replace("host_contact", "contact").replace(
                "service_contact", "contact"
            )
            alias = sites.live().query_value(
                "GET %sgroups\nCache: reload\nColumns: alias\nFilter: name = %s\n"
                % (table, livestatus.lqencode(current_value)),
                current_value,
            )
            return alias
        return None


filter_registry.register(
    FilterGroupCombo(
        ident="opthostgroup",
        title=_l("Host is in Group"),
        sort_index=104,
        description=_l("Optional selection of host group"),
        what="host",
        enforce=False,
    )
)

filter_registry.register(
    FilterGroupCombo(
        ident="optservicegroup",
        title=_l("Service is in Group"),
        sort_index=204,
        description=_l("Optional selection of service group"),
        what="service",
        enforce=False,
    )
)

filter_registry.register(
    FilterGroupCombo(
        ident="opthost_contactgroup",
        title=_l("Host Contact Group"),
        sort_index=106,
        description=_l("Optional selection of host contact group"),
        what="host_contact",
        enforce=False,
    )
)

filter_registry.register(
    FilterGroupCombo(
        ident="optservice_contactgroup",
        title=_l("Service Contact Group"),
        sort_index=206,
        description=_l("Optional selection of service contact group"),
        what="service_contact",
        enforce=False,
    )
)

filter_registry.register(
    FilterText(
        ident="host_ctc",
        title=_l("Host Contact"),
        sort_index=107,
        info="host",
        legacy_filter=legacy_filters.FilterText(
            column="host_contacts", htmlvar="host_ctc", op=">="
        ),
        is_show_more=True,
    )
)

filter_registry.register(
    FilterRegExp(
        ident="host_ctc_regex",
        title=_l("Host Contact (Regex)"),
        sort_index=107,
        info="host",
        legacy_filter=legacy_filters.FilterText(
            column="host_contacts", htmlvar="host_ctc_regex", op="~~"
        ),
        is_show_more=True,
    )
)

filter_registry.register(
    FilterText(
        ident="service_ctc",
        title=_l("Service Contact"),
        sort_index=207,
        info="service",
        legacy_filter=legacy_filters.FilterText(
            column="service_contacts", htmlvar="service_ctc", op=">="
        ),
        is_show_more=True,
    )
)

filter_registry.register(
    FilterRegExp(
        ident="service_ctc_regex",
        title=_l("Service Contact (Regex)"),
        sort_index=207,
        info="service",
        legacy_filter=legacy_filters.FilterText(
            column="service_contacts", htmlvar="service_ctc_regex", op="~~"
        ),
        is_show_more=True,
    )
)


class FilterGroupSelection(Filter):
    """Selection of one group to be used in the info "hostgroup" or "servicegroup"."""

    def __init__(
        self,
        *,
        ident: str,
        title: Union[str, LazyString],
        sort_index: int,
        info: str,
        description: Union[None, str, LazyString] = None,
    ) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=[info],
            link_columns=[],
            description=description,
        )
        # TODO: Rename "what"
        self.what = info

    def display(self, value: FilterHTTPVariables) -> None:
        # chop off "group", leaves host or service
        html.dropdown(
            self.htmlvars[0],
            self._options(self.what[:-5]),
            deflt=value.get(self.htmlvars[0], ""),
            ordered=True,
        )

    @staticmethod
    def _options(group_type: str) -> Choices:
        return list(sites.all_groups(group_type))

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if current_value := value.get(self.htmlvars[0]):
            return "Filter: %s_name = %s\n" % (self.what, livestatus.lqencode(current_value))
        return ""

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        group_name = row[self.what + "_name"]
        return {self.htmlvars[0]: group_name}


filter_registry.register(
    FilterGroupSelection(
        ident="hostgroup",
        title=_l("Host Group"),
        sort_index=104,
        description=_l("Selection of the host group"),
        info="hostgroup",
    )
)

filter_registry.register(
    FilterGroupSelection(
        ident="servicegroup",
        title=_l("Service Group"),
        sort_index=104,
        description=_l("Selection of the service group"),
        info="servicegroup",
    )
)

filter_registry.register(
    FilterRegExp(
        ident="hostgroupnameregex",
        title=_l("Hostgroup (Regex)"),
        sort_index=101,
        description=_l(
            "Search field allowing regular expressions and partial matches on the names of hostgroups"
        ),
        info="hostgroup",
        legacy_filter=legacy_filters.FilterText(
            column="hostgroup_name", htmlvar="hostgroup_regex", op="~~"
        ),
    )
)


@filter_registry.register_instance
class FilterHostgroupVisibility(Filter):
    def __init__(self):
        super().__init__(
            ident="hostgroupvisibility",
            title=_l("Empty Hostgroup Visibilitiy"),
            sort_index=102,
            info="hostgroup",
            htmlvars=["hostgroupshowempty"],
            link_columns=[],
            description=_l("You can enable this checkbox to show empty hostgroups"),
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.checkbox(
            self.htmlvars[0], bool(value.get(self.htmlvars[0])), label="Show empty groups"
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if value.get(self.htmlvars[0]):
            return ""
        return "Filter: hostgroup_num_hosts > 0\n"


@filter_registry.register_instance
class FilterHostgroupProblems(Filter):
    def __init__(self):
        super().__init__(
            ident="hostsgroups_having_problems",
            title=_l("Hostgroups having certain problems"),
            sort_index=103,
            info="hostgroup",
            htmlvars=[
                "hostsgroups_having_hosts_down",
                "hostsgroups_having_hosts_unreach",
                "hostsgroups_having_hosts_pending",
                "hostgroups_show_unhandled_host",
                "hostsgroups_having_services_warn",
                "hostsgroups_having_services_crit",
                "hostsgroups_having_services_pending",
                "hostsgroups_having_services_unknown",
                "hostgroups_show_unhandled_svc",
            ],
            link_columns=[],
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.begin_checkbox_group()
        html.write_text("Service states:" + " ")
        for svc_var, svc_text in self._options("service"):
            namevar = "hostgroups_having_services_%s" % svc_var
            html.checkbox(namevar, bool(value.get(namevar, True)), label=svc_text)

        html.br()
        html.checkbox(
            "hostgroups_show_unhandled_svc",
            bool(value.get("hostgroups_show_unhandled_svc")),
            label=_("Unhandled service problems"),
        )

        html.br()
        html.write_text("Host states:" + " ")
        for host_var, host_text in self._options("host"):
            namevar = "hostgroups_having_hosts_%s" % host_var
            html.checkbox(namevar, bool(value.get(namevar, True)), label=host_text)

        html.checkbox(
            "hostgroups_show_unhandled_host",
            bool(value.get("hostgroups_show_unhandled_host")),
            label=_("Unhandled host problems"),
        )

        html.end_checkbox_group()

    @staticmethod
    def _options(target: Literal["host", "service"]) -> List[Tuple[str, str]]:
        if target == "host":
            return [
                ("down", _("DOWN")),
                ("unreach", _("UNREACH")),
                ("pending", _("PEND")),
            ]

        if target == "service":
            return [
                ("warn", _("WARN")),
                ("crit", _("CRIT")),
                ("pending", _("PEND")),
                ("unknown", _("UNKNOWN")),
            ]
        raise ValueError

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        headers = []
        for svc_var in ["warn", "crit", "pending", "unknown"]:
            if value.get("hostgroups_having_services_%s" % svc_var):
                headers.append("num_services_%s > 0\n" % svc_var)

        for host_var in ["down", "unreach", "pending"]:
            if value.get("hostgroups_having_hosts_%s" % host_var):
                headers.append("num_hosts_%s > 0\n" % host_var)

        if value.get("hostgroups_show_unhandled_host"):
            headers.append("num_hosts_unhandled_problems > 0\n")

        if value.get("hostgroups_show_unhandled_svc"):
            headers.append("num_services_unhandled_problems > 0\n")

        return lq_logic("Filter:", headers, "Or")


filter_registry.register(
    FilterRegExp(
        ident="servicegroupnameregex",
        title=_l("Servicegroup (Regex)"),
        sort_index=101,
        description=_l("Search field allowing regular expression and partial matches"),
        info="servicegroup",
        legacy_filter=legacy_filters.FilterText(
            column="servicegroup_name", htmlvar="servicegroup_regex", op="~~", negateable=True
        ),
    )
)

filter_registry.register(
    FilterText(
        ident="servicegroupname",
        title=_l("Servicegroup (enforced)"),
        sort_index=101,
        description=_l("Exact match, used for linking"),
        info="servicegroup",
        legacy_filter=legacy_filters.FilterText(
            column="servicegroup_name", htmlvar="servicegroup_name", op="="
        ),
    )
)


class FilterQueryDropdown(Filter):
    def __init__(
        self,
        *,
        ident: str,
        title: Union[str, LazyString],
        sort_index: int,
        info: str,
        query: str,
        filterline: str,
        is_show_more: bool = True,
    ) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=[ident],
            link_columns=[],
        )
        self.query = query
        self.filterline = filterline

    def display(self, value: FilterHTTPVariables) -> None:
        html.dropdown(
            self.ident,
            self._options(self.query),
            deflt=value.get(self.htmlvars[0], ""),
            ordered=True,
        )

    @staticmethod
    def _options(query: livestatus.QueryTypes) -> Choices:
        selection = sites.live().query_column_unique(query)
        empty_choices: Choices = [("", "")]
        sel: Choices = [(x, x) for x in selection]
        return empty_choices + sel

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if current := value.get(self.ident):
            return self.filterline % livestatus.lqencode(current)
        return ""


filter_registry.register(
    FilterQueryDropdown(
        ident="host_check_command",
        title=_l("Host check command"),
        sort_index=110,
        info="host",
        query="GET commands\nCache: reload\nColumns: name\n",
        filterline="Filter: host_check_command ~ ^%s(!.*)?\n",
    )
)

filter_registry.register(
    FilterQueryDropdown(
        ident="check_command",
        title=_l("Service check command"),
        sort_index=210,
        info="service",
        query="GET commands\nCache: reload\nColumns: name\n",
        filterline="Filter: service_check_command ~ ^%s(!.*)?$\n",
    )
)


class FilterServiceState(Filter):
    def __init__(
        self,
        *,
        ident: str,
        title: Union[str, LazyString],
        sort_index: int,
        prefix: str,
        is_show_more: bool = False,
    ) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info="service",
            htmlvars=[
                prefix + "_filled",
                prefix + "st0",
                prefix + "st1",
                prefix + "st2",
                prefix + "st3",
                prefix + "stp",
            ],
            link_columns=[],
            is_show_more=is_show_more,
        )
        self.prefix = prefix

    def display(self, value: FilterHTTPVariables) -> None:
        html.begin_checkbox_group()
        html.hidden_field(self.prefix + "_filled", "1", add_var=True)
        checkbox_default = not self._filter_used(value)
        for var, text in self._options(self.prefix):
            html.checkbox(var, bool(value.get(var, checkbox_default)), label=text)
        html.end_checkbox_group()

    @staticmethod
    def _options(prefix: str) -> List[Tuple[str, str]]:
        return [
            (prefix + "st0", _("OK")),
            (prefix + "st1", _("WARN")),
            (prefix + "st2", _("CRIT")),
            (prefix + "st3", _("UNKN")),
            (prefix + "stp", _("PEND")),
        ]

    def _filter_used(self, value: FilterHTTPVariables) -> bool:
        return any(value.values())

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        headers = []
        filter_is_used = self._filter_used(value)
        for i in [0, 1, 2, 3]:
            check_result = bool(value.get(self.prefix + "st%d" % i))

            if filter_is_used and check_result is False:
                if self.prefix == "hd":
                    column = "service_last_hard_state"
                else:
                    column = "service_state"
                headers.append(
                    "Filter: %s = %d\n"
                    "Filter: service_has_been_checked = 1\n"
                    "And: 2\nNegate:\n" % (column, i)
                )

        if filter_is_used and bool(value.get(self.prefix + "stp")) is False:
            headers.append("Filter: service_has_been_checked = 1\n")

        if len(headers) == 5:  # none allowed = all allowed (makes URL building easier)
            return ""
        return "".join(headers)


filter_registry.register(
    FilterServiceState(
        ident="svcstate",
        title=_l("Service states"),
        sort_index=215,
        prefix="",
    )
)

filter_registry.register(
    FilterServiceState(
        ident="svchardstate",
        title=_l("Service hard states"),
        sort_index=216,
        prefix="hd",
        is_show_more=True,
    )
)


@filter_registry.register_instance
class FilterHostState(Filter):
    def __init__(self):
        super().__init__(
            ident="hoststate",
            title=_l("Host states"),
            sort_index=115,
            info="host",
            htmlvars=["hoststate_filled", "hst0", "hst1", "hst2", "hstp"],
            link_columns=[],
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.begin_checkbox_group()
        html.hidden_field("hoststate_filled", "1", add_var=True)
        checkbox_default = not self._filter_used(value)
        for var, text in self._options():
            html.checkbox(var, bool(value.get(var, checkbox_default)), label=text)
        html.end_checkbox_group()

    @staticmethod
    def _options() -> List[Tuple[str, str]]:
        return [
            ("hst0", _("UP")),
            ("hst1", _("DOWN")),
            ("hst2", _("UNREACH")),
            ("hstp", _("PEND")),
        ]

    def _filter_used(self, value: FilterHTTPVariables) -> bool:
        return any(value.values())

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        headers = []
        filter_is_used = self._filter_used(value)
        for i in [0, 1, 2]:
            check_result = bool(value.get("hst%d" % i))

            if filter_is_used and check_result is False:
                headers.append(
                    "Filter: host_state = %d\n"
                    "Filter: host_has_been_checked = 1\n"
                    "And: 2\nNegate:\n" % i
                )

        if filter_is_used and bool(value.get("hstp")) is False:
            headers.append("Filter: host_has_been_checked = 1\n")

        if len(headers) == 4:  # none allowed = all allowed (makes URL building easier)
            return ""
        return "".join(headers)


@filter_registry.register_instance
class FilterHostsHavingServiceProblems(Filter):
    def __init__(self):
        super().__init__(
            ident="hosts_having_service_problems",
            title=_l("Hosts having certain service problems"),
            sort_index=120,
            info="host",
            htmlvars=[
                "hosts_having_services_warn",
                "hosts_having_services_crit",
                "hosts_having_services_pending",
                "hosts_having_services_unknown",
            ],
            link_columns=[],
            is_show_more=True,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.begin_checkbox_group()
        checkbox_default = not any(value.values())  # everything by default
        for var, text in self._options():
            varname = "hosts_having_services_%s" % var
            html.checkbox(varname, bool(value.get(varname, checkbox_default)), label=text)
        html.end_checkbox_group()

    @staticmethod
    def _options() -> List[Tuple[str, str]]:
        return [
            ("warn", _("WARN")),
            ("crit", _("CRIT")),
            ("pending", _("PEND")),
            ("unknown", _("UNKNOWN")),
        ]

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        conditions = [
            "host_num_services_%s > 0" % var
            for var in ["warn", "crit", "pending", "unknown"]
            if bool(value.get("hosts_having_services_%s" % var)) is True
        ]

        return lq_logic("Filter:", conditions, "Or")


def filter_state_type_with_register(
    *, ident: str, title: Union[str, LazyString], sort_index: int, info: str
) -> None:
    filter_registry.register(
        FilterOption(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info=info,
            legacy_filter=legacy_filters.FilterTristate(
                ident=ident,
                filter_code=legacy_filters.state_type,
                options=legacy_filters.tri_state_type_options(),
            ),
            is_show_more=True,
        )
    )


filter_state_type_with_register(
    ident="host_state_type",
    title=_l("Host state type"),
    sort_index=116,
    info="host",
)

filter_state_type_with_register(
    ident="service_state_type",
    title=_l("Service state type"),
    sort_index=217,
    info="service",
)


filter_registry.register(
    FilterOption(
        ident="has_performance_data",
        title=_l("Has performance data"),
        sort_index=251,
        info="service",
        legacy_filter=legacy_filters.FilterTristate(
            ident="has_performance_data", filter_code=legacy_filters.service_perfdata_toggle
        ),
        is_show_more=True,
    )
)


filter_registry.register(
    FilterOption(
        ident="in_downtime",
        title=_l("Host/service in downtime"),
        sort_index=232,
        info="service",
        legacy_filter=legacy_filters.FilterTristate(
            ident="in_downtime", filter_code=legacy_filters.host_service_perfdata_toggle
        ),
    )
)


filter_registry.register(
    FilterOption(
        ident="host_staleness",
        title=_l("Host is stale"),
        sort_index=232,
        info="host",
        legacy_filter=legacy_filters.FilterTristate(
            ident="host_staleness", filter_code=legacy_filters.staleness("host")
        ),
        is_show_more=True,
    )
)


filter_registry.register(
    FilterOption(
        ident="service_staleness",
        title=_l("Service is stale"),
        sort_index=232,
        info="service",
        legacy_filter=legacy_filters.FilterTristate(
            ident="service_staleness", filter_code=legacy_filters.staleness("service")
        ),
        is_show_more=True,
    )
)


def filter_nagios_flag_with_register(
    *,
    ident: str,
    title: Union[str, LazyString],
    sort_index: int,
    info: str,
    is_show_more: bool = False,
) -> None:
    filter_registry.register(
        FilterOption(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info=info,
            legacy_filter=legacy_filters.FilterTristate(
                ident=ident, filter_code=legacy_filters.column_flag(ident)
            ),
            is_show_more=is_show_more,
        )
    )


filter_nagios_flag_with_register(
    ident="service_process_performance_data",
    title=_l("Processes performance data"),
    sort_index=250,
    info="service",
    is_show_more=True,
)

filter_nagios_flag_with_register(
    ident="host_in_notification_period",
    title=_l("Host in notification period"),
    sort_index=130,
    info="host",
)

filter_nagios_flag_with_register(
    ident="host_in_service_period",
    title=_l("Host in service period"),
    sort_index=130,
    info="host",
)

filter_nagios_flag_with_register(
    ident="host_acknowledged",
    title=_l("Host problem has been acknowledged"),
    sort_index=131,
    info="host",
)

filter_nagios_flag_with_register(
    ident="host_active_checks_enabled",
    title=_l("Host active checks enabled"),
    sort_index=132,
    info="host",
    is_show_more=True,
)

filter_nagios_flag_with_register(
    ident="host_notifications_enabled",
    title=_l("Host notifications enabled"),
    sort_index=133,
    info="host",
)

filter_nagios_flag_with_register(
    ident="service_acknowledged",
    title=_l("Problem acknowledged"),
    sort_index=230,
    info="service",
)

filter_nagios_flag_with_register(
    ident="service_in_notification_period",
    title=_l("Service in notification period"),
    sort_index=231,
    info="service",
)

filter_nagios_flag_with_register(
    ident="service_in_service_period",
    title=_l("Service in service period"),
    sort_index=231,
    info="service",
)

filter_nagios_flag_with_register(
    ident="service_active_checks_enabled",
    title=_l("Active checks enabled"),
    sort_index=233,
    info="service",
    is_show_more=True,
)

filter_nagios_flag_with_register(
    ident="service_notifications_enabled",
    title=_l("Notifications enabled"),
    sort_index=234,
    info="service",
)

filter_nagios_flag_with_register(
    ident="service_is_flapping",
    title=_l("Flapping"),
    sort_index=236,
    info="service",
    is_show_more=True,
)

filter_nagios_flag_with_register(
    ident="service_scheduled_downtime_depth",
    title=_l("Service in downtime"),
    sort_index=231,
    info="service",
)

filter_nagios_flag_with_register(
    ident="host_scheduled_downtime_depth",
    title=_l("Host in downtime"),
    sort_index=132,
    info="host",
)


class SiteFilter(Filter):
    def __init__(
        self,
        *,
        ident: str,
        title: Union[str, LazyString],
        sort_index: int,
        enforce: bool,
        description: Union[None, str, LazyString] = None,
        htmlvar: str = "site",
        is_show_more: bool = False,
    ) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info="host",
            htmlvars=[htmlvar],
            link_columns=[],
            description=description,
            is_show_more=is_show_more,
        )
        self.enforce = enforce

    @staticmethod
    def _options() -> List[Tuple[str, str]]:
        return filter_cme_choices() if cmk_version.is_managed_edition() else filter_cre_choices()

    def display(self, value: FilterHTTPVariables) -> None:
        html.dropdown("site", ([] if self.enforce else [("", "")]) + self._options())

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        if cmk_version.is_managed_edition():
            return filter_cme_heading_info(value)
        return filter_cre_heading_info(value)

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {"site": row["site"]}


filter_registry.register(
    SiteFilter(
        ident="siteopt",
        title=_l("Site"),
        sort_index=500,
        description=_l("Optional selection of a site"),
        enforce=False,
    )
)

filter_registry.register(
    SiteFilter(
        ident="site",
        title=_l("Site (enforced)"),
        sort_index=501,
        description=_l("Selection of site is enforced, use this filter for joining"),
        enforce=True,
        is_show_more=True,
    )
)


class MultipleSitesFilter(SiteFilter):
    def get_request_sites(self, value: FilterHTTPVariables) -> List[str]:
        return [x for x in value.get(self.htmlvars[0], "").strip().split("|") if x]

    def display(self, value: FilterHTTPVariables):
        sites_vs = DualListChoice(choices=self._options(), rows=4)
        sites_vs.render_input(self.htmlvars[0], self.get_request_sites(value))


filter_registry.register(
    MultipleSitesFilter(
        ident="sites",
        title=_l("Multiple Sites"),
        sort_index=502,
        description=_l("Associative selection of multiple sites"),
        enforce=False,
        htmlvar="sites",
    )
)


# info: usually either "host" or "service"
# column: a livestatus column of type int or float
class FilterNumberRange(Filter):  # type is int
    def __init__(
        self, *, ident: str, title: Union[str, LazyString], sort_index: int, info: str, column: str
    ) -> None:
        self.column = column
        varnames = [ident + "_from", ident + "_until"]
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=varnames,
            link_columns=[],
            is_show_more=True,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.write_text(_("From:") + "&nbsp;")
        html.text_input(
            self.htmlvars[0], default_value=value.get(self.htmlvars[0], ""), style="width: 80px;"
        )
        html.write_text(" &nbsp; " + _("To:") + "&nbsp;")
        html.text_input(
            self.htmlvars[1], default_value=value.get(self.htmlvars[1], ""), style="width: 80px;"
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        lql = ""
        for i, op in [(0, ">="), (1, "<=")]:
            try:
                lql += "Filter: %s %s %d\n" % (self.column, op, int(value[self.htmlvars[i]]))
            except Exception:
                pass
        return lql


filter_registry.register(
    FilterNumberRange(
        ident="host_notif_number",
        title=_l("Current Host Notification Number"),
        sort_index=232,
        info="host",
        column="current_notification_number",
    )
)

filter_registry.register(
    FilterNumberRange(
        ident="svc_notif_number",
        title=_l("Current Service Notification Number"),
        sort_index=232,
        info="service",
        column="current_notification_number",
    )
)

filter_registry.register(
    FilterNumberRange(
        ident="host_num_services",
        title=_l("Number of Services of the Host"),
        sort_index=234,
        info="host",
        column="num_services",
    )
)

filter_registry.register(
    FilterTime(
        ident="svc_last_state_change",
        title=_l("Last service state change"),
        sort_index=250,
        info="service",
        column="service_last_state_change",
    )
)

filter_registry.register(
    FilterTime(
        ident="svc_last_check",
        title=_l("Last service check"),
        sort_index=251,
        info="service",
        column="service_last_check",
    )
)

filter_registry.register(
    FilterTime(
        ident="host_last_state_change",
        title=_l("Last host state change"),
        sort_index=250,
        info="host",
        column="host_last_state_change",
    )
)

filter_registry.register(
    FilterTime(
        ident="host_last_check",
        title=_l("Last host check"),
        sort_index=251,
        info="host",
        column="host_last_check",
    )
)

filter_registry.register(
    FilterTime(
        ident="comment_entry_time",
        title=_l("Time of comment"),
        sort_index=253,
        info="comment",
        column="comment_entry_time",
    )
)

filter_registry.register(
    FilterText(
        ident="comment_comment",
        title=_l("Comment"),
        sort_index=258,
        info="comment",
        legacy_filter=legacy_filters.FilterText(
            column="comment_comment", htmlvar="comment_comment", op="~~", negateable=True
        ),
    )
)

filter_registry.register(
    FilterText(
        ident="comment_author",
        title=_l("Author comment"),
        sort_index=259,
        info="comment",
        legacy_filter=legacy_filters.FilterText(
            column="comment_author", htmlvar="comment_author", op="~~", negateable=True
        ),
    )
)

filter_registry.register(
    FilterTime(
        ident="downtime_entry_time",
        title=_l("Time when downtime was created"),
        sort_index=253,
        info="downtime",
        column="downtime_entry_time",
    )
)

filter_registry.register(
    FilterText(
        ident="downtime_comment",
        title=_l("Downtime comment"),
        sort_index=254,
        info="downtime",
        legacy_filter=legacy_filters.FilterText(
            column="downtime_comment", htmlvar="downtime_comment", op="~"
        ),
    )
)

filter_registry.register(
    FilterTime(
        ident="downtime_start_time",
        title=_l("Start of downtime"),
        sort_index=255,
        info="downtime",
        column="downtime_start_time",
    )
)

filter_registry.register(
    FilterText(
        ident="downtime_author",
        title=_l("Downtime author"),
        sort_index=256,
        info="downtime",
        legacy_filter=legacy_filters.FilterText(
            column="downtime_author", htmlvar="downtime_author", op="~"
        ),
    )
)

filter_registry.register(
    FilterTime(
        ident="logtime",
        title=_l("Time of log entry"),
        sort_index=252,
        info="log",
        column="log_time",
    )
)

# INFO          0 // all messages not in any other class
# ALERT         1 // alerts: the change service/host state
# PROGRAM       2 // important programm events (restart, ...)
# NOTIFICATION  3 // host/service notifications
# PASSIVECHECK  4 // passive checks
# COMMAND       5 // external commands
# STATE         6 // initial or current states
# ALERT HANDLERS 8


@filter_registry.register_instance
class FilterLogClass(Filter):
    def __init__(self):
        self.log_classes = [
            (0, _l("Informational")),
            (1, _l("Alerts")),
            (2, _l("Program")),
            (3, _l("Notifications")),
            (4, _l("Passive checks")),
            (5, _l("Commands")),
            (6, _l("States")),
            (8, _l("Alert Handlers")),
        ]

        super().__init__(
            ident="log_class",
            title=_l("Logentry class"),
            sort_index=255,
            info="log",
            htmlvars=["logclass_filled"] + ["logclass%d" % l for l, _c in self.log_classes],
            link_columns=[],
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.hidden_field("logclass_filled", "1", add_var=True)
        html.open_table(cellspacing="0", cellpadding="0")
        checkbox_default = not any(value.values())  # everything by default
        if config.filter_columns == 1:
            num_cols = 4
        else:
            num_cols = 2
        col = 1
        for l, c in self.log_classes:
            if col == 1:
                html.open_tr()
            html.open_td()
            html.checkbox("logclass%d" % l, bool(value.get("logclass%d" % l, checkbox_default)))
            html.write_text(str(c))
            html.close_td()
            if col == num_cols:
                html.close_tr()
                col = 1
            else:
                col += 1
        if col < num_cols:
            html.open_td()
            html.close_td()
            html.close_tr()
        html.close_table()

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if not any(value.values()):
            return ""  # Do not apply this filter

        headers = [str(l) for l, _c in self.log_classes if value.get("logclass%d" % l)]

        if not headers:
            return "Limit: 0\n"  # no class allowed
        return lq_logic("Filter: class =", headers, "Or")


filter_registry.register(
    FilterText(
        ident="log_plugin_output",
        title=_l("Log: plugin output"),
        sort_index=202,
        info="log",
        legacy_filter=legacy_filters.FilterText(
            column="log_plugin_output", htmlvar="log_plugin_output", op="~~"
        ),
    )
)

filter_registry.register(
    FilterText(
        ident="log_type",
        title=_l("Log: message type"),
        sort_index=203,
        info="log",
        legacy_filter=legacy_filters.FilterText(column="log_type", htmlvar="log_type", op="~~"),
        show_heading=False,
    )
)

filter_registry.register(
    FilterText(
        ident="log_state_type",
        title=_l('Log: state type (DEPRECATED: Use "state information")'),
        sort_index=204,
        info="log",
        legacy_filter=legacy_filters.FilterText(
            column="log_state_type", htmlvar="log_state_type", op="~~"
        ),
    )
)

filter_registry.register(
    FilterText(
        ident="log_state_info",
        title=_l("Log: state information"),
        sort_index=204,
        info="log",
        legacy_filter=legacy_filters.FilterText(
            column="log_state_info", htmlvar="log_state_info", op="~~"
        ),
    )
)


class FilterLogContactName(FilterText):
    """Special filter class to correctly filter the column contact_name from the log table. This
    list contains comma-separated contact names (user ids), but it is of type string."""

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if current_value := value.get(self.htmlvars[0]):
            new_value = dict(value.items())
            new_value[self.htmlvars[0]] = "(,|^)" + current_value.replace(".", "\\.") + "(,|$)"
            return self.legacy_filter._filter(new_value)
        return ""


filter_registry.register(
    FilterLogContactName(
        ident="log_contact_name",
        title=_l("Log: contact name (exact match)"),
        sort_index=260,
        description=_l("Exact match, used for linking"),
        info="log",
        legacy_filter=legacy_filters.FilterText(
            column="log_contact_name", htmlvar="log_contact_name", op="~"
        ),
    )
)

filter_registry.register(
    FilterRegExp(
        ident="log_contact_name_regex",
        title=_l("Log: contact name"),
        sort_index=261,
        info="log",
        legacy_filter=legacy_filters.FilterText(
            column="log_contact_name", htmlvar="log_contact_name_regex", op="~~", negateable=True
        ),
    )
)

filter_registry.register(
    FilterRegExp(
        ident="log_command_name_regex",
        title=_l("Log: command"),
        sort_index=262,
        info="log",
        legacy_filter=legacy_filters.FilterText(
            column="log_command_name", htmlvar="log_command_name_regex", op="~~", negateable=True
        ),
    )
)


@filter_registry.register_instance
class FilterLogState(Filter):
    def __init__(self):
        self._items = [
            ("h0", "host", 0, _l("Up")),
            ("h1", "host", 1, _l("Down")),
            ("h2", "host", 2, _l("Unreachable")),
            ("s0", "service", 0, _l("OK")),
            ("s1", "service", 1, _l("Warning")),
            ("s2", "service", 2, _l("Critical")),
            ("s3", "service", 3, _l("Unknown")),
        ]

        super().__init__(
            ident="log_state",
            title=_l("Type of alerts of hosts and services"),
            sort_index=270,
            info="log",
            htmlvars=["log_state_filled"] + ["logst_" + e[0] for e in self._items],
            link_columns=[],
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.hidden_field("log_state_filled", "1", add_var=True)
        html.open_table(class_="alertstatefilter")
        html.open_tr()
        html.open_td()
        html.begin_checkbox_group()
        mobile = is_mobile(request, response)
        checkbox_default = not any(value.values())  # everything by default
        for varsuffix, what, state, text in self._items:
            if state == 0:
                title = _("Host") if what == "host" else _("Service")
                html.u("%s:" % title)
                html.close_td()
                html.open_td()
            html.checkbox(
                "logst_" + varsuffix,
                bool(value.get("logst_" + varsuffix, checkbox_default)),
                label=str(text),
            )
            if not mobile:
                html.br()
            if varsuffix == "h2":
                html.close_td()
                html.open_td()
        html.end_checkbox_group()
        html.close_td()
        html.close_tr()
        html.close_table()

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if not any(value.values()):
            return ""  # Do not apply this filter

        headers = []
        for varsuffix, what, state, _text in self._items:
            if value.get("logst_" + varsuffix):
                headers.append(
                    "Filter: log_type ~ %s .*\nFilter: log_state = %d\nAnd: 2\n"
                    % (what.upper(), state)
                )

        if len(headers) == 0:
            return "Limit: 0\n"  # no allowed state
        if len(headers) == len(self._items):
            return ""  # all allowed or form not filled in
        return "".join(headers) + ("Or: %d\n" % len(headers))


@filter_registry.register_instance
class FilterLogNotificationPhase(FilterOption):
    def __init__(self):
        super().__init__(
            ident="log_notification_phase",
            title=_l("Notification phase"),
            sort_index=271,
            info="log",
            legacy_filter=legacy_filters.FilterTristate(
                ident="log_notification_phase",
                filter_code=legacy_filters.log_notification_phase("log_command_name"),
                options=legacy_filters.tri_state_log_notifications_options(),
            ),
        )


def bi_aggr_service_used(on: bool, context: VisualContext, rows: Rows) -> Rows:
    # should be in legacy_filters, but it creates a cyclical import at the moment
    return [
        row
        for row in rows
        if bi.is_part_of_aggregation(row["host_name"], row["service_description"]) is on
    ]


@filter_registry.register_instance
class FilterAggrServiceUsed(FilterOption):
    def __init__(self):
        super().__init__(
            ident="aggr_service_used",
            title=_l("Used in BI aggregate"),
            sort_index=300,
            info="service",
            legacy_filter=legacy_filters.FilterTristate(
                ident="aggr_service_used",
                filter_code=lambda x: "",
                filter_rows=bi_aggr_service_used,
            ),
            is_show_more=True,
        )


filter_registry.register(
    FilterText(
        ident="downtime_id",
        title=_l("Downtime ID"),
        sort_index=301,
        info="downtime",
        legacy_filter=legacy_filters.FilterText(
            column="downtime_id", htmlvar="downtime_id", op="="
        ),
    )
)


class TagFilter(Filter):
    def __init__(
        self,
        *,
        ident: str,
        title: Union[str, LazyString],
        object_type: str,
        is_show_more: bool = False,
    ):
        self.count = 3
        self._object_type = object_type

        htmlvars: List[str] = []
        for num in range(self.count):
            htmlvars += [
                "%s%d_grp" % (self._var_prefix, num),
                "%s%d_op" % (self._var_prefix, num),
                "%s%d_val" % (self._var_prefix, num),
            ]

        super().__init__(
            ident=ident,
            title=title,
            sort_index=302,
            info=object_type,
            htmlvars=htmlvars,
            link_columns=[],
            is_show_more=is_show_more,
        )

    @property
    def _var_prefix(self):
        return "%s_tag_" % (self._object_type)

    def display(self, value: FilterHTTPVariables) -> None:
        groups = config.tags.get_tag_group_choices()
        operators: Choices = [
            ("is", "="),
            ("isnot", "≠"),
        ]

        grouped: Dict[str, Choices] = {}
        for tag_group in config.tags.tag_groups:
            grouped.setdefault(tag_group.id, [("", "")])

            for grouped_tag in tag_group.tags:
                tag_id = "" if grouped_tag.id is None else grouped_tag.id
                grouped[tag_group.id].append((tag_id, grouped_tag.title))

        html.javascript(
            "cmk.utils.set_tag_groups(%s, %s);"
            % (json.dumps(self._object_type), json.dumps(grouped))
        )
        html.open_table()
        group_choices: Choices = [("", "")]
        for num in range(self.count):
            prefix = "%s%d" % (self._var_prefix, num)
            html.open_tr()
            html.open_td()
            html.dropdown(
                prefix + "_grp",
                group_choices + list(groups),
                onchange="cmk.utils.tag_update_value('%s', '%s', this.value)"
                % (self._object_type, prefix),
                style="width:129px",
                ordered=True,
                class_="grp",
            )
            html.close_td()
            html.open_td()
            empty_choices: Choices = [("", "")]
            html.dropdown(
                prefix + "_op",
                empty_choices + operators,
                style="width:36px",
                ordered=True,
                class_="op",
            )
            html.close_td()
            html.open_td()

            if item := value.get(prefix + "_grp", ""):
                if item not in grouped:
                    raise MKUserError(
                        prefix + "_grp", _("The requested item %s does not exist") % item
                    )

                choices: Choices = grouped[item]
            else:
                choices = [("", "")]

            html.dropdown(prefix + "_val", choices, style="width:129px", ordered=True, class_="val")
            html.close_td()
            html.close_tr()
        html.close_table()

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        headers = []

        # Do not restrict to a certain number, because we'd like to link to this
        # via an URL, e.g. from the virtual host tree snapin
        num = 0
        while value.get("%s%d_op" % (self._var_prefix, num)):
            prefix = "%s%d" % (self._var_prefix, num)
            num += 1

            op = value.get(prefix + "_op")
            tag_group = config.tags.get_tag_group(value[prefix + "_grp"])
            tag = value.get(prefix + "_val")

            if not tag_group or not op:
                continue

            headers.append(self._tag_filter(tag_group.id, tag, negate=op != "is"))

        if headers:
            return "\n".join(headers) + "\n"
        return ""

    def _tag_filter(self, tag_group, tag, negate):
        return "Filter: %s_tags %s %s %s" % (
            livestatus.lqencode(self._object_type),
            "!=" if negate else "=",
            livestatus.lqencode(livestatus.quote_dict(tag_group)),
            livestatus.lqencode(livestatus.quote_dict(tag)),
        )


filter_registry.register(
    TagFilter(
        ident="host_tags",
        title=_l("Host Tags"),
        object_type="host",
    )
)

filter_registry.register(
    TagFilter(
        ident="service_tags",
        title=_l("Tags"),
        object_type="service",
        is_show_more=True,
    )
)


@filter_registry.register_instance
class FilterHostAuxTags(Filter):
    def __init__(self):
        self.count = 3
        self.prefix = "host_auxtags"

        htmlvars = []
        for num in range(self.count):
            htmlvars.append("%s_%d" % (self.prefix, num))
            htmlvars.append("%s_%d_neg" % (self.prefix, num))

        super().__init__(
            ident="host_auxtags",
            title=_l("Host Auxiliary Tags"),
            sort_index=302,
            info="host",
            htmlvars=htmlvars,
            link_columns=[],
            is_show_more=True,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        for num in range(self.count):
            varname = "%s_%d" % (self.prefix, num)
            html.dropdown(
                varname, self._options(), deflt=value.get(varname, ""), ordered=True, class_="neg"
            )
            html.open_nobr()
            html.checkbox(varname + "_neg", bool(value.get(varname)), label=_("negate"))
            html.close_nobr()

    @staticmethod
    def _options() -> Choices:
        aux_tag_choices: Choices = [("", "")]
        return aux_tag_choices + list(config.tags.aux_tag_list.get_choices())

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        headers = []

        # Do not restrict to a certain number, because we'd like to link to this
        # via an URL, e.g. from the virtual host tree snapin
        num = 0
        while (this_tag := value.get("%s_%d" % (self.prefix, num))) is not None:
            if this_tag:
                negate = value.get("%s_%d_neg" % (self.prefix, num))
                headers.append(self._host_auxtags_filter(this_tag, negate))
            num += 1

        if headers:
            return "\n".join(headers) + "\n"
        return ""

    def _host_auxtags_filter(self, tag, negate):
        return "Filter: host_tags %s %s %s" % (
            "!=" if negate else "=",
            livestatus.lqencode(livestatus.quote_dict(tag)),
            livestatus.lqencode(livestatus.quote_dict(tag)),
        )


class LabelFilter(Filter):
    def __init__(self, *, ident: str, title: Union[str, LazyString], object_type: str) -> None:
        self._object_type = object_type
        super().__init__(
            ident=ident,
            title=title,
            sort_index=301,
            info=object_type,
            htmlvars=[self._var_prefix],
            link_columns=[],
        )

    @property
    def _var_prefix(self):
        return "%s_label" % self._object_type

    @property
    def _column(self):
        return "%s_labels" % self._object_type

    def _parsed_value(self, value: FilterHTTPVariables):
        return self._valuespec()._from_html_vars(value.get(self._var_prefix, ""), self._var_prefix)

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        return " ".join(":".join(e) for e in sorted(self._parsed_value(value).items()))

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {self.htmlvars[0]: row[self._column]}

    def _valuespec(self):
        return Labels(world=Labels.World.CORE)

    def display(self, value: FilterHTTPVariables) -> None:
        self._valuespec().render_input(self._var_prefix, value)

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if value := self._parsed_value(value):
            return encode_labels_for_livestatus(self._column, iter(value.items())) + "\n"
        return ""


filter_registry.register(
    LabelFilter(
        ident="host_labels",
        title=_l("Host labels"),
        object_type="host",
    )
)

filter_registry.register(
    LabelFilter(
        ident="service_labels",
        title=_l("Service labels"),
        object_type="service",
    )
)


class FilterCustomAttribute(Filter):
    def __init__(
        self,
        *,
        ident: str,
        title: Union[str, LazyString],
        info: str,
        choice_func: Callable[[], Choices],
    ):
        super().__init__(
            ident=ident,
            title=title,
            sort_index=103,
            info=info,
            htmlvars=[self.name_varname(ident), self.value_varname(ident)],
            link_columns=[],
            is_show_more=True,
        )
        self._custom_attribute_choices = choice_func

    def name_varname(self, ident):
        return "%s_name" % ident

    def value_varname(self, ident):
        return "%s_value" % ident

    def display(self, value: FilterHTTPVariables) -> None:

        html.dropdown(
            self.name_varname(self.ident),
            self._options(self._custom_attribute_choices()),
            deflt=value.get(self.name_varname(self.ident), ""),
        )
        html.text_input(
            self.value_varname(self.ident),
            default_value=value.get(self.value_varname(self.ident), ""),
        )

    @staticmethod
    def _options(custom_attribute_choices: Choices) -> Choices:
        choices: Choices = [("", "")]
        choices += custom_attribute_choices
        return choices

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if not value.get(self.name_varname(self.ident)):
            return ""

        items = {k: v for k, v in self._custom_attribute_choices() if k is not None}
        attribute_id = value[self.name_varname(self.ident)]
        if attribute_id not in items:
            raise MKUserError(
                self.name_varname(self.ident),
                _("The requested item %s does not exist") % attribute_id,
            )
        val = value[self.value_varname(self.ident)]
        return "Filter: %s_custom_variables ~~ %s ^%s\n" % (
            self.info,
            livestatus.lqencode(attribute_id.upper()),
            livestatus.lqencode(val),
        )


def _service_attribute_choices() -> Choices:
    choices: Choices = []
    for ident, attr_spec in config.custom_service_attributes.items():
        choices.append((ident, attr_spec["title"]))
    return sorted(choices, key=lambda x: x[1])


filter_registry.register(
    FilterCustomAttribute(
        ident="service_custom_variable",
        title=_l("Service custom attribute"),
        info="service",
        choice_func=_service_attribute_choices,
    )
)


def _host_attribute_choices() -> Choices:
    choices: Choices = []
    for attr_spec in config.wato_host_attrs:
        choices.append((attr_spec["name"], attr_spec["title"]))
    return sorted(choices, key=lambda x: x[1])


filter_registry.register(
    FilterCustomAttribute(
        ident="host_custom_variable",
        title=_l("Host custom attribute"),
        info="host",
        choice_func=_host_attribute_choices,
    )
)


# choices = [ (value, "readable"), .. ]
class FilterECServiceLevelRange(Filter):
    def __init__(self, *, ident: str, title: Union[str, LazyString], info: str) -> None:
        self.lower_bound_varname = "%s_lower" % ident
        self.upper_bound_varname = "%s_upper" % ident
        super().__init__(
            ident=ident,
            title=title,
            sort_index=310,
            info=info,
            htmlvars=[
                self.lower_bound_varname,
                self.upper_bound_varname,
            ],
            link_columns=[],
            is_show_more=True,
        )

    @staticmethod
    def _options() -> List[Tuple[str, str]]:
        choices = sorted(config.mkeventd_service_levels[:])
        return [("", "")] + [(str(x[0]), "%s - %s" % (x[0], x[1])) for x in choices]

    def display(self, value: FilterHTTPVariables) -> None:
        selection = self._options()
        html.open_div(class_="service_level min")
        html.write_text("From")
        html.dropdown(
            self.lower_bound_varname, selection, deflt=value.get(self.lower_bound_varname, "")
        )
        html.close_div()
        html.open_div(class_="service_level max")
        html.write_text("To")
        html.dropdown(
            self.upper_bound_varname, selection, deflt=value.get(self.upper_bound_varname, "")
        )
        html.close_div()

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        lower_bound = value.get(self.lower_bound_varname)
        upper_bound = value.get(self.upper_bound_varname)
        # NOTE: We need this special case only because our construction of the
        # disjunction is broken. We should really have a Livestatus Query DSL...
        if not lower_bound and not upper_bound:
            return ""

        if lower_bound:
            match_lower = lambda val, lo=int(lower_bound): lo <= val
        else:
            match_lower = lambda val, lo=0: True

        if upper_bound:
            match_upper = lambda val, hi=int(upper_bound): val <= hi
        else:
            match_upper = lambda val, hi=0: True

        filterline = "Filter: %s_custom_variable_names >= EC_SL\n" % self.info

        filterline_values = [
            str(val)
            for val, _readable in config.mkeventd_service_levels
            if match_lower(val) and match_upper(val)
        ]

        return filterline + lq_logic(
            "Filter: %s_custom_variable_values >=" % self.info, filterline_values, "Or"
        )


filter_registry.register(
    FilterECServiceLevelRange(
        ident="svc_service_level",
        title=_l("Service service level"),
        info="service",
    )
)

filter_registry.register(
    FilterECServiceLevelRange(
        ident="hst_service_level",
        title=_l("Host service level"),
        info="host",
    )
)


class FilterStarred(FilterOption):
    # TODO: Rename "what"
    def __init__(
        self,
        *,
        what: Literal["host", "service"],
        title: Union[str, LazyString],
        sort_index: int,
    ) -> None:
        super().__init__(
            ident=what + "_favorites",
            title=title,
            sort_index=sort_index,
            info=what,
            legacy_filter=legacy_filters.FilterTristate(
                ident=what + "_favorites",
                filter_code=legacy_filters.starred(what),
            ),
            is_show_more=True,
        )


filter_registry.register(
    FilterStarred(
        what="host",
        title=_l("Favorite Hosts"),
        sort_index=501,
    )
)

filter_registry.register(
    FilterStarred(
        what="service",
        title=_l("Favorite Services"),
        sort_index=501,
    )
)


@filter_registry.register_instance
class FilterDiscoveryState(Filter):
    def __init__(self):
        super().__init__(
            ident="discovery_state",
            title=_l("Discovery state"),
            sort_index=601,
            info="discovery",
            htmlvars=[o[0] for o in self._options()],
            link_columns=[],
        )

    @staticmethod
    def _options() -> List[Tuple[str, str]]:
        return [
            ("discovery_state_ignored", _("Hidden")),
            ("discovery_state_vanished", _("Vanished")),
            ("discovery_state_unmonitored", _("New")),
        ]

    def display(self, value: FilterHTTPVariables) -> None:
        html.begin_checkbox_group()
        checkbox_default = not any(value.values())  # everything by default
        for varname, title in self._options():
            html.checkbox(varname, bool(value.get(varname, checkbox_default)), label=str(title))
        html.end_checkbox_group()

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return ""

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        filter_options = context.get(self.ident, {})
        return [
            row for row in rows if filter_options.get("discovery_state_" + row["discovery_state"])
        ]


@filter_registry.register_instance
class FilterAggrGroup(Filter):
    def __init__(self):
        self.column = "aggr_group"
        super().__init__(
            ident="aggr_group",
            title=_l("Aggregation group"),
            sort_index=90,
            info=self.column,
            htmlvars=[self.column],
            link_columns=[self.column],
        )

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {self.htmlvars[0]: row[self.column]}

    def display(self, value: FilterHTTPVariables) -> None:
        htmlvar = self.htmlvars[0]
        html.dropdown(htmlvar, self._options(), deflt=value.get(htmlvar, ""))

    @staticmethod
    def _options() -> Choices:
        empty_choices: Choices = [("", "")]
        return empty_choices + bi.aggregation_group_choices()

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.ident, {})
        if group := value.get(self.htmlvars[0], ""):
            return [row for row in rows if row[self.column] == group]
        return rows

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        return value.get(self.htmlvars[0])


@filter_registry.register_instance
class FilterAggrGroupTree(Filter):
    def __init__(self):
        self.column = "aggr_group_tree"
        super().__init__(
            ident="aggr_group_tree",
            title=_l("Aggregation group tree"),
            sort_index=91,
            info="aggr_group",
            htmlvars=[self.column],
            link_columns=[self.column],
        )

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {self.htmlvars[0]: row[self.column]}

    def display(self, value: FilterHTTPVariables) -> None:
        htmlvar = self.htmlvars[0]
        html.dropdown(htmlvar, self._options(), deflt=value.get(htmlvar, ""))

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        return value.get(self.htmlvars[0])

    @staticmethod
    def _options() -> Choices:
        def _build_tree(group, parent, path):
            this_node = group[0]
            path = path + (this_node,)
            child = parent.setdefault(this_node, {"__path__": path})
            children = group[1:]
            if children:
                child = child.setdefault("__children__", {})
                _build_tree(children, child, path)

        def _build_selection(selection, tree, index):
            index += 1
            for _unused, sub_tree in tree.items():
                selection.append(_get_selection_entry(sub_tree, index, True))
                _build_selection(selection, sub_tree.get("__children__", {}), index)

        def _get_selection_entry(tree, index, prefix=None):
            path = tree["__path__"]
            if prefix:
                title_prefix = ("\u00a0" * 6 * index) + "\u2514\u2500 "
            else:
                title_prefix = ""
            return ("/".join(path), title_prefix + path[index])

        tree: Dict[str, Any] = {}
        for group in bi.get_aggregation_group_trees():
            _build_tree(group.split("/"), tree, tuple())

        selection: Choices = []
        index = 0
        for _unused, sub_tree in tree.items():
            selection.append(_get_selection_entry(sub_tree, index))
            _build_selection(selection, sub_tree.get("__children__", {}), index)

        empty: Choices = [("", "")]

        return empty + selection


# how is either "regex" or "exact"
class BITextFilter(Filter):
    def __init__(
        self,
        *,
        ident: str,
        title: Union[str, LazyString],
        sort_index: int,
        what: str,
        how: str = "regex",
        suffix: str = "",
    ) -> None:
        self.how = how
        self.column = "aggr_" + what
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info="aggr",
            htmlvars=[self.column + suffix],
            link_columns=[self.column],
        )

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {self.htmlvars[0]: row[self.column]}

    def display(self, value: FilterHTTPVariables) -> None:
        html.text_input(self.htmlvars[0], default_value=value.get(self.htmlvars[0], ""))

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        return value.get(self.htmlvars[0])

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        values = context.get(self.ident, {})
        val = values.get(self.htmlvars[0])

        if not val:
            return rows
        if self.how == "regex":
            try:
                reg = re.compile(val.lower())
            except re.error as e:
                user_errors.add(
                    MKUserError(self.htmlvars[0], _("Invalid regular expression: %s") % e)
                )
                return rows

            return [row for row in rows if reg.search(row[self.column].lower())]
        return [row for row in rows if row[self.column] == val]


filter_registry.register(
    BITextFilter(
        ident="aggr_name_regex",
        title=_l("Aggregation name regex"),
        sort_index=120,
        what="name",
        suffix="_regex",
    )
)

filter_registry.register(
    BITextFilter(
        ident="aggr_name",
        title=_l("Aggregation name (exact match)"),
        sort_index=120,
        what="name",
        how="exact",
    )
)

filter_registry.register(
    BITextFilter(
        ident="aggr_output",
        title=_l("Aggregation output"),
        sort_index=121,
        what="output",
    )
)


@filter_registry.register_instance
class FilterAggrHosts(Filter):
    def __init__(self):
        super().__init__(
            ident="aggr_hosts",
            title=_l("Affected hosts contain"),
            sort_index=130,
            info="aggr",
            htmlvars=["aggr_host_site", "aggr_host_host"],
            link_columns=[],
            description=_l(
                "Filter for all aggregations that base on status information of that host. "
                "Exact match (no regular expression)"
            ),
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.text_input(self.htmlvars[1], default_value=value.get(self.htmlvars[1], ""))

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        return value.get(self.htmlvars[1])

    def find_host(self, host, hostlist):
        return any((h == host for _s, h in hostlist))

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {
            "aggr_host_host": row["host_name"],
            "aggr_host_site": row["site"],
        }

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        values = context.get(self.ident, {})
        if val := values.get(self.htmlvars[1]):
            return [row for row in rows if self.find_host(val, row["aggr_hosts"])]
        return rows


@filter_registry.register_instance
class FilterAggrService(Filter):
    """Not performing filter(), nor filter_table(). The filtering is done directly in BI by
    bi.table(), which calls service_spec()."""

    def __init__(self):
        super().__init__(
            ident="aggr_service",
            title=_l("Affected by service"),
            sort_index=131,
            info="aggr",
            htmlvars=["aggr_service_site", "aggr_service_host", "aggr_service_service"],
            link_columns=[],
            description=_l(
                "Filter for all aggregations that are affected by one specific service on a specific host (no regular expression)"
            ),
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.write_text(_("Host") + ": ")
        html.text_input(self.htmlvars[1], default_value=value.get(self.htmlvars[1], ""))
        html.write_text(_("Service") + ": ")
        html.text_input(self.htmlvars[2], default_value=value.get(self.htmlvars[2], ""))

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        return value.get(self.htmlvars[1], "") + " / " + value.get(self.htmlvars[2], "")

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {
            "site": row["site"],
            "host": row["host_name"],
            "service": row["service_description"],
        }


class BIStatusFilter(Filter):
    # TODO: Rename "what"
    def __init__(
        self, ident: str, title: Union[str, LazyString], sort_index: int, what: str
    ) -> None:
        self.column = "aggr_" + what + "state"
        if what == "":
            self.code = "r"
        else:
            self.code = what[0]
        self.prefix = "bi%ss" % self.code
        vars_ = ["%s%s" % (self.prefix, x) for x in [-1, 0, 1, 2, 3, "_filled"]]
        if self.code == "a":
            vars_.append(self.prefix + "n")
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info="aggr",
            htmlvars=vars_,
            link_columns=[],
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return ""

    def _filter_used(self, value: FilterHTTPVariables) -> FilterHeader:
        return value.get(self.prefix + "_filled", "")

    def display(self, value: FilterHTTPVariables) -> None:
        html.hidden_field(self.prefix + "_filled", "1", add_var=True)
        checkbox_default = not self._filter_used(value)  # everything by default

        for varend, text in self._options():
            if self.code != "a" and varend == "n":
                continue  # no unset for read and effective state
            if varend == "n":
                html.br()
            var = self.prefix + varend
            html.checkbox(var, deflt=bool(value.get(var, checkbox_default)), label=text)

    @staticmethod
    def _options() -> List[Tuple[str, str]]:
        return [
            ("0", _("OK")),
            ("1", _("WARN")),
            ("2", _("CRIT")),
            ("3", _("UNKN")),
            ("-1", _("PEND")),
            ("n", _("no assumed state set")),
        ]

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        value = context.get(self.ident, {})
        if not self._filter_used(value):
            return rows

        allowed_states = []
        for i in ["0", "1", "2", "3", "-1", "n"]:
            if value.get(self.prefix + i):
                if i == "n":
                    s = None
                else:
                    s = int(i)
                allowed_states.append(s)
        newrows = []
        for row in rows:
            if row[self.column] is not None:
                s = row[self.column]["state"]
            else:
                s = None
            if s in allowed_states:
                newrows.append(row)
        return newrows


filter_registry.register(
    BIStatusFilter(
        ident="aggr_state",
        title=_l(" State"),
        sort_index=150,
        what="",
    )
)

filter_registry.register(
    BIStatusFilter(
        ident="aggr_effective_state",
        title=_l("Effective  State"),
        sort_index=151,
        what="effective_",
    )
)

filter_registry.register(
    BIStatusFilter(
        ident="aggr_assumed_state",
        title=_l("Assumed  State"),
        sort_index=152,
        what="assumed_",
    )
)

filter_registry.register(
    FilterText(
        ident="event_id",
        title=_l("Event ID"),
        sort_index=200,
        info="event",
        legacy_filter=legacy_filters.FilterText(column="event_id", htmlvar="event_id", op="="),
    )
)

filter_registry.register(
    FilterText(
        ident="event_rule_id",
        title=_l("ID of rule"),
        sort_index=200,
        info="event",
        legacy_filter=legacy_filters.FilterText(
            column="event_rule_id", htmlvar="event_rule_id", op="="
        ),
    )
)

filter_registry.register(
    FilterText(
        ident="event_text",
        title=_l("Message/Text of event"),
        sort_index=201,
        info="event",
        legacy_filter=legacy_filters.FilterText(column="event_text", htmlvar="event_text", op="~~"),
    )
)

filter_registry.register(
    FilterText(
        ident="event_application",
        title=_l("Application / Syslog-Tag"),
        sort_index=201,
        info="event",
        legacy_filter=legacy_filters.FilterText(
            column="event_application", htmlvar="event_application", op="~~"
        ),
    )
)

filter_registry.register(
    FilterText(
        ident="event_contact",
        title=_l("Contact Person"),
        sort_index=201,
        info="event",
        legacy_filter=legacy_filters.FilterText(
            column="event_contact", htmlvar="event_contact", op="~~"
        ),
    )
)

filter_registry.register(
    FilterText(
        ident="event_comment",
        title=_l("Comment to the event"),
        sort_index=201,
        info="event",
        legacy_filter=legacy_filters.FilterText(
            column="event_comment", htmlvar="event_comment", op="~~"
        ),
    )
)

filter_registry.register(
    FilterRegExp(
        ident="event_host_regex",
        title=_l("Hostname of original event"),
        sort_index=201,
        info="event",
        legacy_filter=legacy_filters.FilterText(
            column="event_host", htmlvar="event_host_regex", op="~~"
        ),
    )
)

filter_registry.register(
    FilterText(
        ident="event_host",
        title=_l("Hostname of event, exact match"),
        sort_index=201,
        info="event",
        legacy_filter=legacy_filters.FilterText(column="event_host", htmlvar="event_host", op="="),
    )
)

filter_registry.register(
    FilterText(
        ident="event_ipaddress",
        title=_l("Original IP Address of event"),
        sort_index=201,
        info="event",
        legacy_filter=legacy_filters.FilterText(
            column="event_ipaddress", htmlvar="event_ipaddress", op="~~"
        ),
    )
)

filter_registry.register(
    FilterText(
        ident="event_owner",
        title=_l("Owner of event"),
        sort_index=201,
        info="event",
        legacy_filter=legacy_filters.FilterText(
            column="event_owner", htmlvar="event_owner", op="~~"
        ),
    )
)

filter_registry.register(
    FilterText(
        ident="history_who",
        title=_l("User that performed action"),
        sort_index=221,
        info="history",
        legacy_filter=legacy_filters.FilterText(
            column="history_who", htmlvar="history_who", op="~~"
        ),
    )
)

filter_registry.register(
    FilterText(
        ident="history_line",
        title=_l("Line number in history logfile"),
        sort_index=222,
        info="history",
        legacy_filter=legacy_filters.FilterText(
            column="history_line", htmlvar="history_line", op="="
        ),
    )
)

filter_nagios_flag_with_register(
    ident="event_host_in_downtime",
    title=_l("Host in downtime during event creation"),
    sort_index=223,
    info="event",
)


@filter_registry.register_instance
class FilterEventCount(Filter):
    def __init__(self):
        name = "event_count"
        super().__init__(
            ident="event_count",
            title=_l("Message count"),
            sort_index=205,
            info="event",
            htmlvars=[name + "_from", name + "_to"],
            link_columns=[name],
        )
        self._name = name

    def display(self, value: FilterHTTPVariables) -> None:
        html.write_text("from: ")
        html.text_input(
            self._name + "_from",
            default_value=value.get(self._name + "_from", ""),
            size=8,
            cssclass="number",
        )
        html.write_text(" to: ")
        html.text_input(
            self._name + "_to",
            default_value=value.get(self._name + "_to", ""),
            size=8,
            cssclass="number",
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        f = ""
        if v_from := value.get(self._name + "_from"):
            f += "Filter: event_count >= %d\n" % int(v_from)

        if v_to := value.get(self._name + "_to"):
            f += "Filter: event_count <= %d\n" % int(v_to)
        return f


class EventFilterState(Filter):
    def __init__(
        self,
        *,
        ident: str,
        title: Union[str, LazyString],
        sort_index: int,
        table: str,
        choices: List[Tuple[str, Union[LazyString, str]]],
    ) -> None:
        varnames = [ident + "_" + c[0] for c in choices]
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info=table,
            htmlvars=varnames,
            link_columns=[ident],
        )
        self._choices = choices

    def display(self, value: FilterHTTPVariables) -> None:
        html.begin_checkbox_group()
        checkbox_default = not any(value.values())  # everything by default
        for name, title in self._choices:
            varname = self.ident + "_" + name
            html.checkbox(varname, bool(value.get(varname, checkbox_default)), label=str(title))
        html.end_checkbox_group()

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if all(value.values()):  # everything on, skip filter
            return ""

        selected = (name for name, _title in self._choices if value.get(self.ident + "_" + name))

        return lq_logic("Filter: %s =" % self.ident, sorted(selected), "Or")


filter_registry.register(
    EventFilterState(
        ident="event_state",
        title=_l("State classification"),
        sort_index=206,
        table="event",
        choices=[
            ("0", _l("OK")),
            ("1", _l("WARN")),
            ("2", _l("CRIT")),
            ("3", _l("UNKNOWN")),
        ],
    )
)

filter_registry.register(
    EventFilterState(
        ident="event_phase",
        title=_l("Phase"),
        sort_index=207,
        table="event",
        choices=list(mkeventd.phase_names.items()),
    )
)

filter_registry.register(
    EventFilterState(
        ident="event_priority",
        title=_l("Syslog Priority"),
        sort_index=209,
        table="event",
        choices=[(str(e[0]), e[1]) for e in mkeventd.syslog_priorities],
    )
)

filter_registry.register(
    EventFilterState(
        ident="history_what",
        title=_l("History action type"),
        sort_index=225,
        table="history",
        choices=[(k, k) for k in mkeventd.action_whats],
    )
)

filter_registry.register(
    FilterTime(
        ident="event_first",
        title=_l("First occurrence of event"),
        sort_index=220,
        info="event",
        column="event_first",
    )
)

filter_registry.register(
    FilterTime(
        ident="event_last",
        title=_l("Last occurrance of event"),
        sort_index=221,
        info="event",
        column="event_last",
    )
)

filter_registry.register(
    FilterTime(
        ident="history_time",
        title=_l("Time of entry in event history"),
        sort_index=222,
        info="history",
        column="history_time",
    )
)


class EventFilterDropdown(Filter):
    def __init__(
        self,
        *,
        ident: str,
        title: Union[str, LazyString],
        sort_index: int,
        choices: Union[Choices, Callable[[], Choices]],
        operator: str = "=",
        column: str,
    ) -> None:
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info="event",
            htmlvars=[ident],
            link_columns=["event_" + column],
        )
        self._choices = choices
        self._column = column
        self._operator = operator

    def display(self, value: FilterHTTPVariables) -> None:
        if isinstance(self._choices, list):
            choices = self._choices
        else:
            choices = self._choices()
        empty_choices: Choices = [("", "")]
        the_choices: Choices = [(str(n), t) for (n, t) in choices]
        html.dropdown(self.ident, empty_choices + the_choices, deflt=value.get(self.ident, ""))

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if val := value.get(self.ident):
            return "Filter: event_%s %s %s\n" % (self._column, self._operator, val)
        return ""


filter_registry.register(
    EventFilterDropdown(
        ident="event_facility",
        title=_l("Syslog Facility"),
        sort_index=210,
        choices=mkeventd.syslog_facilities,
        column="facility",
    )
)

filter_registry.register(
    EventFilterDropdown(
        ident="event_sl",
        title=_l("Service Level at least"),
        sort_index=211,
        choices=mkeventd.service_levels,
        operator=">=",
        column="sl",
    )
)

filter_registry.register(
    EventFilterDropdown(
        ident="event_sl_max",
        title=_l("Service Level at most"),
        sort_index=211,
        choices=mkeventd.service_levels,
        operator="<=",
        column="sl",
    )
)


@filter_registry.register_instance
class FilterOptEventEffectiveContactgroup(FilterGroupCombo):
    def __init__(self):
        # TODO: Cleanup hierarchy here. The FilterGroupCombo constructor needs to be refactored
        super().__init__(
            ident="optevent_effective_contactgroup",
            title=_l("Contact group (effective)"),
            sort_index=212,
            what="event_effective_contact",
            enforce=False,
        )
        self.what = "contact"
        self.info = "event"
        self.link_columns = [
            "event_contact_groups",
            "event_contact_groups_precedence",
            "host_contact_groups",
        ]

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if not value.get(self.htmlvars[0]):
            return ""  # Skip if filter is not being set at all

        current_value = value[self.htmlvars[0]]
        if not self.enforce and value.get(self.htmlvars[1]):
            negate = "!"
        else:
            negate = ""

        return (
            "Filter: event_contact_groups_precedence = host\n"
            "Filter: host_contact_groups %s>= %s\n"
            "And: 2\n"
            "Filter: event_contact_groups_precedence = rule\n"
            "Filter: event_contact_groups %s>= %s\n"
            "And: 2\n"
            "Or: 2\n"
            % (
                negate,
                livestatus.lqencode(current_value),
                negate,
                livestatus.lqencode(current_value),
            )
        )

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {}


class FilterCMKSiteStatisticsByCorePIDs(Filter):
    ID = "service_cmk_site_statistics_core_pid"

    def display(self, value: FilterHTTPVariables) -> None:
        return html.write_text(
            _(
                "Used in the host and service problems graphs of the main dashboard. Not intended "
                "for any other purposes."
            )
        )

    def columns_for_filter_table(self, context: VisualContext) -> Iterable[str]:
        if self.ID in context:
            yield "service_description"
            yield "long_plugin_output"

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        if self.ID not in context:
            return rows

        # ids and core pids of connected sites, i.e., what we hope to find the service output
        pids_of_connected_sites = {
            site_id: site_status["core_pid"]
            for site_id, site_status in sites.states().items()
            if site_status["state"] == "online"
        }
        # apply potential filters on sites
        if only_sites := get_only_sites_from_context(context):
            pids_of_connected_sites = {
                site_id: core_pid
                for site_id, core_pid in pids_of_connected_sites.items()
                if site_id in only_sites
            }

        connected_sites = set(pids_of_connected_sites)

        # ids and core pids from the service output
        sites_and_pids_from_services = []
        rows_right_service = []
        for row in rows:
            if not re.match("Site [^ ]* statistics$", row["service_description"]):
                continue
            rows_right_service.append(row)
            site = row["service_description"].split(" ")[1]
            re_matches_pid = re.findall("Core PID: ([0-9][0-9]*)", row["long_plugin_output"])
            if re_matches_pid:
                pid: Optional[int] = int(re_matches_pid[0])
            else:
                pid = None
            sites_and_pids_from_services.append((site, pid))

        unique_sites_from_services = set(site for (site, _pid) in sites_and_pids_from_services)

        # sites from service outputs are unique and all expected sites are present --> no need to
        # filter by PIDs
        if unique_sites_from_services == connected_sites and len(unique_sites_from_services) == len(
            sites_and_pids_from_services
        ):
            return rows_right_service

        # check if sites are missing
        if not unique_sites_from_services.issuperset(connected_sites):
            manual_ref = html.resolve_help_text_macros(
                _(
                    "Please refer to the [dashboards#host_problems|Checkmk user guide] for more details."
                )
            )
            if len(connected_sites) == 1:
                raise MKMissingDataError(
                    _(
                        "As soon as you add your Checkmk server to the monitoring, a graph showing "
                        "the history of your host problems will appear here. "
                    )
                    + manual_ref
                )
            raise MKMissingDataError(
                _(
                    "As soon as you add your Checkmk server(s) to the monitoring, a graph showing "
                    "the history of your host problems will appear here. Currently the following "
                    "Checkmk sites are not monitored: %s. "
                )
                % ", ".join(connected_sites - unique_sites_from_services)
                + manual_ref
            )

        # there are duplicate sites --> filter by PID
        rows_filtered = []
        for row, (site, pid) in zip(rows_right_service, sites_and_pids_from_services):
            if site in pids_of_connected_sites and pid == pids_of_connected_sites[site]:
                rows_filtered.append(row)
                del pids_of_connected_sites[site]

        return rows_filtered


filter_registry.register(
    FilterCMKSiteStatisticsByCorePIDs(
        ident=FilterCMKSiteStatisticsByCorePIDs.ID,
        title=_l("cmk_site_statistics (core PIDs)"),
        sort_index=900,
        info="service",
        htmlvars=[FilterCMKSiteStatisticsByCorePIDs.ID],
        link_columns=[],
    )
)
