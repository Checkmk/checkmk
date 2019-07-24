#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2018             mk@mathias-kettner.de |
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
r"""Check_MK Agent Plugin: mk_filestats

This is a Check_MK Agent plugin. If configured, it will be called by the
agent without any arguments.

usage: mk_filestats [OPTIONS]

Options:
    -h,  --help           Show this help message and exit
    -v,  -vv              Increase verbosity
    -c,  --config-file    Read config file
                          (default: $MK_CONFDIR/filestats.cfg)

Details:

This plugin is configured using ini-style configuration files, i.e. a file with
sections started by lines of the form '[Section Name]' and consisting of
'key: value' (key-colon-space-value) lines.

Every section will be processed individually, and this processing can be
described by the following four phases:

1. Input:
    This phase will gather (iterators returning) the files the plugin will
    initiallly be aware of.
    Option keys concerning this phase a prefixed 'input_'. Currently, there
    is only one option available (which therefore must be present):
    * ``input_patterns'':
      Here you can specify one or more *globbing* patterns. If more than one
      pattern is provided, they will be splitted according to shell rules
      (using shlex.split). Every matching file will be dealt with, every
      matching folder will recursively searched for *all* files.
2. Filtering:
    This phase will filter the input files according to filters provided using
    the option keys starting with 'filter_' of the corresponding configuration
    section. The following are available (note that regex filters will allways
    be applied before other types of filters)
    * ``filter_regex: regular_expression''
      Only further process a file, if its full path matches the given regular
      expression. Everything following the characters 'filter_regex: ' will
      considered one single regular expression.
    * ``filter_regex_inverse: regular_expression''
      Only further process a file, if its full path *does not* match the given
      regular expression.
    * ``filter_size: specification''
      Only further process a file, if its size in bytes matches the provided
      specification. The specification consists of one of the operators '>',
      '<', '>=', '<=' and '==', directly followed by an integer.
      E.g.: 'filter_size: <43008' will only match files smaller than 42 KB.
    * ``filter_age: specification''
      Only further process a file, if its age in seconds matches the filter.
      See ``filter_size''.
3. Grouping
    Currently every section in the configuration file will result in one
    group in the produced output (indicated by '[[[output_type group_name]]]',
    where the group name will be taken from the sections name in the config
    file.
    Future versions may provide means to create more than one group per
    section (grouped by subfolder, for instance).
4. Output
    You can choose from three different ways the output will be aggregated:
    * ``output: file_stats''
      Output the full information for on every single file that is processed.
      This is the default.
    * ``output: count_only''
      Only count the files matching all of the provided filters. Unless
      required for the filtering operation, no stat call on the files is
      made.
    * ``output: extremes_only''
      Only report the youngest, oldest, smallest, and biggest files. In case
      checks only require this information, we can signifficantly reduce data.

You should find an example configuration file at
'../cfg_examples/filestats.cfg' relative to this file.
"""

import errno
import re
import os
import sys
import time
import glob
import shlex
import logging

try:
    import ConfigParser as configparser
except NameError:  # Python3
    import configparser

DEFAULT_CFG_FILE = os.path.join(os.getenv('MK_CONFDIR', ''), "filestats.cfg")

DEFAULT_CFG_SECTION = {"output": "file_stats"}

FILTER_SPEC_PATTERN = re.compile('(?P<operator>[<>=]+)(?P<value>.+)')

LOGGER = logging.getLogger(__name__)


