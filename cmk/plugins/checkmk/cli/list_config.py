#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk" commands that list parts of the configuration.

--list-hosts, --list-tag and --list-checks.
"""

import dataclasses
import enum
import itertools
import sys
from collections.abc import Iterable, Mapping, Sequence
from contextlib import suppress

import cmk.ccc.debug
from cmk.base import config
from cmk.base.config import ConfigCache
from cmk.base.modes.check_mk import load_checks
from cmk.ccc import tty
from cmk.ccc.hostaddress import HostName, Hosts
from cmk.checkengine.plugin_backend import (
    filter_relevant_raw_sections,
)
from cmk.checkengine.plugins import (
    AgentSectionPlugin,
    CheckPlugin,
    SNMPSectionPlugin,
)
from cmk.cli.engine.modes import (
    write_stdout,
)
from cmk.cli.internal import Args, CLICommand, CLIOption, GlobalOptions, Options
from cmk.discover_plugins import discover_families, PluginGroup
from cmk.ruleset_matcher.tags import HostTags, TagID
from cmk.ruleset_matcher.tuple_rulesets import hosttags_match_taglist
from cmk.server_side_calls_backend import (
    load_active_checks,
)


# TODO: Does not care about internal group "check_mk"
def _list_all_hosts(
    config_cache: ConfigCache,
    hosts_config: Hosts,
    core_objects_config: config.CoreObjectsConfig,
    hostgroups: Sequence[str],
    options: Mapping[str, object],
) -> list[HostName]:
    hostnames: Iterable[HostName]

    all_sites = options.get("all-sites")
    offline = "include-offline" in options

    if all_sites:
        hostnames = filter(
            lambda hn: offline or config_cache.is_online(hn),
            itertools.chain(hosts_config.hosts, hosts_config.clusters, hosts_config.shadow_hosts),
        )
    else:
        hostnames = filter(
            lambda hn: config_cache.is_active(hn) and (offline or config_cache.is_online(hn)),
            itertools.chain(hosts_config.hosts, hosts_config.clusters),
        )

    hostnames = sorted(set(hostnames))
    if not hostgroups:
        return hostnames

    hostlist = []
    for hn in hostnames:
        for hg in core_objects_config.hostgroups(hn):
            if hg in hostgroups:
                hostlist.append(hn)
                break

    return hostlist


def _mode_list_hosts(
    _app: object, _global_options: GlobalOptions, options: Options, args: Args
) -> int:
    loading_result = config.load()
    config_cache = loading_result.config_cache
    core_objects_config = config.CoreObjectsConfig(
        loading_result.loaded_config,
        config_cache.ruleset_matcher,
        config_cache.label_manager,
    )
    hosts = _list_all_hosts(
        config_cache,
        loading_result.hosts_config,
        core_objects_config,
        args,
        options,
    )
    with suppress(IOError):
        sys.stdout.write("\n".join(hosts) + "\n")
        sys.stdout.flush()
    return 0


cli_command_list_hosts = CLICommand(
    long_option="list-hosts",
    short_option="l",
    handler_function=_mode_list_hosts,
    argument=True,
    argument_descr="G1 G2...",
    argument_optional=True,
    sub_options=[
        CLIOption(
            long_option="all-sites",
            short_help="Include hosts of foreign sites",
        ),
        CLIOption(
            long_option="include-offline",
            short_help="Include offline hosts",
        ),
    ],
    short_help="Print list of all hosts or members of host groups",
    long_help=[
        (
            "Called without argument lists all hosts. You may "
            "specify one or more host groups to restrict the output to hosts "
            "that are in at least one of those groups."
        ),
    ],
)


def _list_all_hosts_with_tags(
    tags: Sequence[TagID],
    config_cache: ConfigCache,
    hosts_config: Hosts,
    host_tags: HostTags,
) -> Sequence[HostName]:

    if "offline" in tags:
        hostnames = filter(
            lambda hn: config_cache.is_active(hn) and config_cache.is_offline(hn),
            itertools.chain(hosts_config.hosts, hosts_config.clusters),
        )
    else:
        hostnames = filter(
            lambda hn: config_cache.is_active(hn) and config_cache.is_online(hn),
            itertools.chain(hosts_config.hosts, hosts_config.clusters),
        )

    hosts = []
    for h in set(hostnames):
        if hosttags_match_taglist(host_tags.tag_list(h), tags):
            hosts.append(h)
    return hosts


def _mode_list_tag(
    _app: object, _global_options: GlobalOptions, _options: Options, args: Args
) -> int:
    loading_result = config.load()
    hosts = _list_all_hosts_with_tags(
        tuple(TagID(_) for _ in args),
        loading_result.config_cache,
        loading_result.hosts_config,
        loading_result.host_tags,
    )
    write_stdout("\n".join(sorted(hosts)))
    if hosts:
        write_stdout("\n")
    return 0


cli_command_list_tag = CLICommand(
    long_option="list-tag",
    handler_function=_mode_list_tag,
    argument=True,
    argument_descr="TAG1 TAG2...",
    argument_optional=True,
    short_help="List hosts having certain tags",
    long_help=["Prints all hosts that have all of the specified tags at once."],
)


class _DSType(enum.Enum):
    ACTIVE = enum.auto()
    SNMP = enum.auto()
    AGENT = enum.auto()
    AGENT_SNMP = enum.auto()


@dataclasses.dataclass(frozen=True)
class _TableRow:
    name: str
    ds_type: _DSType
    title: str

    def render_tty(self) -> str:
        return f"{self._render_name()}{self._render_ds_type()}{self._render_title()}"

    def _render_name(self) -> str:
        return f"{tty.bold}{self.name!s:44}"

    def _render_ds_type(self) -> str:
        match self.ds_type:
            case _DSType.ACTIVE:
                return f"{tty.blue}{'active':10}"
            case _DSType.SNMP:
                return f"{tty.magenta}{'snmp':10}"
            case _DSType.AGENT:
                return f"{tty.yellow}{'agent':10}"
            case _DSType.AGENT_SNMP:
                return f"{tty.yellow}agent{tty.white}/{tty.magenta}snmp"

    def _render_title(self) -> str:
        return f"{tty.normal}{self.title}"


def _get_ds_type(
    check: CheckPlugin, sections: Iterable[AgentSectionPlugin | SNMPSectionPlugin]
) -> _DSType:
    raw_section_is_snmp = {
        isinstance(s, SNMPSectionPlugin)
        for s in filter_relevant_raw_sections(
            consumers=(check,),
            sections=sections,
        ).values()
    }
    if all(raw_section_is_snmp):
        return _DSType.SNMP
    if not any(raw_section_is_snmp):
        return _DSType.AGENT
    return _DSType.AGENT_SNMP


def _mode_list_checks(
    _app: object, _global_options: GlobalOptions, _options: Options, _args: Args
) -> int:
    from cmk.utils import man_pages

    plugins = load_checks()
    section_plugins: Iterable[AgentSectionPlugin | SNMPSectionPlugin] = [
        *plugins.agent_sections.values(),
        *plugins.snmp_sections.values(),
    ]

    all_check_manuals = {
        n: man_pages.parse_man_page(n, p)
        for n, p in man_pages.make_man_page_path_map(
            discover_families(raise_errors=cmk.ccc.debug.enabled()),
            PluginGroup.CHECKMAN.value,
        ).items()
    }

    def _get_title(plugin_name: str) -> str:
        try:
            return all_check_manuals[plugin_name].title
        except KeyError:
            return "(no man page present)"

    table = [
        *(
            _TableRow(
                name=(name := f"check_{p.name}"),
                ds_type=_DSType.ACTIVE,
                title=_get_title(name),
            )
            for p in load_active_checks(raise_errors=cmk.ccc.debug.enabled()).values()
        ),
        *(
            _TableRow(
                name=str(plugin.name),
                ds_type=_get_ds_type(plugin, section_plugins),
                title=_get_title(str(plugin.name)),
            )
            for plugin in plugins.check_plugins.values()
        ),
    ]

    for e in sorted(table, key=lambda e: e.name):
        write_stdout(f"{e.render_tty()}\n")
    return 0


cli_command_list_checks = CLICommand(
    long_option="list-checks",
    short_option="L",
    handler_function=_mode_list_checks,
    short_help="List all available Check_MK checks",
)
