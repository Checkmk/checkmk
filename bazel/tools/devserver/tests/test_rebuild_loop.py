# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import ctypes
import errno
import os
import re
import resource
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from bazel_devserver.errors import DevServerError
from bazel_devserver.rebuild_loop import RebuildLoop


class _DevServer:
    """Fake query, build and notify callables; builds can be held until released.

    The log records each query and each notified build result, in order.
    """

    def __init__(self, packages: list[str]) -> None:
        self.packages = packages
        self.query_errors: list[Exception] = []
        self.build_results: list[bool | Exception] = []
        self.build_started = threading.Event()
        self.build_may_finish = threading.Event()
        self.build_may_finish.set()
        self.log: list[str] = []
        self._logged = threading.Condition()

    def query(self) -> list[str]:
        self._append("query")
        if self.query_errors:
            raise self.query_errors.pop(0)
        return list(self.packages)

    def build(self) -> bool:
        self.build_started.set()
        self.build_may_finish.wait()
        result = self.build_results.pop(0) if self.build_results else True
        if isinstance(result, Exception):
            raise result
        return result

    def notify(self, succeeded: bool) -> None:
        self._append("success" if succeeded else "failure")

    @property
    def notifications(self) -> list[str]:
        return [entry for entry in self.log if entry != "query"]

    def wait_for_builds(self, count: int, timeout: float = 5.0) -> bool:
        with self._logged:
            return self._logged.wait_for(lambda: len(self.notifications) >= count, timeout)

    def wait_for_queries(self, count: int, timeout: float = 5.0) -> bool:
        with self._logged:
            return self._logged.wait_for(lambda: self.log.count("query") >= count, timeout)

    def _append(self, entry: str) -> None:
        with self._logged:
            self.log.append(entry)
            self._logged.notify_all()


class _InotifyWatches:
    """Simulates the user's limit of inotify watches; ``free`` is ``None`` for no limit.

    Like the kernel, it charges no watch for a directory that is watched already."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from watchdog.observers import inotify_c

        self.free: int | None = None
        add_watch = inotify_c.inotify_add_watch
        rm_watch = inotify_c.inotify_rm_watch

        def limited_add_watch(fd: int, path: bytes, mask: int) -> int:
            wd = add_watch(fd, path, mask)
            watched = inotify_c.InotifyFD.get_instance()._watch_for_wd  # noqa: SLF001
            if self.free is None or wd == -1 or wd in watched:
                return wd
            if self.free == 0:
                rm_watch(fd, wd)  # the kernel would not have added it
                ctypes.set_errno(errno.ENOSPC)
                return -1
            self.free -= 1
            return wd

        # The system call is a boundary we cannot inject.
        monkeypatch.setattr(inotify_c, "inotify_add_watch", limited_add_watch)


def _fail_to_watch(monkeypatch: pytest.MonkeyPatch, directory: Path) -> None:
    """Make watching *directory* fail as if the watches were used up, but not watching others, as
    when the watches are used up just then and free again right after."""
    from watchdog.observers import inotify_c

    add_watch = inotify_c.inotify_add_watch

    def failing_add_watch(fd: int, path: bytes, mask: int) -> int:
        if path != os.fsencode(directory):
            return add_watch(fd, path, mask)
        ctypes.set_errno(errno.ENOSPC)
        return -1

    # The system call is a boundary we cannot inject.
    monkeypatch.setattr(inotify_c, "inotify_add_watch", failing_add_watch)


def _fail_to_watch_once_filled(
    monkeypatch: pytest.MonkeyPatch, directory: Path, file_name: str
) -> None:
    """Make watching *directory* fail as if the watches were used up, once the file *file_name*
    has appeared in it, as when the file is written right after creating the directory."""
    from watchdog.observers import inotify_c

    add_watch = inotify_c.inotify_add_watch

    def failing_add_watch(fd: int, path: bytes, mask: int) -> int:
        if path != os.fsencode(directory):
            return add_watch(fd, path, mask)
        (directory / file_name).touch()
        ctypes.set_errno(errno.ENOSPC)
        return -1

    # The system call is a boundary we cannot inject.
    monkeypatch.setattr(inotify_c, "inotify_add_watch", failing_add_watch)


def _fail_to_watch_once_nested(
    monkeypatch: pytest.MonkeyPatch, directory: Path, nested: str
) -> None:
    """Make watching *directory* and the directories below it fail as if the watches were used up,
    once the directories *nested* have appeared in it, as when a tree is copied in."""
    from watchdog.observers import inotify_c

    add_watch = inotify_c.inotify_add_watch

    def failing_add_watch(fd: int, path: bytes, mask: int) -> int:
        if not Path(os.fsdecode(path)).is_relative_to(directory):
            return add_watch(fd, path, mask)
        (directory / nested).mkdir(parents=True, exist_ok=True)
        ctypes.set_errno(errno.ENOSPC)
        return -1

    # The system call is a boundary we cannot inject.
    monkeypatch.setattr(inotify_c, "inotify_add_watch", failing_add_watch)


def _use_up_inotify_instances(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make creating watchdog's inotify instance fail as if the user's instances were used up."""
    from watchdog.observers import inotify_c

    def failing_inotify_init() -> int:
        ctypes.set_errno(errno.EMFILE)
        return -1

    # watchdog's process-wide instance and the system call are boundaries we cannot inject.
    # Without the instance, watchdog creates it anew.
    monkeypatch.setattr(inotify_c.InotifyFD, "_instance", None)
    monkeypatch.setattr(inotify_c, "inotify_init", failing_inotify_init)


