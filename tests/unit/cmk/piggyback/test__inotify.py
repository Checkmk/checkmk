#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from unittest.mock import ANY

from cmk.piggyback.backend._inotify import Cookie, Event, INotify, Masks, Watchee


def test_basic_event_observing(tmp_path: Path) -> None:
    """This tests the happy path of observing events on a file."""
    folder = tmp_path / "folder"
    file = tmp_path / "file"
    file2 = tmp_path / "file2"

    inotify = INotify()
    watch_flags = (
        Masks.CREATE
        | Masks.DELETE
        | Masks.MODIFY
        | Masks.DELETE_SELF
        | Masks.MOVE_SELF
        | Masks.MOVED_TO
        | Masks.MOVED_FROM
    )
    _wd = inotify.add_watch(tmp_path, watch_flags)

    folder.mkdir()
    file.write_text("watch this!")
    file.write_text("see it?")
    file.rename(file2)
    file2.unlink()
    folder.rmdir()

    tmp_path.rmdir()

    actual = inotify.read()
    assert actual == [
        Event(
            watchee=Watchee(wd=1, path=tmp_path),
            type=Masks.CREATE | Masks.ISDIR,
            cookie=Cookie(),
            name="folder",
        ),
        Event(
            watchee=Watchee(wd=1, path=tmp_path),
            type=Masks.CREATE,
            cookie=Cookie(),
            name="file",
        ),
        Event(
            watchee=Watchee(wd=1, path=tmp_path),
            type=Masks.MODIFY,
            cookie=Cookie(),
            name="file",
        ),
        Event(
            watchee=Watchee(wd=1, path=tmp_path),
            type=Masks.MOVED_FROM,
            cookie=ANY,
            name="file",
        ),
        Event(
            watchee=Watchee(wd=1, path=tmp_path),
            type=Masks.MOVED_TO,
            cookie=ANY,
            name="file2",
        ),
        Event(
            watchee=Watchee(wd=1, path=tmp_path),
            type=Masks.DELETE,
            cookie=Cookie(),
            name="file2",
        ),
        Event(
            watchee=Watchee(wd=1, path=tmp_path),
            type=Masks.DELETE | Masks.ISDIR,
            cookie=Cookie(),
            name="folder",
        ),
        Event(
            watchee=Watchee(wd=1, path=tmp_path),
            type=Masks.DELETE_SELF,
            cookie=Cookie(),
            name="",
        ),
        Event(
            watchee=Watchee(wd=1, path=tmp_path),
            type=Masks.IGNORED,
            cookie=Cookie(),
            name="",
        ),
    ]
    assert isinstance(actual[4].cookie, Cookie)
    assert actual[3].cookie == actual[4].cookie
