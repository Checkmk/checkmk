#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Page objects for the Checkmk Maps SPA (``maps.py``).

Maps ships as the ``cmk-maps`` web component mounted inline in ``maps.py``.
Only the main navigation is server-rendered: the page itself carries no heading
and no page menu, so everything these objects address — heading, actions, map
list, map view and dialogs — is rendered by the SPA. The two page objects mirror
the SPA's two routed views:

* :class:`MapsHomePage` — the map listing (cards/table, filter, search) plus
  the ``Add map`` / ``Import`` buttons in its header.
* :class:`MapsMapView` — a single opened map (``maps.py?name=<map>``).
"""

import logging
import re
from enum import StrEnum
from typing import override
from urllib.parse import urljoin

from playwright.sync_api import expect, Locator, Page

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


class MapType(StrEnum):
    """Map types offered by the *Add map* dialog (label as shown in the UI)."""

    STATIC = "Static map"
    GEO = "Geo map"
    FLOW = "Flow map"
    RADAR = "Radar (dynamic filter)"
    FOLDER_TREE = "Folder tree"
    PRESENTATION = "Presentation"


class MapsFilter(StrEnum):
    """The map-list ownership filter toggles."""

    ALL = "All"
    YOURS = "Yours"
    BUILT_IN = "Built-in"


class DrawerTab(StrEnum):
    """Tabs of the map object detail drawer."""

    STATUS = "Status"
    CONTEXT = "Context"


class MapsDetailDrawer:
    """The object detail drawer that slides in when a map object is opened.

    Not a page of its own: it teleports into the map view's portal, so it
    wraps the shared :class:`~playwright.sync_api.Page` rather than subclassing
    :class:`CmkPage`. Obtained from :meth:`MapsMapView.open_object_details`.
    """

    def __init__(self, page: Page) -> None:
        self.page = page
        # The drawer is the map view's slide-in; it is the only dialog the map
        # opens while an object is being read.
        self.root = page.get_by_role("dialog").first

    @property
    def name(self) -> Locator:
        """The opened object's name (host/service/group), the drawer's heading."""
        return self.root.get_by_role("heading")

    @property
    def state_pill(self) -> Locator:
        """The object's current state (e.g. UP / DOWN / CRIT), announced live."""
        return self.root.get_by_role("status", name="Current state")

    def tab(self, which: DrawerTab) -> Locator:
        """A drawer tab (Status / Context) by its label."""
        return self.root.get_by_role("tab", name=which.value, exact=True)

    def switch_to(self, which: DrawerTab) -> None:
        """Activate a drawer tab and confirm it is selected."""
        logger.info("Switch object drawer to the '%s' tab", which.value)
        tab = self.tab(which)
        tab.click()
        expect(tab, message=f"'{which.value}' tab did not become active").to_have_attribute(
            "aria-selected", "true"
        )

    def close(self) -> None:
        """Close the drawer and wait for it to disappear."""
        logger.info("Close the object detail drawer")
        self.root.get_by_role("button", name="Close", exact=True).click()
        expect(self.root, message="Object detail drawer did not close").to_have_count(0)


