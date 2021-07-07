#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module cares about Check_MK's file storage accessing. Most important
functionality is the locked file opening realized with the File() context
manager."""

import enum
from contextlib import nullcontext
import logging
import pprint
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from cmk.utils.exceptions import MKGeneralException, MKTerminate, MKTimeout
from cmk.utils.i18n import _

from cmk.utils.store._file import (
    BytesSerializer,
    TextSerializer,
    DimSerializer,
    ObjectStore,
)

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
        return ObjectStore(Path(path), serializer=DimSerializer()).read_obj(default=default)


def load_text_from_file(path: Union[Path, str], default: str = "", lock: bool = False) -> str:
    with _leave_locked_unless_exception(path) if lock else nullcontext():
        return ObjectStore(Path(path), serializer=TextSerializer()).read_obj(default=default)


def load_bytes_from_file(path: Union[Path, str], default: bytes = b"", lock: bool = False) -> bytes:
    with _leave_locked_unless_exception(path) if lock else nullcontext():
        return ObjectStore(Path(path), serializer=BytesSerializer()).read_obj(default=default)


# A simple wrapper for cases where you want to store a python data
# structure that is then read by load_data_from_file() again
def save_object_to_file(path: Union[Path, str], data: Any, pretty: bool = False) -> None:
    serializer = DimSerializer(pretty=pretty)
    # Normally the file is already locked (when data has been loaded before with lock=True),
    # but lock it just to be sure we have the lock on the file.
    #
    # NOTE:
    #  * this creates the file with 0 bytes in case it is missing
    #  * this will leave the file behind unlocked, regardless of it being locked before or
    #    not!
    with locked(path):
        ObjectStore(Path(path), serializer=serializer).write_obj(data)


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
        ObjectStore(Path(path), serializer=TextSerializer()).write_obj(content, mode=mode)


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
        ObjectStore(Path(path), serializer=BytesSerializer()).write_obj(content, mode=mode)


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
