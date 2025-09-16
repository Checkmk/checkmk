#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path

import pytest

from cmk.ccc.config_path import VersionedConfigPath


class TestVersionedConfigPath:
    @pytest.fixture
    def base_path(self, tmp_path: Path) -> Path:
        return tmp_path

    @pytest.fixture
    def config_path(self, base_path: Path) -> Iterator[VersionedConfigPath]:
        yield VersionedConfigPath.next(base_path)

    def test_next(self, base_path: Path, config_path: VersionedConfigPath) -> None:
        assert config_path == VersionedConfigPath(base_path, 1)

        config_path = VersionedConfigPath.next(base_path)
        assert config_path == VersionedConfigPath(base_path, 2)

        config_path = VersionedConfigPath.next(base_path)
        assert config_path == VersionedConfigPath(base_path, 3)

    def test_str(self, config_path: VersionedConfigPath) -> None:
        assert isinstance(str(config_path), str)

    def test_repr(self, config_path: VersionedConfigPath) -> None:
        assert isinstance(repr(config_path), str)

    def test_eq(self, base_path: Path, config_path: VersionedConfigPath) -> None:
        assert config_path == type(config_path)(base_path, config_path.serial)
        assert config_path == Path(config_path)
        assert config_path != VersionedConfigPath.make_latest_path(base_path)
        assert config_path != VersionedConfigPath.make_latest_path(base_path)
        next_config_path = VersionedConfigPath.next(base_path)
        assert config_path != next_config_path

    def test_hash(self, base_path: Path, config_path: VersionedConfigPath) -> None:
        assert isinstance(hash(config_path), int)
        assert hash(config_path) == hash(type(config_path)(base_path, config_path.serial))
        assert hash(config_path) != hash(VersionedConfigPath.make_latest_path(base_path))
        next_config_path = VersionedConfigPath.next(base_path)
        assert hash(config_path) != hash(next_config_path)

    def test_fspath(self, config_path: VersionedConfigPath) -> None:
        assert config_path.serial == 1
        assert Path(config_path) / "filename" == config_path.root / "1/filename"
        assert Path("dir") / Path(config_path).name == Path("dir/1")

    @pytest.mark.parametrize("is_cmc", (True, False))
    def test_create_success(
        self, base_path: Path, config_path: VersionedConfigPath, is_cmc: bool
    ) -> None:
        latest_path = VersionedConfigPath.make_latest_path(base_path)
        assert not Path(config_path).exists()
        assert not latest_path.exists()

        with config_path.create(is_cmc=is_cmc):
            assert Path(config_path).exists()
            assert not latest_path.exists()

        assert Path(config_path).exists()
        assert latest_path.exists()
        assert latest_path.resolve() == Path(config_path).resolve()

        next_config_path = VersionedConfigPath.next(base_path)
        with next_config_path.create(is_cmc=is_cmc):
            assert Path(next_config_path).exists()
            assert latest_path.exists()
            assert latest_path.resolve() == Path(config_path).resolve()

        assert Path(next_config_path).exists()
        assert latest_path.exists()
        assert latest_path.resolve() == Path(next_config_path)

    @pytest.mark.parametrize("is_cmc", (True, False))
    def test_create_no_latest_link_update_on_failure(
        self, base_path: Path, config_path: VersionedConfigPath, is_cmc: bool
    ) -> None:
        latest_path = VersionedConfigPath.make_latest_path(base_path)
        assert not Path(config_path).exists()
        assert not latest_path.exists()

        with config_path.create(is_cmc=is_cmc):
            assert Path(config_path).exists()
            assert not latest_path.exists()

        assert Path(config_path).exists()
        assert latest_path.exists()
        assert latest_path.resolve() == Path(config_path).resolve()

        next_config_path = VersionedConfigPath.next(base_path)
        with suppress(RuntimeError), next_config_path.create(is_cmc=is_cmc):
            assert Path(next_config_path).exists()
            assert latest_path.exists()
            assert latest_path.resolve() == Path(config_path).resolve()
            raise RuntimeError("boom")

        assert Path(next_config_path).exists()
        assert latest_path.exists()
        assert latest_path.resolve() != Path(next_config_path).resolve()
        assert latest_path.resolve() == Path(config_path).resolve()
