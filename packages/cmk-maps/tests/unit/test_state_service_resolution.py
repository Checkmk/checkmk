#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""State-resolution tests for the Maps daemon ``state_service``.

Covers the resolution paths layered on top of the primary-host + roll-up core
(tested in ``test_state_service.py``): connection registry lookup, map state
fetch + batch-failure fallback, recursive map-link aggregation, per-object
connection override, worldmap automap/bundle inflation, the SSE delta encoders
(state / topology / folder-tree), and the folder-tree assembly driven by the
demo ``FakeConnection``.

Async coroutines are driven with ``asyncio.run`` — the cmk-maps test target
has no async plugin (mirrors ``test_state_service.py``). The delta encoders are
plain ``def`` and need no wrapper.
"""

import asyncio
from collections.abc import Iterator
from typing import Literal
from unittest.mock import AsyncMock, MagicMock

import pytest
from fake_connection import FakeConnection

from cmk.maps.backend.connections.base import FolderTreeData
from cmk.maps.backend.schemas.map import (
    MapConfig,
    MapElement,
    StaticView,
    WorldmapView,
)
from cmk.maps.backend.schemas.presentation import (
    DataElement,
    PresentationView,
    ShapeElement,
)
from cmk.maps.backend.schemas.state import (
    FolderTreeNode,
    ObjectState,
    ServicesSummary,
)
from cmk.maps.backend.schemas.topology import ServiceNode, TopologyNode
from cmk.maps.backend.services import map_service, state_service
from cmk.maps.backend.services.state_service import (
    get_connection,
    get_map_states,
    register_connection,
)
from cmk.maps.shared.states import SEVERITY_RANK

pytestmark = pytest.mark.usefixtures("_clear_topology_snapshots")


def _map(
    objects: list[MapElement], *, name: str = "test", connection_id: str = "mock"
) -> MapConfig:
    return MapConfig(
        name=name,
        alias="Test",
        connection_id=connection_id,
        view=StaticView(),
        objects=objects,
    )


def _obj(obj_id: str, obj_type: str = "host", **kwargs: object) -> MapElement:
    return MapElement.model_validate({"id": obj_id, "type": obj_type, **kwargs})


# ---------------------------------------------------------------------------
# register_connection / get_connection
# ---------------------------------------------------------------------------


def test_register_and_get_connection(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(state_service, "_connections", {})
    register_connection("myconn", mock_connection)
    assert get_connection("myconn") is mock_connection


def test_get_connection_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(state_service, "_connections", {})
    assert get_connection("nonexistent") is None


# ---------------------------------------------------------------------------
# get_map_states — connection presence / failures
# ---------------------------------------------------------------------------


def test_get_map_states_no_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(state_service, "_connections", {})
    map_cfg = _map(
        [
            _obj("h1", "host", host_name="srv1"),
            _obj("s1", "service", host_name="srv1", service_description="CPU"),
        ],
        connection_id="missing",
    )
    result = asyncio.run(get_map_states(map_cfg))
    assert result.connection_ok is False
    assert all(s.state == "PENDING" for s in result.states)
    assert len(result.states) == 2


def test_get_map_states_with_connection(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    host_state = ObjectState(object_id="h1", type="host", state="UP")
    mock_connection.get_hosts_states = AsyncMock(return_value={"srv1": host_state})

    map_cfg = _map([_obj("h1", "host", host_name="srv1")])
    result = asyncio.run(get_map_states(map_cfg))

    assert result.connection_ok is True
    assert result.states[0].state == "UP"
    assert result.states[0].object_id == "h1"


def test_get_map_states_batch_exception_yields_pending(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.get_hosts_states = AsyncMock(side_effect=Exception("socket error"))
    # A socket that still answers does not make a failed query a live map.
    mock_connection.is_available = AsyncMock(return_value=True)

    map_cfg = _map([_obj("h1", "host", host_name="srv1")])
    result = asyncio.run(get_map_states(map_cfg))

    assert result.connection_ok is False
    assert result.states[0].state == "PENDING"
    assert result.states[0].stale is True


def test_get_map_states_overdue_checks_keep_the_connection_up(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.get_hosts_states = AsyncMock(
        return_value={"srv1": ObjectState(object_id="h1", type="host", state="UP", stale=True)}
    )
    mock_connection.is_available = AsyncMock(return_value=False)

    result = asyncio.run(get_map_states(_map([_obj("h1", "host", host_name="srv1")])))

    assert result.connection_ok is True
    assert result.states[0].stale is True
    mock_connection.is_available.assert_not_awaited()


def test_get_map_states_names_the_sites_that_stopped_answering(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.dead_sites = MagicMock(return_value=["remote"])
    cfg = MapConfig(
        name="geo",
        alias="Geo",
        connection_id="mock",
        view=WorldmapView(auto_source="all_hosts"),
        objects=[],
    )

    assert asyncio.run(get_map_states(cfg)).dead_sites == ["remote"]


def test_get_map_states_non_monitoring_objects(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.is_available = AsyncMock(return_value=True)

    # textbox and image are non-monitoring → connection_ok comes from is_available.
    map_cfg = _map([_obj("t1", "textbox"), _obj("i1", "image")])
    result = asyncio.run(get_map_states(map_cfg))
    assert result.connection_ok is True
    assert all(s.state == "PENDING" for s in result.states)


# ---------------------------------------------------------------------------
# Map-link aggregation (recursive nested map states + cycle guard)
# ---------------------------------------------------------------------------


def test_map_link_aggregates_nested_map_states(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Map-A → Map-B → host(DOWN) chain must surface DOWN on the top link."""
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    inner = _map([_obj("h_inner", "host", host_name="srv-crit")], name="inner")
    leaf = _map([_obj("link_to_inner", "map", map_name="inner")], name="leaf")
    outer = _map([_obj("link_to_leaf", "map", map_name="leaf")], name="outer")

    maps = {"inner": inner, "leaf": leaf, "outer": outer}
    monkeypatch.setattr(map_service, "get_map", lambda _owner, name="": maps.get(name))
    mock_connection.get_hosts_states = AsyncMock(
        return_value={"srv-crit": ObjectState(object_id="h_inner", type="host", state="DOWN")}
    )

    result = asyncio.run(get_map_states(outer))
    by_id = {s.object_id: s for s in result.states}
    assert by_id["link_to_leaf"].state == "DOWN"


