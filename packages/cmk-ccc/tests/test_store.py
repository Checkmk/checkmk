#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import errno
import importlib.machinery
import importlib.util
import os
import queue
import sys
import threading
import time
from collections.abc import Generator, Iterator, Sequence
from multiprocessing.pool import ThreadPool
from pathlib import Path
from types import ModuleType

import pytest
from pytest import MonkeyPatch

import cmk.ccc.debug
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.store import FileIo, ObjectStore, RealIo, TextSerializer


class FakeIo:
    """This is no-op/fake version of _file.RealIO
    TODO(sk): should be moved in testlib when we need it not only for store testing"""

    def __init__(self, path: Path):
        self.path = path
        self._data = b""

    def write(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data

    def locked(self) -> Iterator[None]:
        yield


@pytest.mark.parametrize("io,exists", [(RealIo, True), (FakeIo, False)])
def test_object_store(io: type[FileIo], exists: bool, tmp_path: Path) -> None:
    test_file = tmp_path / "hurz"
    a = ObjectStore(test_file, serializer=TextSerializer(), io=io)
    a.write_obj("aaaaa")
    assert a.read_obj(default="") == "aaaaa"
    assert test_file.exists() == exists
    test_file.unlink(missing_ok=True)


def test_object_store_fake_io() -> None:
    a = ObjectStore(Path("  "), serializer=TextSerializer(), io=FakeIo)
    a.write_obj("aaaaa")
    assert a.read_obj(default="") == "aaaaa"


@pytest.mark.parametrize("io,exists", [(RealIo, True), (FakeIo, False)])
def test_object_store_locked(io: type[FileIo], exists: bool, tmp_path: Path) -> None:
    test_file = tmp_path / "locked_hurz"
    a = ObjectStore(test_file, serializer=TextSerializer(), io=io)
    with a.locked():
        a.write_obj("aaaaa")
        with a.locked():
            a.write_obj("bbbbb")
    assert a.read_obj(default="") == "bbbbb"
    assert test_file.exists() == exists
    test_file.unlink(missing_ok=True)


@pytest.mark.parametrize("io", [RealIo, FakeIo])
def test_object_store_default(io: type[FileIo], tmp_path: Path) -> None:
    test_file = tmp_path / "locked_hurz"
    a = ObjectStore(test_file, serializer=TextSerializer(), io=io)
    assert a.read_obj(default="zz") == "zz"


def test_load_data_from_file_not_existing(tmp_path: Path) -> None:
    data = store.load_object_from_file(tmp_path / "x", default=None)
    assert data is None

    data = store.load_object_from_file(tmp_path / "x", default="DEFAULT")
    assert data == "DEFAULT"


def test_load_data_from_file_empty(tmp_path: Path) -> None:
    locked_file = tmp_path / "test"
    locked_file.write_text("", encoding="utf-8")
    data = store.load_object_from_file(tmp_path / "x", default="DEF")
    assert data == "DEF"


def test_load_data_not_locked(tmp_path: Path) -> None:
    locked_file = tmp_path / "locked_file"
    locked_file.write_text("[1, 2]", encoding="utf-8")

    store.load_object_from_file(locked_file, default=None)
    assert store.have_lock(locked_file) is False


def test_load_data_from_file_locking(tmp_path: Path) -> None:
    locked_file = tmp_path / "locked_file"
    locked_file.write_text("[1, 2]", encoding="utf-8")

    data = store.load_object_from_file(locked_file, default=None, lock=True)
    assert data == [1, 2]
    assert store.have_lock(locked_file) is True


def test_load_data_from_not_permitted_file(tmp_path: Path) -> None:
    # Note: The code is actually a lot more expressive in debug mode.
    cmk.ccc.debug.disable()

    locked_file = tmp_path / "test"
    locked_file.write_text("[1, 2]", encoding="utf-8")
    os.chmod(str(locked_file), 0o200)

    with pytest.raises(MKGeneralException) as e:
        store.load_object_from_file(locked_file, default=None)
    assert str(locked_file) in f"{e!s}"
    assert "Permission denied" in f"{e!s}"


def test_load_data_from_file_dict(tmp_path: Path) -> None:
    # Note: The code is actually a lot more expressive in debug mode.
    cmk.ccc.debug.disable()

    locked_file = tmp_path / "test"
    locked_file.write_bytes(repr({"1": 2, "ä": "ß"}).encode())

    data = store.load_object_from_file(locked_file, default=None)
    assert isinstance(data, dict)
    assert data["1"] == 2
    assert isinstance(data["ä"], str)
    assert data["ä"] == "ß"


def test_load_mk_file(tmp_path: Path) -> None:
    locked_file = tmp_path / "test"
    locked_file.write_bytes(b"# encoding: utf-8\nabc = '\xc3\xa4bc'\n")

    config = store.load_mk_file(locked_file, default={}, lock=False)

    assert config["abc"] == "äbc"


def test_save_data_to_file_pretty(tmp_path: Path) -> None:
    path = tmp_path / "test"

    data = {
        "asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "1asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "2asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "3asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "4asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "5asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
    }
    store.save_object_to_file(path, data, pprint_value=True)
    assert Path(path).read_text().count("\n") > 4
    assert store.load_object_from_file(path, default=None) == data


def test_save_data_to_file_not_pretty(tmp_path: Path) -> None:
    path = tmp_path / "test"

    data = {
        "asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "1asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "2asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "3asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "4asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "5asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
    }
    store.save_object_to_file(path, data)
    assert Path(path).read_text().count("\n") == 1
    assert store.load_object_from_file(path, default=None) == data


@pytest.mark.parametrize(
    "data",
    [
        None,
        [2, 3],
        ["föö"],
        [b"foob\xc3\xa4r"],
    ],
)
def test_save_data_to_file(tmp_path: Path, data: None | Sequence[str | int]) -> None:
    path = tmp_path / "lala"
    store.save_object_to_file(path, data)
    assert store.load_object_from_file(path, default=None) == data


@pytest.mark.parametrize(
    "data",
    [
        "föö",
    ],
)
def test_save_text_to_file(tmp_path: Path, data: str) -> None:
    path = tmp_path / "lala"
    store.save_text_to_file(path, data)
    assert store.load_text_from_file(path) == data


@pytest.mark.parametrize("permissions", [0o002, 0o666, 0o777])
def test_load_world_writable_file(tmp_path: Path, permissions: int) -> None:
    path = tmp_path / "writeme.txt"
    store.save_text_to_file(path, "")
    os.chmod(path, permissions)
    with pytest.raises(MKGeneralException, match="Refusing to read world writable file"):
        store.load_bytes_from_file(path, default=b"")
    with pytest.raises(MKGeneralException, match="Refusing to read world writable file"):
        store.load_object_from_file(path, default=object())
    with pytest.raises(MKGeneralException, match="Refusing to read world writable file"):
        store.load_text_from_file(path, default="")


@pytest.mark.parametrize(
    "data",
    [
        b"foob\xc3\xa4r",
    ],
)
def test_save_bytes_to_file(tmp_path: Path, data: bytes) -> None:
    path = tmp_path / "lala"
    store.save_bytes_to_file(path, data)
    assert store.load_bytes_from_file(path, default=b"") == data


def test_save_mk_file(tmp_path: Path) -> None:
    path = tmp_path / "lala"
    store.save_mk_file(path, "x = 1")

    actual = store.load_mk_file(path, default={}, lock=False)

    assert actual == {"x": 1}


def test_save_to_mk_file(tmp_path: Path) -> None:
    path = tmp_path / "huhu"
    store.save_to_mk_file(path, key="x", value={"a": 1})

    actual = store.load_mk_file(path, default={"x": {"a": 2, "y": 1}}, lock=False)

    assert actual == {"x": {"a": 1, "y": 1}}


def test_acquire_lock_not_existing(tmp_path: Path) -> None:
    assert store.acquire_lock(tmp_path / "asd") is True


@pytest.mark.parametrize("path_type", [str, Path])
def test_locked(test_file: Path, path_type: type[str] | type[Path]) -> None:
    path = path_type(test_file)

    assert store.have_lock(path) is False

    with store.locked(path):
        assert store.have_lock(path) is True
        with store.locked(path):
            assert store.have_lock(path) is True
        assert store.have_lock(path) is True

    assert store.have_lock(path) is False


@pytest.fixture(name="test_file")
def fixture_test_file(tmp_path: Path) -> Path:
    test_file = tmp_path / "test_file"
    test_file.write_text("", encoding="utf-8")
    return test_file


@pytest.mark.parametrize("path_type", [str, Path])
def test_try_locked(test_file: Path, path_type: type[str] | type[Path]) -> None:
    path = path_type(test_file)

    assert store.have_lock(path) is False

    with store.try_locked(path) as result:
        assert result is True
        assert store.have_lock(path) is True
        with store.try_locked(path) as result_1:
            assert result_1 is False
            assert store.have_lock(path) is True

    assert store.have_lock(path) is False


@pytest.mark.parametrize("path_type", [str, Path])
def test_try_locked_fails(
    test_file: Path, path_type: type[str] | type[Path], monkeypatch: MonkeyPatch
) -> None:
    path = path_type(test_file)

    def _is_already_locked(path: Path, blocking: object) -> bool:  # noqa: ARG001
        raise OSError(errno.EAGAIN, "%s is already locked" % path)

    monkeypatch.setattr(store._locks, "acquire_lock", _is_already_locked)  # noqa: SLF001

    assert store.have_lock(path) is False

    with store.try_locked(path) as result:
        assert result is False
        assert store.have_lock(path) is False

    assert store.have_lock(path) is False


@pytest.mark.parametrize("path_type", [str, Path])
def test_acquire_lock(test_file: Path, path_type: type[str] | type[Path]) -> None:
    path = path_type(test_file)

    assert store.have_lock(path) is False
    assert store.acquire_lock(path)
    assert store.have_lock(path) is True


@pytest.mark.parametrize("path_type", [str, Path])
def test_acquire_lock_twice(test_file: Path, path_type: type[str] | type[Path]) -> None:
    path = path_type(test_file)

    assert store.acquire_lock(path) is True
    assert store.have_lock(path) is True
    assert store.acquire_lock(path) is False
    assert store.have_lock(path) is True


@pytest.mark.parametrize("path_type", [str, Path])
def test_release_lock_not_locked_no_exception(path_type: type[str] | type[Path]) -> None:
    store.release_lock(path_type("/asdasd/aasdasd"))


@pytest.mark.parametrize("path_type", [str, Path])
def test_release_lock(test_file: Path, path_type: type[str] | type[Path]) -> None:
    path = path_type(test_file)

    store.acquire_lock(path)
    assert store.have_lock(path) is True
    store.release_lock(path)
    assert store.have_lock(path) is False


@pytest.mark.parametrize("path_type", [str, Path])
def test_release_lock_already_closed(test_file: Path, path_type: type[str] | type[Path]) -> None:
    """Should not raise exception"""
    path = path_type(test_file)

    store.acquire_lock(path)
    fd = store._locks._get_lock(str(path))  # noqa: SLF001
    assert isinstance(fd, int)
    os.close(fd)
    store.release_lock(path)
    assert store.have_lock(path) is False


_Files = Generator[Path, None, None]


@pytest.fixture(name="few_files")
def fixture_few_files(tmp_path: Path) -> _Files:
    files = (tmp_path / name for name in ("locked_file1", "locked_file2"))
    for f in files:
        f.write_text("", encoding="utf-8")
    return files


@pytest.mark.parametrize("path_type", [str, Path])
def test_release_all_locks(few_files: _Files, path_type: type[str] | type[Path]) -> None:
    files = (path_type(f) for f in few_files)

    assert all(store.acquire_lock(f) for f in files)
    store.release_all_locks()
    assert all(store.have_lock(f) is False for f in files)


@pytest.mark.parametrize("path_type", [str, Path])
def test_release_all_locks_already_closed(
    test_file: Path, path_type: type[str] | type[Path]
) -> None:
    """Should not raise exception"""
    path = path_type(test_file)
    store.acquire_lock(path)

    fd = store._locks._get_lock(str(path))  # noqa: SLF001
    assert isinstance(fd, int)
    os.close(fd)

    store.release_all_locks()
    assert store.have_lock(path) is False


class LockTestJob(enum.Enum):
    TERMINATE = enum.auto()
    LOCK = enum.auto()
    UNLOCK = enum.auto()


class LockTestThread(threading.Thread):
    def __init__(self, store_mod: ModuleType, path: Path) -> None:
        super().__init__()
        self.daemon = True

        self.store = store_mod
        self.path = path

        self._jobs: queue.Queue[LockTestJob] = queue.Queue()

    def run(self) -> None:
        while True:
            try:
                job = self._jobs.get(block=True, timeout=0.1)
            except queue.Empty:
                continue

            try:
                if job is LockTestJob.TERMINATE:
                    break

                if job is LockTestJob.LOCK:
                    assert self.store.have_lock(self.path) is False
                    self.store.acquire_lock(self.path)
                    assert self.store.have_lock(self.path) is True
                    continue

                if job is LockTestJob.UNLOCK:
                    assert self.store.have_lock(self.path) is True
                    self.store.release_lock(self.path)
                    assert self.store.have_lock(self.path) is False
                    continue
            finally:
                self._jobs.task_done()

    def terminate(self) -> None:
        """Send terminate command to thread from outside and wait for completion"""
        self._jobs.put(LockTestJob.TERMINATE)
        self.join()

    def lock(self) -> None:
        """Send lock command to thread from outside and wait for completion"""
        self.lock_nowait()
        self._jobs.join()

    def unlock(self) -> None:
        """Send unlock command to thread from outside and wait for completion"""
        self._jobs.put(LockTestJob.UNLOCK)
        self._jobs.join()

    def lock_nowait(self) -> None:
        """Send lock command to thread from outside without waiting for completion"""
        self._jobs.put(LockTestJob.LOCK)

    def join_jobs(self) -> None:
        self._jobs.join()


@pytest.fixture(name="t1")
def fixture_test_thread_1(test_file: Path) -> Iterator[LockTestThread]:
    # HACK: We abuse modules as data containers, so we have to do this Kung Fu...
    t_store = import_module_hack(store.__file__)

    t = LockTestThread(t_store, test_file)
    t.start()

    yield t

    t.store.release_all_locks()
    t.terminate()


def import_module_hack(pathname: str) -> ModuleType:
    """Return the module loaded from `pathname`.

    `pathname` is a path relative to the top-level directory
    of the repository.

    This function loads the module at `pathname` even if it does not have
    the ".py" extension.

    See: https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    """
    name = os.path.splitext(os.path.basename(pathname))[0]
    location = os.path.join(repo_path(), pathname)
    loader = importlib.machinery.SourceFileLoader(name, location)
    spec = importlib.machinery.ModuleSpec(name, loader, origin=location)
    spec.has_location = True
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def repo_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


@pytest.fixture(name="t2")
def fixture_test_thread_2(test_file: Path) -> Iterator[LockTestThread]:
    # HACK: We abuse modules as data containers, so we have to do this Kung Fu...
    t_store = store

    t = LockTestThread(t_store, test_file)
    t.start()

    yield t

    t.store.release_all_locks()
    t.terminate()


def _wait_for_waiting_lock() -> None:
    """Use /proc/locks to wait until one lock is in waiting state

    https://man7.org/linux/man-pages/man5/proc_locks.5.html
    """

    def has_waiting_lock() -> bool:
        pid = os.getpid()
        with Path("/proc/locks").open() as f:
            for line in f:
                p = line.strip().split()
                # NOTE: The "->" is *not* mentioned on the proc_locks(5) man page!
                # Nevertheless, it means the PID on the line is waiting for the lock.
                if p[1] == "->" and p[2] == "FLOCK" and p[4] == "WRITE" and p[5] == str(pid):
                    return True
        return False

    start = time.time()
    while time.time() - start < 1:
        if has_waiting_lock():
            return
        time.sleep(0.1)
    raise TimeoutError("Timeout waiting for 'has_waiting_lock' to finish (Timeout: 1 sec)")


@pytest.mark.parametrize("path_type", [str, Path])
def test_blocking_context_manager_from_multiple_threads(
    test_file: Path, path_type: type[str] | type[Path]
) -> None:
    path = path_type(test_file)

    acquired = []

    def acquire(_n: int) -> None:
        with store.locked(path):
            acquired.append(1)
            assert len(acquired) == 1
            acquired.pop()

    pool = ThreadPool(20)
    pool.map(acquire, iter(range(100)))
    pool.close()
    pool.join()


@pytest.mark.parametrize("path_type", [str, Path])
def test_blocking_lock_from_multiple_threads(
    test_file: Path, path_type: type[str] | type[Path]
) -> None:
    path = path_type(test_file)

    acquired = []
    saw_someone_wait: list[int] = []

    def acquire(_n: int) -> None:
        assert not store.have_lock(path)
        store.acquire_lock(path, blocking=True)
        assert store.have_lock(path)

        # We check to see if the other threads are actually waiting.
        if not saw_someone_wait:
            _wait_for_waiting_lock()
            saw_someone_wait.append(1)

        acquired.append(1)
        # This part is guarded by the lock, so we should never have more than one entry in here,
        # even if multiple threads try to append at the same time
        assert len(acquired) == 1

        acquired.pop()
        store.release_lock(path)
        assert not store.have_lock(path)

    # We try to append 100 ints to `acquired` in 20 threads simultaneously. As it is guarded by
    # the lock, we only ever can have one entry in the list at the same time.
    pool = ThreadPool(20)
    pool.map(acquire, iter(range(100)))
    pool.close()
    pool.join()

    # After all the threads have finished, the list should be empty again.
    assert len(acquired) == 0


@pytest.mark.parametrize("path_type", [str, Path])
def test_non_blocking_lock_from_multiple_threads(
    test_file: Path, path_type: type[str] | type[Path]
) -> None:
    path = path_type(test_file)

    acquired = []

    # Only one thread will ever be able to acquire this lock.
    def acquire(_n: int) -> None:
        try:
            store.acquire_lock(path, blocking=False)
            acquired.append(1)
            assert store.have_lock(path)
            store.release_lock(path)
            assert not store.have_lock(path)
        except OSError:
            assert not store.have_lock(path)

    pool = ThreadPool(2)
    pool.map(acquire, iter(range(20)))
    pool.close()
    pool.join()

    assert len(acquired) > 1, "No thread got any lock."


@pytest.mark.parametrize("path_type", [str, Path])
def test_blocking_lock_while_other_holds_the_lock(
    test_file: Path, path_type: type[str] | type[Path], t1: LockTestThread, t2: LockTestThread
) -> None:
    assert t1.store != t2.store

    path = path_type(test_file)

    assert t1.store.have_lock(path) is False
    assert t2.store.have_lock(path) is False

    try:
        # Take lock with t1
        t1.lock()

        # Now request the lock in t2, but don't wait for the successful locking. Only wait until we
        # start waiting for the lock.
        t2.lock_nowait()
        _wait_for_waiting_lock()
    finally:
        t1.unlock()

    t2.join_jobs()


@pytest.mark.parametrize("path_type", [str, Path])
def test_non_blocking_locking_without_previous_lock(
    test_file: Path, path_type: type[str] | type[Path], t1: LockTestThread
) -> None:
    assert t1.store != store
    path = path_type(test_file)

    # Try to lock first
    assert store.try_acquire_lock(path) is True
    assert store.have_lock(path) is True
    store.release_lock(path)
    assert store.have_lock(path) is False


@pytest.mark.parametrize("path_type", [str, Path])
def test_non_blocking_locking_while_already_locked(
    test_file: Path, path_type: type[str] | type[Path], t1: LockTestThread
) -> None:
    assert t1.store != store
    path = path_type(test_file)

    # Now take lock with t1.store
    t1.lock()

    # And now try to get the lock (which should not be possible)
    assert store.try_acquire_lock(path) is False
    assert store.have_lock(path) is False


@pytest.mark.parametrize("path_type", [str, Path])
def test_non_blocking_decorated_locking_without_previous_lock(
    test_file: Path, path_type: type[str] | type[Path], t1: LockTestThread
) -> None:
    assert t1.store != store
    path = path_type(test_file)

    with store.try_locked(path) as result:
        assert result is True
        assert store.have_lock(path) is True
    assert store.have_lock(path) is False


@pytest.mark.parametrize("path_type", [str, Path])
def test_non_blocking_decorated_locking_while_already_locked(
    test_file: Path, path_type: type[str] | type[Path], t1: LockTestThread
) -> None:
    assert t1.store != store
    path = path_type(test_file)

    # Take lock with t1.store
    t1.lock()

    # And now try to get the lock (which should not be possible)
    with store.try_locked(path) as result:
        assert result is False
        assert store.have_lock(path) is False
    assert store.have_lock(path) is False
