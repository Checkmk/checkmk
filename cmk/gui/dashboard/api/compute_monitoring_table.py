#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from http import HTTPStatus
from typing import Annotated, TypeIs

from pydantic import Discriminator

from cmk.gui import visuals
from cmk.gui.dashboard.monitoring_tables import MONITORING_TABLES, RowOffer
from cmk.gui.dashboard.type_defs import MonitoringTableName
from cmk.gui.monitor.command import monitor_commands, MonitorCommands
from cmk.gui.monitor.hosts.table import HostEntry
from cmk.gui.monitor.services.table import ServiceEntry
from cmk.gui.monitor.table_widget import InvalidSortError
from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.type_defs import FilterName, VisualContext
from cmk.gui.visuals.filter import filter_registry
from cmk.shared_typing.monitoring.action_ident import MonitoringActionIdent
from cmk.web.utils import permission_verification as permissions

from ._family import DASHBOARD_FAMILY
from ._widget_resolution import (
    no_built_in_link,
    PERMISSIONS_WIDGET_QUERY,
    resolve_widget,
    ResolvedWidget,
)
from .model.response_model import ComputedWidgetResponse
from .model.widget_content._base import BaseWidgetContent
from .model.widget_content.monitoring_table import MonitoringTableContent
from .model.widget_source import ExplicitWidgetContent, SavedWidgetContent

type MonitoringTableSource = Annotated[
    ExplicitWidgetContent[MonitoringTableContent] | SavedWidgetContent, Discriminator("type")
]


@api_model
class MonitoringTableRequest:
    source: MonitoringTableSource = api_field(description="The widget to compute.")
    sort: list[str] | ApiOmitted = api_field(
        description=(
            "The sort the viewer picked, in place of the one the widget stores. Each value is "
            "'column:direction', e.g. 'name:asc'. Only a column the widget displays can sort."
        ),
        example=["name:asc"],
        default_factory=ApiOmitted,
    )


@api_model
class UnappliedFilter:
    id: str = api_field(description="The ID of the dashboard filter.", example="host_labels")
    title: str = api_field(description="The title of the dashboard filter.", example="Host labels")


@api_model
class MonitoringTableAction:
    ident: MonitoringActionIdent = api_field(
        description="The ID of the command.", example="reschedule"
    )
    title: str = api_field(description="The title of the command.", example="Reschedule")
    icon: str = api_field(description="The icon of the command.", example="reload")


@api_model
class MonitoringTableLink:
    ident: str = api_field(description="The ID of the link.", example="edit")
    title: str = api_field(description="The title of the link.", example="Edit host")
    icon: str = api_field(description="The icon of the link.", example="edit")
    url: str = api_field(
        description="The URL of the link, with '{host}' standing for the host of the row.",
        example="wato.py?mode=edit_host&host={host}",
    )


@api_model
class MonitoringTable:
    table: MonitoringTableName = api_field(description="The monitoring table.", example="hosts")
    rows: list[HostEntry | ServiceEntry] = api_field(
        description="The rows of the table, one per monitored object of the table's kind."
    )
    matched: int = api_field(description="The number of rows the filters select.", example=42)
    total: int = api_field(description="The number of rows without any filter.", example=1234)
    unapplied_filters: list[UnappliedFilter] = api_field(
        description=(
            "The dashboard filters in effect that the table cannot apply. The table shows more "
            "rows than these filters would select."
        )
    )
    unreachable_sites: list[str] = api_field(
        description=(
            "IDs of the sites that could not be reached. Their rows are missing from the rows, "
            "'matched' and 'total'."
        ),
        example=["remote_1"],
    )
    actions: list[MonitoringTableAction] = api_field(
        description="The commands the user may run on a row of the table."
    )
    links: list[MonitoringTableLink] = api_field(
        description=(
            "The links into Setup the user may follow from a row of the table. Empty for a "
            "services table."
        )
    )
    host_actions: list[MonitoringTableAction] = api_field(
        description=(
            "The commands the user may run on the host of a row of the table. Empty for a hosts "
            "table, whose rows are the hosts."
        )
    )
    host_links: list[MonitoringTableLink] = api_field(
        description=(
            "The links into Setup the user may follow from the host of a row of the table. Empty "
            "for a hosts table, whose rows are the hosts."
        )
    )


