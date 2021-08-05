#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import time
import collections
import typing
import fnmatch
from typing import Dict, List, Tuple, Set, Union, Match, Any

from cmk.utils.regex import regex
import cmk.base.plugins.agent_based.utils.eval_regex as eval_regex
from cmk.base.check_api import (
    host_extra_conf,
    host_name,
    get_filesize_human_readable,
    get_age_human_readable,
    check_levels,
    saveint,
    state_markers,
)
import cmk.base.config as config
from cmk.utils.exceptions import MKGeneralException

fileinfo_groups: config.Ruleset = []


def _cast_value(value, data_type):
    try:
        return data_type(value)
    except (ValueError, TypeError):
        return None


def _get_field(row, index):
    try:
        return row[index]
    except IndexError:
        return None


def _parse_single_legacy_row(row, **kwargs):
    name = _cast_value(row[0], str)
    if not name or name.endswith("No such file or directory"):
        # endswith("No such file...") is needed to
        # support the very old solaris perl based version of fileinfo
        return {}
    file_stats_dict = {
        'name': name,
        'size': None,
        'time': None,
        'status': 'ok',
    }
    size = _get_field(row, 1)
    if size == 'missing':
        file_stats_dict['status'] = 'missing'
        return file_stats_dict
    if size in ('not readable', ''):
        file_stats_dict['status'] = 'stat failed'
        return file_stats_dict

    file_stats_dict['size'] = _cast_value(size, int)
    file_stats_dict['time'] = _cast_value(_get_field(row, 2), int)
    return file_stats_dict


def _parse_single_row(row, **kwargs):
    return {
        header_stat[0]: _cast_value(
            header_stat[1],
            kwargs['file_stat_data_types'][header_stat[0]],
        ) for header_stat in zip(kwargs['header'], row)
    }


def _construct_fileinfo_item(name, status, file_stats_dict, FileinfoItem):
    return FileinfoItem(
        name,
        'missing' in status,
        'stat failed' in status,
        file_stats_dict.get('size'),
        file_stats_dict.get('time'),
    )


def parse_fileinfo(info):
    if not info:
        return {}

    parsed = {
        'reftime': _cast_value(info[0][0], int),
        'files': {},
    }

    if len(info) == 1:
        return parsed

    FileinfoItem = collections.namedtuple("FileinfoItem", "name missing failed size time")

    file_stat_data_types = {
        'name': str,
        'size': int,
        'time': int,
        'status': str,
    }

    iter_info = iter(info)
    for row in iter_info:
        if len(row) == 1:
            # the validation whether a section is legacy has to be done inside
            # the loop, because sections might be consolidated, resulting in a
            # legacy section appended to a current section, or vice versa.
            # we have seen this when users monitor both SAP HANA and "regular"
            # files.
            if row == ['[[[header]]]']:
                # non-legacy
                parse_row_func = _parse_single_row
                header = next(iter_info)
                continue
            if row[0].isdigit():
                # designates a timestamp; if following this there is a header (as above),
                # the section is not legacy
                parse_row_func = _parse_single_legacy_row
                header = None
                continue
            continue
        file_stats_dict = parse_row_func(
            row,
            header=header,
            file_stat_data_types=file_stat_data_types,
        )
        name = file_stats_dict.get('name')
        status = file_stats_dict.get('status')
        if not name or not status:
            continue
        parsed['files'][name] = _construct_fileinfo_item(
            name,
            status,
            file_stats_dict,
            FileinfoItem,
        )

    return parsed


def _match(name: str, pattern: str) -> typing.Union[bool, Match, None]:
    return (regex(pattern[1:]).match(name) if pattern.startswith("~") else  #
            fnmatch.fnmatch(name, pattern))


