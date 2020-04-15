#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import argparse
import sys
import io
from pathlib import Path
import pytest  # type: ignore[import]

import cmk.utils.log
import cmk.update_config as update_config
import cmk.gui.config
import cmk.utils.paths


@pytest.fixture()
def uc():
    return update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())


def test_parse_arguments_defaults():
    assert update_config.parse_arguments([]).__dict__ == {
        "debug": False,
        "verbose": 0,
    }


def test_parse_arguments_verbose():
    assert update_config.parse_arguments(["-v"]).verbose == 1
    assert update_config.parse_arguments(["-v"] * 2).verbose == 2
    assert update_config.parse_arguments(["-v"] * 3).verbose == 3


def test_parse_arguments_debug():
    assert update_config.parse_arguments(["--debug"]).debug is True


def test_update_config_init():
    update_config.UpdateConfig(cmk.utils.log.logger, argparse.Namespace())


def test_main(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    monkeypatch.setattr(update_config.UpdateConfig, "run", lambda self: sys.stdout.write("XYZ\n"))
    assert update_config.main([]) == 0
    assert "XYZ" in buf.getvalue()


def test_cleanup_version_specific_caches_missing_directory(uc):
    uc._cleanup_version_specific_caches()


def test_cleanup_version_specific_caches(uc):
    paths = [
        Path(cmk.utils.paths.include_cache_dir, "builtin"),
        Path(cmk.utils.paths.include_cache_dir, "local"),
        Path(cmk.utils.paths.precompiled_checks_dir, "builtin"),
        Path(cmk.utils.paths.precompiled_checks_dir, "local"),
    ]
    for base_dir in paths:
        base_dir.mkdir(parents=True, exist_ok=True)
        cached_file = base_dir / "if"
        with cached_file.open("w", encoding="utf-8") as f:
            f.write(u"\n")
        uc._cleanup_version_specific_caches()
        assert not cached_file.exists()
        assert base_dir.exists()
