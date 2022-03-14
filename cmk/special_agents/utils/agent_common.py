#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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
from types import GeneratorType
from typing import Any, Callable, List, Optional, Sequence

import urllib3

import cmk.utils.password_store


class SectionManager:
    def __init__(self) -> None:
        self._data: List[str] = []

    def __enter__(self) -> "SectionManager":
        return self

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
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

    def writeline(self, line: Any):
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

    def __init__(self, hostname: Optional[str]) -> None:
        super().__init__()
        self.set_piggyback = bool(hostname)
        if self.set_piggyback:
            self.append(f"<<<<{hostname}>>>>")

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        if self.set_piggyback:
            self.append("<<<<>>>>")
        super().__exit__(*args, **kwargs)


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

    def __init__(self, section_name: str, separator: Optional[str] = "\0") -> None:
        super().__init__()
        self.append(f"<<<{section_name}{f':sep({ord(separator)})' if separator else ''}>>>")


def _special_agent_main_core(
    parse_arguments: Callable[[Optional[Sequence[str]]], argparse.Namespace],
    main_fn: Callable[[argparse.Namespace], None],
    argv: Sequence[str],
) -> None:
    """Main logic special agents"""
    args = parse_arguments(argv)
    logging.basicConfig(
        format="%(levelname)s %(asctime)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level={0: logging.WARN, 1: logging.INFO, 2: logging.DEBUG}.get(args.verbose, logging.DEBUG),
    )
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # type: ignore
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    logging.getLogger("vcr").setLevel(logging.WARN)
    logging.info("running file %s", __file__)
    logging.info(
        "using Python interpreter v%s at %s",
        ".".join(map(str, sys.version_info)),
        sys.executable,
    )

    logging.debug("args: %r", args.__dict__)

    try:
        main_fn(args)
    except Exception:
        if args.debug:
            raise
        exctype, value, tb = sys.exc_info()
        assert exctype is not None and tb is not None
        print(
            f"Caught unhandled {exctype.__name__}({value})"
            f" in {tb.tb_frame.f_code.co_filename}:{tb.tb_lineno}",
            file=sys.stderr,
        )
        raise SystemExit(1)


def special_agent_main(
    parse_arguments: Callable[[Optional[Sequence[str]]], argparse.Namespace],
    main_fn: Callable[[argparse.Namespace], None],
    argv: Optional[Sequence[str]] = None,
) -> None:
    """
    Because it modifies sys.argv and part of the functionality is terminating the process with
    the correct return code it's hard to test in unit tests.
    Therefore _active_check_main_core and _output_check_result should be used for unit tests since
    they are not meant to modify the system environment or terminate the process.
    """
    cmk.utils.password_store.replace_passwords()  # type: ignore[no-untyped-call]
    _special_agent_main_core(parse_arguments, main_fn, argv or sys.argv[1:])
