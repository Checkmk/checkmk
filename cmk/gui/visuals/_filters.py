#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"


import re
from collections.abc import Callable, Container, Iterable, Mapping
from functools import partial
from typing import Literal, override

import livestatus

from cmk.ccc.site import SiteId
from cmk.gui import query_filters
from cmk.gui import sites as sites
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKMissingDataError, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.type_defs import (
    ChoiceMapping,
    ColumnName,
    FilterHeader,
    FilterHTTPVariables,
    Row,
    Rows,
    VisualContext,
)
from cmk.gui.utils.autocompleter_config import (
    AutocompleterConfig,
    GroupAutocompleterConfig,
)
from cmk.gui.utils.regex import validate_regex
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.watolib.groups_io import all_groups

from ._livestatus import get_only_sites_from_context
from .filter import (
    AjaxDropdownFilter,
    CheckboxRowFilter,
    DualListFilter,
    Filter,
    FilterGroupCombo,
    FilterNumberRange,
    FilterOption,
    FilterRegistry,
    FilterTime,
    InputTextFilter,
    RegexFilter,
)
from .filter import filter_registry as global_filter_registry
from .filter.components import (
    Checkbox,
    CheckboxGroup,
    Dropdown,
    FilterComponent,
    HorizontalGroup,
    LabelGroupFilterComponent,
    RadioButton,
    StaticText,
    TagFilterComponent,
    TextInput,
)


def register(page_registry: PageRegistry, filter_registry: FilterRegistry) -> None:
    page_registry.register(PageEndpoint("ajax_validate_filter", PageValidateFilter()))
    register_host_and_service_basic_filters(filter_registry)
    register_host_address_filters(filter_registry)
    register_host_and_service_group_filters(filter_registry)
    register_host_and_service_state_filters(filter_registry)
    register_host_and_service_flag_filters(filter_registry)
    register_host_and_service_detail_filters(filter_registry)
    register_contact_filters(filter_registry)
    register_group_table_filters(filter_registry)
    register_comment_filters(filter_registry)
    register_downtime_filters(filter_registry)
    register_log_filters(filter_registry)
    register_tag_and_label_filters(filter_registry)
    register_kubernetes_filters(filter_registry)
    register_custom_attribute_filters(filter_registry)
    register_starred_filters(filter_registry)
    register_discovery_filters(filter_registry)
    register_site_statistics_by_core_filter(filter_registry)


class RegexAjaxDropdownFilter(AjaxDropdownFilter):
    "Select from dropdown with dynamic option query and regex validation"

    def __init__(
        self,
        *,
        title: str | LazyString,
        sort_index: int,
        info: str,
        autocompleter: AutocompleterConfig,
        query_filter: query_filters.TextQuery | query_filters.LabelQuery,
        link_columns: list[ColumnName] | None = None,
        description: None | str | LazyString = None,
        is_show_more: bool = False,
    ) -> None:
        super().__init__(
            title=title,
            sort_index=sort_index,
            info=info,
            autocompleter=autocompleter,
            query_filter=query_filter,
            link_columns=link_columns,
            description=description,
            is_show_more=is_show_more,
            validate_value=validate_regex,
        )


