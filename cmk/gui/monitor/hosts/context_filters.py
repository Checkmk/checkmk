#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from cmk.gui.monitor.legacy_context import (
    ContextFilterTranslation,
    PageFilterModel,
    translate_context,
)
from cmk.gui.type_defs import FilterName, VisualContext

from ._api._filters import (
    BooleanField,
    FILTER_NODE,
    LabelField,
    NameListField,
    NumericField,
    scope_filter_by_site,
    SiteScopedFilter,
    StringField,
)

type _HostField = (
    StringField
    | NameListField
    | BooleanField
    | NumericField
    | LabelField
    | Literal["site_id", "state"]
)

_PAGE = PageFilterModel(tree=FILTER_NODE, check=scope_filter_by_site)

_FIELDS: Mapping[FilterName, _HostField | Mapping[str, _HostField]] = {
    "sites": "site_id",
    "site": "site_id",
    "siteopt": "site_id",
    "host": "name",
    "hostregex": "name",
    "hostalias": "alias",
    "hostnameoralias": {"name": "name", "alias": "alias"},
    "host_address": "address",
    "opthostgroup": "groups",
    "host_ctc": "contacts",
    "host_ctc_regex": "contacts",
    "opthost_contactgroup": "contact_groups",
    "hoststate": "state",
    "hosts_having_service_problems": {
        "warn": "num_services_warn",
        "crit": "num_services_crit",
        "pending": "num_services_pending",
        "unknown": "num_services_unknown",
    },
    "host_staleness": "stale",
    "host_acknowledged": "acknowledged",
    "host_notifications_enabled": "notifications_enabled",
    "host_in_notification_period": "in_notification_period",
    "host_in_service_period": "in_service_period",
    "host_scheduled_downtime_depth": "in_downtime",
    "host_num_services": "num_services",
    "address_family": "tags",
    "address_families": "tags",
    "host_auxtags": "tags",
    "kubernetes_cluster": "labels",
    "kubernetes_namespace": "labels",
    "kubernetes_node": "labels",
    "kubernetes_deployment": "labels",
    "kubernetes_daemonset": "labels",
    "kubernetes_statefulset": "labels",
}


def translate_filters(context: VisualContext) -> ContextFilterTranslation[SiteScopedFilter]:
    return translate_context(context, _FIELDS, _PAGE)
