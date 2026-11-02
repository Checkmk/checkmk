# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Rebuild a target whenever its source packages change."""

import contextlib
import errno
import fnmatch
import functools
import logging
import os
import resource
import threading
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path, PurePosixPath
from typing import NamedTuple, override, TYPE_CHECKING

from bazel_devserver.errors import DevServerError
from watchdog.events import (
    DirCreatedEvent,
    DirDeletedEvent,
    DirMovedEvent,
    FileAttribEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEvent,
    FileSystemEventHandler,
)

if TYPE_CHECKING:
    from watchdog.observers.api import BaseObserver, ObservedWatch
    from watchdog.observers.inotify import InotifyWatchGroup
    from watchdog.observers.inotify_c import InotifyEvent, WatchDescriptor

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
    # e.g. chmod +x, which Bazel tracks. FileAttribEvent alone doesn't make watchdog subscribe
    # to IN_ATTRIB; FileModifiedEvent above does.
    FileAttribEvent,
    FileDeletedEvent,
    FileMovedEvent,
    DirCreatedEvent,
    DirDeletedEvent,
    DirMovedEvent,
]


def _inotify_limit_hint(error: OSError) -> str | None:
    match error.errno:
        case errno.ENOSPC:
            limit = "max_user_watches"
        case errno.EMFILE if _file_descriptors_used_up():
            if (open_files := _raised_open_files_limit()) is None:
                return (
                    "Raise the hard limit of open files of your user, which needs root, e.g. in"
                    " /etc/security/limits.conf, and log in again"
                )
            return (
                "Raise the limit of open files of the shell starting the dev server:\n"
                f"  ulimit -n {open_files}"
            )
        case errno.EMFILE:
            limit = "max_user_instances"
        case _:
            return None
    return (
        "Close other programs that watch files, or raise the limit:\n"
        f"  sudo sysctl fs.inotify.{limit}={_raised_inotify_limit(limit)}"
    )


