#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

from cmk.diskspace.file import _Info, _load_plugin, _PluginData, _read_plugin_info, load_plugins


def test_load_plugins_dont_fail_on_missing_local_dir(tmp_path: Path) -> None:
    (plugin_dir := tmp_path / "internal").mkdir()

    assert not load_plugins(tmp_path, plugin_dir, tmp_path / "local")


def test_load_plugin_from_disk(tmp_path: Path) -> None:
    (plugin_dir := tmp_path / "internal").mkdir()
    (plugin_dir / "bla").write_text("cleanup_paths = ['bla/*']\nfile_infos={'bla': 2.0}")
    plugin = _load_plugin(plugin_dir, "bla")

    assert plugin == _PluginData(
        base_path=plugin_dir, plugin_name="bla", cleanup_paths=["bla/*"], file_infos={"bla": 2.0}
    )


def test_load_plugin_from_disk_ignore_invalid_data(tmp_path: Path) -> None:
    (plugin_dir := tmp_path / "internal").mkdir()
    # Attention: Overwriting file info with the file_infos configuration is not officially supported and should be avoided
    (plugin_dir / "bla").write_text("cleanup_paths = ['bla/*']\nfile_infos={'bla': 2.0}\nfoo='bar'")
    plugin = _load_plugin(plugin_dir, "bla")

    assert plugin == _PluginData(
        base_path=plugin_dir, plugin_name="bla", cleanup_paths=["bla/*"], file_infos={"bla": 2.0}
    )


def test_read_plugin_patterns_match(tmp_path: Path) -> None:
    (tmp_path / "foo").mkdir()
    (tmp_path / "foo" / "tmp").touch()
    os.utime(tmp_path / "foo" / "tmp", times=(123, 456))
    plugin = _PluginData(
        base_path=tmp_path / "internal",
        plugin_name="bla",
        cleanup_paths=["foo/*"],
        file_infos={"bla": 2.0},
    )

    assert _read_plugin_info(tmp_path, plugin) == _Info(
        plugin_name="bla", path_to_mod_time={"bla": 2.0, str(tmp_path / "foo" / "tmp"): 456.0}
    )


def test_read_plugin_patterns_match_non_existent_file(tmp_path: Path) -> None:
    plugin = _PluginData(
        base_path=tmp_path / "internal", plugin_name="bla", cleanup_paths=["bla/*"], file_infos={}
    )

    assert _read_plugin_info(tmp_path, plugin) == _Info(plugin_name="bla", path_to_mod_time={})
