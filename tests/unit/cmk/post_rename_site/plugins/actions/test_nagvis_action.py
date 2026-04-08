#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.site import SiteId
from cmk.post_rename_site.logger import logger
from cmk.post_rename_site.plugins.actions.nagvis import update_nagvis_maps


@pytest.fixture(name="nagvis_maps_dir")
def fixture_nagvis_maps_dir(tmp_path: Path) -> Path:
    maps_dir = tmp_path / "etc" / "nagvis" / "maps"
    maps_dir.mkdir(parents=True)
    return maps_dir


def test_update_nagvis_maps_updates_backend_references(nagvis_maps_dir: Path) -> None:
    map_file = nagvis_maps_dir / "mymap.cfg"
    map_file.write_text(
        "define host {\n"
        "    host_name=myhost\n"
        "    backend=old_site\n"
        "}\n"
        "define service {\n"
        "    host_name=myhost\n"
        "    service_description=CPU\n"
        "    backend=old_site\n"
        "}\n"
    )

    update_nagvis_maps(SiteId("old_site"), SiteId("new_site"), logger, nagvis_maps_dir.parents[2])

    content = map_file.read_text()
    assert "backend=new_site" in content
    assert "backend=old_site" not in content


def test_update_nagvis_maps_does_not_match_prefix(nagvis_maps_dir: Path) -> None:
    map_file = nagvis_maps_dir / "mymap.cfg"
    map_file.write_text("define host {\n    backend=old_site_extra\n}\n")

    update_nagvis_maps(SiteId("old_site"), SiteId("new_site"), logger, nagvis_maps_dir.parents[2])

    content = map_file.read_text()
    assert "backend=old_site_extra" in content
    assert "backend=new_site" not in content


def test_update_nagvis_maps_ignores_other_backends(nagvis_maps_dir: Path) -> None:
    map_file = nagvis_maps_dir / "mymap.cfg"
    map_file.write_text(
        "define host {\n"
        "    host_name=myhost\n"
        "    backend=other_site\n"
        "}\n"
        "define host {\n"
        "    host_name=otherhost\n"
        "    backend=old_site\n"
        "}\n"
    )

    update_nagvis_maps(SiteId("old_site"), SiteId("new_site"), logger, nagvis_maps_dir.parents[2])

    content = map_file.read_text()
    assert "backend=other_site" in content
    assert "backend=new_site" in content
    assert "backend=old_site" not in content


def test_update_nagvis_maps_no_maps_dir(tmp_path: Path) -> None:
    # Should not raise even if the maps directory doesn't exist
    update_nagvis_maps(SiteId("old_site"), SiteId("new_site"), logger, tmp_path)
