#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import errno
import functools
import logging
import os
import resource
import threading
import time
from collections.abc import Callable, Generator, Sequence
from pathlib import Path
from typing import override, TYPE_CHECKING

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler

from ._cache import Cache, CacheError
from ._config import WatcherConfig

if TYPE_CHECKING:
    from watchdog.observers.api import BaseObserver
    from watchdog.observers.inotify import InotifyWatchGroup
    from watchdog.observers.inotify_c import InotifyEvent, WatchDescriptor

LOGGER = logging.getLogger(__name__)


@contextlib.contextmanager
def run(config: WatcherConfig, cache: Cache) -> Generator[None]:
    LOGGER.info("[watcher] Initializing")
    with _marking_unwatched_changes(cache):
        try:
            observer = _start_observer(config, cache)
        except Exception as e:
            LOGGER.exception(
                "[watcher] Error while starting observer%(hint)s", {"hint": _inotify_limit_hint(e)}
            )
            raise
        LOGGER.info("[watcher] Operational")
        try:
            yield
        finally:
            LOGGER.info("[watcher] Shutting down")
            try:
                observer.stop()
                observer.join()
            except Exception:
                # cmk-automation-helper exits without a trace otherwise, as it has daemonized.
                # Some of watchdog's threads may stay blocked, but they don't keep the process
                # alive.
                LOGGER.exception("[watcher] Error while shutting down")
                raise
            LOGGER.info("[watcher] Shutdown complete")


class _Running:
    cache: Cache | None = None
    """The cache of the watcher running in this process, in which the patched watchdog marks that
    changes may go unnoticed."""


_running = _Running()


@contextlib.contextmanager
def _marking_unwatched_changes(cache: Cache) -> Generator[None]:
    """Let the patched watchdog mark in *cache* that changes may go unnoticed, after forgetting
    such a mark of an earlier run."""
    _store_changes_unwatched(cache, unwatched=False)
    _running.cache = cache
    try:
        yield
    finally:
        _running.cache = None


def _mark_changes_unwatched() -> None:
    """Mark in the cache of the running watcher that changes may go unnoticed, so that each
    automation reloads the configuration until the automation helper restarts.

    It marks in a thread of its own, as it runs in watchdog's reader thread, which a slow Redis must
    not hold up: the kernel drops events once its queue for them is full.
    """
    if (cache := _running.cache) is not None:
        threading.Thread(
            target=_store_changes_unwatched,
            args=(cache,),
            kwargs={"unwatched": True},
            name="watcher-mark",
            daemon=True,
        ).start()


def _store_changes_unwatched(cache: Cache, *, unwatched: bool) -> None:
    try:
        cache.store_changes_unwatched(unwatched=unwatched)
    # not only CacheError: Redis may time out, too, and an error in the thread marking would be lost
    except Exception:
        LOGGER.exception("[watcher] Error while storing whether changes may go unnoticed")


def _start_observer(config: WatcherConfig, cache: Cache) -> BaseObserver:
    # Importing any watchdog.observers module creates watchdog's process-wide inotify instance
    # and starts its reader thread. The thread doesn't survive a fork, e.g. the one in
    # daemonize(), and the inotify instance would then never be read. So import the observers
    # here, in the process actually running the watcher, and fail if another module, e.g.
    # werkzeug's reloader, has imported them before the fork.
    from watchdog.observers.inotify import InotifyObserver
    from watchdog.observers.inotify_c import InotifyFD
    from watchdog.observers.inotify_move_event_grouper import InotifyMoveEventGrouper

    if not InotifyFD.get_instance().is_alive():
        raise RuntimeError(
            "watchdog's inotify reader thread is not running,"
            " probably as watchdog.observers was imported before a fork"
        )

    _patch_watchdog()

    # watchdog holds IN_MOVED_FROM back for up to `delay` seconds to pair it with IN_MOVED_TO,
    # and later events wait, too, see "Dealing with rename() events" in inotify(7). Its default
    # of 0.5s could make an automation call right after a save miss the reload; saves rename
    # within one directory, so they are usually paired at once. Zero is too short, though:
    # watchdog follows a renamed directory, e.g. a moved Setup folder, only if it pairs the
    # events in time, else directories created in it later go unwatched. A directory moved in
    # from outside the watched ones is never watched.
    InotifyMoveEventGrouper.delay = 0.05

    observer = InotifyObserver(generate_full_events=True)
    for schedule in config.schedules:
        handler = _AutomationWatcherHandler(
            cache=cache,
            patterns=schedule.patterns,
            ignore_directories=schedule.ignore_directories,
        )
        observer.schedule(
            handler,
            path=str(schedule.path),
            recursive=schedule.recursive,
        )
    try:
        # This checks the start only: a directory created later while the watches are used up,
        # e.g. a new Setup folder, stays unwatched until the automation helper restarts. The
        # patched watchdog logs it and makes each automation reload the configuration until then.
        with _failing_on_unwatched_directories():
            observer.start()
    except BaseException:
        observer.stop()
        if observer.is_alive():
            observer.join()
        raise
    return observer


