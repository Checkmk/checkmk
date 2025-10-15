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
from pathlib import Path
from typing import Any

from cmk.ccc import store

LOG = logging.getLogger(__name__)


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


class _NullContext:
    """A context manager that does nothing and is falsey"""

    def __call__(self, *_args, **_kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc_info: object) -> None:
        pass

    def __bool__(self) -> bool:
        return False


def _check_path(filename: str) -> None:
    """make sure we are only writing/reading traces from tmp/debug"""

    p = Path(filename).resolve()
    allowed_path = (Path.home() / "tmp" / "debug").resolve()
    if not p.is_relative_to(allowed_path):
        raise ValueError(f"Traces can only be stored in {allowed_path}")


def vcrtrace(**vcr_init_kwargs):
    """Returns the class of an argparse.Action to enter a vcr context

    Provided keyword arguments will be passed to the call of vcrpy.VCR.
    The minimal change to use vcrtrace in your program is to add this
    line to your argument parsing:

        parser.add_argument("--vcrtrace", action=vcrtrace())

    If this flag is set to a TRACEFILE that does not exist yet, it will be created and
    all requests the program sends and their corresponding answers will be recorded in said file.
    If the file already exists, no requests are sent to the server, but the responses will be
    replayed from the tracefile.

    If you need to access the VCRs use_cassette method (e.g. to filter out sensitive data),
    you can do so via the returned args namespace (omitting the filename argument):

        with args.vcrtrace(filter_headers=[('authorization', '*********')]):
            requests.get('https://www.google.de', headers={'authorization': 'mooop'})

    If the corresponding flag ('--vcrtrace' in the above example) was not specified,
    the args attribute will be a null-context.
    """

    class VcrTraceAction(argparse.Action):
        def __init__(self, *args, **kwargs):
            kwargs.setdefault("metavar", "TRACEFILE")
            help_part = "" if vcrtrace.__doc__ is None else vcrtrace.__doc__.split("\n\n")[3]
            kwargs["help"] = "{} {}".format(help_part, kwargs.get("help", ""))
            # NOTE: There are various mypy issues around the kwargs Kung Fu
            # below, see e.g. https://github.com/python/mypy/issues/6799.
            super().__init__(*args, nargs=None, default=False, **kwargs)  # type: ignore[misc]

        def __call__(self, _parser, namespace, filename, option_string=None):
            if not filename:
                setattr(namespace, self.dest, _NullContext())
                return

            if not sys.stdin.isatty():
                raise argparse.ArgumentError(self, "You need to run this in a tty")

            try:
                _check_path(filename)
            except ValueError as exc:
                raise argparse.ArgumentError(self, str(exc)) from exc

            import vcr

            use_cassette = vcr.VCR(**vcr_init_kwargs).use_cassette  # type: ignore[attr-defined]
            setattr(namespace, self.dest, lambda **kwargs: use_cassette(filename, **kwargs))
            global_context = use_cassette(filename)
            atexit.register(global_context.__exit__)
            global_context.__enter__()

    return VcrTraceAction
