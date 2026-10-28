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
from pathlib import Path

from cmk.base import config
from cmk.base.config import ConfigCache
from cmk.base.modes.check_mk import load_checks
from cmk.ccc import tty
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName, Hosts
from cmk.checkengine.plugin_backend import (
    filter_relevant_raw_sections,
)
from cmk.checkengine.plugins import (
    AgentSectionPlugin,
    CheckPlugin,
    SNMPSectionPlugin,
)
from cmk.cli.engine.commands import (
    write_stdout,
)
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Option as CLIOption
from cmk.cli.internal import Options
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
    _omd_root: Path, global_options: CLIGlobalOptions, options: Options, args: CLIArgs
) -> CLIExitCode:
    loading_result = config.load(validate_hosts=True, debug=global_options.debug)
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
    return CLIExitCode.SUCCESS


def _run_list_hosts(context: CLIContext, options: Options, args: CLIArgs) -> CLIExitCode:
    try:
        return _mode_list_hosts(context.omd_root, context.global_options, options, args)
    except MKGeneralException as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


cli_command_list_hosts = CLICommand(
    name="list_hosts",
    long="list-hosts",
    short="l",
    handler_function=_run_list_hosts,
    arguments=CLIArguments("G1 G2...", optional=True),
    sub_options=[
        CLIOption(
            long="all-sites",
            help="Include hosts of foreign sites",
        ),
        CLIOption(
            long="include-offline",
            help="Include offline hosts",
        ),
    ],
    help="Print list of all hosts or members of host groups",
    description=[
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
    _omd_root: Path, global_options: CLIGlobalOptions, _options: Options, args: CLIArgs
) -> CLIExitCode:
    loading_result = config.load(validate_hosts=True, debug=global_options.debug)
    hosts = _list_all_hosts_with_tags(
        tuple(TagID(_) for _ in args),
        loading_result.config_cache,
        loading_result.hosts_config,
        loading_result.host_tags,
    )
    write_stdout("\n".join(sorted(hosts)))
    if hosts:
        write_stdout("\n")
    return CLIExitCode.SUCCESS


def _run_list_tag(context: CLIContext, options: Options, args: CLIArgs) -> CLIExitCode:
    try:
        return _mode_list_tag(context.omd_root, context.global_options, options, args)
    except MKGeneralException as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


cli_command_list_tag = CLICommand(
    name="list_tag",
    long="list-tag",
    handler_function=_run_list_tag,
    arguments=CLIArguments("TAG1 TAG2...", optional=True),
    help="List hosts having certain tags",
    description=["Prints all hosts that have all of the specified tags at once."],
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
    _omd_root: Path, global_options: CLIGlobalOptions, _options: Options, _args: CLIArgs
) -> CLIExitCode:
    from cmk.utils import man_pages

    plugins = load_checks(debug=global_options.debug)
    section_plugins: Iterable[AgentSectionPlugin | SNMPSectionPlugin] = [
        *plugins.agent_sections.values(),
        *plugins.snmp_sections.values(),
    ]

    all_check_manuals = {
        n: man_pages.parse_man_page(n, p, debug=global_options.debug)
        for n, p in man_pages.make_man_page_path_map(
            discover_families(raise_errors=global_options.debug),
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
            for p in load_active_checks(raise_errors=global_options.debug).values()
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
    return CLIExitCode.SUCCESS


def _run_list_checks(context: CLIContext, options: Options, args: CLIArgs) -> CLIExitCode:
    try:
        return _mode_list_checks(context.omd_root, context.global_options, options, args)
    except MKGeneralException as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


cli_command_list_checks = CLICommand(
    name="list_checks",
    long="list-checks",
    short="L",
    handler_function=_run_list_checks,
    help="List all available Check_MK checks",
)
