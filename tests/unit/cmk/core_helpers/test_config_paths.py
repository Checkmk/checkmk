#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
from pathlib import Path

import pytest  # type: ignore[import]

import cmk.utils.paths

import cmk.core_helpers.paths as paths


class TestVersionedConfigPath:
    @pytest.fixture
    def config_path(self):
        paths.ConfigPath.ROOT.mkdir(parents=True, exist_ok=True)
        # Call next because this is where `latest` etc. are created and updated.
        yield next(paths.VersionedConfigPath(0))
        shutil.rmtree(paths.ConfigPath.ROOT)

    def test_iter(self, config_path):
        for it, elem in enumerate(config_path, config_path.serial + 1):
            if it == 10:
                break
            assert elem == type(config_path)(it)

    def test_next(self, config_path):
        assert config_path == paths.VersionedConfigPath.current() == paths.VersionedConfigPath(1)

        config_path = next(config_path)
        assert config_path == paths.VersionedConfigPath.current() == paths.VersionedConfigPath(2)

        config_path = next(config_path)
        assert config_path == paths.VersionedConfigPath.current() == paths.VersionedConfigPath(3)

    def test_str(self, config_path):
        assert str(config_path) == str(config_path.serial)

    def test_repr(self, config_path):
        assert isinstance(repr(config_path), str)

    def test_eq(self, config_path):
        assert config_path == type(config_path)(config_path.serial)
        assert config_path != paths.LATEST_CONFIG
        assert config_path != next(config_path)

    def test_hash(self, config_path):
        assert isinstance(hash(config_path), int)
        assert hash(config_path) == hash(type(config_path)(config_path.serial))
        assert hash(config_path) != hash(paths.LATEST_CONFIG)
        assert hash(config_path) != hash(next(config_path))

    def test_truediv(self, config_path):
        assert config_path.serial == 1
        assert config_path / "filename" == Path("1/filename")
        assert Path("dir") / config_path == Path("dir/1")
        assert Path("dir") / config_path / "filename" == Path("dir/1/filename")


class TestLatestConfigPath:
    @pytest.fixture
    def config_path(self):
        yield paths.LatestConfigPath()
        (cmk.utils.paths.core_helper_config_dir / "serial.mk").unlink(missing_ok=True)

    def test_str(self, config_path):
        assert str(config_path) == "latest"

    def test_repr(self, config_path):
        assert isinstance(repr(config_path), str)

    def test_eq(self, config_path):
        assert config_path == paths.LATEST_CONFIG
        assert config_path == type(config_path)()
        assert config_path != paths.VersionedConfigPath(0)

    def test_hash(self, config_path):
        assert isinstance(hash(config_path), int)
        assert hash(config_path) == hash(paths.LATEST_CONFIG)
        assert hash(config_path) != hash(paths.VersionedConfigPath(0))
