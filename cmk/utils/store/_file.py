#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pickle
import pprint
import tempfile
from ast import literal_eval
from collections.abc import Iterator
from contextlib import contextmanager
from os import getgid, getuid
from pathlib import Path
from stat import S_IMODE, S_IWOTH
from typing import Any, Final, Generic, Protocol, TypeVar

import cmk.utils.debug
from cmk.utils.exceptions import MKGeneralException, MKTerminate, MKTimeout
from cmk.utils.i18n import _

from ._locks import acquire_lock, release_lock

__all__ = [
    "BytesSerializer",
    "DimSerializer",
    "ObjectStore",
    "PickleSerializer",
    "TextSerializer",
]

TObject = TypeVar("TObject")


class Serializer(Protocol[TObject]):
    def serialize(self, data: TObject) -> bytes:
        ...

    def deserialize(self, raw: bytes) -> TObject:
        ...


class BytesSerializer:
    @staticmethod
    def serialize(data: bytes) -> bytes:
        return data

    @staticmethod
    def deserialize(raw: bytes) -> bytes:
        return raw


class TextSerializer:
    @staticmethod
    def serialize(data: str) -> bytes:
        return data.encode("utf-8")

    @staticmethod
    def deserialize(raw: bytes) -> str:
        return raw.decode("utf-8")


class DimSerializer:
    """A dangerous serializer that is not very bright and returns `Any`"""

    def __init__(self, *, pretty: bool = False) -> None:
        self.pretty: Final = pretty

    def serialize(self, data: Any) -> bytes:
        data_str = pprint.pformat(data) if self.pretty else repr(data)
        return f"{data_str}\n".encode()

    @staticmethod
    def deserialize(raw: bytes) -> Any:
        return literal_eval(raw.decode("utf-8"))


class PickleSerializer(Generic[TObject]):
    """A dangerous serializer that uses pickle"""

    def serialize(self, data: TObject) -> bytes:
        return pickle.dumps(data)

    def deserialize(self, raw: bytes) -> TObject:
        obj: TObject = pickle.loads(raw)  # nosec B301 # BNS:9a7128
        return obj


def _raise_for_permissions(path: Path) -> None:
    """Ensure that the file is owned by the current user or root and not world writable.
    Raise an exception otherwise."""
    stat = path.stat()
    # we trust root and ourselves
    owned_by_current_user_or_root = stat.st_uid in [0, getuid()] and stat.st_gid in [0, getgid()]
    world_writable = S_IMODE(stat.st_mode) & S_IWOTH != 0

    if path.resolve() == Path("/etc/cma/backup.conf"):
        # The file is group-owned by omd. To fix this in the appliance will
        # take more time, considering the compatibility with older versions
        # So we check for owner and world and don't care for group...
        if not stat.st_uid in [0, getuid()] or world_writable:
            raise MKGeneralException(
                _("/etc/cma/backup.conf has wrong permissions. Refusing to read file")
            )
        return

    if not owned_by_current_user_or_root:
        raise MKGeneralException(_('Refusing to read file not owned by us: "%s"') % path)
    if world_writable:
        raise MKGeneralException(_('Refusing to read world writable file: "%s"') % path)


class ObjectStore(Generic[TObject]):
    def __init__(self, path: Path, *, serializer: Serializer[TObject]) -> None:
        self.path: Final = path
        self._serializer = serializer

    def __fspath__(self) -> str:
        return str(self.path)

    @contextmanager
    def locked(self) -> Iterator[None]:
        acquired = acquire_lock(self.path)
        try:
            yield
        finally:
            if acquired:
                release_lock(self.path)

    def write_obj(self, obj: TObject) -> None:
        return self._save_bytes_to_file(data=self._serializer.serialize(obj))

    def read_obj(self, *, default: TObject) -> TObject:
        raw = self._load_bytes_from_file()
        return self._serializer.deserialize(raw) if raw else default

    def _save_bytes_to_file(self, *, data: bytes) -> None:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "wb",
                dir=str(self.path.parent),
                prefix=f".{self.path.name}.new",
                delete=False,
            ) as tmp:
                tmp_path = Path(tmp.name)
                tmp_path.chmod(0o660)  # otherwise ObjectStore refuse to read world-writable files
                tmp.write(data)

            tmp_path.rename(self.path)

        except (MKTerminate, MKTimeout):
            raise
        except Exception as e:
            if tmp_path:
                tmp_path.unlink(missing_ok=True)

            # TODO: How to handle debug mode or logging?
            raise MKGeneralException(_('Cannot write configuration file "%s": %s') % (self.path, e))

        finally:
            release_lock(self.path)

    def _load_bytes_from_file(self) -> bytes:
        try:
            _raise_for_permissions(self.path)
            return self.path.read_bytes()
        except FileNotFoundError:
            # Since locking (currently) creates an empty file,
            # there is no semantic difference between an empty and a
            # non-existing file, so we ensure consistency here.
            return b""

        except (MKTerminate, MKTimeout):
            raise
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKGeneralException(_('Cannot read file "%s": %s') % (self.path, e))
