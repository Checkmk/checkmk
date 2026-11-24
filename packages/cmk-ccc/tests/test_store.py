#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import fcntl
import functools
import os
import queue
import signal
import sys
import threading
import time
import traceback
from collections.abc import Callable, Iterator, Sequence
from concurrent import futures
from functools import partial
from multiprocessing.pool import ThreadPool
from pathlib import Path
from types import FrameType
from typing import override

import pytest

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.store import FileIo, ObjectStore, RealIo, TextSerializer


class FakeIo(FileIo):
    """This is no-op/fake version of _file.RealIO
    TODO(sk): should be moved in testlib when we need it not only for store testing"""

    def __init__(self, path: Path):
        self.path = path
        self._data = b""

    @override
    def write(self, data: bytes) -> None:
        self._data = data

    @override
    def read(self, *, debug: bool) -> bytes:
        return self._data

    @override
    def locked(self) -> Iterator[None]:
        yield


def _poll_until(done: Callable[[], bool], *, seconds: int) -> bool:
    """Poll done() for about the given time, and return whether it returned True

    Counting the polls instead of watching the clock keeps a stopped process from running out of
    time.
    """
    # 10 polls back off from 0.1 ms to 51.2 ms, 102.3 ms in all, then each poll waits 100 ms.
    delay = 0.0001
    for _ in range(10 * seconds + 9):
        if done():
            return True
        time.sleep(delay)
        delay = min(2 * delay, 0.1)
    return done()


@pytest.mark.parametrize(
    "io, exists",
    [
        pytest.param(RealIo, True, id="real io"),
        pytest.param(FakeIo, False, id="fake io"),
    ],
)
def test_object_store(io: type[FileIo], exists: bool, tmp_path: Path) -> None:
    test_file = tmp_path / "hurz"
    a = ObjectStore(test_file, serializer=TextSerializer(), io=io)
    a.write_obj("aaaaa")
    assert a.read_obj(default="", debug=False) == "aaaaa"
    assert test_file.exists() == exists
    test_file.unlink(missing_ok=True)


def test_object_store_fake_io() -> None:
    a = ObjectStore(Path("  "), serializer=TextSerializer(), io=FakeIo)
    a.write_obj("aaaaa")
    assert a.read_obj(default="", debug=False) == "aaaaa"


def _stack_of(thread: threading.Thread) -> str:
    """Return where the thread is, for the message of a failure"""
    assert thread.ident is not None
    # Documented, but with a leading underscore, and there is no public alternative.
    frame = sys._current_frames().get(thread.ident)  # noqa: SLF001
    return "".join(traceback.format_stack(frame)) if frame else "  (just ended)\n"


def _in_own_thread[**P](test: Callable[P, None]) -> Callable[P, None]:
    """Run the test in a thread of its own, and fail it after about 10 s

    A lock waiting for another lock of the same thread would hang the test's thread otherwise.
    The thread releases its locks in the end.
    """

    @functools.wraps(test)
    def run_in_thread(*args: P.args, **kwargs: P.kwargs) -> None:
        failures: list[BaseException] = []

        def run() -> None:
            try:
                try:
                    test(*args, **kwargs)
                finally:
                    store.release_all_locks()
            except BaseException as e:
                failures.append(e)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        if not _poll_until(lambda: not thread.is_alive(), seconds=10):
            raise TimeoutError(f"Test not done after about 10 s, stuck in:\n{_stack_of(thread)}")
        if failures:
            raise failures[0]

    return run_in_thread


@pytest.mark.parametrize(
    "io, exists",
    [
        pytest.param(RealIo, True, id="real io"),
        pytest.param(FakeIo, False, id="fake io"),
    ],
)
def test_object_store_locked(io: type[FileIo], exists: bool, tmp_path: Path) -> None:
    test_file = tmp_path / "locked_hurz"
    a = ObjectStore(test_file, serializer=TextSerializer(), io=io)
    with a.locked():
        a.write_obj("aaaaa")
        with a.locked():
            a.write_obj("bbbbb")
    assert a.read_obj(default="", debug=False) == "bbbbb"
    assert test_file.exists() == exists
    test_file.unlink(missing_ok=True)