class MapsMapView(CmkPage):
    """A single opened Maps map (``maps.py?name=<map>``).

    Reached from :class:`MapsHomePage` (open or create), never navigated to
    directly, so ``navigate`` is not implemented. A map holds a live
    Server-Sent-Events stream, so the page never reaches ``networkidle`` — wait
    on concrete map elements instead.
    """

    page_title = "Maps"

    @override
    def navigate(self) -> None:
        raise NotImplementedError("Open a map via 'MapsHomePage' instead.")

    @override
    def validate_page(self) -> None:
        logger.info("Validate that the Maps map view is displayed")
        expect(self.map_view, message="Maps map view did not render").to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def map_view(self) -> Locator:
        """The map view the SPA mounts for an opened map."""
        return self.main_area.locator().get_by_role("region", name="Map view")

    @property
    def readonly_badge(self) -> Locator:
        """The 'read-only' badge shown for shipped/built-in maps."""
        return self.main_area.locator().get_by_text("Read-only", exact=True)

    @property
    def world_map(self) -> Locator:
        """The canvas a geo map draws its tiles and markers on."""
        return self.main_area.locator().get_by_role("group", name="Geo map canvas")

    # --- radar map (auto-populated card grid) ----------------------------

    @property
    def radar_cards(self) -> Locator:
        """The object cards of a radar map."""
        return (
            self.main_area.locator()
            .get_by_role("group", name="Radar objects")
            .get_by_role("button")
        )

    @property
    def radar_summary(self) -> Locator:
        """The radar map's object-count / per-state summary, announced live."""
        return self.main_area.locator().get_by_role("status", name="Radar summary")

    def wait_for_radar_ready(self) -> None:
        """Wait until the radar map has streamed in its first object card."""
        expect(
            self.radar_cards.first, message="Radar map did not populate any object"
        ).to_be_visible(timeout=30_000)

    def open_object_details(self) -> MapsDetailDrawer:
        """Open the first radar card's detail drawer and return it."""
        logger.info("Open the detail drawer of the first radar object")
        self.radar_cards.first.click()
        drawer = MapsDetailDrawer(self.page)
        expect(drawer.root, message="Object detail drawer did not open").to_be_visible()
        return drawer

    # --- static map editor (edit mode) -----------------------------------
    #
    # The edit-mode controls (the floating buttons, the add panel, the
    # properties card, the context menu, the confirm dialog) sit in a
    # fixed-position layer outside ``.maps-map-view``, and a dropdown's option
    # list is portalled to ``<body>``. Address all of them from
    # ``self.main_area``, which resolves to the document itself — never scope
    # them to the map view or to the panel that opened them.

    @property
    def editing_badge(self) -> Locator:
        """The topbar 'Editing' badge shown while edit mode is active."""
        return self.main_area.locator().get_by_text("Editing", exact=True)

    @property
    def map_canvas(self) -> Locator:
        """The canvas a static map places its objects on."""
        return self.main_area.locator().get_by_role("group", name="Map canvas")

    @property
    def map_elements(self) -> Locator:
        """All placed monitoring objects on the static map canvas.

        Every placed object is a button carrying its own name and state; the
        canvas holds nothing else that is one.
        """
        return self.map_canvas.get_by_role("button")

    def map_object(self, object_id: str) -> Locator:
        """A placed object on the static canvas by its object id.

        Every drawing tags what it places with the object's id -- an icon, a box,
        a graph and a line alike -- which is how the map itself finds them again.
        """
        return self.map_canvas.locator(f"[data-object-id='{object_id}']")

    def enter_edit_mode(self) -> None:
        """Toggle the map into edit mode and confirm via the 'Editing' badge."""
        logger.info("Enter Maps map edit mode")
        self.main_area.locator().get_by_role("button", name="Edit", exact=True).click()
        expect(self.editing_badge, message="Edit mode did not activate").to_be_visible()

    def _pick(self, combobox: Locator, option: str, query: str | None = None) -> None:
        """Choose an entry in one of the editor's dropdowns.

        The option list is portalled out of the control, so it is addressed from
        the document; a long list (every host of a site) is narrowed by typing
        before the entry is picked.
        """
        combobox.click()
        if query is not None:
            self.page.keyboard.type(query)
        entry = self.main_area.locator(
            "[role='option']", has_text=re.compile(rf"^{re.escape(option)}$")
        )
        expect(entry.first, message=f"No '{option}' entry offered").to_be_visible()
        entry.first.click()

    def open_add_panel(self) -> Locator:
        """Open the add-object panel and return it."""
        self.main_area.locator().get_by_role("button", name="Add object", exact=True).click()
        panel = self.main_area.locator().get_by_role("group", name="Add object")
        expect(panel, message="Add-object panel did not open").to_be_visible()
        return panel

    def add_host_object(self, host_name: str, position: tuple[int, int] = (420, 300)) -> Locator:
        """Add a host object in edit mode and return the placed object locator.

        Drives the add panel → object type 'Host' → hostname → 'Place on map' →
        canvas click. Placing auto-opens the properties card, which is saved with
        its defaults so the map is left in a clean, editable state.
        """
        logger.info("Add host object '%s' to the map", host_name)
        before = self.map_elements.count()
        panel = self.open_add_panel()
        self._pick(panel.get_by_role("combobox", name="Object type"), "Host")
        self._pick(panel.get_by_role("combobox", name="Host name"), host_name, query=host_name)
        place = panel.get_by_role("button", name="Place on map", exact=True)
        expect(place, message="'Place on map' stayed disabled").to_be_enabled()
        place.click()
        self.map_canvas.click(position={"x": position[0], "y": position[1]})
        expect(self.map_elements, message="Object was not placed on the canvas").to_have_count(
            before + 1
        )
        self._save_properties()
        return self.map_elements.last

    @property
    def properties_card(self) -> Locator:
        """The card that edits one object's properties."""
        return self.main_area.locator().get_by_role("dialog", name="Object properties")

    def _save_properties(self) -> None:
        """Close the properties card that placing an object opens."""
        card = self.properties_card
        if card.count():
            card.get_by_role("button", name="Save", exact=True).click()
            expect(card, message="Properties card did not close").to_have_count(0)

    def _property_input(self, label: str) -> Locator:
        """The input of a labelled row of the properties card.

        A row names what it edits, so the control is addressed through that name
        rather than through the row's markup.
        """
        return (
            self.main_area.locator()
            .get_by_role("group", name=label, exact=True)
            .get_by_role("textbox")
        )

    def edit_object_label(self, obj: Locator, label: str) -> None:
        """Open an object's properties (double-click), set its label and save."""
        logger.info("Set object label to '%s'", label)
        obj.dblclick()
        card = self.properties_card
        expect(card, message="Properties card did not open").to_be_visible()
        self._property_input("Label text").fill(label)
        card.get_by_role("button", name="Save", exact=True).click()
        expect(card, message="Properties card did not close after save").to_have_count(0)

    def assert_object_label(self, obj: Locator, label: str) -> None:
        """Reopen an object's properties and assert its stored label, then close."""
        obj.dblclick()
        card = self.properties_card
        expect(card, message="Properties card did not open").to_be_visible()
        expect(
            self._property_input("Label text"),
            message=f"Object label did not persist as '{label}'",
        ).to_have_value(label)
        card.get_by_role("button", name="Cancel", exact=True).click()
        expect(card, message="Properties card did not close").to_have_count(0)

    def open_object_drawer(self, obj: Locator) -> MapsDetailDrawer:
        """Open a placed object's detail drawer (view mode) and return it.

        A plain click on a monitored object in view mode opens the slide-in
        detail drawer (unless the object carries an explicit URL). Edit mode must
        be off — in edit mode a click selects the object instead.
        """
        logger.info("Open the detail drawer of a map object")
        obj.click()
        drawer = MapsDetailDrawer(self.page)
        expect(drawer.root, message="Object detail drawer did not open").to_be_visible()
        return drawer

    @property
    def geo_objects(self) -> Locator:
        """All object markers placed on a geo (world map) map."""
        return self.world_map.get_by_role("button")

    def add_geo_host_object(self, host_name: str) -> tuple[Locator, float, float]:
        """Add a host object to a geo map; return ``(marker, lat, lng)``.

        On a world map map 'Place on map' resolves the host's
        ``maps_lat``/``maps_lng`` and drops the marker there directly — no canvas
        click, so the operator never positions it by hand. Placing auto-opens the
        properties modal; the stored coordinates are read from it here (a marker
        double-click would hit Leaflet's own zoom, not the modal) before saving.
        """
        logger.info("Add geo host object '%s' (auto-placed at its coordinates)", host_name)
        before = self.geo_objects.count()
        panel = self.open_add_panel()
        self._pick(panel.get_by_role("combobox", name="Object type"), "Host")
        self._pick(panel.get_by_role("combobox", name="Host name"), host_name, query=host_name)
        panel.get_by_role("button", name="Place on map", exact=True).click()
        expect(self.geo_objects, message="Host was not auto-placed on the world map").to_have_count(
            before + 1
        )
        card = self.properties_card
        expect(card, message="Properties card did not open after placing").to_be_visible()
        lat = float(self._property_input("Lat").input_value())
        lng = float(self._property_input("Lng").input_value())
        card.get_by_role("button", name="Save", exact=True).click()
        expect(card, message="Properties card did not close").to_have_count(0)
        return self.geo_objects.last, lat, lng

    def delete_object(self, obj: Locator) -> None:
        """Delete a placed object via its context menu and confirm the dialog."""
        logger.info("Delete a map object via the context menu")
        before = self.map_elements.count()
        obj.click(button="right")
        ctx = self.main_area.locator().get_by_role("menu")
        expect(ctx, message="Object context menu did not open").to_be_visible()
        ctx.get_by_role("menuitem", name="Delete", exact=True).click()
        confirm = self.main_area.locator().get_by_role("dialog", name=re.compile(r"^Delete "))
        expect(confirm, message="Delete confirmation did not open").to_be_visible()
        confirm.get_by_role("button", name="Delete", exact=True).click()
        expect(self.map_elements, message="Object was not removed after delete").to_have_count(
            before - 1
        )


