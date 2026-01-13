#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path

from cmk.base.core.interface._snapshot_local_dir import snapshot_local_dir


def test_snapshot_local_dir_link_handling(tmp_path: Path) -> None:
    site_root = tmp_path / "omd"
    # simulate /omd vs /opt/omd
    (tmp_path / "opt/omd").mkdir(parents=True, exist_ok=False)
    site_root.symlink_to(tmp_path / "opt/omd", target_is_directory=True)

    local_dir = site_root / "local"
    config_dir = site_root / "config"
    snapshot_dir = site_root / "config/local"
    snapshot_dir.parent.mkdir(parents=True, exist_ok=False)

    # Setup source directory structure
    local_dir.mkdir(parents=True, exist_ok=False)

    (site_root / "outside").touch()
    (local_dir / "inside").touch()
    (local_dir / "link_to_inside_rel").symlink_to("inside")
    (local_dir / "link_to_inside_abs").symlink_to(local_dir / "inside")
    (local_dir / "link_to_outside").symlink_to("../outside")
    (local_dir / "link_to_inside_missing").symlink_to("inside_missing")
    (local_dir / "link_to_outside_missing").symlink_to("../outside_missing")

    # act
    snapshot_local_dir(local_dir, config_dir)

    # check result:
    assert (snapshot_dir / "inside").is_file()

    # internal link is preserved
    assert (snapshot_dir / "link_to_inside_rel").is_symlink()
    assert (snapshot_dir / "link_to_inside_rel").resolve() == (snapshot_dir / "inside").resolve()

    # external link is dereferenced
    assert (snapshot_dir / "link_to_inside_abs").is_file()
    assert not (snapshot_dir / "link_to_inside_abs").is_symlink()
    assert (snapshot_dir / "link_to_outside").is_file()
    assert not (snapshot_dir / "link_to_outside").is_symlink()

    # dangling links are preserved
    assert (snapshot_dir / "link_to_inside_missing").is_symlink()
    assert not (snapshot_dir / "link_to_inside_missing").resolve().exists()
    assert (snapshot_dir / "link_to_outside_missing").is_symlink()
    assert not (snapshot_dir / "link_to_outside_missing").resolve().exists()
