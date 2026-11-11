#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from pathlib import Path

import pytest

from cmk.maps.gui.nagvis_geo import (
    is_zoom_limited,
    Locations,
    locations,
    place,
    Placement,
    read_geo_files,
    WorldmapTable,
)


def _write_worldmap_db(cfg_dir: Path, *objects: Mapping[str, object]) -> None:
    with closing(sqlite3.connect(cfg_dir / "worldmap.db")) as db:
        db.execute(
            "CREATE TABLE objects (object_id VARCHAR(20), lat REAL, lng REAL, lat2 REAL, "
            "lng2 REAL, object TEXT, PRIMARY KEY(object_id))"
        )
        db.executemany(
            "INSERT INTO objects (object_id, object) VALUES (?, ?)",
            [(obj["object_id"], json.dumps(obj)) for obj in objects],
        )
        db.commit()


def _host(object_id: str, lat: str, lng: str, **params: str) -> dict[str, str]:
    return {
        "object_id": object_id,
        "type": "host",
        "host_name": f"host-{object_id}",
        "x": lat,
        "y": lng,
        **params,
    }


def _worldmap(cfg_dir: Path) -> WorldmapTable:
    return read_geo_files(cfg_dir).worldmap


def test_the_objects_of_the_worldmap_table_are_read_with_their_parameters(
    tmp_path: Path,
) -> None:
    _write_worldmap_db(
        tmp_path,
        {"object_id": "a1b2c3", "type": "host", "x": 48.1, "y": "11.5", "label_show": True},
    )

    assert _worldmap(tmp_path) == WorldmapTable(
        {
            "a1b2c3": {
                "object_id": "a1b2c3",
                "type": "host",
                "x": "48.1",
                "y": "11.5",
                "label_show": "1",
            }
        }
    )


def test_objects_nagvis_has_only_written_to_its_log_are_read(tmp_path: Path) -> None:
    with closing(sqlite3.connect(tmp_path / "worldmap.db")) as nagvis:
        nagvis.execute("PRAGMA journal_mode = wal")
        nagvis.execute("CREATE TABLE objects (object_id VARCHAR(20), object TEXT)")
        nagvis.execute(
            "INSERT INTO objects VALUES (?, ?)",
            ("a1b2c3", json.dumps(_host("a1b2c3", "48.1", "11.5"))),
        )
        nagvis.commit()

        assert list(_worldmap(tmp_path).objects) == ["a1b2c3"]


def test_without_a_worldmap_database_the_table_is_empty(tmp_path: Path) -> None:
    assert _worldmap(tmp_path) == WorldmapTable()


def test_a_worldmap_database_nagvis_never_opened_is_empty(tmp_path: Path) -> None:
    (tmp_path / "worldmap.db").touch()

    assert _worldmap(tmp_path) == WorldmapTable()


def test_a_worldmap_database_that_is_no_database_names_why(tmp_path: Path) -> None:
    (tmp_path / "worldmap.db").write_text("no database")

    assert _worldmap(tmp_path) == WorldmapTable(error="file is not a database")


def test_the_worldmap_database_is_left_untouched(tmp_path: Path) -> None:
    _write_worldmap_db(tmp_path, _host("a1b2c3", "48.1", "11.5"))
    before = (tmp_path / "worldmap.db").read_bytes()

    _worldmap(tmp_path)

    assert (tmp_path / "worldmap.db").read_bytes() == before


def test_unreadable_entries_of_the_worldmap_table_are_counted(tmp_path: Path) -> None:
    _write_worldmap_db(tmp_path, {"object_id": "a1b2c3", "x": "48.1", "y": "11.5"})

    assert _worldmap(tmp_path) == WorldmapTable(unreadable=1)


def test_the_demo_objects_of_the_worldmap_table_are_left_out(tmp_path: Path) -> None:
    _write_worldmap_db(
        tmp_path,
        {
            "object_id": "0df2d3",
            "type": "hostgroup",
            "hostgroup_name": "muc",
            "x": "48.11253172488166",
            "y": "11.67941093444824",
        },
    )

    assert _worldmap(tmp_path) == WorldmapTable()


def test_an_object_under_a_demo_id_that_shows_something_else_is_kept(tmp_path: Path) -> None:
    _write_worldmap_db(
        tmp_path,
        {
            "object_id": "0df2d3",
            "type": "hostgroup",
            "hostgroup_name": "munich",
            "x": "48.1",
            "y": "11.6",
        },
    )

    assert list(_worldmap(tmp_path).objects) == ["0df2d3"]


def test_a_demo_object_that_was_moved_is_kept(tmp_path: Path) -> None:
    _write_worldmap_db(
        tmp_path,
        {
            "object_id": "0df2d3",
            "type": "hostgroup",
            "hostgroup_name": "muc",
            "x": "48.137",
            "y": "11.575",
        },
    )

    assert list(_worldmap(tmp_path).objects) == ["0df2d3"]


