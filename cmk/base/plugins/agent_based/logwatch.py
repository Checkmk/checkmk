#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#########################################################################################
#                                                                                       #
#                                 !!   W A T C H   O U T   !!                           #
#                                                                                       #
#   The logwatch plugin is notorious for being an exception to just about every rule    #
#   or best practice that applies to check plugin development.                          #
#   It is highly discouraged to use this a an example!                                  #
#                                                                                       #
#########################################################################################

import fnmatch
import hashlib
import pathlib
import time
from typing import (
    Any,
    Counter,
    Dict,
    IO,
    Iterable,
    List,
    Literal,
    Mapping,
    Match,
    Optional,
    Sequence,
    Set,
    Tuple,
)

# for now, we shamelessly violate the API:
import cmk.utils.debug  # pylint: disable=cmk-module-layer-violation
import cmk.utils.paths  # pylint: disable=cmk-module-layer-violation

# from cmk.base.config import logwatch_rule will NOT work!
import cmk.base.config  # pylint: disable=cmk-module-layer-violation
from cmk.base.check_api import (  # pylint: disable=cmk-module-layer-violation
    host_name,
    service_extra_conf,
)

from .agent_based_api.v1 import get_value_store, regex, register, render, Result, Service
from .agent_based_api.v1 import State as state
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult
from .utils import eval_regex, logwatch

AllParams = Sequence[Mapping[str, Any]]

ClusterSection = Dict[Optional[str], logwatch.Section]

GroupingPattern = Tuple[str, str]
DiscoveredGroupParams = Mapping[Literal["group_patterns"], Iterable[GroupingPattern]]

_LOGWATCH_MAX_FILESIZE = 500000  # do not save more than 500k of messages
LOGWATCH_SERVICE_OUTPUT = "default"


def _get_discovery_groups(params: AllParams) -> Sequence[List[Tuple[str, GroupingPattern]]]:
    return [p["grouping_patterns"] for p in params if "grouping_patterns" in p]


def _compile_params(item: str) -> Dict[str, Any]:
    compiled_params: Dict[str, Any] = {"reclassify_patterns": []}

    for rule in service_extra_conf(host_name(), item, cmk.base.config.logwatch_rules):
        if isinstance(rule, dict):
            compiled_params["reclassify_patterns"].extend(rule["reclassify_patterns"])
            if "reclassify_states" in rule:
                # (mo) wondering during migration: doesn't this mean the last one wins?
                compiled_params["reclassify_states"] = rule["reclassify_states"]
        else:
            compiled_params["reclassify_patterns"].extend(rule)

    return compiled_params


def _is_cache_new(last_run: float, node: Optional[str]) -> bool:
    return (
        node is None or pathlib.Path(cmk.utils.paths.tcp_cache_dir, node).stat().st_mtime > last_run
    )


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
    params: AllParams,
    section: logwatch.Section,
) -> DiscoveryResult:
    not_forwarded_logs = logwatch.select_forwarded(
        logwatch.discoverable_items(section),
        logwatch.get_ec_rule_params(),
        invert=True,
    )
    inventory_groups = _get_discovery_groups(params)

    for logfile in not_forwarded_logs:
        if not any(
            _groups_of_logfile(group_patterns, logfile) for group_patterns in inventory_groups
        ):
            yield Service(item=logfile)


def discover_logwatch_groups(
    params: AllParams,
    section: logwatch.Section,
) -> DiscoveryResult:
    not_forwarded_logs = logwatch.select_forwarded(
        logwatch.discoverable_items(section),
        logwatch.get_ec_rule_params(),
        invert=True,
    )
    inventory_groups = _get_discovery_groups(params)
    inventory: Dict[str, Set[GroupingPattern]] = {}

    for logfile in not_forwarded_logs:
        for group_patterns in inventory_groups:
            newly_found = _groups_of_logfile(group_patterns, logfile)
            for group_name, pattern_set in newly_found.items():
                inventory.setdefault(group_name, set()).update(pattern_set)

    for group_name, patterns in inventory.items():
        yield Service(
            item=group_name,
            parameters={"group_patterns": sorted(patterns)},
        )


def check_logwatch_node(
    item: str,
    section: logwatch.Section,
) -> CheckResult:
    """fall back to the cluster case with node=None"""
    yield from check_logwatch(item, {None: section})


def check_logwatch(
    item: str,
    section: ClusterSection,
) -> CheckResult:
    yield from logwatch.check_errors(section)

    value_store = get_value_store()
    last_run = value_store.get("last_run", 0)
    value_store["last_run"] = time.time()

    loglines = []
    for node, node_data in section.items():
        item_data: logwatch.ItemData = node_data.logfiles.get(
            item, {"attr": "missing", "lines": []}
        )
        if _is_cache_new(last_run, node):
            loglines.extend(item_data["lines"])

    yield from check_logwatch_generic(
        item=item,
        patterns=_compile_params(item),
        loglines=loglines,
        found=item in logwatch.discoverable_items(*section.values()),
        max_filesize=_LOGWATCH_MAX_FILESIZE,
    )


