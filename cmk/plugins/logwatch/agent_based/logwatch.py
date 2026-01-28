#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="redundant-expr"
# mypy: disable-error-code="type-arg"

#########################################################################################
#                                                                                       #
#                                 !!   W A T C H   O U T   !!                           #
#                                                                                       #
#   The logwatch plug-in is notorious for being an exception to just about every rule   #
#   or best practice that applies to check plug-in development.                         #
#   It is highly discouraged to use this a an example!                                  #
#                                                                                       #
#########################################################################################

import fnmatch
import hashlib
import re
import time
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from re import Match
from typing import IO, Literal, TypedDict

# for now, we shamelessly violate the API:
import cmk.ccc.debug
import cmk.utils.paths
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    render,
    Result,
    RuleSetType,
    Service,
    State,
)
from cmk.plugins.lib import eval_regex

from . import commons as logwatch

ClusterSection = dict[str | None, logwatch.Section]

GroupingPattern = tuple[str, str]


class DiscoveredGroupParams(TypedDict):
    group_patterns: Iterable[GroupingPattern]
    host_name: str


_LOGWATCH_MAX_FILESIZE = 500000  # do not save more than 500k of messages


# New rule-stule logwatch_rules in WATO friendly consistent rule notation:
#
# logwatch_rules = [
#   ( [ PATTERNS ], ALL_HOSTS, [ "Application", "System" ] ),
# ]
# All [ PATTERNS ] of matching rules will be concatenated in order of
# appearance.
#
# PATTERN is a list like:
# [ ( 'O',      ".*ssh.*" ),          # Make informational (OK) messages from these
#   ( (10, 20), "login"   ),          # Warning at 10 messages, Critical at 20
#   ( 'C',      "bad"     ),          # Always critical
#   ( 'W',      "not entirely bad" ), # Always warning
# ]
#


def discover_logwatch_single(
    params: Sequence[logwatch.ParameterLogwatchGroups],
    section: logwatch.Section,
) -> DiscoveryResult:
    _groups, singles = _discovery_make_groups(params, section)
    yield from (
        Service(item=item, labels=logwatch.NEVER_DISCOVER_SERVICE_LABELS) for item in singles
    )


def discover_logwatch_groups(
    params: Sequence[logwatch.ParameterLogwatchGroups],
    section: logwatch.Section,
) -> DiscoveryResult:
    groups, _singles = _discovery_make_groups(params, section)
    yield from (
        Service(
            item=group.name,
            parameters={"group_patterns": sorted(group.patterns)},
            labels=logwatch.NEVER_DISCOVER_SERVICE_LABELS,
        )
        for group in groups
    )


@dataclass
class _Group:
    name: str
    items: set[str]
    patterns: set[GroupingPattern]


def _discovery_make_groups(
    params: Sequence[logwatch.ParameterLogwatchGroups],
    section: logwatch.Section,
) -> tuple[Sequence[_Group], Iterable[str]]:
    log_filter = logwatch.LogFileFilter(
        logwatch.RulesetAccess.logwatch_ec_all(params[0]["host_name"])
    )
    not_forwarded_logs = {
        item for item in logwatch.discoverable_items(section) if not log_filter.is_forwarded(item)
    }
    all_group_patterns = [p["grouping_patterns"] for p in params if "grouping_patterns" in p]

    groups: dict[str, _Group] = {}
    for item in not_forwarded_logs:
        for group_patterns in all_group_patterns:
            for group_name, pattern_set in _groups_of_logfile(group_patterns, item).items():
                group = groups.setdefault(
                    group_name, _Group(name=group_name, items=set(), patterns=set())
                )
                group.items.add(item)
                group.patterns.update(pattern_set)

    return list(groups.values()), not_forwarded_logs - {i for g in groups.values() for i in g.items}


def check_logwatch_node(
    item: str,
    params: Mapping[Literal["host_name"], str],
    section: logwatch.Section,
) -> CheckResult:
    """fall back to the cluster case with node=None"""
    host_name = params["host_name"]
    rules_params = logwatch.RulesetAccess.logwatch_rules_all(
        host_name=host_name, plugin=check_plugin_logwatch, logfile=item
    )
    yield from check_logwatch(item, rules_params, {None: section}, host_name)