@pytest.mark.parametrize(
    "io",
    [
        pytest.param(RealIo, id="real io"),
        pytest.param(FakeIo, id="fake io"),
    ],
)
def test_object_store_default(io: type[FileIo], tmp_path: Path) -> None:
    test_file = tmp_path / "locked_hurz"
    a = ObjectStore(test_file, serializer=TextSerializer(), io=io)
    assert a.read_obj(default="zz", debug=False) == "zz"


def test_load_data_from_file_not_existing(tmp_path: Path) -> None:
    data = store.load_object_from_file(tmp_path / "x", default=None, debug=False)
    assert data is None

    data = store.load_object_from_file(tmp_path / "x", default="DEFAULT", debug=False)
    assert data == "DEFAULT"


def _write_file(path: Path, content: bytes) -> None:
    """Write a file others can't write, whatever the umask: the store wouldn't read it otherwise"""
    path.touch(mode=0o600)
    path.write_bytes(content)


def test_load_data_from_file_empty(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    empty_file = tmp_path / "test"
    _write_file(empty_file, b"")

    data = store.load_object_from_file(empty_file, default="DEF", debug=False)

    assert data == "DEF"
    assert "Failed to deserialize" not in caplog.text


def test_load_data_not_locked(tmp_path: Path) -> None:
    locked_file = tmp_path / "locked_file"
    _write_file(locked_file, b"[1, 2]")

    store.load_object_from_file(locked_file, default=None, debug=False)
    assert store.have_lock(locked_file) is False


@pytest.fixture(name="release_locks")
def fixture_release_locks() -> Iterator[None]:
    yield
    # Otherwise the test's thread keeps its locks until a later test releases them.
    store.release_all_locks()


@pytest.mark.usefixtures("release_locks")
def test_load_data_from_file_locking(tmp_path: Path) -> None:
    locked_file = tmp_path / "locked_file"
    _write_file(locked_file, b"[1, 2]")

    data = store.load_object_from_file(locked_file, default=None, lock=True, debug=False)
    assert data == [1, 2]
    assert store.have_lock(locked_file) is True


def test_load_data_from_file_dict(tmp_path: Path) -> None:
    locked_file = tmp_path / "test"
    _write_file(locked_file, repr({"1": 2, "ä": "ß"}).encode())

    data = store.load_object_from_file(locked_file, default=None, debug=False)
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
    assert store.load_object_from_file(path, default=None, debug=False) == data


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
    assert store.load_object_from_file(path, default=None, debug=False) == data


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(None, id="None"),
        pytest.param([2, 3], id="ints"),
        pytest.param(["föö"], id="non-ASCII str"),
        pytest.param([b"foob\xc3\xa4r"], id="bytes"),
    ],
)
def test_save_data_to_file(tmp_path: Path, data: None | Sequence[str | int]) -> None:
    path = tmp_path / "lala"
    store.save_object_to_file(path, data)
    assert store.load_object_from_file(path, default=None, debug=False) == data


@pytest.mark.parametrize(
    "data",
    [
        pytest.param("föö", id="non-ASCII"),
    ],
)
def test_save_text_to_file(tmp_path: Path, data: str) -> None:
    path = tmp_path / "lala"
    store.save_text_to_file(path, data)
    assert store.load_text_from_file(path) == data


def test_load_object_from_file_null_bytes(tmp_path: Path) -> None:
    """A file containing null bytes should return default, not crash with SyntaxError."""
    path = tmp_path / "corrupted.mk"
    _write_file(path, b"\x00" * 100)
    data = store.load_object_from_file(path, default=[], debug=False)
    assert data == []


@pytest.mark.parametrize(
    "permissions",
    [
        pytest.param(0o002, id="writable for others only"),
        pytest.param(0o666, id="readable and writable for all"),
        pytest.param(0o777, id="everything for all"),
    ],
)
@pytest.mark.parametrize(
    "load",
    [
        pytest.param(partial(store.load_bytes_from_file, default=b"", debug=False), id="bytes"),
        pytest.param(partial(store.load_object_from_file, default=None, debug=False), id="object"),
        pytest.param(partial(store.load_text_from_file, default=""), id="text"),
    ],
)
def test_load_world_writable_file(
    tmp_path: Path, permissions: int, load: Callable[[Path], object]
) -> None:
    path = tmp_path / "writeme.txt"
    store.save_text_to_file(path, "")
    os.chmod(path, permissions)

    with pytest.raises(MKGeneralException, match="Refusing to read world writable file"):
        load(path)


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"foob\xc3\xa4r", id="UTF-8"),
    ],
)
def test_save_bytes_to_file(tmp_path: Path, data: bytes) -> None:
    path = tmp_path / "lala"
    store.save_bytes_to_file(path, data)
    assert store.load_bytes_from_file(path, default=b"", debug=False) == data


