#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pprint
import tempfile
from ast import literal_eval
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Final, Generic, Iterator, Protocol, TypeVar

import cmk.utils.debug
from cmk.utils.exceptions import MKGeneralException, MKTerminate, MKTimeout
from cmk.utils.i18n import _
from cmk.utils.store._locks import aquire_lock, have_lock, release_lock

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
        return f"{data_str}\n".encode("utf-8")

    @staticmethod
    def deserialize(raw: bytes) -> Any:
        return literal_eval(raw.decode("utf-8"))


class ObjectStore(Generic[TObject]):
    def __init__(self, path: Path, *, serializer: Serializer[TObject]) -> None:
        self.path: Final = path
        self._serializer = serializer

    def __fspath__(self) -> str:
        return str(self.path)

    @contextmanager
    def locked(self) -> Iterator[None]:
        already_locked = have_lock(self.path)
        aquire_lock(self.path)  # no-op if already_locked
        try:
            yield
        finally:
            if not already_locked:
                release_lock(self.path)

    def write_obj(self, obj: TObject, *, mode: int = 0o660) -> None:
        return self._save_bytes_to_file(data=self._serializer.serialize(obj), mode=mode)

    def read_obj(self, *, default: TObject) -> TObject:
        raw = self._load_bytes_from_file()
        return self._serializer.deserialize(raw) if raw else default

    def _save_bytes_to_file(self, *, data: bytes, mode: int) -> None:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "wb",
                dir=str(self.path.parent),
                prefix=".%s.new" % self.path.name,
                delete=False,
            ) as tmp:

                tmp_path = Path(tmp.name)
                tmp_path.chmod(mode)
                tmp.write(data)

                # The goal of the fsync would be to ensure that there is a consistent file after a
                # crash. Without the fsync it may happen that the file renamed below is just an empty
                # file. That may lead into unexpected situations during loading.
                #
                # Don't do a fsync here because this may run into IO performance issues. Even when
                # we can specify the fsync on a fd, the disk cache may be flushed completely because
                # the disk does not know anything about fds, only about blocks.
                #
                # For Checkmk 1.4 we can not introduce a good solution for this, because the changes
                # would affect too many parts of Checkmk with possible new issues. For the moment we
                # stick with the IO behaviour of previous Checkmk versions.
                #
                # In the future we'll find a solution to deal better with OS crash recovery situations.
                # for example like this:
                #
                # TODO(lm): The consistency of the file will can be ensured using copies of the
                # original file which are made before replacing it with the new one. After first
                # successful loading of the just written fille the possibly existing copies of this
                # file are deleted.
                # We can archieve this by calling os.link() before the os.rename() below. Then we need
                # to define in which situations we want to check out the backup open(s) and in which
                # cases we can savely delete them.
                # tmp.flush()
                # os.fsync(tmp.fileno())

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
            try:
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
