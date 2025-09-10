#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from abc import ABC, abstractmethod
from collections.abc import Container, Iterable
from typing import Self

from pydantic import model_validator
from pydantic_core import ErrorDetails

from cmk.gui.dashboard import dashlet_registry, DashletConfig
from cmk.gui.openapi.framework import ApiContext
from cmk.gui.openapi.framework.model import api_model


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
        pass

    def iter_validation_errors(
        self,
        location: tuple[str | int, ...],
        context: ApiContext,
        *,
        embedded_views: Container[str],
    ) -> Iterable[ErrorDetails]:
        """Run additional validation based on the config.

        Specifically, this should be used when they validation requires access to the active config
        or the existing dashboard configuration (embedded views). The `location` parameter describes
        the location up to this widget. The errors should include the exact location of the
        erroneous data in the `loc` of the `ErrorDetails`.
        """
        return []