def test_load_mk_file_with_syntax_error_names_the_file(tmp_path: Path) -> None:
    (path := tmp_path / "broken.mk").write_text("x = [", encoding="utf-8")

    with pytest.raises(MKGeneralException, match="broken.mk"):
        store.load_mk_file(path, default={}, lock=False)


def test_load_mk_file_does_not_wrap_errors_raised_by_its_code(tmp_path: Path) -> None:
    (path := tmp_path / "broken.mk").write_text("x = undefined_name", encoding="utf-8")

    with pytest.raises(NameError):
        store.load_mk_file(path, default={}, lock=False)


def test_save_mk_file(tmp_path: Path) -> None:
    path = tmp_path / "lala"
    store.save_mk_file(path, "x = 1")

    actual = store.load_mk_file(path, default={}, lock=False)

    assert actual == {"x": 1}


def test_save_to_mk_file_mapping(tmp_path: Path) -> None:
    path = tmp_path / "huhu"
    store.save_to_mk_file(path, key="x", value={"a": 1})

    actual = store.load_mk_file(path, default={"x": {"a": 2, "y": 1}}, lock=False)

    assert actual == {"x": {"a": 1, "y": 1}}


def test_save_to_mk_file_list(tmp_path: Path) -> None:
    path = tmp_path / "huhu"
    store.save_to_mk_file(path, key="x", value=["a", "b"])

    actual = store.load_mk_file(path, default={"x": ["c"]}, lock=False)

    assert actual == {"x": ["c", "a", "b"]}


def test_save_to_mk_file_dict_loads_without_preseeding(tmp_path: Path) -> None:
    path = tmp_path / "huhu"
    store.save_to_mk_file(path, key="x", value={"a": 1})

    actual = store.load_mk_file(path, default={}, lock=False)

    assert actual == {"x": {"a": 1}}


def test_save_to_mk_file_list_loads_without_preseeding(tmp_path: Path) -> None:
    path = tmp_path / "huhu"
    store.save_to_mk_file(path, key="x", value=[1, 2, 3])

    actual = store.load_mk_file(path, default={}, lock=False)

    assert actual == {"x": [1, 2, 3]}


def test_bootstrap_statement_defines_a_missing_variable() -> None:
    namespace: dict[str, object] = {}

    exec(store.bootstrap_statement("x", "{}"), namespace, namespace)  # nosec B102

    assert namespace["x"] == {}


def test_bootstrap_statement_keeps_a_predefined_object() -> None:
    predefined: list[int] = [1]
    namespace: dict[str, object] = {"x": predefined}

    exec(store.bootstrap_statement("x", "[]"), namespace, namespace)  # nosec B102

    assert namespace["x"] is predefined


@pytest.mark.usefixtures("release_locks")
def test_acquire_lock_not_existing(tmp_path: Path) -> None:
    assert store.acquire_lock(tmp_path / "asd") is True


# The tests with forked children come before the ones in threads of their own: after a failure,
# a thread hanging in flock() would make fork() warn about threads.


def _run_in_child(function: Callable[[], object]) -> None:
    """Run the function in a forked child, and fail if it raises there

    pytest shows the child's traceback with the output of the test. A child which takes longer
    than about 10 s gets killed.
    """
    if (pid := os.fork()) == 0:
        exit_code = 1
        try:
            function()
            exit_code = 0
        except BaseException:
            traceback.print_exc()
        finally:
            os._exit(exit_code)

    statuses: list[int] = []

    def exited() -> bool:
        waited_pid, status = os.waitpid(pid, os.WNOHANG)
        if waited_pid:
            statuses.append(status)
        return bool(waited_pid)

    if not _poll_until(exited, seconds=10):
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
        raise TimeoutError("Child not done after about 10 s")
    assert os.waitstatus_to_exitcode(statuses[0]) == 0, "The child failed, see its stderr"


