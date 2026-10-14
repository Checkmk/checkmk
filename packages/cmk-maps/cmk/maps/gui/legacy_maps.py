#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Reading an OrbVis installation's boards, icons and backgrounds as Maps data.

OrbVis kept each board as ``var/orbvis/boards/<name>.json``, its icon library in
``var/orbvis/images``, the board backgrounds in ``var/orbvis/boards/backgrounds``
and its connections in ``var/orbvis/connections.json``. None of these files is
changed here.
"""

import copy
import json
import math
from collections.abc import Iterator, Mapping
from contextlib import suppress
from logging import Logger
from pathlib import Path

import cmk.utils.paths
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site
from cmk.ccc.user import UserId
from cmk.maps.gui._image_security import (
    BACKGROUND_SUFFIXES,
    ICON_SUFFIXES,
    is_valid_image,
    is_valid_image_name,
    safe_image_stem,
)
from cmk.maps.gui._images import delete_background_files, import_icon, store_background
from cmk.maps.shared.geo import bounded_view
from cmk.maps.shared.map_compat import (
    accept_legacy_backend_id,
    coerce_graph_metric,
    migrate_weathermap,
)
from cmk.maps.shared.map_payload import (
    DISPLAY_FIELD_DEFAULTS,
    LABEL_FIELD_DEFAULTS,
    MAP_FIELD_DEFAULTS,
    OBJECT_FIELD_DEFAULTS,
    RADAR_VIEW_FIELD_DEFAULTS,
)
from cmk.maps.shared.validators import rgb_to_hex


def legacy_maps_dir() -> Path:
    return cmk.utils.paths.omd_root / "var" / "orbvis"


def read_legacy_map(path: Path) -> dict[str, object]:
    board = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(board, dict):
        raise ValueError("board file is not a JSON object")
    return board


def is_demo_map(board: Mapping[str, object]) -> bool:
    """OrbVis's own demo boards, the only read-only ones.

    OrbVis seeded them, refreshed them on every start and refused any edit, so they
    hold nothing of the site.
    """
    return board.get("readonly") is True


def is_hidden_map(board: Mapping[str, object]) -> bool:
    return board.get("show_in_lists") is False


def foreign_connections() -> frozenset[str]:
    """The IDs of the OrbVis connections that do not lead to this site's Livestatus."""
    # OrbVis renames the pre-rename file only when it starts.
    for path in (legacy_maps_dir() / "connections.json", legacy_maps_dir() / "backends.json"):
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except OSError, ValueError:
            continue
        if isinstance(entries, list):
            return frozenset(
                entry["id"]
                for entry in entries
                if isinstance(entry, dict)
                and isinstance(entry.get("id"), str)
                and not _is_site_livestatus(entry)
            )
    return frozenset()


def _is_site_livestatus(entry: Mapping[str, object]) -> bool:
    socket_path = entry.get("socket_path")
    return (
        entry.get("type", "livestatus") == "livestatus"
        # The daemon connects over TCP whenever a host is set.
        and not entry.get("host")
        and isinstance(socket_path, str)
        and Path(socket_path).resolve() == cmk.utils.paths.livestatus_unix_socket.resolve()
    )


def _dict_objects(spec: Mapping[str, object]) -> Iterator[dict[str, object]]:
    """The board's objects, as far as a hand-edited file kept them objects."""
    objects = spec.get("objects")
    for obj in objects if isinstance(objects, list) else []:
        if isinstance(obj, dict):
            yield obj


def used_connections(spec: Mapping[str, object]) -> set[str]:
    return {
        connection
        for holder in (spec, *_dict_objects(spec))
        if isinstance(connection := holder.get("connection_id"), str)
    }


def legacy_map_to_spec(
    board: Mapping[str, object],
    name: str,
    renamed_icons: Mapping[str, str],
    foreign: frozenset[str],
) -> dict[str, object]:
    """The board as a map spec named ``name``, still to be validated.

    Connections to this site's Livestatus, and those OrbVis did not know, become the
    site's own Maps connection; one in ``foreign`` keeps its ID.
    """
    spec = copy.deepcopy(dict(board))
    spec["name"] = name
    _rename_icon_refs(spec, renamed_icons)
    _translate_legacy_keys(spec)
    _count_bundle_services(spec)
    _drop_member_patterns(spec)
    _retarget_connections(spec, foreign)
    _convert_css_colors(spec)
    _fill_map_defaults(spec)
    _bound_geo_view(spec)
    _caption_geo_objects(spec)
    return spec


