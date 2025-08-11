#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from abc import ABC, abstractmethod
from typing import Self

from pydantic import model_validator

from cmk.gui.dashboard import dashlet_registry, DashletConfig
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
