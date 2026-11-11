#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The objects of NagVis' geographic maps, which it keeps outside the map files.

A worldmap shows the objects of ``etc/nagvis/worldmap.db``, a table all worldmaps
share. A geomap shows a host for each line of the CSV file its ``source_file``
names, below ``etc/nagvis/geomap``. ``read_geo_files`` reads both without changing
them; the rest works on what it read.
"""

import json
import re
import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from contextlib import closing, suppress
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from cmk.maps.shared.geo import bounded_view, LAT_LIMIT, MAX_ZOOM, parse_degrees

# What NagVis adds to a new worldmap database and ships as ``demo-locations.csv``, where
# it puts them: a demo object someone moved is theirs.
_DEMO_OBJECTS: Mapping[str, Mapping[str, str]] = {
    "273924": {
        "type": "map",
        "map_name": "demo-ham-racks",
        "x": "53.57495144249931",
        "y": "10.040549039840698",
    },
    "0df2d3": {
        "type": "hostgroup",
        "hostgroup_name": "muc",
        "x": "48.11253172488166",
        "y": "11.67941093444824",
    },
    "ebbf59": {
        "type": "hostgroup",
        "hostgroup_name": "cgn",
        "x": "50.93917617127812",
        "y": "6.958637237548828",
    },
}
_DEMO_LOCATIONS = frozenset(
    {
        ("ham-srv1", "53.556866", "9.994622"),
        ("muc-srv1", "48.1448353", "11.5580067"),
    }
)

# NagVis shows an object from zoom level 2 on unless it says otherwise.
_MIN_ZOOM = 2

_RELATIVE_RE = re.compile(r"^([A-Za-z0-9_]+)%")
_NAME_KEYS = ("host_name", "hostgroup_name", "servicegroup_name", "map_name", "name")

type LatLng = tuple[float, float]


@dataclass(frozen=True)
class WorldmapTable:
    """The objects of ``worldmap.db`` but the demo ones, by ``object_id``.

    ``unreadable`` counts the entries that are no object. ``error`` says why the
    file is no database, which no worldmap can be migrated without.
    """

    objects: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    unreadable: int = 0
    error: str | None = None


@dataclass(frozen=True)
class GeoFiles:
    """What NagVis keeps of its geographic maps outside the map files."""

    worldmap: WorldmapTable
    # The location files below ``etc/nagvis/geomap``, by name without ``.csv``.
    locations: Mapping[str, bytes]


def read_geo_files(cfg_dir: Path) -> GeoFiles:
    """The worldmap table and the location files below NagVis' ``cfg_dir``."""
    locations = {}
    for path in (cfg_dir / "geomap").glob("*.csv"):
        with suppress(OSError):
            locations[path.stem] = path.read_bytes()
    return GeoFiles(_read_worldmap_db(cfg_dir / "worldmap.db"), locations)


def _read_worldmap_db(path: Path) -> WorldmapTable:
    try:
        # Through SQLite, which also reads what NagVis' write-ahead log still holds.
        with closing(sqlite3.connect(f"file:{quote(str(path))}?mode=ro", uri=True)) as db:
            # NagVis adds the table on its first use of the file.
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name = 'objects'").fetchone():
                return WorldmapTable()
            rows = [raw for (raw,) in db.execute("SELECT object FROM objects ORDER BY rowid")]
    except sqlite3.Error as exc:
        # SQLite names a missing file as any other it cannot open.
        return WorldmapTable() if not path.exists() else WorldmapTable(error=str(exc))
    return _worldmap_table(rows)


def _worldmap_table(rows: Iterable[str | None]) -> WorldmapTable:
    objects = {}
    unreadable = 0
    for raw in rows:
        try:
            obj = json.loads(raw) if raw is not None else None
        except ValueError:
            obj = None
        if not isinstance(obj, dict) or not obj.get("object_id") or not obj.get("type"):
            unreadable += 1
            continue
        params = {str(key): _text(value) for key, value in obj.items() if value is not None}
        if not _is_demo_object(params["object_id"], params):
            objects[params["object_id"]] = params
    return WorldmapTable(objects, unreadable)


def _text(value: object) -> str:
    """A value as a map file holds it."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)


def _is_demo_object(object_id: str, params: Mapping[str, str]) -> bool:
    demo = _DEMO_OBJECTS.get(object_id)
    return demo is not None and all(params.get(key) == value for key, value in demo.items())


@dataclass(frozen=True)
class Locations:
    """The hosts of a geomap's location file, with the entries left out."""

    hosts: Mapping[str, LatLng]
    # The entries without valid coordinates: their host, else their line number.
    invalid: Sequence[str]


