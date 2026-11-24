#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Final, Literal

from cmk.gui.monitor.legacy_context import (
    build_column_filter_check,
    check_and_keep_tree,
    ContextFilterTranslation,
    NestedField,
    PageFilterModel,
    translate_context,
)
from cmk.gui.monitor.shared import (
    BooleanField,
    NameListField,
    NumericField,
    StringField,
)
from cmk.gui.monitor.site_scope import SiteScopedFilter
from cmk.gui.type_defs import FilterName, VisualContext
from cmk.shared_typing.monitoring.page_filter_condition import (
    AllServicesFilterCondition,
    HostServicesFilterCondition,
)

from ._api._filters import (
    scope_filter_by_site,
    SERVICE_FILTER_NODE,
    ServiceFilterNode,
    ServiceNameListField,
)

type _ServiceField = (
    ServiceNameListField
    | Literal[
        "site_id",
        "name",
        "host_name",
        "host_state",
        "summary",
        "state",
        "stale",
        "acknowledged",
        "in_downtime",
        "is_flapping",
        "notifications_enabled",
        "in_notification_period",
        "in_service_period",
    ]
)

type _HostField = StringField | NameListField | BooleanField | NumericField | Literal["state"]

type _HostNestedField = NestedField[Literal["host"], _HostField]

_PAGE = PageFilterModel(tree=SERVICE_FILTER_NODE, check=scope_filter_by_site)

_PAGE_FOR_ALL_SERVICES_LINKS = PageFilterModel(
    tree=SERVICE_FILTER_NODE,
    check=check_and_keep_tree(scope_filter_by_site),
    accepts_shape=build_column_filter_check(frozenset(AllServicesFilterCondition)),
)

# Services of host has no column for the host or its site: a link reports a filter on them, unless
# it picks the host the page shows.
_PAGE_FOR_HOST_SERVICES_LINKS = PageFilterModel(
    tree=SERVICE_FILTER_NODE,
    check=check_and_keep_tree(scope_filter_by_site),
    accepts_shape=build_column_filter_check(frozenset(HostServicesFilterCondition)),
)

_FIELDS: Mapping[FilterName, _ServiceField | _HostNestedField] = {
    "sites": "site_id",
    "site": "site_id",
    "siteopt": "site_id",
    "serviceregex": "name",
    "service": "name",
    "output": "summary",
    "svcstate": "state",
    "service_staleness": "stale",
    "service_acknowledged": "acknowledged",
    "service_scheduled_downtime_depth": "in_downtime",
    "service_is_flapping": "is_flapping",
    "service_notifications_enabled": "notifications_enabled",
    "service_in_notification_period": "in_notification_period",
    "service_in_service_period": "in_service_period",
    "service_ctc": "contacts",
    "service_ctc_regex": "contacts",
    "optservice_contactgroup": "contact_groups",
    "servicegroups": "groups",
    "host": NestedField("host", "name"),
    "hostregex": NestedField("host", "name"),
    "hostalias": NestedField("host", "alias"),
    "host_address": NestedField("host", "address"),
    "host_ctc": NestedField("host", "contacts"),
    "opthost_contactgroup": NestedField("host", "contact_groups"),
    "hoststate": NestedField("host", "state"),
    "host_staleness": NestedField("host", "stale"),
    "host_acknowledged": NestedField("host", "acknowledged"),
    "host_notifications_enabled": NestedField("host", "notifications_enabled"),
    "host_in_notification_period": NestedField("host", "in_notification_period"),
    "host_in_service_period": NestedField("host", "in_service_period"),
    "host_scheduled_downtime_depth": NestedField("host", "in_downtime"),
    "host_num_services": NestedField("host", "num_services"),
}


def translate_filters(
    context: VisualContext,
) -> ContextFilterTranslation[SiteScopedFilter[ServiceFilterNode]]:
    return translate_context(context, _FIELDS, _PAGE)


# The columns of the pages filter on the host of a service by fields of the service, not in nested
# host nodes. Which of the fields a page's columns filter on is up to its PageFilterModel.
_FIELDS_FOR_LINKS: Mapping[FilterName, _ServiceField] = {
    **{name: field for name, field in _FIELDS.items() if not isinstance(field, NestedField)},
    "host": "host_name",
    "hostregex": "host_name",
    "hoststate": "host_state",
}

# Which host Services of host shows, and from which site, is in the page's own URL variables.
_FILTERS_PICKING_THE_HOST: Final = frozenset({"host", "site", "siteopt", "sites"})


def translate_filters_for_all_services_link(
    context: VisualContext,
) -> ContextFilterTranslation[ServiceFilterNode]:
    """Translate the filters of a legacy view into the tree a link to All services carries."""
    return translate_context(context, _FIELDS_FOR_LINKS, _PAGE_FOR_ALL_SERVICES_LINKS)


def translate_filters_for_host_services_link(
    context: VisualContext,
) -> ContextFilterTranslation[ServiceFilterNode]:
    """Translate the filters of a legacy view into the tree a link to Services of host carries.

    Skip the filters that pick the host, without reporting them: the link names the host on its
    own."""
    return translate_context(
        remove_host_picking_filters(context), _FIELDS_FOR_LINKS, _PAGE_FOR_HOST_SERVICES_LINKS
    )


def remove_host_picking_filters(context: VisualContext) -> VisualContext:
    """Remove the filters that pick the host and site Services of host shows. A link to the page
    names them in its own URL variables, so they are neither taken over nor reported."""
    return {name: value for name, value in context.items() if name not in _FILTERS_PICKING_THE_HOST}