def test_the_location_files_are_read_by_their_name(tmp_path: Path) -> None:
    (tmp_path / "geomap").mkdir()
    (tmp_path / "geomap" / "offices.csv").write_bytes(b"ber-srv1;Berlin;52.52;13.405\n")

    assert read_geo_files(tmp_path).locations == {"offices": b"ber-srv1;Berlin;52.52;13.405\n"}


def test_a_location_file_has_a_host_for_each_line() -> None:
    assert locations(
        "; name;alias;lat;long\nber-srv1;Berlin;52.52;13.405\ncgn-srv1;Cologne;50.94;6.96\n"
    ) == Locations({"ber-srv1": (52.52, 13.405), "cgn-srv1": (50.94, 6.96)}, [])


@pytest.mark.parametrize(
    "line, named",
    [
        pytest.param("ber-srv1;Berlin;north;13.405", "ber-srv1", id="no number"),
        pytest.param("ber-srv1;Berlin;95;13.405", "ber-srv1", id="latitude out of range"),
        pytest.param("ber-srv1;Berlin", "ber-srv1", id="too few fields"),
        pytest.param(" ;Berlin;52.52;13.405", "line 1", id="no host"),
    ],
)
def test_an_entry_of_a_location_file_without_valid_coordinates_is_named(
    line: str, named: str
) -> None:
    assert locations(f"{line}\ncgn-srv1;Cologne;50.94;6.96\n") == Locations(
        {"cgn-srv1": (50.94, 6.96)}, [named]
    )


def test_the_demo_locations_nagvis_ships_are_left_out() -> None:
    assert locations(
        "ham-srv1;Hamburg Server 1;53.556866;9.994622\n"
        "muc-srv1;Munich Server1;48.1448353;11.5580067\n"
        "ber-srv1;Berlin;52.52;13.405\n"
    ) == Locations({"ber-srv1": (52.52, 13.405)}, [])


def test_a_line_runs_between_its_first_and_last_coordinate() -> None:
    objects = {"l1": {"x": "48.1,49.0,50.9", "y": "11.5,9.0,6.9"}}

    assert place(objects, "l1", line=True) == Placement((48.1, 11.5), (50.9, 6.9))


def test_a_line_end_follows_the_object_it_names() -> None:
    objects = {
        "a1b2c3": _host("a1b2c3", "48.1", "11.5"),
        "l1": {"x": "a1b2c3%+0,50.9", "y": "a1b2c3%+0,6.9"},
    }

    assert place(objects, "l1", line=True) == Placement(
        (48.1, 11.5), (50.9, 6.9), start_ref="a1b2c3"
    )


def test_an_object_placed_at_another_takes_its_position() -> None:
    objects = {
        "a1b2c3": _host("a1b2c3", "48.1", "11.5"),
        "d4e5f6": _host("d4e5f6", "a1b2c3%+20", "a1b2c3%-5"),
    }

    assert place(objects, "d4e5f6", line=False) == Placement((48.1, 11.5), start_ref="a1b2c3")


def test_a_longitude_past_the_antimeridian_is_brought_back() -> None:
    objects = {"a1b2c3": _host("a1b2c3", "10.0", "190.0")}

    assert place(objects, "a1b2c3", line=False) == Placement((10.0, -170.0))


@pytest.mark.parametrize(
    "lat, lng",
    [
        pytest.param("north", "11.5", id="no number"),
        pytest.param("95", "11.5", id="latitude out of range"),
        pytest.param("48.1", "", id="longitude missing"),
        pytest.param("gone00%+0", "gone00%+0", id="names a missing object"),
        pytest.param("a1b2c3%+0", "a1b2c3%+0", id="names itself"),
    ],
)
def test_an_object_without_valid_coordinates_has_no_place(lat: str, lng: str) -> None:
    assert place({"a1b2c3": _host("a1b2c3", lat, lng)}, "a1b2c3", line=False) is None


def test_a_line_with_one_coordinate_has_no_place() -> None:
    assert place({"l1": {"x": "48.1", "y": "11.5"}}, "l1", line=True) is None


@pytest.mark.parametrize(
    "params, limited",
    [
        pytest.param({}, False, id="no limits"),
        pytest.param({"min_zoom": "8"}, True, id="minimum"),
        pytest.param({"max_zoom": "10"}, True, id="maximum"),
        pytest.param({"min_zoom": "12", "max_zoom": "4"}, False, id="contradicting"),
    ],
)
def test_nagvis_shows_an_object_at_some_zoom_levels_only_by_its_limits(
    params: dict[str, str], limited: bool
) -> None:
    assert is_zoom_limited(params) is limited
