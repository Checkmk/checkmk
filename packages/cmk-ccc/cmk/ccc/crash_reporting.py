#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module contains functions that can be used in all Check_MK components
to produce crash reports in a generic format which can then be sent to Check_MK
developers for analyzing the crashes."""

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="type-arg"

from __future__ import annotations

import abc
import base64
import inspect
import itertools
import json
import pprint
import sys
import traceback
import urllib.parse
import uuid
from collections.abc import Iterator, Mapping, Sequence
from contextlib import suppress
from itertools import islice
from pathlib import Path
from typing import Any, Final, NotRequired, TypedDict, TypeVar

from cmk.ccc import store

SENSITIVE_KEYWORDS = ["token", "secret", "pass", "key"]

REDACTED_STRING: Final = "redacted"


TDetails = TypeVar("TDetails", bound=dict[str, object] | None)


class BaseDetails(TypedDict):
    argv: Sequence[str]
    env: Mapping[str, str]


class VersionInfo(TypedDict):
    core: str
    python_version: str
    edition: str
    python_paths: Sequence[str]
    version: str
    time: float
    os: str


class ContactDetails(TypedDict):
    name: NotRequired[str]
    email: NotRequired[str]


class CrashInfo[TDetails](VersionInfo):
    exc_type: str | None
    crash_type: str
    exc_traceback: NotRequired[Sequence[tuple[str, int, str, str]]]
    local_vars: str
    details: TDetails
    exc_value: str
    contact: NotRequired[ContactDetails]
    id: str


# The default JSON encoder raises an exception when detecting unknown types. For the crash
# reporting it is totally ok to have some string representations of the objects.
class RobustJSONEncoder(json.JSONEncoder):
    # Are there cases where no __str__ is available? if so, we should do something like %r
    def default(self, o: object) -> str:
        return str(o)


class CrashReportStore:
    _keep_num_crashes = 200
    """Caring about the persistance of crash reports in the local site"""

    def save(self, crash: ABCCrashReport[Any]) -> None:
        """Save the crash report instance to it's crash report directory"""
        self._prepare_crash_dump_directory(crash.crash_dir())

        for key, value in crash.serialize().items():
            fname = "crash.info" if key == "crash_info" else key

            if value is None:
                continue  # type: ignore[unreachable]

            if fname == "crash.info":
                store.save_text_to_file(
                    crash.crash_dir() / fname,
                    self.dump_crash_info(value) + "\n",
                )
            else:
                assert isinstance(value, bytes)
                store.save_bytes_to_file(crash.crash_dir() / fname, value)

        self._cleanup_old_crashes(crash.crash_dir().parent)

    @staticmethod
    def dump_crash_info(crash_info: CrashInfo[TDetails] | bytes) -> str:
        return json.dumps(
            CrashReportStore._dump_crash_info(crash_info),
            cls=RobustJSONEncoder,
            sort_keys=True,
            indent=4,
        )

    @classmethod
    def _dump_crash_info(cls, d: Any) -> Any:
        if not isinstance(d, dict):
            return d
        return {
            k if isinstance(k, str) else json.dumps(k, cls=RobustJSONEncoder): (
                cls._dump_crash_info(v) if isinstance(v, dict) else v
            )
            for k, v in d.items()
        }

    def _prepare_crash_dump_directory(self, crash_dir: Path) -> None:
        crash_dir.mkdir(parents=True, exist_ok=True)

        # Remove all files of former crash reports
        for f in crash_dir.iterdir():
            with suppress(OSError):
                f.unlink()

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
        ):
            # Remove crash report contents
            for f in crash_dir.iterdir():
                with suppress(OSError):
                    f.unlink()

            # And finally remove the crash report directory
            with suppress(OSError):
                crash_dir.rmdir()


class SerializedCrashReport[T](TypedDict):
    crash_info: CrashInfo[T]


def make_crash_report_base_path(omd_root: Path) -> Path:
    return omd_root / "var/check_mk/crashes"


