#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import abc
from collections.abc import Iterable, Mapping, Sequence
from typing import Generic, TypeVar

from cmk.gui import visuals
from cmk.gui.type_defs import SingleInfos, VisualContext

from ..title_macros import macro_mapping_from_context
from ..type_defs import (
    DashletConfig,
    DashletPosition,
    DashletSize,
)

T = TypeVar("T", bound=DashletConfig)


class Dashlet(abc.ABC, Generic[T]):
    """Base class for all dashboard dashlet implementations"""

    # Minimum width and height of dashlets in raster units
    minimum_size: DashletSize = (12, 12)

    @classmethod
    @abc.abstractmethod
    def type_name(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def title(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def description(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def sort_index(cls) -> int:
        raise NotImplementedError()

    @classmethod
    def has_context(cls) -> bool:
        """Whether or not this dashlet is context sensitive."""
        return False

    @classmethod
    def single_infos(cls) -> SingleInfos:
        """Return a list of the single infos (for the visual context) of this dashlet"""
        return []

    @classmethod
    def ignored_context_choices(cls) -> Sequence[str]:
        """Return a sequence of strings that should be ignored in the context filter dropdown"""
        return ()

    @classmethod
    def is_selectable(cls) -> bool:
        """Whether or not the user can choose to add this dashlet in the dashboard editor"""
        return True

    @classmethod
    def is_resizable(cls) -> bool:
        """Whether or not the user may resize this dashlet"""
        return True

    @classmethod
    def initial_size(cls) -> DashletSize:
        """The initial size of dashlets when being added to the dashboard"""
        return cls.minimum_size

    @classmethod
    def initial_position(cls) -> DashletPosition:
        """The initial position of dashlets when being added to the dashboard"""
        return (1, 1)

    def __init__(
        self,
        dashlet: T,
        base_context: VisualContext | None = None,
    ) -> None:
        super().__init__()
        self._dashlet_spec = dashlet
        self._context: VisualContext | None = self._get_context(base_context)

    def infos(self) -> SingleInfos:
        """Return a list of the supported infos (for the visual context) of this dashlet"""
        return []

    def _get_context(self, base_context: VisualContext | None) -> VisualContext | None:
        if not self.has_context():
            return None

        return visuals.get_merged_context(
            base_context or {},
            self._dashlet_spec["context"] if "context" in self._dashlet_spec else {},
        )

    @property
    def context(self) -> VisualContext:
        if self._context is None:
            raise Exception("Missing context")
        return self._context

    @property
    def dashlet_spec(self) -> T:
        return self._dashlet_spec

    def default_display_title(self) -> str:
        return self.title()

    def _get_macro_mapping(self, title: str) -> Mapping[str, str]:
        return macro_mapping_from_context(
            self.context if self.has_context() else {},
            self.single_infos(),
            title,
            self.default_display_title(),
        )

    @classmethod
    def get_additional_title_macros(cls) -> Iterable[str]:
        yield from []


class IFrameDashlet(Dashlet[T], abc.ABC):
    """Base class for all dashlet using an iframe"""
