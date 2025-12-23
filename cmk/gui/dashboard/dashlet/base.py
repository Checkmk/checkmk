#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import abc
from collections.abc import Iterable, Mapping, Sequence
from typing import Generic, Literal, TypeVar

from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.config import default_authorized_builtin_role_ids
from cmk.gui.type_defs import HTTPVariables, RoleName, SingleInfos, VisualContext
from cmk.gui.utils.html import HTML
from cmk.gui.utils.rendering import text_with_links_to_user_translated_html
from cmk.utils.macros import replace_macros_in_str

from ..title_macros import macro_mapping_from_context
from ..type_defs import (
    DashboardConfig,
    DashboardName,
    DashletConfig,
    DashletId,
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
    def is_iframe_dashlet(cls) -> bool:
        """Whether or not the dashlet is rendered in an iframe"""
        return False

    @classmethod
    def initial_size(cls) -> DashletSize:
        """The initial size of dashlets when being added to the dashboard"""
        return cls.minimum_size

    @classmethod
    def initial_position(cls) -> DashletPosition:
        """The initial position of dashlets when being added to the dashboard"""
        return (1, 1)

    @classmethod
    def allowed_roles(cls) -> list[RoleName]:
        return default_authorized_builtin_role_ids

    def __init__(
        self,
        dashboard_name: DashboardName,
        dashboard_owner: UserId,
        dashboard: DashboardConfig,
        dashlet_id: DashletId,
        dashlet: T,
    ) -> None:
        super().__init__()
        self._dashboard_name = dashboard_name
        self._dashboard_owner = dashboard_owner
        self._dashboard = dashboard
        self._dashlet_id = dashlet_id
        self._dashlet_spec = dashlet
        self._context: VisualContext | None = self._get_context()

    def infos(self) -> SingleInfos:
        """Return a list of the supported infos (for the visual context) of this dashlet"""
        return []

    def _get_context(self) -> VisualContext | None:
        if not self.has_context():
            return None

        return visuals.get_merged_context(
            self._dashboard["context"],
            self._dashlet_spec["context"],
        )

    @property
    def context(self) -> VisualContext:
        if self._context is None:
            raise Exception("Missing context")
        return self._context

    @property
    def dashlet_id(self) -> DashletId:
        return self._dashlet_id

    @property
    def dashlet_spec(self) -> T:
        return self._dashlet_spec

    @property
    def dashboard_name(self) -> str:
        return self._dashboard_name

    @property
    def dashboard_owner(self) -> UserId:
        return self._dashboard_owner

    def default_display_title(self) -> str:
        return self.title()

    def display_title(self) -> str:
        try:
            return self._dashlet_spec["title"]
        except KeyError:
            return self.default_display_title()

    def _get_macro_mapping(self, title: str) -> Mapping[str, str]:
        return macro_mapping_from_context(
            self.context if self.has_context() else {},
            self.single_infos(),
            title,
            self.default_display_title(),
        )

    def render_title_html(self) -> HTML:
        title = self.display_title()
        return text_with_links_to_user_translated_html(
            [
                (
                    replace_macros_in_str(
                        title,
                        self._get_macro_mapping(title),
                    ),
                    self.title_url(),
                ),
            ],
        )

    def show_title(self) -> bool | Literal["transparent"]:
        try:
            return self._dashlet_spec["show_title"]
        except KeyError:
            return True

    def title_url(self) -> str | None:
        try:
            return self._dashlet_spec["title_url"]
        except KeyError:
            return None

    def show_background(self) -> bool:
        try:
            return self._dashlet_spec["background"]
        except KeyError:
            return True

    def _dashlet_context_vars(self) -> HTTPVariables:
        return visuals.context_to_uri_vars(self.context)

    def unconfigured_single_infos(self) -> set[str]:
        """Returns infos that are not set by the dashlet config"""
        if not self.has_context():
            return set()
        return visuals.get_missing_single_infos(self.single_infos(), self._dashlet_spec["context"])

    def missing_single_infos(self) -> set[str]:
        """Returns infos that are neither configured nor available through HTTP variables"""
        if not self.has_context():
            return set()
        return visuals.get_missing_single_infos(self.single_infos(), self.context)

    def size(self) -> DashletSize:
        if self.is_resizable():
            try:
                return self._dashlet_spec["size"]
            except KeyError:
                return self.initial_size()
        return self.initial_size()

    def position(self) -> DashletPosition:
        try:
            return self._dashlet_spec["position"]
        except KeyError:
            return self.initial_position()

    @classmethod
    def get_additional_title_macros(cls) -> Iterable[str]:
        yield from []


class IFrameDashlet(Dashlet[T], abc.ABC):
    """Base class for all dashlet using an iframe"""

    @classmethod
    def is_iframe_dashlet(cls) -> bool:
        """Whether or not the dashlet is rendered in an iframe"""
        return True

    def reload_on_resize(self) -> bool:
        """Whether or not the page should be reloaded when the dashlet is resized"""
        try:
            return self._dashlet_spec["reload_on_resize"]
        except KeyError:
            return False
