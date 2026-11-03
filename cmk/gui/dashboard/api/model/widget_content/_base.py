#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from typing import Literal, Self

from pydantic import model_validator
from pydantic_core import ErrorDetails

from cmk.gui.dashboard import dashlet_registry, DashletConfig
from cmk.gui.dashboard.type_defs import DashboardWindow, FixedWindow
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.framework.model import api_model
from cmk.gui.openapi.framework.model.common_fields import timerange_from_internal, TimerangeModel
from cmk.gui.type_defs import DashboardEmbeddedViewSpec

from ..contextual_link import (
    AnyContextualLinkSpec,
    contextual_link_options,
    ContextualLinkDefault,
    ContextualLinkOptions,
)


def time_range_from_internal(
    window: DashboardWindow | FixedWindow,
) -> Literal["dashboard"] | TimerangeModel:
    if window["type"] == "dashboard":
        return "dashboard"
    return timerange_from_internal(window["window"])


def time_range_to_internal(
    time_range: Literal["dashboard"] | TimerangeModel,
) -> DashboardWindow | FixedWindow:
    if time_range == "dashboard":
        return DashboardWindow(type="dashboard")
    return FixedWindow(type="range", window=time_range.to_internal())


@api_model
class BaseWidgetContent(ABC):
    @property
    @abstractmethod
    def type(self) -> str:
        pass

    @classmethod
    @abstractmethod
    def internal_type(cls) -> str:
        pass

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.internal_type() not in dashlet_registry:
            raise ValueError("Widget is not supported by this edition")
        return self

    @abstractmethod
    def to_internal(self) -> DashletConfig:
        """The internal config representation of the widget content.

        This will then be merged with the general widget config."""

    def configured_contextual_link(self) -> AnyContextualLinkSpec:
        """The link the widget configures; the default link for a widget without a link field."""
        return ContextualLinkDefault(type="default")

    @classmethod
    def contextual_link_options(cls) -> ContextualLinkOptions | None:
        """What a link of this widget may be; None for a widget that configures none."""
        field = cls.__dataclass_fields__.get("contextual_link")
        return None if field is None else contextual_link_options(field.type)

    def iter_validation_errors(
        self,
        location: tuple[str | int, ...],  # noqa: ARG002
        context: ApiContext,  # noqa: ARG002
        *,
        embedded_views: Mapping[str, DashboardEmbeddedViewSpec],  # noqa: ARG002
        stored_widget: DashletConfig | None,  # noqa: ARG002
    ) -> Iterable[ErrorDetails]:
        """Run additional validation based on the config.

        Specifically, this should be used when they validation requires access to the active config
        or the existing dashboard configuration (embedded views, the stored config of the widget
        with the same ID, None if there is none). The `location` parameter describes
        the location up to this widget. The errors should include the exact location of the
        erroneous data in the `loc` of the `ErrorDetails`.
        """
        return []
