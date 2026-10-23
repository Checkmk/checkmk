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

_PAGE = PageFilterModel[ServiceFilterNode, ServiceFilterNode](
    tree=SERVICE_FILTER_NODE, check=lambda node: node
)

_FIELDS: Mapping[FilterName, _ServiceField] = {
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
}


def translate_filters(context: VisualContext) -> ContextFilterTranslation[ServiceFilterNode]:
    return translate_context(context, _FIELDS, _PAGE)
