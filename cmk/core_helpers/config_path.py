"""Fetcher config path manipulation."""
from __future__ import annotations

import abc
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Final, Iterator

import cmk.utils.paths
import cmk.utils.store as store

__all__ = ["root", "ConfigPath", "VersionedConfigPath", "LATEST_CONFIG"]


def root() -> Path:
    return cmk.utils.paths.core_helper_config_dir


def _serial_mk() -> Path:
    return root() / "serial.mk"


class ConfigPath(abc.ABC):
    __slots__ = ()

    @property
    @abc.abstractmethod
    def _path_elem(self) -> str:
        raise NotImplementedError()

    def __str__(self) -> str:
        return self._path_elem

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, os.PathLike):
            return False
        return Path(self) == Path(other)

    def __hash__(self) -> int:
        return hash(type(self)) ^ hash(self._path_elem)

    def __fspath__(self) -> str:
        return str(root() / self._path_elem)


class VersionedConfigPath(ConfigPath, Iterator):
    __slots__ = ("serial",)

    def __init__(self, serial: int) -> None:
        super().__init__()
        self.serial: Final = serial

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.serial})"

    @property
    def _path_elem(self) -> str:
        return str(self.serial)

    @classmethod
    def current(cls) -> VersionedConfigPath:
        serial: int = store.load_object_from_file(
            _serial_mk(),
            default=0,
            lock=True,
        )
        return cls(serial)

    def __iter__(self) -> Iterator[VersionedConfigPath]:
        serial = self.serial
        while True:
            serial += 1
            store.save_object_to_file(_serial_mk(), serial)
            yield VersionedConfigPath(serial)

    def __next__(self) -> VersionedConfigPath:
        serial = self.serial + 1
        store.save_object_to_file(_serial_mk(), serial)
        return VersionedConfigPath(serial)

    @contextmanager
    def create(self, *, is_cmc: bool) -> Iterator[None]:
        if not is_cmc:
            # CMC manages the configs on its own.
            self._cleanup()
        Path(self).mkdir(parents=True, exist_ok=True)
        yield
        # TODO(ml) We should probably remove the files that were created
        #          previously and not update `serial.mk` on error.
        self._link_latest()

    def _cleanup(self) -> None:
        if not root().exists():
            return

        for path in root().iterdir():
            if path.is_symlink() or not path.is_dir():
                continue

            if path.resolve() == Path(LATEST_CONFIG).resolve():
                continue

            shutil.rmtree(path)

    def _link_latest(self) -> None:
        Path(LATEST_CONFIG).unlink(missing_ok=True)
        Path(LATEST_CONFIG).symlink_to(Path(self).name)


class _LatestConfigPath(ConfigPath):
    __slots__ = ()

    @property
    def _path_elem(self) -> str:
        return "latest"

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


# Singleton
LATEST_CONFIG: Final = _LatestConfigPath()