def check_logwatch_cluster(
    item: str,
    params: Mapping[str, str],
    section: Mapping[str, logwatch.Section | None],
) -> CheckResult:
    host_name = params["host_name"]
    rules_params = logwatch.RulesetAccess.logwatch_rules_all(
        host_name=host_name, plugin=check_plugin_logwatch, logfile=item
    )
    yield from check_logwatch(
        item,
        rules_params,
        {k: v for k, v in section.items() if v is not None},
        host_name,
    )


def check_logwatch(
    item: str,
    params: Sequence[logwatch.ParameterLogwatchRules],
    section: ClusterSection,
    host_name: str,
) -> CheckResult:
    yield from logwatch.check_errors(section)
    yield from logwatch.check_unreadable_files(
        logwatch.get_unreadable_logfiles(item, section), State.CRIT
    )

    seen_batches = logwatch.update_seen_batches(get_value_store(), section, [item])

    loglines: list[str] = sum(
        (
            logwatch.extract_unseen_lines(node_data.logfiles[item]["lines"], seen_batches)
            for node_data in section.values()
            if item in node_data.logfiles
        ),
        [],
    )

    yield from check_logwatch_generic(
        item=item,
        reclassify_parameters=logwatch.compile_reclassify_params(params),
        loglines=loglines,
        found=item in logwatch.discoverable_items(*section.values()),
        max_filesize=_LOGWATCH_MAX_FILESIZE,
        host_name=host_name,
    )


check_plugin_logwatch = CheckPlugin(
    name="logwatch",
    service_name="Log %s",
    discovery_function=discover_logwatch_single,
    discovery_ruleset_name="logwatch_groups",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={"grouping_patterns": []},
    check_function=check_logwatch_node,
    # watch out when implementing a check_ruleset:
    # There *are* already check parameters, they're just bypassing the official API.
    # Make sure to give the check ruleset a general name, so we can (maybe, someday)
    # incorporate those.
    check_default_parameters={
        # The next entry will be postprocessed by the backend.
        # Don't try this hack at home, we are trained professionals.
        "host_name": ("cmk_postprocessed", "host_name", None),
    },
    cluster_check_function=check_logwatch_cluster,
)

# .
#   .--logwatch.groups-----------------------------------------------------.
#   |              _                                                       |
#   |             | |_      ____ _ _ __ ___  _   _ _ __  ___               |
#   |             | \ \ /\ / / _` | '__/ _ \| | | | '_ \/ __|              |
#   |             | |\ V  V / (_| | | | (_) | |_| | |_) \__ \              |
#   |             |_| \_/\_(_)__, |_|  \___/ \__,_| .__/|___/              |
#   |                        |___/                |_|                      |
#   '----------------------------------------------------------------------'


def _instantiate_matched(match: Match, group_name: str, inclusion: str) -> tuple[str, str]:
    num_perc_s = group_name.count("%s")
    matches = [g or "" for g in match.groups()]

    if len(matches) < num_perc_s:
        raise RuntimeError(
            "Invalid entry in inventory_logwatch_groups: group name "
            "%r contains %d times '%%s', but regular expression "
            "%r contains only %d subexpression(s)."
            % (group_name, num_perc_s, inclusion, len(matches))
        )

    if not matches:
        return group_name, inclusion

    for num, group in enumerate(matches):
        inclusion = eval_regex.instantiate_regex_pattern_once(inclusion, group)
        group_name = group_name.replace("%%%d" % (num + 1), group)
    return group_name % tuple(matches[:num_perc_s]), inclusion


def _groups_of_logfile(
    group_patterns: Iterable[tuple[str, GroupingPattern]],
    filename: str,
) -> dict[str, set[GroupingPattern]]:
    found_these_groups: dict[str, set[GroupingPattern]] = {}
    for group_name, (inclusion, exclusion) in group_patterns:
        inclusion_is_regex = inclusion.startswith("~")
        exclusion_is_regex = exclusion.startswith("~")

        if inclusion_is_regex:
            match_ = re.match(inclusion[1:], filename)
            if match_:
                group_name, inclusion = _instantiate_matched(match_, group_name, inclusion)
            incl_match = bool(match_)
        else:
            incl_match = fnmatch.fnmatch(filename, inclusion)

        if exclusion_is_regex:
            excl_match = bool(re.match(exclusion[1:], filename))
        else:
            excl_match = fnmatch.fnmatch(filename, exclusion)

        # NOTE: exclusion wins.
        if incl_match and not excl_match:
            found_these_groups.setdefault(group_name, set())
            found_these_groups[group_name].add((inclusion, exclusion))

    return found_these_groups