class PageValidateFilter(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        api_request = ctx.request.get_request()
        varname = str(api_request.get("varname"))
        value = str(api_request.get("value"))
        filter_ident = str(api_request.get("filter_ident"))
        filt = global_filter_registry.get(filter_ident)
        if filt:
            try:
                filt.validate_value({varname: value})
            except MKUserError as e:
                user_errors.add(e)

        return {"error_html": html.render_user_errors() if user_errors else ""}


def register_host_and_service_basic_filters(filter_registry: FilterRegistry) -> None:
    filter_registry.register(
        RegexAjaxDropdownFilter(
            title=_l("Host name (regex)"),
            sort_index=100,
            info="host",
            autocompleter=AutocompleterConfig(ident="monitored_hostname", escape_regex=True),
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
            title=_l("Host name (exact match)"),
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
        RegexFilter(
            title=_l("Hostalias (regex)"),
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
        RegexAjaxDropdownFilter(
            title=_l("Service (regex)"),
            sort_index=200,
            info="service",
            autocompleter=AutocompleterConfig(
                ident="monitored_service_description", escape_regex=True
            ),
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
        RegexFilter(
            title=_l("Service alternative display name (regex)"),
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
        RegexFilter(
            title=_l("Summary (plug-in output) (regex)"),
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
        RegexFilter(
            title=_l("Host name or alias (regex)"),  # HostnameOrAliasQuery implements a regex match
            sort_index=102,
            info="host",
            description=_l("Search field allowing regular expressions and partial matches"),
            query_filter=query_filters.HostnameOrAliasQuery(),
        )
    )

    filter_registry.register(
        AjaxDropdownFilter(
            title=_l("Host check command (regex)"),
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
            title=_l("Host check command (exact match)"),
            sort_index=110,
            info="host",
            autocompleter=AutocompleterConfig(ident="check_cmd"),
            query_filter=query_filters.TextQuery(
                ident="host_check_command_exact",
                op="=",
                column="host_check_command",
            ),
        )
    )

    filter_registry.register(
        AjaxDropdownFilter(
            title=_l("Service check command (regex)"),
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

    filter_registry.register(
        AjaxDropdownFilter(
            title=_l("Service check command (exact match)"),
            sort_index=210,
            info="service",
            autocompleter=AutocompleterConfig(ident="check_cmd"),
            query_filter=query_filters.TextQuery(
                ident="check_command_exact",
                op="=",
                column="service_check_command",
            ),
        )
    )


class IPAddressFilter(Filter):
    def __init__(
        self,
        *,
        title: str | LazyString,
        sort_index: int,
        query_filter: query_filters.IPAddressQuery,
        link_columns: list[str],
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

    def components(self) -> Iterable[FilterComponent]:
        yield TextInput(
            id=self.query_filter.request_vars[0],
        )
        yield RadioButton(
            id=self.query_filter.request_vars[1],
            choices=dict(query_filters.ip_match_options()),
            default_value="yes",
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def request_vars_from_row(self, row: Row) -> dict[str, str]:
        return {self.query_filter.request_vars[0]: row["host_address"]}

    def heading_info(self, value: FilterHTTPVariables) -> str | None:
        return value.get(self.query_filter.request_vars[0])


def register_host_address_filters(filter_registry: FilterRegistry) -> None:
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


def register_host_and_service_group_filters(filter_registry: FilterRegistry) -> None:
    filter_registry.register(
        DualListFilter(
            title=_l("Several host groups"),
            sort_index=105,
            description=_l("Selection of multiple host groups"),
            info="host",
            query_filter=query_filters.MultipleQuery(
                ident="hostgroups", column="host_groups", op=">=", negateable=True
            ),
            options=all_groups,  # type: ignore[arg-type]
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
            options=all_groups,  # type: ignore[arg-type]
        )
    )
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


def register_contact_filters(filter_registry: FilterRegistry) -> None:
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
            autocompleter=GroupAutocompleterConfig(ident="allgroups", group_type="contact"),
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
        RegexFilter(
            title=_l("Host contact (regex)"),
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
        RegexFilter(
            title=_l("Service contact (regex)"),
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


def register_group_table_filters(filter_registry: FilterRegistry) -> None:
    filter_registry.register(
        AjaxDropdownFilter(
            title=_l("Host group (exact match)"),
            sort_index=104,
            description=_l("Selection of the host group"),
            info="hostgroup",
            autocompleter=GroupAutocompleterConfig(
                ident="allgroups", group_type="host", strict=True
            ),
            query_filter=query_filters.TextQuery(
                ident="hostgroup",
                column="hostgroup_name",
                op="=",
            ),
        )
    )

    filter_registry.register(
        AjaxDropdownFilter(
            title=_l("Service group (exact match)"),
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
        RegexFilter(
            title=_l("Host group (regex)"),
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
        RegexFilter(
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

    # TODO: Check whether this filter "Service group (enforced)" is a duplicate of "Service group (exact
    #       match)" and if so, remove this one.
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

    filter_registry.register(_FilterHostgroupProblems())

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


# TODO: I would be great to split this in two filters for host & service kind of problems
class _FilterHostgroupProblems(CheckboxRowFilter):
    def __init__(self) -> None:
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

    def components(self) -> Iterable[FilterComponent]:
        yield CheckboxGroup(
            choices=dict(self.svc_problems),
            label="Service states: ",
        )
        yield CheckboxGroup(
            choices=dict(self.host_problems),
            label="Host states: ",
        )


def register_host_and_service_state_filters(filter_registry: FilterRegistry) -> None:
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

    filter_state_type_with_register(
        filter_registry=filter_registry,
        ident="host_state_type",
        title=_l("Host state type"),
        sort_index=116,
        info="host",
    )

    filter_state_type_with_register(
        filter_registry=filter_registry,
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


def filter_state_type_with_register(
    *,
    filter_registry: FilterRegistry,
    ident: str,
    title: str | LazyString,
    sort_index: int,
    info: str,
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


def filter_nagios_flag_with_register(
    *,
    filter_registry: FilterRegistry,
    ident: str,
    title: str | LazyString,
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


def register_host_and_service_flag_filters(filter_registry: FilterRegistry) -> None:
    filter_nagios_flag_with_register(
        filter_registry=filter_registry,
        ident="service_process_performance_data",
        title=_l("Processes performance data"),
        sort_index=250,
        info="service",
        is_show_more=True,
    )

    filter_nagios_flag_with_register(
        filter_registry=filter_registry,
        ident="host_in_notification_period",
        title=_l("Host in notification period"),
        sort_index=130,
        info="host",
    )

    filter_nagios_flag_with_register(
        filter_registry=filter_registry,
        ident="host_in_service_period",
        title=_l("Host in service period"),
        sort_index=130,
        info="host",
    )

    filter_nagios_flag_with_register(
        filter_registry=filter_registry,
        ident="host_acknowledged",
        title=_l("Host problem has been acknowledged"),
        sort_index=131,
        info="host",
    )

    filter_nagios_flag_with_register(
        filter_registry=filter_registry,
        ident="host_active_checks_enabled",
        title=_l("Host active checks enabled"),
        sort_index=132,
        info="host",
        is_show_more=True,
    )

    filter_nagios_flag_with_register(
        filter_registry=filter_registry,
        ident="host_notifications_enabled",
        title=_l("Host notifications enabled"),
        sort_index=133,
        info="host",
    )

    filter_nagios_flag_with_register(
        filter_registry=filter_registry,
        ident="service_acknowledged",
        title=_l("Problem acknowledged"),
        sort_index=230,
        info="service",
    )

    filter_nagios_flag_with_register(
        filter_registry=filter_registry,
        ident="service_in_notification_period",
        title=_l("Service in notification period"),
        sort_index=231,
        info="service",
    )

    filter_nagios_flag_with_register(
        filter_registry=filter_registry,
        ident="service_in_service_period",
        title=_l("Service in service period"),
        sort_index=231,
        info="service",
    )

    filter_nagios_flag_with_register(
        filter_registry=filter_registry,
        ident="service_active_checks_enabled",
        title=_l("Active checks enabled"),
        sort_index=233,
        info="service",
        is_show_more=True,
    )

    filter_nagios_flag_with_register(
        filter_registry=filter_registry,
        ident="service_notifications_enabled",
        title=_l("Notifications enabled"),
        sort_index=234,
        info="service",
    )

    filter_nagios_flag_with_register(
        filter_registry=filter_registry,
        ident="service_is_flapping",
        title=_l("Flapping"),
        sort_index=236,
        info="service",
        is_show_more=True,
    )

    filter_nagios_flag_with_register(
        filter_registry=filter_registry,
        ident="service_scheduled_downtime_depth",
        title=_l("Service in downtime"),
        sort_index=231,
        info="service",
    )

    filter_nagios_flag_with_register(
        filter_registry=filter_registry,
        ident="host_scheduled_downtime_depth",
        title=_l("Host in downtime"),
        sort_index=132,
        info="host",
    )


def register_host_and_service_detail_filters(filter_registry: FilterRegistry) -> None:
    filter_registry.register(
        FilterNumberRange(
            title=_l("Current host notification number"),
            sort_index=232,
            info="host",
            query_filter=query_filters.NumberRangeQuery(
                ident="host_notif_number", column="current_notification_number"
            ),
        )
    )

    filter_registry.register(
        FilterNumberRange(
            title=_l("Current service notification number"),
            sort_index=232,
            info="service",
            query_filter=query_filters.NumberRangeQuery(
                ident="svc_notif_number", column="current_notification_number"
            ),
        )
    )

    filter_registry.register(
        FilterNumberRange(
            title=_l("Number of services of the host"),
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
            query_filter=query_filters.TimeQuery(
                ident="svc_last_check", column="service_last_check"
            ),
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


def register_comment_filters(filter_registry: FilterRegistry) -> None:
    filter_registry.register(
        FilterTime(
            title=_l("Time of comment"),
            sort_index=253,
            info="comment",
            query_filter=query_filters.TimeQuery(ident="comment_entry_time"),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Comment (regex)"),
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
        RegexFilter(
            title=_l("Author comment (regex)"),
            sort_index=259,
            info="comment",
            query_filter=query_filters.TextQuery(
                ident="comment_author",
                op="~~",
                negateable=True,
            ),
        )
    )


def register_downtime_filters(filter_registry: FilterRegistry) -> None:
    filter_registry.register(
        InputTextFilter(
            title=_l("Downtime ID (exact match)"),
            sort_index=301,
            info="downtime",
            query_filter=query_filters.TextQuery(ident="downtime_id", op="="),
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
        RegexFilter(
            title=_l("Downtime comment (regex)"),
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
        RegexFilter(
            title=_l("Downtime author (regex)"),
            sort_index=256,
            info="downtime",
            query_filter=query_filters.TextQuery(ident="downtime_author", op="~"),
        )
    )


def register_log_filters(filter_registry: FilterRegistry) -> None:
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
        RegexFilter(
            title=_l("Log: plug-in output (regex)"),
            sort_index=202,
            info="log",
            query_filter=query_filters.TextQuery(
                ident="log_plugin_output",
                op="~~",
                negateable=True,
            ),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Log: message type (regex)"),
            sort_index=203,
            info="log",
            query_filter=query_filters.TextQuery(ident="log_type", op="~~"),
            show_heading=False,
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l('Log: state type (DEPRECATED: Use "state information") (regex)'),
            sort_index=204,
            info="log",
            query_filter=query_filters.TextQuery(ident="log_state_type", op="~~"),
        )
    )

    filter_registry.register(
        RegexFilter(
            title=_l("Log: state information (regex)"),
            sort_index=204,
            info="log",
            query_filter=query_filters.TextQuery(ident="log_state_info", op="~~"),
        )
    )

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
        RegexFilter(
            title=_l("Log: contact name (regex)"),
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
        RegexFilter(
            title=_l("Log: command (regex)"),
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

    filter_registry.register(_FilterLogState())

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


class FilterLogContactName(InputTextFilter):
    """Special filter class to correctly filter the column contact_name from the log table. This
    list contains comma-separated contact names (user ids), but it is of type string."""

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if current_value := value.get(self.htmlvars[0]):
            new_value = dict(value.items())
            new_value[self.htmlvars[0]] = "(,|^)" + current_value.replace(".", "\\.") + "(,|$)"
            return self.query_filter._filter(new_value)
        return ""


# TODO: I would be great to split this in two filters for host & service states
class _FilterLogState(CheckboxRowFilter):
    def __init__(self) -> None:
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

    def components(self) -> Iterable[FilterComponent]:
        yield CheckboxGroup(
            choices=dict(self.host_states),
            label="Hosts: ",
        )
        yield CheckboxGroup(
            choices=dict(self.service_states),
            label="Services: ",
        )


class TagFilter(Filter):
    def __init__(
        self,
        *,
        title: str | LazyString,
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

    def components(self) -> Iterable[FilterComponent]:
        yield TagFilterComponent(
            display_rows=self.query_filter.count,
            variable_prefix=self.query_filter.var_prefix,
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def value(self) -> FilterHTTPVariables:
        """Returns the current representation of the filter settings from the HTML
        var context. This can be used to persist the filter settings."""
        return dict(request.itervars(self.query_filter.var_prefix))


class _FilterHostAuxTags(Filter):
    def __init__(self) -> None:
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
        # keep this in sync with components(), remove once all filter menus are switched to vue
        # this special styling is not supported by the current components
        for num in range(self.query_filter.count):
            varname = "%s_%d" % (self.query_filter.var_prefix, num)
            negate_varname = varname + "_neg"
            html.dropdown(
                varname,
                self._options().items(),
                deflt=value.get(varname, ""),
                ordered=True,
                class_=["neg"],
            )
            html.open_nobr()
            html.checkbox(negate_varname, bool(value.get(negate_varname)), label=_("negate"))
            html.close_nobr()

    def components(self) -> Iterable[FilterComponent]:
        for num in range(self.query_filter.count):
            varname = "%s_%d" % (self.query_filter.var_prefix, num)
            negate_varname = varname + "_neg"
            yield HorizontalGroup(
                components=[
                    Dropdown(
                        id=varname,
                        choices=self._options(),
                    ),
                    Checkbox(id=negate_varname, default_value=False, label=_("negate")),
                ]
            )

    @staticmethod
    def _options() -> ChoiceMapping:
        aux_tag_choices = {"": ""}
        aux_tag_choices.update(active_config.tags.aux_tag_list.get_choices())
        # Sort the choices by their label
        return dict(sorted(aux_tag_choices.items(), key=lambda x: x[1]))

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)


class LabelGroupFilter(Filter):
    def __init__(
        self,
        *,
        title: str | LazyString,
        object_type: Literal["host", "service"],
    ) -> None:
        self.query_filter = query_filters.AllLabelGroupsQuery(object_type=object_type)
        super().__init__(
            ident=self.query_filter.ident,
            title=title,
            sort_index=301,
            info=self.query_filter.object_type,
            htmlvars=[f"{self.query_filter.ident}_count"],
            link_columns=[],
        )

    def components(self) -> Iterable[FilterComponent]:
        yield LabelGroupFilterComponent(
            id=self.query_filter.ident,
            object_type=self.query_filter.object_type,
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return self.query_filter.filter(value)

    def value(self) -> FilterHTTPVariables:
        """Returns the current representation of the filter settings from the HTML
        var context. This can be used to persist the filter settings."""
        return dict(request.itervars(self.query_filter.ident))


def register_tag_and_label_filters(filter_registry: FilterRegistry) -> None:
    filter_registry.register(
        TagFilter(
            title=_l("Host tags"),
            query_filter=query_filters.TagsQuery(object_type="host"),
        )
    )

    filter_registry.register(
        TagFilter(
            title=_l("Service tags"),
            query_filter=query_filters.TagsQuery(object_type="service"),
            is_show_more=True,
        )
    )

    filter_registry.register(_FilterHostAuxTags())

    filter_registry.register(
        LabelGroupFilter(
            title=_l("Host labels"),
            object_type="host",
        )
    )

    filter_registry.register(
        LabelGroupFilter(
            title=_l("Service labels"),
            object_type="service",
        )
    )


def register_kubernetes_filters(filter_registry: FilterRegistry) -> None:
    filter_kubernetes_register(filter_registry, _("Kubernetes cluster"), "cluster")
    filter_kubernetes_register(filter_registry, _("Kubernetes namespace"), "namespace")
    filter_kubernetes_register(filter_registry, _("Kubernetes node"), "node")
    filter_kubernetes_register(filter_registry, _("Kubernetes deployment"), "deployment")
    filter_kubernetes_register(filter_registry, _("Kubernetes daemonSet"), "daemonset")
    filter_kubernetes_register(filter_registry, _("Kubernetes statefulSet"), "statefulset")


def filter_kubernetes_register(
    filter_registry: FilterRegistry,
    title: str,
    object_name: Literal["cluster", "node", "deployment", "namespace", "daemonset", "statefulset"],
) -> None:
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
            query_filter=query_filters.LabelQuery(
                ident=f"kubernetes_{object_name}",
                label_base="cmk/kubernetes/",
                object_type=object_name,
            ),
        )
    )


class CustomAttributeFilter(Filter):
    def __init__(
        self,
        *,
        ident: str,
        title: str | LazyString,
        info: str,
        choice_func: Callable[[], ChoiceMapping],
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

    def name_varname(self, ident: str) -> str:
        return "%s_name" % ident

    def value_varname(self, ident: str) -> str:
        return "%s_value" % ident

    def components(self) -> Iterable[FilterComponent]:
        yield Dropdown(
            id=self.name_varname(self.ident),
            choices=self._options(),
        )
        yield TextInput(
            id=self.value_varname(self.ident),
        )

    def _options(self) -> ChoiceMapping:
        choices = {"": ""}
        choices.update(self._custom_attribute_choices())
        return choices

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        if not value.get(self.name_varname(self.ident)):
            return ""

        items = self._custom_attribute_choices()
        attribute_id = value[self.name_varname(self.ident)]
        if attribute_id not in items:
            raise MKUserError(
                self.name_varname(self.ident),
                _("The requested item %s does not exist") % attribute_id,
            )
        val = value[self.value_varname(self.ident)]
        return f"Filter: {self.info}_custom_variables ~~ {livestatus.lqencode(attribute_id.upper())} ^{livestatus.lqencode(val)}\n"

    def validate_value(self, value: FilterHTTPVariables) -> None:
        htmlvar = self.value_varname(self.ident)
        validate_regex(value.get(htmlvar, ""), htmlvar)


def _service_attribute_choices() -> ChoiceMapping:
    return {
        ident: attr_spec["title"]
        for ident, attr_spec in sorted(
            active_config.custom_service_attributes.items(), key=lambda item: item[1]["title"]
        )
    }


def _host_attribute_choices() -> ChoiceMapping:
    return {
        attr_spec["name"]: attr_spec["title"]
        for attr_spec in sorted(active_config.wato_host_attrs, key=lambda x: x["title"])
    }


def register_custom_attribute_filters(filter_registry: FilterRegistry) -> None:
    filter_registry.register(
        CustomAttributeFilter(
            ident="service_custom_variable",
            title=_l("Service custom attribute (regex)"),
            info="service",
            choice_func=_service_attribute_choices,
        )
    )

    filter_registry.register(
        CustomAttributeFilter(
            ident="host_custom_variable",
            title=_l("Host custom attribute (regex)"),
            info="host",
            choice_func=_host_attribute_choices,
        )
    )


def filter_starred_with_register(
    *,
    filter_registry: FilterRegistry,
    what: Literal["host", "service"],
    title: str | LazyString,
    sort_index: int,
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


def register_starred_filters(filter_registry: FilterRegistry) -> None:
    filter_starred_with_register(
        filter_registry=filter_registry,
        what="host",
        title=_l("Favorite Hosts"),
        sort_index=501,
    )

    filter_starred_with_register(
        filter_registry=filter_registry,
        what="service",
        title=_l("Favorite Services"),
        sort_index=501,
    )


def register_discovery_filters(filter_registry: FilterRegistry) -> None:
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


class FilterCMKSiteStatisticsByCorePIDs(Filter):
    ID = "service_cmk_site_statistics_core_pid"

    def __init__(
        self,
        *,
        ident: str,
        title: str | LazyString,
        sort_index: int,
        info: str,
        htmlvars: list[str],
        link_columns: list[ColumnName],
    ):
        super().__init__(
            ident=ident,
            title=title,
            sort_index=sort_index,
            info=info,
            htmlvars=htmlvars,
            link_columns=link_columns,
        )

    def components(self) -> Iterable[FilterComponent]:
        yield StaticText(
            text=_(
                "Used in the host and service problems graphs of the main dashboard. Not intended "
                "for any other purposes."
            )
        )

    def filter(self, value: FilterHTTPVariables) -> FilterHeader:
        return (
            f"Filter: service_description ~~ Site ({'|'.join(self._connected_sites_to_pids())}) statistics$"
            if self._should_apply(value)
            else ""
        )

    def columns_for_filter_table(self, context: VisualContext) -> Iterable[str]:
        if self._should_apply(context):
            yield "host_name"
            yield "service_description"
            yield "long_plugin_output"

    def filter_table(self, context: VisualContext, rows: Rows) -> Rows:
        if not self._should_apply(context):
            return rows

        # ids and core pids of connected sites, i.e., what we hope to find the service output
        pids_of_connected_sites = dict(self._connected_sites_to_pids())
        # apply potential filters on sites
        if (only_sites := get_only_sites_from_context(context)) is not None:
            pids_of_connected_sites = {
                site_id: core_pid
                for site_id, core_pid in pids_of_connected_sites.items()
                if site_id in only_sites
            }

        connected_sites = set(pids_of_connected_sites)

        # ids and core pids from the service output
        sites_and_pids_from_services = []
        rows_right_service = []
        # we sort to be independent of the order of the incoming rows
        for row in sorted(
            rows,
            key=lambda r: (r.get("site", ""), r["host_name"], r["service_description"]),
        ):
            if not re.match("Site [^ ]* statistics$", row["service_description"]):
                continue
            rows_right_service.append(row)
            site = row["service_description"].split(" ")[1]
            re_matches_pid = re.findall("Core PID: ([0-9][0-9]*)", row["long_plugin_output"])
            if re_matches_pid:
                pid: int | None = int(re_matches_pid[0])
            else:
                pid = None
            sites_and_pids_from_services.append((site, pid))

        unique_sites_from_services = {site for (site, _pid) in sites_and_pids_from_services}

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
                    "Please refer to the [dashboards#host_problems|Checkmk User Guide] for more details."
                )
            )
            if len(connected_sites) == 1:
                raise MKMissingDataError(
                    _(
                        "As soon as you add your Checkmk server to the "
                        "monitoring, a graph showing the history of your host "
                        "problems will appear here.\n Please also be aware that "
                        "this message might appear as a result of a filtered "
                        "dashboard. This dashlet currently only supports "
                        "filtering for sites."
                    )
                    + doc_ref
                )
            raise MKMissingDataError(
                _(
                    "As soon as you add your Checkmk server(s) to the "
                    "monitoring, a graph showing the history of your host "
                    "problems will appear here. Currently, the following Checkmk "
                    "sites are not monitored: %s\n Please also be aware that "
                    "this message might appear as a result of a filtered "
                    "dashboard. This dashlet currently only supports filtering "
                    "for sites."
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

    @classmethod
    def _should_apply(cls, ctx: Container[str]) -> bool:
        return cls.ID in ctx

    @staticmethod
    def _connected_sites_to_pids() -> Mapping[SiteId, int]:
        return {
            site_id: site_status["core_pid"]
            for site_id, site_status in sites.states().items()
            if site_status["state"] == "online"
        }


def register_site_statistics_by_core_filter(filter_registry: FilterRegistry) -> None:
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
