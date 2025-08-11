#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import Annotated, assert_never, Literal, override, Self

from annotated_types import Ge
from pydantic import AfterValidator, Discriminator, model_validator

from cmk.ccc.user import UserId
from cmk.gui.config import active_config
from cmk.gui.dashboard import LinkedViewDashletConfig, ViewDashletConfig
from cmk.gui.data_source import data_source_registry
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.converter import RegistryConverter
from cmk.gui.painter.v0 import all_painters
from cmk.gui.type_defs import (
    ColumnSpec,
    ColumnTypes,
    InventoryJoinMacrosSpec,
    PainterParameters,
    SorterName,
    SorterSpec,
    ViewSpec,
    VisualLinkSpec,
    VisualName,
    VisualTypeName,
)
from cmk.gui.views.layout import layout_registry
from cmk.gui.views.store import get_permitted_views
from cmk.gui.visuals.type import visual_type_registry

from ..type_defs import AnnotatedInfoName
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
class ApiVisualLink:
    type: VisualTypeName = api_field(
        description="The type of the link, e.g. 'views' for a link to another view."
    )
    name: VisualName = api_field(description="The name of the linked entity.")

    @model_validator(mode="after")
    def _validate(self) -> Self:
        visual = visual_type_registry[self.type]()
        if self.name not in visual.permitted_visuals:
            link_type = self.type.title()[:-1]  # remove trailing "s"
            raise ValueError(
                f"{link_type} '{self.name}' does not exist or you don't have permission to see it."
            )
        return self

    @classmethod
    def from_internal(cls, value: VisualLinkSpec | None) -> Self | ApiOmitted:
        if value is None:
            return ApiOmitted()
        return cls(
            type=value.type_name,
            name=value.name,
        )

    @classmethod
    def to_internal(cls, value: Self | ApiOmitted) -> VisualLinkSpec | None:
        if isinstance(value, ApiOmitted):
            return None
        return VisualLinkSpec(
            type_name=value.type,
            name=value.name,
        )


@api_model
class _BaseApiColumnSpec(ABC):
    @property
    @abstractmethod
    def type(self) -> ColumnTypes:
        pass

    @property
    def join_value(self) -> str | None:
        return None

    name: Annotated[
        str, AfterValidator(RegistryConverter(lambda: all_painters(active_config)).validate)
    ] = api_field(description="The name of the painter to render this column.")
    parameters: PainterParameters = api_field(description="The parameters for the painter.")
    link_spec: ApiVisualLink | ApiOmitted = api_field(
        description="Use this column as a link to another view or entity.",
        default_factory=ApiOmitted,
    )
    tooltip: str | ApiOmitted = api_field(
        description="Optional tooltip for this column.",
        default_factory=ApiOmitted,
    )
    column_title: str | ApiOmitted = api_field(
        description="Optional title for this column. If not set, the painter's title will be used.",
        default_factory=ApiOmitted,
    )

    @staticmethod
    def from_internal(
        spec: ColumnSpec,
    ) -> "ApiColumnSpec | ApiJoinColumnSpec | ApiJoinInventoryColumnSpec":
        match spec.column_type:
            case "join_column":
                return ApiJoinColumnSpec.from_internal(spec)
            case "join_inv_column":
                return ApiJoinInventoryColumnSpec.from_internal(spec)
            case "column":
                return ApiColumnSpec.from_internal(spec)

        assert_never(spec)

    def to_internal(self) -> ColumnSpec:
        return ColumnSpec(
            _column_type=self.type,
            name=self.name,
            parameters=self.parameters,
            link_spec=ApiVisualLink.to_internal(self.link_spec),
            tooltip=ApiOmitted.to_optional(self.tooltip),
            join_value=ApiOmitted.to_optional(self.join_value),
            column_title=ApiOmitted.to_optional(self.column_title),
        )


@api_model
class ApiColumnSpec(_BaseApiColumnSpec):
    type: Literal["column"] = api_field(description="A normal column.")

    @classmethod
    @override
    def from_internal(cls, spec: ColumnSpec) -> Self:
        return cls(
            type="column",
            name=spec.name,
            parameters=spec.parameters,
            link_spec=ApiVisualLink.from_internal(spec.link_spec),
            tooltip=ApiOmitted.from_optional(spec.tooltip),
            column_title=ApiOmitted.from_optional(spec.column_title),
        )