def _match_group_patterns(
    logfile_name: str,
    inclusion: str,
    exclusion: str,
) -> bool:
    # NOTE: in the grouped sap and fileinfo checks, the *exclusion* pattern wins.
    inclusion_is_regex = inclusion.startswith("~")
    if inclusion_is_regex:
        incl_match = bool(re.match(inclusion[1:], logfile_name))
    else:
        incl_match = fnmatch.fnmatch(logfile_name, inclusion)
    if not incl_match:
        return False

    if exclusion.startswith("~"):
        return not re.match(exclusion[1:], logfile_name)
    return not fnmatch.fnmatch(logfile_name, exclusion)


def check_logwatch_groups_node(
    item: str,
    params: DiscoveredGroupParams,
    section: logwatch.Section,
) -> CheckResult:
    """fall back to the cluster case with node=None"""
    params_rules = logwatch.RulesetAccess.logwatch_rules_all(
        host_name=params["host_name"],
        plugin=check_plugin_logwatch_groups,
        logfile=item,
    )
    yield from check_logwatch_groups(item, params, params_rules, {None: section})


def check_logwatch_groups_cluster(
    item: str,
    params: DiscoveredGroupParams,
    section: Mapping[str, logwatch.Section | None],
) -> CheckResult:
    params_rules = logwatch.RulesetAccess.logwatch_rules_all(
        host_name=params["host_name"],
        plugin=check_plugin_logwatch_groups,
        logfile=item,
    )
    yield from check_logwatch_groups(
        item, params, params_rules, {k: v for k, v in section.items() if v is not None}
    )


def check_logwatch_groups(
    item: str,
    params: DiscoveredGroupParams,
    params_rules: Sequence[logwatch.ParameterLogwatchRules],
    section: ClusterSection,
) -> CheckResult:
    yield from logwatch.check_errors(section)

    value_store = get_value_store()
    matching_files = _get_matching_logfiles(set(params["group_patterns"]), section)
    seen_batches = logwatch.update_seen_batches(value_store, section, matching_files)

    loglines = [
        line
        # node name ignored (only used in regular logwatch check)
        for node_data in section.values()
        for logfile_name, item_data in node_data.logfiles.items()
        if logfile_name in matching_files
        for line in logwatch.extract_unseen_lines(item_data["lines"], seen_batches)
    ]

    yield from check_logwatch_generic(
        item=item,
        reclassify_parameters=logwatch.compile_reclassify_params(params_rules),
        loglines=loglines,
        found=True,
        max_filesize=_LOGWATCH_MAX_FILESIZE,
        host_name=params["host_name"],
    )


def _get_matching_logfiles(
    group_patterns: set[GroupingPattern], section: ClusterSection
) -> list[str]:
    return [
        logfile_name
        for node_data in section.values()
        for logfile_name in node_data.logfiles
        if any(
            _match_group_patterns(logfile_name, inclusion, exclusion)
            for inclusion, exclusion in group_patterns
        )
    ]


check_plugin_logwatch_groups = CheckPlugin(
    name="logwatch_groups",
    service_name="Log %s",
    sections=["logwatch"],
    discovery_function=discover_logwatch_groups,
    discovery_ruleset_name="logwatch_groups",
    discovery_ruleset_type=RuleSetType.ALL,
    discovery_default_parameters={"grouping_patterns": []},
    check_function=check_logwatch_groups_node,
    check_default_parameters={
        "group_patterns": [],
        "host_name": ("cmk_postprocessed", "host_name", None),
    },
    cluster_check_function=check_logwatch_groups_cluster,
)


