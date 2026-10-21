#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated, Literal, override, Self

from annotated_types import Interval, MinLen
from pydantic import model_validator

from cmk.gui.dashboard.monitoring_tables import MONITORING_TABLES
from cmk.gui.dashboard.type_defs import (
    MonitoringTableDashletConfig,
    MonitoringTableDateFormat,
    MonitoringTableName,
    MonitoringTableTimestampFormat,
)
from cmk.gui.openapi.framework.model import api_field, api_model

from ._base import BaseWidgetContent

MAX_MONITORING_TABLE_ROWS = 5000


@api_model
class MonitoringTableContent(BaseWidgetContent):
    type: Literal["monitoring_table"] = api_field(
        description="Displays a monitoring table with the rows the dashboard filters select."
    )
    table: MonitoringTableName = api_field(
        description="The monitoring table to display.", example="hosts"
    )
    columns: Annotated[list[str], MinLen(1)] = api_field(
        description="The columns to display, in this order. Allowed columns per table: "
        + "; ".join(
            f"{name}: {', '.join(spec.catalog.column_ids)}"
            for name, spec in MONITORING_TABLES.items()
        )
        + ".",
        example=["state", "name", "num_services"],
    )
    sort: list[str] = api_field(
        description=(
            "The initial sort. Each value is 'column:direction', e.g. 'name:asc'; multiple values "
            "sort by several columns in the given order. Only a displayed column can sort."
        ),
        example=["name:asc"],
    )
    limit: Annotated[int, Interval(ge=1, le=MAX_MONITORING_TABLE_ROWS)] = api_field(
        description="The maximum number of rows to display.", example=100
    )
    date_format: MonitoringTableDateFormat = api_field(
        description="The strftime pattern of the date in absolute timestamps.",
        example="%Y-%m-%d",
    )
    timestamp_format: MonitoringTableTimestampFormat = api_field(
        description=(
            "How the timestamp columns, e.g. the check age, render: 'abs' as date and time, 'rel' "
            "as age, 'mixed' as age if less than 48 hours, else as date, 'both' as both, 'epoch' as Unix "
            "timestamp."
        ),
        example="mixed",
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "monitoring_table"

    @model_validator(mode="after")
    def _validate_table(self) -> Self:
        MONITORING_TABLES[self.table].catalog.validate(self.columns, self.sort)
        return self

    @classmethod
    def from_internal(cls, config: MonitoringTableDashletConfig) -> Self:
        return cls(
            type="monitoring_table",
            table=config["table"],
            columns=list(config["columns"]),
            sort=list(config["sort"]),
            limit=config["limit"],
            date_format=config.get("date_format", "%Y-%m-%d"),
            timestamp_format=config.get("timestamp_format", "mixed"),
        )

    @override
    def to_internal(self) -> MonitoringTableDashletConfig:
        return MonitoringTableDashletConfig(
            type=self.internal_type(),
            table=self.table,
            columns=self.columns,
            sort=self.sort,
            limit=self.limit,
            date_format=self.date_format,
            timestamp_format=self.timestamp_format,
        )
