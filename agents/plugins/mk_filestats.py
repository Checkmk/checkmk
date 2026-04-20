#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="possibly-undefined"

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
    It is possible to group files within a file group further into subgroups
    using grouping criteria. The supported options are:
    * ``grouping_regex: regular_expression''
      Assign a file to a subgroup if its full path matches the given regular
      expression.
    * ``grouping_name_template: template''
      (Optional) Build the subgroup name dynamically when the regex matches.
      Placeholders like ``$1`` reference regex capture groups. When omitted,
      the static subgroup name from the configuration section is used.
    A separate service is created for each subgroup, prefixed with its parent
    group name (i.e. <parent group name> <subgroup name>). The order in which
    subgroups and corresponding patterns are specified matters: rules are
    processed in the given order.
    Files that match the specified subgroups are shown as a separate service
    and are excluded from the parent file group.
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
    * ``output: single_file''
      Monitor a single file and send its metrics. If a input_pattern of a .cfg section
      matches multiple files, the agent sents one subsection per file.

You should find an example configuration file at
'../cfg_examples/filestats.cfg' relative to this file.
"""

__version__ = "2.6.0b1"

import collections
import configparser
import errno
import glob
import logging
import operator
import os
import re
import shlex
import sys
import time


def ensure_str(s):
    if isinstance(s, bytes):
        return s.decode("utf-8")
    return s


def ensure_text(s):
    if isinstance(s, bytes):
        return s.decode("utf-8")
    return s


DEFAULT_CFG_FILE = os.path.join(os.getenv("MK_CONFDIR", ""), "filestats.cfg")

DEFAULT_CFG_SECTION = {"output": "file_stats", "subgroups_delimiter": "@"}

GROUPING_TEMPLATE_PLACEHOLDER_RE = re.compile(r"\$(\d+)")

FILTER_SPEC_PATTERN = re.compile("(?P<operator>[<>=]+)(?P<value>.+)")

LOGGER = logging.getLogger(__name__)


def parse_arguments(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parsed_args = {}

    if "-h" in argv or "--help" in argv:
        sys.stderr.write(ensure_str(__doc__))
        sys.exit(0)

    if "-v" in argv or "--verbose" in argv:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    elif "-vv" in argv or "--verbose" in argv:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(lineno)s: %(message)s")
    else:
        LOGGER.propagate = False

    parsed_args["cfg_file"] = DEFAULT_CFG_FILE
    for opt in ("-c", "--config-file"):
        if opt in argv:
            try:
                parsed_args["cfg_file"] = argv[argv.index(opt) + 1]
            except IndexError:
                sys.stderr.write("missing value for option %r\n" % opt)
                sys.exit(1)
    return parsed_args


class FileStat:
    """Wrapper around os.stat

    Only call os.stat once.
    """

    @classmethod
    def from_path(cls, raw_file_path, file_path):
        LOGGER.debug("Creating FileStat(%r)", raw_file_path)
        try:
            file_stat = os.stat(raw_file_path)
        except OSError as exc:
            # report on errors, regard failure as 'file'
            stat_status = "file vanished" if exc.errno == errno.ENOENT else str(exc)
            return cls(file_path, stat_status)

        try:
            size = int(file_stat.st_size)
        except ValueError as exc:
            stat_status = str(exc)
            return cls(file_path, stat_status)

        try:
            m_time = int(file_stat.st_mtime)
            age = int(time.time()) - m_time
        except ValueError as exc:
            stat_status = str(exc)
            return cls(file_path, stat_status, size)

        return cls(file_path, "ok", size, age, m_time)

    def __init__(self, file_path, stat_status, size=None, age=None, m_time=None):
        super().__init__()
        self.file_path = file_path
        self.stat_status = stat_status
        self.size = size
        self.age = age
        self._m_time = m_time

    def dumps(self):
        data = {
            "type": "file",
            "path": self.file_path,
            "stat_status": self.stat_status,
            "size": self.size,
            "age": self.age,
            "mtime": self._m_time,
        }
        return repr(data)


# .
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


def _sanitize_path(raw_file_path):
    # raw_file_path is the value returned by iglob. This value cannot typed meaningfully:
    # * if the path is utf-8 decodable, python2: unicode
    # * if the path is not utf-8 decodable, python2: str
    # * python3: str, possibly with surrogates aka it can only be encoded again like so:
    #   str_with_surrogates.encode('utf-8', 'surrogateescape')
    return raw_file_path.encode("utf-8", "surrogateescape").decode("utf-8", "replace")
    if isinstance(raw_file_path, unicode):  # type: ignore[name-defined,unreachable] # noqa: F821
        return raw_file_path
    return raw_file_path.decode("utf-8", "replace")


class PatternIterator:
    """Recursively iterate over all files"""

    def __init__(self, pattern_list, filters):
        super().__init__()
        self._patterns = [os.path.abspath(os.path.expanduser(p)) for p in pattern_list]
        self._regex_filters = [f for f in filters if isinstance(f, RegexFilter)]
        self._numerical_filters = [f for f in filters if isinstance(f, AbstractNumericFilter)]

    def _file_stats(self, raw_file_paths):
        for raw_file_path in raw_file_paths:
            file_path = _sanitize_path(raw_file_path)
            if not all(f.matches(file_path) for f in self._regex_filters):
                LOGGER.debug("File %r does not match any regex filter", raw_file_path)
                continue

            file_stat = FileStat.from_path(raw_file_path, file_path)
            if not all(f.matches(file_stat) for f in self._numerical_filters):
                LOGGER.debug("File %r does not match any numerical filter", raw_file_path)
                continue

            LOGGER.debug("File %s matches all regex and numerical filters", raw_file_path)
            yield file_stat

    def __iter__(self):
        for pattern in self._patterns:
            LOGGER.info("processing pattern: %r", pattern)
            # pattern needs to be a unicode/python3 str. Otherwise things might go sour, for instance:
            # If we pass "*".encode("utf-8"), then a non-UTF-8 filesystem may no longer realize that
            # b'\x2A' refers to a wildcard. Instead iglob is responsible for conversion.
            for item in glob.iglob(pattern):
                if os.path.isdir(item):
                    # equivalent to `find -type f`
                    for currentpath, _folders, file_names in os.walk(item):
                        for file_stat in self._file_stats(
                            [os.path.join(currentpath, fn) for fn in file_names]
                        ):
                            yield file_stat
                else:
                    for file_stat in self._file_stats([item]):
                        yield file_stat


def get_file_iterator(config):
    """get a FileStat iterator"""
    input_specs = [(k[6:], v) for k, v in config.items() if k.startswith("input_")]
    if not input_specs:
        raise ValueError("missing input definition")
    if len(input_specs) != 1:  # currently not supported
        raise ValueError("multiple input definitions: %r" % input_specs)
    variety, spec_string = input_specs[0]
    if variety != "patterns":
        raise ValueError("unknown input type: %r" % variety)
    patterns = shlex.split(spec_string)
    return PatternIterator(patterns, get_file_filters(config))


# .
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


COMPARATORS = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
}


class AbstractNumericFilter:
    """Common code for filtering by comparing integers"""

    def __init__(self, spec_string):
        super().__init__()
        match = FILTER_SPEC_PATTERN.match(spec_string)
        if match is None:
            raise ValueError("unable to parse filter spec: %r" % spec_string)
        spec = match.groupdict()
        comp = COMPARATORS.get(spec["operator"])
        if comp is None:
            raise ValueError("unknown operator for numeric filter: %r" % spec["operator"])
        reference = int(spec["value"])
        self._matches_value = lambda actual: comp(int(actual), reference)

    def matches(self, filestat):
        raise NotImplementedError()


class SizeFilter(AbstractNumericFilter):
    def matches(self, filestat):
        """apply AbstractNumericFilter ti file size"""
        size = filestat.size
        if size is not None and size != "null":
            return self._matches_value(size)
        # Don't return vanished files.
        # Other cases are a problem, and should be included
        return filestat.stat_status != "file vanished"


class AgeFilter(AbstractNumericFilter):
    def matches(self, filestat):
        """apply AbstractNumericFilter ti file age"""
        age = filestat.age
        if age is not None and age != "null":
            return self._matches_value(age)
        # Don't return vanished files.
        # Other cases are a problem, and should be included
        return filestat.stat_status != "file vanished"


class RegexFilter:
    def __init__(self, regex_pattern):
        super().__init__()
        LOGGER.debug("initializing with pattern: %r", regex_pattern)
        self._regex = re.compile(ensure_text(regex_pattern), re.UNICODE)

    def matches(self, file_path):
        return bool(self._regex.match(file_path))


class InverseRegexFilter(RegexFilter):
    def matches(self, file_path):
        return not self._regex.match(file_path)


def get_file_filters(config):
    filter_specs = ((k[7:], v) for k, v in config.items() if k.startswith("filter_"))

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


# .
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


def parse_grouping_config(
    config,
    raw_config_section_name,
    options,
    subgroups_delimiter,
):
    parent_group_name, child_group_name = raw_config_section_name.split(subgroups_delimiter, 1)

    grouping_type = None
    grouping_rule = None
    name_template = None
    for option in options:
        if not option.startswith("grouping_"):
            continue
        option_suffix = option.split("_", 1)[1]
        option_value = config.get(raw_config_section_name, option)
        if option_suffix == "name_template":
            name_template = option_value
            continue
        grouping_type = option_suffix
        grouping_rule = option_value

    if grouping_type is None or grouping_rule is None:
        raise ValueError(
            "missing grouping rule in section %r" % raw_config_section_name
        )

    grouping_config = {
        "type": grouping_type,
        "rule": grouping_rule,
    }
    if name_template is not None:
        grouping_config["name_template"] = name_template

    LOGGER.info("found subgroup: %s", raw_config_section_name)
    return parent_group_name, (
        child_group_name,
        grouping_config,
    )


def _grouping_construct_group_name(parent_group_name, child_group_name=""):
    """allow the user to format the service name using '%s'.

    >>> _grouping_construct_group_name('aard %s vark', 'banana')
    'aard banana vark'

    >>> _grouping_construct_group_name('aard %s vark %s %s', 'banana')
    'aard banana vark %s %s'

    >>> _grouping_construct_group_name('aard %s vark')
    'aard %s vark'

    >>> _grouping_construct_group_name('aard %s', '')
    'aard %s'
    """

    format_specifiers_count = parent_group_name.count("%s")
    if not format_specifiers_count:
        return ("%s %s" % (parent_group_name, child_group_name)).strip()

    if not child_group_name:
        return parent_group_name

    return (
        parent_group_name % ((child_group_name,) + ("%s",) * (format_specifiers_count - 1))
    ).strip()


def _substitute_group_name(template, match):
    def _replace(placeholder_match):
        group_index = int(placeholder_match.group(1))
        if group_index == 0:
            return match.group(0)
        try:
            return match.group(group_index) or ""
        except IndexError:
            return ""

    return GROUPING_TEMPLATE_PLACEHOLDER_RE.sub(_replace, template)


def _get_matching_child_group(single_file, grouping_conditions):
    for child_group_name, grouping_condition in grouping_conditions:
        regex_match = re.match(grouping_condition["rule"], single_file.file_path)
        if not regex_match:
            continue

        template = grouping_condition.get("name_template")
        if template:
            dynamic_name = _substitute_group_name(template, regex_match)
            if dynamic_name:
                return dynamic_name
        return child_group_name
    return ""


def grouping_multiple_groups(config_section_name, files_iter, grouping_conditions):
    """create multiple groups per section if the agent is configured
    for grouping. each group is shown as a separate service. if a file
    does not belong to a group, it is added to the section."""
    parent_group_name = config_section_name
    # Initalise dict with parent and child group because they should be in the section
    # with 0 count if there are no files for them.
    grouped_files = {
        "": [],  # parent
    }  # type: dict[str, list[FileStat]]
    grouped_files.update({g[0]: [] for g in grouping_conditions if "name_template" not in g[1]})
    for single_file in files_iter:
        matching_child_group = _get_matching_child_group(single_file, grouping_conditions)
        grouped_files.setdefault(matching_child_group, []).append(single_file)

    for matching_child_group, files in grouped_files.items():
        yield _grouping_construct_group_name(parent_group_name, matching_child_group), files


def grouping_single_group(config_section_name, files_iter, _grouping_conditions):
    """create one single group per section"""
    group_name = config_section_name
    yield group_name, files_iter


def get_grouper(grouping_conditions):
    if grouping_conditions:
        return grouping_multiple_groups
    return grouping_single_group


# .
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
    yield "[[[count_only %s]]]" % group_name
    count = sum(1 for __ in files_iter)
    yield repr({"type": "summary", "count": count})


def output_aggregator_file_stats(group_name, files_iter):
    yield "[[[file_stats %s]]]" % group_name
    count = 0
    for count, filestat in enumerate(files_iter, 1):
        yield filestat.dumps()
    yield repr({"type": "summary", "count": count})


def output_aggregator_extremes_only(group_name, files_iter):
    yield "[[[extremes_only %s]]]" % group_name

    files = list(files_iter)
    count = len(files)

    if not count:
        yield repr({"type": "summary", "count": count})
        return

    min_age = max_age = min_size = max_size = files[0]

    for filestat in files[1:]:
        if filestat.age is None:
            continue

        if min_age.age is None or filestat.age < min_age.age:
            min_age = filestat
        if max_age.age is None or filestat.age > max_age.age:
            max_age = filestat
        if min_size.size is None or filestat.size < min_size.size:
            min_size = filestat
        if max_size.size is None or filestat.size > max_size.size:
            max_size = filestat

    for extreme_file in set((min_age, max_age, min_size, max_size)):
        yield extreme_file.dumps()
    yield repr({"type": "summary", "count": count})


def output_aggregator_single_file(group_name, files_iter):
    for lazy_file in files_iter:
        count_format_specifiers = group_name.count("%s")

        if count_format_specifiers == 0:
            subsection_name = group_name
        else:
            subsection_name = group_name % (
                (lazy_file.file_path,) + (("%s",) * (count_format_specifiers - 1))
            )
        yield "[[[single_file %s]]]" % subsection_name
        yield lazy_file.dumps()


def get_output_aggregator(config):
    output_spec = config.get("output")
    try:
        return {
            "count_only": output_aggregator_count_only,
            "extremes_only": output_aggregator_extremes_only,
            "file_stats": output_aggregator_file_stats,
            "single_file": output_aggregator_single_file,
        }[output_spec]
    except KeyError:
        raise ValueError("unknown 'output' spec: %r" % output_spec)


def write_output(groups, output_aggregator):
    for group_name, group_files_iter in groups:
        for line in output_aggregator(group_name, group_files_iter):
            sys.stdout.write("%s\n" % line)


# .
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
    # FIXME: Python 2.6 has no OrderedDict at all, it is only available in a separate ordereddict
    # package, but we simply can't assume that this is installed on the client!
    config = configparser.ConfigParser(
        DEFAULT_CFG_SECTION,
        dict_type=collections.OrderedDict,
    )
    LOGGER.debug("trying to read %r", cfg_file)
    files_read = config.read(cfg_file)
    LOGGER.info("read configration file(s): %r", files_read)

    parsed_config = {}
    for raw_cfg_section_name in config.sections():
        options = config.options(raw_cfg_section_name)
        subgroups_delimiter = config.get(raw_cfg_section_name, "subgroups_delimiter")
        if subgroups_delimiter not in raw_cfg_section_name:
            consolidated_cfg_section_name = raw_cfg_section_name
            parsed_config[consolidated_cfg_section_name] = {
                k: config.get(raw_cfg_section_name, k) for k in options
            }
            continue
        parent_group_name, parsed_grouping_config = parse_grouping_config(
            config,
            raw_cfg_section_name,
            options,
            subgroups_delimiter,
        )
        consolidated_cfg_section_name = parent_group_name
        # TODO: The below suppressions are due to the fact that typing the parsed config properly
        # requires a more sophisticated type (perhaps a class) and a bigger refactoring to validate
        # the options and dispatch immediately after parsing is complete.
        parsed_config[consolidated_cfg_section_name].setdefault(
            "grouping",
            [],  # type: ignore[arg-type]
        ).append(  # type: ignore[attr-defined]
            parsed_grouping_config
        )

    for consolidated_cfg_section_name, parsed_option in parsed_config.items():
        yield consolidated_cfg_section_name, parsed_option


def main():
    args = parse_arguments()

    sys.stdout.write("<<<filestats:sep(0)>>>\n")
    for config_section_name, config in iter_config_section_dicts(args["cfg_file"]):
        # 1 input and
        # 2 filtering
        filtered_files = get_file_iterator(config)

        # 3 grouping
        grouping_conditions = config.get("grouping")
        grouper = get_grouper(grouping_conditions)
        groups = grouper(config_section_name, filtered_files, grouping_conditions)

        # 4 output
        output_aggregator = get_output_aggregator(config)
        write_output(groups, output_aggregator)


if __name__ == "__main__":
    main()