def _cannot_watch(error: OSError) -> DevServerError:
    return DevServerError(f"Cannot watch the sources: {error}", recovery=_inotify_limit_hint(error))


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
        """Watch the packages' top-level directories, which covers new BUILD files next to them.

        Such a BUILD file may define a package the target depends on by now. Each directory below
        the top-level directories costs one of the user's inotify watches.
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


def _start_observer() -> BaseObserver:
    # Importing the observer creates watchdog's inotify instance, which may exceed the user's
    # limit of instances, so the import is part of starting to watch.
    from watchdog.observers.inotify import InotifyObserver

    _patch_watchdog()
    observer = InotifyObserver()
    observer.start()
    return observer


# _patch_watchdog(), the functions it patches watchdog with, _warn_about_unwatched_directories(),
# _watching, _recording_unwatched_directories(), _failing_on_unwatched_directories(),
# _raised_inotify_limit(), _file_descriptors_used_up() and _raised_open_files_limit() are copies of
# those in cmk/automations/helper/_watcher.py, adapted to this module. Sharing them would give the
# devserver an additional dependency, which it should not get, and cmk cannot depend on the
# devserver. Change both together.


@functools.cache
def _patch_watchdog() -> None:
    """Keep errors in watchdog's bookkeeping from ending its reader thread, and log new directories
    it cannot watch as the watches are used up.

    watchdog 7.0.0 handles all events in one reader thread, and an error ends it, so no change is
    noticed from then on. The patches fix two such errors and log any other: the KeyError for the
    contents of a new directory that could not be watched, and the one for a path another watch has
    taken over and dropped. The latter also breaks stopping to watch, which leaves watchdog's
    threads blocked. watchdog also ignores that it cannot watch a new directory, so changes below it
    would go unnoticed without a trace. The patches apply to this version only, as others may
    change the code they replace, so constraints.txt holds watchdog back. Another version gets a
    warning instead, and the tests show whether it still needs them.
    """
    import watchdog.version
    from watchdog.observers.inotify import InotifyWatchGroup

    if watchdog.version.VERSION_STRING != "7.0.0":
        _logger.warning(
            "Not patching watchdog %(version)s, the patches are for 7.0.0 only",
            {"version": watchdog.version.VERSION_STRING},
        )
        return
    InotifyWatchGroup._add_callback = _add_callback  # type: ignore[method-assign]  # noqa: SLF001
    add_all_callbacks = InotifyWatchGroup._add_all_callbacks  # noqa: SLF001
    InotifyWatchGroup._add_all_callbacks = _reporting_unwatched_directories(add_all_callbacks)  # type: ignore[method-assign,assignment]  # noqa: SLF001
    InotifyWatchGroup._recursive_simulate = _recursive_simulate  # type: ignore[method-assign]  # noqa: SLF001
    InotifyWatchGroup._remove_watch_internally = _remove_watch_internally  # type: ignore[method-assign]  # noqa: SLF001
    InotifyWatchGroup.on_event = _logging_errors(InotifyWatchGroup.on_event)  # type: ignore[method-assign,assignment]
    InotifyWatchGroup.on_watch_deleted = _logging_errors(InotifyWatchGroup.on_watch_deleted)  # type: ignore[method-assign,assignment]


def _logging_errors[T](
    handle: Callable[[InotifyWatchGroup, T], None],
) -> Callable[[InotifyWatchGroup, T], None]:
    """*handle* of ``InotifyWatchGroup``, but it logs an error instead of raising it."""

    @functools.wraps(handle)
    def logging_errors(self: InotifyWatchGroup, arg: T) -> None:
        try:
            handle(self, arg)
        except Exception:
            _logger.exception(
                "Handling a change below %(path)s failed, some changes there may go unnoticed",
                {"path": os.fsdecode(self.path)},
            )

    return logging_errors


def _reporting_unwatched_directories(
    add_all_callbacks: Callable[[InotifyWatchGroup, bytes], None],
) -> Callable[[InotifyWatchGroup, bytes], None]:
    """watchdog's ``InotifyWatchGroup._add_all_callbacks``, but it logs the directories it cannot
    watch as the watches are used up in one warning, not in one per directory, e.g. for a copied
    tree.

    While _recording_unwatched_directories() runs, e.g. when watching starts, it leaves them to it.
    """

    @functools.wraps(add_all_callbacks)
    def reporting_unwatched_directories(self: InotifyWatchGroup, path: bytes) -> None:
        if _watching.unwatched is not None:
            add_all_callbacks(self, path)
            return
        unwatched: list[bytes] = []
        with _recording_unwatched_directories(unwatched):
            add_all_callbacks(self, path)
        if unwatched:
            _warn_about_unwatched_directories(unwatched)

    return reporting_unwatched_directories


def _recursive_simulate(self: InotifyWatchGroup, src_path: bytes) -> list[InotifyEvent]:
    """watchdog's ``InotifyWatchGroup._recursive_simulate``, but it names the entries of a directory
    without a watch relative to its closest watched ancestor instead of raising a KeyError."""
    from watchdog.observers.inotify_c import InotifyConstants, InotifyEvent, Mask

    events: list[InotifyEvent] = []
    for directory, dirnames, filenames in os.walk(src_path, followlinks=self.follow_symlink):
        watched = directory
        while watched not in self._active_callbacks_by_path and watched != os.path.dirname(watched):
            watched = os.path.dirname(watched)
        if (wd := self._active_callbacks_by_path.get(watched)) is None:
            continue
        prefix = os.path.relpath(directory, watched)
        events.extend(
            InotifyEvent(
                wd,
                Mask(InotifyConstants.IN_CREATE | InotifyConstants.IN_ISDIR),
                0,
                os.path.normpath(os.path.join(prefix, name)),
            )
            for name in dirnames
        )
        events.extend(
            InotifyEvent(
                wd, InotifyConstants.IN_CREATE, 0, os.path.normpath(os.path.join(prefix, name))
            )
            for name in filenames
        )
    return events


def _remove_watch_internally(self: InotifyWatchGroup, wd: WatchDescriptor) -> None:
    """watchdog's ``InotifyWatchGroup._remove_watch_internally``, but it leaves a path that is gone
    alone instead of raising a KeyError.

    watchdog keeps the path of a directory moved out of the watched ones. A directory created in its
    place takes the path over, and deleting that directory drops the path.
    """
    path = self._active_callbacks_by_watch.pop(wd)
    if self._active_callbacks_by_path.get(path) == wd:
        del self._active_callbacks_by_path[path]


def _add_callback(self: InotifyWatchGroup, path: bytes) -> None:
    """watchdog's ``InotifyWatchGroup._add_callback``, but it logs a new directory it cannot watch
    as the watches are used up instead of ignoring it.

    While _recording_unwatched_directories() runs, e.g. in _reporting_unwatched_directories() or
    _failing_on_unwatched_directories(), it records the directory instead, so that all of them are
    reported in one go.
    """
    try:
        wd = self._inotify_fd.add_callback(path, self.event_mask, self._callback, self._id)
    except OSError as e:
        # Directories below the watched one may vanish while they are added, but a failure to
        # watch the watched one itself must reach the caller.
        if path == self.path:
            raise
        if e.errno != errno.ENOSPC:
            return
        if (unwatched := _watching.unwatched) is not None:
            unwatched.append(path)
        else:
            _warn_about_unwatched_directories([path])
        return
    self._active_callbacks_by_path[path] = wd
    self._active_callbacks_by_watch[wd] = path


def _warn_about_unwatched_directories(unwatched: Sequence[bytes]) -> None:
    """Log that watchdog cannot watch the new directories *unwatched* as the watches are used up."""
    error = OSError(errno.ENOSPC, "inotify watch limit reached")
    _logger.warning(
        "Cannot watch %(path)s%(more)s: %(error)s, later changes there go unnoticed until the dev"
        " server restarts\n%(recovery)s",
        {
            "path": os.fsdecode(unwatched[0]),
            "more": f" and {len(unwatched) - 1} more" if len(unwatched) > 1 else "",
            "error": error,
            "recovery": _inotify_limit_hint(error),
        },
    )


class _Watching(threading.local):
    unwatched: list[bytes] | None = None
    """The directories watchdog cannot watch as the watches are used up, while
    _recording_unwatched_directories() runs in this thread."""


_watching = _Watching()


@contextlib.contextmanager
def _recording_unwatched_directories(unwatched: list[bytes]) -> Iterator[None]:
    """Record in *unwatched* the directories watchdog cannot watch in this context in this thread,
    as the user's inotify watches are used up, instead of logging each of them."""
    previous, _watching.unwatched = _watching.unwatched, unwatched
    try:
        yield
    finally:
        _watching.unwatched = previous


