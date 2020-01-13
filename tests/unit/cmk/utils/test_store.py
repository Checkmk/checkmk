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
from testlib import import_module

import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException


@pytest.mark.parametrize("path_type", [str, Path])
def test_mkdir(tmp_path, path_type):
    test_dir = tmp_path / "abc"
    store.mkdir(path_type(test_dir))
    store.mkdir(path_type(test_dir))


@pytest.mark.parametrize("path_type", [str, Path])
def test_mkdir_mode(tmp_path, path_type):
    test_dir = tmp_path / "bla"
    store.mkdir(path_type(test_dir), mode=0o750)
    assert stat.S_IMODE(os.stat(str(test_dir)).st_mode) == 0o750


@pytest.mark.parametrize("path_type", [str, Path])
def test_mkdir_parent_not_exists(tmp_path, path_type):
    test_dir = tmp_path / "not-existing/xyz"
    with pytest.raises(OSError, match="No such file or directory"):
        store.mkdir(path_type(test_dir))


@pytest.mark.parametrize("path_type", [str, Path])
def test_makedirs(tmp_path, path_type):
    test_dir = tmp_path / "not-existing/xyz"
    store.makedirs(path_type(test_dir))
    store.makedirs(path_type(test_dir))


@pytest.mark.parametrize("path_type", [str, Path])
def test_makedirs_mode(tmp_path, path_type):
    test_dir = tmp_path / "whee/blub"
    store.makedirs(path_type(test_dir), mode=0o750)
    assert stat.S_IMODE(os.stat(str(test_dir)).st_mode) == 0o750


@pytest.mark.parametrize("path_type", [str, Path])
def test_load_data_from_file_not_existing(tmp_path, path_type):
    data = store.load_object_from_file(path_type(tmp_path / "x"))
    assert data is None

    data = store.load_object_from_file(path_type(tmp_path / "x"), default="DEFAULT")
    assert data == "DEFAULT"


@pytest.mark.parametrize("path_type", [str, Path])
def test_load_data_from_file_empty(tmp_path, path_type):
    locked_file = tmp_path / "test"
    locked_file.write_text(u"", encoding="utf-8")
    data = store.load_object_from_file(path_type(tmp_path / "x"), default="DEF")
    assert data == "DEF"


@pytest.mark.parametrize("path_type", [str, Path])
def test_load_data_not_locked(tmp_path, path_type):
    locked_file = tmp_path / "locked_file"
    locked_file.write_text(u"[1, 2]", encoding="utf-8")

    store.load_object_from_file(path_type(locked_file))
    assert store.have_lock(path_type(locked_file)) is False


@pytest.mark.parametrize("path_type", [str, Path])
def test_load_data_from_file_locking(tmp_path, path_type):
    locked_file = tmp_path / "locked_file"
    locked_file.write_text(u"[1, 2]", encoding="utf-8")

    data = store.load_object_from_file(path_type(locked_file), lock=True)
    assert data == [1, 2]
    assert store.have_lock(path_type(locked_file)) is True


@pytest.mark.parametrize("path_type", [str, Path])
def test_load_data_from_not_permitted_file(tmp_path, path_type):
    locked_file = tmp_path / "test"
    locked_file.write_text(u"[1, 2]", encoding="utf-8")
    os.chmod(str(locked_file), 0o200)

    with pytest.raises(MKGeneralException) as e:
        store.load_object_from_file(path_type(locked_file))
    assert str(locked_file) in "%s" % e
    assert "Permission denied" in "%s" % e


@pytest.mark.parametrize("path_type", [str, Path])
def test_load_data_from_file_dict(tmp_path, path_type):
    locked_file = tmp_path / "test"
    locked_file.write_bytes(repr({"1": 2, "ä": u"ß"}))

    data = store.load_object_from_file(path_type(locked_file))
    assert isinstance(data, dict)
    assert data["1"] == 2
    assert isinstance(data["ä"], six.text_type)
    assert data["ä"] == u"ß"


