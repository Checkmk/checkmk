#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Place for common code shared among different Check_MK special agents

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

Please don't add code to this file and allow new components to have a module for their own.
"""

import abc
import argparse
import atexit
import datetime
import json
import logging
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

from requests import Request

from cmk.ccc import store


def datetime_serializer(obj):
    """Custom serializer to pass to json dump functions"""
    if isinstance(obj, datetime.datetime):
        return str(obj)
    # fall back to json default behaviour:
    raise TypeError("%r is not JSON serializable" % obj)


class DataCache(abc.ABC):
    """
    Attention! A user may configure multiple special agents per Checkmk instance.
    Most of the time you don't want to share the Cache between those configurations.
    Normally you should use the hostname as part of the cache_file_name or cache_file_dir.
    """

    def __init__(self, cache_file_dir: Path, cache_file_name: str, debug: bool = False) -> None:
        self._cache_file_dir = cache_file_dir
        self._cache_file = self._cache_file_dir / ("%s.cache" % cache_file_name)
        self.debug = debug

    @property
    @abc.abstractmethod
    def cache_interval(self) -> int:
        """
        Return the time for how long cached data is valid
        """

    @abc.abstractmethod
    def get_validity_from_args(self, *args: Any) -> bool:
        """
        Decide whether we need to update the cache due to new arguments
        """

    @abc.abstractmethod
    def get_live_data(self, *args: Any) -> Any:
        """
        This is the function that will be called if no cached data can be found.
        """

    @property
    def cache_timestamp(self):
        if not self._cache_file.exists():
            return None

        try:
            return self._cache_file.stat().st_mtime
        except FileNotFoundError:
            logging.info("No such file or directory %s (cache_timestamp)", self._cache_file)
            return None
        except OSError as exc:
            logging.info("Cannot calculate cache file age: %s", exc)
            raise

    def _cache_is_valid(self):
        mtime = self.cache_timestamp
        if mtime is None:
            return False

        age = time.time() - mtime
        if 0 < age < self.cache_interval:
            return True

        if age < 0:
            logging.info("Cache file from future considered invalid: %s", self._cache_file)
        else:
            logging.info("Cache file %s is outdated", self._cache_file)
        return False

    def get_cached_data(self):
        try:
            with self._cache_file.open(encoding="utf-8") as f:
                raw_content = f.read().strip()
        except FileNotFoundError:
            logging.info("No such file or directory %s (read from cache)", self._cache_file)
            raise
        except OSError as exc:
            logging.info("Cannot read from cache file: %s", exc)
            raise

        try:
            content = json.loads(raw_content)
        except ValueError as exc:
            logging.info("Cannot load raw content: %s", exc)
            raise
        return content

    def get_data(self, *args, **kwargs):
        use_cache = kwargs.pop("use_cache", True)
        if use_cache and self.get_validity_from_args(*args) and self._cache_is_valid():
            try:
                return self.get_cached_data()
            except (OSError, ValueError) as exc:
                logging.info("Getting live data (failed to read from cache: %s).", exc)
                if self.debug:
                    raise

        live_data = self.get_live_data(*args)
        try:
            self._write_to_cache(live_data)
        except (OSError, TypeError) as exc:
            logging.info("Failed to write data to cache file: %s", exc)
            if self.debug:
                raise
        return live_data

    def _write_to_cache(self, raw_content):
        self._cache_file_dir.mkdir(parents=True, exist_ok=True)

        json_dump = json.dumps(raw_content, default=datetime_serializer)
        store.save_text_to_file(self._cache_file, json_dump)


def _check_path(filename: str) -> None:
    """make sure we are only writing/reading traces from tmp/debug"""

    p = Path(filename).resolve()
    allowed_path = (Path.home() / "tmp" / "debug").resolve()
    if not p.is_relative_to(allowed_path):
        raise ValueError(f"Traces can only be stored in {allowed_path}")


def vcrtrace(
    before_record_request: Callable[[Request], Request] | None = None,
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
        ) -> None:
            help_part = "" if vcrtrace.__doc__ is None else vcrtrace.__doc__.split("\n\n")[3]
            help = f"{help_part} {help}" if help else help_part

            super().__init__(
                option_strings=option_strings,
                dest=dest,
                nargs=nargs,
                const=const,
                default=False,
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
            values: str | Sequence[Any] | None,
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

            setattr(namespace, self.dest, True)
            use_cassette = vcr.VCR(  # type: ignore[attr-defined]
                before_record_request=before_record_request,
                filter_query_parameters=filter_query_parameters,
                filter_headers=filter_headers,
                filter_post_data_parameters=filter_post_data_parameters,
            ).use_cassette
            global_context = use_cassette(filename)
            atexit.register(global_context.__exit__)
            global_context.__enter__()

    return VcrTraceAction