@contextlib.contextmanager
def _failing_on_unwatched_directories() -> Iterator[None]:
    """Raise an OSError if watchdog cannot watch a directory in this context as the user's inotify
    watches are used up.

    watchdog ignores errors while watching the subdirectories of a watched directory, so the patched
    _add_callback() records them for this. Watches used up otherwise, e.g. by another program, don't
    matter, as watchdog reuses the watch of a directory watched already.
    """
    unwatched: list[bytes] = []
    with _recording_unwatched_directories(unwatched):
        yield
    if unwatched:
        raise OSError(errno.ENOSPC, "inotify watch limit reached", os.fsdecode(unwatched[0]))


def _raised_inotify_limit(name: str) -> str:
    """Twice the current value of the inotify limit *name*, whose default depends on the kernel
    and the memory."""
    try:
        return str(2 * int(Path("/proc/sys/fs/inotify", name).read_text()))
    except OSError, ValueError:
        return "<higher value>"


def _file_descriptors_used_up() -> bool:
    """Whether this process cannot open another file, as its limit of open files is reached.

    inotify_init() fails with EMFILE both then and when the user's inotify instances are used up.
    """
    try:
        os.close(os.open(os.devnull, os.O_RDONLY))
    except OSError as e:
        return e.errno == errno.EMFILE
    return False


