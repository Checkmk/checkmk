#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import re
from functools import partial
from typing import Any, Callable, Dict, Iterable, List, Literal, Optional, Tuple, Union

import livestatus

import cmk.utils.version as cmk_version
from cmk.utils.prediction import lq_logic

import cmk.gui.bi as bi
import cmk.gui.mkeventd as mkeventd
import cmk.gui.sites as sites
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKMissingDataError, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.type_defs import (
    Choices,
    ColumnName,
    FilterHeader,
    FilterHTTPVariables,
    Row,
    Rows,
    VisualContext,
)
from cmk.gui.utils.autocompleter_config import AutocompleterConfig, GroupAutocompleterConfig
from cmk.gui.utils.regex import validate_regex
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import DualListChoice, Labels

if cmk_version.is_managed_edition():
    from cmk.gui.cme.plugins.visuals.managed import (  # pylint: disable=no-name-in-module
        filter_cme_heading_info,
    )

import cmk.gui.query_filters as query_filters
from cmk.gui.plugins.visuals.utils import (
    checkbox_component,
    checkbox_row,
    CheckboxRowFilter,
    display_filter_radiobuttons,
    DualListFilter,
    Filter,
    filter_cre_heading_info,
    filter_registry,
    FilterNumberRange,
    FilterOption,
    FilterTime,
    get_only_sites_from_context,
    InputTextFilter,
)


class RegExpFilter(InputTextFilter):
    def validate_value(self, value: FilterHTTPVariables) -> None:
        htmlvar = self.htmlvars[0]
        validate_regex(value.get(htmlvar, ""), htmlvar)


class AjaxDropdownFilter(Filter):
    "Select from dropdown with dynamic option query"

    def __init__(
        self,
        *,
        title: Union[str, LazyString],
        sort_index: int,
        info: str,
        autocompleter: AutocompleterConfig,
        query_filter: Union[query_filters.TextQuery, query_filters.KubernetesQuery],
        link_columns: Optional[List[ColumnName]] = None,
        description: Union[None, str, LazyString] = None,
        is_show_more: bool = False,
    ) -> None:
        self.query_filter = query_filter
        self.autocompleter = autocompleter

        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=self.query_filter.request_vars,
            link_columns=link_columns or self.query_filter.link_columns,
            description=description,
            is_show_more=is_show_more,
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        return self.query_filter.filter_table(context, rows)

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {self.query_filter.request_vars[0]: row[self.query_filter.column]}

    def display(self, value: FilterHTTPVariables) -> None:
        current_value = value.get(self.query_filter.request_vars[0], "")
        choices = [(current_value, current_value)] if current_value else []

        html.dropdown(
            self.query_filter.request_vars[0],
            choices,
            current_value,
            style="width: 250px;",
            class_=["ajax-vals"],
            data_autocompleter=json.dumps(self.autocompleter.config),
        )

        if self.query_filter.negateable:
            checkbox_component(self.query_filter.request_vars[1], value, _("negate"))


# TODO: Dare for the moment not to validate the regex, because user can only
# select what comes back. In general we should validate all input although that
# is not yet implemented. Only the regex had a control, and the dropdown display
# was a hack
filter_registry.register(
    AjaxDropdownFilter(
        title=_l("Hostname"),
        sort_index=100,
        info="host",
        autocompleter=AutocompleterConfig(ident="monitored_hostname"),
        query_filter=query_filters.TextQuery(
            ident="hostregex",
            column="host_name",
            request_var="host_regex",
            op="~~",
            negateable=True,
        ),
        description=_l("Search field allowing regular expressions and partial matches"),
    )
)

filter_registry.register(
    AjaxDropdownFilter(
        title=_l("Hostname (exact match)"),
        sort_index=101,
        info="host",
        autocompleter=AutocompleterConfig(ident="monitored_hostname", strict=True),
        query_filter=query_filters.TextQuery(
            ident="host",
            column="host_name",
            op="=",
            negateable=True,
        ),
        description=_l("Exact match, used for linking"),
        is_show_more=True,
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Hostalias"),
        sort_index=102,
        info="host",
        query_filter=query_filters.TextQuery(
            ident="hostalias", column="host_alias", op="~~", negateable=True
        ),
        description=_l("Search field allowing regular expressions and partial matches"),
        is_show_more=True,
    )
)

filter_registry.register(
    AjaxDropdownFilter(
        title=_l("Service"),
        sort_index=200,
        info="service",
        autocompleter=AutocompleterConfig(ident="monitored_service_description"),
        query_filter=query_filters.TextQuery(
            ident="serviceregex",
            column="service_description",
            request_var="service_regex",
            op="~~",
            negateable=True,
        ),
        description=_l("Search field allowing regular expressions and partial matches"),
    )
)

filter_registry.register(
    AjaxDropdownFilter(
        title=_l("Service (exact match)"),
        sort_index=201,
        info="service",
        autocompleter=AutocompleterConfig(ident="monitored_service_description", strict=True),
        query_filter=query_filters.TextQuery(
            ident="service",
            column="service_description",
            op="=",
        ),
        description=_l("Exact match, used for linking"),
        is_show_more=True,
    )
)