# truncate a file near the specified offset while keeping lines intact
def truncate_by_line(file_path: Path, offset: int) -> None:
    with file_path.open("r+") as handle:
        handle.seek(offset)
        handle.readline()  # ensures we don't cut inside a line
        handle.truncate()


class LogwatchBlock:
    CHAR_TO_STATE = {"O": 0, "W": 1, "u": 1, "C": 2}
    STATE_TO_STR = {0: "OK", 1: "WARN"}

    def __init__(self, header: str, reclassify_parameters: logwatch.ReclassifyParameters) -> None:
        self._timestamp = header.strip("<>").rsplit(None, 1)[0]
        self.worst = -1
        self.lines: list = []
        self.saw_lines = False
        self.last_worst_line = ""
        self.states_counter: Counter[str] = Counter()  # lines with a certain state
        self._reclassify_parameters = reclassify_parameters

    def finalize(self):
        state_str = LogwatchBlock.STATE_TO_STR.get(self.worst, "CRIT")
        header = f"<<<{self._timestamp} {state_str}>>>\n"
        return [header] + self.lines

    def add_line(self, line, reclassify):
        self.saw_lines = True

        try:
            level, text = line.split(None, 1)
        except ValueError:
            level, text = line.strip(), ""

        if reclassify:
            level = logwatch.reclassify(self._reclassify_parameters, text, level)

        state_int = LogwatchBlock.CHAR_TO_STATE.get(level, -1)
        self.worst = max(state_int, self.worst)

        # Save the last worst line of this block
        if max(state_int, 0) == self.worst:
            self.last_worst_line = text

        # Count the number of lines by state
        if level != ".":
            self.states_counter[level] += 1

        if reclassify and level != "I":
            self.lines.append(f"{level} {text}\n")


class LogwatchBlockCollector:
    def __init__(self) -> None:
        self.worst = 0
        self.last_worst_line = ""
        self.saw_lines = False
        self._output_lines: list[str] = []
        self._states_counter: Counter[str] = Counter()

    @property
    def size(self) -> int:
        return sum(len(line.encode("utf-8")) for line in self._output_lines)

    def extend(self, blocks: Iterable[LogwatchBlock]) -> None:
        for block in blocks:
            self.add(block)

    def add(self, block: LogwatchBlock) -> None:
        self.saw_lines |= block.saw_lines

        if block.worst <= -1:
            return

        self._states_counter += block.states_counter

        self._output_lines.extend(block.finalize())
        if block.worst >= self.worst:
            self.worst = block.worst
            self.last_worst_line = block.last_worst_line

    def clear_lines(self) -> None:
        self._output_lines = []

    def get_lines(self) -> list[str]:
        return self._output_lines

    def get_count_info(self) -> str:
        expanded_levels = {"O": "OK", "W": "WARN", "u": "WARN", "C": "CRIT"}
        count_txt = (
            "%d %s" % (count, expanded_levels.get(level, "IGN"))
            for level, count in self._states_counter.items()
        )
        return "%s messages" % ", ".join(count_txt)


def _logmsg_file_path(item: str, host_name: str) -> Path:
    logmsg_dir = cmk.utils.paths.var_dir / "logwatch" / host_name
    logmsg_dir.mkdir(parents=True, exist_ok=True)
    return logmsg_dir / item.replace("/", "\\")