@api_model
class ApiJoinColumnSpec(_BaseApiColumnSpec):
    type: Literal["join_column"] = api_field(description="Join data from another source.")
    join_value: str = api_field(
        description="Value to join this column with another column.",
    )

    @classmethod
    @override
    def from_internal(cls, spec: ColumnSpec) -> Self:
        return cls(
            type="join_column",
            name=spec.name,
            parameters=spec.parameters,
            link_spec=ApiVisualLink.from_internal(spec.link_spec),
            tooltip=ApiOmitted.from_optional(spec.tooltip),
            column_title=ApiOmitted.from_optional(spec.column_title),
            join_value=spec.join_value or "",  # this should never be None
        )


@api_model
class ApiJoinInventoryColumnSpec(_BaseApiColumnSpec):
    type: Literal["join_inv_column"] = api_field(description="Join data from the HW/SW inventory.")
    join_value: str = api_field(
        description="Value to join this column with another column.",
    )

    @classmethod
    @override
    def from_internal(cls, spec: ColumnSpec) -> Self:
        return cls(
            type="join_inv_column",
            name=spec.name,
            parameters=spec.parameters,
            link_spec=ApiVisualLink.from_internal(spec.link_spec),
            tooltip=ApiOmitted.from_optional(spec.tooltip),
            column_title=ApiOmitted.from_optional(spec.column_title),
            join_value=spec.join_value or "",  # this should never be None
        )


type ApiAnyColumnSpec = Annotated[
    ApiColumnSpec | ApiJoinColumnSpec | ApiJoinInventoryColumnSpec, Discriminator("type")
]


