#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Common module for stuff every special agent should use
Current responsibilities include:
* manages password store
* agent output handling
* exception handling
* common argument parsing
* logging
"""

import argparse
import json
import logging
import sys
import traceback
from collections.abc import Callable, Sequence
from types import GeneratorType
from typing import Any

import urllib3

from cmk.utils.password_store import lookup as lookup_stored_passwords
from cmk.utils.password_store.hack import resolve_password_hack

from cmk.special_agents.v0_unstable.crash_reporting import create_agent_crash_dump


class CannotRecover(RuntimeError):
    """Make the special agent fail gracefully
    Raise this when there is no way to successfully proceed,
    e.g. the server does not respond or credentials are not valid.
    This will make the Check_MK service go critical
    and display the passed message in the GUI.
    In contrast to any other raised exception,
    this will not create a crash report.
    """


class SectionManager:
    def __init__(self) -> None:
        self._data: list[str] = []

    def __enter__(self) -> "SectionManager":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.flush()

    def append(self, data: Any) -> None:
        if isinstance(data, GeneratorType):
            for l in data:
                self.writeline(l)
        else:
            self.writeline(data)

    def append_json(self, data: Any) -> None:
        if isinstance(data, GeneratorType):
            for l in data:
                self.writeline(json.dumps(l, sort_keys=True))
        else:
            self.writeline(json.dumps(data, sort_keys=True))

    def flush(self) -> None:
        for d in self._data:
            sys.stdout.write(str(d))
            sys.stdout.write("\n")
        self._data.clear()
        sys.stdout.flush()

    def writeline(self, line: Any) -> None:
        sys.stdout.write(str(line))
        sys.stdout.write("\n")


class ConditionalPiggybackSection(SectionManager):
    """Exception-Safely open and close a piggyback section
    In order to avoid clumsy constructs it's possible to amend the piggyback sections by
    letting @hostname be falsy
    >>> with ConditionalPiggybackSection("horst"):
    ...     print("foo: bar")
    <<<<horst>>>>
    foo: bar
    <<<<>>>>
    >>> with ConditionalPiggybackSection(None):
    ...     print("foo: bar")
    foo: bar
    """

    def __init__(self, hostname: str | None) -> None:
        super().__init__()
        self.set_piggyback = bool(hostname)
        if self.set_piggyback:
            self.append(f"<<<<{hostname}>>>>")

    def __exit__(self, *exc_info: object) -> None:
        if self.set_piggyback:
            self.append("<<<<>>>>")
        super().__exit__(*exc_info)


class SectionWriter(SectionManager):
    """
    >>> with SectionWriter("foo") as writer:
    ...   writer.append("str")
    ...   writer.append(char for char in "ab")
    ...   writer.append_json({"some": "dict"})
    ...   writer.append_json(char for char in "ab")
    <<<foo:sep(0)>>>
    str
    a
    b
    {"some": "dict"}
    "a"
    "b"
    """

    def __init__(self, section_name: str, separator: str | None = "\0") -> None:
        super().__init__()
        self.append(f"<<<{section_name}{f':sep({ord(separator)})' if separator else ''}>>>")


def _special_agent_main_core(
    parse_arguments: Callable[[Sequence[str] | None], argparse.Namespace],
    main_fn: Callable[[argparse.Namespace], int],
    argv: Sequence[str],
) -> int:
    """Main logic special agents"""
    args = parse_arguments(argv)
    logging.basicConfig(
        format="%(levelname)s %(asctime)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level={0: logging.WARN, 1: logging.INFO, 2: logging.DEBUG}.get(args.verbose, logging.DEBUG),
    )
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    logging.getLogger("vcr").setLevel(logging.WARN)
    logging.info("running file %s", __file__)
    logging.info(
        "using Python interpreter v%s at %s",
        ".".join(map(str, sys.version_info)),
        sys.executable,
    )

    # Don't log args here, it may contain secrets.
    # logging.debug("args: %r", args.__dict__)

    try:
        return main_fn(args)
    except CannotRecover as exc:
        sys.stderr.write(f"{exc}\n")
    except Exception:
        if args.debug:
            raise
        crash_dump = create_agent_crash_dump()
        sys.stderr.write(crash_dump)
        sys.stderr.write(f"\n\n{traceback.format_exc()}")
    return 1


def special_agent_main(
    parse_arguments: Callable[[Sequence[str] | None], argparse.Namespace],
    main_fn: Callable[[argparse.Namespace], int],
    argv: Sequence[str] | None = None,
    *,
    apply_password_store_hack: bool = True,
) -> int:
    """
    Because it modifies sys.argv and part of the functionality is terminating the process with
    the correct return code it's hard to test in unit tests.
    Therefore _active_check_main_core and _output_check_result should be used for unit tests since
    they are not meant to modify the system environment or terminate the process.

    Watch out!
    This will crash unless `parse_arguments` implements the `--debug` and `--verbose` options.
    """
    argv = sys.argv[1:] if argv is None else argv
    return _special_agent_main_core(
        parse_arguments,
        main_fn,
        resolve_password_hack(argv, lookup_stored_passwords) if apply_password_store_hack else argv,
    )