def fileinfo_groups_get_group_name(group_patterns, filename, reftime):
    found_these_groups: Dict[str, Set] = {}
    for group_name, pattern in group_patterns:
        if isinstance(pattern, str):  # support old format
            inclusion, exclusion = pattern, ''
        else:
            inclusion, exclusion = pattern

        if _match(filename, exclusion):
            continue

        inclusion = (("~" + fileinfo_process_date(inclusion[1:], reftime))
                     if inclusion.startswith("~") else fileinfo_process_date(inclusion, reftime))

        incl_match = _match(filename, inclusion)
        if not incl_match:
            continue

        matches = []
        num_perc_s = 0
        if isinstance(incl_match, re.Match):  # it's match object then!
            num_perc_s = group_name.count("%s")
            matches = [g and g or "" for g in incl_match.groups()]

            if len(matches) < num_perc_s:
                raise MKGeneralException(
                    "Invalid entry in inventory_fileinfo_groups: "
                    "group name '%s' contains %d times '%%s', but regular expression "
                    "'%s' contains only %d subexpression(s)." %
                    (group_name, num_perc_s, inclusion, len(matches)))

        if matches:
            for nr, group in enumerate(matches):
                inclusion = eval_regex.instantiate_regex_pattern_once(inclusion, group)
                group_name = group_name.replace("%%%d" % (nr + 1), group)

            this_group_name = group_name % tuple(matches[:num_perc_s])
            this_pattern = ("~%s" % inclusion, exclusion)

        else:
            this_group_name = group_name
            this_pattern = pattern

        found_these_groups.setdefault(this_group_name, set()).add(this_pattern)

    # Convert pattern containers to lists (sets are not possible in autochecks)
    # It is possible now. keep this to not break the "append" in the check function
    return {k: list(v) for k, v in found_these_groups.items()}


def inventory_fileinfo_common(parsed, case):
    inventory: List[Tuple[str, Dict]] = []

    reftime = parsed.get('reftime')
    if reftime is None:
        return inventory

    inventory_groups = host_extra_conf(host_name(), fileinfo_groups)

    for item in parsed['files'].values():
        found_groups = {}
        for group_patterns in inventory_groups:
            found_groups.update(fileinfo_groups_get_group_name(group_patterns, item.name, reftime))

        if not found_groups and case == 'single' and not item.missing:
            inventory.append((item.name, {}))

        elif found_groups and case == 'group':
            for group_name, patterns in found_groups.items():
                inventory.append((group_name, {"group_patterns": patterns}))

    return inventory


def fileinfo_process_date(pattern, reftime):
    for what, the_time in [("DATE", reftime), ("YESTERDAY", reftime - 86400)]:
        the_regex = r'((?:/|[A-Za-z]).*)\$%s:((?:%%\w.?){1,})\$(.*)' % what
        disect = re.match(the_regex, pattern)
        if disect:
            prefix = disect.group(1)
            datepattern = time.strftime(disect.group(2), time.localtime(the_time))
            postfix = disect.group(3)
            pattern = prefix + datepattern + postfix
            return pattern
    return pattern


def fileinfo_check_timeranges(params) -> str:
    ranges = params.get("timeofday")
    if ranges is None:
        return ""

    now = time.localtime()
    for range_spec in ranges:
        if fileinfo_in_timerange(now, *range_spec):
            return ""
    return "Out of relevant time of day"


def check_fileinfo_data(file_stat, reftime, params):
    outof_range_txt = fileinfo_check_timeranges(params)

    if file_stat is not None and not file_stat.missing:
        if file_stat.failed:
            return 1, "File stat failed"
        if file_stat.time is None:
            return 1, 'File stat time failed'
        age = reftime - file_stat.time
        check_definition = [
            ("Size", "size", file_stat.size, get_filesize_human_readable),
            ("Age", "age", age, get_age_human_readable),
        ]
        return _fileinfo_check_function(check_definition, params, outof_range_txt)

    if outof_range_txt:
        return 0, "File not found - %s" % outof_range_txt
    return params.get("state_missing", 3), "File not found"


