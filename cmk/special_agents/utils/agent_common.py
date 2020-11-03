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

from typing import (
    Sequence,
    List,
    Any,
    Callable,
    Optional,
)
from types import GeneratorType
import argparse
import json
import sys
import logging

import cmk.utils.password_store


class SectionWriter:
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
    def __init__(self, section_name: str) -> None:
        self._data: List[str] = []
        self.append("<<<%s:sep(0)>>>" % section_name)

    def __enter__(self) -> "SectionWriter":
        return self

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        self.flush()

    def append(self, data: Any) -> None:
        self._data += list(data) if isinstance(data, GeneratorType) else [data]

    def append_json(self, data: Any) -> None:
        if isinstance(data, GeneratorType):
            self.append(json.dumps(e) for e in data)
        else:
            self.append(json.dumps(data))

    def flush(self) -> None:
        for d in self._data:
            sys.stdout.write(d)
            sys.stdout.write("\n")
        sys.stdout.flush()
        self._data.clear()


def _special_agent_main_core(
    parse_arguments: Callable[[Optional[Sequence[str]]], argparse.Namespace],
    main_fn: Callable[[argparse.Namespace], None],
    argv: Sequence[str],
) -> None:
    """Main logic special agents"""
    args = parse_arguments(argv)
    logging.basicConfig(
        format="%(levelname)s %(asctime)s %(name)s: %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        level={
            0: logging.WARN,
            1: logging.INFO,
            2: logging.DEBUG
        }.get(args.verbose, logging.DEBUG),
    )

    logging.debug("args: %r", args.__dict__)
    try:
        main_fn(args)
    except Exception as exc:
        if args.debug:
            raise
        sys.stderr.write("Unhandled exception: %r\n" % exc)


def special_agent_main(
    parse_arguments: Callable[[Optional[Sequence[str]]], argparse.Namespace],
    main_fn: Callable[[argparse.Namespace], None],
) -> None:
    """
    Because it modifies sys.argv and part of the functionality is terminating the process with
    the correct return code it's hard to test in unit tests.
    Therefore _active_check_main_core and _output_check_result should be used for unit tests since
    they are not meant to modify the system environment or terminate the process.
    """
    cmk.utils.password_store.replace_passwords()  # type: ignore[no-untyped-call]
    _special_agent_main_core(parse_arguments, main_fn, sys.argv[1:])