def test_a_forked_child_releasing_a_lock_leaves_the_lock_of_the_parent(test_file: Path) -> None:
    store.acquire_lock(test_file)
    try:
        _run_in_child(store.release_all_locks)

        assert _locked_by_anyone(test_file)
    finally:
        store.release_lock(test_file)


def test_release_lock_already_closed(test_file: Path) -> None:
    """Should not raise exception"""
    # It comes before the tests starting threads: another thread could get the number of the
    # closed fd, and release_lock() would close its file then.
    store.acquire_lock(test_file)
    os.close(_fd_of(test_file))

    store.release_lock(test_file)

    assert store.have_lock(test_file) is False


@_in_own_thread
def test_locked(test_file: Path) -> None:
    assert store.have_lock(test_file) is False

    with store.locked(test_file):
        assert store.have_lock(test_file) is True
        with store.locked(test_file):
            assert store.have_lock(test_file) is True
        assert store.have_lock(test_file) is True

    assert store.have_lock(test_file) is False


@pytest.fixture(name="test_file")
def fixture_test_file(tmp_path: Path) -> Path:
    test_file = tmp_path / "test_file"
    test_file.write_text("", encoding="utf-8")
    return test_file


def test_try_locked(test_file: Path) -> None:
    assert store.have_lock(test_file) is False

    with store.try_locked(test_file) as result:
        assert result is True
        assert store.have_lock(test_file) is True
        with store.try_locked(test_file) as result_1:
            assert result_1 is False
            assert store.have_lock(test_file) is True

    assert store.have_lock(test_file) is False


@pytest.mark.usefixtures("release_locks")
def test_acquire_lock(test_file: Path) -> None:
    assert store.have_lock(test_file) is False
    assert store.acquire_lock(test_file)
    assert store.have_lock(test_file) is True


@_in_own_thread
def test_acquire_lock_twice(test_file: Path) -> None:
    assert store.acquire_lock(test_file) is True
    assert store.have_lock(test_file) is True
    assert store.acquire_lock(test_file) is False
    assert store.have_lock(test_file) is True


def test_release_lock_not_locked_no_exception() -> None:
    store.release_lock(Path("/asdasd/aasdasd"))


def test_release_lock(test_file: Path) -> None:
    store.acquire_lock(test_file)
    assert store.have_lock(test_file) is True

    store.release_lock(test_file)

    assert store.have_lock(test_file) is False
    assert not _locked_by_anyone(test_file)


def _fd_of(path: Path) -> int:
    """Return the only fd of the process for the path"""
    fds = []
    for name in os.listdir("/proc/self/fd"):
        try:
            if Path("/proc/self/fd", name).readlink() == path.resolve():
                fds.append(int(name))
        except OSError:
            pass  # The fd of the listing itself is gone by now.
    assert len(fds) == 1, f"Not exactly one fd for {path}: {fds}"
    return fds[0]


def test_release_all_locks(tmp_path: Path) -> None:
    files = [tmp_path / name for name in ("locked_file1", "locked_file2")]
    for f in files:
        f.write_text("", encoding="utf-8")

    assert all(store.acquire_lock(f) for f in files)
    store.release_all_locks()
    assert all(store.have_lock(f) is False for f in files)


class _Interrupt(BaseException):
    """Stands for an exception raised asynchronously in a thread, like a request timeout"""


def _interrupted(call: Callable[[], object], at_step: int) -> bool:
    """Run the call and raise _Interrupt at the given line or bytecode step of the lock functions

    Returns whether the call was interrupted, i.e. whether the call has that many steps.
    """
    locks_file = store.acquire_lock.__code__.co_filename
    steps = 0

    def count_steps(_frame: FrameType, event: str, _arg: object) -> object:
        nonlocal steps
        if event in ("line", "opcode"):
            steps += 1
            if steps == at_step:
                raise _Interrupt
        return count_steps

    def trace_lock_functions(frame: FrameType, _event: str, _arg: object) -> object:
        if frame.f_code.co_filename != locks_file:
            return None
        frame.f_trace_opcodes = True
        return count_steps

    previous_trace = sys.gettrace()
    sys.settrace(trace_lock_functions)  # type: ignore[arg-type]
    try:
        call()
    except _Interrupt:
        return True
    finally:
        sys.settrace(previous_trace)
    return False


