#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path

import pytest

from cmk.ccc.config_path import cleanup_old_configs, create, VersionedConfigPath


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
    with create(tmp_path) as ctx:
        assert ctx.path_created.exists()
        assert ctx.serial_created == 1

    with create(tmp_path) as ctx:
        assert ctx.serial_created == 2

    with create(tmp_path) as ctx:
        assert ctx.serial_created == 3


def test_create_success(tmp_path: Path) -> None:
    latest_path = VersionedConfigPath.make_latest_path(tmp_path)
    assert not latest_path.exists()

    with create(tmp_path) as ctx:
        assert ctx.path_created.exists()
        created_config_path = ctx.path_created

    assert latest_path.exists()
    assert latest_path.resolve() == created_config_path.resolve()


def test_create_no_latest_link_update_on_failure(tmp_path: Path) -> None:
    latest_path = VersionedConfigPath.make_latest_path(tmp_path)

    with create(tmp_path) as ctx:
        succesfully_created_path = ctx.path_created

    assert latest_path.resolve() == succesfully_created_path
    assert succesfully_created_path.exists()

    with suppress(RuntimeError), create(tmp_path) as ctx:
        failing_created_path = ctx.path_created
        raise RuntimeError("boom")

    assert failing_created_path.exists()
    assert latest_path.resolve() == succesfully_created_path


class TestCleanupOldConfigs:
    @staticmethod
    def _make_helper_config(
        base: Path, serials: list[int], latest_serial: int
    ) -> tuple[Path, list[Path]]:
        """Set up a helper_config directory with numbered serial dirs, the latest symlink, and serial.mk.

        Returns (root, serial_dirs) where root is the helper_config directory and serial_dirs
        is the list of created serial directories (in the order of `serials`).
        """
        root = VersionedConfigPath.make_root_path(base)
        root.mkdir(parents=True, exist_ok=True)

        serial_dirs = []
        for serial in serials:
            d = root / str(serial)
            d.mkdir()
            serial_dirs.append(d)

        latest_link = root / "latest"
        latest_link.symlink_to(str(latest_serial))

        # serial.mk is a regular file that must survive cleanup
        (root / "serial.mk").touch()

        return root, serial_dirs

    def test_noop_when_root_does_not_exist(self, tmp_path: Path) -> None:
        """tolerate helper_config root not existing."""
        cleanup_old_configs(tmp_path)  # must not raise

    def test_keeps_latest(self, tmp_path: Path) -> None:
        """the 'latest' symlink itself is preserved."""
        root, _ = self._make_helper_config(tmp_path, serials=[1, 2, 3], latest_serial=3)
        cleanup_old_configs(tmp_path)
        assert (root / "latest").is_symlink()
        assert (root / "3").exists()

    def test_keeps_serial_mk(self, tmp_path: Path) -> None:
        """serial.mk (a regular file) is preserved."""
        root, _ = self._make_helper_config(tmp_path, serials=[1, 2, 3], latest_serial=3)
        cleanup_old_configs(tmp_path)
        assert (root / "serial.mk").exists()

    def test_removal_of_outdated(self, tmp_path: Path) -> None:
        """directories other than the latest are removed"""
        root, _ = self._make_helper_config(tmp_path, serials=[1, 2, 3], latest_serial=3)
        cleanup_old_configs(tmp_path)
        assert not (root / "1").exists()

    def test_single_config_nothing_removed(self, tmp_path: Path) -> None:
        """Only one config dir exists; nothing to remove."""
        root, _ = self._make_helper_config(tmp_path, serials=[1], latest_serial=1)
        cleanup_old_configs(tmp_path)
        assert (root / "1").exists()

    def test_two_configs_nothing_removed(self, tmp_path: Path) -> None:
        """Two config dirs exist; both should survive"""
        root, _ = self._make_helper_config(tmp_path, serials=[1, 2], latest_serial=2)
        cleanup_old_configs(tmp_path)
        assert (root / "1").exists()
        assert (root / "2").exists()

    def test_latest_not_highest_serial(self, tmp_path: Path) -> None:
        """Latest symlink may not point to the highest serial (e.g. after a failed create).

        keep the latest target AND the highest-serial remaining dir.
        """
        root, _ = self._make_helper_config(tmp_path, serials=[1, 2, 3], latest_serial=2)
        cleanup_old_configs(tmp_path)
        # latest target (2) must survive
        assert (root / "1").exists()
        assert (root / "2").exists()
        assert not (root / "3").exists()

    def test_many_old_configs(self, tmp_path: Path) -> None:
        """With many serials, only the two latest should remain."""
        serials, latest = [1, 2, 3, 4, 5], 5
        root, _ = self._make_helper_config(tmp_path, serials=serials, latest_serial=latest)
        cleanup_old_configs(tmp_path)
        for serial in serials[:-2]:
            assert not (root / str(serial)).exists()
        for serial in serials[-2:]:
            assert (root / str(serial)).exists()

    def test_non_sequential_serials(self, tmp_path: Path) -> None:
        """Serials may have gaps; cleanup must still work correctly."""
        root, _ = self._make_helper_config(tmp_path, serials=[10, 20, 30], latest_serial=30)
        cleanup_old_configs(tmp_path)
        assert not (root / "10").exists()
        assert (root / "30").exists()

    def test_integration_with_create(self, tmp_path: Path) -> None:
        """End-to-end: use the real `create` context manager, then clean up."""
        for _ in range(4):
            with create(tmp_path):
                pass

        root = VersionedConfigPath.make_root_path(tmp_path)
        # serials 1..4 exist, latest → 4
        assert all((root / str(s)).exists() for s in range(1, 5))

        cleanup_old_configs(tmp_path)

        assert (root / "4").exists()  # latest target
        assert (root / "latest").is_symlink()
        assert (root / "serial.mk").exists()

    def test_proper_sorting(self, tmp_path: Path) -> None:
        """Serial directories must be sorted numerically, not lexically."""
        root, _ = self._make_helper_config(tmp_path, serials=[1, 5, 7, 12, 23], latest_serial=23)
        cleanup_old_configs(tmp_path)
        assert not (root / "1").exists()
        assert not (root / "5").exists()
        assert not (root / "7").exists()
        assert (root / "12").exists()
        assert (root / "23").exists()