class ABCCrashReport[TDetails](abc.ABC):
    """Base class for the component specific crash report types"""

    def __init__(self, *, crash_report_base_path: Path, crash_info: CrashInfo[TDetails]) -> None:
        super().__init__()
        self.crashdir: Final = crash_report_base_path
        self.crash_info: Final = crash_info

    @classmethod
    @abc.abstractmethod
    def type(cls) -> str:
        raise NotImplementedError()

    @classmethod
    def make_crash_info(
        cls,
        version_info: VersionInfo,
        details: TDetails,
    ) -> CrashInfo[TDetails]:
        """Create a crash info object from the current exception context

        details - Is an optional dictionary of crash type specific attributes
                  that are added to the "details" key of the crash_info.
        """
        return _get_generic_crash_info(cls.type(), version_info, details)

    def _serialize_attributes(self) -> dict[str, CrashInfo[TDetails] | bytes]:
        """Serialize object type specific attributes for transport"""
        return {"crash_info": self.crash_info}

    def serialize(self) -> dict[str, CrashInfo[TDetails] | bytes]:
        """Serialize the object

        Nested structures are allowed. Only objects that can be handled by
        ast.literal_eval() are allowed.
        """
        if self.crash_info is None:
            raise TypeError("No crash information available")

        return self._serialize_attributes()

    def ident(self) -> tuple[str, ...]:
        """Return the identity in form of a tuple of a single crash report"""
        return (self.crash_info["id"],)

    def ident_to_text(self) -> str:
        """Returns the textual representation of the identity

        The parts are separated with "@" signs. The "@" signs found in the parts are
        replaced with "~" which is not allowed to be in the single parts. E.g.
        service names don't have such signs."""
        return "@".join([p.replace("@", "~") for p in self.ident()])

    def crash_dir(self, ident_text: str | None = None) -> Path:
        """Returns the path to the crash directory of the current or given crash report"""
        if ident_text is None:
            ident_text = self.ident_to_text()
        return self.crashdir / self.type() / ident_text

    def local_crash_report_url(self) -> str:
        """Returns the site local URL to the current crash report"""
        return "crash.py?{}".format(
            urllib.parse.urlencode([("component", self.type()), ("ident", self.ident_to_text())])
        )


def _follow_exception_chain(exc: BaseException | None) -> list[BaseException]:
    if exc is None:
        return []

    return [exc] + _follow_exception_chain(
        exc.__context__ if exc.__cause__ is None and not exc.__suppress_context__ else exc.__cause__
    )


def _get_generic_crash_info[TDetails](
    type_name: str,
    version_info: VersionInfo,
    details: TDetails,
) -> CrashInfo[TDetails]:
    """Produces the crash info data structure.

    The top level keys of the crash info dict are standardized and need
    to be set for all crash reports."""
    exc_type, exc_value, _ = sys.exc_info()

    tb_list = list(
        itertools.chain.from_iterable(
            [traceback.extract_tb(exc.__traceback__) for exc in _follow_exception_chain(exc_value)]
        )
    )

    # TODO: The typing gets *really* chaotic here, hence the Any a.k.a implicit cast. :-P
    modified_details: Any = details
    if isinstance(details, Mapping) and "vars" in details:
        modified_details = (
            {k: _sanitize_variables(v) if k == "vars" else v for k, v in details.items()}
            if details
            else {}
        )

    return CrashInfo(
        id=str(uuid.uuid1()),
        crash_type=type_name,
        exc_type=exc_type.__name__ if exc_type else None,
        exc_value=str(exc_value),
        exc_traceback=[tuple(e) for e in tb_list],
        local_vars=_get_local_vars_of_last_exception(),
        details=modified_details,
        core=version_info["core"],
        python_version=version_info["python_version"],
        edition=version_info["edition"],
        python_paths=version_info["python_paths"],
        version=version_info["version"],
        time=version_info["time"],
        os=version_info["os"],
    )


def _get_local_vars_of_last_exception() -> str:
    # Suppressing to handle case where sys.exc_info has no crash information
    # (https://docs.python.org/2/library/sys.html#sys.exc_info)
    with suppress(IndexError):
        local_vars = _sanitize_variables(inspect.trace()[-1][0].f_locals)
    # This needs to be encoded as the local vars might contain binary data which can not be
    # transported using JSON.
    return base64.b64encode(
        _format_var_for_export(pprint.pformat(local_vars).encode("utf-8"), maxsize=5 * 1024 * 1024)
    ).decode()


def _sanitize_variables(unsanitized_variables: dict[str, Any]) -> dict[str, Any]:
    return {
        key: REDACTED_STRING
        if any(sensitive_keyword in key.lower() for sensitive_keyword in SENSITIVE_KEYWORDS)
        else _format_var_for_export(value)
        for key, value in unsanitized_variables.items()
    }


def _format_var_for_export(val: Any, maxdepth: int = 4, maxsize: int = 1024 * 1024) -> Any:
    if maxdepth == 0:
        return "Max recursion depth reached"

    if isinstance(val, dict):
        val = val.copy()
        for item_key, item_val in val.items():
            if any(
                sensitive_keyword in item_key.lower() for sensitive_keyword in SENSITIVE_KEYWORDS
            ):
                val[item_key] = REDACTED_STRING
            else:
                val[item_key] = _format_var_for_export(item_val, maxdepth - 1)

    elif isinstance(val, list):
        val = val[:]
        for index, item in enumerate(val):
            val[index] = _format_var_for_export(item, maxdepth - 1)

    elif isinstance(val, tuple):
        new_val: tuple[Any, ...] = ()
        for item in val:
            new_val += (_format_var_for_export(item, maxdepth - 1),)
        val = new_val

    # Check and limit size
    if isinstance(val, str):
        size = len(val)
        if size > maxsize:
            val = val[:maxsize] + f"... ({(size - maxsize)} bytes stripped)"

    return val
