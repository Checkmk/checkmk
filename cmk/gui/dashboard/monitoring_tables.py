#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Protocol

from cmk.gui.dashboard.type_defs import MonitoringTableName
from cmk.gui.monitor.command import (
    host_setup_links,
    HOST_SUPPORTED_ACTIONS,
    HostSetupLink,
    MonitorCommand,
    MonitorCommands,
    MonitorObjectType,
)
from cmk.gui.monitor.hosts.table import (
    HOST_TABLE,
    HostEntry,
    HostOptionalField,
    HostTable,
    MonitorFolders,
)
from cmk.gui.monitor.services.table import (
    SERVICE_SUPPORTED_ACTIONS,
    SERVICE_TABLE,
    ServiceEntry,
    ServiceOptionalField,
    ServiceTable,
)
from cmk.gui.monitor.table_widget import TableCatalog, TableRows
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.type_defs import SingleInfos, VisualContext
from cmk.gui.watolib.hosts_and_folders import FolderReader


class MonitoringTableSource[R](Protocol):
    def rows(
        self, *, columns: Sequence[str], sort: Sequence[str], limit: int, context: VisualContext
    ) -> TableRows[R]: ...


def _reads_shared_dashboard(api_context: ApiContext) -> bool:
    """Whether the table is read for a shared dashboard.

    A shared dashboard reads its tables with a token, which acts as the user who shared it. Its
    viewer has no session, and the token reaches no endpoint that runs an action."""
    return api_context.token is not None


def _no_links(_api_context: ApiContext) -> Sequence[HostSetupLink]:
    return []


def _host_setup_links(api_context: ApiContext) -> Sequence[HostSetupLink]:
    if _reads_shared_dashboard(api_context):
        return []
    return host_setup_links(api_context.config, api_context.user)


@dataclass(frozen=True)
class RowOffer:
    """What the page of an object type offers to do with one of its objects."""

    object_type: MonitorObjectType
    supported_actions: tuple[str, ...]
    links: Callable[[ApiContext], Sequence[HostSetupLink]] = _no_links

    def actions(
        self, api_context: ApiContext, commands: MonitorCommands
    ) -> Sequence[MonitorCommand]:
        """The commands the reader may run on the object."""
        if _reads_shared_dashboard(api_context):
            return []
        return commands.permitted_actions(
            api_context.user, self.object_type, self.supported_actions
        )


_HOST_OFFER: Final = RowOffer("host", HOST_SUPPORTED_ACTIONS, links=_host_setup_links)
_SERVICE_OFFER: Final = RowOffer("service", SERVICE_SUPPORTED_ACTIONS)


@dataclass(frozen=True)
class MonitoringTableSpec[R]:
    catalog: TableCatalog[object]
    infos: SingleInfos
    source: Callable[[ApiContext], MonitoringTableSource[R]]
    row_offer: RowOffer
    # What the table offers for the host of a row, if its rows are not hosts themselves: the page
    # of the table's objects offers that too.
    host_offer: RowOffer | None = None


def _graphs_link_field[F](api_context: ApiContext, graphs_link: F) -> frozenset[F]:
    # The viewer of a shared dashboard has no session, to open the graphs page or load their
    # preview with, so a row only links to its graphs for a logged-in viewer.
    if _reads_shared_dashboard(api_context):
        return frozenset()
    return frozenset({graphs_link})


def _host_row_fields(api_context: ApiContext) -> frozenset[HostOptionalField]:
    fields = _graphs_link_field(api_context, HostOptionalField.GRAPHS_LINK)
    # A row linking into Setup says whether the user may open its host there.
    if _host_setup_links(api_context):
        return fields | {HostOptionalField.SETUP_ACCESS}
    return fields


MONITORING_TABLES: Final[
    Mapping[MonitoringTableName, MonitoringTableSpec[HostEntry] | MonitoringTableSpec[ServiceEntry]]
] = {
    "hosts": MonitoringTableSpec(
        catalog=HOST_TABLE,
        infos=["host"],
        source=lambda api_context: HostTable(
            api_context.config.sites,
            MonitorFolders(FolderReader(api_context.config, api_context.user)),
            tag_groups=frozenset(group.id for group in api_context.config.tags.tag_groups),
            row_fields=_host_row_fields(api_context),
        ),
        row_offer=_HOST_OFFER,
    ),
    "services": MonitoringTableSpec(
        catalog=SERVICE_TABLE,
        infos=["host", "service"],
        source=lambda api_context: ServiceTable(
            api_context.config.sites,
            row_fields=_graphs_link_field(api_context, ServiceOptionalField.GRAPHS_LINK),
        ),
        row_offer=_SERVICE_OFFER,
        host_offer=_HOST_OFFER,
    ),
}
