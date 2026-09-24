#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Reads of the effective Maps configuration.

Everything the GUI needs to know about *what is configured* — the authoring
defaults that seed the SPA editor, the daemon's runtime knobs, the configured
connections and the local site's monitoring core. The values live in the
feature's own :class:`ConfigDomainMaps` globals (plus the site's ``CONFIG_CORE``
for the core); this module resolves them and hands out the shapes the callers
need. Rendering those shapes into forms is :mod:`cmk.maps.gui._form_schemas`'
job, not this module's.

The authoring defaults are stored as two FormSpec ``Dictionary`` globals
(``maps_map_defaults`` / ``maps_object_defaults``) and flattened here into the
shape the SPA consumes (the frontend ``GlobalSettings`` type). The GUI is the
sole owner of both the values and the flat shape now — the previous daemon
round-trip (``/api/v1/settings``) is gone.
"""

import re
from collections.abc import Mapping
from typing import get_args, Literal, TypedDict
from urllib.parse import urlsplit

from cmk.ccc.site import get_omd_config, omd_site
from cmk.gui.type_defs import GlobalSettings
from cmk.maps.gui._config_domain import (
    CONFIG_VAR_CONNECTIONS,
    CONFIG_VAR_MAP_DEFAULTS,
    CONFIG_VAR_OBJECT_DEFAULTS,
    ConfigDomainMaps,
)
from cmk.maps.shared.map_payload import LineStyle
from cmk.utils import paths

# Clamped by the flatten below (an unknown stored value falls back), so these
# are real domains rather than documentation — the REST model and the SPA's
# generated types narrow to them.
RenderMode = Literal["default", "nagvis_classic"]
MapListView = Literal["cards", "table"]


class AuthoringDefaults(TypedDict):
    """The flat map/object authoring defaults the SPA editor seeds itself from.

    The frontend ``GlobalSettings`` type; the daemon never reads it. The nested,
    tuple-based WATO storage shape of the two FormSpec globals is flattened into
    this by :func:`_flatten`.
    """

    icon_size: int
    view_type: str
    url_target: str
    z: int
    line_style: LineStyle
    label_show: bool
    label_size: int
    label_color: str
    label_background: str
    hover_template: str | None
    context_template: str | None
    default_backend_id: str
    default_map_type: str
    default_render_mode: RenderMode
    default_tile_url: str | None
    # Per-operator localStorage overrides this client-side.
    map_list_view: MapListView


# Factory defaults for every flat field the SPA reads. A field missing from the
# stored FormSpec value falls back to these.
_FLAT_DEFAULTS: AuthoringDefaults = {
    # Object appearance
    "icon_size": 30,
    "view_type": "icon",
    "url_target": "_blank",
    "z": 1,
    "line_style": "plain",
    # Object labels
    "label_show": True,
    "label_size": 11,
    "label_color": "#ffffff",
    "label_background": "transparent",
    # Object templates
    "hover_template": None,
    "context_template": None,
    # New-map defaults. ``default_backend_id`` is resolved site-aware in
    # ``_flatten`` (the default connection is ``cmk_<site>``); the empty base here
    # is always overridden.
    "default_backend_id": "",
    "default_map_type": "static",
    "default_render_mode": "default",
    "default_tile_url": None,
    # Home overview layout (per-operator localStorage overrides this client-side).
    "map_list_view": "cards",
}


def _optional_text(value: object) -> str | None:
    """A template/URL field: a non-empty string, else None."""
    return value if isinstance(value, str) and value else None


def _line_style(value: object, fallback: LineStyle) -> LineStyle:
    """The stored value comes from a fixed-choice FormSpec, but a hand-edited or
    outdated global can still hold something else — fall back rather than let it
    reach the SPA as a style nothing renders."""
    styles: tuple[LineStyle, ...] = get_args(LineStyle)
    for style in styles:
        if value == style:
            return style
    return fallback


def _int_or(value: object, fallback: int) -> int:
    """A numeric FormSpec field, keeping *fallback* for anything non-numeric."""
    return (
        int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else fallback
    )


class _LabelDefaults(TypedDict):
    """The flat label fields the ``labels`` cascade contributes."""

    label_show: bool
    label_size: int
    label_color: str
    label_background: str


def _labels_from(object_form: Mapping[str, object], fallback: _LabelDefaults) -> _LabelDefaults:
    """Unpack the ``labels`` CascadingSingleChoice (``("shown"|"hidden", payload)``).

    An unset/unknown cascade keeps *fallback* wholesale, and the "hidden" branch
    carries no payload — it only flips ``label_show`` off, so size/color stay at
    the factory values.
    """
    out: _LabelDefaults = {**fallback}
    labels = object_form.get("labels")
    if not (isinstance(labels, (list, tuple)) and len(labels) == 2):
        return out
    kind, payload = labels
    if kind == "hidden":
        out["label_show"] = False
        return out
    if kind != "shown" or not isinstance(payload, dict):
        return out
    out["label_show"] = True
    out["label_size"] = int(payload.get("size", out["label_size"]))
    out["label_color"] = str(payload.get("color", out["label_color"]))
    # The background is itself a cascade: ("transparent", None) | ("color", "#…").
    bg = payload.get("background")
    if isinstance(bg, (list, tuple)) and len(bg) == 2:
        out["label_background"] = (
            "transparent" if bg[0] == "transparent" else str(bg[1] or "transparent")
        )
    elif isinstance(bg, str) and bg:
        out["label_background"] = bg
    return out


def _map_type_from(map_form: Mapping[str, object], fallback: str) -> tuple[str, str | None]:
    """Unpack ``default_map_type`` into (type, tile URL).

    A CascadingSingleChoice: (name, sub) where the "worldmap" branch carries
    ``{"tile_url": …}`` and the others carry ``None``. The tile URL is only
    meaningful for worldmap, so it stays ``None`` for every other type.
    """
    raw = map_form.get("default_map_type")
    if isinstance(raw, (list, tuple)) and len(raw) == 2:
        name, cfg = raw
    else:
        name, cfg = raw, None
    map_type = str(name) if name else fallback
    if map_type == "worldmap" and isinstance(cfg, dict):
        return map_type, _optional_text(cfg.get("tile_url"))
    return map_type, None


def _flatten(
    map_form: Mapping[str, object], object_form: Mapping[str, object]
) -> AuthoringDefaults:
    """Merge the map- and object-defaults FormSpec values into the flat shape.

    Either form may be empty (its global not configured) — missing fields keep the
    factory default. The two nested cascades are unpacked by :func:`_labels_from`
    and :func:`_map_type_from`; everything else here is a scalar.
    """
    out: AuthoringDefaults = {**_FLAT_DEFAULTS}
    labels = _labels_from(
        object_form,
        {
            "label_show": out["label_show"],
            "label_size": out["label_size"],
            "label_color": out["label_color"],
            "label_background": out["label_background"],
        },
    )
    out["label_show"] = labels["label_show"]
    out["label_size"] = labels["label_size"]
    out["label_color"] = labels["label_color"]
    out["label_background"] = labels["label_background"]

    # ── Object appearance / templates ──
    out["icon_size"] = _int_or(object_form.get("icon_size"), out["icon_size"])
    out["view_type"] = str(object_form.get("view_type", out["view_type"]))
    out["url_target"] = str(object_form.get("url_target", out["url_target"]))
    out["line_style"] = _line_style(object_form.get("line_style"), out["line_style"])
    out["hover_template"] = _optional_text(object_form.get("hover_template"))
    out["context_template"] = _optional_text(object_form.get("context_template"))

    # ── New-map defaults ──
    out["default_backend_id"] = str(map_form.get("default_backend_id") or f"cmk_{omd_site()}")
    out["default_map_type"], out["default_tile_url"] = _map_type_from(
        map_form, out["default_map_type"]
    )
    out["default_render_mode"] = (
        "nagvis_classic" if map_form.get("default_render_mode") == "nagvis_classic" else "default"
    )
    return out


def effective_settings() -> GlobalSettings:
    """Every Maps global with its effective value (stored value over factory default).

    The one read path for all four callers below. Going through the *domain* rather
    than the global ``load_configuration_settings()`` keeps the read symmetric with
    the write: WATO stores these variables in ``ConfigDomainMaps``' own
    ``maps.d/wato/global.mk`` (that is what ``primary_domain`` selects and what the
    ReplicationPath ships to the remotes), so reading the domain cannot drift from
    the file the daemon actually consumes. Layering ``default_globals()``
    underneath also keeps the defaults in one place — the domain — instead of
    re-hardcoding each one at the call site.
    """
    domain = ConfigDomainMaps()
    return {**domain.default_globals(), **domain.load()}


def map_object_defaults() -> AuthoringDefaults:
    """The flat map/object authoring defaults for the logged-in site.

    Reads the two FormSpec globals from :class:`ConfigDomainMaps` (stored value
    over factory default) and flattens them for the SPA."""
    stored = effective_settings()
    map_form = stored.get(CONFIG_VAR_MAP_DEFAULTS) or {}
    object_form = stored.get(CONFIG_VAR_OBJECT_DEFAULTS) or {}
    if not isinstance(map_form, Mapping) or not isinstance(object_form, Mapping):
        fallback: AuthoringDefaults = {**_FLAT_DEFAULTS}
        fallback["default_backend_id"] = f"cmk_{omd_site()}"
        return fallback
    return _flatten(map_form, object_form)


# The SPA's built-in tile server, as Leaflet's template and as the two CSP sources
# it can be reached under. The legacy site-wide policy already carries the
# ``*.tile.openstreetmap.org`` wildcard (NagVis' worldmap, werk 7825), but not the
# bare host the SPA defaults to; both are named here so one list answers "may the
# browser load these tiles" for the page policy and for the SPA alike.
_OSM_TILE_TEMPLATE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
_OSM_TILE_SOURCES = ["https://tile.openstreetmap.org/", "https://*.tile.openstreetmap.org/"]

# A CSP source expression has to be a bare scheme://host[:port]; ``add_csp_source``
# rejects anything else, and an unusable global must not take the page down with it.
_CSP_HOST = re.compile(r"^[A-Za-z0-9.\-*]+(?::[0-9]{1,5})?$")


def _csp_source(tile_url: str) -> str | None:
    """The CSP source a Leaflet tile template needs, or None if it has no usable one."""
    parsed = urlsplit(tile_url)
    host = parsed.netloc
    # Leaflet expands ``{s}`` into a subdomain, so the template host is not one.
    if host.startswith("{s}."):
        host = f"*.{host.removeprefix('{s}.')}"
    if parsed.scheme not in ("http", "https") or not _CSP_HOST.match(host):
        return None
    return f"{parsed.scheme}://{host}/"


def tile_csp_sources() -> list[str]:
    """The ``img-src`` sources the maps page must allow for geo-map tiles.

    The browser fetches tiles straight from the tile server, so the page policy —
    not the map config — decides which ones a geo map can reach. Without the
    configured server in here a site pointing its maps at an internal tile
    service just renders an empty canvas.
    """
    sources = list(_OSM_TILE_SOURCES)
    configured = map_object_defaults()["default_tile_url"]
    if configured and (source := _csp_source(configured)) and source not in sources:
        sources.append(source)
    return sources


def default_tile_template() -> str:
    """The tile template a worldmap that sets none of its own is drawn with.

    The site's configured server where there is one: a map created before it was
    configured must not keep fetching from openstreetmap.org on an air-gapped
    installation.
    """
    return map_object_defaults()["default_tile_url"] or _OSM_TILE_TEMPLATE


def connection_choices() -> list[tuple[str, str]]:
    """(id, label) for each connection configured in the ``maps_connections`` global.

    WATO owns the connections (ConfigDomainMaps); read the effective list so the
    map editor's connection picker stays in sync with what is configured.
    """
    raw = effective_settings()[CONFIG_VAR_CONNECTIONS]
    if not isinstance(raw, list):
        return []
    out: list[tuple[str, str]] = []
    for entry in raw:
        if isinstance(entry, dict) and isinstance(cid := entry.get("id"), str) and cid:
            out.append((cid, str(entry.get("label") or cid)))
    return out


def monitoring_core() -> Literal["cmc", "nagios"] | None:
    """The local site's monitoring core, or None when unknown.

    Used only to pre-select the connection form's metric-history default (CMC →
    Livestatus, Nagios → REST API). Read from the site's CONFIG_CORE; fails safe
    to None (Livestatus default). Mirrors how Checkmk seeds core-dependent
    defaults (cmk/gui/wato/_check_mk_configuration.py:_default_check_interval).
    """
    try:
        core = get_omd_config(paths.omd_root).get("CONFIG_CORE")
    except OSError, ValueError:
        return None
    if core == "cmc":
        return "cmc"
    if core == "nagios":
        return "nagios"
    return None