class _MonitoringTableComputation:
    def __init__(
        self,
        api_context: ApiContext,
        widget: ResolvedWidget[MonitoringTableContent],
        commands: MonitorCommands,
    ) -> None:
        self._api_context = api_context
        self._widget = widget
        self._commands = commands

    def compute(self, sort_override: Sequence[str] | None) -> MonitoringTable:
        content = self._widget.content
        sort = content.sort if sort_override is None else sort_override
        spec = MONITORING_TABLES[content.table]
        try:
            computed = spec.source(self._api_context).rows(
                columns=content.columns,
                sort=sort,
                limit=content.limit,
                context=self._context_for_infos(),
            )
        except InvalidSortError as exc:
            raise ProblemException(
                status=HTTPStatus.BAD_REQUEST, title="Invalid sort", detail=str(exc)
            ) from exc
        return MonitoringTable(
            table=content.table,
            rows=list(computed.rows),
            matched=computed.matched,
            total=computed.total,
            unapplied_filters=[
                UnappliedFilter(id=name, title=self._filter_title(name))
                for name in computed.unapplied_filters
            ],
            unreachable_sites=list(computed.unreachable_sites),
            actions=self._actions(spec.row_offer),
            links=self._links(spec.row_offer),
            host_actions=self._actions(spec.host_offer),
            host_links=self._links(spec.host_offer),
        )

    def _actions(self, offer: RowOffer | None) -> list[MonitoringTableAction]:
        if offer is None:
            return []
        return [
            MonitoringTableAction(ident=command.ident, title=str(command.title), icon=command.icon)
            for command in offer.actions(self._api_context, self._commands)
        ]

    def _links(self, offer: RowOffer | None) -> list[MonitoringTableLink]:
        if offer is None:
            return []
        return [
            MonitoringTableLink(ident=link.ident, title=link.title, icon=link.icon, url=link.url)
            for link in offer.links(self._api_context)
        ]

    def _context_for_infos(self) -> VisualContext:
        allowed = visuals.filters_allowed_for_infos(self._widget.infos)
        return {name: value for name, value in self._widget.context.items() if name in allowed}

    @staticmethod
    def _filter_title(name: FilterName) -> str:
        return (
            name
            if (context_filter := filter_registry.get(name)) is None
            else str(context_filter.title)
        )


def _is_monitoring_table(content: BaseWidgetContent) -> TypeIs[MonitoringTableContent]:
    return isinstance(content, MonitoringTableContent)


def compute_monitoring_table(
    api_context: ApiContext, body: MonitoringTableRequest
) -> ComputedWidgetResponse[MonitoringTable]:
    """Compute a monitoring table widget."""
    sort_override = None if isinstance(body.sort, ApiOmitted) else body.sort
    with resolve_widget(api_context, body.source, _is_monitoring_table, no_built_in_link) as widget:
        return ComputedWidgetResponse.of(
            _MonitoringTableComputation(api_context, widget, monitor_commands).compute(
                sort_override
            )
        )


ENDPOINT_COMPUTE_MONITORING_TABLE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href(domain_type="dashboard", action="compute-monitoring-table"),
        link_relation="cmk/compute_monitoring_table",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.AllPerm(
            [
                PERMISSIONS_WIDGET_QUERY,
                permissions.Optional(permissions.OkayToIgnorePerm("wato.see_all_folders")),
                # The row actions offered: the commands the user may run, the links into Setup.
                permissions.Optional(permissions.Perm("general.act")),
                permissions.Optional(permissions.PrefixPerm("action")),
                permissions.Optional(permissions.Perm("mkeventd.archive_events_of_hosts")),
                permissions.Optional(permissions.Perm("wato.use")),
                permissions.Optional(permissions.Perm("wato.seeall")),
                permissions.Optional(permissions.Perm("wato.hosts")),
                permissions.Optional(permissions.Perm("wato.rulesets")),
            ]
        )
    ),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=compute_monitoring_table)},
    allowed_tokens={"dashboard"},
)