def _locked_by_anyone(path: Path) -> bool:
    fd = os.open(path, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    finally:
        os.close(fd)
    return False


def test_an_interrupted_acquire_lock_leaves_no_lock_behind(test_file: Path) -> None:
    step = 1
    while _interrupted(lambda: store.acquire_lock(test_file), at_step=step):
        store.release_all_locks()
        assert not _locked_by_anyone(test_file), f"Lock left behind when interrupted at {step}"
        step += 1

    store.release_all_locks()
    assert not _locked_by_anyone(test_file)


def test_an_interrupted_acquire_lock_cleans_up_without_release_all_locks(
    test_file: Path,
) -> None:
    step = 1
    while _interrupted(lambda: store.acquire_lock(test_file), at_step=step):
        assert not store.have_lock(test_file), f"Lock registered when interrupted at {step}"
        assert not _locked_by_anyone(test_file), f"Lock left behind when interrupted at {step}"
        step += 1

    store.release_lock(test_file)


def test_an_interrupted_release_lock_leaves_no_lock_behind(test_file: Path) -> None:
    step = 1
    while True:
        store.acquire_lock(test_file)
        interrupted = _interrupted(lambda: store.release_lock(test_file), at_step=step)
        store.release_all_locks()
        assert not _locked_by_anyone(test_file), f"Lock left behind when interrupted at {step}"
        if not interrupted:
            break
        step += 1


@_in_own_thread
def test_an_interrupted_release_lock_leaves_a_consistent_lock_without_release_all_locks(
    test_file: Path,
) -> None:
    step = 1
    while True:
        store.acquire_lock(test_file)
        interrupted = _interrupted(lambda: store.release_lock(test_file), at_step=step)

        store.acquire_lock(test_file)
        assert store.have_lock(test_file), f"Lock not reported when interrupted at {step}"
        assert _locked_by_anyone(test_file), f"Lock not held when interrupted at {step}"
        store.release_lock(test_file)
        assert not store.have_lock(test_file), f"Lock reported when interrupted at {step}"
        assert not _locked_by_anyone(test_file), f"Lock left behind when interrupted at {step}"

        if not interrupted:
            break
        step += 1


class LockTestJob(enum.Enum):
    TERMINATE = enum.auto()
    LOCK = enum.auto()
    UNLOCK = enum.auto()
    TRY_LOCK = enum.auto()
    TRY_LOCKED = enum.auto()


class LockTestThread(threading.Thread):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.daemon = True

        self.path = path

        self._jobs: queue.Queue[tuple[LockTestJob, futures.Future[bool | None]]] = queue.Queue()
        self._pending: list[futures.Future[bool | None]] = []
        self._hung = False

    @override
    def run(self) -> None:
        while True:
            job, done = self._jobs.get()
            try:
                result = self._run(job)
            except BaseException as e:
                # The test's thread raises it: raised here, it would end this thread.
                done.set_exception(e)
            else:
                done.set_result(result)
            if job is LockTestJob.TERMINATE:
                return

    def _run(self, job: LockTestJob) -> bool | None:
        match job:
            case LockTestJob.LOCK:
                assert store.have_lock(self.path) is False
                store.acquire_lock(self.path)
                assert store.have_lock(self.path) is True
                return None
            case LockTestJob.UNLOCK:
                assert store.have_lock(self.path) is True
                store.release_lock(self.path)
                assert store.have_lock(self.path) is False
                return None
            case LockTestJob.TRY_LOCK:
                locked = store.try_acquire_lock(self.path)
                assert store.have_lock(self.path) is locked
                return locked
            case LockTestJob.TRY_LOCKED:
                with store.try_locked(self.path) as locked:
                    assert store.have_lock(self.path) is locked
                assert store.have_lock(self.path) is False
                return locked
            case LockTestJob.TERMINATE:
                # Locks belong to the thread which acquired them.
                store.release_all_locks()
                return None

    def _send(self, job: LockTestJob) -> futures.Future[bool | None]:
        done: futures.Future[bool | None] = futures.Future()
        self._pending.append(done)
        self._jobs.put((job, done))
        return done

    def terminate(self) -> None:
        """Send terminate command to thread from outside and wait for completion, unless it hung"""
        self._send(LockTestJob.TERMINATE)
        if self._hung:
            return  # As a daemon, it doesn't block the exit.
        self.join_jobs()
        self.join()

    def lock(self) -> None:
        """Send lock command to thread from outside and wait for completion"""
        self._send(LockTestJob.LOCK)
        self.join_jobs()

    def unlock(self) -> None:
        """Send unlock command to thread from outside and wait for completion"""
        self._send(LockTestJob.UNLOCK)
        self.join_jobs()

    def lock_until_waiting(self) -> None:
        """Send lock command to thread from outside, and wait until the thread waits for the lock

        If the job ends instead, raise its failure.
        """
        locked = self._send(LockTestJob.LOCK)
        try:
            _wait_for_waiting_lock(self.path, unless=locked.done)
        except TimeoutError:
            self._hung = True
            raise TimeoutError(
                f"Lock job not waiting after about 10 s, stuck in:\n{_stack_of(self)}"
            ) from None
        if locked.done():
            self.join_jobs()
            raise AssertionError("Got the lock, although another thread holds it")

    def try_lock(self) -> bool:
        """Let the thread try to lock without blocking, and return whether it got the lock"""
        done = self._send(LockTestJob.TRY_LOCK)
        self.join_jobs()
        assert isinstance(locked := done.result(), bool)
        return locked

    def try_locked(self) -> bool:
        """Like try_lock(), but via the context manager, which releases the lock again"""
        done = self._send(LockTestJob.TRY_LOCKED)
        self.join_jobs()
        assert isinstance(locked := done.result(), bool)
        return locked

    def join_jobs(self) -> None:
        """Wait for the jobs sent so far, and raise the first of their failures"""
        pending, self._pending = self._pending, []
        if not _poll_until(lambda: all(done.done() for done in pending), seconds=10):
            self._hung = True
            raise TimeoutError(f"Lock job not done after about 10 s, stuck in:\n{_stack_of(self)}")
        for done in pending:
            done.result()


@pytest.fixture(name="t1")
def fixture_test_thread_1(test_file: Path) -> Iterator[LockTestThread]:
    yield from _lock_test_thread(test_file)


@pytest.fixture(name="t2")
def fixture_test_thread_2(test_file: Path) -> Iterator[LockTestThread]:
    yield from _lock_test_thread(test_file)


def _lock_test_thread(path: Path) -> Iterator[LockTestThread]:
    t = LockTestThread(path)
    t.start()
    yield t
    t.terminate()


def _wait_for_waiting_lock(path: Path, unless: Callable[[], bool] = lambda: False) -> None:
    """Use /proc/locks to wait until one lock on the path is in waiting state, or unless() holds

    https://man7.org/linux/man-pages/man5/proc_locks.5.html
    """
    # Only the inode: stat() and /proc/locks may disagree on the device.
    inode = str(path.stat().st_ino)

    def has_waiting_lock() -> bool:
        pid = os.getpid()
        with Path("/proc/locks").open() as f:
            for line in f:
                p = line.strip().split()
                # NOTE: The "->" is *not* mentioned on the proc_locks(5) man page!
                # Nevertheless, it means the PID on the line is waiting for the lock.
                if (
                    p[1] == "->"
                    and p[2] == "FLOCK"
                    and p[4] == "WRITE"
                    and p[5] == str(pid)
                    and p[6].rpartition(":")[2] == inode
                ):
                    return True
        return False

    # A loaded machine can take a while to schedule the waiting thread.
    if not _poll_until(lambda: has_waiting_lock() or unless(), seconds=10):
        raise TimeoutError("No lock in waiting state after about 10 s")


def _map_in_threads(function: Callable[[int], None]) -> None:
    """Call the function 100 times in 20 threads, and raise the first of their failures"""
    failures: list[BaseException] = []
    busy: set[threading.Thread] = set()

    def call(n: int) -> None:
        busy.add(threading.current_thread())
        try:
            function(n)
        except BaseException as e:
            failures.append(e)  # A timeout would hide it otherwise.
            raise
        finally:
            busy.discard(threading.current_thread())

    pool = ThreadPool(20)
    result = pool.map_async(call, range(100))
    # Twice as long as _wait_for_waiting_lock(), so that its more specific failure wins.
    if not _poll_until(result.ready, seconds=20):
        stuck = next(iter(list(busy)), None)
        where = _stack_of(stuck) if stuck else "  (none busy)\n"
        # Threads stuck in flock() would block join(). As daemons, they don't block the exit.
        pool.terminate()
        raise TimeoutError(f"Threads not done after about 20 s, one stuck in:\n{where}") from (
            failures[0] if failures else None
        )
    pool.close()
    pool.join()
    result.get()


def test_blocking_context_manager_from_multiple_threads(test_file: Path) -> None:
    acquired = []
    looked_for_a_waiter: list[int] = []

    def acquire(_n: int) -> None:
        with store.locked(test_file):
            acquired.append(1)
            # Threads rarely overlap here, so the first one stays until another one waits.
            if not looked_for_a_waiter:
                looked_for_a_waiter.append(1)
                _wait_for_waiting_lock(test_file)
            assert len(acquired) == 1
            acquired.pop()

    _map_in_threads(acquire)


def test_blocking_lock_from_multiple_threads(test_file: Path) -> None:
    acquired = []
    looked_for_a_waiter: list[int] = []

    def acquire(_n: int) -> None:
        assert not store.have_lock(test_file)
        store.acquire_lock(test_file, blocking=True)
        try:
            assert store.have_lock(test_file)
            # The lock guards this part, so it never holds more than one entry.
            acquired.append(1)

            # Check once that other threads wait: with broken locks, every check would wait in
            # vain. A thread getting in meanwhile finds the entry.
            if not looked_for_a_waiter:
                looked_for_a_waiter.append(1)
                _wait_for_waiting_lock(test_file)

            assert len(acquired) == 1

            acquired.pop()
        finally:
            # Other threads would wait for the lock forever, and the test with them.
            store.release_lock(test_file)
        assert not store.have_lock(test_file)

    # We try to append 100 ints to `acquired` in 20 threads simultaneously. As it is guarded by
    # the lock, we only ever can have one entry in the list at the same time.
    _map_in_threads(acquire)

    # After all the threads have finished, the list should be empty again.
    assert len(acquired) == 0


def test_blocking_lock_while_other_holds_the_lock(t1: LockTestThread, t2: LockTestThread) -> None:
    # Before the try: a failure here would make t1.unlock() fail, too.
    t1.lock()
    try:
        t2.lock_until_waiting()
    finally:
        t1.unlock()

    t2.join_jobs()


@pytest.mark.usefixtures("release_locks")
def test_non_blocking_locking_without_previous_lock(test_file: Path) -> None:
    # Try to lock first
    assert store.try_acquire_lock(test_file) is True
    assert store.have_lock(test_file) is True
    store.release_lock(test_file)
    assert store.have_lock(test_file) is False


def test_non_blocking_locking_while_already_locked(t1: LockTestThread, t2: LockTestThread) -> None:
    t1.lock()

    assert t2.try_lock() is False


def test_non_blocking_decorated_locking_without_previous_lock(test_file: Path) -> None:
    with store.try_locked(test_file) as result:
        assert result is True
        assert store.have_lock(test_file) is True
    assert store.have_lock(test_file) is False


def test_non_blocking_decorated_locking_while_already_locked(
    t1: LockTestThread, t2: LockTestThread
) -> None:
    t1.lock()

    assert t2.try_locked() is False


def test_load_object_from_unreadable_file_reraises_in_debug_mode(tmp_path: Path) -> None:
    (unreadable := tmp_path / "directory").mkdir(mode=0o700)

    with pytest.raises(IsADirectoryError):
        store.load_object_from_file(unreadable, default=None, debug=True)


def test_load_object_from_unreadable_file_names_the_file_and_the_reason(tmp_path: Path) -> None:
    (unreadable := tmp_path / "directory").mkdir(mode=0o700)

    with pytest.raises(MKGeneralException) as e:
        store.load_object_from_file(unreadable, default=None, debug=False)

    assert str(e.value) == (
        f"Cannot read file \"{unreadable}\": [Errno 21] Is a directory: '{unreadable}'"
    )
