#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.config.paths import BaseConfigurationMKFiles, key_config_paths


def test_base_configuration_mk_files_from_omd_root() -> None:
    assert BaseConfigurationMKFiles.from_omd_root(
        Path("/omd/sites/heute")
    ) == BaseConfigurationMKFiles(
        main_mk=Path("/omd/sites/heute/etc/check_mk/main.mk"),
        conf_d=Path("/omd/sites/heute/etc/check_mk/conf.d"),
        final_mk=Path("/omd/sites/heute/etc/check_mk/final.mk"),
        local_mk=Path("/omd/sites/heute/etc/check_mk/local.mk"),
        include_conf_d=True,
    )


def _write_site_config(omd_root: Path, *relative_paths: str) -> None:
    for relative_path in relative_paths:
        path = omd_root / "etc/check_mk" / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")


def test_iterating_yields_the_files_in_read_order_with_their_conf_d_path(tmp_path: Path) -> None:
    _write_site_config(
        tmp_path, "main.mk", "conf.d/b.mk", "conf.d/a/x.mk", "conf.d/c.mk", "local.mk"
    )
    conf_d = tmp_path / "etc/check_mk/conf.d"

    assert list(BaseConfigurationMKFiles.from_omd_root(tmp_path).iterate_for_loading()) == [
        (tmp_path / "etc/check_mk/main.mk", None),
        (conf_d / "b.mk", Path("b.mk")),
        (conf_d / "c.mk", Path("c.mk")),
        (conf_d / "a/x.mk", Path("a/x.mk")),
        (tmp_path / "etc/check_mk/local.mk", None),
    ]


def test_iterating_without_conf_d_skips_its_files(tmp_path: Path) -> None:
    _write_site_config(tmp_path, "main.mk", "conf.d/a.mk", "final.mk")

    files = BaseConfigurationMKFiles.from_omd_root(tmp_path, include_conf_d=False)

    assert list(files.iterate_for_loading()) == [
        (tmp_path / "etc/check_mk/main.mk", None),
        (tmp_path / "etc/check_mk/final.mk", None),
    ]


def test_files_of_a_directory_sort_before_its_subdirectories_both_lexically() -> None:
    paths = [
        Path("/conf.d/sub/inner/q.mk"),
        Path("/conf.d/sub/a.mk"),
        Path("/conf.d/z.mk"),
        Path("/conf.d/b/x.mk"),
        Path("/conf.d/a.mk"),
    ]

    assert sorted(paths, key=key_config_paths) == [
        Path("/conf.d/a.mk"),
        Path("/conf.d/z.mk"),
        Path("/conf.d/b/x.mk"),
        Path("/conf.d/sub/a.mk"),
        Path("/conf.d/sub/inner/q.mk"),
    ]