def cluster_check_logwatch(
    item: str, section: Mapping[str, Optional[logwatch.Section]]
) -> CheckResult:
    yield from check_logwatch(item, {k: v for k, v in section.items() if v is not None})


register.check_plugin(
    name="logwatch",
    service_name="Log %s",
    discovery_function=discover_logwatch_single,
    discovery_ruleset_name="logwatch_groups",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters={},
    check_function=check_logwatch_node,
    # watch out when implementing a check_ruleset:
    # There *are* already check parameters, they're just bypassing the official API.
    # Make sure to give the check ruleset a general name, so we can (maybe, someday)
    # incorporate those.
    cluster_check_function=cluster_check_logwatch,
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


def _instantiate_matched(match: Match, group_name: str, inclusion: str) -> Tuple[str, str]:
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
    group_patterns: List[Tuple[str, GroupingPattern]],
    filename: str,
) -> Dict[str, Set[GroupingPattern]]:
    found_these_groups: Dict[str, Set[GroupingPattern]] = {}
    for group_name, (inclusion, exclusion) in group_patterns:
        inclusion_is_regex = inclusion.startswith("~")
        exclusion_is_regex = exclusion.startswith("~")

        if inclusion_is_regex:
            reg = regex(inclusion[1:])
            _match = reg.match(filename)
            if _match:
                group_name, inclusion = _instantiate_matched(_match, group_name, inclusion)
            incl_match = bool(_match)
        else:
            incl_match = fnmatch.fnmatch(filename, inclusion)

        if exclusion_is_regex:
            reg = regex(exclusion[1:])
            excl_match = bool(reg.match(filename))
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
        incl_match = bool(regex(inclusion[1:]).match(logfile_name))
    else:
        incl_match = fnmatch.fnmatch(logfile_name, inclusion)
    if not incl_match:
        return False

    if exclusion.startswith("~"):
        return not regex(exclusion[1:]).match(logfile_name)
    return not fnmatch.fnmatch(logfile_name, exclusion)


def check_logwatch_groups_node(
    item: str,
    params: DiscoveredGroupParams,
    section: logwatch.Section,
) -> CheckResult:
    """fall back to the cluster case with node=None"""
    yield from check_logwatch_groups(item, params, {None: section})


def check_logwatch_groups(
    item: str,
    params: DiscoveredGroupParams,
    section: ClusterSection,
) -> CheckResult:
    yield from logwatch.check_errors(section)

    group_patterns = set(params["group_patterns"])

    loglines = []
    # node name ignored (only used in regular logwatch check)
    for node_data in section.values():
        for logfile_name, item_data in node_data.logfiles.items():
            for inclusion, exclusion in group_patterns:
                if _match_group_patterns(logfile_name, inclusion, exclusion):
                    loglines.extend(item_data["lines"])
                break

    yield from check_logwatch_generic(
        item=item,
        patterns=_compile_params(item),
        loglines=loglines,
        found=True,
        max_filesize=_LOGWATCH_MAX_FILESIZE,
    )


def cluster_check_logwatch_groups(
    item: str,
    params: DiscoveredGroupParams,
    section: Mapping[str, Optional[logwatch.Section]],
) -> CheckResult:
    yield from check_logwatch_groups(
        item, params, {k: v for k, v in section.items() if v is not None}
    )


register.check_plugin(
    name="logwatch_groups",
    service_name="Log %s",
    sections=["logwatch"],
    discovery_function=discover_logwatch_groups,
    discovery_ruleset_name="logwatch_groups",
    discovery_ruleset_type=register.RuleSetType.ALL,
    discovery_default_parameters={},
    check_function=check_logwatch_groups_node,
    check_default_parameters={"group_patterns": []},
    cluster_check_function=cluster_check_logwatch_groups,
)


# truncate a file near the specified offset while keeping lines intact
def truncate_by_line(file_path: pathlib.Path, offset: int) -> None:
    with file_path.open("r+") as handle:
        handle.seek(offset)
        handle.readline()  # ensures we don't cut inside a line
        handle.truncate()