def _inotify_limit_hint(error: Exception) -> str:
    match error:
        case OSError(errno=errno.ENOSPC):
            limit = "max_user_watches"
        case OSError(errno=errno.EMFILE) if _file_descriptors_used_up():
            if (open_files := _raised_open_files_limit()) is None:
                return (
                    ", raise the hard limit of open files of the site user as root,"
                    " e.g. in /etc/security/limits.conf"
                )
            return (
                ", raise the limit of open files, e.g. with:"
                f" ulimit -n {open_files} before omd start"
            )
        case OSError(errno=errno.EMFILE):
            limit = "max_user_instances"
        case _:
            return ""
    return (
        ", raise the inotify limit as root, e.g. with:"
        f" sysctl fs.inotify.{limit}={_raised_inotify_limit(limit)}"
    )


# _raised_inotify_limit(), _file_descriptors_used_up(), _raised_open_files_limit(), _watching,
# _recording_unwatched_directories(), _failing_on_unwatched_directories(), _patch_watchdog(), the
# functions it patches watchdog with and _warn_about_unwatched_directories() are copies of those in
# bazel/tools/devserver/bazel_devserver/rebuild_loop.py, adapted to this module, e.g. by marking
# that changes may go unnoticed. Sharing them would give the devserver an additional dependency,
# which it should not get, and this module cannot depend on the devserver. Change both together.


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


class _Watching(threading.local):
    unwatched: list[bytes] | None = None
    """The directories watchdog cannot watch as the watches are used up, while
    _recording_unwatched_directories() runs in this thread."""


_watching = _Watching()


@contextlib.contextmanager
def _recording_unwatched_directories(unwatched: list[bytes]) -> Generator[None]:
    """Record in *unwatched* the directories watchdog cannot watch in this context in this thread,
    as the user's inotify watches are used up, instead of logging each of them."""
    previous, _watching.unwatched = _watching.unwatched, unwatched
    try:
        yield
    finally:
        _watching.unwatched = previous


@contextlib.contextmanager
def _failing_on_unwatched_directories() -> Generator[None]:
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
        LOGGER.warning(
            "[watcher] Not patching watchdog %(version)s, the patches are for 7.0.0 only",
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
    """*handle* of ``InotifyWatchGroup``, but it logs an error instead of raising it, and marks
    that changes may go unnoticed."""

    @functools.wraps(handle)
    def logging_errors(self: InotifyWatchGroup, arg: T) -> None:
        try:
            handle(self, arg)
        except Exception:
            LOGGER.exception(
                "[watcher] Error while handling a change below %(path)s, so each automation"
                " reloads the configuration until the automation helper restarts",
                {"path": os.fsdecode(self.path)},
            )
            _mark_changes_unwatched()

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
    """Log that watchdog cannot watch the new directories *unwatched* as the watches are used up,
    and mark that changes may go unnoticed."""
    error = OSError(errno.ENOSPC, "inotify watch limit reached")
    LOGGER.warning(
        "[watcher] Cannot watch %(path)s%(more)s: %(error)s, so each automation reloads the"
        " configuration until the automation helper restarts%(hint)s",
        {
            "path": os.fsdecode(unwatched[0]),
            "more": f" and {len(unwatched) - 1} more" if len(unwatched) > 1 else "",
            "error": error,
            "hint": _inotify_limit_hint(error),
        },
    )
    _mark_changes_unwatched()


class _AutomationWatcherHandler(PatternMatchingEventHandler):
    def __init__(
        self,
        *,
        cache: Cache,
        patterns: Sequence[str] | None,
        ignore_directories: bool,
    ) -> None:
        self._cache = cache
        patterns_ = list(patterns) if patterns else None
        super().__init__(patterns=patterns_, ignore_directories=ignore_directories)

    @override
    def on_moved(self, event: FileSystemEvent) -> None:
        self._store_last_detected_change(time.time())
        self._log_handled_event(event)

    @override
    def on_created(self, event: FileSystemEvent) -> None:
        self._store_last_detected_change(time.time())
        self._log_handled_event(event)

    @override
    def on_modified(self, event: FileSystemEvent) -> None:
        self._store_last_detected_change(time.time())
        self._log_handled_event(event)

    @override
    def on_deleted(self, event: FileSystemEvent) -> None:
        self._store_last_detected_change(time.time())
        self._log_handled_event(event)

    @override
    def on_attrib(self, event: FileSystemEvent) -> None:
        self._store_last_detected_change(time.time())
        self._log_handled_event(event)

    def _store_last_detected_change(self, time: float) -> None:
        try:
            self._cache.store_last_detected_change(time)
        except CacheError:
            LOGGER.exception("[watcher] Cache failure")

    @classmethod
    def _log_handled_event(cls, event: FileSystemEvent) -> None:
        LOGGER.info(
            "[watcher] Source: %(src_path)s, destination: %(dest_path)s, type: %(type)s",
            {
                "src_path": _decode_if_necessary(event.src_path) or "n/a",
                "dest_path": _decode_if_necessary(event.dest_path) or "n/a",
                "type": event.event_type,
            },
        )


def _decode_if_necessary(v: str | bytes, encoding: str = "utf-8") -> str:
    return v if isinstance(v, str) else v.decode(encoding)
