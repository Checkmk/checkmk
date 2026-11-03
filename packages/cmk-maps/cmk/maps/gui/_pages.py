#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The GUI page that mounts the Checkmk Maps SPA.

Maps ships as the ``cmk-maps`` web component inside the shared cmk-frontend-vue
bundle (loaded by ``make_header``); this page mounts it. Everything the SPA then
calls is a REST endpoint — map CRUD the official ``cmk.maps.rest_api``, the
ticket handshake and the rest the internal family in
``cmk.maps.rest_api.internal``.
"""

from dataclasses import asdict
from pathlib import Path
from typing import override

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.user import UserId
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.monitor.command import (
    acknowledge_defaults,
    acknowledge_presets_url,
    downtime_presets,
    downtime_presets_url,
    downtime_recurrences,
    notification_rules_url,
)
from cmk.gui.page_menu import PageMenu
from cmk.gui.pages import Page, PageContext, PageResult
from cmk.gui.permissions import all_permissions
from cmk.gui.type_defs import VisualPublic
from cmk.gui.utils.roles import is_user_with_publish_permissions, UserPermissions
from cmk.maps.gui._images import seed_builtin_images
from cmk.maps.gui._page_menu import (
    images_breadcrumb,
    images_page_menu,
    map_list_page_menu,
    maps_breadcrumb,
    PAGE_MENU_EVENT,
)
from cmk.maps.gui._settings import map_object_defaults, MapListView, tile_csp_sources
from cmk.maps.gui._settings_page import SETTINGS_URL
from cmk.maps.gui._tickets import _publishable_contact_groups, _publishable_sites
from cmk.maps.gui.pagetype import MapPage
from cmk.maps.gui.store import get_permitted_map
from cmk.shared_typing.maps import (
    AcknowledgeDefaults,
    DowntimePreset,
    DowntimeRecurrence,
    DowntimeUntilKeyword,
    MapListLayout,
    MapsApp,
    MapsCommandSettings,
)
from cmk.web.utils.escaping import escape


class ShowMapsPage(Page):
    """Render the Checkmk chrome and mount the Maps SPA inline (no iframe).

    Maps is the ``cmk-maps`` web component in the shared cmk-frontend-vue bundle,
    which ``make_header`` already loads (``load_frontend_vue``). The current view
    travels in the page query string (``maps.py?name=<map>``,
    ``maps.py?mode=<admin-tab>``) and is read by the SPA via the History API (no
    hash, no reload), mirroring the Dashboard page.
    """

    @override
    def page(self, ctx: PageContext) -> PageResult:
        user.need_permission("maps.use")
        shown = _shown_map(ctx)
        # Geo maps let the browser fetch tiles straight from the tile server, so
        # this policy is what decides which ones it may reach — the SPA's default
        # host plus whatever the site has configured. Widened for this page
        # instead of site-wide.
        for tile_source in tile_csp_sources():
            response.add_csp_source("img-src", tile_source)
        # Ensure the built-in icons are present in the Apache-served images dir
        # before the SPA renders any map (non-destructive; cheap after first run).
        seed_builtin_images()
        # Preview (settings live-preview iframe) and kiosk (NOC wall) render the
        # map chromeless: no Checkmk main navigation, just the SPA.
        chromeless = ctx.request.has_var("preview") or ctx.request.has_var("kiosk")
        # The map list and the image library are Checkmk pages with their
        # heading and page menu. A map renders its own title bar over the
        # canvas, so it gets neither. The SPA loads the other page when it
        # switches between them, so the server chrome always belongs to what is
        # shown.
        layout = _list_layout(ctx)
        title, breadcrumb, page_menu = _chrome(ctx, shown, layout)
        make_header(
            html,
            title=title,
            breadcrumb=breadcrumb,
            page_menu=page_menu,
            show_top_heading=page_menu is not None,
            show_main_navigation=not chromeless,
            enable_main_page_scrollbar=False,
            debug=ctx.config.debug,
            lang=user.language,
            inject_js_profiling_code=ctx.config.inject_js_profiling_code,
            load_frontend_vue=ctx.config.load_frontend_vue,
            custom_style_sheet=ctx.config.custom_style_sheet,
            screenshotmode=ctx.config.screenshotmode,
            inline_help_as_text=user.inline_help_as_text,
            hide_suggestions=not user.get_tree_state("suggestions", "all", True),
            user_role_ids=user.role_ids,
        )
        # Mount inside ``#app``: that is where the SPA's overlays teleport to.
        # One ``.maps-app--embed`` wrapper keeps
        # ``#main_page_content.vue-scrolling > *`` from stretching stray nodes
        # and pushing the mount point off-screen; the SPA fills the wrapper.
        html.open_div(class_="maps-app--embed")
        # Only what the page itself decides or the SPA cannot fetch goes in as a
        # prop; the SPA fetches everything it shows (the ticket, the map and the
        # listing, the authoring defaults). Hydrating any of that would be a
        # second data-assembly path to keep in step with those, and its
        # optionality would reach every consumer of the values.
        #
        # ``commands`` is what the SPA cannot fetch, as on the monitoring pages:
        # how the site has its acknowledge and downtime dialogs set up, which no
        # endpoint serves and the dialogs need before they open.
        #
        # ``list_layout`` is what the page decides: the page menu above is
        # rendered here and offers the layout not shown, so the list has to show
        # this one.
        #
        # ``page_menu_event`` is not data but wiring: the page menu above
        # dispatches it, and its name belongs to ``_page_menu``, not to a
        # TypeScript constant a rename would leave listening for nothing. The
        # monitoring pages hand out their export event the same way.
        html.open_div(id_="app")
        html.vue_component(
            "cmk-maps",
            data=asdict(
                MapsApp(
                    page_menu_event=PAGE_MENU_EVENT,
                    commands=_command_settings(ctx),
                    list_layout=MapListLayout(layout),
                )
            ),
        )
        html.close_div()
        html.close_div()
        html.footer()
        return None


def _command_settings(ctx: PageContext) -> MapsCommandSettings:
    ack = acknowledge_defaults(ctx.config)
    return MapsCommandSettings(
        acknowledge_defaults=AcknowledgeDefaults(
            sticky=ack.sticky,
            persistent=ack.persistent,
            notify=ack.notify,
            expire_seconds=ack.expire_seconds,
        ),
        acknowledge_presets_url=acknowledge_presets_url(ctx.config),
        notification_rules_url=notification_rules_url(ctx.config),
        # Repeating a downtime is the edition's to offer; an edition without it
        # offers none.
        downtime_recurrences=[
            DowntimeRecurrence(recur=recurrence.recur, title=recurrence.title)
            for recurrence in downtime_recurrences.offered()
        ],
        downtime_presets=[
            DowntimePreset(
                title=preset.title,
                end=(
                    preset.end if isinstance(preset.end, int) else DowntimeUntilKeyword(preset.end)
                ),
            )
            for preset in downtime_presets(ctx.config)
        ],
        downtime_presets_url=downtime_presets_url(ctx.config),
    )


def _require_visible_map(name: str) -> MapPage:
    """Answer an unknown map like an unknown view or dashboard.

    A map the user may not see reads the same as one that does not exist, so
    the page does not tell which names are taken.
    """
    if (page := get_permitted_map(name)) is None:
        raise MKUserError(
            "name",
            _("The requested map %(name)s does not exist") % {"name": escape(name)},
        )
    return page


def _list_layout(ctx: PageContext) -> MapListView:
    # Remembered per user: the ways back to the list (breadcrumbs, back links)
    # load a bare maps.py and would otherwise lose the layout last chosen.
    path = None if user.id is None else _list_layout_path(user.id)
    stored = (
        None if path is None else _as_list_layout(store.load_object_from_file(path, default=None))
    )
    if (requested := _as_list_layout(ctx.request.get_ascii_input("layout"))) is None:
        return stored or map_object_defaults()["map_list_view"]
    # The switch leaves ``layout`` in the URL, so a reload must not write again.
    if path is not None and requested != stored:
        store.save_object_to_file(path, requested)
    return requested


def _list_layout_path(user_id: UserId) -> Path:
    return cmk.utils.paths.profile_dir / user_id / "maps_list_layout.mk"


def _as_list_layout(value: object) -> MapListView | None:
    match value:
        case "cards":
            return "cards"
        case "table":
            return "table"
        case _:
            return None


def _chrome(
    ctx: PageContext, shown: MapPage | None, layout: MapListView
) -> tuple[str, Breadcrumb, PageMenu | None]:
    # The map's own title, so a tab or a history entry says which map it is.
    if shown is not None:
        return shown.title() or shown.name(), Breadcrumb(), None
    if _shows_images(ctx) and user.may("maps.configure"):
        breadcrumb = images_breadcrumb()
        return _("Images"), breadcrumb, images_page_menu(breadcrumb)
    breadcrumb = maps_breadcrumb()
    return (
        _("Maps"),
        breadcrumb,
        map_list_page_menu(user, breadcrumb, settings_url=SETTINGS_URL, layout=layout),
    )


def _shown_map(ctx: PageContext) -> MapPage | None:
    # The image library goes before a map name, and an empty name is the list,
    # as the SPA's router has it, so the chrome rendered here belongs to the
    # view the SPA shows.
    if _shows_images(ctx) or not (name := ctx.request.get_str_input("name")):
        return None
    return _require_visible_map(name)


def _shows_images(ctx: PageContext) -> bool:
    return ctx.request.get_ascii_input("mode") == "icons"


def _authorized_public(requested: object) -> VisualPublic:
    """Clamp a requested map visibility to what the user may publish.

    Same overall gate the pagetype edit page uses: no publish permission →
    private regardless of what was submitted. Beyond that,
    the requested scope is server-side re-validated against exactly the groups /
    sites the user may publish to (mirroring the valuespec's ``with_foreign_groups``
    restriction), so a client cannot publish to a contact group it isn't in or to
    sites it isn't authorized for by crafting the request.
    """
    user_permissions = UserPermissions.from_config(active_config, all_permissions())
    if not is_user_with_publish_permissions("pagetype", user.ident, "map", user_permissions):
        return False
    if requested is True:
        return user.may("general.publish_map")
    if (
        isinstance(requested, (list, tuple))
        and len(requested) == 2
        and requested[0] in ("contact_groups", "sites")
        and isinstance(requested[1], (list, tuple))
    ):
        scope = requested[0]
        names = [str(n) for n in requested[1]]
        if scope == "contact_groups":
            allowed = {g["id"] for g in _publishable_contact_groups(user)}
        else:
            allowed = {s["id"] for s in _publishable_sites(user)}
        permitted = [n for n in names if n in allowed]
        # Publishing to none of the allowed scopes is effectively private.
        if not permitted:
            return False
        return (scope, permitted)
    return False
