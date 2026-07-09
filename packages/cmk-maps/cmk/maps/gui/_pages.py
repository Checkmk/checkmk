#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""GUI endpoints backing the Checkmk Maps SPA.

Maps ships as the ``cmk-maps`` web component inside the shared cmk-frontend-vue
bundle (loaded by ``make_header``); this page mounts it and provides the
session-authenticated ticket handshake the daemon needs — a signed ticket plus
the caller's resolved capabilities for show/hide decisions in the UI.
"""

from typing import NotRequired, override, TypedDict

from cmk.gui.breadcrumb import Breadcrumb, make_simple_page_breadcrumb
from cmk.gui.config import active_config
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.page_menu import (
    make_javascript_link,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import AjaxPage, Page, PageContext, PageResult
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import VisualPublic
from cmk.gui.utils.roles import is_user_with_publish_permissions, UserPermissions
from cmk.maps.gui._images import seed_builtin_images
from cmk.maps.gui._settings import tile_csp_sources
from cmk.maps.gui._settings_modes import ModeMapsAuthoringSettings, ModeMapsDaemonSettings
from cmk.maps.gui._tickets import (
    _publishable_contact_groups,
    _publishable_sites,
    gather_capabilities,
    mint_stream_ticket,
    mint_ticket,
)
from cmk.maps.gui.store import get_permitted_map
from cmk.maps.shared.ticket import MapClaim, TicketCapabilities
from cmk.web.utils.icons import DynamicIconName


class TicketResponse(TypedDict):
    """The ticket handshake payload, served by ``AjaxMapsTicket``."""

    ticket: str
    user_id: str
    language: str | None
    capabilities: TicketCapabilities
    # Only present once a map is open: the SSE stream is per-map.
    stream_token: NotRequired[str]


def _ticket_response(request: Request) -> TicketResponse:
    """Mint the daemon ticket + resolved capabilities for the Maps SPA.

    The SPA's first call on boot, and the same endpoint it re-mints from for the
    periodic refresh and map-scope changes. Capabilities are resolved once here
    and baked into the ticket, so the SPA and the daemon see the same set.

    Map-scoped ticket: on ``maps.py?name=<map>`` the ticket is bound to the
    map's REAL owner (resolved via the permission model, never a client value) so
    the daemon can key its shared broadcast loop by the map's true (owner, name).
    Unknown/forbidden names fall through to an unbound ticket.
    """
    caps = gather_capabilities(user)
    map_claim: MapClaim | None = None
    name = request.get_ascii_input("name")
    if name is not None and (page := get_permitted_map(name)) is not None:
        map_claim = MapClaim(owner=str(page.config.owner), name=name)
    response = TicketResponse(
        ticket=mint_ticket(user, caps=caps, map_claim=map_claim),
        user_id=str(user.ident),
        language=user.language,
        capabilities=caps,
    )
    # The SSE stream token travels in the URL, so it is minted separately with a
    # reduced cap set and its own audience (useless on the REST API). It is always
    # map-scoped — the stream is per-map — so it exists only once a map is
    # opened; the map-list / global phase runs no SSE and needs none.
    if map_claim is not None:
        response["stream_token"] = mint_stream_ticket(user, map_claim=map_claim)
    return response


def _home_page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    """Page menu for the Maps home listing.

    The list-affecting controls live in the Checkmk chrome (like the dashboards
    list), not in the SPA toolbar. ``Add map`` and the card/table switch act on
    the mounted SPA via the ``window._cmkMapsHome`` bridge it registers on mount;
    ``Images`` is a plain navigation the SPA resolves from ``?mode=icons``. The
    switch mirrors the inline-help toggle: it sits in "Display", its title names
    the view it leads to and its ``toggle_on/off`` icon carries the current one,
    flipped client side because the SPA is what persists the view.

    Creating a map, importing one and switching the list view are the suggested
    actions; the image library and the two settings views are not, so they stay
    in their dropdown.
    """
    maps_entries: list[PageMenuEntry] = []
    if user.may("general.edit_map"):
        maps_entries.append(
            PageMenuEntry(
                title=_("Add map"),
                icon_name=DynamicIconName("new"),
                item=make_javascript_link("window._cmkMapsHome && window._cmkMapsHome.newMap()"),
                is_shortcut=True,
                is_suggested=True,
                name="maps_new",
            )
        )
        maps_entries.append(
            PageMenuEntry(
                title=_("Import"),
                icon_name=DynamicIconName("insert"),
                item=make_javascript_link("window._cmkMapsHome && window._cmkMapsHome.importMap()"),
                is_shortcut=True,
                is_suggested=True,
                name="maps_import",
            )
        )
    if user.may("maps.configure"):
        maps_entries.append(
            PageMenuEntry(
                title=_("Images"),
                icon_name=DynamicIconName("upload"),
                item=make_simple_link("maps.py?mode=icons"),
                name="maps_images",
            )
        )
        # The Maps globals also live in Setup → Global settings; these shortcuts
        # bring the two curated views right next to the module (the DCD pattern).
        maps_entries.append(
            PageMenuEntry(
                title=_("Map & object defaults"),
                icon_name=DynamicIconName("painteroptions"),
                item=make_simple_link(ModeMapsAuthoringSettings.mode_url()),
                name="maps_authoring_settings",
            )
        )
        maps_entries.append(
            PageMenuEntry(
                title=_("Connections & daemon"),
                icon_name=DynamicIconName("configuration"),
                item=make_simple_link(ModeMapsDaemonSettings.mode_url()),
                name="maps_daemon_settings",
            )
        )
    menu = PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name="maps",
                title=_("Maps"),
                topics=[PageMenuTopic(title=_("Maps"), entries=maps_entries)],
            ),
        ],
        breadcrumb=breadcrumb,
    )
    # ``PageMenu`` always adds the standard "Display" dropdown; extend it with the
    # card/table switch instead of declaring a second (colliding) one.
    menu["display"].topics.append(
        PageMenuTopic(
            title=_("View"),
            entries=[
                PageMenuEntry(
                    title=_("Table view"),
                    icon_name=DynamicIconName("toggle_off"),
                    item=make_javascript_link(
                        "window._cmkMapsHome && window._cmkMapsHome.toggleView()"
                    ),
                    is_shortcut=True,
                    is_suggested=True,
                    name="maps_view_toggle",
                ),
            ],
        )
    )
    return menu


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
        # A direct map/admin entry (``?name=<map>`` / ``?mode=<tab>``, mirroring
        # the SPA's own URL parsing) opens a view that hides the native heading +
        # page menu. Those ship unconditionally (the home listing needs them and
        # the client-routed SPA can't re-render server chrome), so set the matching
        # body class up front: a render-blocking CSS rule (MapsApp.vue) then hides
        # the chrome before the first paint instead of it flashing until the SPA
        # bundle mounts and toggles it. The home listing keeps the class off.
        name = ctx.request.get_ascii_input("name")
        initial_home = name is None and not ctx.request.has_var("mode")
        if not chromeless and not initial_home:
            html.add_body_css_class("maps-app--embedded")
        breadcrumb = (
            Breadcrumb()
            if chromeless
            else make_simple_page_breadcrumb(main_menu_registry.menu_customize(), _("Maps"))
        )
        make_header(
            html,
            title=_("Maps"),
            breadcrumb=breadcrumb,
            page_menu=None if chromeless else _home_page_menu(breadcrumb),
            show_top_heading=not chromeless,
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
        # No props: the SPA fetches everything it needs (the ticket from
        # AjaxMapsTicket, the map and the listing from the Maps REST API, the
        # authoring defaults from the internal settings endpoint). Hydrating any
        # of it would be a second data-assembly path to keep in step with those,
        # and its optionality would reach every consumer of the values. It also
        # turns a forbidden or unknown ``?name=`` into a plain REST 403/404 the
        # SPA can render, rather than a silently absent prop.
        html.open_div(id_="app")
        html.vue_component("cmk-maps", data={})
        html.close_div()
        html.close_div()
        html.footer()
        return None


class AjaxMapsTicket(AjaxPage):
    """Mint a short-lived signed ticket for the Maps backend daemon.

    The SPA calls this on boot and then again for the periodic refresh and on
    map-scope changes (``?name=<map>``).
    """

    @override
    def page(self, ctx: PageContext) -> PageResult:
        user.need_permission("maps.use")
        return _ticket_response(ctx.request)


def _authorized_public(requested: object) -> VisualPublic:
    """Clamp a requested map visibility to what the user may publish.

    Same overall gate the pagetype edit page uses: no publish permission →
    private regardless of what was submitted. Beyond that,
    the requested scope is server-side re-validated against exactly the groups /
    sites the user may publish to (mirroring the valuespec's ``with_foreign_groups``
    restriction), so a client cannot publish to a contact group it isn't in or to
    sites it isn't authorized for by crafting the request.
    """
    user_permissions = UserPermissions.from_config(active_config, permission_registry)
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