def fileinfo_in_timerange(now, range_from, range_to) -> bool:
    minutes_from = range_from[0] * 60 + range_from[1]
    minutes_to = range_to[0] * 60 + range_to[1]
    minutes_now = now.tm_hour * 60 + now.tm_min
    return minutes_to > minutes_now >= minutes_from


def _filename_matches(filename, reftime, inclusion, exclusion):
    date_inclusion = ""
    inclusion_is_regex = False
    exclusion_is_regex = False

    if inclusion.startswith("~"):
        inclusion_is_regex = True
        inclusion = inclusion[1:]
    if exclusion.startswith("~"):
        exclusion_is_regex = True
        exclusion = exclusion[1:]

    inclusion_tmp = fileinfo_process_date(inclusion, reftime)
    if inclusion != inclusion_tmp:
        inclusion = inclusion_tmp
        date_inclusion = inclusion_tmp

    incl_match: Union[bool, Match, None] = None
    if inclusion_is_regex:
        incl_match = regex(inclusion).match(filename)
    else:
        incl_match = fnmatch.fnmatch(filename, inclusion)

    excl_match: Union[bool, Match, None] = None
    if exclusion_is_regex:
        excl_match = regex(exclusion).match(filename)
    else:
        excl_match = fnmatch.fnmatch(filename, exclusion)
    return incl_match and not excl_match, date_inclusion


def _update_minmax(new_value: float, current_minmax: typing.Optional[typing.Tuple[float, float]]):

    if not current_minmax:
        return new_value, new_value

    current_min, current_max = current_minmax

    return min(new_value, current_min), max(new_value, current_max)


def _check_individual_files(params, file_size, file_age):
    '''This function checks individual files against levels defined for the file group.
    This is done to generate information for the long output.'''
    states = []
    for key, value in [
        ("age_oldest", file_age),
        ("age_newest", file_age),
        ("size_smallest", file_size),
        ("size_largest", file_size),
    ]:
        levels = params.get("max" + key, (None, None)) + params.get("min" + key, (None, None))
        state, _text, _no_perf = check_levels(value, key, levels)
        states.append(state)

    overall_state = max(states)
    return overall_state, 'Age: %s, Size: %s%s' % (get_age_human_readable(file_age),
                                                   get_filesize_human_readable(file_size),
                                                   state_markers[overall_state])


def _define_fileinfo_group_check(files_matching, date_inclusion):
    size_smallest, size_largest = files_matching['size_minmax'] or (None, None)
    age_newest, age_oldest = files_matching['age_minmax'] or (None, None)
    return [
        ("Count", "count", files_matching['count_all'], saveint),
        ("Size", "size", files_matching['size_all'], get_filesize_human_readable),
        ("Largest size", "size_largest", size_largest, get_filesize_human_readable),
        ("Smallest size", "size_smallest", size_smallest, get_filesize_human_readable),
        ("Oldest age", "age_oldest", age_oldest, get_age_human_readable),
        ("Newest age", "age_newest", age_newest, get_age_human_readable),
        ("Date pattern", "date pattern", date_inclusion, str),
    ]


def _get_group_patterns_from_extra_conf(item):
    '''Return patterns from host extra conf in the event that checks are configured as
    enforced services. This means that the group patterns are not passed to the check
    as parameters.
    '''
    # TODO: find a better way to handle this in the new API
    return [
        rule for e in host_extra_conf(host_name(), fileinfo_groups) for rule_name, rule in e
        if rule_name == item
    ]