@api_model
class ApiSorterSpec:
    sorter_name: SorterName = api_field(description="The name of the sorter.")
    parameters: dict[str, object] | ApiOmitted = api_field(
        description="The parameters for the sorter.", default_factory=ApiOmitted
    )
    direction: Literal["asc", "desc"] = api_field(description="The direction of the sorter.")
    join_key: str | ApiOmitted = api_field(
        description="The key to join this sorter with another column.",
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_internal_list(cls, specs: Sequence[SorterSpec]) -> list[Self] | ApiOmitted:
        if not specs:
            return ApiOmitted()
        return [cls.from_internal(spec) for spec in specs]

    @classmethod
    def from_internal(cls, spec: SorterSpec) -> Self:
        if isinstance(spec.sorter, str):
            sorter_name = spec.sorter
            parameters = PainterParameters()
        else:
            sorter_name, parameters = spec.sorter
        return cls(
            sorter_name=sorter_name,
            # NOTE: the parameters are different for each sorter, and the typed dict is incomplete
            parameters=parameters,  # type: ignore[arg-type]
            direction="desc" if spec.negate else "asc",
            join_key=ApiOmitted.from_optional(spec.join_key),
        )

    @classmethod
    def to_internal_list(cls, values: Iterable[Self] | ApiOmitted) -> list[SorterSpec]:
        if isinstance(values, ApiOmitted):
            return []
        return [value.to_internal() for value in values]

    def to_internal(self) -> SorterSpec:
        return SorterSpec(
            sorter=(
                # NOTE: the parameters are different for each sorter, and the typed dict is incomplete
                (self.sorter_name, self.parameters) if self.parameters else self.sorter_name  # type: ignore[arg-type]
            ),
            negate=self.direction == "desc",
            join_key=ApiOmitted.to_optional(self.join_key),
        )


@api_model
class ApiInventoryJoinMacro:
    column_name: str = api_field(description="The name of the column.")
    macro_name: str = api_field(description="The name of the macro.")

    @classmethod
    def from_internal(cls, spec: InventoryJoinMacrosSpec | None) -> list[Self] | ApiOmitted:
        if spec is None:
            return ApiOmitted()

        return [cls(column_name=column, macro_name=macro) for column, macro in spec["macros"]]

    @classmethod
    def to_internal(cls, values: Iterable[Self] | ApiOmitted) -> InventoryJoinMacrosSpec | None:
        if isinstance(values, ApiOmitted):
            return None

        return InventoryJoinMacrosSpec(
            macros=[(value.column_name, value.macro_name) for value in values]
        )


@api_model
class EmbeddedViewContent(BaseWidgetContent):
    # NOTE: this is called "view" internally, that name must be used in `to_internal`
    type: Literal["embedded_view"] = api_field(
        description="Display a view which is fully defined within the dashboard.",
    )
    restricted_to_single: list[AnnotatedInfoName] = api_field(
        description="This view is restricted to a single entity per info object, e.g. a single host or service."
    )
    datasource: Annotated[str, AfterValidator(RegistryConverter(data_source_registry).validate)] = (
        api_field(description="The data source name.")
    )
    layout: Annotated[str, AfterValidator(RegistryConverter(layout_registry).validate)] = api_field(
        description="The layout name."
    )
    columns: list[ApiAnyColumnSpec] = api_field(description="The columns for this view.")
    grouping_columns: list[ApiColumnSpec] | ApiOmitted = api_field(
        description="Columns that values should be grouped by.",
        default_factory=ApiOmitted,
    )
    sorters: list[ApiSorterSpec] | ApiOmitted = api_field(
        description="Sorters for this view.",
        default_factory=ApiOmitted,
    )
    inventory_join_macros: list[ApiInventoryJoinMacro] | ApiOmitted = api_field(
        description="Macros to join inventory data with this view.",
        default_factory=ApiOmitted,
    )
    reload_interval_seconds: Annotated[int, Ge(0)] = api_field(
        description="Reload interval in seconds. 0 means no reload."
    )
    entries_per_row: Annotated[int, Ge(1)] = api_field(description="Number of entries per row.")
    column_headers: Literal["off", "pergroup", "repeat"] = api_field(
        description="How to display column headers.",
        # default="pergroup",
    )

    @classmethod
    @override
    def internal_type(cls) -> str:
        return "view"

    @classmethod
    def from_internal(cls, config: ViewDashletConfig | ViewSpec) -> Self:
        return cls(
            type="embedded_view",
            restricted_to_single=list(config.get("single_infos", [])),
            datasource=config["datasource"],
            layout=config["layout"],
            columns=[ApiColumnSpec.from_internal(column) for column in config["painters"]],
            grouping_columns=(
                [ApiColumnSpec.from_internal(column) for column in config["group_painters"]]
                if config["group_painters"]
                else ApiOmitted()
            ),
            sorters=ApiSorterSpec.from_internal_list(config["sorters"]),
            inventory_join_macros=ApiInventoryJoinMacro.from_internal(
                config.get("inventory_join_macros")
            ),
            reload_interval_seconds=config.get("browser_reload", 0),
            entries_per_row=config.get("num_columns", 1),
            column_headers=config.get("column_headers", "pergroup"),
        )

    def to_view_spec(self, owner: UserId, name: str) -> ViewSpec:
        # everything that doesn't use `self` doesn't matter for this page
        spec = ViewSpec(
            # visual
            owner=owner,
            name=name,
            context={},
            single_infos=self.restricted_to_single,
            add_context_to_title=False,
            title=name,
            description="",
            topic="",
            sort_index=99999,
            is_show_more=True,
            icon=None,
            hidden=False,
            hidebutton=False,
            public=False,
            packaged=False,
            link_from={},
            main_menu_search_terms=[],
            # view spec
            datasource=self.datasource,
            layout=self.layout,
            painters=[column.to_internal() for column in self.columns],
            group_painters=(
                [column.to_internal() for column in self.grouping_columns]
                if isinstance(self.grouping_columns, list)
                else []
            ),
            sorters=ApiSorterSpec.to_internal_list(self.sorters),
            browser_reload=self.reload_interval_seconds,
            num_columns=self.entries_per_row,
            column_headers=self.column_headers,
        )
        if inventory_join_macros := ApiInventoryJoinMacro.to_internal(self.inventory_join_macros):
            spec["inventory_join_macros"] = inventory_join_macros
        return spec

    @override
    def to_internal(self) -> ViewDashletConfig:
        spec = ViewDashletConfig(
            type=self.internal_type(),
            name="embedded_view_dummy_name",  # TODO: cleanup ViewDashletConfig
            single_infos=self.restricted_to_single,
            context={},
            datasource=self.datasource,
            layout=self.layout,
            painters=[column.to_internal() for column in self.columns],
            group_painters=(
                [column.to_internal() for column in self.grouping_columns]
                if isinstance(self.grouping_columns, list)
                else []
            ),
            sorters=ApiSorterSpec.to_internal_list(self.sorters),
            browser_reload=self.reload_interval_seconds,
            num_columns=self.entries_per_row,
            column_headers=self.column_headers,
            add_context_to_title=False,
            is_show_more=True,
            sort_index=99999,
        )
        if inventory_join_macros := ApiInventoryJoinMacro.to_internal(self.inventory_join_macros):
            spec["inventory_join_macros"] = inventory_join_macros
        return spec
