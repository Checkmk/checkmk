#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from cmk.gui.monitor.legacy_context import (
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
from cmk.gui.type_defs import FilterName, VisualContext

from ._api._filters import SERVICE_FILTER_NODE, ServiceFilterNode, ServiceNameListField

type _ServiceField = (
    ServiceNameListField
    | Literal[
        "name",
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

_PAGE = PageFilterModel[ServiceFilterNode, ServiceFilterNode](
    tree=SERVICE_FILTER_NODE, check=lambda node: node
)

_FIELDS: Mapping[FilterName, _ServiceField | _HostNestedField] = {
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


def translate_filters(context: VisualContext) -> ContextFilterTranslation[ServiceFilterNode]:
    return translate_context(context, _FIELDS, _PAGE)