def check_logwatch_generic(
    *,
    item: str,
    reclassify_parameters: logwatch.ReclassifyParameters,
    loglines: Iterable[str],
    found: bool,
    max_filesize: int,
    host_name: str,
) -> CheckResult:
    logmsg_file_path = _logmsg_file_path(item, host_name)

    # Logfile (=item) section not found and no local file found. This usually
    # means, that the corresponding logfile also vanished on the target host.
    if not found and not logmsg_file_path.exists():
        yield Result(state=State.UNKNOWN, summary="log not present anymore")
        return

    block_collector = LogwatchBlockCollector()

    logmsg_file_exists = logmsg_file_path.exists()
    logmsg_file_handle = logmsg_file_path.open(
        "r+" if logmsg_file_exists else "w", encoding="utf-8"
    )

    pattern_hash = hashlib.sha256(repr(reclassify_parameters).encode()).hexdigest()
    if not logmsg_file_exists:
        output_size = 0
        reclassify = True
    else:  # parse cached log lines
        reclassify = _patterns_changed(logmsg_file_handle, pattern_hash)

        if not reclassify and _truncate_way_too_large_result(logmsg_file_path, max_filesize):
            yield _dropped_msg_result(max_filesize)
            return

        block_collector.extend(
            _extract_blocks(logmsg_file_handle, reclassify_parameters, reclassify)
        )

        if reclassify:
            output_size = block_collector.size
        else:
            output_size = logmsg_file_handle.tell()
            # when skipping reclassification, output lines contain only headers anyway
            block_collector.clear_lines()

    header = time.strftime("<<<%Y-%m-%d %H:%M:%S UNKNOWN>>>\n")
    output_size += len(header)

    # process new input lines - but only when there is some room left in the file
    block_collector.extend(
        _extract_blocks(
            [header, *loglines], reclassify_parameters, True, limit=max_filesize - output_size
        )
    )

    # when reclassifying, rewrite the whole file, otherwise append
    if reclassify and block_collector.get_lines():
        logmsg_file_handle.seek(0)
        logmsg_file_handle.truncate()
        logmsg_file_handle.write("[[[%s]]]\n" % pattern_hash)

    for line in block_collector.get_lines():
        logmsg_file_handle.write(line)
    # correct output size
    logmsg_file_handle.close()

    if not block_collector.saw_lines:
        logmsg_file_path.unlink(missing_ok=True)

    # if logfile has reached maximum size, abort with critical state
    if logmsg_file_path.exists() and logmsg_file_path.stat().st_size > max_filesize:
        yield _dropped_msg_result(max_filesize)
        return

    #
    # Render output
    #
    summary, details = "", None
    if block_collector.worst <= 0:
        block_collector.worst = 0
        summary = "No error messages"

    if block_collector.last_worst_line != "":
        summary = block_collector.get_count_info()
        summary += ' (Last worst: "%s")' % block_collector.last_worst_line

        if "\n" in summary.strip():
            summary, details = summary.split("\n", 1)

    yield Result(
        state=State(block_collector.worst),
        summary=summary,
        details=details,
    )


def _patterns_changed(file_handle: IO[str], current_pattern: str) -> bool:
    first_line = file_handle.readline().rstrip("\n")
    pref, pattern, suff = first_line[:3], first_line[3:-3], first_line[-3:]
    if (pref, suff) == ("[[[", "]]]"):
        return pattern != current_pattern
    file_handle.seek(0)
    return True


def _truncate_way_too_large_result(
    file_path: Path,
    max_filesize: int,
) -> bool:
    logfile_size = file_path.stat().st_size
    if logfile_size <= max_filesize:
        return False

    # early out: without reclassification the file won't shrink and if it is already at
    # the maximum size, all input is dropped anyway
    if logfile_size > max_filesize * 2:
        # if the file is far too large, truncate it
        truncate_by_line(file_path, max_filesize)
    return True


def _extract_blocks(
    lines: Iterable[str],
    reclassify_parameters: logwatch.ReclassifyParameters,
    reclassify: bool,
    *,
    limit: float = float("inf"),
) -> Iterable[LogwatchBlock]:
    """Extract logwatch blocks from the given lines.
    When limit is reached, stop processing further lines, but yield the current block so it can be
    written to file, triggering the file size limit.
    """
    current_block = None
    for line in lines:
        line = line.rstrip("\n")
        # Skip empty lines
        if not line:
            continue
        if line.startswith("<<<") and line.endswith(">>>"):
            if current_block is not None:
                yield current_block
            current_block = LogwatchBlock(line, reclassify_parameters)
        elif current_block is not None:
            current_block.add_line(line, reclassify)
            limit -= len(line.encode("utf-8"))
            if limit <= 0:
                yield current_block
                return

    if current_block is not None:
        yield current_block


def _dropped_msg_result(max_size: int) -> Result:
    return Result(
        state=State.CRIT,
        summary=(
            "Unacknowledged messages have exceeded max size, new messages are dropped "
            "(limit %s)" % render.filesize(max_size)
        ),
    )
