#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Place for common code shared among different Check_MK special agents

Please don't add code to this file and allow new components to have a module for their own.
"""

import abc
import argparse
import atexit
import datetime
import errno
import getopt
import json
import logging
from pathlib import Path
import pprint
import sys
import time
from typing import Any, Dict, List

import requests

import cmk.utils.store as store


class AgentJSON:
    def __init__(self, key, title):
        self._key = key
        self._title = title

    def usage(self):
        sys.stderr.write("""
Check_MK %s Agent

USAGE: agent_%s --section_url [{section_name},{url}]

    Parameters:
        --section_url   Pair of section_name and url
                        Can be defined multiple times
        --debug         Output json data with pprint

""" % (self._title, self._key))

    def get_content(self):
        short_options = "h"
        long_options = ["section_url=", "help", "newline_replacement=", "debug"]

        try:
            opts, _args = getopt.getopt(sys.argv[1:], short_options, long_options)
        except getopt.GetoptError as err:
            sys.stderr.write("%s\n" % err)
            sys.exit(1)

        sections = []
        newline_replacement = "\\n"
        opt_debug = False

        for o, a in opts:
            if o in ["--section_url"]:
                sections.append(a.split(",", 1))
            elif o in ["--newline_replacement"]:
                newline_replacement = a
            elif o in ["--debug"]:
                opt_debug = True
            elif o in ['-h', '--help']:
                self.usage()
                sys.exit(0)

        if not sections:
            self.usage()
            sys.exit(0)

        content: Dict[str, List[str]] = {}
        for section_name, url in sections:
            content.setdefault(section_name, [])
            content[section_name].append(requests.get(url).text.replace("\n", newline_replacement))

        if opt_debug:
            for line in content:
                try:
                    pprint.pprint(json.loads(line))
                except Exception:
                    print(line)
        else:
            return content


def datetime_serializer(obj):
    """Custom serializer to pass to json dump functions"""
    if isinstance(obj, datetime.datetime):
        return obj.__str__()
    # fall back to json default behaviour:
    raise TypeError("%r is not JSON serializable" % obj)


class DataCache(abc.ABC):
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
        except OSError as exc:
            if exc.errno == errno.ENOENT:
                logging.info("No such file or directory %s (cache_timestamp)", self._cache_file)
                return None
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
        except IOError as exc:
            if exc.errno == errno.ENOENT:
                logging.info("No such file or directory %s (read from cache)", self._cache_file)
            else:
                logging.info("Cannot read from cache file: %s", exc)
            raise

        try:
            content = json.loads(raw_content)
        except ValueError as exc:
            logging.info("Cannot load raw content: %s", exc)
            raise
        return content

    def get_data(self, *args, **kwargs):
        use_cache = kwargs.pop('use_cache', True)
        if (use_cache and self.get_validity_from_args(*args) and self._cache_is_valid()):
            try:
                return self.get_cached_data()
            except (OSError, IOError, ValueError) as exc:
                logging.info("Getting live data (failed to read from cache: %s).", exc)
                if self.debug:
                    raise

        live_data = self.get_live_data(*args)
        try:
            self._write_to_cache(live_data)
        except (OSError, IOError, TypeError) as exc:
            logging.info("Failed to write data to cache file: %s", exc)
            if self.debug:
                raise
        return live_data

    def _write_to_cache(self, raw_content):
        self._cache_file_dir.mkdir(parents=True, exist_ok=True)

        json_dump = json.dumps(raw_content, default=datetime_serializer)
        store.save_file(str(self._cache_file), json_dump)


class _NullContext:
    """A context manager that does nothing and is falsey"""
    def __call__(self, *_args, **_kwargs):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass

    def __bool__(self):
        return False


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
            help_part = "" if vcrtrace.__doc__ is None else vcrtrace.__doc__.split('\n\n')[3]
            kwargs["help"] = "%s %s" % (help_part, kwargs.get("help", ""))
            # NOTE: There are various mypy issues around the kwargs Kung Fu
            # below, see e.g. https://github.com/python/mypy/issues/6799.
            super(VcrTraceAction, self).__init__(  # type: ignore[misc]
                *args, nargs=None, default=False, **kwargs)

        def __call__(self, _parser, namespace, filename, option_string=None):
            if not filename:
                setattr(namespace, self.dest, _NullContext())
                return

            import vcr  # type: ignore[import] # pylint: disable=import-outside-toplevel
            use_cassette = vcr.VCR(**vcr_init_kwargs).use_cassette
            setattr(namespace, self.dest, lambda **kwargs: use_cassette(filename, **kwargs))
            global_context = use_cassette(filename)
            atexit.register(global_context.__exit__)
            global_context.__enter__()

    return VcrTraceAction


def get_seconds_since_midnight(current_time) -> float:
    midnight = datetime.datetime.combine(current_time.date(), datetime.datetime.min.time())
    return (current_time - midnight).total_seconds()