@pytest.mark.parametrize("path_type", [str, Path])
def test_load_mk_file(tmp_path, path_type):
    locked_file = tmp_path / "test"
    locked_file.write_bytes("# encoding: utf-8\nabc = 'äbc'\n")

    config = store.load_mk_file(path_type(locked_file), default={})
    assert config["abc"] == "äbc"


@pytest.mark.parametrize("path_type", [str, Path])
def test_save_data_to_file_pretty(tmp_path, path_type):
    path = path_type(tmp_path / "test")

    data = {
        "asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "1asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "2asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "3asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "4asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "5asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
    }
    store.save_object_to_file(path, data, pretty=True)
    assert open(str(path)).read().count("\n") > 4
    assert store.load_object_from_file(path) == data


@pytest.mark.parametrize("path_type", [str, Path])
def test_save_data_to_file_not_pretty(tmp_path, path_type):
    path = path_type(tmp_path / "test")

    data = {
        "asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "1asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "2asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "3asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "4asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
        "5asdasaaaaaaaaaaaaaaaaaaaad": "asbbbbbbbbbbbbbbbbbbd",
    }
    store.save_object_to_file(path, data)
    assert open(str(path)).read().count("\n") == 1
    assert store.load_object_from_file(path) == data


@pytest.mark.parametrize("path_type", [str, Path])
@pytest.mark.parametrize("data", [
    None,
    [2, 3],
    [u"föö"],
    [b'foob\xc3\xa4r'],
])
def test_save_data_to_file(tmp_path, path_type, data):
    path = path_type(tmp_path / "lala")
    store.save_object_to_file(path, data)
    assert store.load_object_from_file(path) == data


@pytest.mark.parametrize("path_type", [str, Path])
@pytest.mark.parametrize("data", [
    u"föö",
])
def test_save_text_to_file(tmp_path, path_type, data):
    path = path_type(tmp_path / "lala")
    store.save_text_to_file(path, data)
    assert store.load_text_from_file(path) == data


@pytest.mark.parametrize("path_type", [str, Path])
@pytest.mark.parametrize("data", [
    None,
    b'foob\xc3\xa4r',
])
def test_save_text_to_file_bytes(tmp_path, path_type, data):
    path = path_type(tmp_path / "lala")
    with pytest.raises(TypeError) as e:
        store.save_text_to_file(path, data)
    assert "content argument must be Text, not bytes" in "%s" % e


@pytest.mark.parametrize("path_type", [str, Path])
@pytest.mark.parametrize("data", [
    b'foob\xc3\xa4r',
])
def test_save_bytes_to_file(tmp_path, path_type, data):
    path = path_type(tmp_path / "lala")
    store.save_bytes_to_file(path, data)
    assert store.load_bytes_from_file(path) == data


@pytest.mark.parametrize("path_type", [str, Path])
@pytest.mark.parametrize("data", [
    None,
    u"föö",
])
def test_save_bytes_to_file_unicode(tmp_path, path_type, data):
    path = path_type(tmp_path / "lala")
    with pytest.raises(TypeError) as e:
        store.save_bytes_to_file(path, data)
    assert "content argument must be bytes, not Text" in "%s" % e


@pytest.mark.parametrize("path_type", [str, Path])
def test_save_mk_file(tmp_path, path_type):
    path = path_type(tmp_path / "lala")
    store.save_mk_file(path, "x = 1")
    assert store.load_mk_file(path, default={}) == {"x": 1}


@pytest.mark.parametrize("path_type", [str, Path])
def test_save_to_mk_file(tmp_path, path_type):
    path = path_type(tmp_path / "huhu")
    store.save_to_mk_file(path, "x", {"a": 1})
    assert store.load_mk_file(path, default={"x": {"a": 2, "y": 1}}) == {"x": {"a": 1, "y": 1}}


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


@pytest.mark.parametrize("path_type", [str, Path])
def test_locking(tmp_path, path_type):
    # HACK: We abuse modules as data containers, so we have to do this Kung Fu...
    store1 = store
    store2 = import_module("cmk/utils/store.py")

    assert store1 != store2

    locked_file_path = tmp_path / "locked_file"
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