def locations(text: str) -> Locations:
    """The hosts of a location file but the demo ones NagVis ships."""
    hosts: dict[str, LatLng] = {}
    invalid = []
    for number, line in enumerate(text.splitlines(), start=1):
        # NagVis takes a line starting with one of these as a comment.
        if not line.strip() or line[0] in ";#/":
            continue
        fields = [part.strip() for part in line.split(";")]
        host_name = fields[0]
        at = _degrees(fields[2], fields[3]) if len(fields) >= 4 else None
        if not host_name or at is None:
            invalid.append(host_name or f"line {number}")
        elif (host_name, fields[2], fields[3]) not in _DEMO_LOCATIONS:
            hosts[host_name] = at
    return Locations(hosts, invalid)


def is_zoom_limited(params: Mapping[str, str]) -> bool:
    """Whether NagVis shows the object at some zoom levels only."""
    min_zoom = _zoom(params.get("min_zoom"), _MIN_ZOOM)
    max_zoom = _zoom(params.get("max_zoom"), MAX_ZOOM)
    # As in NagVis, limits that contradict each other do not apply.
    return min_zoom <= max_zoom and (min_zoom > _MIN_ZOOM or max_zoom < MAX_ZOOM)


def _zoom(value: str | None, default: int) -> int:
    return int(value) if value and value.isdigit() else default


def describe(object_type: str, object_id: str, params: Mapping[str, str]) -> str:
    """The object as a warning names it."""
    name = next((params[key] for key in _NAME_KEYS if params.get(key)), object_id)
    if service := params.get("service_description"):
        name = f"{name}/{service}"
    return f"{object_type} {name}"


def _degrees(lat: str, lng: str) -> LatLng | None:
    """The position, with a longitude NagVis stored past the antimeridian brought back."""
    lat_degrees, lng_degrees = parse_degrees(lat), parse_degrees(lng)
    if lat_degrees is None or lng_degrees is None or not -LAT_LIMIT <= lat_degrees <= LAT_LIMIT:
        return None
    lat_degrees, lng_degrees, _zoom_level = bounded_view(lat_degrees, lng_degrees, 0)
    return lat_degrees, lng_degrees


@dataclass(frozen=True)
class Placement:
    """Where an object of a worldmap sits; a line runs from ``at`` to ``end``.

    ``start_ref`` and ``end_ref`` name the ``object_id`` of the object that end
    follows.
    """

    at: LatLng
    end: LatLng | None = None
    start_ref: str | None = None
    end_ref: str | None = None


def place(
    objects: Mapping[str, Mapping[str, str]], object_id: str, *, line: bool
) -> Placement | None:
    """Where the object of ``objects`` is, ``None`` without a valid position.

    NagVis stores the latitudes in ``x`` and the longitudes in ``y``, one of each
    for an icon and one per end for a line. A coordinate can name another object
    instead, as ``<object_id>%<offset>``; the offset is in pixels of the current
    zoom level and is not kept.
    """
    lats, lngs = _coordinates(objects[object_id])
    if len(lats) != len(lngs) or (line and len(lats) < 2):
        return None
    if (start := _end(objects, object_id, lats[0], lngs[0])) is None:
        return None
    if not line:
        return Placement(start[0], start_ref=start[1])
    # A line's middle coordinate only bends it.
    if (end := _end(objects, object_id, lats[-1], lngs[-1])) is None:
        return None
    return Placement(start[0], end[0], start_ref=start[1], end_ref=end[1])


def _coordinates(params: Mapping[str, str]) -> tuple[list[str], list[str]]:
    return params.get("x", "").split(","), params.get("y", "").split(",")


def _end(
    objects: Mapping[str, Mapping[str, str]], object_id: str, lat: str, lng: str
) -> tuple[LatLng, str | None] | None:
    ref = _ref(lat, lng)
    at = _at(objects, ref, {object_id}) if ref else _degrees(lat, lng)
    return None if at is None else (at, ref)


def _ref(lat: str, lng: str) -> str | None:
    match = _RELATIVE_RE.match(lat.strip()) or _RELATIVE_RE.match(lng.strip())
    return match[1] if match else None


def _at(objects: Mapping[str, Mapping[str, str]], object_id: str, seen: set[str]) -> LatLng | None:
    """Where the object is, or where its line starts."""
    if object_id in seen or (params := objects.get(object_id)) is None:
        return None
    lats, lngs = _coordinates(params)
    if ref := _ref(lats[0], lngs[0]):
        return _at(objects, ref, seen | {object_id})
    return _degrees(lats[0], lngs[0])
