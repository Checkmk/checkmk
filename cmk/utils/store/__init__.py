#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module cares about Check_MK's file storage accessing. Most important
functionality is the locked file opening realized with the File() context
manager."""

import ast
import enum
from contextlib import nullcontext
import logging
import pprint
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from cmk.utils.exceptions import MKGeneralException, MKTerminate, MKTimeout
from cmk.utils.i18n import _

from cmk.utils.store._locks import (
    MKConfigLockTimeout,
    configuration_lockfile,
    lock_checkmk_configuration,
    lock_exclusive,
    locked,
    aquire_lock,
    try_locked,
    try_aquire_lock,
    release_lock,
    have_lock,
    release_all_locks,
    cleanup_locks,
    leave_locked_unless_exception as _leave_locked_unless_exception,
)

logger = logging.getLogger("cmk.store")

# TODO: Make all methods handle paths the same way. e.g. mkdir() and makedirs()
# care about encoding a path to UTF-8. The others don't to that.

#.
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


def mkdir(path: Union[Path, str], mode: int = 0o770) -> None:
    if not isinstance(path, Path):
        path = Path(path)
    path.mkdir(mode=mode, exist_ok=True)


def makedirs(path: Union[Path, str], mode: int = 0o770) -> None:
    if not isinstance(path, Path):
        path = Path(path)
    path.mkdir(mode=mode, exist_ok=True, parents=True)


#.
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
def load_mk_file(path: Union[Path, str], default: Any = None, lock: bool = False) -> Any:
    if not isinstance(path, Path):
        path = Path(path)

    if default is None:
        raise MKGeneralException(
            _("You need to provide a config dictionary to merge with the "
              "read configuration. The dictionary should have all expected "
              "keys and their default values set."))

    if lock:
        aquire_lock(path)

    try:
        exec(path.read_bytes(), globals(), default)
    except FileNotFoundError:
        pass
    except (MKTerminate, MKTimeout):
        raise
    except Exception as e:
        # TODO: How to handle debug mode or logging?
        raise MKGeneralException(_("Cannot read configuration file \"%s\": %s") % (path, e))

    return default


# A simple wrapper for cases where you only have to read a single value from a .mk file.
def load_from_mk_file(path: Union[Path, str], key: str, default: Any, lock: bool = False) -> Any:
    return load_mk_file(path, {key: default}, lock=False)[key]


def save_mk_file(path: Union[Path, str], mk_content: str, add_header: bool = True) -> None:
    content = ""

    if add_header:
        content += "# Written by Checkmk store\n\n"

    content += mk_content
    content += "\n"
    save_text_to_file(path, content)


# A simple wrapper for cases where you only have to write a single value to a .mk file.
def save_to_mk_file(path: Union[Path, str],
                    key: str,
                    value: Any,
                    pprint_value: bool = False) -> None:
    format_func = repr
    if pprint_value:
        format_func = pprint.pformat

    # mypy complains: "[mypy:] Cannot call function of unknown type"
    if isinstance(value, dict):
        formated = "%s.update(%s)" % (key, format_func(value))
    else:
        formated = "%s += %s" % (key, format_func(value))

    save_mk_file(path, formated)


#.
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
def load_object_from_file(path: Union[Path, str], *, default: Any, lock: bool = False) -> Any:
    with _leave_locked_unless_exception(path) if lock else nullcontext():
        content = _load_bytes_from_file(path).decode("utf-8")

    return ast.literal_eval(content) if content else default


def load_text_from_file(path: Union[Path, str], default: str = "", lock: bool = False) -> str:
    with _leave_locked_unless_exception(path) if lock else nullcontext():
        return _load_bytes_from_file(path).decode("utf-8") or default


def load_bytes_from_file(path: Union[Path, str], default: bytes = b"", lock: bool = False) -> bytes:
    with _leave_locked_unless_exception(path) if lock else nullcontext():
        return _load_bytes_from_file(path) or default


def _load_bytes_from_file(path: Union[Path, str]) -> bytes:
    if not isinstance(path, Path):
        path = Path(path)

    try:

        try:
            return path.read_bytes()
        except FileNotFoundError:
            return b''

    except (MKTerminate, MKTimeout):
        raise
    except Exception as e:
        # TODO: How to handle debug mode or logging?
        raise MKGeneralException(_("Cannot read file \"%s\": %s") % (path, e))


# A simple wrapper for cases where you want to store a python data
# structure that is then read by load_data_from_file() again
def save_object_to_file(path: Union[Path, str], data: Any, pretty: bool = False) -> None:
    formatted_data = pprint.pformat(data) if pretty else repr(data)
    save_text_to_file(path, "%s\n" % formatted_data)


def save_text_to_file(path: Union[Path, str], content: str, mode: int = 0o660) -> None:
    if not isinstance(content, str):
        raise TypeError("content argument must be Text, not bytes")
    # Normally the file is already locked (when data has been loaded before with lock=True),
    # but lock it just to be sure we have the lock on the file.
    #
    # NOTE:
    #  * this creates the file with 0 bytes in case it is missing
    #  * this will leave the file behind unlocked, regardless of it being locked before or
    #    not!
    with locked(path):
        _save_data_to_file(path, content.encode("utf-8"), mode)


def save_bytes_to_file(path: Union[Path, str], content: bytes, mode: int = 0o660) -> None:
    if not isinstance(content, bytes):
        raise TypeError("content argument must be bytes, not Text")
    # Normally the file is already locked (when data has been loaded before with lock=True),
    # but lock it just to be sure we have the lock on the file.
    #
    # NOTE:
    #  * this creates the file with 0 bytes in case it is missing
    #  * this will leave the file behind unlocked, regardless of it being locked before or
    #    not!
    with locked(path):
        _save_data_to_file(path, content, mode)


# Saving assumes a locked destination file (usually done by loading code)
# Then the new file is written to a temporary file and moved to the target path
def _save_data_to_file(path: Union[Path, str], content: bytes, mode: int = 0o660) -> None:
    if not isinstance(path, Path):
        path = Path(path)

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile("wb",
                                         dir=str(path.parent),
                                         prefix=".%s.new" % path.name,
                                         delete=False) as tmp:

            tmp_path = Path(tmp.name)
            tmp_path.chmod(mode)
            tmp.write(content)

            # The goal of the fsync would be to ensure that there is a consistent file after a
            # crash. Without the fsync it may happen that the file renamed below is just an empty
            # file. That may lead into unexpected situations during loading.
            #
            # Don't do a fsync here because this may run into IO performance issues. Even when
            # we can specify the fsync on a fd, the disk cache may be flushed completely because
            # the disk does not know anything about fds, only about blocks.
            #
            # For Checkmk 1.4 we can not introduce a good solution for this, because the changes
            # would affect too many parts of Checkmk with possible new issues. For the moment we
            # stick with the IO behaviour of previous Checkmk versions.
            #
            # In the future we'll find a solution to deal better with OS crash recovery situations.
            # for example like this:
            #
            # TODO(lm): The consistency of the file will can be ensured using copies of the
            # original file which are made before replacing it with the new one. After first
            # successful loading of the just written fille the possibly existing copies of this
            # file are deleted.
            # We can archieve this by calling os.link() before the os.rename() below. Then we need
            # to define in which situations we want to check out the backup open(s) and in which
            # cases we can savely delete them.
            #tmp.flush()
            #os.fsync(tmp.fileno())

        tmp_path.rename(path)

    except (MKTerminate, MKTimeout):
        raise
    except Exception as e:
        if tmp_path:
            tmp_path.unlink(missing_ok=True)

        # TODO: How to handle debug mode or logging?
        raise MKGeneralException(_("Cannot write configuration file \"%s\": %s") % (path, e))


class RawStorageLoader:
    """This is POC class: minimal working functionality. OOP and more clear API is planned"""
    __slots__ = ['_data', '_loaded']

    def __init__(self) -> None:
        self._data: str = ""
        self._loaded: Dict[str, Any] = {}

    def read(self, filename: Path) -> None:
        with filename.open() as f:
            self._data = f.read()

    def parse(self) -> None:
        to_run = "loaded.update(" + self._data + ")"

        exec(to_run, {'__builtins__': None}, {"loaded": self._loaded})

    def apply(self, variables: Dict[str, Any]) -> bool:
        """Stub"""
        isinstance(variables, dict)
        return True

    def _all_hosts(self) -> List[str]:
        return self._loaded.get("all_hosts", [])

    def _host_tags(self) -> Dict[str, Any]:
        return self._loaded.get("host_tags", {})

    def _host_labels(self) -> Dict[str, Any]:
        return self._loaded.get("host_labels", {})

    def _attributes(self) -> Dict[str, Dict[str, Any]]:
        return self._loaded.get("attributes", {})

    def _host_attributes(self) -> Dict[str, Any]:
        return self._loaded.get("host_attributes", {})

    def _explicit_host_conf(self) -> Dict[str, Dict[str, Any]]:
        return self._loaded.get("explicit_host_conf", {})

    def _extra_host_conf(self) -> Dict[str, List[Tuple[str, List[str]]]]:
        return self._loaded.get("extra_host_conf", {})


class StorageFormat(enum.Enum):
    STANDARD = "standard"
    RAW = "raw"

    def __str__(self) -> str:
        return str(self.value)

    @classmethod
    def from_str(cls, value: str) -> 'StorageFormat':
        return cls[value.upper()]

    def extension(self) -> str:
        # This typing error is a false positive.  There are tests to demonstrate that.
        return {  # type: ignore[return-value]
            StorageFormat.STANDARD: ".mk",
            StorageFormat.RAW: ".cfg",
        }[self]

    def hosts_file(self) -> str:
        return "hosts" + self.extension()

    def is_hosts_config(self, filename: str) -> bool:
        """Unified method to determine that the file is hosts config."""
        return filename.startswith("/wato/") and filename.endswith("/" + self.hosts_file())