def check_fileinfo_groups_data(item, params, parsed, reftime):

    outof_range_txt = fileinfo_check_timeranges(params)
    date_inclusion = None
    files_stat_failed = set()
    files_matching: Dict[str, Any] = {
        'count_all': 0,
        'size_all': 0,
        'size_minmax': None,
        'age_minmax': None,
        'file_text': {},
    }

    skip_ok_files = params.get('shorten_multiline_output', False)

    raw_group_patterns = params.get(
        'group_patterns',
        # group pattern is not available in autochecks for enforced services
        _get_group_patterns_from_extra_conf(item),
    )

    if not raw_group_patterns:
        yield 3, ("No group pattern found.")
        return

    group_patterns = set((p, '') if isinstance(p, str) else p for p in raw_group_patterns)

    # Start counting values on all files
    for file_stat in parsed.get('files', {}).values():
        if file_stat.missing:
            continue

        for inclusion, exclusion in group_patterns:

            filename_matches, date_inclusion = _filename_matches(file_stat.name, reftime, inclusion,
                                                                 exclusion)
            if not filename_matches:
                continue
            if file_stat.failed:
                files_stat_failed.add(file_stat.name)
                break

            files_matching['size_all'] += file_stat.size
            files_matching['count_all'] += 1

            files_matching['size_minmax'] = _update_minmax(file_stat.size,
                                                           files_matching['size_minmax'])

            age = reftime - file_stat.time
            files_matching['age_minmax'] = _update_minmax(age, files_matching['age_minmax'])

            # Used for long ouput information
            state, text = _check_individual_files(params, file_stat.size, age)
            if not skip_ok_files or state:
                files_matching['file_text'][file_stat.name] = text
            break

    # Start Checking
    check_definition = _define_fileinfo_group_check(files_matching, date_inclusion)

    if files_stat_failed:
        yield 1, "Files with unknown stat: %s" % ", ".join(files_stat_failed)

    yield from _fileinfo_check_function(check_definition, params, outof_range_txt)

    yield from _fileinfo_check_conjunctions(check_definition, params)

    long_output = []
    include_patterns = [i for i, _e in group_patterns]
    exclude_patterns = [e for _i, e in group_patterns if e != '']

    long_output.append("Include patterns: %s" % ", ".join(include_patterns))

    if exclude_patterns:
        long_output.append("Exclude patterns: %s" % ", ".join(exclude_patterns))

    long_output.extend(
        ['[%s] %s' % file_text for file_text in sorted(files_matching['file_text'].items())])

    if long_output:
        yield 0, "\n%s" % "\n".join(long_output)


def _fileinfo_check_function(check_definition, params, outof_range_txt):
    infotexts = []
    states = []
    allperfdata: List[List[Any]] = []
    for title, key, value, verbfunc in check_definition:
        if value in [None, ""]:
            continue
        levels = params.get("max" + key, (None, None)) + params.get("min" + key, (None, None))
        state, infotext, perfdata = check_levels(value,
                                                 key,
                                                 levels,
                                                 human_readable_func=verbfunc,
                                                 infoname=title)
        states.append(state)
        infotexts.append(infotext)

        # because strings go into infos but not into perfdata
        if isinstance(value, int):
            allperfdata.append(perfdata)
        else:
            allperfdata.append([])

    if outof_range_txt:
        infotexts = [outof_range_txt] + infotexts
        states = [0] * (len(states) + 1)
        allperfdata = [[]] + allperfdata

    for res in zip(states, infotexts, allperfdata):
        yield res


def inventory_fileinfo(parsed):
    return inventory_fileinfo_common(parsed, "single")


def _fileinfo_check_conjunctions(check_definition, params):
    conjunctions = params.get("conjunctions", [])
    for conjunction_state, levels in conjunctions:
        levels = dict(levels)
        match_texts = []
        matches = 0
        for title, key, value, readable_f in check_definition:
            level = levels.get(key)
            if level is not None and value >= level:
                match_texts.append("%s at %s" % (title.lower(), readable_f(level)))
                matches += 1

            level_lower = levels.get("%s_lower" % key)
            if level_lower is not None and value < level_lower:
                match_texts.append("%s below %s" % (title.lower(), readable_f(level_lower)))
                matches += 1

        if matches == len(levels):
            yield conjunction_state, "Conjunction: %s" % " AND ".join(match_texts)


def inventory_fileinfo_groups(parsed):
    return inventory_fileinfo_common(parsed, "group")
