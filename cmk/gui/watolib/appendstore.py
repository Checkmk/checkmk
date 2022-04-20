#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import ast
import errno
import os
from pathlib import Path
from typing import Generic, List, TypeVar

import cmk.utils.store as store

from cmk.gui.exceptions import MKGeneralException
from cmk.gui.i18n import _

_VT = TypeVar("_VT")


class ABCAppendStore(Generic[_VT], abc.ABC):
    """Managing a file with structured data that can be appended in a cheap way

    The file holds basic python structures separated by "\0".
    """

    @staticmethod
    @abc.abstractmethod
    def make_path(*args: str) -> Path:
        """Note:
        Abstract static methods do not make any sense.  This should
        be a free function.

        """
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def _serialize(entry: _VT) -> object:
        """Prepare _VT objects for serialization

        Note:
            Abstract static methods do not make any sense.  This should
            either be a free function or on `entry : _VT`.

        Override this to execute some logic before repr()"""
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def _deserialize(raw: object) -> _VT:
        """Create _VT objects from serialized data

        Note:
            Abstract static methods do not make any sense.  This should
            either be a free function or on `entry : _VT`.

        Override this to execute some logic after literal_eval() to produce _VT objects"""
        raise NotImplementedError()

    def __init__(self, path: Path) -> None:
        self._path = path

    def exists(self) -> bool:
        return self._path.exists()

    # TODO: Implement this locking as context manager
    def read(self, lock: bool = False) -> List[_VT]:
        """Parse the file and return the entries"""
        path = self._path

        if lock:
            store.aquire_lock(path)

        entries = []
        try:
            with path.open("rb") as f:
                for entry in f.read().split(b"\0"):
                    if entry:
                        entries.append(self._deserialize(ast.literal_eval(entry.decode("utf-8"))))
        except IOError as e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise
        except Exception:
            if lock:
                store.release_lock(path)
            raise

        return entries

    def write(self, entries: List[_VT]) -> None:
        # First truncate the file
        with self._path.open("wb"):
            pass

        for entry in entries:
            self.append(entry)

    def append(self, entry: _VT) -> None:
        path = self._path
        try:
            store.aquire_lock(path)

            with path.open("ab+") as f:
                f.write(repr(self._serialize(entry)).encode("utf-8") + b"\0")
                f.flush()
                os.fsync(f.fileno())

            path.chmod(0o660)

        except Exception as e:
            raise MKGeneralException(_('Cannot write file "%s": %s') % (path, e))

        finally:
            store.release_lock(path)

    def clear(self) -> None:
        try:
            self._path.unlink()
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass  # Not existant -> OK
            else:
                raise
