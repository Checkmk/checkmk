# encoding: utf-8

import sys
import threading
import time
import os

import pytest  # type: ignore
from testlib import import_module

import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException


def test_load_data_from_file_not_existing(tmpdir):
    data = store.load_data_from_file("%s/x" % tmpdir)
    assert data is None

    data = store.load_data_from_file("%s/x" % tmpdir, "DEFAULT")
    assert data == "DEFAULT"


def test_load_data_from_file_empty(tmpdir):
    locked_file = tmpdir.join("test")
    locked_file.write("")
    data = store.load_data_from_file("%s/x" % tmpdir, "DEF")
    assert data == "DEF"


def test_load_data_not_locked(tmpdir):
    locked_file = tmpdir.join("locked_file")
    locked_file.write("[1, 2]")

    store.load_data_from_file("%s" % locked_file)
    assert store.have_lock("%s" % locked_file) is False


def test_load_data_from_file_locking(tmpdir):
    locked_file = tmpdir.join("locked_file")
    locked_file.write("[1, 2]")

    data = store.load_data_from_file("%s" % locked_file, lock=True)
    assert data == [1, 2]
    assert store.have_lock("%s" % locked_file) is True


def test_load_data_from_not_permitted_file(tmpdir):
    locked_file = tmpdir.join("test")
    locked_file.write("[1, 2]")
    os.chmod("%s" % locked_file, 0200)

    with pytest.raises(MKGeneralException) as e:
        store.load_data_from_file("%s" % locked_file)
    assert "%s" % locked_file in "%s" % e
    assert "Permission denied" in "%s" % e


def test_load_data_from_file_dict(tmpdir):
    locked_file = tmpdir.join("test")
    locked_file.write(repr({"1": 2, "ä": u"ß"}))

    data = store.load_data_from_file("%s" % locked_file)
    assert isinstance(data, dict)
    assert data["1"] == 2
    assert isinstance(data["ä"], unicode)
    assert data["ä"] == u"ß"


def test_save_data_to_file(tmpdir):
    f = tmpdir.join("test")
    path = "%s" % f

    store.save_data_to_file(path, [2, 3])
    assert store.load_data_from_file(path) == [2, 3]


def test_save_data_to_file_pretty(tmpdir):
    f = tmpdir.join("test")
    path = "%s" % f

    data = {
        "asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "1asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "2asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "3asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "4asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "5asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
    }
    store.save_data_to_file(path, data)
    assert file(path).read().count("\n") > 4
    assert store.load_data_from_file(path) == data


def test_save_data_to_file_not_pretty(tmpdir):
    f = tmpdir.join("test")
    path = "%s" % f

    data = {
        "asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "1asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "2asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "3asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "4asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "5asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
    }
    store.save_data_to_file(path, data, pretty=False)
    assert file(path).read().count("\n") == 1
    assert store.load_data_from_file(path) == data


def test_acquire_lock_not_existing(tmpdir):
    store.aquire_lock("%s/asd" % tmpdir)


def test_acquire_lock(tmpdir):
    locked_file = tmpdir.join("locked_file")
    locked_file.write("")

    path = "%s" % locked_file

    assert store.have_lock(path) is False
    store.aquire_lock(path)
    assert store.have_lock(path) is True


def test_acquire_lock_twice(tmpdir):
    locked_file = tmpdir.join("locked_file")
    locked_file.write("")

    path = "%s" % locked_file

    assert store.have_lock(path) is False
    store.aquire_lock(path)
    assert store.have_lock(path) is True
    store.aquire_lock(path)
    assert store.have_lock(path) is True


def test_release_lock_not_locked():
    store.release_lock("/asdasd/aasdasd")


def test_release_lock(tmpdir):
    locked_file = tmpdir.join("locked_file")
    locked_file.write("")

    path = "%s" % locked_file

    assert store.have_lock(path) is False
    store.aquire_lock(path)
    assert store.have_lock(path) is True
    store.release_lock(path)
    assert store.have_lock(path) is False


def test_release_lock_already_closed(tmpdir):
    locked_file = tmpdir.join("locked_file")
    locked_file.write("")

    path = "%s" % locked_file

    assert store.have_lock(path) is False
    store.aquire_lock(path)
    assert store.have_lock(path) is True

    os.close(store._acquired_locks[path])

    store.release_lock(path)
    assert store.have_lock(path) is False


def test_release_all_locks(tmpdir):
    locked_file1 = tmpdir.join("locked_file1")
    locked_file1.write("")
    locked_file2 = tmpdir.join("locked_file2")
    locked_file2.write("")

    path1 = "%s" % locked_file1
    path2 = "%s" % locked_file2

    assert store.have_lock(path1) is False
    store.aquire_lock(path1)
    assert store.have_lock(path1) is True

    assert store.have_lock(path2) is False
    store.aquire_lock(path2)
    assert store.have_lock(path2) is True

    store.release_all_locks()
    assert store.have_lock(path1) is False
    assert store.have_lock(path2) is False


def test_release_all_locks_already_closed(tmpdir):
    locked_file = tmpdir.join("locked_file")
    locked_file.write("")

    path = "%s" % locked_file

    assert store.have_lock(path) is False
    store.aquire_lock(path)
    assert store.have_lock(path) is True

    os.close(store._acquired_locks[path])

    store.release_all_locks()
    assert store.have_lock(path) is False


class LockTestThread(threading.Thread):
    def __init__(self, store, path):
        self.store = store
        self.path = path
        self.do = None
        self.is_locked = False
        self._need_stop = threading.Event()
        super(LockTestThread, self).__init__()
        self.daemon = True

    def run(self):
        while not self._need_stop.is_set():
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

    def terminate(self):
        self._need_stop.set()


def test_locking(tmp_path, monkeypatch):
    # HACK: We abuse modules as data containers, so we have to do this Kung Fu...
    store1 = store
    store2 = import_module("cmk/utils/store.py")

    assert store1 != store2

    locked_file_path = tmp_path.joinpath("locked_file")
    with locked_file_path.open(mode="w", encoding="utf-8") as locked_file:
        locked_file.write(u"")
        path = "%s" % locked_file_path

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

        # Not 100% safe, but protects agains left over ressources in the good case at least
        store1.release_all_locks()
        store2.release_all_locks()
        t1.terminate()
        t1.join()
        t2.terminate()
        t2.join()