@contextlib.contextmanager
def _used_up_file_descriptors(
    monkeypatch: pytest.MonkeyPatch, *, up_to_the_hard_limit: bool = False
) -> Iterator[None]:
    """Lower this process's limit of open files to the files it has open, so that creating
    watchdog's inotify instance fails; *up_to_the_hard_limit* reports that limit as the hard one,
    too."""
    from watchdog.observers import inotify_c

    # watchdog's process-wide instance is a boundary we cannot inject. Without it, watchdog
    # creates it anew.
    monkeypatch.setattr(inotify_c.InotifyFD, "_instance", None)
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    lowest_free = os.open(os.devnull, os.O_RDONLY)
    os.close(lowest_free)
    resource.setrlimit(resource.RLIMIT_NOFILE, (lowest_free, hard))
    if up_to_the_hard_limit:
        getrlimit = resource.getrlimit

        def getrlimit_at_hard_limit(which: int) -> tuple[int, int]:
            if which == resource.RLIMIT_NOFILE:
                return lowest_free, lowest_free
            return getrlimit(which)

        # The system call is a boundary we cannot inject, and lowering the hard limit for real
        # could not be undone.
        monkeypatch.setattr(resource, "getrlimit", getrlimit_at_hard_limit)
    try:
        yield
    finally:
        resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))


def _make_watchdog_fail(monkeypatch: pytest.MonkeyPatch, directory: Path) -> None:
    """Make watchdog fail unexpectedly to handle the creation of *directory*, as a bug in it would."""
    from watchdog.observers import inotify_c

    add_watch = inotify_c.inotify_add_watch

    def failing_add_watch(fd: int, path: bytes, mask: int) -> int:
        if path == os.fsencode(directory):
            raise RuntimeError("bug in watchdog")
        return add_watch(fd, path, mask)

    # The system call is a boundary we cannot inject.
    monkeypatch.setattr(inotify_c, "inotify_add_watch", failing_add_watch)


def _reuse_the_place_of_a_moved_out_directory(
    dev_server: _DevServer, directory: Path, outside: Path
) -> None:
    """Create *directory*, move it to *outside*, then create and delete a directory in its place;
    each step is built.

    watchdog 7.0.0 keeps the path of a directory moved out of the watched directories. The new
    directory takes the path over and deleting it drops the path, so watchdog looks the path up in
    vain when it stops watching the moved directory."""
    directory.mkdir()
    dev_server.wait_for_builds(1)  # so the directory has a watch
    outside.mkdir()
    directory.rename(outside / directory.name)
    dev_server.wait_for_builds(2)
    directory.mkdir()
    dev_server.wait_for_builds(3)  # so the directory in its place has a watch
    directory.rmdir()
    dev_server.wait_for_builds(4)
    (directory.parent / "app.ts").write_text("export const app = 2\n")
    # watchdog handles the changes in order, so it has handled the deletion by now
    dev_server.wait_for_builds(5)


