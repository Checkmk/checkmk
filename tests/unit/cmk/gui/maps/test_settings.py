#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Reads of the effective Maps configuration.

The authoring defaults are two FormSpec ``Dictionary`` globals;
:mod:`cmk.maps.gui._settings` flattens their (nested, tuple-based) WATO storage
shape into the flat dict the SPA consumes. These pin that flatten — the shape
WATO writes is captured verbatim — plus the connection-choice and
monitoring-core lookups the form specs seed their defaults from.
"""

import pytest

from cmk.maps.gui import _settings
from cmk.maps.gui._config_domain import (
    CONFIG_VAR_MAP_DEFAULTS,
    CONFIG_VAR_OBJECT_DEFAULTS,
    ConfigDomainMaps,
)
from cmk.maps.rest_api.internal.models.response_models import MapsAuthoringSettings

# Captured verbatim from a real WATO "Save": ``default_map_type`` and ``labels``
# are stored as TUPLEs (CascadingSingleChoice), ``background`` too.
WATO_MAP_DEFAULTS = {
    "default_backend_id": "cmk_main",
    "default_map_type": ("static", None),
    "default_render_mode": "default",
}
WATO_OBJECT_DEFAULTS = {
    "icon_size": 30,
    "labels": ("shown", {"background": ("transparent", None), "color": "#ffffff", "size": 11}),
    "line_style": "plain",
    "url_target": "_blank",
    "view_type": "icon",
}


def test_flatten_merges_map_and_object() -> None:
    g = _settings._flatten(WATO_MAP_DEFAULTS, WATO_OBJECT_DEFAULTS)  # noqa: SLF001
    assert g["default_backend_id"] == "cmk_main"
    assert g["default_map_type"] == "static"
    assert g["icon_size"] == 30
    assert g["line_style"] == "plain"
    assert g["label_show"] is True
    assert g["label_color"] == "#ffffff"
    assert g["label_background"] == "transparent"
    assert g["label_size"] == 11


def test_flatten_geo_map_carries_tile_url() -> None:
    map_form = {
        **WATO_MAP_DEFAULTS,
        "default_map_type": ("worldmap", {"tile_url": "https://t/{z}"}),
    }
    g = _settings._flatten(map_form, WATO_OBJECT_DEFAULTS)  # noqa: SLF001
    assert g["default_map_type"] == "worldmap"
    assert g["default_tile_url"] == "https://t/{z}"


def test_flatten_non_geo_has_no_tile_url() -> None:
    g = _settings._flatten(WATO_MAP_DEFAULTS, WATO_OBJECT_DEFAULTS)  # noqa: SLF001
    assert g["default_map_type"] == "static"
    assert g["default_tile_url"] is None


def test_flatten_solid_colour_background() -> None:
    labels = ("shown", {"background": ("color", "#112233"), "color": "#ffffff", "size": 11})
    g = _settings._flatten(WATO_MAP_DEFAULTS, {**WATO_OBJECT_DEFAULTS, "labels": labels})  # noqa: SLF001
    assert g["label_background"] == "#112233"


def test_flatten_hidden_labels() -> None:
    g = _settings._flatten(WATO_MAP_DEFAULTS, {**WATO_OBJECT_DEFAULTS, "labels": ("hidden", None)})  # noqa: SLF001
    assert g["label_show"] is False


def test_flatten_tolerates_missing_forms() -> None:
    g = _settings._flatten(WATO_MAP_DEFAULTS, {})  # noqa: SLF001
    assert g["default_backend_id"] == "cmk_main"
    assert g["icon_size"] == _settings._FLAT_DEFAULTS["icon_size"]  # noqa: SLF001


def test_flatten_backend_id_falls_back_to_local_connection() -> None:
    # A map form without an explicit connection resolves to the seeded local
    # connection (cmk_<site>), never the legacy "live_1" that exists on no site.
    g = _settings._flatten({}, WATO_OBJECT_DEFAULTS)  # noqa: SLF001
    assert g["default_backend_id"].startswith("cmk_")
    assert g["default_backend_id"] != "live_1"


def test_flatten_malformed_labels_keeps_defaults() -> None:
    # A bad ``labels`` value must not crash — it just keeps the label defaults.
    g = _settings._flatten({}, {"labels": "nope"})  # noqa: SLF001
    assert g["label_show"] == _settings._FLAT_DEFAULTS["label_show"]  # noqa: SLF001


def test_map_object_defaults_reads_the_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ConfigDomainMaps, "default_globals", lambda self: {}, raising=True)  # noqa: ARG005
    monkeypatch.setattr(
        ConfigDomainMaps,
        "load",
        lambda self, **kw: {  # noqa: ARG005
            CONFIG_VAR_MAP_DEFAULTS: WATO_MAP_DEFAULTS,
            CONFIG_VAR_OBJECT_DEFAULTS: WATO_OBJECT_DEFAULTS,
        },
        raising=True,
    )
    g = _settings.map_object_defaults()
    assert g["default_backend_id"] == "cmk_main"
    assert g["icon_size"] == 30


def _with_tile_url(monkeypatch: pytest.MonkeyPatch, tile_url: str | None) -> None:
    defaults = {**_settings._FLAT_DEFAULTS, "default_tile_url": tile_url}  # noqa: SLF001
    monkeypatch.setattr(_settings, "map_object_defaults", lambda: defaults)


def test_tile_csp_sources_allows_openstreetmap_without_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _with_tile_url(monkeypatch, None)
    assert _settings.tile_csp_sources() == ["https://tile.openstreetmap.org/"]


@pytest.mark.parametrize(
    ("tile_url", "expected"),
    [
        pytest.param(
            "https://tiles.internal:8443/{z}/{x}/{y}.png",
            "https://tiles.internal:8443/",
            id="host-and-port",
        ),
        # Leaflet expands {s} into a subdomain, so the source has to be a wildcard.
        pytest.param(
            "https://{s}.basemaps.example.com/dark/{z}/{x}/{y}.png",
            "https://*.basemaps.example.com/",
            id="subdomain-placeholder",
        ),
    ],
)
def test_tile_csp_sources_adds_the_configured_server(
    monkeypatch: pytest.MonkeyPatch, tile_url: str, expected: str
) -> None:
    _with_tile_url(monkeypatch, tile_url)
    assert _settings.tile_csp_sources() == ["https://tile.openstreetmap.org/", expected]


@pytest.mark.parametrize(
    "tile_url",
    [
        pytest.param("javascript:alert(1)", id="unusable-scheme"),
        pytest.param("/local/{z}/{x}/{y}.png", id="no-host"),
        # A source expression with whitespace/";" would make add_csp_source raise
        # and take the whole page down — such a global is dropped instead.
        pytest.param("https://evil one;/{z}/{x}/{y}.png", id="not-a-host"),
    ],
)
def test_tile_csp_sources_drops_an_unusable_global(
    monkeypatch: pytest.MonkeyPatch, tile_url: str
) -> None:
    _with_tile_url(monkeypatch, tile_url)
    assert _settings.tile_csp_sources() == ["https://tile.openstreetmap.org/"]


def test_connection_choices_maps_id_and_label(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        _settings,
        "effective_settings",
        lambda: {
            "maps_connections": [
                {"id": "cmk_heute", "label": "Local"},
                {"id": "no_label"},  # label falls back to the id
                {"label": "orphan-without-id"},  # skipped (no id)
                "not-a-dict",  # skipped
            ]
        },
    )
    assert _settings.connection_choices() == [("cmk_heute", "Local"), ("no_label", "no_label")]


def test_connection_choices_tolerates_non_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_settings, "effective_settings", lambda: {"maps_connections": "broken"})
    assert _settings.connection_choices() == []


@pytest.mark.parametrize(
    ("config_core", "expected"),
    [
        pytest.param("cmc", "cmc", id="cmc"),
        pytest.param("nagios", "nagios", id="nagios"),
        pytest.param("something-else", None, id="unknown-core"),
    ],
)
def test_monitoring_core_reads_config_core(
    monkeypatch: pytest.MonkeyPatch, config_core: str, expected: str | None
) -> None:
    monkeypatch.setattr(_settings, "get_omd_config", lambda _root: {"CONFIG_CORE": config_core})
    assert _settings.monitoring_core() == expected


def test_monitoring_core_fails_safe_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(_root: object) -> dict[str, str]:
        raise OSError("no site.conf")

    monkeypatch.setattr(_settings, "get_omd_config", _raise)
    assert _settings.monitoring_core() is None


def test_rest_model_covers_every_authoring_default() -> None:
    """The SPA reads these defaults over REST, so the endpoint must carry them all.

    ``MapsAuthoringSettings`` is built by splatting ``AuthoringDefaults``, so a
    field added on one side and not the other is either a TypeError at runtime or
    a value the editor silently never sees. Pin the two shapes together instead.
    """
    assert set(MapsAuthoringSettings.__dataclass_fields__) == set(
        _settings.AuthoringDefaults.__annotations__
    )