class LogwatchBlock:

    CHAR_TO_STATE = {"O": 0, "W": 1, "u": 1, "C": 2}
    STATE_TO_STR = {0: "OK", 1: "WARN"}

    def __init__(self, header, patterns):
        self._timestamp = header.strip("<>").rsplit(None, 1)[0]
        self.worst = -1
        self.lines = []
        self.saw_lines = False
        self.last_worst_line = ""
        self.counts: Counter[int] = Counter()  # matches of a certain pattern
        self.states_counter: Counter[str] = Counter()  # lines with a certain state
        self._patterns = patterns or {}

    def finalize(self):
        state_str = LogwatchBlock.STATE_TO_STR.get(self.worst, "CRIT")
        header = "<<<%s %s>>>\n" % (self._timestamp, state_str)
        return [header] + self.lines

    def add_line(self, line, reclassify):
        self.saw_lines = True

        try:
            level, text = line.split(None, 1)
        except ValueError:
            level, text = line.strip(), ""

        if reclassify:
            level = logwatch.reclassify(self.counts, self._patterns, text, level)

        state_int = LogwatchBlock.CHAR_TO_STATE.get(level, -1)
        self.worst = max(state_int, self.worst)

        # Save the last worst line of this block
        if max(state_int, 0) == self.worst:
            self.last_worst_line = text

        # Count the number of lines by state
        if level != ".":
            self.states_counter[level] += 1

        if reclassify and level != "I":
            self.lines.append("%s %s\n" % (level, text))


class LogwatchBlockCollector:
    def __init__(self):
        self.worst = 0
        self.last_worst_line = ""
        self.saw_lines = False
        self._output_lines: List[str] = []
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

    def get_lines(self) -> List[str]:
        return self._output_lines

    def get_count_info(self) -> str:
        expanded_levels = {"O": "OK", "W": "WARN", "u": "WARN", "C": "CRIT"}
        count_txt = (
            "%d %s" % (count, expanded_levels.get(level, "IGN"))
            for level, count in self._states_counter.items()
        )
        return "%s messages" % ", ".join(count_txt)


def _logmsg_file_path(item: str) -> pathlib.Path:
    logmsg_dir = pathlib.Path(cmk.utils.paths.var_dir, "logwatch", host_name())
    logmsg_dir.mkdir(parents=True, exist_ok=True)
    return logmsg_dir / item.replace("/", "\\")


def check_logwatch_generic(
    *,
    item: str,
    patterns,
    loglines: Iterable[str],
    found: bool,
    max_filesize: int,
) -> CheckResult:
    logmsg_file_path = _logmsg_file_path(item)

    # Logfile (=item) section not found and no local file found. This usually
    # means, that the corresponding logfile also vanished on the target host.
    if not found and not logmsg_file_path.exists():
        yield Result(state=state.UNKNOWN, summary="log not present anymore")
        return

    block_collector = LogwatchBlockCollector()

    logmsg_file_exists = logmsg_file_path.exists()
    logmsg_file_handle = logmsg_file_path.open(
        "r+" if logmsg_file_exists else "w", encoding="utf-8"
    )

    # TODO: repr() of a dict may change.
    pattern_hash = hashlib.sha256(repr(patterns).encode()).hexdigest()
    if not logmsg_file_exists:
        output_size = 0
        reclassify = True
    else:  # parse cached log lines
        reclassify = _patterns_changed(logmsg_file_handle, pattern_hash)

        if not reclassify and _truncate_way_too_large_result(logmsg_file_path, max_filesize):
            yield _dropped_msg_result(max_filesize)
            return

        block_collector.extend(_extract_blocks(logmsg_file_handle, patterns, reclassify))

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
        _extract_blocks([header, *loglines], patterns, False, limit=max_filesize - output_size)
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

    if block_collector.worst <= 0:
        yield Result(state=state.OK, summary="No error messages")
        return

    info = block_collector.get_count_info()
    if LOGWATCH_SERVICE_OUTPUT == "default":
        info += ' (Last worst: "%s")' % block_collector.last_worst_line

    summary, details = info, None
    if "\n" in info.strip():
        summary, details = info.split("\n", 1)

    yield Result(
        state=state(block_collector.worst),
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
    file_path: pathlib.Path,
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
    patterns,
    reclassify: bool,
    *,
    limit=float("inf"),
) -> Iterable[LogwatchBlock]:
    current_block = None
    for line in lines:
        line = line.rstrip("\n")
        # Skip empty lines
        if not line:
            continue
        if line.startswith("<<<") and line.endswith(">>>"):
            if current_block is not None:
                yield current_block
            current_block = LogwatchBlock(line, patterns)
        elif current_block is not None:
            current_block.add_line(line, reclassify)
            limit -= len(line.encode("utf-8"))
            if limit <= 0:
                return

    if current_block is not None:
        yield current_block


def _dropped_msg_result(max_size: int) -> Result:
    return Result(
        state=state.CRIT,
        summary=(
            "Unacknowledged messages have exceeded max size, new messages are dropped "
            "(limit %s)" % render.filesize(max_size)
        ),
    )
