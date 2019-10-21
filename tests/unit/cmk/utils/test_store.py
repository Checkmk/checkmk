# encoding: utf-8

import sys
import threading
import time
import os
import stat
import six

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path

import pytest  # type: ignore

import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException


def test_mkdir(tmp_path):
    test_dir = tmp_path.joinpath("abc")
    store.mkdir(test_dir)
    store.mkdir(test_dir)


def test_mkdir_mode(tmp_path):
    test_dir = tmp_path.joinpath("bla")
    store.mkdir(test_dir, mode=0o750)
    assert stat.S_IMODE(os.stat(str(test_dir)).st_mode) == 0o750


def test_mkdir_parent_not_exists(tmp_path):
    test_dir = tmp_path.joinpath("not-existing/xyz")
    with pytest.raises(OSError, match="No such file or directory"):
        store.mkdir(test_dir)


def test_makedirs(tmp_path):
    test_dir = tmp_path.joinpath("not-existing/xyz")
    store.makedirs(test_dir)
    store.makedirs(test_dir)


def test_makedirs_mode(tmp_path):
    test_dir = tmp_path.joinpath("whee/blub")
    store.makedirs(test_dir, mode=0o750)
    assert stat.S_IMODE(os.stat(str(test_dir)).st_mode) == 0o750


def test_load_data_from_file_not_existing(tmp_path):
    data = store.load_data_from_file(str(tmp_path / "x"))
    assert data is None

    data = store.load_data_from_file(str(tmp_path / "x"), "DEFAULT")
    assert data == "DEFAULT"


def test_load_data_from_file_empty(tmp_path):
    locked_file = tmp_path / "test"
    locked_file.write_text(u"", encoding="utf-8")
    data = store.load_data_from_file(str(tmp_path / "x"), "DEF")
    assert data == "DEF"


def test_load_data_not_locked(tmp_path):
    locked_file = tmp_path / "locked_file"
    locked_file.write_text(u"[1, 2]", encoding="utf-8")

    store.load_data_from_file(str(locked_file))
    assert store.have_lock(str(locked_file)) is False


def test_load_data_from_file_locking(tmp_path):
    locked_file = tmp_path / "locked_file"
    locked_file.write_text(u"[1, 2]", encoding="utf-8")

    data = store.load_data_from_file(str(locked_file), lock=True)
    assert data == [1, 2]
    assert store.have_lock(str(locked_file)) is True


def test_load_data_from_not_permitted_file(tmp_path):
    locked_file = tmp_path / "test"
    locked_file.write_text(u"[1, 2]", encoding="utf-8")
    os.chmod(str(locked_file), 0o200)

    with pytest.raises(MKGeneralException) as e:
        store.load_data_from_file(str(locked_file))
    assert str(locked_file) in "%s" % e
    assert "Permission denied" in "%s" % e


def test_load_data_from_file_dict(tmp_path):
    locked_file = tmp_path / "test"
    locked_file.write_bytes(repr({"1": 2, "ä": u"ß"}))

    data = store.load_data_from_file(str(locked_file))
    assert isinstance(data, dict)
    assert data["1"] == 2
    assert isinstance(data["ä"], six.text_type)
    assert data["ä"] == u"ß"


def test_save_data_to_file(tmp_path):
    path = str(tmp_path / "test")

    store.save_data_to_file(path, [2, 3])
    assert store.load_data_from_file(path) == [2, 3]


def test_save_data_to_file_pretty(tmp_path):
    path = str(tmp_path / "test")

    data = {
        "asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "1asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "2asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "3asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "4asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "5asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
    }
    store.save_data_to_file(path, data)
    assert open(path).read().count("\n") > 4
    assert store.load_data_from_file(path) == data


def test_save_data_to_file_not_pretty(tmp_path):
    path = str(tmp_path / "test")

    data = {
        "asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "1asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "2asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "3asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "4asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "5asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
    }
    store.save_data_to_file(path, data, pretty=False)
    assert open(path).read().count("\n") == 1
    assert store.load_data_from_file(path) == data


@pytest.mark.parametrize("path_type", [str, Path])
def test_aquire_lock_not_existing(tmp_path, path_type):
    store.aquire_lock(path_type(tmp_path / "asd"))


@pytest.mark.parametrize("path_type", [str, Path])
def test_aquire_lock(tmp_path, path_type):
    locked_file = tmp_path / "locked_file"
    locked_file.write_text(u"", encoding="utf-8")

    path = path_type(locked_file)

    assert store.have_lock(path) is False
    store.aquire_lock(path)
    assert store.have_lock(path) is True


