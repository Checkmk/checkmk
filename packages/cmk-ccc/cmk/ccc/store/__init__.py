#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module cares about Check_MK's file storage accessing. Most important
functionality is the locked file opening realized with the File() context
manager."""

import logging
import pickle
import pprint
import shutil
from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from threading import Lock
from typing import Any

from cmk.ccc.exceptions import MKGeneralException, MKTerminate, MKTimeout
from cmk.ccc.i18n import _
from cmk.ccc.store._file import (
    BytesSerializer,
    DimSerializer,
    FileIo,
    ObjectStore,
    PickleSerializer,
    RealIo,
    Serializer,
    TextSerializer,
)
from cmk.ccc.store._locks import (
    acquire_lock,
    cleanup_locks,
    have_lock,
    lock_checkmk_configuration,
    locked,
    release_all_locks,
    release_lock,
    try_acquire_lock,
    try_locked,
)
from cmk.ccc.store._locks import leave_locked_unless_exception as _leave_locked_unless_exception

__all__ = [
    "BytesSerializer",
    "DimSerializer",
    "FileIo",
    "ObjectStore",
    "PickleSerializer",
    "RealIo",
    "Serializer",
    "TextSerializer",
    "acquire_lock",
    "cleanup_locks",
    "have_lock",
    "lock_checkmk_configuration",
    "locked",
    "release_all_locks",
    "release_lock",
    "try_acquire_lock",
    "try_locked",
]

logger = logging.getLogger("cmk.store")


class LazyTracer:
    def __init__(self):
        self._lock = Lock()
        self._tracer = None

    def span(self, name: str, *, attributes: Mapping[str, str]) -> AbstractContextManager:
        with self._lock:
            if self._tracer is None:
                from cmk.trace import get_tracer

                self._tracer = get_tracer()
        return self._tracer.span(name, attributes=attributes)

    def simple_span(self, name: str, path: Path) -> AbstractContextManager:
        return self.span(f"{name}[{path}]", attributes={"cmk.file.path": str(path)})


tracer = LazyTracer()


# TODO: Make all methods handle paths the same way. e.g. mkdir() and makedirs()
# care about encoding a path to UTF-8. The others don't to that.

# .
#   .--.mk Configs---------------------------------------------------------.
#   |                     _       ____             __ _                    |
#   |           _ __ ___ | | __  / ___|___  _ __  / _(_) __ _ ___          |
#   |          | '_ ` _ \| |/ / | |   / _ \| '_ \| |_| |/ _` / __|         |
#   |         _| | | | | |   <  | |__| (_) | | | |  _| | (_| \__ \         |
#   |        (_)_| |_| |_|_|\_\  \____\___/|_| |_|_| |_|\__, |___/         |
#   |                                                   |___/              |
#   +----------------------------------------------------------------------+
#   | Loading and saving of .mk configuration files                        |
#   '----------------------------------------------------------------------'

# TODO: These functions could handle paths unicode > str conversion. This would make
#       the using code again shorter in some cases. It would not have to care about
#       encoding anymore.


# This function generalizes reading from a .mk configuration file. It is basically meant to
# generalize the exception handling for all file IO. This function handles all those files
# that are read with exec().
def load_mk_file(path: Path, *, default: Mapping[str, object], lock: bool) -> Mapping[str, object]:
    with tracer.simple_span("load_mk_file", path):
        if default is None:  # leave this for now, we still have a lot of `Any`s flying around
            raise MKGeneralException(
                _(
                    "You need to provide a config dictionary to merge with the "
                    "read configuration. The dictionary should have all expected "
                    "keys and their default values set."
                )
            )

        if lock:
            acquire_lock(path)

        try:
            exec(compile(path.read_bytes(), path, "exec"), globals(), default)  # nosec B102 # BNS:aee528
        except FileNotFoundError:
            pass
        except (MKTerminate, MKTimeout):
            raise
        except Exception as e:
            # TODO: How to handle debug mode or logging?
            raise MKGeneralException(_('Cannot read configuration file "%s": %s') % (path, e))

        return default


# A simple wrapper for cases where you only have to read a single value from a .mk file.
def load_from_mk_file[T](path: Path, *, key: str, default: T, lock: bool) -> T:
    # NOTE: The whole typing of the file contents in this module is basically a lie...
    return load_mk_file(path, default={key: default}, lock=lock)[key]  # type: ignore[return-value]


def save_mk_file(path: Path, data: str, *, add_header: bool = True) -> None:
    with tracer.simple_span("save_mk_file", path):
        content = ""
        if add_header:
            content += "# Written by Checkmk store\n\n"
        content += data
        content += "\n"
        save_text_to_file(path, content)


# A simple wrapper for cases where you only have to write a single value to a .mk file.
def save_to_mk_file(path: Path, *, key: str, value: object, pprint_value: bool = False) -> None:
    fmt = pprint.pformat if pprint_value else repr
    save_mk_file(
        path,
        f"{key}.update({fmt(value)})" if isinstance(value, dict) else f"{key} += {fmt(value)}",
    )


# .
#   .--load/save-----------------------------------------------------------.
#   |             _                 _    __                                |
#   |            | | ___   __ _  __| |  / /__  __ ___   _____              |
#   |            | |/ _ \ / _` |/ _` | / / __|/ _` \ \ / / _ \             |
#   |            | | (_) | (_| | (_| |/ /\__ \ (_| |\ V /  __/             |
#   |            |_|\___/ \__,_|\__,_/_/ |___/\__,_| \_/ \___|             |
#   |                                                                      |
#   '----------------------------------------------------------------------'


# Handle .mk files that are only holding a python data structure and often
# directly read via file/open and then parsed using eval.
# TODO: Consolidate with load_mk_file?
def load_object_from_file(path: Path, *, default: Any, lock: bool = False) -> Any:
    with (
        tracer.simple_span("load_object_from_file", path),
        _leave_locked_unless_exception(path) if lock else nullcontext(),
    ):
        return ObjectStore(path, serializer=DimSerializer()).read_obj(default=default)


def load_object_from_pickle_file(path: Path, *, default: Any, lock: bool = False) -> Any:
    with (
        tracer.simple_span("load_object_from_pickle_file", path),
        _leave_locked_unless_exception(path) if lock else nullcontext(),
    ):
        return ObjectStore(path, serializer=PickleSerializer()).read_obj(default=default)


def load_text_from_file(path: Path, *, default: str = "", lock: bool = False) -> str:
    with (
        tracer.simple_span("load_text_from_file", path),
        _leave_locked_unless_exception(path) if lock else nullcontext(),
    ):
        return ObjectStore(path, serializer=TextSerializer()).read_obj(default=default)


def load_bytes_from_file(path: Path, *, default: bytes) -> bytes:
    with tracer.simple_span("load_bytes_from_file", path):
        return ObjectStore(path, serializer=BytesSerializer()).read_obj(default=default)


def save_object_to_file(path: Path, data: object, *, pprint_value: bool = False) -> None:
    store = ObjectStore(path, serializer=DimSerializer(pretty=pprint_value))
    with tracer.simple_span("save_object_to_file", path), store.locked():
        store.write_obj(data)


def save_object_to_pickle_file(path: Path, data: object) -> None:
    store = ObjectStore(path, serializer=PickleSerializer[object]())
    with tracer.simple_span("save_object_to_pickle_file", path), store.locked():
        store.write_obj(data)


def save_text_to_file(path: Path, data: str) -> None:
    store = ObjectStore(path, serializer=TextSerializer())
    with tracer.simple_span("save_text_to_file", path), store.locked():
        store.write_obj(data)


def save_bytes_to_file(path: Path, data: bytes) -> None:
    store = ObjectStore(path, serializer=BytesSerializer())
    with tracer.simple_span("save_bytes_to_file", path), store.locked():
        store.write_obj(data)


def _pickled_files_cache_dir(temp_dir: Path) -> Path:
    return temp_dir / "pickled_files_cache"


def try_load_file_from_pickle_cache(
    path: Path,
    *,
    default: Any,
    lock: bool = False,
    temp_dir: Path,
    root_dir: Path,
) -> Any:
    """Try to load a pickled version of the requested file from cache, otherwise load `path`

    This function tries to find a ".pkl" version of the requested filename in the pickle files cache
    and loads the pickled file, IF the pickled file is more recent.
    Otherwise, if the requested file exists, it is loaded as a raw python object and added to the
    pickle cache for next time.

    The pickled versions are located in the tmpfs directory under the same relative site path.
    They are vanishing when the tmpfs is unmounted (reboots/software updates, etc.)
    If no pickled version exists or the pickled version is older than the original file,
    the original file is read and a pickled version of it is written.

    Note: I'm not a big fan of all this pathlib.Path stuff here, os.path >>> pathlib.Path (7 times slower)
          Let's see how that works out..
    """

    if lock:
        # Lock the original file and try to return the pickled data
        acquire_lock(path)

    try:
        relative_path = path.relative_to(root_dir)  # usually cmk.utils.paths.omd_root
    except ValueError:
        # No idea why someone is trying to load something outside the sites home directory
        return load_object_from_file(path, default=default, lock=lock)

    pickle_path = (
        _pickled_files_cache_dir(temp_dir) / relative_path.parent / (relative_path.name + ".pkl")
    )
    try:
        if pickle_path.stat().st_mtime > path.stat().st_mtime:
            # Use pickled version since this file is newer and therefore valid
            return load_object_from_pickle_file(pickle_path, default=default)
    except (FileNotFoundError, pickle.UnpicklingError):
        pass

    # Scenarios depending on lock
    # lock == True
    #       The original file always exists -> create pickle file, even an empty one
    #       in case the original file just came into existence
    # lock == False
    #       original-missing/pickle-exists: no pickling, use load_object_from_file
    #       original-missing/pickle-missing_broken_outdated: no pickling, use load_object_from_file
    #       original-exists/pickle-missing_broken_outdated: create pickle file
    data = load_object_from_file(path, default=default, lock=lock)
    if path.exists():
        # Only create the pickled version if an original file actually exists
        pickle_path.parent.mkdir(exist_ok=True, parents=True)
        ObjectStore(pickle_path, serializer=PickleSerializer[Any]()).write_obj(data)
    return data


def clear_pickled_files_cache(temp_dir: Path) -> None:
    """Remove all cached pickle files"""
    shutil.rmtree(_pickled_files_cache_dir(temp_dir), ignore_errors=True)
