#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterable, Mapping
from typing import Annotated, Literal, override, Self

from pydantic import AfterValidator
from pydantic_core import ErrorDetails

from cmk.gui.dashboard import LinkedViewDashletConfig
from cmk.gui.dashboard.dashlet.dashlets.view import EmbeddedViewDashletConfig
from cmk.gui.data_source import data_source_registry
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.converter import RegistryConverter
from cmk.gui.type_defs import DashboardEmbeddedViewSpec
from cmk.gui.views.store import get_permitted_views

from ._base import BaseWidgetContent


def _validate_view_name(name: str) -> str:
    if name not in get_permitted_views():
        raise ValueError("View does not exist or you don't have permission to see it.")
    return name


@api_model
class LinkedViewContent(BaseWidgetContent):
    type: Literal["linked_view"] = api_field(description="Display an existing view.")
    view_name: Annotated[str, AfterValidator(_validate_view_name)] = api_field(
        description="The name of the view."
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "linked_view"

    @classmethod
    def from_internal(cls, config: LinkedViewDashletConfig) -> Self:
        return cls(
            type="linked_view",
            view_name=config["name"],
        )

    @override
    def to_internal(self) -> LinkedViewDashletConfig:
        return LinkedViewDashletConfig(
            type=self.internal_type(),
            name=self.view_name,
        )


@api_model
class EmbeddedViewContent(BaseWidgetContent):
    type: Literal["embedded_view"] = api_field(
        description="Display a view which is fully defined within the dashboard.",
    )
    embedded_id: str = api_field(
        description=(
            "The internal ID of the view. This must exist in the embedded view definitions."
        ),
    )
    datasource: Annotated[str, AfterValidator(RegistryConverter(data_source_registry).validate)] = (
        api_field(
            description="The datasource of the embedded view. Must match the embedded view.",
        )
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "embedded_view"

    @classmethod
    def from_internal(cls, config: EmbeddedViewDashletConfig) -> Self:
        return cls(
            type="embedded_view",
            embedded_id=config["name"],
            datasource=config["datasource"],
        )

    @override
    def to_internal(self) -> EmbeddedViewDashletConfig:
        return EmbeddedViewDashletConfig(
            type=self.internal_type(),
            name=self.embedded_id,
            datasource=self.datasource,
        )

    def iter_validation_errors(
        self,
        location: tuple[str | int, ...],
        context: ApiContext,
        *,
        embedded_views: Mapping[str, DashboardEmbeddedViewSpec],
    ) -> Iterable[ErrorDetails]:
        if self.embedded_id not in embedded_views:
            yield ErrorDetails(
                type="value_error",
                msg="Embedded view with this ID does not exist.",
                loc=location + ("embedded_id",),
                input=self.embedded_id,
            )
        else:
            embedded_view = embedded_views[self.embedded_id]
            if self.datasource != embedded_view["datasource"]:
                yield ErrorDetails(
                    type="value_error",
                    msg="Datasource does not match the embedded view definition.",
                    loc=location + ("datasource",),
                    input=self.datasource,
                )
