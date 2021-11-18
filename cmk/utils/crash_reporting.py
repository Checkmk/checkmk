#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains functions that can be used in all Check_MK components
to produce crash reports in a generic format which can then be sent to Check_MK
developers for analyzing the crashes."""

from __future__ import annotations

import abc
import base64
import inspect
import json
import pprint
import sys
import traceback
import urllib.parse
import uuid
from contextlib import suppress
from itertools import islice
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple, Type

import cmk.utils.paths
import cmk.utils.plugin_registry
import cmk.utils.store as store
import cmk.utils.version as cmk_version

CrashInfo = Dict[str, Any]  # TODO: improve this type


# The default JSON encoder raises an exception when detecting unknown types. For the crash
# reporting it is totally ok to have some string representations of the objects.
class RobustJSONEncoder(json.JSONEncoder):
    # Are there cases where no __str__ is available? if so, we should do something like %r
    # pylint: disable=method-hidden
    def default(self, o):
        return "%s" % o


class CrashReportStore:
    _keep_num_crashes = 200
    """Caring about the persistance of crash reports in the local site"""

    def save(self, crash: ABCCrashReport) -> None:
        """Save the crash report instance to it's crash report directory"""
        self._prepare_crash_dump_directory(crash)

        for key, value in crash.serialize().items():
            fname = "crash.info" if key == "crash_info" else key

            if value is None:
                continue

            if fname == "crash.info":
                store.save_text_to_file(
                    crash.crash_dir() / fname, str(json.dumps(value, cls=RobustJSONEncoder)) + "\n"
                )
            else:
                store.save_bytes_to_file(crash.crash_dir() / fname, value)

        self._cleanup_old_crashes(crash.crash_dir().parent)

    def _prepare_crash_dump_directory(self, crash: ABCCrashReport) -> None:
        crash_dir = crash.crash_dir()
        crash_dir.mkdir(parents=True, exist_ok=True)

        # Remove all files of former crash reports
        for f in crash_dir.iterdir():
            try:
                f.unlink()
            except OSError:
                pass

    def _cleanup_old_crashes(self, base_dir: Path) -> None:
        """Simple cleanup mechanism: For each crash type we keep up to X crashes"""

        def uuid_paths(path: Path) -> Iterator[Path]:
            for p in path.iterdir():
                try:
                    uuid.UUID(str(p.name))
                except (ValueError, TypeError):
                    continue
                yield p

        for crash_dir in islice(
            sorted(uuid_paths(base_dir), key=lambda p: uuid.UUID(str(p.name)).time, reverse=True),
            self._keep_num_crashes,
            None,
        ):  # type: Path
            # Remove crash report contents
            for f in crash_dir.iterdir():
                with suppress(OSError):
                    f.unlink()

            # And finally remove the crash report directory
            with suppress(OSError):
                crash_dir.rmdir()

    def load_from_directory(self, crash_dir: Path) -> ABCCrashReport:
        """Populate the crash info from the given crash directory"""
        return ABCCrashReport.deserialize(self._load_decoded_from_directory(crash_dir))

    def _load_decoded_from_directory(self, crash_dir: Path) -> Dict[str, Any]:
        serialized = self.load_serialized_from_directory(crash_dir)
        serialized["crash_info"] = json.loads(serialized["crash_info"])
        return serialized

    def load_serialized_from_directory(self, crash_dir: Path) -> Dict[str, bytes]:
        """Load the raw serialized crash report from the given directory

        Nothing is decoded here, the plain files are read into a dictionary. This creates a
        data structure similar to CrashReportsRowTable() in the GUI code."""
        serialized = {}
        for file_path in crash_dir.iterdir():
            key = "crash_info" if file_path.name == "crash.info" else file_path.name
            with file_path.open(mode="rb") as f:
                serialized[key] = f.read()
        return serialized