@pytest.fixture(name="inotify_watches")
def fixture_inotify_watches(monkeypatch: pytest.MonkeyPatch) -> _InotifyWatches:
    return _InotifyWatches(monkeypatch)


@pytest.fixture(name="package")
def fixture_package(tmp_path: Path) -> Path:
    package = tmp_path / "packages" / "app"
    package.mkdir(parents=True)
    (package / "app.ts").write_text("export const app = 1\n")
    return package


@pytest.fixture(name="packages")
def fixture_packages(tmp_path: Path, package: Path) -> list[str]:
    return [package.relative_to(tmp_path).as_posix()]


@pytest.fixture(name="dev_server")
def fixture_dev_server(packages: list[str]) -> _DevServer:
    return _DevServer(packages)


@pytest.fixture(name="bazelignore")
def fixture_bazelignore() -> str | None:
    """The content of the repository's ``.bazelignore``; ``None`` for none."""
    return None


@pytest.fixture(name="loop")
def fixture_loop(
    tmp_path: Path, dev_server: _DevServer, bazelignore: str | None
) -> Iterator[RebuildLoop]:
    if bazelignore is not None:
        (tmp_path / ".bazelignore").write_text(bazelignore)
    loop = RebuildLoop(tmp_path, dev_server.query, dev_server.build, dev_server.notify)
    loop.start()
    yield loop
    loop.stop(interrupt=dev_server.build_may_finish.set)


pytestmark = pytest.mark.usefixtures("loop")


def test_modified_file_triggers_rebuild(package: Path, dev_server: _DevServer) -> None:
    (package / "app.ts").write_text("export const app = 2\n")

    assert dev_server.wait_for_builds(1)


def test_failed_build_is_reported_as_failure(package: Path, dev_server: _DevServer) -> None:
    dev_server.build_results.append(False)

    (package / "app.ts").write_text("export const app = 2\n")

    assert dev_server.wait_for_builds(1)
    assert dev_server.notifications == ["failure"]


def test_build_error_is_reported_as_failure(package: Path, dev_server: _DevServer) -> None:
    dev_server.build_results.append(RuntimeError("bazel vanished"))

    (package / "app.ts").write_text("export const app = 2\n")

    assert dev_server.wait_for_builds(1)
    assert dev_server.notifications == ["failure"]


def test_change_after_build_error_triggers_rebuild(package: Path, dev_server: _DevServer) -> None:
    dev_server.build_results.append(RuntimeError("bazel vanished"))
    (package / "app.ts").write_text("export const app = 2\n")
    dev_server.wait_for_builds(1)

    (package / "app.ts").write_text("export const app = 3\n")

    assert dev_server.wait_for_builds(2)


def test_file_saved_by_rename_triggers_rebuild(package: Path, dev_server: _DevServer) -> None:
    saved = package.parent / "app.ts.tmp"
    saved.write_text("export const app = 2\n")

    saved.replace(package / "app.ts")

    assert dev_server.wait_for_builds(1)


def test_deleted_file_triggers_rebuild(package: Path, dev_server: _DevServer) -> None:
    (package / "app.ts").unlink()

    assert dev_server.wait_for_builds(1)


def test_file_made_executable_triggers_rebuild(package: Path, dev_server: _DevServer) -> None:
    (package / "app.ts").chmod(0o755)

    assert dev_server.wait_for_builds(1)


def test_file_added_to_new_subdirectory_triggers_rebuild(
    package: Path, dev_server: _DevServer
) -> None:
    subdirectory = package / "components"
    subdirectory.mkdir()
    dev_server.wait_for_builds(1)

    (subdirectory / "new.ts").write_text("export const new = 1\n")

    assert dev_server.wait_for_builds(2)


