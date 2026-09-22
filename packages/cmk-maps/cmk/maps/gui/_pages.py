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

from dataclasses import asdict
from typing import NotRequired, override, TypedDict

from cmk.gui.breadcrumb import Breadcrumb, make_main_menu_breadcrumb
from cmk.gui.config import active_config
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
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
from cmk.shared_typing.maps import MapsApp, MapsBreadcrumbItem, MapsPageLinks


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
        # No heading and no page menu, like the dashboard page: the SPA routes
        # between the map list, a map and the image library client side, and
        # server chrome cannot follow that. So it renders its own title and the
        # actions over the list, and nothing here has to be hidden again once the
        # bundle mounts.
        make_header(
            html,
            title=_("Maps"),
            breadcrumb=Breadcrumb(),
            page_menu=None,
            show_top_heading=False,
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
        # No data props: the SPA fetches everything it shows (the ticket from
        # AjaxMapsTicket, the map and the listing from the Maps REST API, the
        # authoring defaults from the internal settings endpoint). Hydrating any
        # of it would be a second data-assembly path to keep in step with those,
        # and its optionality would reach every consumer of the values. It also
        # turns a forbidden or unknown ``?name=`` into a plain REST 403/404 the
        # SPA can render, rather than a silently absent prop.
        #
        # ``links`` is not data but wiring: the two curated settings forms have
        # no other entry point (Maps has no Setup tile) and their mode names
        # belong here, not to a TypeScript constant that a rename would leave
        # pointing nowhere. The dashboard page hands its own out the same way.
        #
        # ``breadcrumb_root`` is the same kind of wiring: the levels above the SPA
        # (the main menu Maps hangs under), so the app can put its own levels
        # behind them without naming a Checkmk menu in TypeScript. The settings
        # modes root their breadcrumb the same way.
        html.open_div(id_="app")
        html.vue_component(
            "cmk-maps",
            data=asdict(
                MapsApp(
                    links=MapsPageLinks(
                        authoring_settings=ModeMapsAuthoringSettings.mode_url(),
                        daemon_settings=ModeMapsDaemonSettings.mode_url(),
                    ),
                    breadcrumb_root=[
                        MapsBreadcrumbItem(title=str(item.title), link=item.url)
                        for item in make_main_menu_breadcrumb(main_menu_registry.menu_customize())
                    ],
                )
            ),
        )
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
