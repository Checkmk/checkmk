#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import abc
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Generic, Self, TypeVar

from cmk.gui import visuals
from cmk.gui.i18n import _u
from cmk.gui.type_defs import SingleInfos, VisualContext
from cmk.utils.macros import replace_macros_in_str

from ..title_macros import macro_mapping_from_context
from ..type_defs import DashletConfig, ResponsiveGridBreakpoint


@dataclass(frozen=True, kw_only=True, slots=True)
class WidgetPositon:
    x: int
    y: int


@dataclass(frozen=True, kw_only=True, slots=True)
class WidgetSize:
    width: int
    height: int

    def to_tuple(self) -> tuple[int, int]:
        return self.width, self.height


@dataclass(frozen=True, kw_only=True, slots=True)
class RelativeLayoutConstraints:
    initial_position: WidgetPositon = field(default_factory=lambda: WidgetPositon(x=1, y=1))
    initial_size: WidgetSize = field(default_factory=lambda: WidgetSize(width=12, height=12))
    minimum_size: WidgetSize = field(default_factory=lambda: WidgetSize(width=12, height=12))
    is_resizable: bool = True


@dataclass(frozen=True, kw_only=True, slots=True)
class ResponsiveLayoutBreakpointConstraints:
    initial_size: WidgetSize
    minimum_size: WidgetSize


@dataclass(frozen=True, kw_only=True, slots=True)
class ResponsiveLayoutConstraints:
    XS: ResponsiveLayoutBreakpointConstraints = field(
        default_factory=lambda: ResponsiveLayoutBreakpointConstraints(
            minimum_size=WidgetSize(width=4, height=8),
            initial_size=WidgetSize(width=4, height=8),
        )
    )
    S: ResponsiveLayoutBreakpointConstraints = field(
        default_factory=lambda: ResponsiveLayoutBreakpointConstraints(
            minimum_size=WidgetSize(width=4, height=8),
            initial_size=WidgetSize(width=4, height=8),
        )
    )
    M: ResponsiveLayoutBreakpointConstraints = field(
        default_factory=lambda: ResponsiveLayoutBreakpointConstraints(
            minimum_size=WidgetSize(width=4, height=8),
            initial_size=WidgetSize(width=6, height=8),
        )
    )
    L: ResponsiveLayoutBreakpointConstraints = field(
        default_factory=lambda: ResponsiveLayoutBreakpointConstraints(
            minimum_size=WidgetSize(width=3, height=8),
            initial_size=WidgetSize(width=4, height=8),
        )
    )
    XL: ResponsiveLayoutBreakpointConstraints = field(
        default_factory=lambda: ResponsiveLayoutBreakpointConstraints(
            minimum_size=WidgetSize(width=3, height=8),
            initial_size=WidgetSize(width=6, height=8),
        )
    )

    @classmethod
    def large_default(cls) -> Self:
        """Larger default size for widgets that need more space."""
        return cls(
            S=ResponsiveLayoutBreakpointConstraints(
                minimum_size=WidgetSize(width=4, height=8),
                initial_size=WidgetSize(width=8, height=8),
            ),
        )

    def to_dict(self) -> dict[ResponsiveGridBreakpoint, ResponsiveLayoutBreakpointConstraints]:
        return {
            "XS": self.XS,
            "S": self.S,
            "M": self.M,
            "L": self.L,
            "XL": self.XL,
        }


T = TypeVar("T", bound=DashletConfig)


class Dashlet(abc.ABC, Generic[T]):
    """Base class for all dashboard dashlet implementations"""

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
    def relative_layout_constraints(cls) -> RelativeLayoutConstraints:
        return RelativeLayoutConstraints()

    @classmethod
    def responsive_layout_constraints(cls) -> ResponsiveLayoutConstraints:
        return ResponsiveLayoutConstraints()

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
            **self._get_additional_macros(),
        )

    def _get_additional_macros(self) -> Mapping[str, str]:
        return {}

    @classmethod
    def get_additional_macro_names(cls) -> Iterable[str]:
        yield from []

    def compute_title(self) -> str:
        try:
            raw_title = self._dashlet_spec["title"]
        except KeyError:
            raw_title = self.default_display_title()

        untranslated_title = replace_macros_in_str(
            raw_title,
            self._get_macro_mapping(raw_title),
        )
        return _u(untranslated_title)


class IFrameDashlet(Dashlet[T], abc.ABC):
    """Base class for all dashlet using an iframe"""