def test_map_link_handles_cycle_without_recursion(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A self-referential map cycle must not stack-overflow; result is PENDING."""
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    a = _map([_obj("a_to_b", "map", map_name="b")], name="a")
    b = _map([_obj("b_to_a", "map", map_name="a")], name="b")
    monkeypatch.setattr(map_service, "get_map", lambda _owner, name="": {"a": a, "b": b}.get(name))
    mock_connection.is_available = AsyncMock(return_value=True)

    result = asyncio.run(get_map_states(a))
    by_id = {s.object_id: s for s in result.states}
    assert by_id["a_to_b"].state == "PENDING"


# ---------------------------------------------------------------------------
# Per-object connection override
# ---------------------------------------------------------------------------


def test_per_object_connection_override_routes_to_other_connection(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An object's ``connection_id`` overrides the map default."""
    primary = mock_connection
    secondary = AsyncMock()
    secondary.get_hosts_states = AsyncMock(
        return_value={
            "remote-host": ObjectState(object_id="remote-host", type="host", state="DOWN")
        }
    )
    secondary.get_services_summary = AsyncMock(return_value={})
    secondary.is_available = AsyncMock(return_value=True)

    primary.get_hosts_states = AsyncMock(
        return_value={"local-host": ObjectState(object_id="local-host", type="host", state="UP")}
    )

    monkeypatch.setattr(state_service, "_connections", {"primary": primary, "secondary": secondary})

    map_cfg = _map(
        [
            _obj("local", "host", host_name="local-host"),
            _obj("remote", "host", host_name="remote-host", connection_id="secondary"),
        ],
        connection_id="primary",
    )
    result = asyncio.run(get_map_states(map_cfg))
    by_id = {s.object_id: s for s in result.states}
    assert by_id["local"].state == "UP"
    assert by_id["remote"].state == "DOWN"
    primary.get_hosts_states.assert_called_once()
    secondary.get_hosts_states.assert_called_once()


def test_per_object_connection_override_unregistered_yields_pending(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(state_service, "_connections", {"primary": mock_connection})
    mock_connection.get_hosts_states = AsyncMock(return_value={})

    map_cfg = _map(
        [_obj("orphan", "host", host_name="anywhere", connection_id="ghost")],
        connection_id="primary",
    )
    result = asyncio.run(get_map_states(map_cfg))
    by_id = {s.object_id: s for s in result.states}
    assert by_id["orphan"].state == "PENDING"
    assert by_id["orphan"].stale is True


# ---------------------------------------------------------------------------
# Worldmap auto_source + geo bundles (inflate_auto_objects)
# ---------------------------------------------------------------------------


def test_worldmap_auto_source_inflates_geo_hosts(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """worldmap.auto_source pulls hosts with geo coords into transient objects."""
    mock_connection.get_hosts_states = AsyncMock(
        return_value={
            "ham-srv1": ObjectState(object_id="ham-srv1", type="host", state="UP"),
            "muc-srv1": ObjectState(object_id="muc-srv1", type="host", state="DOWN"),
        }
    )
    mock_connection.get_hosts_with_geo = AsyncMock(
        return_value=[
            {"name": "ham-srv1", "alias": "Hamburg srv1", "lat": 53.5, "lng": 10.0},
            {"name": "muc-srv1", "alias": "Munich srv1", "lat": 48.1, "lng": 11.5},
        ]
    )
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    cfg = MapConfig(
        name="geo",
        alias="Geo",
        connection_id="mock",
        view=WorldmapView(auto_source="all_hosts"),
        objects=[],
    )
    result = asyncio.run(get_map_states(cfg))
    by_id = {s.object_id: s for s in result.states}
    assert by_id["auto:ham-srv1"].state == "UP"
    assert by_id["auto:muc-srv1"].state == "DOWN"


def test_worldmap_auto_source_folds_service_states_into_hosts(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_connection.get_hosts_states = AsyncMock(
        return_value={"lei-srv1": ObjectState(object_id="lei-srv1", type="host", state="UP")}
    )
    summary = ServicesSummary(ok=3, critical=1)
    mock_connection.get_services_summary = AsyncMock(return_value={"lei-srv1": summary})
    mock_connection.get_hosts_with_geo = AsyncMock(
        return_value=[{"name": "lei-srv1", "alias": "Leipzig srv1", "lat": 51.3, "lng": 12.4}]
    )
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    cfg = MapConfig(
        name="geo",
        alias="Geo",
        connection_id="mock",
        view=WorldmapView(auto_source="all_hosts"),
        objects=[],
    )
    result = asyncio.run(get_map_states(cfg))
    by_id = {s.object_id: s for s in result.states}
    assert by_id["auto:lei-srv1"].state == "CRITICAL"
    # The fold changes the state, not what else is known about the host.
    assert by_id["auto:lei-srv1"].services_summary == summary


def test_worldmap_auto_source_keeps_a_pending_host_with_ok_services_pending(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    mock_connection.get_hosts_states = AsyncMock(
        return_value={"kie-srv1": ObjectState(object_id="kie-srv1", type="host", state="PENDING")}
    )
    mock_connection.get_services_summary = AsyncMock(
        return_value={"kie-srv1": ServicesSummary(ok=1, pending=1)}
    )
    mock_connection.get_hosts_with_geo = AsyncMock(
        return_value=[{"name": "kie-srv1", "alias": "Kiel srv1", "lat": 54.3, "lng": 10.1}]
    )
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    cfg = MapConfig(
        name="geo",
        alias="Geo",
        connection_id="mock",
        view=WorldmapView(auto_source="all_hosts"),
        objects=[],
    )
    result = asyncio.run(get_map_states(cfg))
    by_id = {s.object_id: s for s in result.states}
    assert by_id["auto:kie-srv1"].state == "PENDING"


def test_worldmap_auto_source_skips_persisted_duplicates(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Persisted objects with matching host names win over auto-discovered ones."""
    mock_connection.get_hosts_states = AsyncMock(
        return_value={"srv1": ObjectState(object_id="srv1", type="host", state="DOWN")}
    )
    mock_connection.get_hosts_with_geo = AsyncMock(
        return_value=[{"name": "srv1", "alias": "srv1", "lat": 1.0, "lng": 2.0}]
    )
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    cfg = MapConfig(
        name="geo",
        alias="Geo",
        connection_id="mock",
        view=WorldmapView(auto_source="all_hosts"),
        objects=[MapElement(id="manual_srv1", type="host", host_name="srv1", lat=10, lng=20)],
    )
    result = asyncio.run(get_map_states(cfg))
    ids = {s.object_id for s in result.states}
    assert "manual_srv1" in ids
    assert "auto:srv1" not in ids


def test_static_bundle_suppresses_markers_and_folds_services(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A static geo bundle hides its members' auto markers and shows the worst
    host+service state, not just host up/down."""
    mock_connection.get_hosts_with_geo = AsyncMock(
        return_value=[
            {"name": "srv1", "alias": "srv1", "lat": 1.0, "lng": 2.0},
            {"name": "srv2", "alias": "srv2", "lat": 1.0, "lng": 2.0},
            {"name": "srv3", "alias": "srv3", "lat": 5.0, "lng": 6.0},
        ]
    )
    mock_connection.get_hosts_states = AsyncMock(
        return_value={"srv3": ObjectState(object_id="srv3", type="host", state="UP")}
    )
    mock_connection.get_dyngroup_state = AsyncMock(
        return_value=ObjectState(
            object_id="",
            type="dyngroup",
            state="UP",
            services_summary=ServicesSummary(critical=1),
        )
    )
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    cfg = MapConfig(
        name="geo",
        alias="Geo",
        connection_id="mock",
        view=WorldmapView(auto_source="all_hosts"),
        objects=[
            MapElement(
                id="bundle1",
                type="dyngroup",
                object_types="host",
                object_filter="Filter: name = srv1\nFilter: name = srv2\nOr: 2\n",
                bundle_kind="static",
                bundle_hosts=["srv1", "srv2"],
                recognize_services=True,
                lat=1.0,
                lng=2.0,
            )
        ],
    )
    result = asyncio.run(get_map_states(cfg))
    by_id = {s.object_id: s for s in result.states}
    assert by_id["bundle1"].state == "CRITICAL"
    assert "auto:srv1" not in by_id
    assert "auto:srv2" not in by_id
    assert "auto:srv3" in by_id
    mock_connection.get_dyngroup_state.assert_awaited_once()


def test_location_bundle_matches_hosts_at_coordinate(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A location bundle re-resolves its members from the live geo hosts at its
    coordinate and suppresses their individual markers."""
    mock_connection.get_hosts_with_geo = AsyncMock(
        return_value=[
            {"name": "srv1", "alias": "srv1", "lat": 1.0, "lng": 2.0},
            {"name": "srv2", "alias": "srv2", "lat": 1.0, "lng": 2.0},
            {"name": "srv3", "alias": "srv3", "lat": 5.0, "lng": 6.0},
        ]
    )
    mock_connection.get_hosts_states = AsyncMock(
        return_value={"srv3": ObjectState(object_id="srv3", type="host", state="UP")}
    )
    mock_connection.get_dyngroup_state = AsyncMock(
        return_value=ObjectState(
            object_id="", type="dyngroup", state="UP", services_summary=ServicesSummary()
        )
    )
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    cfg = MapConfig(
        name="geo",
        alias="Geo",
        connection_id="mock",
        view=WorldmapView(auto_source="all_hosts"),
        objects=[
            MapElement(
                id="loc1",
                type="dyngroup",
                object_types="host",
                bundle_kind="location",
                lat=1.0,
                lng=2.0,
            )
        ],
    )
    result = asyncio.run(get_map_states(cfg))
    by_id = {s.object_id for s in result.states}
    assert "loc1" in by_id
    assert "auto:srv1" not in by_id
    assert "auto:srv2" not in by_id
    assert "auto:srv3" in by_id
    called_filter = mock_connection.get_dyngroup_state.await_args.args[1]
    assert "Filter: name = srv1" in called_filter
    assert "Filter: name = srv2" in called_filter
    assert "Or: 2" in called_filter


def test_location_bundle_without_auto_source_uses_baseline(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A location bundle on a map without auto_source still resolves its
    selected members, so it isn't stuck PENDING when no host matches the coord."""
    mock_connection.get_hosts_with_geo = AsyncMock(return_value=[])
    mock_connection.get_dyngroup_state = AsyncMock(
        return_value=ObjectState(
            object_id="", type="dyngroup", state="UP", services_summary=ServicesSummary()
        )
    )
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    cfg = MapConfig(
        name="geo",
        alias="Geo",
        connection_id="mock",
        view=WorldmapView(auto_source=None),
        objects=[
            MapElement(
                id="loc1",
                type="dyngroup",
                object_types="host",
                bundle_kind="location",
                bundle_hosts=["srv1", "srv2"],
                object_filter="Filter: name = srv1\nFilter: name = srv2\nOr: 2\n",
                lat=1.0,
                lng=2.0,
            )
        ],
    )
    result = asyncio.run(get_map_states(cfg))
    assert "loc1" in {s.object_id for s in result.states}
    mock_connection.get_dyngroup_state.assert_awaited_once()
    called_filter = mock_connection.get_dyngroup_state.await_args.args[1]
    assert "Filter: name = srv1" in called_filter
    assert "Filter: name = srv2" in called_filter


# ---------------------------------------------------------------------------
# Presentation map binding resolution
# ---------------------------------------------------------------------------


def test_presentation_map_resolves_bound_data_elements(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A presentation map resolves live state for its bound data elements,
    keyed by element id, and ignores design-only elements."""
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    host_state = ObjectState(object_id="ignored", type="host", state="UP")
    mock_connection.get_hosts_states = AsyncMock(return_value={"web01": host_state})

    view = PresentationView(
        elements=[
            ShapeElement(id="shape1", kind="shape", shape="rect"),
            ShapeElement(id="shape2", kind="shape", shape="line", host_name="web01"),
            DataElement(id="data1", kind="data", host_name="web01"),
            DataElement(id="data2", kind="data"),
        ]
    )
    map_cfg = MapConfig(name="pres", alias="P", connection_id="mock", view=view)

    result = asyncio.run(get_map_states(map_cfg))
    by_id = {s.object_id: s for s in result.states}
    assert by_id["data1"].state == "UP"
    # A monitoring-bound shape (weathermap-style link) resolves like a data element.
    assert by_id["shape2"].state == "UP"
    # Design-only elements (unbound shape, unbound data) carry no state.
    assert "shape1" not in by_id
    assert "data2" not in by_id
    assert result.connection_ok is True


def test_presentation_map_resolves_group_bindings(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Group-bound presentation elements resolve through the same per-type paths
    as static map objects; legacy host/service derivation stays intact for
    elements without an explicit object_type."""
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.get_hosts_states = AsyncMock(
        return_value={"web01": ObjectState(object_id="x", type="host", state="UP")}
    )
    mock_connection.get_hostgroup_states = AsyncMock(
        return_value=ObjectState(object_id="x", type="hostgroup", state="WARNING")
    )
    mock_connection.get_servicegroup_states = AsyncMock(
        return_value=ObjectState(object_id="x", type="servicegroup", state="CRITICAL")
    )

    view = PresentationView(
        elements=[
            DataElement(id="legacy", kind="data", host_name="web01"),
            DataElement(id="hg", kind="data", object_type="hostgroup", group_name="linux"),
            DataElement(id="sg", kind="data", object_type="servicegroup", group_name="https"),
        ]
    )
    map_cfg = MapConfig(name="pres", alias="P", connection_id="mock", view=view)

    result = asyncio.run(get_map_states(map_cfg))
    by_id = {s.object_id: s for s in result.states}
    assert by_id["legacy"].state == "UP"
    assert by_id["hg"].state == "WARNING"
    assert by_id["sg"].state == "CRITICAL"
    mock_connection.get_hostgroup_states.assert_awaited_once_with(
        "linux", only_hard=False, with_services=False, exclude=None
    )
    mock_connection.get_servicegroup_states.assert_awaited_once_with(
        "https", only_hard=False, exclude=None
    )


def test_presentation_view_rejects_duplicate_element_ids() -> None:
    with pytest.raises(ValueError, match="duplicate element id"):
        PresentationView(
            elements=[
                ShapeElement(id="dup", kind="shape"),
                DataElement(id="dup", kind="data"),
            ]
        )


def test_presentation_shape_rejects_css_injection_color() -> None:
    with pytest.raises(ValueError, match="invalid color"):
        ShapeElement(id="x", kind="shape", fill="expression(alert(1))")


# ---------------------------------------------------------------------------
# Object-state SSE delta — compute_states_delta (slim timing patches)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "recognize_services, expected",
    [
        (False, "UP"),
        (True, "WARNING"),  # NagVis counts the members' services too
    ],
)
def test_hostgroup_counts_its_services_only_where_asked(
    mock_connection: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    recognize_services: bool,
    expected: str,
) -> None:
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.get_hostgroup_states = AsyncMock(
        return_value=ObjectState(
            object_id="x",
            type="hostgroup",
            state="UP",
            services_summary=ServicesSummary(ok=3, warning=1) if recognize_services else None,
        )
    )
    map_cfg = _map(
        [
            _obj(
                "hg",
                "hostgroup",
                group_name="web",
                recognize_services=recognize_services,
                only_hard_states=True,
            )
        ]
    )

    result = asyncio.run(get_map_states(map_cfg))

    assert result.states[0].state == expected
    mock_connection.get_hostgroup_states.assert_awaited_once_with(
        "web", only_hard=True, with_services=recognize_services, exclude=None
    )


def test_host_group_leaves_out_the_members_whose_state_is_excluded(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    # As in NagVis, the pattern for the state replaces the one for the members.
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.get_hostgroup_states = AsyncMock(
        return_value=ObjectState(object_id="x", type="hostgroup", state="UP")
    )
    map_cfg = _map(
        [
            _obj(
                "hg",
                "hostgroup",
                group_name="web",
                exclude_members="^test-",
                exclude_member_states="^db-",
            )
        ]
    )

    asyncio.run(get_map_states(map_cfg))

    mock_connection.get_hostgroup_states.assert_awaited_once_with(
        "web", only_hard=False, with_services=False, exclude="^db-"
    )


def test_host_counts_only_the_services_it_does_not_leave_out(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.get_hosts_states = AsyncMock(
        return_value={"web01": ObjectState(object_id="x", type="host", state="UP")}
    )
    mock_connection.get_services_summary = AsyncMock(
        return_value={"web01": ServicesSummary(ok=3, critical=1)}
    )
    mock_connection.get_hosts_services_summaries = AsyncMock(
        return_value={"web01": ServicesSummary(ok=3)}
    )
    map_cfg = _map([_obj("h", host_name="web01", recognize_services=True, exclude_members="^CPU")])

    result = asyncio.run(get_map_states(map_cfg))

    assert result.states[0].state == "UP"
    assert result.states[0].services_summary == ServicesSummary(ok=3)
    mock_connection.get_hosts_services_summaries.assert_awaited_once_with(["web01"], "^CPU")


def test_graph_counts_every_service_of_its_host(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.get_hosts_states = AsyncMock(
        return_value={"web01": ObjectState(object_id="x", type="host", state="UP")}
    )
    mock_connection.get_services_summary = AsyncMock(
        return_value={"web01": ServicesSummary(ok=3, critical=1)}
    )
    mock_connection.get_hosts_services_summaries = AsyncMock(
        return_value={"web01": ServicesSummary(ok=3)}
    )
    map_cfg = _map([_obj("g", "graph", host_name="web01", exclude_members="^CPU")])

    result = asyncio.run(get_map_states(map_cfg))

    assert result.states[0].services_summary == ServicesSummary(ok=3, critical=1)


def test_host_whose_excluded_services_cannot_be_read_is_stale(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Falling back to every service would count the excluded ones again.
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.get_hosts_states = AsyncMock(
        return_value={"web01": ObjectState(object_id="x", type="host", state="UP")}
    )
    mock_connection.get_services_summary = AsyncMock(
        return_value={"web01": ServicesSummary(critical=1)}
    )
    mock_connection.get_hosts_services_summaries = AsyncMock(side_effect=OSError)
    map_cfg = _map(
        [_obj("h", host_name="web01", recognize_services=True, exclude_members="^Backup")]
    )

    state = asyncio.run(get_map_states(map_cfg)).states[0]

    assert state.state == "UP"
    assert state.stale is True


def test_dynamic_host_group_counts_its_services_only_where_asked(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    # One state per call: the resolver stamps the object id onto what it gets.
    mock_connection.get_dyngroup_state = AsyncMock(
        side_effect=lambda *_args, **_kwargs: ObjectState(
            object_id="", type="dyngroup", state="UP", services_summary=ServicesSummary(warning=1)
        )
    )
    group = {"object_types": "host", "object_filter": "Filter: groups >= web\n"}
    map_cfg = _map(
        [
            _obj("hosts", "dyngroup", recognize_services=False, only_hard_states=True, **group),
            _obj("services", "dyngroup", recognize_services=True, **group),
        ]
    )

    result = asyncio.run(get_map_states(map_cfg))

    assert {s.object_id: s.state for s in result.states} == {"hosts": "UP", "services": "WARNING"}
    mock_connection.get_dyngroup_state.assert_any_await(
        "host", "Filter: groups >= web\n", only_hard=True, with_services=False
    )
    mock_connection.get_dyngroup_state.assert_any_await(
        "host", "Filter: groups >= web\n", only_hard=False, with_services=True
    )


def test_line_shows_the_state_of_its_host_group(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.get_hostgroup_states = AsyncMock(
        return_value=ObjectState(
            object_id="x",
            type="hostgroup",
            state="UP",
            services_summary=ServicesSummary(ok=3, critical=1),
        )
    )
    map_cfg = _map(
        [
            _obj(
                "l1",
                "line",
                line_object_type="hostgroup",
                group_name="web",
                recognize_services=True,
            )
        ]
    )

    result = asyncio.run(get_map_states(map_cfg))

    assert (result.states[0].object_id, result.states[0].state) == ("l1", "CRITICAL")


def test_line_shows_the_worst_state_of_its_map(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    inner = _map([_obj("h_inner", "host", host_name="srv-down")], name="inner")
    monkeypatch.setattr(map_service, "get_map", lambda _owner, name="": {"inner": inner}.get(name))
    mock_connection.get_hosts_states = AsyncMock(
        return_value={"srv-down": ObjectState(object_id="h_inner", type="host", state="DOWN")}
    )
    outer = _map([_obj("l1", "line", line_object_type="map", map_name="inner")], name="outer")

    result = asyncio.run(get_map_states(outer))

    assert {s.object_id: s.state for s in result.states}["l1"] == "DOWN"


@pytest.mark.parametrize(
    "binding, expected",
    [
        pytest.param({"host_name": "web01"}, "DOWN", id="host"),
        pytest.param({"host_name": "web01", "service_description": "CPU"}, "WARNING", id="service"),
    ],
)
def test_line_without_object_type_shows_its_host_or_service(
    mock_connection: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
    binding: dict[str, str],
    expected: str,
) -> None:
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})
    mock_connection.get_hosts_states = AsyncMock(
        return_value={"web01": ObjectState(object_id="x", type="host", state="DOWN")}
    )
    mock_connection.get_services_states = AsyncMock(
        return_value={("web01", "CPU"): ObjectState(object_id="x", type="service", state="WARNING")}
    )

    result = asyncio.run(get_map_states(_map([_obj("l1", "line", **binding)])))

    assert result.states[0].state == expected


def test_line_bound_to_nothing_stays_a_line(
    mock_connection: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(state_service, "_connections", {"mock": mock_connection})

    result = asyncio.run(get_map_states(_map([_obj("l1", "line", x2=10, y2=10)])))

    assert (result.states[0].type, result.states[0].state) == ("line", "PENDING")


def _timed(object_id: str, state: str, *, last: float, nxt: float, attempt: int = 1) -> ObjectState:
    return ObjectState(
        object_id=object_id,
        type="host",
        state=state,
        last_check=last,
        next_check=nxt,
        current_attempt=attempt,
    )


def test_states_delta_first_call_is_full_without_timing() -> None:
    the_map = "timing-map-1"
    state_service.drop_states_snapshot(the_map)
    cur = [_timed("h1", "UP", last=10, nxt=70)]

    to_send, removed, full, timing = state_service.compute_states_delta(the_map, None, cur)

    assert full is True
    assert to_send == cur
    assert removed == []
    assert timing == []  # full send already carries timing inside the state
    state_service.drop_states_snapshot(the_map)


def test_states_delta_timing_only_change_rides_slim_patch() -> None:
    the_map = "timing-map-2"
    state_service.drop_states_snapshot(the_map)
    state_service.compute_states_delta(the_map, None, [_timed("h1", "UP", last=10, nxt=70)])

    # Same operational state, only the check times moved forward (SmartPing).
    to_send, removed, full, timing = state_service.compute_states_delta(
        the_map, None, [_timed("h1", "UP", last=70, nxt=130)]
    )

    assert full is False
    assert removed == []
    assert to_send == []  # no full re-send
    assert [t.object_id for t in timing] == ["h1"]
    assert timing[0].next_check == 130
    assert timing[0].last_check == 70
    state_service.drop_states_snapshot(the_map)


def test_states_delta_operational_change_carries_timing_inline() -> None:
    the_map = "timing-map-3"
    state_service.drop_states_snapshot(the_map)
    state_service.compute_states_delta(the_map, None, [_timed("h1", "UP", last=10, nxt=70)])

    # State flipped *and* timing moved: object is in to_send, so it must not
    # also appear in the slim timing list.
    to_send, removed, full, timing = state_service.compute_states_delta(
        the_map, None, [_timed("h1", "DOWN", last=70, nxt=130)]
    )

    assert [s.object_id for s in to_send] == ["h1"]
    assert full is False
    assert removed == []
    assert timing == []
    state_service.drop_states_snapshot(the_map)


def test_states_delta_resends_a_group_whose_host_counts_change() -> None:
    the_map = "timing-map-hosts"
    state_service.drop_states_snapshot(the_map)

    def group(down: int) -> ObjectState:
        return ObjectState(
            object_id="hg",
            type="hostgroup",
            state="DOWN",
            hosts_summary=ServicesSummary(ok=2, critical=down),
        )

    state_service.compute_states_delta(the_map, None, [group(1)])
    to_send, _removed, _full, _timing = state_service.compute_states_delta(
        the_map, None, [group(2)]
    )

    assert [s.object_id for s in to_send] == ["hg"]
    state_service.drop_states_snapshot(the_map)


def test_states_delta_no_change_sends_nothing() -> None:
    the_map = "timing-map-4"
    state_service.drop_states_snapshot(the_map)
    state_service.compute_states_delta(the_map, None, [_timed("h1", "UP", last=10, nxt=70)])

    to_send, removed, full, timing = state_service.compute_states_delta(
        the_map, None, [_timed("h1", "UP", last=10, nxt=70)]
    )

    assert full is False
    assert to_send == []
    assert removed == []
    assert timing == []
    state_service.drop_states_snapshot(the_map)


# ---------------------------------------------------------------------------
# Topology SSE delta — compute_topology_delta
# ---------------------------------------------------------------------------


def _topo_node(name: str, **kwargs: object) -> TopologyNode:
    """A TopologyNode with sensible defaults for diff tests."""
    return TopologyNode.model_validate(
        {"parents": [], "state": "UP", "output": "ok", "name": name, **kwargs}
    )


@pytest.fixture
def _clear_topology_snapshots() -> Iterator[None]:
    state_service._topology_snapshots.clear()  # noqa: SLF001
    state_service._topology_timing_snapshots.clear()  # noqa: SLF001
    yield
    state_service._topology_snapshots.clear()  # noqa: SLF001
    state_service._topology_timing_snapshots.clear()  # noqa: SLF001


def test_topology_delta_first_call_is_full() -> None:
    nodes = [_topo_node("h1"), _topo_node("h2")]
    delta = state_service.compute_topology_delta("b1", None, nodes)
    assert delta.full is True
    assert {n.name for n in delta.added} == {"h1", "h2"}
    assert delta.changed == [] and delta.removed == []


def test_topology_delta_no_changes_returns_empty_lists() -> None:
    nodes = [_topo_node("h1"), _topo_node("h2")]
    state_service.compute_topology_delta("b1", None, nodes)
    delta = state_service.compute_topology_delta("b1", None, nodes)
    assert delta.full is False
    assert delta.added == [] and delta.changed == [] and delta.removed == []


def test_topology_delta_detects_added_host() -> None:
    state_service.compute_topology_delta("b1", None, [_topo_node("h1")])
    delta = state_service.compute_topology_delta("b1", None, [_topo_node("h1"), _topo_node("h2")])
    assert [n.name for n in delta.added] == ["h2"]
    assert delta.changed == [] and delta.removed == []


def test_topology_delta_store_false_does_not_persist_snapshot() -> None:
    # A one-off full for a single joining subscriber must not overwrite the shared
    # snapshot, so the group's already-connected viewers keep diffing against the
    # last real tick (no group-wide re-full on a reconnect).
    state_service.compute_topology_delta("b1", None, [_topo_node("h1", state="UP")])
    full = state_service.compute_topology_delta(
        "b1", None, [_topo_node("h1", state="DOWN")], force_full=True, store=False
    )
    assert full.full is True
    # The next real tick therefore still diffs against the UP snapshot and sees
    # the DOWN change — proving the store=False call left the snapshot untouched.
    delta = state_service.compute_topology_delta("b1", None, [_topo_node("h1", state="DOWN")])
    assert delta.full is False
    assert [n.name for n in delta.changed] == ["h1"]


def test_topology_delta_detects_changed_volatile_field() -> None:
    state_service.compute_topology_delta("b1", None, [_topo_node("h1", state="UP", output="ok")])
    delta = state_service.compute_topology_delta(
        "b1", None, [_topo_node("h1", state="DOWN", output="boom")]
    )
    assert [n.name for n in delta.changed] == ["h1"]
    assert delta.added == [] and delta.removed == []


def test_topology_delta_emits_timing_patch_on_recheck_only() -> None:
    # A re-check bumps next_check/last_check/current_attempt but nothing else.
    # That must NOT mark the host as `changed` (would defeat the delta) — it
    # travels as a slim `timing` patch so the Flow Map's next-check stays live.
    state_service.compute_topology_delta(
        "b1", None, [_topo_node("h1", last_check=100.0, next_check=160.0, current_attempt=1)]
    )
    delta = state_service.compute_topology_delta(
        "b1", None, [_topo_node("h1", last_check=160.0, next_check=220.0, current_attempt=1)]
    )
    assert delta.changed == [] and delta.added == [] and delta.removed == []
    assert [t.name for t in delta.timing] == ["h1"]
    assert delta.timing[0].next_check == 220.0
    assert delta.timing[0].last_check == 160.0


def test_topology_delta_changed_host_not_also_in_timing() -> None:
    state_service.compute_topology_delta(
        "b1", None, [_topo_node("h1", state="UP", next_check=160.0)]
    )
    delta = state_service.compute_topology_delta(
        "b1", None, [_topo_node("h1", state="DOWN", next_check=220.0)]
    )
    assert [n.name for n in delta.changed] == ["h1"]
    assert delta.timing == []


def test_topology_delta_timing_patch_tracks_service_recheck() -> None:
    def node(svc_next: float) -> TopologyNode:
        return _topo_node(
            "h1",
            services=[ServiceNode(name="CPU", state="OK", output="ok", next_check=svc_next)],
        )

    state_service.compute_topology_delta("b1", None, [node(160.0)])
    delta = state_service.compute_topology_delta("b1", None, [node(220.0)])
    assert delta.changed == []
    assert [t.name for t in delta.timing] == ["h1"]
    assert delta.timing[0].services[0].name == "CPU"
    assert delta.timing[0].services[0].next_check == 220.0


def test_topology_delta_detects_removed_host() -> None:
    state_service.compute_topology_delta("b1", None, [_topo_node("h1"), _topo_node("h2")])
    delta = state_service.compute_topology_delta("b1", None, [_topo_node("h1")])
    assert delta.removed == ["h2"]
    assert delta.added == [] and delta.changed == []


def test_topology_delta_ignores_stable_field_change() -> None:
    # alias is metadata, not a volatile field — changing it must not trigger a delta.
    state_service.compute_topology_delta("b1", None, [_topo_node("h1", alias="old")])
    delta = state_service.compute_topology_delta("b1", None, [_topo_node("h1", alias="new")])
    assert delta.added == [] and delta.changed == [] and delta.removed == []


def test_topology_delta_force_full_resends_everything() -> None:
    nodes = [_topo_node("h1"), _topo_node("h2")]
    state_service.compute_topology_delta("b1", None, nodes)
    delta = state_service.compute_topology_delta("b1", None, nodes, force_full=True)
    assert delta.full is True
    assert {n.name for n in delta.added} == {"h1", "h2"}


def test_topology_delta_per_user_isolation() -> None:
    # Different auth_users see different host sets — snapshots must not collide.
    state_service.compute_topology_delta("b1", "alice", [_topo_node("h1")])
    state_service.compute_topology_delta("b1", "bob", [_topo_node("h2")])
    delta_bob = state_service.compute_topology_delta("b1", "bob", [_topo_node("h2")])
    assert delta_bob.full is False
    assert delta_bob.added == [] and delta_bob.changed == [] and delta_bob.removed == []


def test_drop_topology_snapshot_clears_all_users_for_map() -> None:
    state_service.compute_topology_delta("b1", "alice", [_topo_node("h1")])
    state_service.compute_topology_delta("b1", "bob", [_topo_node("h2")])
    state_service.compute_topology_delta("b2", None, [_topo_node("h3")])
    state_service.drop_topology_snapshot("b1")
    assert all(k[0] != "b1" for k in state_service._topology_snapshots)  # noqa: SLF001
    assert ("b2", None) in state_service._topology_snapshots  # noqa: SLF001


# ---------------------------------------------------------------------------
# Folder-tree SSE delta — compute_folder_tree_delta
# ---------------------------------------------------------------------------


def _ftn(
    path: str,
    kind: Literal["folder", "host", "service"],
    state: str,
    children: list[FolderTreeNode] | None = None,
    **kw: object,
) -> FolderTreeNode:
    return FolderTreeNode.model_validate(
        {
            "path": path,
            "title": path or "Main",
            "kind": kind,
            "state": state,
            "children": children or [],
            **kw,
        }
    )


def _ftree(*hosts: tuple[str, str]) -> FolderTreeNode:
    # Root folder "f" with the given (host_name, state) leaves, in argument order.
    kids = [_ftn(f"f/{h}", "host", st, host_count=1) for h, st in hosts]
    problems = sum(1 for _, st in hosts if st in ("DOWN", "CRITICAL", "WARNING"))
    return _ftn("f", "folder", "CRITICAL" if problems else "OK", kids, problem_count=problems)


def test_folder_tree_delta_first_tick_is_full() -> None:
    state_service.drop_states_snapshot("ftd")
    tree = _ftree(("h1", "UP"), ("h2", "UP"))
    d = state_service.compute_folder_tree_delta("ftd", None, tree)
    assert d.full and d.tree is not None
    # Identical second tick → not full, nothing changed.
    d2 = state_service.compute_folder_tree_delta("ftd", None, _ftree(("h1", "UP"), ("h2", "UP")))
    assert not d2.full and d2.changed == []
    state_service.drop_states_snapshot("ftd")


def test_folder_tree_delta_field_change_patches_host_and_parent() -> None:
    state_service.drop_states_snapshot("ftd2")
    state_service.compute_folder_tree_delta("ftd2", None, _ftree(("h1", "UP"), ("h2", "UP")))
    # h1 flips to DOWN → its node + the bubbled parent folder change.
    d = state_service.compute_folder_tree_delta("ftd2", None, _ftree(("h1", "DOWN"), ("h2", "UP")))
    assert not d.full
    changed = {p.path: p for p in d.changed}
    assert "f/h1" in changed and changed["f/h1"].state == "DOWN"
    assert "f" in changed  # parent folder problem_count bubbled
    assert "f/h2" not in changed  # untouched sibling not resent
    state_service.drop_states_snapshot("ftd2")


def test_folder_tree_delta_reorder_carries_children_order() -> None:
    state_service.drop_states_snapshot("ftd3")
    state_service.compute_folder_tree_delta("ftd3", None, _ftree(("h1", "UP"), ("h2", "UP")))
    reordered = _ftn(
        "f",
        "folder",
        "CRITICAL",
        [_ftn("f/h2", "host", "DOWN", host_count=1), _ftn("f/h1", "host", "UP", host_count=1)],
        problem_count=1,
    )
    d = state_service.compute_folder_tree_delta("ftd3", None, reordered)
    assert not d.full
    root_patch = next(p for p in d.changed if p.path == "f")
    assert root_patch.children_order == ["f/h2", "f/h1"]
    state_service.drop_states_snapshot("ftd3")


def test_folder_tree_delta_structural_change_is_full() -> None:
    state_service.drop_states_snapshot("ftd4")
    state_service.compute_folder_tree_delta("ftd4", None, _ftree(("h1", "UP")))
    # A new host appears → path set changes → full resend.
    d = state_service.compute_folder_tree_delta("ftd4", None, _ftree(("h1", "UP"), ("h2", "UP")))
    assert d.full and d.tree is not None
    state_service.drop_states_snapshot("ftd4")


def test_folder_tree_delta_ignores_output_drift() -> None:
    def _tree(state: str = "OK", output: str = "rta 0.1ms") -> FolderTreeNode:
        return _ftn(
            "dc",
            "folder",
            state,
            [FolderTreeNode(path="dc/h1", title="h1", kind="host", state=state, output=output)],
        )

    state_service.drop_states_snapshot("ftsig")
    assert state_service.compute_folder_tree_delta("ftsig", None, _tree()).full is True
    # Same structure → no changes.
    assert state_service.compute_folder_tree_delta("ftsig", None, _tree()).changed == []
    # Output drift alone must NOT force a resend (output is excluded from the sig).
    assert (
        state_service.compute_folder_tree_delta("ftsig", None, _tree(output="rta 9.9ms")).changed
        == []
    )
    # A real state change does.
    d = state_service.compute_folder_tree_delta("ftsig", None, _tree(state="CRITICAL"))
    assert any(p.path == "dc/h1" for p in d.changed)
    state_service.drop_states_snapshot("ftsig")


# ---------------------------------------------------------------------------
# Folder-tree build via the real FakeConnection (_build_folder_tree path)
# ---------------------------------------------------------------------------


def _folder_map(view_kwargs: dict[str, object] | None = None) -> MapConfig:
    from cmk.maps.backend.schemas.map import FolderTreeView

    return MapConfig(
        name="ft",
        alias="FT",
        connection_id="test",
        view=FolderTreeView.model_validate(view_kwargs or {}),
        objects=[],
    )


def _find_node(node: FolderTreeNode, path: str) -> FolderTreeNode | None:
    if node.path == path:
        return node
    for child in node.children:
        found = _find_node(child, path)
        if found is not None:
            return found
    return None


@pytest.fixture
def test_conn(monkeypatch: pytest.MonkeyPatch) -> FakeConnection:
    conn = FakeConnection()
    monkeypatch.setattr(state_service, "_connections", {"test": conn})
    return conn


def test_foldertree_builds_tree_with_empty_folders(test_conn: FakeConnection) -> None:  # noqa: ARG001
    result = asyncio.run(get_map_states(_folder_map()))
    tree = result.folder_tree
    assert tree is not None and tree.path == ""
    muc = _find_node(tree, "datacenters/muc")
    assert muc is not None and muc.kind == "folder" and muc.host_count == 2
    staging = _find_node(tree, "staging")
    assert staging is not None and staging.is_empty and staging.state == "EMPTY"
    dc = _find_node(tree, "datacenters")
    assert dc is not None and not dc.is_empty
    # Empty folder is excluded from the root's worst-state.
    assert tree.state != "EMPTY"


def test_foldertree_severity_counts_bubble_by_host_state(test_conn: FakeConnection) -> None:  # noqa: ARG001
    result = asyncio.run(get_map_states(_folder_map()))
    tree = result.folder_tree
    assert tree is not None
    dc = _find_node(tree, "datacenters")
    muc = _find_node(tree, "datacenters/muc")
    assert dc is not None and muc is not None
    for node in (tree, dc, muc):
        assert sum(node.severity_counts.values()) == node.problem_count
        assert all(SEVERITY_RANK.get(s, 0) > 0 for s in node.severity_counts)
    # OK/UP hosts are not counted; service leaves never feed the breakdown.
    assert "OK" not in muc.severity_counts and "UP" not in muc.severity_counts


def test_foldertree_hide_empty_folders(test_conn: FakeConnection) -> None:  # noqa: ARG001
    result = asyncio.run(get_map_states(_folder_map({"show_empty_folders": False})))
    tree = result.folder_tree
    assert tree is not None
    assert _find_node(tree, "staging") is None
    assert _find_node(tree, "decommissioned") is None
    assert _find_node(tree, "datacenters/muc") is not None


def test_foldertree_prunes_unpermitted_empty_folders(
    test_conn: FakeConnection, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A scoped user must not see SETUP folder names they have no access to.

    Empty folders the user can't read (``permitted=False``) are pruned even with
    ``show_empty_folders`` on; an empty *permitted* folder is kept, and a folder
    that contains a visible host is kept regardless of its own permission flag.
    """

    async def _fake_folder_tree(
        *,
        only_hard: bool = False,  # noqa: ARG001
        sites: list[str] | None = None,  # noqa: ARG001
    ) -> FolderTreeData:
        return FolderTreeData(
            folders=[
                {"path": "", "title": "Main", "permitted": True},
                {"path": "secret", "title": "Secret", "permitted": False},
                {"path": "shared", "title": "Shared", "permitted": True},
                {"path": "withhost", "title": "WithHost", "permitted": False},
            ],
            hosts=[
                {
                    "host_name": "h1",
                    "folder_path": "withhost",
                    "state": "UP",
                    "output": "",
                    "site_id": "central",
                }
            ],
        )

    monkeypatch.setattr(test_conn, "get_folder_tree", _fake_folder_tree)
    result = asyncio.run(get_map_states(_folder_map({"show_empty_folders": True})))
    tree = result.folder_tree
    assert tree is not None
    # Empty + not permitted → hidden, even though show_empty_folders is on.
    assert _find_node(tree, "secret") is None
    # Empty + permitted → shown (respects show_empty_folders).
    assert _find_node(tree, "shared") is not None
    # Has a visible host → shown regardless of its own permission flag.
    wh = _find_node(tree, "withhost")
    assert wh is not None and wh.host_count == 1


def test_foldertree_sites_filter(test_conn: FakeConnection) -> None:  # noqa: ARG001
    result = asyncio.run(get_map_states(_folder_map({"sites": ["central"]})))
    tree = result.folder_tree
    assert tree is not None
    # Frankfurt only had a remote_fra host → no longer populated.
    fra = _find_node(tree, "datacenters/fra")
    assert fra is None or fra.is_empty
    muc = _find_node(tree, "datacenters/muc")
    assert muc is not None and muc.host_count == 2
    # Foldertree maps carry hosts only as tree nodes — assert the site filter
    # on the leaf nodes themselves.
    hosts: list[FolderTreeNode] = []

    def _collect_hosts(n: FolderTreeNode) -> None:
        if n.kind == "host":
            hosts.append(n)
        for c in n.children:
            _collect_hosts(c)

    _collect_hosts(tree)
    assert hosts and all(h.site_id == "central" for h in hosts)


def test_foldertree_root_scoping(test_conn: FakeConnection) -> None:  # noqa: ARG001
    result = asyncio.run(get_map_states(_folder_map({"root_folder": "network"})))
    tree = result.folder_tree
    assert tree is not None and tree.path == "network"
    # Subtree only — datacenters not reachable from this root.
    assert _find_node(tree, "datacenters") is None


def test_foldertree_show_services_is_not_eager(test_conn: FakeConnection) -> None:  # noqa: ARG001
    # show_services must NOT materialise service leaves into the SSE tree.
    result = asyncio.run(get_map_states(_folder_map({"show_services": True})))
    assert result.folder_tree is not None
    host = _find_node(result.folder_tree, "datacenters/muc/localhost")
    assert host is not None and host.kind == "host"
    assert not host.children, "show_services must not eagerly attach service leaves"


def test_foldertree_no_services_by_default(test_conn: FakeConnection) -> None:  # noqa: ARG001
    result = asyncio.run(get_map_states(_folder_map()))
    assert result.folder_tree is not None
    host = _find_node(result.folder_tree, "datacenters/muc/localhost")
    assert host is not None and not host.children