def _retarget_connections(spec: dict[str, object], foreign: frozenset[str]) -> None:
    site_connection = f"cmk_{omd_site()}"
    connection = spec.get("connection_id")
    if not (isinstance(connection, str) and connection in foreign):
        spec["connection_id"] = site_connection
    for obj in _dict_objects(spec):
        # ``None`` inherits the board's connection.
        if (own := obj.get("connection_id")) is not None and not (
            isinstance(own, str) and own in foreign
        ):
            obj["connection_id"] = site_connection


def _fill_map_defaults(spec: dict[str, object]) -> None:
    # The board model defaults these fields, the REST model requires them.
    for key, default in MAP_FIELD_DEFAULTS.items():
        spec.setdefault(key, default)
    spec.setdefault("objects", [])
    view = spec.setdefault("view", {"type": "static"})
    if isinstance(view, dict) and view.get("type") == "radar":
        for key, default in RADAR_VIEW_FIELD_DEFAULTS.items():
            view.setdefault(key, default)
    for obj in _dict_objects(spec):
        for key, default in OBJECT_FIELD_DEFAULTS.items():
            obj.setdefault(key, default)
        if isinstance(label := obj.get("label"), dict):
            obj["label"] = {**LABEL_FIELD_DEFAULTS, **label}
        if isinstance(display := obj.get("display"), dict):
            obj["display"] = {**DISPLAY_FIELD_DEFAULTS, **display}


def _bound_geo_view(spec: dict[str, object]) -> None:
    """Bring a geo board's view within the limits Maps enforces.

    OrbVis saved the view as Leaflet reported it: past the antimeridian once
    panned across it, and up to the tile layer's zoom 19.
    """
    view = spec.get("view")
    if not isinstance(view, dict) or view.get("type") != "worldmap":
        return
    view["lat"], view["lng"], view["zoom"] = bounded_view(
        _finite(view.get("lat"), 51.0),
        _finite(view.get("lng"), 10.0),
        int(_finite(view.get("zoom"), 5)),
    )


def _finite(value: object, default: float) -> float:
    # A hand-edited board can hold anything; json reads NaN and Infinity, too.
    if isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value):
        return float(value)
    return default


def _caption_geo_objects(spec: dict[str, object]) -> None:
    """Keep a geo board's objects captioned.

    OrbVis captioned a geo object without label settings, while Maps, like an
    OrbVis static board, shows no label for it.
    """
    view = spec.get("view")
    if not isinstance(view, dict) or view.get("type") != "worldmap":
        return
    for obj in _dict_objects(spec):
        if obj.get("label") is None:
            obj["label"] = dict(LABEL_FIELD_DEFAULTS)


def _translate_legacy_keys(spec: dict[str, object]) -> None:
    accept_legacy_backend_id(spec)
    # The pagetype holds ``show_in_lists`` as its ``hidden``; ``readonly`` only
    # marked the demo boards.
    spec.pop("show_in_lists", None)
    spec.pop("readonly", None)
    for obj in _dict_objects(spec):
        migrate_weathermap(obj)
        if "graph_metric" in obj:
            obj["graph_metric"] = coerce_graph_metric(obj["graph_metric"])


def _count_bundle_services(spec: dict[str, object]) -> None:
    """Keep a board's geo bundles counting their services.

    OrbVis folded a bundle's service counts into its state, yet stored
    ``recognize_services`` off on every dynamic group; Maps goes by that flag.
    """
    objects = spec.get("objects")
    if not isinstance(objects, list):
        return
    for obj in objects:
        if isinstance(obj, dict) and obj.get("type") == "dyngroup" and obj.get("bundle_kind"):
            obj["recognize_services"] = True


def _drop_member_patterns(spec: dict[str, object]) -> None:
    """Drop the member patterns of a board.

    OrbVis stored them but never applied them, and its editor asked for state
    names where Maps reads a pattern on member names.
    """
    objects = spec.get("objects")
    if not isinstance(objects, list):
        return
    for obj in objects:
        if isinstance(obj, dict):
            obj.pop("exclude_members", None)
            obj.pop("exclude_member_states", None)