filter_registry.register(
    RegExpFilter(
        title=_l("Service alternative display name"),
        sort_index=202,
        description=_l("Alternative display name of the service, regex match"),
        info="service",
        query_filter=query_filters.TextQuery(
            ident="service_display_name",
            op="~~",
        ),
        is_show_more=True,
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Summary (Plugin output)"),
        sort_index=202,
        info="service",
        query_filter=query_filters.TextQuery(
            ident="output",
            column="service_plugin_output",
            request_var="service_output",
            op="~~",
            negateable=True,
        ),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Hostname or Alias"),
        sort_index=102,
        info="host",
        description=_l("Search field allowing regular expressions and partial matches"),
        query_filter=query_filters.HostnameOrAliasQuery(),
    )
)


class IPAddressFilter(Filter):
    def __init__(
        self,
        *,
        title: Union[str, LazyString],
        sort_index: int,
        query_filter: query_filters.IPAddressQuery,
        link_columns: List[str],
        is_show_more: bool = False,
    ):
        self.query_filter = query_filter
        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=sort_index,
            info="host",
            htmlvars=self.query_filter.request_vars,
            link_columns=link_columns,
            is_show_more=is_show_more,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        html.text_input(
            self.query_filter.request_vars[0], value.get(self.query_filter.request_vars[0], "")
        )
        html.br()
        display_filter_radiobuttons(
            varname=self.query_filter.request_vars[1],
            options=query_filters.ip_match_options(),
            default="yes",
            value=value,
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {self.query_filter.request_vars[0]: row["host_address"]}

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        return value.get(self.query_filter.request_vars[0])


filter_registry.register(
    IPAddressFilter(
        title=_l("Host address (Primary)"),
        sort_index=102,
        link_columns=["host_address"],
        query_filter=query_filters.IPAddressQuery(
            ident="host_address",
            what="primary",
        ),
        is_show_more=True,
    )
)

filter_registry.register(
    IPAddressFilter(
        title=_l("Host address (IPv4)"),
        sort_index=102,
        link_columns=[],
        query_filter=query_filters.IPAddressQuery(
            ident="host_ipv4_address",
            what="ipv4",
        ),
    )
)

filter_registry.register(
    IPAddressFilter(
        title=_l("Host address (IPv6)"),
        sort_index=102,
        link_columns=[],
        query_filter=query_filters.IPAddressQuery(
            ident="host_ipv6_address",
            what="ipv6",
        ),
    )
)

filter_registry.register(
    FilterOption(
        title=_l("Host address family (Primary)"),
        sort_index=103,
        info="host",
        query_filter=query_filters.SingleOptionQuery(
            ident="address_family",
            options=query_filters.ip_address_family_options(),
            filter_code=query_filters.address_family,
        ),
        is_show_more=True,
    )
)


filter_registry.register(
    FilterOption(
        title=_l("Host address families"),
        sort_index=103,
        info="host",
        query_filter=query_filters.SingleOptionQuery(
            ident="address_families",
            options=query_filters.ip_address_families_options(),
            filter_code=query_filters.address_families,
        ),
        is_show_more=True,
    )
)


filter_registry.register(
    DualListFilter(
        title=_l("Several host groups"),
        sort_index=105,
        description=_l("Selection of multiple host groups"),
        info="host",
        query_filter=query_filters.MultipleQuery(
            ident="hostgroups", column="host_groups", op=">=", negateable=True
        ),
        options=sites.all_groups,
    )
)

filter_registry.register(
    DualListFilter(
        title=_l("Several service groups"),
        sort_index=205,
        description=_l("Selection of multiple service groups"),
        info="service",
        query_filter=query_filters.MultipleQuery(
            ident="servicegroups", column="service_groups", op=">=", negateable=True
        ),
        options=sites.all_groups,
    )
)

GroupType = Literal[
    "host", "service", "contact", "host_contact", "service_contact", "event_effective_contact"
]


class FilterGroupCombo(AjaxDropdownFilter):
    """Selection of a host/service(-contact) group as an attribute of a host or service"""

    def __init__(
        self,
        *,
        title: Union[str, LazyString],
        sort_index: int,
        group_type: GroupType,
        autocompleter: AutocompleterConfig,
        query_filter: query_filters.TextQuery,
        description: Union[None, str, LazyString] = None,
    ) -> None:
        self.query_filter = query_filter
        self.group_type = group_type

        super().__init__(
            title=title,
            sort_index=sort_index,
            info=group_type.split("_")[0],
            autocompleter=autocompleter,
            query_filter=query_filter,
            link_columns=[group_type + "group_name"],
            description=description,
        )

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        varname = self.htmlvars[0]
        value = row.get(self.group_type + "group_name")
        if value:
            s = {varname: value}
            if self.query_filter.negateable:
                negvar = self.query_filter.request_vars[1]
                if request.var(negvar):  # This violates the idea of originating from row
                    s[negvar] = request.var(negvar)
            return s
        return {}

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        # TODO: This should be part of the general options query
        if current_value := value.get(self.query_filter.request_vars[0]):
            group_type = "contact" if self.group_type.endswith("_contact") else self.group_type
            alias = sites.live().query_value(
                "GET %sgroups\nCache: reload\nColumns: alias\nFilter: name = %s\n"
                % (group_type, livestatus.lqencode(current_value)),
                current_value,
            )
            return alias
        return None


filter_registry.register(
    FilterGroupCombo(
        title=_l("Host is in Group"),
        sort_index=104,
        description=_l("Optional selection of host group"),
        autocompleter=GroupAutocompleterConfig(ident="allgroups", group_type="host"),
        query_filter=query_filters.MultipleQuery(
            ident="opthostgroup",
            request_var="opthost_group",
            column="host_groups",
            op=">=",
            negateable=True,
        ),
        group_type="host",
    )
)

filter_registry.register(
    FilterGroupCombo(
        title=_l("Service is in Group"),
        sort_index=204,
        description=_l("Optional selection of service group"),
        autocompleter=GroupAutocompleterConfig(ident="allgroups", group_type="service"),
        query_filter=query_filters.MultipleQuery(
            ident="optservicegroup",
            request_var="optservice_group",
            column="service_groups",
            op=">=",
            negateable=True,
        ),
        group_type="service",
    )
)

filter_registry.register(
    FilterGroupCombo(
        title=_l("Host Contact Group"),
        sort_index=106,
        description=_l("Optional selection of host contact group"),
        autocompleter=GroupAutocompleterConfig(ident="allgroups", group_type="contact"),
        query_filter=query_filters.MultipleQuery(
            ident="opthost_contactgroup",
            request_var="opthost_contact_group",
            column="host_contact_groups",
            op=">=",
            negateable=True,
        ),
        group_type="host_contact",
    )
)

filter_registry.register(
    FilterGroupCombo(
        title=_l("Service Contact Group"),
        sort_index=206,
        description=_l("Optional selection of service contact group"),
        autocompleter=GroupAutocompleterConfig(ident="allgroups", group_type="service"),
        query_filter=query_filters.MultipleQuery(
            ident="optservice_contactgroup",
            request_var="optservice_contact_group",
            column="service_contact_groups",
            op=">=",
            negateable=True,
        ),
        group_type="service_contact",
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Host Contact"),
        sort_index=107,
        info="host",
        query_filter=query_filters.TextQuery(ident="host_ctc", column="host_contacts", op=">="),
        is_show_more=True,
    )
)

filter_registry.register(
    RegExpFilter(
        title=_l("Host Contact (Regex)"),
        sort_index=107,
        info="host",
        query_filter=query_filters.TextQuery(
            ident="host_ctc_regex", column="host_contacts", op="~~"
        ),
        is_show_more=True,
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Service Contact"),
        sort_index=207,
        info="service",
        query_filter=query_filters.TextQuery(
            ident="service_ctc", column="service_contacts", op=">="
        ),
        is_show_more=True,
    )
)

filter_registry.register(
    RegExpFilter(
        title=_l("Service Contact (Regex)"),
        sort_index=207,
        info="service",
        query_filter=query_filters.TextQuery(
            ident="service_ctc_regex",
            column="service_contacts",
            op="~~",
        ),
        is_show_more=True,
    )
)

filter_registry.register(
    AjaxDropdownFilter(
        title=_l("Host group"),
        sort_index=104,
        description=_l("Selection of the host group"),
        info="hostgroup",
        autocompleter=GroupAutocompleterConfig(ident="allgroups", group_type="host", strict=True),
        query_filter=query_filters.TextQuery(
            ident="hostgroup",
            column="hostgroup_name",
            op="=",
        ),
    )
)

filter_registry.register(
    AjaxDropdownFilter(
        title=_l("Service group"),
        sort_index=104,
        description=_l("Selection of the service group"),
        info="servicegroup",
        autocompleter=GroupAutocompleterConfig(
            ident="allgroups", group_type="service", strict=True
        ),
        query_filter=query_filters.TextQuery(
            ident="servicegroup",
            column="servicegroup_name",
            op="=",
        ),
    )
)

filter_registry.register(
    RegExpFilter(
        title=_l("Host group (Regex)"),
        sort_index=101,
        description=_l(
            "Search field allowing regular expressions and partial matches on the names of host groups"
        ),
        info="hostgroup",
        query_filter=query_filters.TextQuery(
            ident="hostgroupnameregex",
            column="hostgroup_name",
            request_var="hostgroup_regex",
            op="~~",
        ),
    )
)

filter_registry.register(
    RegExpFilter(
        title=_l("Service group (regex)"),
        sort_index=101,
        description=_l("Search field allowing regular expression and partial matches"),
        info="servicegroup",
        query_filter=query_filters.TextQuery(
            ident="servicegroupnameregex",
            column="servicegroup_name",
            request_var="servicegroup_regex",
            op="~~",
            negateable=True,
        ),
    )
)

filter_registry.register(
    AjaxDropdownFilter(
        title=_l("Service group (enforced)"),
        sort_index=101,
        description=_l("Exact match, used for linking"),
        info="servicegroup",
        autocompleter=GroupAutocompleterConfig(
            ident="allgroups", group_type="service", strict=True
        ),
        query_filter=query_filters.TextQuery(
            ident="servicegroupname",
            column="servicegroup_name",
            request_var="servicegroup_name",
            op="=",
        ),
    )
)


filter_registry.register(
    AjaxDropdownFilter(
        title=_l("Host check command"),
        sort_index=110,
        info="host",
        autocompleter=AutocompleterConfig(ident="check_cmd"),
        query_filter=query_filters.CheckCommandQuery(
            ident="host_check_command",
            op="~",
        ),
    )
)

filter_registry.register(
    AjaxDropdownFilter(
        title=_l("Service check command"),
        sort_index=210,
        info="service",
        autocompleter=AutocompleterConfig(ident="check_cmd"),
        query_filter=query_filters.CheckCommandQuery(
            ident="check_command",
            op="~",
            column="service_check_command",
        ),
    )
)

# TODO: I would be great to split this in two filters for host & service kind of problems
@filter_registry.register_instance
class FilterHostgroupProblems(CheckboxRowFilter):
    def __init__(self):
        self.host_problems = query_filters.host_problems_options("hostgroups_having_hosts_")
        self.host_problems.append(("hostgroups_show_unhandled_host", _("Unhandled host problems")))

        self.svc_problems = query_filters.svc_problems_options("hostgroups_having_services_")
        self.svc_problems.append(("hostgroups_show_unhandled_svc", _("Unhandled service problems")))

        super().__init__(
            title=_l("Host groups having certain problems"),
            sort_index=103,
            info="hostgroup",
            query_filter=query_filters.MultipleOptionsQuery(
                ident="hostsgroups_having_problems",
                options=self.host_problems + self.svc_problems,
                livestatus_query=query_filters.hostgroup_problems_filter,
            ),
        )

    def display(self, value: FilterHTTPVariables) -> None:
        checkbox_row(self.svc_problems, value, "Service states: ")

        html.br()
        checkbox_row(self.host_problems, value, "Host states: ")


filter_registry.register(
    CheckboxRowFilter(
        title=_l("Empty host group visibilitiy"),
        sort_index=102,
        info="hostgroup",
        query_filter=query_filters.MultipleOptionsQuery(
            ident="hostgroupvisibility",
            options=[("hostgroupshowempty", _("Show empty groups"))],
            livestatus_query=query_filters.empty_hostgroup_filter,
        ),
    )
)


filter_registry.register(
    CheckboxRowFilter(
        title=_l("Service states"),
        sort_index=215,
        info="service",
        query_filter=query_filters.MultipleOptionsQuery(
            ident="svcstate",
            options=query_filters.svc_state_options(""),
            livestatus_query=partial(query_filters.service_state_filter, ""),
        ),
    )
)

filter_registry.register(
    CheckboxRowFilter(
        title=_l("Service hard states"),
        sort_index=216,
        info="service",
        is_show_more=True,
        query_filter=query_filters.MultipleOptionsQuery(
            ident="svchardstate",
            options=query_filters.svc_state_options("hd"),
            livestatus_query=partial(query_filters.service_state_filter, "hd"),
        ),
    )
)

filter_registry.register(
    CheckboxRowFilter(
        title=_l("Host states"),
        sort_index=115,
        info="host",
        query_filter=query_filters.MultipleOptionsQuery(
            ident="hoststate",
            options=query_filters.host_state_options(),
            livestatus_query=query_filters.host_state_filter,
        ),
    )
)

filter_registry.register(
    CheckboxRowFilter(
        title=_l("Hosts having certain service problems"),
        sort_index=120,
        info="host",
        query_filter=query_filters.MultipleOptionsQuery(
            ident="hosts_having_service_problems",
            options=query_filters.svc_problems_options("hosts_having_services_"),
            livestatus_query=query_filters.host_having_svc_problems_filter,
        ),
    )
)


def filter_state_type_with_register(
    *, ident: str, title: Union[str, LazyString], sort_index: int, info: str
) -> None:
    filter_registry.register(
        FilterOption(
            title=title,
            sort_index=sort_index,
            info=info,
            query_filter=query_filters.TristateQuery(
                ident=ident,
                filter_code=query_filters.state_type,
                options=query_filters.tri_state_type_options(),
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
        title=_l("Has performance data"),
        sort_index=251,
        info="service",
        query_filter=query_filters.TristateQuery(
            ident="has_performance_data", filter_code=query_filters.service_perfdata_toggle
        ),
        is_show_more=True,
    )
)


filter_registry.register(
    FilterOption(
        title=_l("Host/service in downtime"),
        sort_index=232,
        info="service",
        query_filter=query_filters.TristateQuery(
            ident="in_downtime", filter_code=query_filters.host_service_perfdata_toggle
        ),
    )
)


filter_registry.register(
    FilterOption(
        title=_l("Host is stale"),
        sort_index=232,
        info="host",
        query_filter=query_filters.TristateQuery(
            ident="host_staleness", filter_code=query_filters.staleness("host")
        ),
        is_show_more=True,
    )
)


filter_registry.register(
    FilterOption(
        title=_l("Service is stale"),
        sort_index=232,
        info="service",
        query_filter=query_filters.TristateQuery(
            ident="service_staleness", filter_code=query_filters.staleness("service")
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
            title=title,
            sort_index=sort_index,
            info=info,
            query_filter=query_filters.TristateQuery(
                ident=ident, filter_code=query_filters.column_flag(ident)
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
        title: Union[str, LazyString],
        sort_index: int,
        query_filter: query_filters.Query,
        description: Union[None, str, LazyString] = None,
        is_show_more: bool = False,
    ) -> None:
        self.query_filter = query_filter

        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=sort_index,
            info="host",
            htmlvars=self.query_filter.request_vars,
            link_columns=[],
            description=description,
            is_show_more=is_show_more,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        current_value = value.get(self.query_filter.request_vars[0], "")
        choices = [(current_value, current_value)] if current_value else []

        html.dropdown(
            self.query_filter.request_vars[0],
            choices,
            current_value,
            style="width: 250px;",
            class_=["ajax-vals"],
            data_autocompleter=json.dumps(
                AutocompleterConfig(
                    ident="sites",
                    strict=self.query_filter.ident == "site",
                ).config
            ),
        )

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        if cmk_version.is_managed_edition():
            return filter_cme_heading_info(value)
        return filter_cre_heading_info(value)

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {"site": row["site"]}


filter_registry.register(
    SiteFilter(
        title=_l("Site"),
        sort_index=500,
        query_filter=query_filters.Query(
            ident="siteopt",
            request_vars=["site"],
        ),
        description=_l("Optional selection of a site"),
    )
)

filter_registry.register(
    SiteFilter(
        title=_l("Site (enforced)"),
        sort_index=501,
        query_filter=query_filters.Query(ident="site", request_vars=["site"]),
        description=_l("Selection of site is enforced, use this filter for joining"),
        is_show_more=True,
    )
)


class MultipleSitesFilter(SiteFilter):
    def get_request_sites(self, value: FilterHTTPVariables) -> List[str]:
        return [x for x in value.get(self.htmlvars[0], "").strip().split("|") if x]

    def display(self, value: FilterHTTPVariables):
        sites_vs = DualListChoice(choices=query_filters.sites_options(), rows=4)
        sites_vs.render_input(self.htmlvars[0], self.get_request_sites(value))


filter_registry.register(
    MultipleSitesFilter(
        title=_l("Multiple Sites"),
        sort_index=502,
        query_filter=query_filters.Query(ident="sites", request_vars=["sites"]),
        description=_l("Associative selection of multiple sites"),
    )
)


filter_registry.register(
    FilterNumberRange(
        title=_l("Current Host Notification Number"),
        sort_index=232,
        info="host",
        query_filter=query_filters.NumberRangeQuery(
            ident="host_notif_number", column="current_notification_number"
        ),
    )
)

filter_registry.register(
    FilterNumberRange(
        title=_l("Current Service Notification Number"),
        sort_index=232,
        info="service",
        query_filter=query_filters.NumberRangeQuery(
            ident="svc_notif_number", column="current_notification_number"
        ),
    )
)

filter_registry.register(
    FilterNumberRange(
        title=_l("Number of Services of the Host"),
        sort_index=234,
        info="host",
        query_filter=query_filters.NumberRangeQuery(
            ident="host_num_services", column="num_services"
        ),
    )
)

filter_registry.register(
    FilterTime(
        title=_l("Last service state change"),
        sort_index=250,
        info="service",
        query_filter=query_filters.TimeQuery(
            ident="svc_last_state_change", column="service_last_state_change"
        ),
    )
)

filter_registry.register(
    FilterTime(
        title=_l("Last service check"),
        sort_index=251,
        info="service",
        query_filter=query_filters.TimeQuery(ident="svc_last_check", column="service_last_check"),
    )
)

filter_registry.register(
    FilterTime(
        title=_l("Last host state change"),
        sort_index=250,
        info="host",
        query_filter=query_filters.TimeQuery(ident="host_last_state_change"),
    )
)

filter_registry.register(
    FilterTime(
        title=_l("Last host check"),
        sort_index=251,
        info="host",
        query_filter=query_filters.TimeQuery(ident="host_last_check"),
    )
)

filter_registry.register(
    FilterTime(
        title=_l("Time of comment"),
        sort_index=253,
        info="comment",
        query_filter=query_filters.TimeQuery(ident="comment_entry_time"),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Comment"),
        sort_index=258,
        info="comment",
        query_filter=query_filters.TextQuery(
            ident="comment_comment",
            op="~~",
            negateable=True,
        ),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Author comment"),
        sort_index=259,
        info="comment",
        query_filter=query_filters.TextQuery(
            ident="comment_author",
            op="~~",
            negateable=True,
        ),
    )
)

filter_registry.register(
    FilterTime(
        title=_l("Time when downtime was created"),
        sort_index=253,
        info="downtime",
        query_filter=query_filters.TimeQuery(ident="downtime_entry_time"),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Downtime comment"),
        sort_index=254,
        info="downtime",
        query_filter=query_filters.TextQuery(ident="downtime_comment", op="~"),
    )
)

filter_registry.register(
    FilterTime(
        title=_l("Start of downtime"),
        sort_index=255,
        info="downtime",
        query_filter=query_filters.TimeQuery(ident="downtime_start_time"),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Downtime author"),
        sort_index=256,
        info="downtime",
        query_filter=query_filters.TextQuery(ident="downtime_author", op="~"),
    )
)

filter_registry.register(
    FilterTime(
        title=_l("Time of log entry"),
        sort_index=252,
        info="log",
        query_filter=query_filters.TimeQuery(ident="logtime", column="log_time"),
    )
)

filter_registry.register(
    CheckboxRowFilter(
        title=_l("Logentry class"),
        sort_index=255,
        info="log",
        query_filter=query_filters.MultipleOptionsQuery(
            ident="log_class",
            options=query_filters.log_class_options(),
            livestatus_query=query_filters.log_class_filter,
        ),
    )
)


filter_registry.register(
    InputTextFilter(
        title=_l("Log: plugin output"),
        sort_index=202,
        info="log",
        query_filter=query_filters.TextQuery(
            ident="log_plugin_output",
            op="~~",
        ),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Log: message type"),
        sort_index=203,
        info="log",
        query_filter=query_filters.TextQuery(ident="log_type", op="~~"),
        show_heading=False,
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l('Log: state type (DEPRECATED: Use "state information")'),
        sort_index=204,
        info="log",
        query_filter=query_filters.TextQuery(ident="log_state_type", op="~~"),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Log: state information"),
        sort_index=204,
        info="log",
        query_filter=query_filters.TextQuery(ident="log_state_info", op="~~"),
    )
)


class FilterLogContactName(InputTextFilter):
    """Special filter class to correctly filter the column contact_name from the log table. This
    list contains comma-separated contact names (user ids), but it is of type string."""

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if current_value := value.get(self.htmlvars[0]):
            new_value = dict(value.items())
            new_value[self.htmlvars[0]] = "(,|^)" + current_value.replace(".", "\\.") + "(,|$)"
            return self.query_filter._filter(new_value)
        return ""


filter_registry.register(
    FilterLogContactName(
        title=_l("Log: contact name (exact match)"),
        sort_index=260,
        description=_l("Exact match, used for linking"),
        info="log",
        query_filter=query_filters.TextQuery(ident="log_contact_name", op="~"),
    )
)

filter_registry.register(
    RegExpFilter(
        title=_l("Log: contact name"),
        sort_index=261,
        info="log",
        query_filter=query_filters.TextQuery(
            ident="log_contact_name_regex",
            column="log_contact_name",
            op="~~",
            negateable=True,
        ),
    )
)

filter_registry.register(
    RegExpFilter(
        title=_l("Log: command"),
        sort_index=262,
        info="log",
        query_filter=query_filters.TextQuery(
            ident="log_command_name_regex",
            column="log_command_name",
            op="~~",
            negateable=True,
        ),
    )
)


# TODO: I would be great to split this in two filters for host & service states
@filter_registry.register_instance
class FilterLogState(CheckboxRowFilter):
    def __init__(self):
        self.host_states = [
            ("logst_h0", _("Up")),
            ("logst_h1", _("Down")),
            ("logst_h2", _("Unreachable")),
        ]
        self.service_states = [
            ("logst_s0", _("OK")),
            ("logst_s1", _("Warning")),
            ("logst_s2", _("Critical")),
            ("logst_s3", _("Unknown")),
        ]

        super().__init__(
            title=_l("Type of alerts of hosts and services"),
            sort_index=270,
            info="log",
            query_filter=query_filters.MultipleOptionsQuery(
                ident="log_state",
                options=self.host_states + self.service_states,
                livestatus_query=query_filters.log_alerts_filter,
            ),
        )

    def display(self, value: FilterHTTPVariables) -> None:
        checkbox_row(self.host_states, value, "Hosts: ")
        html.br()
        checkbox_row(self.service_states, value, "Services: ")


filter_registry.register(
    FilterOption(
        title=_l("Notification phase"),
        sort_index=271,
        info="log",
        query_filter=query_filters.TristateQuery(
            ident="log_notification_phase",
            filter_code=query_filters.log_notification_phase("log_command_name"),
            options=query_filters.tri_state_log_notifications_options(),
        ),
    )
)


def bi_aggr_service_used(on: bool, row: Row) -> bool:
    # should be in query_filters, but it creates a cyclical import at the moment
    return bi.is_part_of_aggregation(row["host_name"], row["service_description"]) is on


filter_registry.register(
    FilterOption(
        title=_l("Used in BI aggregate"),
        sort_index=300,
        info="service",
        query_filter=query_filters.TristateQuery(
            ident="aggr_service_used",
            filter_code=lambda x: "",
            filter_row=bi_aggr_service_used,
        ),
        is_show_more=True,
    )
)


filter_registry.register(
    InputTextFilter(
        title=_l("Downtime ID"),
        sort_index=301,
        info="downtime",
        query_filter=query_filters.TextQuery(ident="downtime_id", op="="),
    )
)


class TagFilter(Filter):
    def __init__(
        self,
        *,
        title: Union[str, LazyString],
        query_filter: query_filters.TagsQuery,
        is_show_more: bool = False,
    ):

        self.query_filter = query_filter
        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=302,
            info=self.query_filter.object_type,
            htmlvars=self.query_filter.request_vars,
            link_columns=[],
            is_show_more=is_show_more,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        operators: Choices = [
            ("", ""),
            ("is", "="),
            ("isnot", "≠"),
        ]

        html.open_table()
        for num in range(self.query_filter.count):
            prefix = "%s_%d" % (self.query_filter.var_prefix, num)
            html.open_tr()
            html.open_td()
            grp_value = value.get(prefix + "_grp", "")
            grp_choices = [(grp_value, grp_value)] if grp_value else []
            html.dropdown(
                prefix + "_grp",
                grp_choices,
                grp_value,
                style="width: 129px;",
                class_=["ajax-vals"],
                data_autocompleter=json.dumps(
                    AutocompleterConfig(
                        ident="tag_groups",
                        strict=True,
                    ).config
                ),
            )

            html.close_td()
            html.open_td()
            html.dropdown(
                prefix + "_op",
                operators,
                style="width:36px",
                ordered=True,
                class_="op",
            )
            html.close_td()
            html.open_td()

            current_value = value.get(prefix + "_val", "")
            choices = [(current_value, current_value)] if current_value else []
            html.dropdown(
                prefix + "_val",
                choices,
                current_value,
                style="width: 129px;",
                class_=["ajax-vals"],
                data_autocompleter=json.dumps(
                    AutocompleterConfig(
                        ident="tag_groups_opt",
                        strict=True,
                        dynamic_params_callback_name="tag_group_options_autocompleter",
                    ).config
                ),
            )

            html.close_td()
            html.close_tr()
        html.close_table()

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)


filter_registry.register(
    TagFilter(
        title=_l("Host Tags"),
        query_filter=query_filters.TagsQuery(object_type="host"),
    )
)

filter_registry.register(
    TagFilter(
        title=_l("Tags"),
        query_filter=query_filters.TagsQuery(object_type="service"),
        is_show_more=True,
    )
)


@filter_registry.register_instance
class FilterHostAuxTags(Filter):
    def __init__(self):
        self.query_filter = query_filters.AuxTagsQuery(object_type="host")
        super().__init__(
            ident=self.query_filter.ident,
            title=_l("Host Auxiliary Tags"),
            sort_index=302,
            info=self.query_filter.object_type,
            htmlvars=self.query_filter.request_vars,
            link_columns=[],
            is_show_more=True,
        )

    def display(self, value: FilterHTTPVariables) -> None:
        for num in range(self.query_filter.count):
            varname = "%s_%d" % (self.query_filter.var_prefix, num)
            html.dropdown(
                varname, self._options(), deflt=value.get(varname, ""), ordered=True, class_="neg"
            )
            html.open_nobr()
            html.checkbox(varname + "_neg", bool(value.get(varname)), label=_("negate"))
            html.close_nobr()

    @staticmethod
    def _options() -> Choices:
        aux_tag_choices: Choices = [("", "")]
        return aux_tag_choices + list(active_config.tags.aux_tag_list.get_choices())

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)


class LabelFilter(Filter):
    def __init__(
        self,
        *,
        title: Union[str, LazyString],
        object_type: Literal["host", "service"],
    ) -> None:
        self.query_filter = query_filters.AllLabelsQuery(object_type=object_type)
        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=301,
            info=self.query_filter.object_type,
            htmlvars=self.query_filter.request_vars,
            link_columns=[],
        )

    def heading_info(self, value: FilterHTTPVariables) -> Optional[str]:
        return " ".join(f"{e.id}:{e.value}" for e in sorted(self.query_filter.parse_value(value)))

    def request_vars_from_row(self, row: Row) -> Dict[str, str]:
        return {self.query_filter.request_vars[0]: row[self.query_filter.ident]}

    def _valuespec(self):
        return Labels(world=Labels.World.CORE)

    def display(self, value: FilterHTTPVariables) -> None:
        self._valuespec().render_input(
            self.query_filter.request_vars[0],
            {e.id: e.value for e in self.query_filter.parse_value(value)},
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)


filter_registry.register(
    LabelFilter(
        title=_l("Host labels"),
        object_type="host",
    )
)

filter_registry.register(
    LabelFilter(
        title=_l("Service labels"),
        object_type="service",
    )
)


def filter_kubernetes_register(
    title: str,
    object_name: Literal["cluster", "node", "deployment", "namespace", "daemonset", "statefulset"],
):
    filter_registry.register(
        AjaxDropdownFilter(
            title=title,
            sort_index=550,
            info="host",
            autocompleter=GroupAutocompleterConfig(
                ident="kubernetes_labels",
                group_type=object_name,
                strict=True,
            ),
            query_filter=query_filters.KubernetesQuery(
                ident=f"kubernetes_{object_name}", kubernetes_object_type=object_name
            ),
        )
    )


filter_kubernetes_register(_("Kubernetes Cluster"), "cluster")
filter_kubernetes_register(_("Kubernetes Namespace"), "namespace")
filter_kubernetes_register(_("Kubernetes Node"), "node")
filter_kubernetes_register(_("Kubernetes Deployment"), "deployment")
filter_kubernetes_register(_("Kubernetes DaemonSet"), "daemonset")
filter_kubernetes_register(_("Kubernetes StatefulSet"), "statefulset")


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
    for ident, attr_spec in active_config.custom_service_attributes.items():
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
    for attr_spec in active_config.wato_host_attrs:
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
        choices = sorted(active_config.mkeventd_service_levels[:])
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
            for val, _readable in active_config.mkeventd_service_levels
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


def filter_starred_with_register(
    *, what: Literal["host", "service"], title: Union[str, LazyString], sort_index: int
) -> None:
    filter_registry.register(
        FilterOption(
            title=title,
            sort_index=sort_index,
            info=what,
            query_filter=query_filters.TristateQuery(
                ident=what + "_favorites",
                filter_code=query_filters.starred(what),
            ),
            is_show_more=True,
        )
    )


filter_starred_with_register(
    what="host",
    title=_l("Favorite Hosts"),
    sort_index=501,
)

filter_starred_with_register(
    what="service",
    title=_l("Favorite Services"),
    sort_index=501,
)

filter_registry.register(
    CheckboxRowFilter(
        title=_l("Discovery state"),
        sort_index=601,
        info="discovery",
        query_filter=query_filters.MultipleOptionsQuery(
            ident="discovery_state",
            options=query_filters.discovery_state_options(),
            rows_filter=partial(query_filters.discovery_state_filter_table, "discovery_state"),
        ),
    )
)


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
        return empty_choices + list(bi.aggregation_group_choices())

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
    InputTextFilter(
        title=_l("Event ID"),
        sort_index=200,
        info="event",
        query_filter=query_filters.TextQuery(ident="event_id", op="="),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("ID of rule"),
        sort_index=200,
        info="event",
        query_filter=query_filters.TextQuery(ident="event_rule_id", op="="),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Message/Text of event"),
        sort_index=201,
        info="event",
        query_filter=query_filters.TextQuery(ident="event_text", op="~~"),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Application / Syslog-Tag"),
        sort_index=201,
        info="event",
        query_filter=query_filters.TextQuery(
            ident="event_application",
            op="~~",
        ),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Contact Person"),
        sort_index=201,
        info="event",
        query_filter=query_filters.TextQuery(ident="event_contact", op="~~"),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Comment to the event"),
        sort_index=201,
        info="event",
        query_filter=query_filters.TextQuery(ident="event_comment", op="~~"),
    )
)

filter_registry.register(
    RegExpFilter(
        title=_l("Hostname of original event"),
        sort_index=201,
        info="event",
        query_filter=query_filters.TextQuery(
            ident="event_host_regex", op="~~", column="event_host"
        ),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Hostname of event, exact match"),
        sort_index=201,
        info="event",
        query_filter=query_filters.TextQuery(ident="event_host", op="="),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Original IP Address of event"),
        sort_index=201,
        info="event",
        query_filter=query_filters.TextQuery(ident="event_ipaddress", op="~~"),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Owner of event"),
        sort_index=201,
        info="event",
        query_filter=query_filters.TextQuery(ident="event_owner", op="~~"),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("User that performed action"),
        sort_index=221,
        info="history",
        query_filter=query_filters.TextQuery(ident="history_who", op="~~"),
    )
)

filter_registry.register(
    InputTextFilter(
        title=_l("Line number in history logfile"),
        sort_index=222,
        info="history",
        query_filter=query_filters.TextQuery(ident="history_line", op="="),
    )
)

filter_nagios_flag_with_register(
    ident="event_host_in_downtime",
    title=_l("Host in downtime during event creation"),
    sort_index=223,
    info="event",
)

filter_registry.register(
    FilterNumberRange(
        title=_l("Message count"),
        sort_index=205,
        info="event",
        query_filter=query_filters.NumberRangeQuery(ident="event_count"),
    )
)

filter_registry.register(
    CheckboxRowFilter(
        title=_l("State classification"),
        sort_index=206,
        info="event",
        query_filter=query_filters.MultipleOptionsQuery(
            ident="event_state",
            options=query_filters.svc_state_min_options("event_state_"),
            livestatus_query=partial(query_filters.options_toggled_filter, "event_state"),
        ),
    )
)

filter_registry.register(
    CheckboxRowFilter(
        title=_l("Phase"),
        sort_index=207,
        info="event",
        query_filter=query_filters.MultipleOptionsQuery(
            ident="event_phase",
            options=[("event_phase_" + var, title) for var, title in mkeventd.phase_names.items()],
            livestatus_query=partial(query_filters.options_toggled_filter, "event_phase"),
        ),
    )
)

filter_registry.register(
    CheckboxRowFilter(
        title=_l("Syslog Priority"),
        sort_index=209,
        info="event",
        query_filter=query_filters.MultipleOptionsQuery(
            ident="event_priority",
            options=[("event_priority_%d" % e[0], e[1]) for e in mkeventd.syslog_priorities],
            livestatus_query=partial(query_filters.options_toggled_filter, "event_priority"),
        ),
    )
)

filter_registry.register(
    CheckboxRowFilter(
        title=_l("History action type"),
        sort_index=225,
        info="history",
        query_filter=query_filters.MultipleOptionsQuery(
            ident="history_what",
            options=[("history_what_%s" % k, k) for k in mkeventd.action_whats],
            livestatus_query=partial(query_filters.options_toggled_filter, "history_what"),
        ),
    )
)

filter_registry.register(
    FilterTime(
        title=_l("First occurrence of event"),
        sort_index=220,
        info="event",
        query_filter=query_filters.TimeQuery(ident="event_first"),
    )
)

filter_registry.register(
    FilterTime(
        title=_l("Last occurrance of event"),
        sort_index=221,
        info="event",
        query_filter=query_filters.TimeQuery(ident="event_last"),
    )
)

filter_registry.register(
    FilterTime(
        title=_l("Time of entry in event history"),
        sort_index=222,
        info="history",
        query_filter=query_filters.TimeQuery(
            ident="history_time",
        ),
    )
)

filter_registry.register(
    AjaxDropdownFilter(
        title=_l("Syslog Facility"),
        sort_index=210,
        info="event",
        autocompleter=AutocompleterConfig(ident="syslog_facilities", strict=True),
        query_filter=query_filters.TextQuery(ident="event_facility", op="="),
    )
)

filter_registry.register(
    AjaxDropdownFilter(
        title=_l("Service Level at least"),
        sort_index=211,
        info="event",
        autocompleter=AutocompleterConfig(ident="service_levels"),
        query_filter=query_filters.TextQuery(ident="event_sl", op=">="),
    )
)

filter_registry.register(
    AjaxDropdownFilter(
        title=_l("Service Level at most"),
        sort_index=211,
        info="event",
        autocompleter=AutocompleterConfig(ident="service_levels"),
        query_filter=query_filters.TextQuery(ident="event_sl_max", op="<=", column="event_sl"),
    )
)

# TODO: Cleanup as a dropdown visual Filter later on
@filter_registry.register_instance
class FilterOptEventEffectiveContactgroup(FilterGroupCombo):
    def __init__(self):
        super().__init__(
            title=_l("Contact group (effective)"),
            sort_index=212,
            group_type="event_effective_contact",
            autocompleter=GroupAutocompleterConfig(ident="allgroups", group_type="contact"),
            query_filter=query_filters.OptEventEffectiveContactgroupQuery(),
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
            doc_ref = html.resolve_help_text_macros(
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
                    + doc_ref
                )
            raise MKMissingDataError(
                _(
                    "As soon as you add your Checkmk server(s) to the monitoring, a graph showing "
                    "the history of your host problems will appear here. Currently the following "
                    "Checkmk sites are not monitored: %s. "
                )
                % ", ".join(connected_sites - unique_sites_from_services)
                + doc_ref
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
