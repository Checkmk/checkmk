#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Protocol

from cmk.gui.dashboard.type_defs import MonitoringTableName
from cmk.gui.monitor.hosts.table import (
    HOST_TABLE,
    HostEntry,
    HostOptionalField,
    HostTable,
    MonitorFolders,
)
from cmk.gui.monitor.table_widget import TableCatalog, TableRows
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.type_defs import SingleInfos, VisualContext
from cmk.gui.watolib.hosts_and_folders import FolderReader


class MonitoringTableSource[R](Protocol):
    def rows(
        self, *, columns: Sequence[str], sort: Sequence[str], limit: int, context: VisualContext
    ) -> TableRows[R]: ...


@dataclass(frozen=True)
class MonitoringTableSpec[R]:
    catalog: TableCatalog[object]
    infos: SingleInfos
    source: Callable[[ApiContext], MonitoringTableSource[R]]


def _host_row_fields(api_context: ApiContext) -> frozenset[HostOptionalField]:
    # The viewer of a shared dashboard has no session, to open the graphs page or load their
    # preview with, so a row only links to its graphs for a logged-in viewer.
    if api_context.token is not None:
        return frozenset()
    return frozenset({HostOptionalField.GRAPHS_LINK})


MONITORING_TABLES: Final[Mapping[MonitoringTableName, MonitoringTableSpec[HostEntry]]] = {
    "hosts": MonitoringTableSpec(
        catalog=HOST_TABLE,
        infos=["host"],
        source=lambda api_context: HostTable(
            api_context.config.sites,
            MonitorFolders(FolderReader(api_context.config, api_context.user)),
            tag_groups=frozenset(group.id for group in api_context.config.tags.tag_groups),
            row_fields=_host_row_fields(api_context),
        ),
    ),
}
