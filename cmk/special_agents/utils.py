#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Place for common code shared among different Check_MK special agents"""
from __future__ import print_function

import abc
import datetime
import errno
import getopt
import json
import logging
import pprint
import sys
import time

import requests
from pathlib2 import Path
import six

import cmk.utils.store


class AgentJSON(object):
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

        content = {}
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


class DataCache(six.with_metaclass(abc.ABCMeta, object)):
    def __init__(self, cache_file_dir, cache_file_name, debug=False):
        self._cache_file_dir = Path(cache_file_dir)
        self._cache_file = self._cache_file_dir / ("%s.cache" % cache_file_name)
        self.debug = debug

    @abc.abstractproperty
    def cache_interval(self):
        """
        Return the time for how long cached data is valid
        """
        pass

    @abc.abstractmethod
    def get_validity_from_args(self, *args):
        """
        Decide whether we need to update the cache due to new arguments
        """
        pass

    @abc.abstractmethod
    def get_live_data(self, *args):
        """
        This is the function that will be called if no cached data can be found.
        """
        pass

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
        if use_cache:
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
        cmk.utils.store.save_file(str(self._cache_file), json_dump)