@pytest.mark.parametrize("path_type", [str, Path])
def test_aquire_lock_twice(tmp_path, path_type):
    locked_file = tmp_path / "locked_file"
    locked_file.write_text(u"", encoding="utf-8")

    path = path_type(locked_file)

    assert store.have_lock(path) is False
    store.aquire_lock(path)
    assert store.have_lock(path) is True
    store.aquire_lock(path)
    assert store.have_lock(path) is True


@pytest.mark.parametrize("path_type", [str, Path])
def test_release_lock_not_locked(path_type):
    store.release_lock(path_type("/asdasd/aasdasd"))


@pytest.mark.parametrize("path_type", [str, Path])
def test_release_lock(tmp_path, path_type):
    locked_file = tmp_path / "locked_file"
    locked_file.write_text(u"", encoding="utf-8")

    path = path_type(locked_file)

    assert store.have_lock(path) is False
    store.aquire_lock(path)
    assert store.have_lock(path) is True
    store.release_lock(path)
    assert store.have_lock(path) is False


@pytest.mark.parametrize("path_type", [str, Path])
def test_release_lock_already_closed(tmp_path, path_type):
    locked_file = tmp_path / "locked_file"
    locked_file.write_text(u"", encoding="utf-8")

    path = path_type(locked_file)

    assert store.have_lock(path) is False
    store.aquire_lock(path)
    assert store.have_lock(path) is True

    os.close(store._acquired_locks[str(path)])

    store.release_lock(path)
    assert store.have_lock(path) is False


@pytest.mark.parametrize("path_type", [str, Path])
def test_release_all_locks(tmp_path, path_type):
    locked_file1 = tmp_path / "locked_file1"
    locked_file1.write_text(u"", encoding="utf-8")
    locked_file2 = tmp_path / "locked_file2"
    locked_file2.write_text(u"", encoding="utf-8")

    path1 = path_type(locked_file1)
    path2 = path_type(locked_file2)

    assert store.have_lock(path1) is False
    store.aquire_lock(path1)
    assert store.have_lock(path1) is True

    assert store.have_lock(path2) is False
    store.aquire_lock(path2)
    assert store.have_lock(path2) is True

    store.release_all_locks()
    assert store.have_lock(path1) is False
    assert store.have_lock(path2) is False


@pytest.mark.parametrize("path_type", [str, Path])
def test_release_all_locks_already_closed(tmp_path, path_type):
    locked_file = tmp_path / "locked_file"
    locked_file.write_text(u"", encoding="utf-8")

    path = path_type(locked_file)

    assert store.have_lock(path) is False
    store.aquire_lock(path)
    assert store.have_lock(path) is True

    os.close(store._acquired_locks[str(path)])

    store.release_all_locks()
    assert store.have_lock(path) is False


class LockTestThread(threading.Thread):
    def __init__(self, store_mod, path):
        self.store = store_mod
        self.path = path
        self.do = None
        self.is_locked = False
        super(LockTestThread, self).__init__()
        self.daemon = True

    def run(self):
        while True:
            if self.do == "lock":
                assert self.store.have_lock(self.path) is False
                self.store.aquire_lock(self.path)
                assert self.store.have_lock(self.path) is True
                self.do = None

            elif self.do == "unlock":
                assert self.store.have_lock(self.path) is True
                self.store.release_lock(self.path)
                assert self.store.have_lock(self.path) is False
                self.do = None

            else:
                time.sleep(0.1)


@pytest.mark.parametrize("path_type", [str, Path])
def test_locking(tmp_path, path_type):
    # HACK: We abuse modules as data containers, so we have to do this Kung Fu...
    store1 = sys.modules["cmk.utils.store"]
    del sys.modules["cmk.utils.store"]
    import cmk.utils.store as _store  # pylint: disable=reimported
    store2 = sys.modules["cmk.utils.store"]

    assert store1 != store2

    locked_file = tmp_path / "locked_file"
    locked_file.write_text(u"", encoding="utf-8")
    path = path_type(locked_file)

    t1 = LockTestThread(store1, path)
    t1.start()
    t2 = LockTestThread(store2, path)
    t2.start()

    # Take lock with store1
    t1.do = "lock"
    while range(20):
        if store1.have_lock(path):
            break
        time.sleep(0.01)
    assert store1.have_lock(path) is True

    # Now try to get lock with store2
    t2.do = "lock"
    time.sleep(0.2)
    assert store1.have_lock(path) is True
    assert store2.have_lock(path) is False

    # And now unlock store1 and check whether store2 has the lock now
    t1.do = "unlock"
    while range(20):
        if not store1.have_lock(path):
            break
        time.sleep(0.01)
    assert store1.have_lock(path) is False
    time.sleep(0.2)
    assert store2.have_lock(path) is True