class MapsHomePage(CmkPage):
    """The Maps home listing (``maps.py``): map cards, ownership filter, search."""

    page_title = "Maps"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'Maps' home page")
        self.page.goto(urljoin(self.page.url, "maps.py"), wait_until="load")
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that the Maps home page is displayed")
        expect(self.heading, message="Maps heading did not render").to_be_visible()
        expect(self.home_view, message="Maps home listing did not render").to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    # --- locators ----------------------------------------------------------

    @property
    def home_view(self) -> Locator:
        """The SPA's map listing."""
        return self.main_area.locator().get_by_role("region", name="Maps")

    @property
    def heading(self) -> Locator:
        """The listing's own page heading -- ``maps.py`` renders none."""
        return self.home_view.get_by_role("heading", name=self.page_title, exact=True)

    @property
    def map_cards(self) -> Locator:
        """All map cards currently rendered in the listing."""
        return self.main_area.locator().get_by_role("listitem")

    def map_card(self, name: str) -> Locator:
        """The map card whose link points at the given map name."""
        return self.map_cards.filter(has=self.page.locator(f"a[href*='name={name}']"))

    @property
    def search_input(self) -> Locator:
        """The 'Search maps…' input in the list toolbar."""
        return self.main_area.locator().get_by_role("searchbox", name="Search maps…")

    def filter_toggle(self, which: MapsFilter) -> Locator:
        """The ownership filter chip (All / Yours / Built-in)."""
        return (
            self.main_area.locator()
            .get_by_role("group", name="Show maps")
            .get_by_role("button", name=which.value, exact=True)
        )

    @property
    def new_map_button(self) -> Locator:
        """The 'Add map' button — only present with the create permission
        (``general.edit_map``); absent for view-only users."""
        return self.home_view.get_by_role("button", name="Add map", exact=True)

    def administration_entry(self, name: str) -> Locator:
        """An entry of the header's administration menu (``maps.configure``)."""
        return self.main_area.locator().get_by_role("menuitem", name=name, exact=True)

    def open_administration(self) -> None:
        """Open the header's administration menu."""
        logger.info("Open the Maps administration menu")
        self.home_view.get_by_role("button", name="Maps administration", exact=True).click()

    # --- actions -----------------------------------------------------------

    def filter_by(self, which: MapsFilter) -> None:
        """Switch the map-list ownership filter."""
        logger.info("Filter Maps listing by '%s'", which.value)
        toggle = self.filter_toggle(which)
        toggle.click()
        expect(toggle, message=f"'{which.value}' filter was not selected").to_have_attribute(
            "aria-pressed", "true"
        )

    def search(self, query: str) -> None:
        """Type a query into the map search box."""
        logger.info("Search Maps listing for '%s'", query)
        self.search_input.fill(query)

    def create_map(
        self, name: str, map_type: MapType = MapType.STATIC, alias: str | None = None
    ) -> MapsMapView:
        """Create a new map via the header's 'Add map' button and open it.

        Returns the opened map view (the SPA routes to the new map on save).
        """
        logger.info("Create map '%s' (type '%s')", name, map_type.value)
        self.new_map_button.click()
        dialog = self.main_area.locator().get_by_role("dialog", name="Add map")
        expect(dialog, message="'Add map' dialog did not open").to_be_visible()

        dialog.get_by_label("Map ID").fill(name)
        if alias is not None:
            dialog.get_by_label("Display name").fill(alias)
        # A type card names itself before it describes itself.
        dialog.get_by_role("radio", name=re.compile(rf"^{re.escape(map_type.value)}\b")).click()

        create_button = dialog.get_by_role("button", name="Create", exact=True)
        expect(create_button, message="'Create' button stayed disabled").to_be_enabled()
        create_button.click()

        self.page.wait_for_url(re.compile(rf"maps\.py\?name={re.escape(name)}"), wait_until="load")
        return MapsMapView(self.page, navigate_to_page=False)

    def open_map(self, name: str) -> MapsMapView:
        """Open a map from its card and return the map view."""
        logger.info("Open Maps map '%s'", name)
        self.map_card(name).locator("a.maps-map-card__title").click()
        self.page.wait_for_url(re.compile(rf"maps\.py\?name={re.escape(name)}"), wait_until="load")
        return MapsMapView(self.page, navigate_to_page=False)

    def import_cfg(self, path: str, map_name: str) -> MapsMapView:
        """Import a legacy NagVis ``.cfg`` and open the resulting map.

        The header's 'Import' button wires a hidden ``<input type=file>`` that
        accepts ``.cfg``; setting the file triggers the GUI-side parser and saves
        the map, which then appears in the listing (the import does not navigate
        to it). Returns the opened map view.
        """
        logger.info("Import NagVis .cfg '%s'", path)
        # The file input is hidden by design (the header's button drives it), so
        # it has no accessible representation to address it by.
        self.main_area.locator("input[type='file'][accept*='.cfg']").set_input_files(path)
        expect(
            self.map_card(map_name), message="Imported map did not appear in the listing"
        ).to_be_visible()
        return self.open_map(map_name)

    def delete_map(self, name: str) -> None:
        """Delete a map from its card and confirm, then wait for it to disappear.

        The card's actions sit behind an overflow menu, whose content is portalled
        out of the card, so the entry is looked up on the page rather than on it.
        """
        logger.info("Delete Maps map '%s'", name)
        card = self.map_card(name)
        card.get_by_title(re.compile(r"^Actions for map ")).click()
        self.main_area.locator().get_by_role("menuitem", name="Delete map", exact=True).click()
        confirm = (
            self.main_area.locator()
            .get_by_role("dialog", name="Delete map")
            .get_by_role("button", name="Delete", exact=True)
        )
        expect(confirm, message="Delete confirmation dialog did not open").to_be_visible()
        confirm.click()
        expect(
            self.map_card(name), message=f"Map '{name}' was not removed after delete"
        ).to_have_count(0)