def parse_arguments(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parsed_args = {}

    if "-h" in argv or "--help" in argv:
        sys.stderr.write(__doc__)
        sys.exit(0)

    if "-v" in argv or "--verbose" in argv:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    elif "-vv" in argv or "--verbose" in argv:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(lineno)s: %(message)s")
    else:
        LOGGER.propagate = False

    parsed_args['cfg_file'] = DEFAULT_CFG_FILE
    for opt in ("-c", "--config-file"):
        if opt in argv:
            try:
                parsed_args['cfg_file'] = argv[argv.index(opt) + 1]
            except IndexError:
                sys.stderr.write("missing value for option %r\n" % opt)
                sys.exit(1)
    return parsed_args


class LazyFileStats(object):
    """Wrapper arount os.stat

    Only call os.stat once, and not until corresponding attributes
    are actually needed.
    """
    def __init__(self, path):
        super(LazyFileStats, self).__init__()
        LOGGER.debug("Creating LazyFileStats(%r)", path)
        if not isinstance(path, unicode):
            path = unicode(path, 'utf8')
        self.path = os.path.abspath(path)
        self.stat_status = None
        self._size = None
        self._age = None
        self._m_time = None

    def _stat(self):
        if self.stat_status is not None:
            return

        LOGGER.debug("os.stat(%r)", self.path)

        path = self.path.encode('utf8')
        try:
            stat = os.stat(path)
        except OSError as exc:
            self.stat_status = "file vanished" if exc.errno == errno.ENOENT else str(exc)
            return

        try:
            self._size = int(stat.st_size)
        except ValueError as exc:
            self.stat_status = str(exc)
            return

        try:
            self._m_time = int(stat.st_mtime)
            self._age = int(time.time()) - self._m_time
        except ValueError as exc:
            self.stat_status = str(exc)
            return

        self.stat_status = 'ok'

    @property
    def size(self):
        self._stat()
        return self._size

    @property
    def age(self):
        self._stat()
        return self._age

    def __repr__(self):
        return "LazyFileStats(%r)" % self.path

    def dumps(self):
        data = {
            "type": "file",
            "path": self.path,
            "stat_status": self.stat_status,
            "size": self.size,
            "age": self.age,
            "mtime": self._m_time
        }
        return repr(data)


#.
#   .--Input---------------------------------------------------------------.
#   |                      ___                   _                         |
#   |                     |_ _|_ __  _ __  _   _| |_                       |
#   |                      | || '_ \| '_ \| | | | __|                      |
#   |                      | || | | | |_) | |_| | |_                       |
#   |                     |___|_| |_| .__/ \__,_|\__|                      |
#   |                               |_|                                    |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class PatternIterator(object):
    """Recursively iterate over all files"""
    def __init__(self, pattern_list):
        super(PatternIterator, self).__init__()
        self._patterns = [os.path.expanduser(p) for p in pattern_list]

    def _iter_files(self, pattern):
        for item in glob.iglob(pattern):
            if os.path.isfile(item):
                yield LazyFileStats(item)
            # for now, we recurse unconditionally
            else:
                for lazy_file in self._iter_files(os.path.join(item, '*')):
                    yield lazy_file

    def __iter__(self):
        for pat in self._patterns:
            LOGGER.info("processing pattern: %r", pat)
            for lazy_file in self._iter_files(pat):
                yield lazy_file


def get_file_iterator(config):
    """get a LazyFileStats iterator"""
    input_specs = [(k[6:], v) for k, v in config.items() if k.startswith('input_')]
    if not input_specs:
        raise ValueError("missing input definition")
    if len(input_specs) != 1:  # currently not supported
        raise ValueError("multiple input definitions: %r" % input_specs)
    variety, spec_string = input_specs[0]
    if variety != "patterns":
        raise ValueError("unknown input type: %r" % variety)
    patterns = shlex.split(spec_string)
    return PatternIterator(patterns)


#.
#   .--Filtering-----------------------------------------------------------.
#   |                _____ _ _ _            _                              |
#   |               |  ___(_) | |_ ___ _ __(_)_ __   __ _                  |
#   |               | |_  | | | __/ _ \ '__| | '_ \ / _` |                 |
#   |               |  _| | | | ||  __/ |  | | | | | (_| |                 |
#   |               |_|   |_|_|\__\___|_|  |_|_| |_|\__, |                 |
#   |                                               |___/                  |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


class AbstractFilter(object):
    """Abstract filter interface"""
    def matches(self, lazy_file):
        """return a boolean"""
        raise NotImplementedError()


class AbstractNumericFilter(AbstractFilter):
    """Common code for filtering by comparing integers"""
    def __init__(self, spec_string):
        super(AbstractNumericFilter, self).__init__()
        try:
            spec = FILTER_SPEC_PATTERN.match(spec_string).groupdict()
        except AttributeError:
            raise ValueError("unable to parse filter spec: %r" % spec_string)
        operator, value = spec['operator'], spec['value']
        self._value = int(value)
        if operator not in ('<', '<=', '>', '>=', '=='):
            raise ValueError("unknown operator for numeric filter: %r" % operator)
        self._positive_cmp_results = []
        if '<' in operator:
            self._positive_cmp_results.append(1)
        if '>' in operator:
            self._positive_cmp_results.append(-1)
        if '=' in operator:
            self._positive_cmp_results.append(0)

    def _matches_value(self, other_value):
        """decide whether an integer value matches"""
        return self._value.__cmp__(int(other_value)) in self._positive_cmp_results

    def matches(self, lazy_file):
        raise NotImplementedError()


class SizeFilter(AbstractNumericFilter):
    def matches(self, lazy_file):
        """apply AbstractNumericFilter ti file size"""
        size = lazy_file.size
        if size is not None:
            return self._matches_value(size)
        # Don't return vanished files.
        # Other cases are a problem, and should be included
        return lazy_file.stat_status != "file vanished"


class AgeFilter(AbstractNumericFilter):
    def matches(self, lazy_file):
        """apply AbstractNumericFilter ti file age"""
        age = lazy_file.age
        if age is not None:
            return self._matches_value(age)
        # Don't return vanished files.
        # Other cases are a problem, and should be included
        return lazy_file.stat_status != "file vanished"


class RegexFilter(AbstractFilter):
    def __init__(self, regex_pattern):
        super(RegexFilter, self).__init__()
        LOGGER.debug("initializing with pattern: %r", regex_pattern)
        if not isinstance(regex_pattern, unicode):
            regex_pattern = unicode(regex_pattern, 'utf8')
        self._regex = re.compile(regex_pattern, re.UNICODE)

    def matches(self, lazy_file):
        return bool(self._regex.match(lazy_file.path))


class InverseRegexFilter(RegexFilter):
    def matches(self, lazy_file):
        return not bool(self._regex.match(lazy_file.path))


def get_file_filters(config):
    filter_specs = ((k[7:], v) for k, v in config.items() if k.startswith('filter_'))

    filters = []
    for variety, spec_string in filter_specs:
        LOGGER.debug("found filter spec: %r", (variety, spec_string))
        try:
            filter_type = {
                "regex": RegexFilter,
                "regex_inverse": InverseRegexFilter,
                "size": SizeFilter,
                "age": AgeFilter,
            }[variety]
        except KeyError:
            raise ValueError("unknown filter type: %r" % variety)
        filters.append(filter_type(spec_string))

    # add regex filters first to save stat calls
    return sorted(filters, key=lambda x: not isinstance(x, RegexFilter))


def iter_filtered_files(file_filters, iterator):
    for lazy_file in iterator:
        if all(f.matches(lazy_file) for f in file_filters):
            LOGGER.debug("matched all filters: %r", lazy_file)
            yield lazy_file


#.
#   .--Grouping------------------------------------------------------------.
#   |               ____                       _                           |
#   |              / ___|_ __ ___  _   _ _ __ (_)_ __   __ _               |
#   |             | |  _| '__/ _ \| | | | '_ \| | '_ \ / _` |              |
#   |             | |_| | | | (_) | |_| | |_) | | | | | (_| |              |
#   |              \____|_|  \___/ \__,_| .__/|_|_| |_|\__, |              |
#   |                                   |_|            |___/               |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def grouping_single_group(section_name, files_iter):
    """create one single group per section"""
    yield section_name, files_iter


#.
#   .--Output--------------------------------------------------------------.
#   |                    ___        _               _                      |
#   |                   / _ \ _   _| |_ _ __  _   _| |_                    |
#   |                  | | | | | | | __| '_ \| | | | __|                   |
#   |                  | |_| | |_| | |_| |_) | |_| | |_                    |
#   |                   \___/ \__,_|\__| .__/ \__,_|\__|                   |
#   |                                  |_|                                 |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def output_aggregator_count_only(group_name, files_iter):
    yield '[[[count_only %s]]]' % group_name
    count = sum(1 for __ in files_iter)
    yield repr({"type": "summary", "count": count})


def output_aggregator_file_stats(group_name, files_iter):
    yield "[[[file_stats %s]]]" % group_name
    count = 0
    for count, lazy_file in enumerate(files_iter, 1):
        yield lazy_file.dumps()
    yield repr({"type": "summary", "count": count})


def output_aggregator_extremes_only(group_name, files_iter):
    yield "[[[extremes_only %s]]]" % group_name

    count = 0
    for count, lazy_file in enumerate(files_iter, 1):
        if count == 1:  # init
            min_age = max_age = min_size = max_size = lazy_file
        if lazy_file.age < min_age.age:
            min_age = lazy_file
        elif lazy_file.age > max_age.age:
            max_age = lazy_file
        if lazy_file.size < min_size.size:
            min_size = lazy_file
        elif lazy_file.size > max_size.size:
            max_size = lazy_file

    extremes = set((min_age, max_age, min_size, max_size)) if count else ()
    for extreme_file in extremes:
        yield extreme_file.dumps()
    yield repr({"type": "summary", "count": count})


def get_output_aggregator(config):
    output_spec = config.get("output")
    try:
        return {
            "count_only": output_aggregator_count_only,
            "extremes_only": output_aggregator_extremes_only,
            "file_stats": output_aggregator_file_stats,
        }[output_spec]
    except KeyError:
        raise ValueError("unknown 'output' spec: %r" % output_spec)


def write_output(groups, output_aggregator):
    for group_name, group_files_iter in groups:
        for line in output_aggregator(group_name, group_files_iter):
            sys.stdout.write("%s\n" % line)


#.
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def iter_config_section_dicts(cfg_file=None):
    if cfg_file is None:
        cfg_file = DEFAULT_CFG_FILE
    config = configparser.ConfigParser(DEFAULT_CFG_SECTION)
    LOGGER.debug("trying to read %r", cfg_file)
    files_read = config.read(cfg_file)
    LOGGER.info("read configration file(s): %r", files_read)

    for section_name in config.sections():
        options = config.options(section_name)
        yield section_name, dict((k, config.get(section_name, k)) for k in options)


def main():

    args = parse_arguments()

    sys.stdout.write('<<<filestats:sep(0)>>>\n')
    for section_name, config in iter_config_section_dicts(args['cfg_file']):

        #1 input
        files_iter = get_file_iterator(config)

        #2 filtering
        filters = get_file_filters(config)
        filtered_files = iter_filtered_files(filters, files_iter)

        #3 grouping
        grouper = grouping_single_group
        groups = grouper(section_name, filtered_files)

        #4 output
        output_aggregator = get_output_aggregator(config)
        write_output(groups, output_aggregator)


if __name__ == "__main__":
    main()
