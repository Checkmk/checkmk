#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import functools
import inspect
import json
import os
import pprint
import sys
import time
import traceback
import uuid
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Literal, ParamSpec, Self

_P = ParamSpec("_P")
_CrashType = Literal["agent", "active_check"]

_SSP_CRASH_REPORT_PATH_ENV_VAR = "SERVER_SIDE_PROGRAM_CRASHES_PATH"

_SENSITIVE_KEYWORDS = ["token", "secret", "pass", "key"]

_REDACTED_STRING: Final = "redacted"


def _get_crash_report_path() -> Path | None:
    return Path(crash_path) if (crash_path := os.getenv(_SSP_CRASH_REPORT_PATH_ENV_VAR)) else None


def report_agent_crashes(
    name: str,
    version: str,
) -> Callable[[Callable[_P, int]], Callable[_P, int]]:
    """ "Decorator factory to report crashes from agents

    Wrapping a function with the returned decorator will catch all exceptions raised by the function
    and create a crash report.

    Args:
        name: The name of the agent
        version: The version of the agent

    Example:

        >>> @report_agent_crashes("smith", "1.0.0")
        ... def main() -> int:
        ...     # your code here
        ...     return 0

    """
    return _report_crashes("agent", name, version)


def report_check_crashes(
    name: str,
    version: str,
) -> Callable[[Callable[_P, int]], Callable[_P, int]]:
    """Decorator factory to report crashes from active checks

    Wrapping a function with the returned decorator will catch all exceptions raised by the function
    and create a crash report.

    Args:
        name: The name of the active check
        version: The version of the active check

    Example:

        >>> @report_check_crashes("norris", "1.0.0")
        ... def main() -> int:
        ...     # your code here
        ...     return 0

    """
    return _report_crashes("active_check", name, version)


def _report_crashes(
    type_: _CrashType,
    name: str,
    version: str,
) -> Callable[[Callable[_P, int]], Callable[_P, int]]:
    if (crash_report_path := _get_crash_report_path()) is None:
        return lambda x: x

    def decorator(func: Callable[_P, int]) -> Callable[_P, int]:
        @functools.wraps(func)
        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> int:
            try:
                return func(*args, **kwargs)
            except Exception as outer_exception:
                sys.stderr.write(traceback.format_exc() + "\n")
                try:
                    crash = _CrashReport.from_current_exception(type_, name, version)
                except Exception as inner_exception:
                    sys.stderr.write(traceback.format_exc() + "\n")
                    sys.stderr.write(
                        f"Failed: {outer_exception}"
                        f" - failed to create a crash report: {inner_exception}\n"
                    )
                    return 1

                _store_crash_report(crash, crash_report_path)
                sys.stderr.write(
                    f"Failed: {outer_exception}"
                    f" - please submit a crash report! (Crash-ID: {crash.crash_id})\n"
                )
                return 1

        return wrapper

    return decorator


@dataclass(frozen=True)
class _CrashReport:
    crash_id: str
    crash_type: _CrashType
    exc_type: str | None
    exc_value: str
    exc_traceback: list[tuple[str, int, str, str]]
    local_vars: str
    details: dict[str, str | None]
    core: str
    python_version: str
    edition: str
    python_paths: list[str]
    version: str
    time: float
    os: str

    @classmethod
    def from_current_exception(cls, type_: _CrashType, name: str, version: str) -> Self:
        exc_type, exc_value, _ = sys.exc_info()
        return cls(
            crash_id=str(uuid.uuid1()),
            crash_type=type_,
            exc_type=exc_type.__name__ if exc_type else None,
            exc_value=str(exc_value),
            exc_traceback=[
                tuple(e)
                for exc in _follow_exception_chain(exc_value)
                for e in traceback.extract_tb(exc.__traceback__)
            ],
            details={
                "program_type": type_,
                "program_name": name,
            },
            core="N/A",
            python_version=sys.version,
            python_paths=sys.path,
            edition="N/A",
            version=version,
            time=time.time(),
            os="N/A",
            local_vars=_get_local_vars_of_last_exception(),
        )

    def dump(self) -> str:
        return json.dumps(asdict(self), indent=4)


def _store_crash_report(crash: _CrashReport, crash_report_base_path: Path) -> None:
    crash_dir = crash_report_base_path / crash.crash_type / crash.crash_id
    crash_dir.mkdir(parents=True, exist_ok=True)
    (crash_dir / "crash.info").write_text(crash.dump())


def _follow_exception_chain(exc: BaseException | None) -> list[BaseException]:
    if exc is None:
        return []

    return [exc] + _follow_exception_chain(
        exc.__context__ if exc.__cause__ is None and not exc.__suppress_context__ else exc.__cause__
    )


def _get_local_vars_of_last_exception() -> str:
    # Suppressing to handle case where sys.exc_info has no crash information
    # (https://docs.python.org/2/library/sys.html#sys.exc_info)
    with suppress(IndexError):
        local_vars = _format_var_for_export(inspect.trace()[-1][0].f_locals)
    # This needs to be encoded as the local vars might contain binary data which can not be
    # transported using JSON.
    return base64.b64encode(
        _truncate_str(pprint.pformat(local_vars), max_size=5 * 1024 * 1024).encode("utf-8")
    ).decode()


def _truncate_str(value: str, max_size: int) -> str:
    """truncate a string if it is too long and add how much was truncated

    >>> _truncate_str("foo", 3)
    'foo'
    >>> _truncate_str("foo", 2)
    'fo... (1 bytes stripped)'
    """
    if (size := len(value)) > max_size:
        return value[:max_size] + f"... ({(size - max_size)} bytes stripped)"
    return value


def _format_var_for_export(val: object, maxdepth: int = 4, maxsize: int = 1024 * 1024) -> object:
    if maxdepth == 0:
        return "Max recursion depth reached"

    match val:
        case Mapping():
            return {
                k: _REDACTED_STRING
                if _key_indicates_sensitivity(k)
                else _format_var_for_export(v, maxdepth - 1)
                for k, v in val.items()
            }

        case list() | set() | tuple():
            return type(val)(_format_var_for_export(item, maxdepth - 1) for item in val)

        # Check and limit size
        case str():
            return _truncate_str(val, maxsize)

        case _:
            return val


def _key_indicates_sensitivity(key: object) -> bool:
    return isinstance(key, str) and any(
        indicator in key.lower() for indicator in _SENSITIVE_KEYWORDS
    )
