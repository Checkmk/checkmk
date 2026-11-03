#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from cmk.gui.i18n import _l
from cmk.gui.monitor.table_widget import ColumnCatalog, TableColumn

from ._api._validators import parse_host_sort_options
from ._models import HostOptionalField, HostSort, HostSortColumn, HostSortDirection

_ALL_HOSTS_COLUMNS: Final[dict[str, TableColumn[HostOptionalField]]] = {
    "state": TableColumn(_l("State")),
    "modes": TableColumn(_l("Mode")),
    "name": TableColumn(_l("Host")),
    "num_relations": TableColumn(_l("Relations"), HostOptionalField.NUM_RELATIONS),
    "alias": TableColumn(_l("Host alias"), HostOptionalField.ALIAS),
    "address": TableColumn(_l("IP address"), HostOptionalField.ADDRESS),
    "folder": TableColumn(_l("Folder"), HostOptionalField.FOLDER),
    "site_id": TableColumn(_l("Site")),
    "last_check": TableColumn(_l("Last check"), HostOptionalField.LAST_CHECK),
    "last_state_change": TableColumn(_l("Last state change"), HostOptionalField.LAST_STATE_CHANGE),
    "labels": TableColumn(_l("Labels"), HostOptionalField.LABELS),
    "tags": TableColumn(_l("Tags"), HostOptionalField.TAGS),
    "contacts": TableColumn(_l("Contacts"), HostOptionalField.CONTACTS),
    "contact_groups": TableColumn(_l("Contact groups"), HostOptionalField.CONTACT_GROUPS),
    "groups": TableColumn(_l("Host groups"), HostOptionalField.GROUPS),
    "num_services": TableColumn(_l("All services"), HostOptionalField.NUM_SERVICES),
    "num_services_ok": TableColumn(_l("OK"), HostOptionalField.NUM_SERVICES_OK),
    "num_services_warn": TableColumn(_l("Wa"), HostOptionalField.NUM_SERVICES_WARN),
    "num_services_crit": TableColumn(_l("Cr"), HostOptionalField.NUM_SERVICES_CRIT),
    "num_services_unknown": TableColumn(_l("Un"), HostOptionalField.NUM_SERVICES_UNKNOWN),
    "num_services_pending": TableColumn(_l("Pd"), HostOptionalField.NUM_SERVICES_PENDING),
    "customer": TableColumn(_l("Customer")),
}

DEFAULT_HOST_SORT: Final = (HostSort(column=HostSortColumn.NAME, direction=HostSortDirection.ASC),)

ALL_HOSTS_TABLE: Final[ColumnCatalog[HostOptionalField, HostSort]] = ColumnCatalog(
    _ALL_HOSTS_COLUMNS, parse_host_sort_options, DEFAULT_HOST_SORT
)

HOST_TABLE: Final[ColumnCatalog[HostOptionalField, HostSort]] = ColumnCatalog(
    {
        column: spec
        for column, spec in _ALL_HOSTS_COLUMNS.items()
        if column not in {"num_relations", "groups"}
    },
    parse_host_sort_options,
    DEFAULT_HOST_SORT,
)
