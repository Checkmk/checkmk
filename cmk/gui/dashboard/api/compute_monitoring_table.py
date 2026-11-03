#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from http import HTTPStatus
from typing import Annotated, TypeIs

from pydantic import Discriminator

from cmk.gui import visuals
from cmk.gui.dashboard.monitoring_tables import MONITORING_TABLES
from cmk.gui.dashboard.type_defs import MonitoringTableName
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


class _MonitoringTableComputation:
    def __init__(
        self, api_context: ApiContext, widget: ResolvedWidget[MonitoringTableContent]
    ) -> None:
        self._api_context = api_context
        self._widget = widget

    def compute(self, sort_override: Sequence[str] | None) -> MonitoringTable:
        content = self._widget.content
        sort = content.sort if sort_override is None else sort_override
        try:
            computed = (
                MONITORING_TABLES[content.table]
                .source(self._api_context)
                .rows(
                    columns=content.columns,
                    sort=sort,
                    limit=content.limit,
                    context=self._context_for_infos(),
                )
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
        )

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
            _MonitoringTableComputation(api_context, widget).compute(sort_override)
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
            ]
        )
    ),
    doc=EndpointDoc(family=DASHBOARD_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=compute_monitoring_table)},
    allowed_tokens={"dashboard"},
)
