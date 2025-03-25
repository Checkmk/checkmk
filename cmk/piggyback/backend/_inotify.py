#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Small wrapper for the kernels `inotify` feature

Existing libraries seem to be rather unmaintained or lack
features that we want (type annotations).

This is quite stripped down to only provide what we currently need,
rather than being a comprehensive interface to what the kernel offers.

As this is currently only needed for the piggyback hub, we put it here.
"""

import enum
import os
from collections.abc import Iterator, Sequence
from ctypes import c_int, CDLL, get_errno
from ctypes.util import find_library
from dataclasses import dataclass
from fcntl import ioctl
from io import FileIO
from os import fsdecode, fsencode
from pathlib import Path
from select import poll
from struct import calcsize, unpack_from
from termios import FIONREAD


class Masks(enum.IntFlag):
    """For watching and describing occurred event.

    This list is outdated (incomplete), but currently
    this is more than enough for our needs.
    """

    # These be passed to add_watch, *and* returned in an Event instance:
    ACCESS = 0x00000001  #: File was accessed
    MODIFY = 0x00000002  #: File was modified
    ATTRIB = 0x00000004  #: Metadata changed
    CLOSE_WRITE = 0x00000008  #: Writable file was closed
    CLOSE_NOWRITE = 0x00000010  #: Unwritable file closed
    OPEN = 0x00000020  #: File was opened
    MOVED_FROM = 0x00000040  #: File was moved from X
    MOVED_TO = 0x00000080  #: File was moved to Y
    CREATE = 0x00000100  #: Subfile was created
    DELETE = 0x00000200  #: Subfile was deleted
    DELETE_SELF = 0x00000400  #: Self was deleted
    MOVE_SELF = 0x00000800  #: Self was moved

    # These can passed to add_watch:
    ONLYDIR = 0x01000000  #: only watch the path if it is a directory
    DONT_FOLLOW = 0x02000000  #: don't follow a sym link
    EXCL_UNLINK = 0x04000000  #: exclude events on unlinked objects
    MASK_ADD = 0x20000000  #: add to the mask of an already existing watch
    ONESHOT = 0x80000000  #: only send event once

    # These are returned in an Event instance:
    UNMOUNT = 0x00002000  #: Backing fs was unmounted
    Q_OVERFLOW = 0x00004000  #: Event queue overflowed
    IGNORED = 0x00008000  #: File was ignored
    ISDIR = 0x40000000  #: event occurred against dir


@dataclass(frozen=True)
class Watchee:
    """Corresponding to the watch descriptor"""

    wd: int
    path: Path


class Cookie(int): ...


@dataclass(frozen=True)
class Event:
    watchee: Watchee
    type: Masks
    cookie: Cookie
    name: str


class _EventParser:
    _FIXED_EVENT_PART = "iIII"
    _FIXED_EVENT_PART_LEN = calcsize(_FIXED_EVENT_PART)

    def __init__(self) -> None:
        self._wd_map: dict[int, Path] = {}

    def track(self, wd: int, path: Path) -> None:
        self._wd_map[wd] = path

    def drop(self, wd: int) -> None:
        self._wd_map.pop(wd)

    def iterate_parsed_events(self, data: bytes) -> Iterator[Event]:
        offset = 0
        while offset < len(data):
            raw_watch_descriptor, raw_event_type, raw_cookie, bytes_remaining = unpack_from(
                self._FIXED_EVENT_PART, data, offset
            )
            raw_name = data[
                offset + self._FIXED_EVENT_PART_LEN : offset
                + self._FIXED_EVENT_PART_LEN
                + bytes_remaining
            ].split(b"\x00", 1)[0]
            offset = offset + self._FIXED_EVENT_PART_LEN + bytes_remaining

            yield Event(
                Watchee(int(raw_watch_descriptor), self._wd_map[raw_watch_descriptor]),
                Masks(raw_event_type),
                Cookie(raw_cookie),
                fsdecode(raw_name),
            )


class _LibCINotify:
    """Wrap the CDLL object for proper typing"""

    __libc: CDLL | None = None

    def __init__(self):
        if self.__libc is None:
            libc_so = find_library("c") or "libc.so.6"
            self.__libc = CDLL(libc_so, use_errno=True)
        self._libc = self.__libc

    def init1(self, flags: int) -> int:
        if (rc := int(self._libc.inotify_init1(flags))) == -1:
            raise OSError(errno := get_errno(), os.strerror(errno))
        return rc

    def add_watch(self, fd: int, path: bytes, mask: int) -> int:
        if (rc := int(self._libc.inotify_add_watch(fd, path, mask))) == -1:
            raise OSError(errno := get_errno(), os.strerror(errno))
        return rc

    def rm_watch(self, fd: int, wd: int) -> None:
        if self._libc.inotify_rm_watch(fd, wd) == -1:
            raise OSError(errno := get_errno(), os.strerror(errno))


class INotify:
    def __init__(self):
        self._libc = _LibCINotify()
        self._parser = _EventParser()
        self._fileio = FileIO(self._libc.init1(os.O_CLOEXEC), mode="rb")
        self._poller = poll()
        self._poller.register(self._fileio.fileno())

    def add_watch(self, path: Path, mask: Masks) -> Watchee:
        watch_descriptor = self._libc.add_watch(self._fileio.fileno(), fsencode(path), mask)
        self._parser.track(watch_descriptor, path)
        return Watchee(watch_descriptor, path)

    def rm_watch(self, watchee: Watchee) -> None:
        self._libc.rm_watch(self._fileio.fileno(), watchee.wd)
        self._parser.drop(watchee.wd)

    def read_forever(self) -> Iterator[Event]:
        while True:
            yield from self.read()

    def read(self, timeout: int | None = None) -> Sequence[Event]:
        """Read occured events once.

        If timeout is set and there are no events, wait up to `timeout`
        seconds. Otherwise block until there are events.
        """
        if timeout is not None and timeout < 0:
            raise ValueError(timeout)
        data = self._read_bytes()
        if (
            not data
            and timeout != 0
            and self._poller.poll(None if timeout is None else timeout * 1000)
        ):
            data = self._read_bytes()
        return list(self._parser.iterate_parsed_events(data))

    def _read_bytes(self) -> bytes:
        readable = c_int()
        ioctl(self._fileio, FIONREAD, readable)
        if not readable.value:
            return b""
        return os.read(self._fileio.fileno(), readable.value)