def test_change_during_build_triggers_another_build(package: Path, dev_server: _DevServer) -> None:
    dev_server.build_may_finish.clear()
    (package / "app.ts").write_text("export const app = 2\n")
    assert dev_server.build_started.wait(5.0)

    (package / "app.ts").write_text("export const app = 3\n")
    dev_server.build_may_finish.set()

    assert dev_server.wait_for_builds(2)


def test_stop_waits_for_the_running_build(
    package: Path, dev_server: _DevServer, loop: RebuildLoop
) -> None:
    dev_server.build_may_finish.clear()
    (package / "app.ts").write_text("export const app = 2\n")
    assert dev_server.build_started.wait(5.0)

    stopping = threading.Thread(target=loop.stop, args=(lambda: None,))
    stopping.start()
    stopping.join(0.5)

    assert stopping.is_alive()


def test_interrupted_build_is_not_reported(
    package: Path, dev_server: _DevServer, loop: RebuildLoop
) -> None:
    dev_server.build_results.append(False)
    dev_server.build_may_finish.clear()
    (package / "BUILD").write_text("")
    assert dev_server.build_started.wait(5.0)

    loop.stop(interrupt=dev_server.build_may_finish.set)

    assert dev_server.log == ["query"]


def test_build_is_reported_before_the_packages_are_queried_again(
    package: Path, dev_server: _DevServer
) -> None:
    (package / "BUILD").write_text("")

    assert dev_server.wait_for_queries(2)
    assert dev_server.log[:3] == ["query", "success", "query"]


def test_package_added_by_build_file_change_is_built(
    tmp_path: Path, package: Path, packages: list[str], dev_server: _DevServer
) -> None:
    (tmp_path / "added").mkdir()
    packages.append("added")

    (package / "BUILD").write_text("")

    assert dev_server.wait_for_builds(2)


def test_package_added_by_build_file_change_is_watched(
    tmp_path: Path, package: Path, packages: list[str], dev_server: _DevServer
) -> None:
    (tmp_path / "added").mkdir()
    packages.append("added")
    (package / "BUILD").write_text("")
    dev_server.wait_for_builds(2)

    (tmp_path / "added" / "new.ts").write_text("export const new = 1\n")

    assert dev_server.wait_for_builds(3)


def test_package_added_while_watches_are_used_up_is_watched_once_they_are_free(
    tmp_path: Path,
    package: Path,
    packages: list[str],
    dev_server: _DevServer,
    inotify_watches: _InotifyWatches,
) -> None:
    (tmp_path / "added" / "sub").mkdir(parents=True)
    packages.append("added")
    inotify_watches.free = 1  # for added/, but not for added/sub/
    (package / "BUILD").write_text("")
    dev_server.wait_for_builds(2)  # the build, then the failure to watch the added package
    inotify_watches.free = None
    (package / "BUILD").write_text("# changed\n")
    dev_server.wait_for_builds(4)  # the build, then the one for the added package

    (tmp_path / "added" / "sub" / "new.ts").write_text("export const new = 1\n")

    assert dev_server.wait_for_builds(5)


def test_package_created_while_watches_are_used_up_is_watched_once_they_are_free(
    tmp_path: Path,
    package: Path,
    packages: list[str],
    dev_server: _DevServer,
    inotify_watches: _InotifyWatches,
) -> None:
    created = package.parent / "created"
    inotify_watches.free = 0
    created.mkdir()  # below the watched packages/, but without a watch
    packages.append(created.relative_to(tmp_path).as_posix())
    (package / "BUILD").write_text("")
    dev_server.wait_for_builds(2)  # the build, then the failure to watch the created package
    inotify_watches.free = None
    (package / "BUILD").write_text("# changed\n")
    dev_server.wait_for_builds(4)  # the build, then the one for the created package

    (created / "new.ts").write_text("export const new = 1\n")

    assert dev_server.wait_for_builds(5)


