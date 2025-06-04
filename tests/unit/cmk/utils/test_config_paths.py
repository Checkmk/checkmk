#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shutil
from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path

import pytest

from cmk.utils.config_path import LATEST_CONFIG, VersionedConfigPath


class TestVersionedConfigPath:
    @pytest.fixture
    def config_path(self) -> Iterator[VersionedConfigPath]:
        VersionedConfigPath.ROOT.mkdir(parents=True, exist_ok=True)
        # Call next because this is where `latest` etc. are created and updated.
        yield next(VersionedConfigPath(0))
        shutil.rmtree(VersionedConfigPath.ROOT)

    def test_iter(self, config_path: VersionedConfigPath) -> None:
        for it, elem in enumerate(config_path, config_path.serial + 1):
            if it == 10:
                break
            assert elem == type(config_path)(it)

    def test_next(self, config_path: VersionedConfigPath) -> None:
        assert config_path == VersionedConfigPath.current() == VersionedConfigPath(1)

        config_path = next(config_path)
        assert config_path == VersionedConfigPath.current() == VersionedConfigPath(2)

        config_path = next(config_path)
        assert config_path == VersionedConfigPath.current() == VersionedConfigPath(3)

    def test_str(self, config_path: VersionedConfigPath) -> None:
        assert isinstance(str(config_path), str)

    def test_repr(self, config_path: VersionedConfigPath) -> None:
        assert isinstance(repr(config_path), str)

    def test_eq(self, config_path: VersionedConfigPath) -> None:
        assert config_path == type(config_path)(config_path.serial)
        assert config_path == Path(config_path)
        assert config_path != LATEST_CONFIG
        assert config_path != LATEST_CONFIG
        assert config_path != next(config_path)

    def test_hash(self, config_path: VersionedConfigPath) -> None:
        assert isinstance(hash(config_path), int)
        assert hash(config_path) == hash(type(config_path)(config_path.serial))
        assert hash(config_path) != hash(LATEST_CONFIG)
        assert hash(config_path) != hash(next(config_path))

    def test_fspath(self, config_path: VersionedConfigPath) -> None:
        assert config_path.serial == 1
        assert Path(config_path) / "filename" == VersionedConfigPath.ROOT / "1/filename"
        assert Path("dir") / Path(config_path).name == Path("dir/1")

    @pytest.mark.parametrize("is_cmc", (True, False))
    def test_create_success(self, config_path: VersionedConfigPath, is_cmc: bool) -> None:
        assert not Path(config_path).exists()
        assert not LATEST_CONFIG.exists()

        with config_path.create(is_cmc=is_cmc):
            assert Path(config_path).exists()
            assert not LATEST_CONFIG.exists()

        assert Path(config_path).exists()
        assert LATEST_CONFIG.exists()
        assert LATEST_CONFIG.resolve() == Path(config_path).resolve()

        next_config_path = next(config_path)
        with next_config_path.create(is_cmc=is_cmc):
            assert Path(next_config_path).exists()
            assert LATEST_CONFIG.exists()
            assert LATEST_CONFIG.resolve() == Path(config_path).resolve()

        assert Path(next_config_path).exists()
        assert LATEST_CONFIG.exists()
        assert LATEST_CONFIG.resolve() == Path(next_config_path)

    @pytest.mark.parametrize("is_cmc", (True, False))
    def test_create_no_latest_link_update_on_failure(
        self, config_path: VersionedConfigPath, is_cmc: bool
    ) -> None:
        assert not Path(config_path).exists()
        assert not LATEST_CONFIG.exists()

        with config_path.create(is_cmc=is_cmc):
            assert Path(config_path).exists()
            assert not LATEST_CONFIG.exists()

        assert Path(config_path).exists()
        assert LATEST_CONFIG.exists()
        assert LATEST_CONFIG.resolve() == Path(config_path).resolve()

        next_config_path = next(config_path)
        with suppress(RuntimeError), next_config_path.create(is_cmc=is_cmc):
            assert Path(next_config_path).exists()
            assert LATEST_CONFIG.exists()
            assert LATEST_CONFIG.resolve() == Path(config_path).resolve()
            raise RuntimeError("boom")

        assert Path(next_config_path).exists()
        assert LATEST_CONFIG.exists()
        assert LATEST_CONFIG.resolve() != Path(next_config_path).resolve()
        assert LATEST_CONFIG.resolve() == Path(config_path).resolve()
