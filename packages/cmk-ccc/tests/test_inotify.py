#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from cmk.ccc.inotify import Cookie, Event, INotify, Masks, Watchee

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


def test_deleted_directory_is_reported_as_deleted_and_ignored(tmp_path: Path) -> None:
    (directory := tmp_path / "directory").mkdir()
    with INotify() as inotify:
        watchee = inotify.add_watch(directory, Masks.DELETE_SELF)

        directory.rmdir()
        events = inotify.read(timeout=10)

    assert events == [
        Event(watchee, Masks.DELETE_SELF, Cookie(0), ""),
        Event(watchee, Masks.IGNORED, Cookie(0), ""),
    ]


def test_removing_the_watch_of_a_deleted_directory_after_its_events_does_not_raise(
    tmp_path: Path,
) -> None:
    (directory := tmp_path / "directory").mkdir()
    with INotify() as inotify:
        watchee = inotify.add_watch(directory, Masks.DELETE_SELF)
        directory.rmdir()
        inotify.read(timeout=10)

        inotify.rm_watch(watchee)


def _modify_and_access(path: Path, *, times: int) -> None:
    # The kernel only merges identical consecutive events.
    fd = os.open(path, os.O_RDWR)
    try:
        for _ in range(times):
            os.pwrite(fd, b"x", 0)
            os.pread(fd, 1, 0)
    finally:
        os.close(fd)


def test_overflowing_the_event_queue_is_reported(tmp_path: Path) -> None:
    queue_size = int(Path("/proc/sys/fs/inotify/max_queued_events").read_text())
    if queue_size > 65536:
        pytest.skip(f"Overflowing a queue for {queue_size} events would take too long")
    (file := tmp_path / "file").write_bytes(b"x")
    with INotify() as inotify:
        inotify.add_watch(file, Masks.MODIFY | Masks.ACCESS)

        _modify_and_access(file, times=queue_size // 2 + 1)
        events = inotify.read(timeout=0)

    assert events[-1] == Event(Watchee(-1, Path()), Masks.Q_OVERFLOW, Cookie(0), "")


def test_created_and_deleted_directories_are_reported_as_directories(tmp_path: Path) -> None:
    with INotify() as inotify:
        watchee = inotify.add_watch(tmp_path, Masks.CREATE | Masks.DELETE)

        (directory := tmp_path / "directory").mkdir()
        directory.rmdir()
        events = inotify.read(timeout=10)

    assert events == [
        Event(watchee, Masks.CREATE | Masks.ISDIR, Cookie(0), "directory"),
        Event(watchee, Masks.DELETE | Masks.ISDIR, Cookie(0), "directory"),
    ]


def test_deleted_file_is_reported(tmp_path: Path) -> None:
    (file := tmp_path / "file").touch()
    with INotify() as inotify:
        watchee = inotify.add_watch(tmp_path, Masks.DELETE)

        file.unlink()
        events = inotify.read(timeout=10)

    assert events == [Event(watchee, Masks.DELETE, Cookie(0), "file")]


def test_modified_file_is_reported(tmp_path: Path) -> None:
    (file := tmp_path / "file").touch()
    with INotify() as inotify:
        watchee = inotify.add_watch(tmp_path, Masks.MODIFY)

        with file.open("ab") as f:
            f.write(b"x")
        events = inotify.read(timeout=10)

    assert events == [Event(watchee, Masks.MODIFY, Cookie(0), "file")]


# Audit events for starting programs or forking
_PROCESS_STARTS = {
    "_posixsubprocess.fork_exec",
    "os.exec",
    "os.fork",
    "os.forkpty",
    "os.posix_spawn",
    "os.system",
    "subprocess.Popen",
}


def _processes_started_while(action: Callable[[], object]) -> list[str]:
    started: list[str] = []
    recording = True

    def record(event: str, args: tuple[object, ...]) -> None:
        if recording and event in _PROCESS_STARTS:
            started.append(" ".join(str(arg) for arg in (event, *args[:1])))

    # Audit hooks can't be removed, so this one goes quiet afterwards.
    sys.addaudithook(record)
    try:
        action()
    finally:
        recording = False
    return started


def test_watching_starts_no_process(tmp_path: Path) -> None:
    def watch() -> None:
        with INotify() as inotify:
            inotify.add_watch(tmp_path, Masks.CREATE)

    started = _processes_started_while(watch)

    assert started == []
