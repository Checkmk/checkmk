import pytest
from pathlib2 import Path
import os

import cmk.utils.store as store
import cmk.utils.daemon as daemon
from cmk.utils.exceptions import MKGeneralException


@pytest.fixture(autouse=True)
def cleanup_locks():
    yield
    store.release_all_locks()


def test_lock_with_pid_file(tmpdir):
    pid_file = Path(tmpdir) / "test.pid"

    daemon.lock_with_pid_file(pid_file)

    assert store.have_lock("%s" % pid_file)

    with pid_file.open() as f:
        assert int(f.read()) == os.getpid()


def test_cleanup_locked_pid_file(tmpdir):
    pid_file = Path(tmpdir) / "test.pid"

    assert not store.have_lock("%s" % pid_file)
    daemon.lock_with_pid_file(pid_file)
    assert store.have_lock("%s" % pid_file)

    daemon._cleanup_locked_pid_file(pid_file)

    assert not store.have_lock("%s" % pid_file)


def test_pid_file_lock_context_manager(tmpdir):
    pid_file = Path(tmpdir) / "test.pid"

    assert not store.have_lock("%s" % pid_file)

    with daemon.pid_file_lock(pid_file):
        assert store.have_lock("%s" % pid_file)


def test_pid_file_lock_context_manager_exception(tmpdir):
    pid_file = Path(tmpdir) / "test.pid"

    assert not store.have_lock("%s" % pid_file)
    try:
        with daemon.pid_file_lock(pid_file):
            assert store.have_lock("%s" % pid_file)
            raise MKGeneralException("bla")
    except MKGeneralException:
        pass

    assert not store.have_lock("%s" % pid_file)
