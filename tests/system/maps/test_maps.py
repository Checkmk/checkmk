#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""End-to-end tests for the Checkmk Maps SPA (``maps.py``).

Covers the operator-facing flows:

* the home listing renders, its ownership filter and search narrow the map
  list, and a map can be created, opened and deleted through the UI
  (create/open/delete round trip);
* a geo map created through the dialog mounts its interactive world map;
* a shipped auto-populating map opens, its objects open a detail drawer whose
  tabs switch and close, and all shipped map types (folder-tree, flow,
  presentation, radar) render;
* a host object can be added to a static map, relabelled (persisting across a
  reload via autosave) and deleted through the editor;
* a monitored object's live state change propagates to the map over SSE;
* a host with geo labels is auto-placed on a geo map at its coordinates;
* the permission model gates authoring and hides private maps from other users;
* a comprehensive legacy NagVis ``.cfg`` imports into an equivalent map with
  every object and line type reproduced.
"""

import logging
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from playwright.sync_api import BrowserContext, expect, Page

from tests.system.gui.testlib.playwright.helpers import CmkCredentials
from tests.system.maps.conftest import navigate_to_page
from tests.system.maps.testlib.pom import (
    DrawerTab,
    MapsFilter,
    MapsHomePage,
    MapType,
)
from tests.testlib.common.utils2 import is_cleanup_enabled
from tests.testlib.system.site import Site

logger = logging.getLogger(__name__)


@pytest.fixture(name="maps_home_page")
def fixture_maps_home_page(
    cmk_page: Page, test_site: Site, credentials: CmkCredentials
) -> MapsHomePage:
    """Entrypoint to the Maps home listing."""
    return navigate_to_page(cmk_page, test_site.internal_url, credentials, MapsHomePage)


@pytest.fixture(name="temporary_map")
def fixture_temporary_map(
    request: pytest.FixtureRequest, maps_home_page: MapsHomePage
) -> Iterator[str]:
    """Provide a per-test map name; ensure the name is free before and after.

    Creating a map whose ID already exists returns 409 and the create dialog
    stays open (no navigation), so the test would hang. Under ``CLEANUP=0`` the
    teardown below is skipped, leaving the map behind and breaking the next
    ``REUSE=1`` run. Deleting a stale namesake at setup keeps the test idempotent
    regardless of the cleanup policy.
    """
    # The map-name field caps at 64 chars (CreateMapModal._MAX_NAME_LEN);
    # verbose parametrize ids (e.g. "Radar (dynamic filter)") push the sanitized
    # node name past that, which keeps the Create button disabled. Cap it so the
    # generated name is always a valid map id.
    name = ("e2e_" + re.sub(r"[^a-zA-Z0-9]", "_", request.node.name))[:64]
    if maps_home_page.map_card(name).count():
        maps_home_page.delete_map(name)
    yield name
    if is_cleanup_enabled():
        maps_home_page.navigate()
        if maps_home_page.map_card(name).count():
            maps_home_page.delete_map(name)


_OBJECT_HOST = "maps_e2e_object_host"


@pytest.fixture(name="monitored_host")
def fixture_monitored_host(test_site: Site) -> Iterator[str]:
    """Create and activate a host so the Maps object picker can resolve it.

    The picker (add-object autocomplete, radar/flow population) queries live
    monitoring through the daemon, so the host must be activated into the core.
    Self-contained on purpose: the site is shared and its existing hosts must not
    be assumed — the test brings its own and removes it again.
    """
    test_site.openapi.hosts.create(_OBJECT_HOST, attributes={"ipaddress": "127.0.0.1"})
    test_site.openapi.changes.activate_and_wait_for_completion()
    try:
        yield _OBJECT_HOST
    finally:
        if is_cleanup_enabled():
            test_site.openapi.hosts.delete(_OBJECT_HOST)
            test_site.openapi.changes.activate_and_wait_for_completion()


_GEO_HOST = "maps_e2e_geo_host"
_GEO_LAT = 52.52
_GEO_LNG = 13.40


@pytest.fixture(name="geo_host")
def fixture_geo_host(test_site: Site) -> Iterator[str]:
    """A host carrying ``maps_lat``/``maps_lng`` labels for geo auto-placement.

    Maps resolves a host's coordinates from these labels, so a geo map can drop
    the host's marker at the right spot without manual positioning. Self-contained:
    brought by the test, not assumed to exist on the shared site.
    """
    test_site.openapi.hosts.create(
        _GEO_HOST,
        attributes={
            "ipaddress": "127.0.0.1",
            "labels": {"maps_lat": str(_GEO_LAT), "maps_lng": str(_GEO_LNG)},
        },
    )
    test_site.openapi.changes.activate_and_wait_for_completion()
    try:
        yield _GEO_HOST
    finally:
        if is_cleanup_enabled():
            test_site.openapi.hosts.delete(_GEO_HOST)
            test_site.openapi.changes.activate_and_wait_for_completion()


_VIEWER_ROLE = "maps_e2e_viewer_role"
_VIEWER_USER = "maps_e2e_viewer"
_VIEWER_PASSWORD = "cmk_e2e_viewer_pw"


@pytest.fixture(name="maps_view_only_user")
def fixture_maps_view_only_user(test_site: Site) -> Iterator[CmkCredentials]:
    """A user who may open Maps but not author them.

    A clone of the built-in ``user`` role with ``general.edit_map`` denied: it
    keeps ``maps.use`` (viewing) but loses create/edit. Deleted again on teardown.
    """
    test_site.openapi.user_role.create("user", _VIEWER_ROLE, "Maps viewer (e2e)")
    test_site.openapi.user_role.edit_permissions(_VIEWER_ROLE, {"general.edit_map": "no"})
    test_site.openapi.users.create(
        username=_VIEWER_USER,
        fullname="Maps Viewer (e2e)",
        password=_VIEWER_PASSWORD,
        email="",
        contactgroups=[],
        roles=[_VIEWER_ROLE],
    )
    test_site.openapi.changes.activate_and_wait_for_completion()
    try:
        yield CmkCredentials(_VIEWER_USER, _VIEWER_PASSWORD)
    finally:
        if is_cleanup_enabled():
            test_site.openapi.users.delete(_VIEWER_USER)
            test_site.openapi.user_role.delete(_VIEWER_ROLE)
            test_site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)


def test_maps_home_page_loads(maps_home_page: MapsHomePage) -> None:
    """The Maps home listing renders with its controls."""
    expect(maps_home_page.home_view, message="Maps home listing is not visible").to_be_visible()
    for which in MapsFilter:
        expect(
            maps_home_page.filter_toggle(which),
            message=f"'{which.value}' filter toggle is missing",
        ).to_be_visible()
    expect(maps_home_page.search_input, message="Map search input is missing").to_be_visible()


def test_maps_create_open_delete_round_trip(
    maps_home_page: MapsHomePage, temporary_map: str
) -> None:
    """A map can be created, opened, filtered/searched for and deleted via the UI."""
    map_view = maps_home_page.create_map(temporary_map, MapType.STATIC)
    expect(map_view.map_view, message="Map view did not render after create").to_be_visible()
    expect(map_view.page).to_have_url(re.compile(rf"maps\.py\?name={temporary_map}"))

    maps_home_page.navigate()
    expect(
        maps_home_page.map_card(temporary_map),
        message="Created map is not listed on the home page",
    ).to_be_visible()

    # The freshly created map is owned by the acting user: it shows under
    # 'Yours' but not under 'Built-in'.
    maps_home_page.filter_by(MapsFilter.YOURS)
    expect(
        maps_home_page.map_card(temporary_map),
        message="Created map is not shown under the 'Yours' filter",
    ).to_be_visible()
    maps_home_page.filter_by(MapsFilter.BUILT_IN)
    expect(
        maps_home_page.map_card(temporary_map),
        message="User-owned map wrongly shown under the 'Built-in' filter",
    ).to_have_count(0)
    maps_home_page.filter_by(MapsFilter.ALL)

    maps_home_page.search(temporary_map)
    expect(
        maps_home_page.map_cards,
        message="Search did not narrow the listing to the matching map",
    ).to_have_count(1)
    maps_home_page.search("zzz_no_such_map_zzz")
    expect(maps_home_page.map_cards, message="Search matched an unexpected map").to_have_count(0)
    maps_home_page.search("")

    maps_home_page.open_map(temporary_map)

    maps_home_page.navigate()
    maps_home_page.delete_map(temporary_map)


def test_maps_static_map_element_crud(
    maps_home_page: MapsHomePage, temporary_map: str, monitored_host: str
) -> None:
    """Add, edit and delete a host object on a static map via the editor.

    Covers the operator authoring loop: enter edit mode, place a monitored host
    from the object picker, rename it, confirm the rename persists across a reload
    (autosave), then remove it via the context menu.
    """
    map_page = maps_home_page.create_map(temporary_map, MapType.STATIC)
    map_page.enter_edit_mode()

    obj = map_page.add_host_object(monitored_host)
    expect(obj, message="Placed host object is not visible").to_be_visible()
    expect(map_page.map_elements, message="Map should hold exactly one object").to_have_count(1)

    map_page.edit_object_label(obj, "Renamed Node")

    # Autosave persists the whole map; reload and confirm the object and its
    # renamed label survived.
    maps_home_page.navigate()
    map_page = maps_home_page.open_map(temporary_map)
    map_page.enter_edit_mode()
    expect(map_page.map_elements, message="Object did not persist across reload").to_have_count(1)
    map_page.assert_object_label(map_page.map_elements.first, "Renamed Node")

    map_page.delete_object(map_page.map_elements.first)
    expect(map_page.map_elements, message="Object was not deleted").to_have_count(0)

    maps_home_page.navigate()
    maps_home_page.delete_map(temporary_map)


def test_maps_map_element_reflects_status_change(
    maps_home_page: MapsHomePage, temporary_map: str, monitored_host: str, test_site: Site
) -> None:
    """A monitored object's live state change is reflected on the map.

    Place a host object (UP), force the host DOWN via a passive check result, and
    assert the change propagates over the SSE state stream to both the on-canvas
    object (its accessible name) and the detail drawer's state pill — without a
    page reload.
    """
    map_page = maps_home_page.create_map(temporary_map, MapType.STATIC)
    map_page.enter_edit_mode()
    map_page.add_host_object(monitored_host)

    # Reopen in view mode (flushes autosave, leaves edit mode) so a click opens
    # the detail drawer instead of selecting the object.
    maps_home_page.navigate()
    map_page = maps_home_page.open_map(temporary_map)
    obj = map_page.map_elements.first
    expect(obj, message="Host object should start in the UP state").to_have_attribute(
        "aria-label", re.compile(r"\bUp\b"), timeout=30_000
    )
    drawer = map_page.open_object_drawer(obj)
    expect(drawer.state_pill, message="Drawer should read UP").to_have_text("UP")
    drawer.close()

    # Force the host DOWN (blocks until Livestatus reflects it), then assert the
    # map updates live via SSE — no reload.
    test_site.send_host_check_result(monitored_host, 1, "e2e forced down")
    expect(obj, message="Map object did not reflect the DOWN state").to_have_attribute(
        "aria-label", re.compile(r"\bDown\b"), timeout=30_000
    )
    drawer = map_page.open_object_drawer(obj)
    expect(drawer.state_pill, message="Drawer should read DOWN").to_have_text("DOWN")
    drawer.close()

    maps_home_page.navigate()
    maps_home_page.delete_map(temporary_map)


def test_maps_create_geo_map_renders_world_map(
    maps_home_page: MapsHomePage, temporary_map: str
) -> None:
    """A geo map can be created and mounts its interactive world map.

    Geo is the one map type without a shipped built-in, so it is only reachable
    through the create dialog — the other four types render from built-ins in
    ``test_maps_builtin_map_renders`` / ``test_maps_radar_map_element_drawer``.
    """
    map_page = maps_home_page.create_map(temporary_map, MapType.GEO)
    expect(map_page.map_view, message="Map view did not render after create").to_be_visible()
    expect(map_page.world_map, message="Geo map did not mount its world map").to_be_visible()


def test_maps_geo_map_auto_places_host_by_coordinates(
    maps_home_page: MapsHomePage, temporary_map: str, geo_host: str
) -> None:
    """A host with geo labels is auto-placed on a geo map at its coordinates.

    Adding the host on a world map map resolves its ``maps_lat``/``maps_lng``
    and drops the marker there directly — no manual positioning — so the stored
    marker coordinates must match the host's labels.
    """
    map_page = maps_home_page.create_map(temporary_map, MapType.GEO)
    expect(map_page.world_map, message="Geo map did not mount its world map").to_be_visible()
    map_page.enter_edit_mode()

    marker, lat, lng = map_page.add_geo_host_object(geo_host)
    expect(marker, message="Geo host marker was not placed").to_be_visible()
    expect(map_page.geo_objects, message="Geo map should hold one marker").to_have_count(1)
    assert abs(lat - _GEO_LAT) < 0.01, f"marker latitude {lat} != host label {_GEO_LAT}"
    assert abs(lng - _GEO_LNG) < 0.01, f"marker longitude {lng} != host label {_GEO_LNG}"

    maps_home_page.navigate()
    maps_home_page.delete_map(temporary_map)


def test_maps_administration_menu_reaches_the_settings_form(
    maps_home_page: MapsHomePage,
) -> None:
    """The listing's administration menu leads to the curated settings forms.

    ``maps.py`` renders no page menu, so this menu is the only way from the SPA
    into the two WATO modes -- and the only consumer of the URLs the page hands
    the SPA.
    """
    maps_home_page.open_administration()
    maps_home_page.administration_entry("Map & object defaults").click()

    maps_home_page.page.wait_for_url(
        re.compile(r"wato\.py\?mode=maps_authoring_settings"), wait_until="load"
    )
    maps_home_page.main_area.check_page_title("Map & object defaults")


def test_maps_permissions_view_only_user(
    maps_home_page: MapsHomePage,
    temporary_map: str,
    maps_view_only_user: CmkCredentials,
    new_browser_context_and_page: tuple[BrowserContext, Page],
    test_site: Site,
) -> None:
    """Maps' permission model gates authoring and isolates private maps.

    A view-only user (``maps.use`` but no ``general.edit_map``) can open Maps and
    see the shipped built-in maps, but has no 'Add map' affordance and cannot
    see another user's private map.
    """
    # Control: the acting admin may create, so the button is present.
    expect(
        maps_home_page.new_map_button, message="Admin should see the 'Add map' button"
    ).to_be_visible()

    # Admin creates a private map (default visibility).
    maps_home_page.create_map(temporary_map, MapType.STATIC)

    # The view-only user, in a fresh browser context.
    _, viewer_page = new_browser_context_and_page
    viewer_home = navigate_to_page(
        viewer_page, test_site.internal_url, maps_view_only_user, MapsHomePage
    )

    expect(viewer_home.home_view, message="View-only user cannot open Maps").to_be_visible()
    expect(
        viewer_home.map_cards.first,
        message="View-only user should see the shipped built-in maps",
    ).to_be_visible()
    expect(
        viewer_home.map_card(temporary_map),
        message="A private map must not be visible to another user",
    ).to_have_count(0)
    expect(
        viewer_home.new_map_button,
        message="View-only user must not have the 'Add map' affordance",
    ).to_have_count(0)

    maps_home_page.navigate()
    maps_home_page.delete_map(temporary_map)


def test_maps_radar_map_element_drawer(maps_home_page: MapsHomePage) -> None:
    """A built-in radar map populates and its objects open a detail drawer.

    Uses the shipped ``all_hosts`` map, which auto-populates from live
    monitoring, so it needs no map authoring to have objects to interact with.
    """
    map_page = maps_home_page.open_map("all_hosts")
    expect(map_page.readonly_badge, message="Built-in map is not marked read-only").to_be_visible()
    map_page.wait_for_radar_ready()
    expect(map_page.radar_summary, message="Radar map summary is missing").to_be_visible()

    drawer = map_page.open_object_details()
    expect(drawer.name, message="Detail drawer has no object name").to_have_text(re.compile(r".+"))
    expect(drawer.state_pill, message="Detail drawer shows no object state").to_be_visible()

    drawer.switch_to(DrawerTab.CONTEXT)
    drawer.switch_to(DrawerTab.STATUS)
    drawer.close()


@pytest.mark.parametrize(
    "map_type",
    [MapType.FLOW, MapType.RADAR, MapType.FOLDER_TREE, MapType.PRESENTATION],
)
def test_maps_create_map_type_renders(
    maps_home_page: MapsHomePage, temporary_map: str, map_type: MapType
) -> None:
    """Every remaining map type can be created through the dialog and mounts.

    The static and geo *create* paths have their own round-trip tests; this
    covers the create → render → (fixture) delete path for the other four types,
    which are otherwise only exercised as shipped built-ins.
    """
    map_page = maps_home_page.create_map(temporary_map, map_type)
    expect(
        map_page.map_view, message=f"'{map_type.value}' map did not render after create"
    ).to_be_visible()
    expect(map_page.page).to_have_url(re.compile(rf"maps\.py\?name={temporary_map}"))


@pytest.mark.parametrize(
    "map_name",
    ["monitoring_folders", "infrastructure", "noc_wall", "service_problems"],
)
def test_maps_builtin_map_renders(maps_home_page: MapsHomePage, map_name: str) -> None:
    """The shipped folder-tree, flow, presentation and radar maps open and render.

    Together with ``test_maps_radar_map_element_drawer`` (``all_hosts``) this
    covers all five built-in map types end to end.
    """
    map_page = maps_home_page.open_map(map_name)
    expect(map_page.map_view, message=f"Map '{map_name}' did not render").to_be_visible()
    expect(
        map_page.readonly_badge, message=f"Map '{map_name}' is not marked read-only"
    ).to_be_visible()


# A NagVis map exercising every importable block type (host, service, host/
# servicegroup, map link, BI aggregation, dynamic group, shape→image, textbox,
# container→graph) and every line_type (10 bidirectional, 11 arrow, 12 plain,
# 13/14/15 stateful weathermap). The importer names the map after the file.
_NAGVIS_MAP = "e2e_maps_nagvis_import"
_NAGVIS_DEMO_CFG = """
define global {
    alias=Maps E2E NagVis Demo
    iconset=std_medium
}
define host {
    object_id=h1
    host_name=demo-host
    x=100
    y=100
}
define service {
    object_id=s1
    host_name=demo-host
    service_description=CPU load
    x=200
    y=100
}
define hostgroup {
    object_id=hg1
    hostgroup_name=linux
    x=300
    y=100
}
define servicegroup {
    object_id=sg1
    servicegroup_name=web
    x=400
    y=100
}
define map {
    object_id=m1
    map_name=another_map
    x=500
    y=100
}
define aggr {
    object_id=a1
    aggr_name=My Aggregation
    x=600
    y=100
}
define dyngroup {
    object_id=dg1
    name=dyn1
    object_types=host
    object_filter=host_name~demo
    x=100
    y=200
}
define shape {
    object_id=sh1
    icon=demo_icon.png
    x=200
    y=200
}
define textbox {
    object_id=tb1
    text=<b>Weathermap</b>
    x=300
    y=200
    w=160
    h=40
}
define container {
    object_id=c1
    url=https://example.org/embed
    x=450
    y=200
    w=300
    h=150
}
define line {
    object_id=l10
    line_type=10
    x=100,180
    y=320,320
}
define line {
    object_id=l11
    line_type=11
    x=100,180
    y=360,360
}
define line {
    object_id=l12
    line_type=12
    x=100,180
    y=400,400
}
define line {
    object_id=l13
    line_type=13
    host_name=demo-host
    service_description=Interface 1
    x=250,330
    y=320,320
}
define line {
    object_id=l14
    line_type=14
    host_name=demo-host
    service_description=Interface 1
    x=250,330
    y=360,360
}
define line {
    object_id=l15
    line_type=15
    host_name=demo-host
    service_description=Interface 1
    x=250,330
    y=400,400
}
"""

# object_id -> Maps object id the importer assigns ({maps_type}_{object_id}).
_NAGVIS_ICON_OBJECT_IDS = [
    "host_h1",
    "service_s1",
    "hostgroup_hg1",
    "servicegroup_sg1",
    "map_m1",
    "aggregation_a1",
    "dyngroup_dg1",
    "image_sh1",
    "textbox_tb1",
    "graph_c1",
]
_NAGVIS_LINE_OBJECT_IDS = ["line_l10", "line_l11", "line_l12", "line_l13", "line_l14", "line_l15"]


def test_maps_nagvis_import_reproduces_all_object_types(
    maps_home_page: MapsHomePage, tmp_path: Path
) -> None:
    """Importing a comprehensive NagVis .cfg reproduces every object and line type.

    The map is parsed GUI-side and saved through the Maps REST API, then opened;
    each imported object must be present on the canvas with the expected id, so a
    NagVis map round-trips into an equivalent Maps map.
    """
    cfg_file = tmp_path / f"{_NAGVIS_MAP}.cfg"
    cfg_file.write_text(_NAGVIS_DEMO_CFG, encoding="utf-8")

    # Idempotent under REUSE/CLEANUP=0: drop a map left over from a prior run.
    if maps_home_page.map_card(_NAGVIS_MAP).count():
        maps_home_page.delete_map(_NAGVIS_MAP)

    map_page = maps_home_page.import_cfg(str(cfg_file), _NAGVIS_MAP)

    for object_id in _NAGVIS_ICON_OBJECT_IDS:
        expect(
            map_page.map_object(object_id),
            message=f"Imported object '{object_id}' is missing from the map",
        ).to_have_count(1)
    for line_id in _NAGVIS_LINE_OBJECT_IDS:
        expect(
            map_page.map_object(line_id),
            message=f"Imported line '{line_id}' is missing from the map",
        ).to_have_count(1)

    maps_home_page.navigate()
    maps_home_page.delete_map(_NAGVIS_MAP)
