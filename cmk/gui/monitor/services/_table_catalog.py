#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from cmk.gui.i18n import _l
from cmk.gui.monitor.table_widget import ColumnCatalog, TableColumn

from ._api._validators import parse_service_sort_options
from ._models import ALL_SERVICES_DEFAULT_SORT, ServiceOptionalField, ServiceSort

_HOST_SERVICES_COLUMNS: Final[dict[str, TableColumn[ServiceOptionalField]]] = {
    "state": TableColumn(_l("State")),
    "modes": TableColumn(_l("Mode")),
    "name": TableColumn(_l("Service")),
    "summary": TableColumn(_l("Summary")),
    "last_state_change": TableColumn(_l("Last state change")),
    "last_check": TableColumn(_l("Last check")),
    "labels": TableColumn(_l("Labels"), ServiceOptionalField.LABELS),
    "tags": TableColumn(_l("Tags"), ServiceOptionalField.TAGS),
    "contacts": TableColumn(_l("Contacts"), ServiceOptionalField.CONTACTS),
    "contact_groups": TableColumn(_l("Contact groups"), ServiceOptionalField.CONTACT_GROUPS),
    "groups": TableColumn(_l("Service groups"), ServiceOptionalField.GROUPS),
    "perfometer": TableColumn(_l("Perf-O-Meter")),
}

HOST_SERVICES_TABLE: Final[ColumnCatalog[ServiceOptionalField, ServiceSort]] = ColumnCatalog(
    _HOST_SERVICES_COLUMNS,
    parse_service_sort_options,
)

SERVICE_TABLE: Final[ColumnCatalog[ServiceOptionalField, ServiceSort]] = ColumnCatalog(
    # The host follows state and modes, where the service rows of All services draw it.
    {
        **{key: _HOST_SERVICES_COLUMNS[key] for key in ("state", "modes")},
        "host_name": TableColumn(_l("Host")),
        **_HOST_SERVICES_COLUMNS,
    },
    parse_service_sort_options,
    ALL_SERVICES_DEFAULT_SORT,
)