def _raised_open_files_limit() -> int | None:
    """The limit of open files to raise the soft one to without root: the hard one if the soft one
    is below it, else None. Linux has no unlimited hard limit for open files."""
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    return hard if soft < hard else None


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
        self._observer: BaseObserver | None = None
        self._packages = _Packages(())
        self._ignored: tuple[PurePosixPath, ...] = ()
        self._watches: dict[_WatchRoot, ObservedWatch] = {}
        self._package_watches: dict[str, ObservedWatch] = {}
        self._changed = threading.Condition()
        self._dirty = False
        self._build_files_changed = False
        self._stopped = threading.Event()
        self._notifying = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        """Watch the queried packages; returns once changes are being watched."""
        packages = self._query()
        try:
            self._observer = _start_observer()
        except OSError as e:
            raise _cannot_watch(e) from e
        try:
            # This fails for the directories there are now only: a directory created later while
            # the watches are used up stays unwatched, which the patched watchdog logs.
            self._watch(packages)
        except BaseException:
            self._stop_observer()
            raise
        self._thread.start()

    def stop(self, interrupt: Callable[[], None]) -> None:
        """Stop watching; a running build is ended by *interrupt* and not reported."""
        with self._changed:
            self._stopped.set()
            self._changed.notify()
        interrupt()
        if self._thread.is_alive():
            self._thread.join()
        self._stop_observer()

    def _stop_observer(self) -> None:
        if (observer := self._observer) is not None:
            self._observer = None
            self._watches.clear()
            self._package_watches.clear()
            observer.stop()
            if observer.is_alive():
                observer.join()

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
        if (observer := self._observer) is None:
            raise RuntimeError("The rebuild loop was not started")
        self._ignored = _bazel_ignored(self._repo_root)
        watched = _Packages(packages)
        roots = watched.watch_roots(self._repo_root)
        # watchdog skips directories it cannot watch, e.g. while the watches are used up, so a
        # root may lack watches. So a new package below a watched root gets a watch of its own,
        # again on the next call if that failed. watchdog shares watches, so this only adds the
        # ones the root lacks, and changes below the package are reported twice, which is
        # harmless. Rewatching the root would walk all of it, and known packages could lose their
        # watches. Directories created below known packages while the watches are used up, or
        # moved in from outside, stay unwatched.
        added = {
            name
            for name in watched.names - self._packages.names
            if name
            and _WatchRoot(self._repo_root / PurePosixPath(name).parts[0], recursive=True)
            in self._watches
            and (self._repo_root / name).is_dir()
        }
        try:
            for root in self._watches.keys() - roots:
                observer.unschedule(self._watches.pop(root))
            for name in (self._package_watches.keys() - watched.names) | (
                self._package_watches.keys() & added
            ):
                observer.unschedule(self._package_watches.pop(name))
            with _failing_on_unwatched_directories():
                for root in roots - self._watches.keys():
                    self._watches[root] = observer.schedule(
                        self, str(root.path), recursive=root.recursive, event_filter=_CHANGE_EVENTS
                    )
                for name in added:
                    # watchdog tells watches apart by their path, so "/." keeps the watch of a
                    # top-level package apart from its root's
                    self._package_watches[name] = observer.schedule(
                        self,
                        f"{self._repo_root / name}/.",
                        recursive=True,
                        event_filter=_CHANGE_EVENTS,
                    )
        except OSError as e:
            raise _cannot_watch(e) from e
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
