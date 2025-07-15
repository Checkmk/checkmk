#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import ast
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Generic, TypeVar

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _

_VT = TypeVar("_VT")


class ABCAppendStore(Generic[_VT], abc.ABC):
    """Managing a file with structured data that can be appended in a cheap way

    The file holds basic python structures separated by "\\0".
    """

    separator = b"\0"

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

    def __read_bytes(self) -> list[bytes]:
        try:
            with self._path.open("rb") as f:
                return [entry for entry in f.read().split(self.separator) if entry]
        except FileNotFoundError:
            return []

    def __write_bytes(self, entries: Sequence[bytes]) -> None:
        try:
            content = self.separator.join(entry for entry in entries)
            store.save_bytes_to_file(self._path, content)
        except Exception as e:
            raise MKGeneralException(_('Cannot write file "%s": %s') % (self._path, e))

    def __to_bytes(self, entry: _VT) -> bytes:
        return repr(self._serialize(entry)).encode("utf-8")

    def read(self) -> Sequence[_VT]:
        """Parse the file and return the entries"""
        with store.locked(self._path):
            try:
                return [
                    self._deserialize(ast.literal_eval(entry.decode("utf-8")))
                    for entry in self.__read_bytes()
                ]
            except SyntaxError as e:
                raise MKUserError(
                    None,
                    _(
                        "The audit log can not be shown because of "
                        "a syntax error in %s.<br><br>Please review and fix the file "
                        "content or remove the file before you visit this page "
                        "again.<br><br>The problematic entry is:<br>%s"
                    )
                    % (self._path, e.text),
                )

    def append(self, entry: _VT) -> None:
        with store.locked(self._path):
            entries = self.__read_bytes()
            entries.append(self.__to_bytes(entry))
            self.__write_bytes(entries)

    @contextmanager
    def mutable_view(self) -> Iterator[list[_VT]]:
        with store.locked(self._path):
            entries = list(self.read())
            try:
                yield entries
            finally:
                self.__write_bytes([self.__to_bytes(entry) for entry in entries])
