#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.ccc.inotify import Cookie, Event, INotify, Masks

# The kernel queues an operation's events before it returns: timeouts only guard against hangs.


def test_created_file_is_reported(tmp_path: Path) -> None:
    with INotify() as inotify:
        watchee = inotify.add_watch(tmp_path, Masks.CREATE)

        (tmp_path / "file").touch()
        events = inotify.read(timeout=10)

    assert events == [Event(watchee, Masks.CREATE, Cookie(0), "file")]


def test_renamed_file_is_reported_with_one_cookie_for_both_names(tmp_path: Path) -> None:
    (tmp_path / "old").touch()
    with INotify() as inotify:
        watchee = inotify.add_watch(tmp_path, Masks.MOVED_FROM | Masks.MOVED_TO)

        (tmp_path / "old").rename(tmp_path / "new")
        moved_from, moved_to = inotify.read(timeout=10)

    assert (moved_from, moved_to) == (
        Event(watchee, Masks.MOVED_FROM, moved_from.cookie, "old"),
        Event(watchee, Masks.MOVED_TO, moved_from.cookie, "new"),
    )
    assert moved_from.cookie != Cookie(0)


def test_read_without_changes_returns_no_events(tmp_path: Path) -> None:
    with INotify() as inotify:
        inotify.add_watch(tmp_path, Masks.CREATE)

        events = inotify.read(timeout=0)

    assert events == []


def test_removed_watch_reports_nothing(tmp_path: Path) -> None:
    with INotify() as inotify:
        inotify.rm_watch(inotify.add_watch(tmp_path, Masks.CREATE))

        (tmp_path / "file").touch()
        events = inotify.read(timeout=0)

    assert events == []


def test_watching_outside_of_the_context_raises(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Context not entered"):
        INotify().add_watch(tmp_path, Masks.CREATE)
