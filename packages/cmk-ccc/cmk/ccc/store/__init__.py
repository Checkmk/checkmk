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
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from cmk.ccc.exceptions import MKGeneralException, MKTerminate, MKTimeout
from cmk.ccc.i18n import _
from cmk.ccc.store._file import (
    BytesSerializer,
    DimSerializer,
    ObjectStore,
    PickleSerializer,
    PydanticStore,
    Serializer,
    TextSerializer,
)
from cmk.ccc.store._locks import (
    acquire_lock,
    cleanup_locks,
    have_lock,
    lock_checkmk_configuration,
    lock_exclusive,
    locked,
    release_all_locks,
    release_lock,
    try_acquire_lock,
    try_locked,
)
from cmk.ccc.store._locks import leave_locked_unless_exception as _leave_locked_unless_exception

from cmk import trace

__all__ = [
    "BytesSerializer",
    "DimSerializer",
    "ObjectStore",
    "PickleSerializer",
    "Serializer",
    "PydanticStore",
    "TextSerializer",
    "acquire_lock",
    "cleanup_locks",
    "have_lock",
    "lock_checkmk_configuration",
    "lock_exclusive",
    "locked",
    "release_all_locks",
    "release_lock",
    "try_acquire_lock",
    "try_locked",
]

logger = logging.getLogger("cmk.store")
tracer = trace.get_tracer()

# TODO: Make all methods handle paths the same way. e.g. mkdir() and makedirs()
# care about encoding a path to UTF-8. The others don't to that.

# .
#   .--Directories---------------------------------------------------------.
#   |           ____  _               _             _                      |
#   |          |  _ \(_)_ __ ___  ___| |_ ___  _ __(_) ___  ___            |
#   |          | | | | | '__/ _ \/ __| __/ _ \| '__| |/ _ \/ __|           |
#   |          | |_| | | | |  __/ (__| || (_) | |  | |  __/\__ \           |
#   |          |____/|_|_|  \___|\___|\__\___/|_|  |_|\___||___/           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Some small wrappers around the python standard directory handling    |
#   | functions.                                                           |
#   '----------------------------------------------------------------------'


def mkdir(path: Path | str, mode: int = 0o770) -> None:
    if not isinstance(path, Path):
        path = Path(path)
    path.mkdir(mode=mode, exist_ok=True)


def makedirs(path: Path | str, mode: int = 0o770) -> None:
    if not isinstance(path, Path):
        path = Path(path)
    path.mkdir(mode=mode, exist_ok=True, parents=True)


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
def load_mk_file(
    path: Path | str, default: Mapping[str, object], lock: bool = False
) -> Mapping[str, object]:
    with tracer.span(
        f"load_mk_file[{path}]",
        attributes={"cmk.file.path": str(path)},
    ):
        if not isinstance(path, Path):
            path = Path(path)

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
def load_from_mk_file(path: Path | str, key: str, default: Any, lock: bool = False) -> Any:
    return load_mk_file(path, {key: default}, lock=lock)[key]


def save_mk_file(path: Path | str, mk_content: str, add_header: bool = True) -> None:
    with tracer.span(
        f"save_mk_file[{path}]",
        attributes={"cmk.file.path": str(path)},
    ):
        content = ""

        if add_header:
            content += "# Written by Checkmk store\n\n"

        content += mk_content
        content += "\n"
        save_text_to_file(path, content)


# A simple wrapper for cases where you only have to write a single value to a .mk file.
def save_to_mk_file(path: Path | str, key: str, value: Any, pprint_value: bool = False) -> None:
    format_func = repr
    if pprint_value:
        format_func = pprint.pformat

    # mypy complains: "[mypy:] Cannot call function of unknown type"
    if isinstance(value, dict):
        formated = f"{key}.update({format_func(value)})"
    else:
        formated = f"{key} += {format_func(value)}"

    save_mk_file(path, formated)


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
def load_object_from_file(path: Path | str, *, default: Any, lock: bool = False) -> Any:
    with (
        tracer.span(
            f"load_object_from_file[{path}]",
            attributes={"cmk.file.path": str(path)},
        ),
        _leave_locked_unless_exception(path) if lock else nullcontext(),
    ):
        return ObjectStore(Path(path), serializer=DimSerializer()).read_obj(default=default)


def load_object_from_pickle_file(path: Path | str, *, default: Any, lock: bool = False) -> Any:
    with (
        tracer.span(
            f"load_object_from_pickle_file[{path}]",
            attributes={"cmk.file.path": str(path)},
        ),
        _leave_locked_unless_exception(path) if lock else nullcontext(),
    ):
        return ObjectStore(Path(path), serializer=PickleSerializer()).read_obj(default=default)


def load_text_from_file(path: Path | str, default: str = "", lock: bool = False) -> str:
    with (
        tracer.span(
            f"load_text_from_file[{path}]",
            attributes={"cmk.file.path": str(path)},
        ),
        _leave_locked_unless_exception(path) if lock else nullcontext(),
    ):
        return ObjectStore(Path(path), serializer=TextSerializer()).read_obj(default=default)


def load_bytes_from_file(path: Path | str, default: bytes = b"", lock: bool = False) -> bytes:
    with (
        tracer.span(
            f"load_bytes_from_file[{path}]",
            attributes={"cmk.file.path": str(path)},
        ),
        _leave_locked_unless_exception(path) if lock else nullcontext(),
    ):
        return ObjectStore(Path(path), serializer=BytesSerializer()).read_obj(default=default)


def save_object_to_file(path: Path | str, data: Any, pretty: bool = False) -> None:
    _write(Path(path), DimSerializer(pretty=pretty), data)


# A simple wrapper for cases where you want to store a python data with pickle
# that is then read by load_object_from_pickle_file() again
def save_object_to_pickle_file(path: Path | str, data: Any) -> None:
    serializer = PickleSerializer[Any]()
    # Normally the file is already locked (when data has been loaded before with lock=True),
    # but lock it just to be sure we have the lock on the file.
    #
    # NOTE:
    #  * this creates the file with 0 bytes in case it is missing
    #  * this will leave the file behind unlocked, regardless of it being locked before or
    #    not!
    with locked(path):
        ObjectStore(Path(path), serializer=serializer).write_obj(data)


def save_text_to_file(path: Path | str, content: str) -> None:
    if not isinstance(content, str):
        raise TypeError("content argument must be Text, not bytes")
    _write(Path(path), TextSerializer(), content)


def save_bytes_to_file(path: Path | str, content: bytes) -> None:
    if not isinstance(content, bytes):
        raise TypeError("content argument must be bytes, not Text")
    _write(Path(path), BytesSerializer(), content)


def _write(path: Path, serializer: Serializer, content: Any) -> None:
    store = ObjectStore(Path(path), serializer=serializer)
    # Normally the file is already locked (when data has been loaded before with lock=True),
    # but lock it just to be sure we have the lock on the file.
    #
    # NOTE:
    #  * this creates the file with 0 bytes in case it is missing
    with (
        tracer.span(
            f"_write[{path}]",
            attributes={"cmk.file.path": str(path)},
        ),
        store.locked(),
    ):
        store.write_obj(content)


def _pickled_files_cache_dir(temp_dir: Path) -> Path:
    return temp_dir / "pickled_files_cache"


_pickle_serializer = PickleSerializer[Any]()


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
        ObjectStore(pickle_path, serializer=_pickle_serializer).write_obj(data)
    return data


def clear_pickled_files_cache(temp_dir: Path) -> None:
    """Remove all cached pickle files"""
    shutil.rmtree(_pickled_files_cache_dir(temp_dir), ignore_errors=True)