class ABCCrashReport(abc.ABC):
    """Base class for the component specific crash report types"""

    @classmethod
    @abc.abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @classmethod
    def from_exception(
        cls, details: Optional[Dict] = None, type_specific_attributes: Optional[Dict] = None
    ) -> ABCCrashReport:
        """Create a crash info object from the current exception context

        details - Is an optional dictionary of crash type specific attributes
                  that are added to the "details" key of the crash_info.
        type_specific_attributes - Crash type specific class attributes that
                                   are set as attributes on the crash objects.
        """
        attributes = {
            "crash_info": _get_generic_crash_info(cls.type(), details or {}),
        }
        attributes.update(type_specific_attributes or {})
        return cls(**attributes)

    @classmethod
    def deserialize(cls: Type[ABCCrashReport], serialized: dict) -> ABCCrashReport:
        """Deserialize the object"""
        class_ = crash_report_registry[serialized["crash_info"]["crash_type"]]
        return class_(**serialized)

    def _serialize_attributes(self) -> dict:
        """Serialize object type specific attributes for transport"""
        return {"crash_info": self.crash_info}

    def serialize(self) -> Dict:
        """Serialize the object

        Nested structures are allowed. Only objects that can be handled by
        ast.literal_eval() are allowed.
        """
        if self.crash_info is None:
            raise TypeError("No crash information available")

        return self._serialize_attributes()

    def __init__(self, crash_info: CrashInfo) -> None:
        super().__init__()
        self.crash_info = crash_info

    def ident(self) -> Tuple[str, ...]:
        """Return the identity in form of a tuple of a single crash report"""
        return (self.crash_info["id"],)

    def ident_to_text(self) -> str:
        """Returns the textual representation of the identity

        The parts are separated with "@" signs. The "@" signs found in the parts are
        replaced with "~" which is not allowed to be in the single parts. E.g.
        service descriptions don't have such signs."""
        return "@".join([p.replace("@", "~") for p in self.ident()])

    def crash_dir(self, ident_text: Optional[str] = None) -> Path:
        """Returns the path to the crash directory of the current or given crash report"""
        if ident_text is None:
            ident_text = self.ident_to_text()
        return cmk.utils.paths.crash_dir / self.type() / ident_text

    def local_crash_report_url(self) -> str:
        """Returns the site local URL to the current crash report"""
        return "crash.py?%s" % urllib.parse.urlencode(
            [("component", self.type()), ("ident", self.ident_to_text())]
        )


def _get_generic_crash_info(type_name: str, details: Dict) -> CrashInfo:
    """Produces the crash info data structure.

    The top level keys of the crash info dict are standardized and need
    to be set for all crash reports."""
    exc_type, exc_value, exc_traceback = sys.exc_info()

    tb_list = traceback.extract_tb(exc_traceback)

    # TODO: This ma be cleaned up by using reraising with python 3
    # MKParseFunctionError() are re raised exceptions originating from the
    # parse functions of checks. They have the original traceback object saved.
    # The formated stack of these tracebacks is somehow relative to the calling
    # function. To get the full stack trace instead of this relative one we need
    # to concatenate the traceback of the MKParseFunctionError() and the original
    # exception.
    # Re-raising exceptions will be much easier with Python 3.x.
    if exc_type and exc_value and exc_type.__name__ == "MKParseFunctionError":
        tb_list += traceback.extract_tb(exc_value.exc_info()[2])  # type: ignore[attr-defined]

    # Unify different string types from exception messages to a unicode string
    # HACK: copy-n-paste from cmk.utils.exception.MKException.__str__ below.
    # Remove this after migration...
    if exc_value is None or not exc_value.args:
        exc_txt = str("")
    elif len(exc_value.args) == 1 and isinstance(exc_value.args[0], bytes):
        try:
            exc_txt = exc_value.args[0].decode("utf-8")
        except UnicodeDecodeError:
            exc_txt = "b%s" % repr(exc_value.args[0])
    elif len(exc_value.args) == 1:
        exc_txt = str(exc_value.args[0])
    else:
        exc_txt = str(exc_value.args)

    infos = cmk_version.get_general_version_infos()
    infos.update(
        {
            "id": str(uuid.uuid1()),
            "crash_type": type_name,
            "exc_type": exc_type.__name__ if exc_type else None,
            "exc_value": exc_txt,
            # Py3: Make traceback.FrameSummary serializable
            "exc_traceback": [tuple(e) for e in tb_list],
            "local_vars": _get_local_vars_of_last_exception(),
            "details": details,
        }
    )
    return infos


def _get_local_vars_of_last_exception() -> str:
    local_vars = {}
    try:
        for key, val in inspect.trace()[-1][0].f_locals.items():
            local_vars[key] = _format_var_for_export(val)
    except IndexError:
        # Handle case where sys.exc_info has no crash information
        # (https://docs.python.org/2/library/sys.html#sys.exc_info)
        pass

    # This needs to be encoded as the local vars might contain binary data which can not be
    # transported using JSON.
    return base64.b64encode(
        _format_var_for_export(pprint.pformat(local_vars).encode("utf-8"), maxsize=5 * 1024 * 1024)
    ).decode()


def _format_var_for_export(val: Any, maxdepth: int = 4, maxsize: int = 1024 * 1024) -> Any:
    if maxdepth == 0:
        return "Max recursion depth reached"

    if isinstance(val, dict):
        val = val.copy()
        for item_key, item_val in val.items():
            val[item_key] = _format_var_for_export(item_val, maxdepth - 1)

    elif isinstance(val, list):
        val = val[:]
        for index, item in enumerate(val):
            val[index] = _format_var_for_export(item, maxdepth - 1)

    elif isinstance(val, tuple):
        new_val: Tuple = ()
        for item in val:
            new_val += (_format_var_for_export(item, maxdepth - 1),)
        val = new_val

    # Check and limit size
    if isinstance(val, str):
        size = len(val)
        if size > maxsize:
            val = val[:maxsize] + "... (%d bytes stripped)" % (size - maxsize)

    return val


class CrashReportRegistry(cmk.utils.plugin_registry.Registry[Type[ABCCrashReport]]):
    def plugin_name(self, instance):
        return instance.type()


crash_report_registry = CrashReportRegistry()
