# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Rebuild a target whenever its source packages change."""

import contextlib
import errno
import fnmatch
import logging
import os
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path, PurePosixPath
from typing import NamedTuple, override

from watchdog.events import (
    DirCreatedEvent,
    DirDeletedEvent,
    DirMovedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer
from watchdog.observers.api import ObservedWatch

from bazel_devserver.errors import DevServerError

_logger = logging.getLogger(__name__)

_DEBOUNCE_S = 0.2
"""Lets the writes of one editor save or refactoring land in one build."""

_IGNORED_DIRS = frozenset({"__pycache__"})

_SCRATCH_FILES = (
    ".*.sw?",  # vim swap files
    "4913",  # vim's probe whether it may write the directory
    "*~",  # backups of vim and emacs
    ".#*",  # emacs locks
    "#*#",  # emacs autosaves
    "*___jb_tmp___",  # JetBrains safe writes
    "*___jb_old___",
    ".coverage",
)
"""Files that editors and tools write next to sources, which are never sources themselves."""

_CHANGE_EVENTS: list[type[FileSystemEvent]] = [
    FileCreatedEvent,
    FileModifiedEvent,
    FileDeletedEvent,
    FileMovedEvent,
    DirCreatedEvent,
    DirDeletedEvent,
    DirMovedEvent,
]


def _inotify_limit_hint(error: OSError) -> str | None:
    match error.errno:
        case errno.ENOSPC:
            limit = "max_user_watches=524288"
        case errno.EMFILE:
            limit = "max_user_instances=512"
        case _:
            return None
    return (
        "Close other programs that watch files, or raise the limit:\n"
        f"  sudo sysctl fs.inotify.{limit}"
    )


class _WatchRoot(NamedTuple):
    path: Path
    recursive: bool


class _Packages:
    """Bazel packages given by name; ``""`` is the root package, which owns only its own files."""

    def __init__(self, names: Iterable[str]) -> None:
        self.names = frozenset(names)
        self._root = "" in self.names
        self._others = tuple(PurePosixPath(name) for name in self.names if name)

    def contain(self, path: PurePosixPath) -> bool:
        """Whether *path*, relative to the repository root, lies within one of the packages."""
        return (self._root and len(path.parts) == 1) or any(
            path.is_relative_to(package) for package in self._others
        )

    def watch_roots(self, repo_root: Path) -> set[_WatchRoot]:
        """Watch the packages' top-level directories, as each watch costs an inotify instance.

        A user gets 128 instances by default, shared with editors and desktop services.
        """
        roots = {_WatchRoot(repo_root, recursive=False)} if self._root else set()
        return roots | {
            _WatchRoot(repo_root / top_level, recursive=True)
            for top_level in {package.parts[0] for package in self._others}
            if (repo_root / top_level).is_dir()
        }


def _bazel_ignored(repo_root: Path) -> tuple[PurePosixPath, ...]:
    """The directories ``.bazelignore`` hides from Bazel, relative to the repository root."""
    try:
        lines = (repo_root / ".bazelignore").read_text().splitlines()
    except OSError:
        return ()
    return tuple(
        PurePosixPath(line)
        for line in (line.strip() for line in lines)
        if line and not line.startswith("#")
    )


def _is_package_definition(path: PurePosixPath) -> bool:
    return path.name in ("BUILD", "BUILD.bazel")


def _is_build_file(path: PurePosixPath) -> bool:
    return _is_package_definition(path) or path.suffix == ".bzl"


def _is_scratch_file(path: PurePosixPath) -> bool:
    return any(fnmatch.fnmatchcase(path.name, pattern) for pattern in _SCRATCH_FILES)


class RebuildLoop(FileSystemEventHandler):
    """Runs *build* after changes below the packages *query* returns, then *notify*.

    *notify* receives whether the build succeeded.  A change during a build
    starts another one.  A changed BUILD or ``.bzl`` file makes the loop
    query the packages again after the next build is notified, and build
    once more if packages were added; so does a BUILD file anywhere below
    the watched directories, which may define a package the target
    depends on by now.  A failed query is repeated after the next build.
    Changes below the directories in ``.bazelignore``, which Bazel does not
    see, and below ``__pycache__``, and editor scratch files are ignored.
    Any error is warned about and notified as a failed build.
    """

    def __init__(
        self,
        repo_root: Path,
        query: Callable[[], Sequence[str]],
        build: Callable[[], bool],
        notify: Callable[[bool], None],
    ) -> None:
        self._repo_root = repo_root
        self._query = query
        self._build = build
        self._notify = notify
        self._observer = Observer()
        self._packages = _Packages(())
        self._ignored: tuple[PurePosixPath, ...] = ()
        self._watches: dict[_WatchRoot, ObservedWatch] = {}
        self._changed = threading.Condition()
        self._dirty = False
        self._build_files_changed = False
        self._stopped = threading.Event()
        self._notifying = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        """Watch the queried packages; returns once changes are being watched."""
        self._watch(self._query())
        try:
            self._observer.start()
        except OSError as e:
            raise DevServerError(
                f"Cannot watch the sources: {e}", recovery=_inotify_limit_hint(e)
            ) from e
        self._thread.start()

    def stop(self, interrupt: Callable[[], None]) -> None:
        """Stop watching; a running build is ended by *interrupt* and not reported."""
        with self._changed:
            self._stopped.set()
            self._changed.notify()
        interrupt()
        if self._thread.is_alive():
            self._thread.join()
        self._observer.stop()
        if self._observer.is_alive():
            self._observer.join()

    @override
    def on_any_event(self, event: FileSystemEvent) -> None:
        try:
            self._record(event)
        except Exception as e:
            self._fail(e)

    def _record(self, event: FileSystemEvent) -> None:
        paths = [
            PurePosixPath(Path(os.fsdecode(p)).relative_to(self._repo_root))
            for p in (event.src_path, event.dest_path)
            if p
        ]
        changed = [p for p in paths if self._is_relevant(p, event.is_directory)]
        if not changed:
            return
        with self._changed:
            self._dirty = True
            self._build_files_changed |= any(_is_build_file(p) for p in changed)
            self._changed.notify()

    def _is_relevant(self, path: PurePosixPath, is_directory: bool) -> bool:
        """Whether *path*, relative to the repository root, is a source or defines a package."""
        directories = path.parts if is_directory else path.parts[:-1]
        if any(part in _IGNORED_DIRS for part in directories) or any(
            path.is_relative_to(ignored) for ignored in self._ignored
        ):
            return False
        if is_directory:
            return self._packages.contain(path)
        return _is_package_definition(path) or (
            self._packages.contain(path) and not _is_scratch_file(path)
        )

    def _watch(self, packages: Sequence[str]) -> None:
        """Watch *packages*; they count as known only once all of their directories are watched."""
        self._ignored = _bazel_ignored(self._repo_root)
        watched = _Packages(packages)
        roots = watched.watch_roots(self._repo_root)
        for root in self._watches.keys() - roots:
            self._observer.unschedule(self._watches.pop(root))
        for root in roots - self._watches.keys():
            self._watches[root] = self._observer.schedule(
                self, str(root.path), recursive=root.recursive, event_filter=_CHANGE_EVENTS
            )
        self._packages = watched

    def _run(self) -> None:
        while True:
            with self._changed:
                self._changed.wait_for(lambda: self._dirty or self._stopped.is_set())
            time.sleep(_DEBOUNCE_S)
            with self._changed:
                if self._stopped.is_set():
                    return
                self._dirty = False
                requery, self._build_files_changed = self._build_files_changed, False
            try:
                self._rebuild(requery)
            except Exception as e:
                self._fail(e)

    def _rebuild(self, requery: bool) -> None:
        succeeded = self._build()
        if self._stopped.is_set():
            return
        self._report(succeeded)
        if requery:
            self._requery()

    def _requery(self) -> None:
        known = self._packages.names
        try:
            self._watch(self._query())
        except Exception:
            with self._changed:
                self._build_files_changed = True
            raise
        if self._packages.names - known:
            with self._changed:
                self._dirty = True

    def _report(self, succeeded: bool) -> None:
        with self._notifying:
            self._notify(succeeded)

    def _fail(self, error: Exception) -> None:
        _logger.warning("Rebuilding on changes failed: %(error)s", {"error": error})
        with contextlib.suppress(Exception):
            self._report(False)
