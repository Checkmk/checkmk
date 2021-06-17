"""Fetcher config path manipulation."""
from __future__ import annotations

import abc
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Final, Iterator, Literal, NewType, Union

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.type_defs import HostName

__all__ = [
    "LATEST_SERIAL",
    "ConfigSerial",
    "OptionalConfigSerial",
    "ConfigPath",
    "VersionedConfigPath",
    "LatestConfigPath",
    "LATEST_CONFIG",
    "make_helper_config_path",
    "make_fetchers_config_path",
    "make_local_config_path",
    "make_global_config_path",
]

# LATEST_SERIAL, ConfigSerial, and OptionalConfigSerial are deprecated.

LATEST_SERIAL: Final[Literal["latest"]] = "latest"
# TODO(ml): The strings in ConfigSerial look like this: "0", "1", "2"...
#           We should use `int` or even better make a full-blown
#           abstraction out of that.
#           See also: a few of its "methods" are below.
ConfigSerial = NewType("ConfigSerial", str)
OptionalConfigSerial = Union[ConfigSerial, Literal["latest"]]


class ConfigPath(abc.ABC):
    __slots__ = ()

    ROOT: Final = cmk.utils.paths.core_helper_config_dir

    @property
    @abc.abstractmethod
    def _path_elem(self) -> str:
        raise NotImplementedError()

    def __str__(self) -> str:
        return self._path_elem

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, ConfigPath):
            return False
        return self._path_elem == other._path_elem

    def __hash__(self) -> int:
        return hash(type(self)) ^ hash(self._path_elem)

    def __truediv__(self, other: Union[str, Path]) -> Path:
        try:
            return Path(str(self)) / other
        except TypeError:
            return NotImplemented

    def __rtruediv__(self, other: Union[str, Path]) -> Path:
        try:
            return Path(other) / str(self)
        except TypeError:
            return NotImplemented

    def helper_config_path(self) -> Path:
        return self.ROOT / self._path_elem

    def fetchers_config_path(self) -> Path:
        return self.helper_config_path() / "fetchers"

    def local_config_path(self, host_name: HostName) -> Path:
        return self.fetchers_config_path() / "hosts" / f"{host_name}.json"

    def global_config_path(self) -> Path:
        return self.fetchers_config_path() / "global_config.json"


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
            cmk.utils.paths.core_helper_config_dir / "serial.mk",
            default=0,
            lock=True,
        )
        return cls(serial)

    def __iter__(self) -> Iterator[VersionedConfigPath]:
        serial = self.serial
        while True:
            serial += 1
            store.save_object_to_file(
                cmk.utils.paths.core_helper_config_dir / "serial.mk",
                serial,
            )
            yield VersionedConfigPath(serial)

    def __next__(self) -> VersionedConfigPath:
        serial = self.serial + 1
        store.save_object_to_file(
            cmk.utils.paths.core_helper_config_dir / "serial.mk",
            serial,
        )
        return VersionedConfigPath(serial)

    @contextmanager
    def create(self, *, is_cmc: bool) -> Iterator[None]:
        if not is_cmc:
            # CMC manages the configs on its own.
            self._cleanup()
        self.helper_config_path().mkdir(parents=True, exist_ok=True)
        yield
        # TODO(ml) We should probably remove the files that were created
        #          previously and not update `serial.mk` on error.
        self._link_latest()

    def _cleanup(self) -> None:
        if not self.ROOT.exists():
            return

        for path in self.ROOT.iterdir():
            if path.is_symlink() or not path.is_dir():
                continue

            if path.resolve() == LATEST_CONFIG.helper_config_path().resolve():
                continue

            shutil.rmtree(path)

    def _link_latest(self) -> None:
        LATEST_CONFIG.helper_config_path().unlink(missing_ok=True)
        LATEST_CONFIG.helper_config_path().symlink_to(self.helper_config_path().name)


class LatestConfigPath(ConfigPath):
    __slots__ = ()

    @property
    def _path_elem(self) -> str:
        return "latest"

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


# Singleton
LATEST_CONFIG: Final = LatestConfigPath()


def _from_deprecated(config_paths: Union[ConfigPath, str]) -> ConfigPath:
    if isinstance(config_paths, str):
        # Deprecated!!
        try:
            return VersionedConfigPath(int(config_paths))
        except ValueError:
            # int(config_paths) failed
            return LatestConfigPath()

    assert isinstance(config_paths, ConfigPath), repr(config_paths)
    return config_paths


def make_helper_config_path(config_paths: Union[ConfigPath, str]) -> Path:
    return _from_deprecated(config_paths).helper_config_path()


def make_fetchers_config_path(config_paths: Union[ConfigPath, str]) -> Path:
    return _from_deprecated(config_paths).fetchers_config_path()


def make_local_config_path(config_paths: Union[ConfigPath, str], host_name: HostName) -> Path:
    return _from_deprecated(config_paths).local_config_path(host_name)


def make_global_config_path(config_paths: Union[ConfigPath, str]) -> Path:
    return _from_deprecated(config_paths).global_config_path()