def test_known_package_stays_watched_when_a_new_package_cannot_be_watched(
    tmp_path: Path,
    package: Path,
    packages: list[str],
    dev_server: _DevServer,
    inotify_watches: _InotifyWatches,
) -> None:
    created = package.parent / "created"
    inotify_watches.free = 0
    created.mkdir()  # below the watched packages/, but without a watch
    (package / "app.ts").write_text("export const app = 2\n")
    dev_server.wait_for_builds(1)  # the watcher has seen the empty created/ by now
    (created / "sub").mkdir()  # without a watch, as created/ has none
    packages.append(created.relative_to(tmp_path).as_posix())
    inotify_watches.free = 1  # for created/, but not for created/sub/
    (package / "BUILD").write_text("")
    dev_server.wait_for_builds(3)  # the build, then the failure to watch the created package

    (package / "app.ts").write_text("export const app = 3\n")

    assert dev_server.wait_for_builds(4)


def test_change_triggers_rebuild_after_a_new_directory_cannot_be_watched(
    package: Path, dev_server: _DevServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    _fail_to_watch_once_filled(monkeypatch, package / "new", "new.ts")
    (package / "new").mkdir()
    dev_server.wait_for_builds(1)  # the build for new/

    (package / "app.ts").write_text("export const app = 2\n")

    assert dev_server.wait_for_builds(2)


def test_new_directory_that_cannot_be_watched_is_reported_with_a_hint(
    caplog: pytest.LogCaptureFixture,
    package: Path,
    dev_server: _DevServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fail_to_watch_once_filled(monkeypatch, package / "new", "new.ts")

    (package / "new").mkdir()
    dev_server.wait_for_builds(1)  # the build for new/

    assert any(
        f"Cannot watch {package / 'new'}:" in message and "sudo sysctl fs.inotify." in message
        for message in caplog.messages
    )


def test_new_directory_tree_that_cannot_be_watched_is_reported_once(
    caplog: pytest.LogCaptureFixture,
    package: Path,
    dev_server: _DevServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fail_to_watch_once_nested(monkeypatch, package / "new", "sub/subsub")

    (package / "new").mkdir()
    dev_server.wait_for_builds(1)  # the build for new/, after watchdog tried to watch it

    assert sum("Cannot watch" in message for message in caplog.messages) == 1


def test_change_triggers_rebuild_after_watchdog_fails_to_handle_an_event(
    package: Path, dev_server: _DevServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_watchdog_fail(monkeypatch, package / "new")
    (package / "new").mkdir()

    (package / "app.ts").write_text("export const app = 2\n")

    assert dev_server.wait_for_builds(1)


def test_loop_stops_after_the_place_of_a_moved_out_directory_was_reused(
    tmp_path: Path, package: Path, dev_server: _DevServer, loop: RebuildLoop
) -> None:
    _reuse_the_place_of_a_moved_out_directory(dev_server, package / "new", tmp_path / "outside")

    loop.stop(interrupt=dev_server.build_may_finish.set)


def test_watches_used_up_after_the_start_fail_no_build_that_needs_no_new_watch(
    package: Path, dev_server: _DevServer, inotify_watches: _InotifyWatches
) -> None:
    inotify_watches.free = 0  # e.g. by another program
    (package / "BUILD").write_text("")
    dev_server.wait_for_builds(1)  # the build, then the query of the same packages

    (package / "app.ts").write_text("export const app = 2\n")

    assert dev_server.wait_for_builds(2)
    assert dev_server.notifications == ["success", "success"]


def test_used_up_watches_are_reported_with_twice_the_current_limit(
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
    package: Path,
    packages: list[str],
    dev_server: _DevServer,
    inotify_watches: _InotifyWatches,
) -> None:
    current_limit = int(Path("/proc/sys/fs/inotify/max_user_watches").read_text())
    (tmp_path / "added" / "sub").mkdir(parents=True)
    packages.append("added")
    inotify_watches.free = 1  # for added/, but not for added/sub/

    (package / "BUILD").write_text("")
    dev_server.wait_for_builds(2)  # the build, then the failure to watch the added package

    assert _suggested_limit(caplog.text, "max_user_watches") == 2 * current_limit


def test_used_up_watches_keep_the_loop_from_starting(
    tmp_path: Path, dev_server: _DevServer, inotify_watches: _InotifyWatches
) -> None:
    loop = _loop_for_other_repository(tmp_path, dev_server)
    inotify_watches.free = 1  # for packages/, but not for packages/app/

    with pytest.raises(DevServerError, match="sudo sysctl fs.inotify.max_user_watches="):
        loop.start()


def test_directory_that_cannot_be_watched_keeps_the_loop_from_starting(
    tmp_path: Path, dev_server: _DevServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    loop = _loop_for_other_repository(tmp_path, dev_server)
    _fail_to_watch(monkeypatch, tmp_path / "other" / "packages" / "app")

    with pytest.raises(DevServerError, match="sudo sysctl fs.inotify.max_user_watches="):
        loop.start()


def test_used_up_file_descriptors_keep_the_loop_from_starting(
    tmp_path: Path, dev_server: _DevServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    loop = _loop_for_other_repository(tmp_path, dev_server)

    with (
        pytest.raises(DevServerError, match="\n  ulimit -n "),
        _used_up_file_descriptors(monkeypatch),
    ):
        loop.start()


def test_used_up_file_descriptors_at_the_hard_limit_keep_the_loop_from_starting(
    tmp_path: Path, dev_server: _DevServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    loop = _loop_for_other_repository(tmp_path, dev_server)

    with (
        pytest.raises(DevServerError, match="\nRaise the hard limit of open files of your user"),
        _used_up_file_descriptors(monkeypatch, up_to_the_hard_limit=True),
    ):
        loop.start()


def test_used_up_inotify_instances_keep_the_loop_from_starting(
    tmp_path: Path, dev_server: _DevServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    loop = _loop_for_other_repository(tmp_path, dev_server)
    _use_up_inotify_instances(monkeypatch)

    with pytest.raises(DevServerError, match="sudo sysctl fs.inotify.max_user_instances="):
        loop.start()


def test_failed_start_leaves_no_thread_behind(
    tmp_path: Path, dev_server: _DevServer, inotify_watches: _InotifyWatches
) -> None:
    loop = _loop_for_other_repository(tmp_path, dev_server)
    inotify_watches.free = 1  # for packages/, but not for packages/app/
    threads = threading.active_count()

    with contextlib.suppress(DevServerError):
        loop.start()

    assert threading.active_count() == threads


def test_loop_started_again_after_a_failed_start_watches_the_packages(
    tmp_path: Path, dev_server: _DevServer, inotify_watches: _InotifyWatches
) -> None:
    loop = _loop_for_other_repository(tmp_path, dev_server)
    inotify_watches.free = 1  # for packages/, but not for packages/app/
    with contextlib.suppress(DevServerError):
        loop.start()
    inotify_watches.free = None

    try:
        loop.start()
        (tmp_path / "other" / "packages" / "app" / "new.ts").write_text("export const new = 1\n")

        assert dev_server.wait_for_builds(1)
    finally:
        loop.stop(interrupt=dev_server.build_may_finish.set)


def test_package_below_a_watched_root_is_built_while_watches_are_used_up(
    tmp_path: Path, packages: list[str], dev_server: _DevServer, inotify_watches: _InotifyWatches
) -> None:
    loop = _loop_for_other_repository(tmp_path, dev_server)
    added = tmp_path / "other" / "packages" / "added"
    (added / "sub").mkdir(parents=True)

    try:
        loop.start()
        inotify_watches.free = 0  # e.g. by another program, but packages/added/ is watched already
        packages.append("packages/added")
        (tmp_path / "other" / "packages" / "app" / "BUILD").write_text("")
        dev_server.wait_for_builds(2)  # the build, then the one for the added package
        (added / "sub" / "new.ts").write_text("export const new = 1\n")

        assert dev_server.wait_for_builds(3)
        assert dev_server.notifications == ["success", "success", "success"]
    finally:
        loop.stop(interrupt=dev_server.build_may_finish.set)


def _suggested_limit(text: str, name: str) -> int:
    """The value *text* suggests for the inotify limit *name*, or 0 if it suggests none."""
    return int(match[1]) if (match := re.search(rf"sysctl fs\.inotify\.{name}=(\d+)", text)) else 0


def _loop_for_other_repository(tmp_path: Path, dev_server: _DevServer) -> RebuildLoop:
    """A loop besides the started one, for a repository with the same packages."""
    repo_root = tmp_path / "other"
    for package in dev_server.packages:
        (repo_root / package).mkdir(parents=True)
    return RebuildLoop(repo_root, dev_server.query, dev_server.build, dev_server.notify)


def test_failed_query_is_repeated_after_next_build(package: Path, dev_server: _DevServer) -> None:
    dev_server.query_errors.append(RuntimeError("no such package"))
    (package / "BUILD").write_text("")
    dev_server.wait_for_queries(2)

    (package / "app.ts").write_text("export const app = 2\n")

    assert dev_server.wait_for_queries(3)


def test_build_file_outside_the_packages_triggers_query(
    tmp_path: Path, dev_server: _DevServer
) -> None:
    added = tmp_path / "packages" / "added"
    added.mkdir()

    (added / "BUILD").write_text("")

    assert dev_server.wait_for_queries(2)


class TestRootPackage:
    @pytest.fixture(name="packages")
    def fixture_packages(self, tmp_path: Path, package: Path) -> list[str]:
        return ["", (package.parent / "other").relative_to(tmp_path).as_posix()]

    def test_top_level_file_triggers_rebuild(self, tmp_path: Path, dev_server: _DevServer) -> None:
        (tmp_path / "MODULE.bazel").write_text("")

        assert dev_server.wait_for_builds(1)

    def test_file_below_another_directory_triggers_no_rebuild(
        self, package: Path, dev_server: _DevServer
    ) -> None:
        (package / "app.ts").write_text("export const app = 2\n")

        assert not dev_server.wait_for_builds(1, timeout=0.5)


def test_change_outside_the_packages_triggers_no_rebuild(
    tmp_path: Path, dev_server: _DevServer
) -> None:
    other = tmp_path / "packages" / "other"
    other.mkdir()

    (other / "other.ts").write_text("export const other = 1\n")

    assert not dev_server.wait_for_builds(1, timeout=0.5)


@pytest.mark.parametrize(
    "name",
    [
        pytest.param(".app.ts.swp", id="vim swap file"),
        pytest.param("4913", id="vim write probe"),
        pytest.param("app.ts~", id="backup"),
        pytest.param("#app.ts#", id="emacs autosave"),
        pytest.param("app.ts___jb_tmp___", id="JetBrains safe write"),
        pytest.param(".coverage", id="coverage data"),
    ],
)
def test_scratch_file_triggers_no_rebuild(package: Path, dev_server: _DevServer, name: str) -> None:
    (package / name).write_text("")

    assert not dev_server.wait_for_builds(1, timeout=0.5)


def test_dot_file_triggers_rebuild(package: Path, dev_server: _DevServer) -> None:
    (package / ".eslintrc.json").write_text("{}\n")

    assert dev_server.wait_for_builds(1)


def test_change_in_pycache_triggers_no_rebuild(package: Path, dev_server: _DevServer) -> None:
    pycache = package / "__pycache__"
    pycache.mkdir()

    (pycache / "app.cpython-314.pyc").write_bytes(b"")

    assert not dev_server.wait_for_builds(1, timeout=0.5)


def test_change_in_dot_directory_triggers_rebuild(package: Path, dev_server: _DevServer) -> None:
    cargo = package / ".cargo"
    cargo.mkdir()
    dev_server.wait_for_builds(1)

    (cargo / "config.toml").write_text("")

    assert dev_server.wait_for_builds(2)


class TestBazelIgnore:
    @pytest.fixture(name="bazelignore")
    def fixture_bazelignore(self) -> str:
        return "# installed by pnpm\n\npackages/app/node_modules\n"

    @pytest.mark.parametrize("name", ["module.js", "BUILD"])
    def test_change_in_ignored_directory_triggers_no_rebuild(
        self, package: Path, dev_server: _DevServer, name: str
    ) -> None:
        ignored = package / "node_modules"
        ignored.mkdir()

        (ignored / name).write_text("")

        assert not dev_server.wait_for_builds(1, timeout=0.5)

    def test_change_next_to_ignored_directory_triggers_rebuild(
        self, package: Path, dev_server: _DevServer
    ) -> None:
        (package / "node_modules.ts").write_text("export const modules = 1\n")

        assert dev_server.wait_for_builds(1)
