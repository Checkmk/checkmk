#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Main-navigation configuration and rendering entry point.

Provides the :class:`MainNavigation` dataclass that bundles the values
:func:`cmk.gui.header.make_header` needs to emit the navigation strip and
sidebar around a page.

The actual rendering lives in :mod:`cmk.gui.sidebar` but this module does
**not** import sidebar — sidebar is heavy and pulls in
:mod:`cmk.gui.pages` (and from there :mod:`cmk.gui.crash_handler`,
:mod:`cmk.gui.pagetypes`, etc.), all of which are themselves callers of
``make_header(main_navigation=...)``. A direct module-level import would
create a transitive cycle.

Instead, :data:`main_navigation_renderer_registry` is populated once at
process startup by :mod:`cmk.gui.main_modules`, which is the wiring layer
that imports both sidebar and this module. :meth:`MainNavigation.render`
then dispatches via the registered callable.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from cmk.ccc.plugin_registry import Registry
from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.permissions import permission_registry
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import is_kiosk_request


@dataclass(frozen=True, kw_only=True)
class MainNavigation:
    """Bundle of values needed to render the main navigation + sidebar.

    Built once per request from :class:`Config` via
    :func:`MainNavigation.from_config` and passed to
    :func:`cmk.gui.header.make_header` as ``main_navigation=...``.
    """

    config: Config
    user_permissions: UserPermissions
    sidebar_config: Sequence[tuple[str, str]]
    start_url: str
    screenshot_mode: bool
    sidebar_notify_interval: int | None
    show_scrollbar: bool
    sidebar_update_interval: float
    kiosk: bool

    @staticmethod
    def render(config: Config, title: str | None) -> None:
        """Emit ``html_head``, ``<body>``, the main nav, sidebar, and open
        ``#content_area``.

        Pages reach this either via ``make_header(...)`` or directly (for
        the views, dashboards and SLA pages that build their own
        breadcrumb / top_heading). The matching close happens in
        :meth:`cmk.gui.htmllib.html.HTMLGenerator.body_end`.

        Skips silently for non-HTML output and for repeated calls in the
        same request, so direct callers don't have to mirror the guards
        ``make_header`` already applies.

        Raises :class:`RuntimeError` if no renderer has been registered —
        meaning :mod:`cmk.gui.main_modules` was not loaded before the first
        chrome-bearing :func:`make_header` call. WSGI processes load
        ``main_modules`` from ``wsgi_import.py`` before any request, so
        this is a programming error in test / standalone-script setups.
        """
        if html.output_format != "html" or html._header_sent:
            return
        try:
            renderer = main_navigation_renderer_registry[_RENDERER_KEY]
        except KeyError:
            raise RuntimeError(
                "No main_navigation renderer registered. Import "
                "cmk.gui.main_modules (or call its `register()` for an "
                "edition) before make_header(main_navigation=...)."
            ) from None
        renderer(title, MainNavigation.from_config(config=config))

    @staticmethod
    def from_config(config: Config) -> "MainNavigation":
        """Build a :class:`MainNavigation` from the active :class:`Config`.

        ``kiosk`` defaults to ``is_kiosk_request(request)`` so callers don't have
        to thread the ``?kiosk=`` query parameter through every ``make_header``
        callsite. Pass an explicit ``True``/``False`` to override.
        """
        return MainNavigation(
            config=config,
            user_permissions=UserPermissions.from_config(config, permission_registry),
            sidebar_config=config.sidebar,
            start_url=user.start_url or config.start_url,
            screenshot_mode=config.screenshotmode,
            sidebar_notify_interval=config.sidebar_notify_interval,
            show_scrollbar=config.sidebar_show_scrollbar,
            sidebar_update_interval=config.sidebar_update_interval,
            kiosk=is_kiosk_request(request),
        )


MainNavigationRenderer = Callable[[str | None, MainNavigation], None]

# The single key every renderer is stored under: this registry holds exactly
# one entry (see MainNavigationRendererRegistry), so the name is fixed rather
# than derived from the instance.
_RENDERER_KEY = "default"


class MainNavigationRendererRegistry(Registry[MainNavigationRenderer]):
    """Holds the function :meth:`MainNavigation.render` dispatches to.

    Despite being a name-keyed registry, only one renderer is active per
    process: every entry is stored under :data:`_RENDERER_KEY`, so calling
    :meth:`register` again replaces the previous renderer. The registry is the
    indirection that breaks the import cycle described in the module docstring;
    :mod:`cmk.gui.main_modules` populates it once at startup.
    """

    def plugin_name(self, instance: MainNavigationRenderer) -> str:
        return _RENDERER_KEY


main_navigation_renderer_registry = MainNavigationRendererRegistry()
