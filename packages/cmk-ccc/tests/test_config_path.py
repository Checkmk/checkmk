#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path

import pytest

from cmk.ccc.config_path import create, VersionedConfigPath


class TestVersionedConfigPath:
    @pytest.fixture
    def base_path(self, tmp_path: Path) -> Path:
        return tmp_path

    @pytest.fixture
    def config_path(self, base_path: Path) -> Iterator[VersionedConfigPath]:
        yield VersionedConfigPath(base_path, 1)

    def test_str(self, config_path: VersionedConfigPath) -> None:
        assert isinstance(str(config_path), str)

    def test_repr(self, config_path: VersionedConfigPath) -> None:
        assert isinstance(repr(config_path), str)

    def test_eq(self, base_path: Path, config_path: VersionedConfigPath) -> None:
        assert config_path == type(config_path)(base_path, config_path.serial)
        assert config_path == Path(config_path)
        assert config_path != VersionedConfigPath.make_latest_path(base_path)
        assert config_path != VersionedConfigPath.make_latest_path(base_path)

    def test_hash(self, base_path: Path, config_path: VersionedConfigPath) -> None:
        assert isinstance(hash(config_path), int)
        assert hash(config_path) == hash(type(config_path)(base_path, config_path.serial))
        assert hash(config_path) != hash(VersionedConfigPath.make_latest_path(base_path))

    def test_fspath(self, config_path: VersionedConfigPath) -> None:
        assert config_path.serial == 1
        assert Path(config_path) / "filename" == config_path.root / "1/filename"
        assert Path("dir") / Path(config_path).name == Path("dir/1")


def test_create(tmp_path: Path) -> None:
    with create(tmp_path, is_cmc=True) as ctx:
        assert ctx.path_created.exists()
        assert ctx.serial_created == 1

    with create(tmp_path, is_cmc=True) as ctx:
        assert ctx.serial_created == 2

    with create(tmp_path, is_cmc=True) as ctx:
        assert ctx.serial_created == 3


@pytest.mark.parametrize("is_cmc", (True, False))
def test_create_success(tmp_path: Path, is_cmc: bool) -> None:
    latest_path = VersionedConfigPath.make_latest_path(tmp_path)
    assert not latest_path.exists()

    with create(tmp_path, is_cmc=is_cmc) as ctx:
        assert ctx.path_created.exists()
        created_config_path = ctx.path_created

    assert latest_path.exists()
    assert latest_path.resolve() == created_config_path.resolve()


@pytest.mark.parametrize("is_cmc", (True, False))
def test_create_no_latest_link_update_on_failure(tmp_path: Path, is_cmc: bool) -> None:
    latest_path = VersionedConfigPath.make_latest_path(tmp_path)

    with create(tmp_path, is_cmc=is_cmc) as ctx:
        succesfully_created_path = ctx.path_created

    assert latest_path.resolve() == succesfully_created_path
    assert succesfully_created_path.exists()

    with suppress(RuntimeError), create(tmp_path, is_cmc=is_cmc) as ctx:
        failing_created_path = ctx.path_created
        raise RuntimeError("boom")

    assert failing_created_path.exists()
    assert latest_path.resolve() == succesfully_created_path
