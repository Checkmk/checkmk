#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Arguments: unused / shadowing builtins. But we're following argparse.Action protocol.
# ruff: noqa: ARG002,A001,A002

import argparse
import atexit
import sys
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path


def _check_path(filename: str) -> None:
    """make sure we are only writing/reading traces from tmp/debug"""

    p = Path(filename).resolve()
    allowed_path = (Path.home() / "tmp" / "debug").resolve()
    if not p.is_relative_to(allowed_path):
        raise ValueError(f"Traces can only be stored in {allowed_path}")


def vcrtrace(
    filter_body: Callable[[bytes], bytes] = lambda b: b,
    filter_query_parameters: Sequence[tuple[str, str | None]] = (),
    filter_headers: Sequence[tuple[str, str | None]] = (),
    filter_post_data_parameters: Sequence[tuple[str, str | None]] = (),
) -> type[argparse.Action]:
    """Returns the class of an argparse.Action to enter a vcr context

    Provided keyword arguments will be passed to the call of vcrpy.VCR.
    The minimal change to use vcrtrace in your program is to add this
    line to your argument parsing:

        parser.add_argument("--vcrtrace", action=vcrtrace())

    If this flag is set to a TRACEFILE that does not exist yet, it will be created and
    all requests the program sends and their corresponding answers will be recorded in said file.
    If the file already exists, no requests are sent to the server, but the responses will be
    replayed from the tracefile.

    The destination attribute will be set to `True` if the option was specified, the
    provided default otherwise.
    """

    class VcrTraceAction[T](argparse.Action):
        def __init__(
            self,
            option_strings: Sequence[str],
            dest: str,
            nargs: int | str | None = None,
            const: T | None = None,
            default: T | str | None = None,
            type: Callable[[str], T] | argparse.FileType | None = None,
            choices: Iterable[T] | None = None,
            required: bool = False,
            help: str | None = None,
            metavar: str | tuple[str, ...] | None = "TRACEFILE",
        ):
            help_part = (
                "" if vcrtrace.__doc__ is None else vcrtrace.__doc__.split("\n\n")[3]
            )
            help = f"{help_part} {help}" if help else help_part

            super().__init__(
                option_strings=option_strings,
                dest=dest,
                nargs=nargs,
                const=const,
                default=default,
                type=type,
                choices=choices,
                required=required,
                help=help,
                metavar=metavar,
            )

        def __call__(
            self,
            parser: argparse.ArgumentParser,
            namespace: argparse.Namespace,
            values: str | Sequence[object] | None,
            option_string: str | None = None,
        ) -> None:
            if not isinstance(filename := values, str):
                return

            if not sys.stdin.isatty():
                raise argparse.ArgumentError(self, "You need to run this in a tty")

            try:
                _check_path(filename)
            except ValueError as exc:
                raise argparse.ArgumentError(self, str(exc)) from exc

            import vcr
            from vcr.request import Request

            def before_record_request(request: Request) -> Request:
                request.body = filter_body(request.body)
                return request

            setattr(namespace, self.dest, True)
            use_cassette = vcr.VCR(  # type: ignore[no-untyped-call,attr-defined]
                before_record_request=before_record_request,
                filter_query_parameters=filter_query_parameters,
                filter_headers=filter_headers,
                filter_post_data_parameters=filter_post_data_parameters,
            ).use_cassette
            global_context = use_cassette(filename)  # type: ignore[no-untyped-call]
            atexit.register(global_context.__exit__)
            global_context.__enter__()

    return VcrTraceAction