# The keys that hold a color, at any depth of a board.
_COLOR_KEYS = frozenset(
    {
        "background",
        "background_color",
        "border",
        "color",
        "color_border",
        "fill",
        "label_border",
        "line_color",
        "line_color_border",
        "stroke",
        "textbox_background",
        "textbox_border",
    }
)


def _convert_css_colors(node: object) -> None:
    """Rewrite CSS ``rgb()`` colors, which OrbVis took from NagVis maps, to hex."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in _COLOR_KEYS and isinstance(value, str):
                node[key] = rgb_to_hex(value)
            else:
                _convert_css_colors(value)
    elif isinstance(node, list):
        for item in node:
            _convert_css_colors(item)


def _legacy_icons() -> list[Path]:
    source = legacy_maps_dir() / "images"
    return sorted(path for path in source.iterdir() if path.is_file()) if source.is_dir() else []


def _cleaned_icon_name(path: Path) -> str:
    # Cleaned like an upload: names from before OrbVis cleaned them may carry
    # characters that break the image URL.
    return safe_image_stem(path.name) + path.suffix.lower()


def legacy_icon_names(copied: Mapping[str, str]) -> dict[str, str]:
    """The name a board refers to each OrbVis icon by, where it differs from OrbVis's.

    A copied icon has the name it got in Maps' library; any other gets the cleaned
    name the copy would give it. That lets a board be checked before the copy, and
    keeps one that refers to an icon the copy left out from failing after it.
    """
    names = {path.name: _cleaned_icon_name(path) for path in _legacy_icons()}
    names.update(copied)
    return {name: stored for name, stored in names.items() if stored != name}


def copy_legacy_icons(logger: Logger, copied: Mapping[str, str]) -> dict[str, str]:
    """Copy the OrbVis icons not in ``copied`` into Maps' library.

    Returns the name each got there. One that could not be copied is left out, so a
    later run tries it again.
    """
    stored: dict[str, str] = {}
    for path in _legacy_icons():
        if path.name in copied:
            continue
        try:
            contents = path.read_bytes()
            if path.suffix.lower() not in ICON_SUFFIXES or not is_valid_image(
                contents, allow_gif=False
            ):
                logger.warning(
                    "OrbVis image %(name)s is not a supported image and was not copied.",
                    {"name": path.name},
                )
                continue
            stored[path.name] = import_icon(_cleaned_icon_name(path), contents)
        except (OSError, MKGeneralException) as exc:
            # One unreadable file must not hold back the other icons and every board.
            logger.warning(
                "OrbVis image %(name)s could not be copied: %(error)s",
                {"name": path.name, "error": exc},
            )
    return stored


def _rename_icon_refs(spec: Mapping[str, object], renamed: Mapping[str, str]) -> None:
    def rename(holder: object, key: str) -> None:
        if isinstance(holder, dict) and isinstance(ref := holder.get(key), str) and ref in renamed:
            holder[key] = renamed[ref]

    for obj in _dict_objects(spec):
        rename(obj, "image_src")
        rename(obj.get("display"), "image")
    view = spec.get("view")
    rename(view, "background_image")
    elements = view.get("elements") if isinstance(view, dict) else None
    for element in elements if isinstance(elements, list) else []:
        rename(element, "src")
        if isinstance(element, dict):
            rename(element.get("display"), "image")


def copy_legacy_background(
    spec: dict[str, object], owner: UserId, name: str, logger: Logger
) -> None:
    """Store the board's background as the map's; a missing one keeps its reference."""
    ref = spec.get("background_image")
    if not isinstance(ref, str) or not ref:
        return
    path = legacy_maps_dir() / "boards" / "backgrounds" / ref
    with suppress(OSError):
        if (
            is_valid_image_name(ref)
            and path.suffix.lower() in BACKGROUND_SUFFIXES
            and path.is_file()
            and is_valid_image(contents := path.read_bytes())
        ):
            spec["background_image"] = store_background(owner, name, path.suffix.lower(), contents)
            return
    logger.warning(
        "The background %(file)s of the migrated map %(name)r is missing, unreadable or not a "
        "supported image; the map keeps the reference without the image.",
        {"file": ref, "name": name},
    )


def drop_legacy_background(owner: UserId, name: str) -> None:
    """Remove what ``copy_legacy_background`` stored for a map that was not created."""
    delete_background_files(owner, name)
