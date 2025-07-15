#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import json
import urllib.parse
from collections.abc import Callable, Iterable, Sequence
from typing import Any, Generic, Literal, TypeVar

from cmk.ccc.user import UserId

from cmk.utils.macros import MacroMapping, replace_macros_in_str

from cmk.gui import visuals
from cmk.gui.config import active_config, default_authorized_builtin_role_ids
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.type_defs import HTTPVariables, RoleName, SingleInfos, VisualContext
from cmk.gui.utils.html import HTML
from cmk.gui.utils.rendering import text_with_links_to_user_translated_html
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.valuespec import DictionaryEntry, ValueSpec, ValueSpecValidateFunc

from ..title_macros import macro_mapping_from_context
from ..type_defs import (
    DashboardConfig,
    DashboardName,
    DashletConfig,
    DashletId,
    DashletPosition,
    DashletRefreshAction,
    DashletRefreshInterval,
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
    def initial_refresh_interval(cls) -> DashletRefreshInterval:
        return False

    @classmethod
    def vs_parameters(
        cls,
    ) -> (
        None
        | list[DictionaryEntry]
        | ValueSpec
        | tuple[Callable[[T], None], Callable[[DashletId, T, T], T]]
    ):
        """Returns a valuespec instance in case the dashlet has parameters, otherwise None"""
        # For legacy reasons this may also return a list of Dashboard() elements. (TODO: Clean this up)
        return None

    @classmethod
    def opt_parameters(cls) -> bool | list[str]:
        """List of optional parameters in case vs_parameters() returns a list"""
        return False

    @classmethod
    def validate_parameters_func(cls) -> ValueSpecValidateFunc[Any] | None:
        """Optional validation function in case vs_parameters() returns a list"""
        return None

    @classmethod
    def styles(cls) -> str | None:
        """Optional registration of snapin type specific stylesheets"""
        return None

    @classmethod
    def script(cls) -> str | None:
        """Optional registration of snapin type specific javascript"""
        return None

    @classmethod
    def allowed_roles(cls) -> list[RoleName]:
        return default_authorized_builtin_role_ids

    @classmethod
    def add_url(cls) -> str:
        """The URL to open for adding a new dashlet of this type to a dashboard"""
        return makeuri(
            request,
            [("type", cls.type_name()), ("back", makeuri(request, [("edit", "1")]))],
            filename="edit_dashlet.py",
        )

    @classmethod
    def default_settings(cls):
        """Overwrite specific default settings for dashlets by returning a dict
            return { key: default_value, ... }
        e.g. to have a dashlet default to not showing its title
            return { "show_title": False }
        """
        return {}

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

    def _get_macro_mapping(self, title: str) -> MacroMapping:
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

    def on_resize(self) -> str | None:
        """Returns either Javascript code to execute when a resize event occurs or None"""
        return None

    def on_refresh(self) -> str | None:
        """Returns either Javascript code to execute when a the dashlet should be refreshed or None"""
        return None

    def update(self) -> None:
        """Called by the ajax call to update dashlet contents

        This is normally equivalent to the .show() method. Differs only for
        iframe and single metric dashlets.
        """
        self.show()

    @abc.abstractmethod
    def show(self) -> None:
        """Produces the HTML code of the dashlet content."""
        raise NotImplementedError()

    def _add_context_vars_to_url(self, url: str) -> str:
        """Adds missing context variables to the given URL"""
        if not self.has_context():
            return url

        context_vars = {k: str(v) for k, v in self._dashlet_context_vars() if v is not None}  #

        # This is a long distance hack to be able to rebuild the variables on the dashlet _get_context
        # using the visuals.VisualFilterListWithAddPopup.from_html_vars, which
        # requires this flag.
        parts = urllib.parse.urlparse(url)
        url_vars = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
        url_vars.update(context_vars)

        new_qs = urllib.parse.urlencode(url_vars)
        return urllib.parse.urlunparse(tuple(parts[:4] + (new_qs,) + parts[5:]))

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

    def refresh_interval(self) -> DashletRefreshInterval:
        return self.initial_refresh_interval()

    def get_refresh_action(self) -> DashletRefreshAction:
        if not self.refresh_interval():
            return None

        url = self._get_refresh_url()
        try:
            if on_refresh := self.on_refresh():
                return f"(function() {{{on_refresh}}})"
            return f'"{self._add_context_vars_to_url(url)}"'  # url to dashboard_dashlet.py
        except Exception:
            # Ignore the exceptions in non debug mode, assuming the exception also occurs
            # while dashlet rendering, which is then shown in the dashlet itselfs.
            if active_config.debug:
                raise

        return None

    def _get_refresh_url(self) -> str:
        """Returns the URL to be used for loading the dashlet contents"""
        return makeuri_contextless(
            request,
            [
                ("name", self._dashboard_name),
                ("owner", self._dashboard_owner),
                ("id", self._dashlet_id),
                ("mtime", self._dashboard["mtime"]),
            ],
            filename="dashboard_dashlet.py",
        )

    @classmethod
    def get_additional_title_macros(cls) -> Iterable[str]:
        yield from []


class IFrameDashlet(Dashlet[T], abc.ABC):
    """Base class for all dashlet using an iframe"""

    @classmethod
    def is_iframe_dashlet(cls) -> bool:
        """Whether or not the dashlet is rendered in an iframe"""
        return True

    def show(self) -> None:
        self._show_initial_iframe_container()

    def reload_on_resize(self) -> bool:
        """Whether or not the page should be reloaded when the dashlet is resized"""
        try:
            return self._dashlet_spec["reload_on_resize"]
        except KeyError:
            return False

    def _show_initial_iframe_container(self) -> None:
        iframe_url = self._get_iframe_url()
        if not iframe_url:
            return

        # Fix of iPad >:-P
        html.open_div(style="width: 100%; height: 100%; -webkit-overflow-scrolling:touch;")
        html.iframe(
            "",
            src="about:blank" if self.reload_on_resize() else iframe_url,
            id_="dashlet_iframe_%d" % self._dashlet_id,
            allowTransparency="true",
            frameborder="0",
            width="100%",
            height="100%",
        )
        html.close_div()

        if self.reload_on_resize():
            html.javascript(
                f"cmk.dashboard.set_reload_on_resize({json.dumps(self._dashlet_id)}, {json.dumps(iframe_url)});"
            )

    def _get_iframe_url(self) -> str | None:
        if not self.is_iframe_dashlet():
            return None

        return self._add_context_vars_to_url(self._get_refresh_url())

    @abc.abstractmethod
    def update(self) -> None:
        raise NotImplementedError()
