#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, TypedDict

from six import ensure_str

import cmk.utils.debug
import cmk.utils.log as log
import cmk.utils.paths
import cmk.utils.piggyback as piggyback
import cmk.utils.store as store
import cmk.utils.tty as tty
import cmk.utils.version as cmk_version
from cmk.utils.check_utils import maincheckify
from cmk.utils.diagnostics import (
    DiagnosticsModesParameters,
    OPT_CHECKMK_CONFIG_FILES,
    OPT_CHECKMK_OVERVIEW,
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
)
from cmk.utils.exceptions import MKBailOut, MKGeneralException
from cmk.utils.log import console
from cmk.utils.type_defs import (
    CheckPluginName,
    HostAddress,
    HostgroupName,
    HostName,
    TagValue,
)

import cmk.snmplib.snmp_modes as snmp_modes

import cmk.fetchers.factory as snmp_factory

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.backup
import cmk.base.check_utils
import cmk.base.config as config
import cmk.base.core
import cmk.base.core_nagios
import cmk.base.checkers as checkers
import cmk.base.diagnostics
import cmk.base.discovery as discovery
import cmk.base.dump_host
import cmk.base.inventory as inventory
import cmk.base.ip_lookup as ip_lookup
import cmk.base.localize
import cmk.base.obsolete_output as out
import cmk.base.packaging
import cmk.base.parent_scan
import cmk.base.profiling as profiling
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.core_factory import create_core
from cmk.base.modes import keepalive_option, Mode, modes, Option

# TODO: Investigate all modes and try to find out whether or not we can
# set needs_checks=False for them. This would save a lot of IO/time for
# these modes.

#.
#   .--General options-----------------------------------------------------.
#   |       ____                           _               _               |
#   |      / ___| ___ _ __   ___ _ __ __ _| |   ___  _ __ | |_ ___         |
#   |     | |  _ / _ \ '_ \ / _ \ '__/ _` | |  / _ \| '_ \| __/ __|        |
#   |     | |_| |  __/ | | |  __/ | | (_| | | | (_) | |_) | |_\__ \_       |
#   |      \____|\___|_| |_|\___|_|  \__,_|_|  \___/| .__/ \__|___(_)      |
#   |                                               |_|                    |
#   +----------------------------------------------------------------------+
#   | The general options that are available for all Checkmk modes. Only  |
#   | add new general options in case they are really affecting basic      |
#   | things and used by the most of the modes.                            |
#   '----------------------------------------------------------------------'

_verbosity = 0


def option_verbosity() -> None:
    global _verbosity
    _verbosity += 1
    log.logger.setLevel(log.verbosity_to_log_level(_verbosity))


modes.register_general_option(
    Option(
        long_option="verbose",
        short_option="v",
        short_help="Enable verbose output (Use twice for more)",
        handler_function=option_verbosity,
    ))

_verbosity = 0


def option_cache() -> None:
    checkers.set_cache_opts(use_caches=True)


modes.register_general_option(
    Option(
        long_option="cache",
        short_help="Read info from data source cache files when existant, even when it "
        "is outdated. Only contact the data sources when the cache file "
        "is absent",
        handler_function=option_cache,
    ))


def option_no_cache() -> None:
    cmk.base.checkers.FileCacheFactory.disabled = True


modes.register_general_option(
    Option(
        long_option="no-cache",
        short_help="Never use cached information",
        handler_function=option_no_cache,
    ))


def option_no_tcp() -> None:
    checkers.tcp.TCPSource.use_only_cache = True


# TODO: Check whether or not this is used only for -I as written in the help.
# Does it affect inventory/checking too?
modes.register_general_option(
    Option(
        long_option="no-tcp",
        short_help="For -I: Only use cache files. Skip hosts without cache files.",
        handler_function=option_no_tcp,
    ))


def option_usewalk() -> None:
    snmp_factory.force_stored_walks()
    ip_lookup.enforce_localhost()


modes.register_general_option(
    Option(
        long_option="usewalk",
        short_help="Use snmpwalk stored with --snmpwalk",
        handler_function=option_usewalk,
    ))


def option_debug() -> None:
    cmk.utils.debug.enable()


modes.register_general_option(
    Option(
        long_option="debug",
        short_help="Let most Python exceptions raise through",
        handler_function=option_debug,
    ))


def option_profile() -> None:
    profiling.enable()


modes.register_general_option(
    Option(
        long_option="profile",
        short_help="Enable profiling mode",
        handler_function=option_profile,
    ))


def option_fake_dns(a: str) -> None:
    ip_lookup.enforce_fake_dns(a)


modes.register_general_option(
    Option(
        long_option="fake-dns",
        short_help="Fake IP addresses of all hosts to be IP. This "
        "prevents DNS lookups.",
        handler_function=option_fake_dns,
        argument=True,
        argument_descr="IP",
    ))

#.
#.
#   .--list-hosts----------------------------------------------------------.
#   |              _ _     _        _               _                      |
#   |             | (_)___| |_     | |__   ___  ___| |_ ___                |
#   |             | | / __| __|____| '_ \ / _ \/ __| __/ __|               |
#   |             | | \__ \ ||_____| | | | (_) \__ \ |_\__ \               |
#   |             |_|_|___/\__|    |_| |_|\___/|___/\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_list_hosts(options: Dict, args: List[str]) -> None:
    hosts = _list_all_hosts(args, options)
    out.output("\n".join(hosts))
    if hosts:
        out.output("\n")


# TODO: Does not care about internal group "check_mk"
def _list_all_hosts(hostgroups: List[HostgroupName], options: Dict) -> List[HostName]:
    config_cache = config.get_config_cache()

    hostnames = set()

    if options.get("all-sites"):
        hostnames.update(config_cache.all_configured_hosts())  # Return all hosts, including offline
        if "include-offline" not in options:
            hostnames -= config.all_configured_offline_hosts()
    else:
        hostnames.update(config_cache.all_active_hosts())
        if "include-offline" in options:
            hostnames.update(config.all_offline_hosts())

    if not hostgroups:
        return sorted(hostnames)

    hostlist = []
    for hn in hostnames:
        host_config = config_cache.get_host_config(hn)
        for hg in host_config.hostgroups:
            if hg in hostgroups:
                hostlist.append(hn)
                break

    return sorted(hostlist)


modes.register(
    Mode(long_option="list-hosts",
         short_option="l",
         handler_function=mode_list_hosts,
         argument=True,
         argument_descr="G1 G2...",
         argument_optional=True,
         short_help="Print list of all hosts or members of host groups",
         long_help=[
             "Called without argument lists all hosts. You may "
             "specify one or more host groups to restrict the output to hosts "
             "that are in at least one of those groups.",
         ],
         sub_options=[
             Option(
                 long_option="all-sites",
                 short_help="Include hosts of foreign sites",
             ),
             Option(
                 long_option="include-offline",
                 short_help="Include offline hosts",
             ),
         ]))

#.
#   .--list-tag------------------------------------------------------------.
#   |                   _ _     _        _                                 |
#   |                  | (_)___| |_     | |_ __ _  __ _                    |
#   |                  | | / __| __|____| __/ _` |/ _` |                   |
#   |                  | | \__ \ ||_____| || (_| | (_| |                   |
#   |                  |_|_|___/\__|     \__\__,_|\__, |                   |
#   |                                             |___/                    |
#   '----------------------------------------------------------------------'


def mode_list_tag(args: List[str]) -> None:
    hosts = _list_all_hosts_with_tags(args)
    out.output("\n".join(sorted(hosts)))
    if hosts:
        out.output("\n")


def _list_all_hosts_with_tags(tags: List[TagValue]) -> List[HostName]:
    config_cache = config.get_config_cache()
    hosts = []

    if "offline" in tags:
        hostlist = config.all_offline_hosts()
    else:
        hostlist = config_cache.all_active_hosts()

    config_cache = config.get_config_cache()
    for h in hostlist:
        if config.hosttags_match_taglist(config_cache.tag_list_of_host(h), tags):
            hosts.append(h)
    return hosts


modes.register(
    Mode(long_option="list-tag",
         handler_function=mode_list_tag,
         argument=True,
         argument_descr="TAG1 TAG2...",
         argument_optional=True,
         short_help="List hosts having certain tags",
         long_help=["Prints all hosts that have all of the specified tags at once."]))

#.
#   .--list-checks---------------------------------------------------------.
#   |           _ _     _             _               _                    |
#   |          | (_)___| |_       ___| |__   ___  ___| | _____             |
#   |          | | / __| __|____ / __| '_ \ / _ \/ __| |/ / __|            |
#   |          | | \__ \ ||_____| (__| | | |  __/ (__|   <\__ \            |
#   |          |_|_|___/\__|     \___|_| |_|\___|\___|_|\_\___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_list_checks() -> None:
    import cmk.utils.man_pages as man_pages  # pylint: disable=import-outside-toplevel
    all_check_manuals = {maincheckify(n): k for n, k in man_pages.all_man_pages().items()}

    registered_checks = [(p.name, p) for p in agent_based_register.iter_all_check_plugins()]
    active_checks = [("check_%s" % name, entry) for name, entry in config.active_check_info.items()]
    # TODO clean mixed typed list up:
    all_checks = registered_checks + active_checks  # type: ignore[operator]

    for plugin_name, check in sorted(all_checks, key=lambda x: str(x[0])):
        if not isinstance(check, CheckPlugin):  # active check
            what = 'active'
            ty_color = tty.blue
        else:
            if plugin_name in config.legacy_check_plugin_names:
                what = 'auto migrated'
                ty_color = tty.magenta
            else:
                what = ''
                ty_color = tty.yellow

        title = _get_check_plugin_title(str(plugin_name), all_check_manuals)

        out.output((tty.bold + "%-44s" + tty.normal + ty_color + " %-13s " + tty.normal + "%s\n") %
                   (plugin_name, what, title))


def _get_check_plugin_title(
    check_plugin_name: str,
    all_man_pages: Dict[str, str],
) -> str:

    man_filename = all_man_pages.get(check_plugin_name)
    if man_filename is None:
        return "(no man page present)"

    try:
        return cmk.utils.man_pages.get_title_from_man_page(Path(man_filename))
    except MKGeneralException:
        return "(failed to read man page)"


modes.register(
    Mode(
        long_option="list-checks",
        short_option="L",
        handler_function=mode_list_checks,
        needs_config=False,
        short_help="List all available Check_MK checks",
    ))

#.
#   .--dump-agent----------------------------------------------------------.
#   |        _                                                    _        |
#   |     __| |_   _ _ __ ___  _ __         __ _  __ _  ___ _ __ | |_      |
#   |    / _` | | | | '_ ` _ \| '_ \ _____ / _` |/ _` |/ _ \ '_ \| __|     |
#   |   | (_| | |_| | | | | | | |_) |_____| (_| | (_| |  __/ | | | |_      |
#   |    \__,_|\__,_|_| |_| |_| .__/       \__,_|\__, |\___|_| |_|\__|     |
#   |                         |_|                |___/                     |
#   '----------------------------------------------------------------------'


def mode_dump_agent(hostname: HostName) -> None:
    try:
        config_cache = config.get_config_cache()
        host_config = config_cache.get_host_config(hostname)

        if host_config.is_cluster:
            raise MKBailOut("Can not be used with cluster hosts")

        ipaddress = ip_lookup.lookup_ip_address(host_config)

        output = []
        # Show errors of problematic data sources
        has_errors = False
        mode = checkers.Mode.CHECKING
        for source in checkers.make_sources(
                host_config,
                ipaddress,
                mode=mode,
        ):
            source.file_cache_max_age = config.check_max_cachefile_age
            if not isinstance(source, checkers.agent.AgentSource):
                continue

            raw_data = source.fetch()
            host_sections = source.parse(raw_data)
            source_state, source_output, _source_perfdata = source.summarize(host_sections)
            if source_state != 0:
                console.error(
                    "ERROR [%s]: %s\n",
                    source.id,
                    ensure_str(source_output),
                )
                has_errors = True
            if raw_data.is_ok():
                assert raw_data.ok is not None
                output.append(raw_data.ok)

        out.output(ensure_str(b"".join(output), errors="surrogateescape"))
        if has_errors:
            sys.exit(1)
    except Exception as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKBailOut("Unhandled exception: %s" % e)


modes.register(
    Mode(long_option="dump-agent",
         short_option="d",
         handler_function=mode_dump_agent,
         argument=True,
         argument_descr="HOSTNAME|ADDRESS",
         short_help="Show raw information from agent",
         long_help=[
             "Shows the raw information received from the given host. For regular "
             "hosts it shows the agent output plus possible piggyback information. "
             "Does not work on clusters but only on real hosts. "
         ]))

#.
#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'


def mode_dump_hosts(hostlist: List[HostName]) -> None:
    config_cache = config.get_config_cache()
    if not hostlist:
        hostlist = sorted(config_cache.all_active_hosts())

    for hostname in hostlist:
        cmk.base.dump_host.dump_host(hostname)


modes.register(
    Mode(long_option="dump",
         short_option="D",
         handler_function=mode_dump_hosts,
         argument=True,
         argument_descr="H1 H2...",
         argument_optional=True,
         short_help="Dump info about all or some hosts",
         long_help=[
             "Dumps out the complete configuration and information "
             "about one, several or all hosts. It shows all services, hostgroups, "
             "contacts and other information about that host.",
         ]))

#.
#   .--paths---------------------------------------------------------------.
#   |                                  _   _                               |
#   |                      _ __   __ _| |_| |__  ___                       |
#   |                     | '_ \ / _` | __| '_ \/ __|                      |
#   |                     | |_) | (_| | |_| | | \__ \                      |
#   |                     | .__/ \__,_|\__|_| |_|___/                      |
#   |                     |_|                                              |
#   '----------------------------------------------------------------------'


def mode_paths() -> None:
    inst = 1
    conf = 2
    data = 3
    pipe = 4
    local = 5
    directory = 1
    fil = 2

    paths = [
        (cmk.utils.paths.modules_dir, directory, inst, "Main components of check_mk"),
        (cmk.utils.paths.checks_dir, directory, inst, "Checks"),
        (str(cmk.utils.paths.notifications_dir), directory, inst, "Notification scripts"),
        (cmk.utils.paths.inventory_dir, directory, inst, "Inventory plugins"),
        (cmk.utils.paths.agents_dir, directory, inst, "Agents for operating systems"),
        (str(cmk.utils.paths.doc_dir), directory, inst, "Documentation files"),
        (cmk.utils.paths.web_dir, directory, inst, "Check_MK's web pages"),
        (cmk.utils.paths.check_manpages_dir, directory, inst, "Check manpages (for check_mk -M)"),
        (cmk.utils.paths.lib_dir, directory, inst, "Binary plugins (architecture specific)"),
        (str(cmk.utils.paths.pnp_templates_dir), directory, inst, "Templates for PNP4Nagios"),
    ]
    if config.monitoring_core == "nagios":
        paths += [
            (cmk.utils.paths.nagios_startscript, fil, inst, "Startscript for Nagios daemon"),
            (cmk.utils.paths.nagios_binary, fil, inst, "Path to Nagios executable"),
            (cmk.utils.paths.nagios_config_file, fil, conf, "Main configuration file of Nagios"),
            (cmk.utils.paths.nagios_conf_dir, directory, conf,
             "Directory where Nagios reads all *.cfg files"),
            (cmk.utils.paths.nagios_objects_file, fil, data,
             "File into which Nagios configuration is written"),
            (cmk.utils.paths.nagios_status_file, fil, data, "Path to Nagios status.dat"),
            (cmk.utils.paths.nagios_command_pipe_path, fil, pipe, "Nagios' command pipe"),
            (cmk.utils.paths.check_result_path, fil, pipe, "Nagios' check results directory"),
        ]

    paths += [
        (cmk.utils.paths.default_config_dir, directory, conf, "Directory that contains main.mk"),
        (cmk.utils.paths.check_mk_config_dir, directory, conf,
         "Directory containing further *.mk files"),
        (cmk.utils.paths.apache_config_dir, directory, conf,
         "Directory where Apache reads all config files"),
        (cmk.utils.paths.htpasswd_file, fil, conf, "Users/Passwords for HTTP basic authentication"),
        (cmk.utils.paths.var_dir, directory, data, "Base working directory for variable data"),
        (cmk.utils.paths.autochecks_dir, directory, data, "Checks found by inventory"),
        (cmk.utils.paths.precompiled_hostchecks_dir, directory, data, "Precompiled host checks"),
        (cmk.utils.paths.snmpwalks_dir, directory, data, "Stored snmpwalks (output of --snmpwalk)"),
        (cmk.utils.paths.counters_dir, directory, data, "Current state of performance counters"),
        (cmk.utils.paths.tcp_cache_dir, directory, data, "Cached output from agents"),
        (cmk.utils.paths.logwatch_dir, directory, data,
         "Unacknowledged logfiles of logwatch extension"),
        (cmk.utils.paths.livestatus_unix_socket, fil, pipe,
         "Socket of Check_MK's livestatus module"),
        (str(cmk.utils.paths.local_checks_dir), directory, local, "Locally installed checks"),
        (str(cmk.utils.paths.local_notifications_dir), directory, local,
         "Locally installed notification scripts"),
        (str(cmk.utils.paths.local_inventory_dir), directory, local,
         "Locally installed inventory plugins"),
        (str(cmk.utils.paths.local_check_manpages_dir), directory, local,
         "Locally installed check man pages"),
        (str(cmk.utils.paths.local_agents_dir), directory, local,
         "Locally installed agents and plugins"),
        (str(cmk.utils.paths.local_web_dir), directory, local,
         "Locally installed Multisite addons"),
        (str(cmk.utils.paths.local_pnp_templates_dir), directory, local,
         "Locally installed PNP templates"),
        (str(cmk.utils.paths.local_doc_dir), directory, local, "Locally installed documentation"),
        (str(cmk.utils.paths.local_locale_dir), directory, local,
         "Locally installed localizations"),
    ]

    def show_paths(title: str, t: int) -> None:
        if t != inst:
            out.output("\n")
        out.output(tty.bold + title + tty.normal + "\n")
        for path, filedir, typp, descr in paths:
            if typp == t:
                if filedir == directory:
                    path += "/"
                out.output("  %-47s: %s%s%s\n" % (descr, tty.bold + tty.blue, path, tty.normal))

    for title, t in [
        ("Files copied or created during installation", inst),
        ("Configuration files edited by you", conf),
        ("Data created by Nagios/Check_MK at runtime", data),
        ("Sockets and pipes", pipe),
        ("Locally installed addons", local),
    ]:
        show_paths(title, t)


modes.register(
    Mode(
        long_option="paths",
        handler_function=mode_paths,
        needs_config=False,
        short_help="List all pathnames and directories",
    ))

#.
#   .--backup/restore------------------------------------------------------.
#   |      _                _                  __             _            |
#   |     | |__   __ _  ___| | ___   _ _ __   / / __ ___  ___| |_          |
#   |     | '_ \ / _` |/ __| |/ / | | | '_ \ / / '__/ _ \/ __| __|         |
#   |     | |_) | (_| | (__|   <| |_| | |_) / /| | |  __/\__ \ |_ _        |
#   |     |_.__/ \__,_|\___|_|\_\\__,_| .__/_/ |_|  \___||___/\__(_)       |
#   |                                 |_|                                  |
#   '----------------------------------------------------------------------'


def mode_backup(tarname: str) -> None:
    cmk.base.backup.do_backup(tarname)


modes.register(
    Mode(
        long_option="backup",
        handler_function=mode_backup,
        argument=True,
        argument_descr="BACKUPFILE.tar.gz",
        short_help="make backup of configuration and data",
        long_help=[
            "Saves all configuration and runtime data to a gzip "
            "compressed tar file to the path specified as argument.",
        ],
    ))


def mode_restore(tarname: str) -> None:
    cmk.base.backup.do_restore(tarname)


modes.register(
    Mode(
        long_option="restore",
        handler_function=mode_restore,
        argument=True,
        argument_descr="BACKUPFILE.tar.gz",
        short_help="restore configuration and data",
        long_help=[
            "*Erases* the current configuration and data and replaces "
            "it with that from the backup file."
        ],
    ))

#.
#   .--package-------------------------------------------------------------.
#   |                                 _                                    |
#   |                _ __   __ _  ___| | ____ _  __ _  ___                 |
#   |               | '_ \ / _` |/ __| |/ / _` |/ _` |/ _ \                |
#   |               | |_) | (_| | (__|   < (_| | (_| |  __/                |
#   |               | .__/ \__,_|\___|_|\_\__,_|\__, |\___|                |
#   |               |_|                         |___/                      |
#   '----------------------------------------------------------------------'


def mode_packaging(args: List[str]) -> None:
    cmk.base.packaging.do_packaging(args)


modes.register(
    Mode(
        long_option="package",
        short_option="P",
        handler_function=mode_packaging,
        argument=True,
        argument_descr="COMMAND",
        argument_optional=True,
        short_help="Do package operations",
        long_help=[
            "Brings you into packager mode. Packages are "
            "used to ship inofficial extensions of Check_MK. Call without "
            "arguments for a help on packaging."
        ],
        needs_config=False,
        needs_checks=False,
    ))

#.
#   .--localize------------------------------------------------------------.
#   |                    _                 _ _                             |
#   |                   | | ___   ___ __ _| (_)_______                     |
#   |                   | |/ _ \ / __/ _` | | |_  / _ \                    |
#   |                   | | (_) | (_| (_| | | |/ /  __/                    |
#   |                   |_|\___/ \___\__,_|_|_/___\___|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_localize(args: List[str]) -> None:
    cmk.base.localize.do_localize(args)


modes.register(
    Mode(
        long_option="localize",
        handler_function=mode_localize,
        needs_config=False,
        needs_checks=False,
        argument=True,
        argument_descr="COMMAND",
        argument_optional=True,
        short_help="Do localization operations",
        long_help=[
            "Brings you into localization mode. You can create "
            "and/or improve the localization of Check_MKs GUI. "
            "Call without arguments for a help on localization."
        ],
    ))

#.
#   .--config-check--------------------------------------------------------.
#   |                      __ _                  _               _         |
#   |      ___ ___  _ __  / _(_) __ _        ___| |__   ___  ___| | __     |
#   |     / __/ _ \| '_ \| |_| |/ _` |_____ / __| '_ \ / _ \/ __| |/ /     |
#   |    | (_| (_) | | | |  _| | (_| |_____| (__| | | |  __/ (__|   <      |
#   |     \___\___/|_| |_|_| |_|\__, |      \___|_| |_|\___|\___|_|\_\     |
#   |                           |___/                                      |
#   '----------------------------------------------------------------------'
# TODO: Can we remove this?

modes.register(
    Mode(
        long_option="config-check",
        short_option="X",
        handler_function=lambda: None,
        short_help="Check configuration for invalid vars",
    ))

#.
#   .--update-dns-cache----------------------------------------------------.
#   |                        _            _                                |
#   |        _   _ _ __   __| |        __| |_ __  ___        ___           |
#   |       | | | | '_ \ / _` | _____ / _` | '_ \/ __|_____ / __|          |
#   |       | |_| | |_) | (_| ||_____| (_| | | | \__ \_____| (__ _         |
#   |        \__,_| .__/ \__,_(_)     \__,_|_| |_|___/      \___(_)        |
#   |             |_|                                                      |
#   '----------------------------------------------------------------------'


def mode_update_dns_cache() -> None:
    ip_lookup.update_dns_cache()


modes.register(
    Mode(
        long_option="update-dns-cache",
        handler_function=mode_update_dns_cache,
        short_help="Update IP address lookup cache",
    ))

#.
#   .--clean.-piggyb.------------------------------------------------------.
#   |        _                               _                   _         |
#   |    ___| | ___  __ _ _ __         _ __ (_) __ _  __ _ _   _| |__      |
#   |   / __| |/ _ \/ _` | '_ \  _____| '_ \| |/ _` |/ _` | | | | '_ \     |
#   |  | (__| |  __/ (_| | | | ||_____| |_) | | (_| | (_| | |_| | |_) |    |
#   |   \___|_|\___|\__,_|_| |_(_)    | .__/|_|\__, |\__, |\__, |_.__(_)   |
#   |                                 |_|      |___/ |___/ |___/           |
#   '----------------------------------------------------------------------'


def mode_cleanup_piggyback() -> None:
    time_settings = config.get_config_cache().get_piggybacked_hosts_time_settings()
    piggyback.cleanup_piggyback_files(time_settings)


modes.register(
    Mode(
        long_option="cleanup-piggyback",
        handler_function=mode_cleanup_piggyback,
        short_help="Cleanup outdated piggyback files",
    ))

#.
#   .--scan-parents--------------------------------------------------------.
#   |                                                         _            |
#   |    ___  ___ __ _ _ __        _ __   __ _ _ __ ___ _ __ | |_ ___      |
#   |   / __|/ __/ _` | '_ \ _____| '_ \ / _` | '__/ _ \ '_ \| __/ __|     |
#   |   \__ \ (_| (_| | | | |_____| |_) | (_| | | |  __/ | | | |_\__ \     |
#   |   |___/\___\__,_|_| |_|     | .__/ \__,_|_|  \___|_| |_|\__|___/     |
#   |                             |_|                                      |
#   '----------------------------------------------------------------------'


def mode_scan_parents(options: Dict, args: List[str]) -> None:
    config.load(exclude_parents_mk=True)

    if "procs" in options:
        config.max_num_processes = options["procs"]

    cmk.base.parent_scan.do_scan_parents(args)


modes.register(
    Mode(long_option="scan-parents",
         handler_function=mode_scan_parents,
         needs_config=False,
         needs_checks=False,
         argument=True,
         argument_descr="HOST1 HOST2...",
         argument_optional=True,
         short_help="Autoscan parents, create conf.d/parents.mk",
         long_help=[
             "Uses traceroute in order to automatically detect hosts's parents. "
             "It creates the file conf.d/parents.mk which "
             "defines gateway hosts and parent declarations.",
         ],
         sub_options=[
             Option(
                 long_option="procs",
                 argument=True,
                 argument_descr="N",
                 argument_conv=int,
                 short_help="Start up to N processes in parallel. Defaults to 50.",
             ),
         ]))

#.
#   .--snmptranslate-------------------------------------------------------.
#   |                            _                       _       _         |
#   |  ___ _ __  _ __ ___  _ __ | |_ _ __ __ _ _ __  ___| | __ _| |_ ___   |
#   | / __| '_ \| '_ ` _ \| '_ \| __| '__/ _` | '_ \/ __| |/ _` | __/ _ \  |
#   | \__ \ | | | | | | | | |_) | |_| | | (_| | | | \__ \ | (_| | ||  __/  |
#   | |___/_| |_|_| |_| |_| .__/ \__|_|  \__,_|_| |_|___/_|\__,_|\__\___|  |
#   |                     |_|                                              |
#   '----------------------------------------------------------------------'


def mode_snmptranslate(walk_filename: str) -> None:
    snmp_modes.do_snmptranslate(walk_filename)


modes.register(
    Mode(
        long_option="snmptranslate",
        handler_function=mode_snmptranslate,
        needs_config=False,
        needs_checks=False,
        argument=True,
        argument_descr="HOST",
        short_help="Do snmptranslate on walk",
        long_help=[
            "Does not contact the host again, but reuses the hosts walk from the "
            "directory %s. You can add further MIBs to the directory %s." %
            (cmk.utils.paths.snmpwalks_dir, cmk.utils.paths.local_mib_dir)
        ],
    ))

#.
#   .--snmpwalk------------------------------------------------------------.
#   |                                                   _ _                |
#   |            ___ _ __  _ __ ___  _ ____      ____ _| | | __            |
#   |           / __| '_ \| '_ ` _ \| '_ \ \ /\ / / _` | | |/ /            |
#   |           \__ \ | | | | | | | | |_) \ V  V / (_| | |   <             |
#   |           |___/_| |_|_| |_| |_| .__/ \_/\_/ \__,_|_|_|\_\            |
#   |                               |_|                                    |
#   '----------------------------------------------------------------------'

_oids: List[str] = []
_extra_oids: List[str] = []


def mode_snmpwalk(options: Dict, hostnames: List[str]) -> None:
    if _oids:
        options["oids"] = _oids
    if _extra_oids:
        options["extraoids"] = _extra_oids
    if "oids" in options and "extraoids" in options:
        raise MKGeneralException("You cannot specify --oid and --extraoid at the same time.")

    if not hostnames:
        raise MKBailOut("Please specify host names to walk on.")

    config_cache = config.get_config_cache()

    for hostname in hostnames:
        host_config = config_cache.get_host_config(hostname)
        ipaddress = ip_lookup.lookup_ip_address(host_config)
        if not ipaddress:
            raise MKGeneralException("Failed to gather IP address of %s" % hostname)

        snmp_config = config.HostConfig.make_snmp_config(hostname, ipaddress)
        snmp_modes.do_snmpwalk(options, backend=snmp_factory.backend(snmp_config, log.logger))


modes.register(
    Mode(
        long_option="snmpwalk",
        handler_function=mode_snmpwalk,
        argument=True,
        argument_descr="HOST1 HOST2...",
        argument_optional=True,
        short_help="Do snmpwalk on one or more hosts",
        long_help=[
            "Does a complete snmpwalk for the specified hosts both "
            "on the standard MIB and the enterprises MIB and stores the "
            "result in the directory '%s'. Use the option --oid one or several "
            "times in order to specify alternative OIDs to walk. You need to "
            "specify numeric OIDs. If you want to keep the two standard OIDS "
            ".1.3.6.1.2.1 and .1.3.6.1.4.1 then use --extraoid for just adding "
            "additional OIDs to walk." % cmk.utils.paths.snmpwalks_dir,
        ],
        sub_options=[
            Option(
                long_option="extraoid",
                argument=True,
                argument_descr="A",
                argument_conv=_extra_oids.append,
                short_help="Walk also on this OID, in addition to mib-2 and "
                "enterprises. You can specify this option multiple "
                "times.",
            ),
            Option(long_option="oid",
                   argument=True,
                   argument_descr="A",
                   argument_conv=_oids.append,
                   short_help="Walk on this OID instead of mib-2 and enterprises. "
                   "You can specify this option multiple times."),
        ],
    ))

#.
#   .--snmpget-------------------------------------------------------------.
#   |                                                   _                  |
#   |              ___ _ __  _ __ ___  _ __   __ _  ___| |_                |
#   |             / __| '_ \| '_ ` _ \| '_ \ / _` |/ _ \ __|               |
#   |             \__ \ | | | | | | | | |_) | (_| |  __/ |_                |
#   |             |___/_| |_|_| |_| |_| .__/ \__, |\___|\__|               |
#   |                                 |_|    |___/                         |
#   '----------------------------------------------------------------------'


def mode_snmpget(args: List[str]) -> None:
    if not args:
        raise MKBailOut("You need to specify an OID.")

    config_cache = config.get_config_cache()
    oid, *hostnames = args

    if not hostnames:
        hostnames.extend(host for host in config_cache.all_active_realhosts()
                         if config_cache.get_host_config(host).is_snmp_host)

    assert hostnames
    for hostname in hostnames:
        host_config = config_cache.get_host_config(hostname)
        ipaddress = ip_lookup.lookup_ip_address(host_config)
        if not ipaddress:
            raise MKGeneralException("Failed to gather IP address of %s" % hostname)

        snmp_config = config.HostConfig.make_snmp_config(hostname, ipaddress)
        snmp_modes.do_snmpget(oid, backend=snmp_factory.backend(snmp_config, log.logger))


modes.register(
    Mode(
        long_option="snmpget",
        handler_function=mode_snmpget,
        argument=True,
        argument_descr="OID [HOST1 HOST2...]",
        argument_optional=True,
        short_help="Fetch single OID from one or multiple hosts",
        long_help=[
            "Does a snmpget on the given OID on one or multiple hosts. In case "
            "no host is given, all known SNMP hosts are queried."
        ],
    ))

#.
#   .--flush---------------------------------------------------------------.
#   |                         __ _           _                             |
#   |                        / _| |_   _ ___| |__                          |
#   |                       | |_| | | | / __| '_ \                         |
#   |                       |  _| | |_| \__ \ | | |                        |
#   |                       |_| |_|\__,_|___/_| |_|                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_flush(hosts: List[HostName]) -> None:
    config_cache = config.get_config_cache()

    if not hosts:
        hosts = sorted(config_cache.all_active_hosts())

    for host in hosts:
        host_config = config_cache.get_host_config(host)

        out.output("%-20s: " % host)
        flushed = False

        # counters
        try:
            os.remove(cmk.utils.paths.counters_dir + "/" + host)
            out.output(tty.bold + tty.blue + " counters")
            flushed = True
        except OSError:
            pass

        # cache files
        d = 0
        cache_dir = cmk.utils.paths.tcp_cache_dir
        if os.path.exists(cache_dir):
            for f in os.listdir(cache_dir):
                if f == host or f.startswith(host + "."):
                    try:
                        os.remove(cache_dir + "/" + f)
                        d += 1
                        flushed = True
                    except OSError:
                        pass
            if d == 1:
                out.output(tty.bold + tty.green + " cache")
            elif d > 1:
                out.output(tty.bold + tty.green + " cache(%d)" % d)

        # piggy files from this as source host
        d = piggyback.remove_source_status_file(host)
        if d:
            out.output(tty.bold + tty.magenta + " piggyback(1)")

        # logfiles
        log_dir = cmk.utils.paths.logwatch_dir + "/" + host
        if os.path.exists(log_dir):
            d = 0
            for f in os.listdir(log_dir):
                if f not in [".", ".."]:
                    try:
                        os.remove(log_dir + "/" + f)
                        d += 1
                        flushed = True
                    except OSError:
                        pass
            if d > 0:
                out.output(tty.bold + tty.magenta + " logfiles(%d)" % d)

        # autochecks
        count = host_config.remove_autochecks()
        if count:
            flushed = True
            out.output(tty.bold + tty.cyan + " autochecks(%d)" % count)

        # inventory
        path = cmk.utils.paths.var_dir + "/inventory/" + host
        if os.path.exists(path):
            os.remove(path)
            out.output(tty.bold + tty.yellow + " inventory")

        if not flushed:
            out.output("(nothing)")

        out.output(tty.normal + "\n")


modes.register(
    Mode(
        long_option="flush",
        handler_function=mode_flush,
        argument=True,
        argument_descr="HOST1 HOST2...",
        argument_optional=True,
        needs_config=True,
        short_help="Flush all data of some or all hosts",
        long_help=[
            "Deletes all runtime data belonging to a host. This includes "
            "the inventorized checks, the state of performance counters, "
            "cached agent output, and logfiles. Precompiled host checks "
            "are not deleted.",
        ],
    ))

#.
#   .--nagios-config-------------------------------------------------------.
#   |                     _                                  __ _          |
#   |   _ __   __ _  __ _(_) ___  ___        ___ ___  _ __  / _(_) __ _    |
#   |  | '_ \ / _` |/ _` | |/ _ \/ __|_____ / __/ _ \| '_ \| |_| |/ _` |   |
#   |  | | | | (_| | (_| | | (_) \__ \_____| (_| (_) | | | |  _| | (_| |   |
#   |  |_| |_|\__,_|\__, |_|\___/|___/      \___\___/|_| |_|_| |_|\__, |   |
#   |               |___/                                         |___/    |
#   '----------------------------------------------------------------------'


def mode_dump_nagios_config(args: List[HostName]) -> None:
    from cmk.base.core_nagios import create_config  # pylint: disable=import-outside-toplevel
    create_config(sys.stdout, args if len(args) else None)


modes.register(
    Mode(
        long_option="nagios-config",
        short_option="N",
        handler_function=mode_dump_nagios_config,
        argument=True,
        argument_descr="HOST1 HOST2...",
        argument_optional=True,
        short_help="Output Nagios configuration",
        long_help=[
            "Outputs the Nagios configuration. You may optionally add a list "
            "of hosts. In that case the configuration is generated only for "
            "that hosts (useful for debugging).",
        ],
    ))

#.
#   .--update--------------------------------------------------------------.
#   |                                   _       _                          |
#   |                   _   _ _ __   __| | __ _| |_ ___                    |
#   |                  | | | | '_ \ / _` |/ _` | __/ _ \                   |
#   |                  | |_| | |_) | (_| | (_| | ||  __/                   |
#   |                   \__,_| .__/ \__,_|\__,_|\__\___|                   |
#   |                        |_|                                           |
#   '----------------------------------------------------------------------'


def mode_update() -> None:
    from cmk.base.core_config import do_create_config  # pylint: disable=import-outside-toplevel
    try:
        with cmk.base.core.activation_lock(mode=config.restart_locking):
            do_create_config(create_core(config.monitoring_core))
    except Exception as e:
        console.error("Configuration Error: %s\n" % e)
        if cmk.utils.debug.enabled():
            raise
        sys.exit(1)


modes.register(
    Mode(
        long_option="update",
        short_option="U",
        handler_function=mode_update,
        short_help="Create core config",
        long_help=[
            "Updates the core configuration based on the current Checkmk "
            "configuration. When using the Nagios core, the precompiled host "
            "checks are created and the nagios configuration is updated. "
            "When using the CheckMK Microcore, the core configuration is created "
            "and the configuration for the Core helper processes is being created.",
            "The agent bakery is updating the agents.",
        ],
    ))

#.
#   .--restart-------------------------------------------------------------.
#   |                                 _             _                      |
#   |                   _ __ ___  ___| |_ __ _ _ __| |_                    |
#   |                  | '__/ _ \/ __| __/ _` | '__| __|                   |
#   |                  | | |  __/\__ \ || (_| | |  | |_                    |
#   |                  |_|  \___||___/\__\__,_|_|   \__|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_restart() -> None:
    cmk.base.core.do_restart(create_core(config.monitoring_core))


modes.register(
    Mode(
        long_option="restart",
        short_option="R",
        handler_function=mode_restart,
        short_help="Create core config + core restart",
    ))

#.
#   .--reload--------------------------------------------------------------.
#   |                             _                 _                      |
#   |                    _ __ ___| | ___   __ _  __| |                     |
#   |                   | '__/ _ \ |/ _ \ / _` |/ _` |                     |
#   |                   | | |  __/ | (_) | (_| | (_| |                     |
#   |                   |_|  \___|_|\___/ \__,_|\__,_|                     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_reload() -> None:
    cmk.base.core.do_reload(create_core(config.monitoring_core))


modes.register(
    Mode(
        long_option="reload",
        short_option="O",
        handler_function=mode_reload,
        short_help="Create core config + core reload",
    ))

#.
#   .--man-----------------------------------------------------------------.
#   |                                                                      |
#   |                        _ __ ___   __ _ _ __                          |
#   |                       | '_ ` _ \ / _` | '_ \                         |
#   |                       | | | | | | (_| | | | |                        |
#   |                       |_| |_| |_|\__,_|_| |_|                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_man(args: List[str]) -> None:
    import cmk.utils.man_pages as man_pages  # pylint: disable=import-outside-toplevel
    if args:
        man_pages.ConsoleManPageRenderer(args[0]).paint()
    else:
        man_pages.print_man_page_table()


modes.register(
    Mode(
        long_option="man",
        short_option="M",
        handler_function=mode_man,
        argument=True,
        argument_descr="CHECKTYPE",
        argument_optional=True,
        needs_config=False,
        needs_checks=False,
        short_help="Show manpage for check CHECKTYPE",
        long_help=[
            "Shows documentation about a check type. If /usr/bin/less is "
            "available it is used as pager. Exit by pressing Q. "
            "Use -M without an argument to show a list of all manual pages."
        ],
    ))

#.
#   .--browse-man----------------------------------------------------------.
#   |    _                                                                 |
#   |   | |__  _ __ _____      _____  ___       _ __ ___   __ _ _ __       |
#   |   | '_ \| '__/ _ \ \ /\ / / __|/ _ \_____| '_ ` _ \ / _` | '_ \      |
#   |   | |_) | | | (_) \ V  V /\__ \  __/_____| | | | | | (_| | | | |     |
#   |   |_.__/|_|  \___/ \_/\_/ |___/\___|     |_| |_| |_|\__,_|_| |_|     |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_browse_man() -> None:
    import cmk.utils.man_pages as man_pages  # pylint: disable=import-outside-toplevel
    man_pages.print_man_page_browser()


modes.register(
    Mode(
        long_option="browse-man",
        short_option="m",
        handler_function=mode_browse_man,
        needs_config=False,
        needs_checks=False,
        short_help="Open interactive manpage browser",
    ))

#.
#   .--inventory-----------------------------------------------------------.
#   |             _                      _                                 |
#   |            (_)_ ____   _____ _ __ | |_ ___  _ __ _   _               |
#   |            | | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |              |
#   |            | | | | \ V /  __/ | | | || (_) | |  | |_| |              |
#   |            |_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |              |
#   |                                                  |___/               |
#   '----------------------------------------------------------------------'


def mode_inventory(options: Dict, args: List[str]) -> None:
    config_cache = config.get_config_cache()

    if args:
        hostnames = modes.parse_hostname_list(args, with_clusters=True)
        console.verbose("Doing HW/SW inventory on: %s\n" % ", ".join(hostnames))
    else:
        # No hosts specified: do all hosts and force caching
        hostnames = sorted(config_cache.all_active_hosts())
        checkers.FileCacheFactory.reset_maybe()
        console.verbose("Doing HW/SW inventory on all hosts\n")

    if "force" in options:
        checkers.agent.AgentSource.use_outdated_persisted_sections = True

    inventory.do_inv(hostnames)


modes.register(
    Mode(long_option="inventory",
         short_option="i",
         handler_function=mode_inventory,
         argument=True,
         argument_descr="HOST1 HOST2...",
         argument_optional=True,
         short_help="Do a HW/SW-Inventory on some ar all hosts",
         long_help=[
             "Does a HW/SW-Inventory for all, one or several "
             "hosts. If you add the option -f, --force then persisted sections "
             "will be used even if they are outdated."
         ],
         sub_options=[
             Option(
                 long_option="force",
                 short_option="f",
                 short_help="Use cached agent data even if it's outdated.",
             ),
         ]))

#.
#   .--inventory-as-check--------------------------------------------------.
#   | _                      _                              _     _        |
#   |(_)_ ____   _____ _ __ | |_ ___  _ __ _   _        ___| |__ | | __    |
#   || | '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |_____ / __| '_ \| |/ /    |
#   || | | | \ V /  __/ | | | || (_) | |  | |_| |_____| (__| | | |   < _   |
#   ||_|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |      \___|_| |_|_|\_(_)  |
#   |                                      |___/                           |
#   '----------------------------------------------------------------------'


def mode_inventory_as_check(options: Dict, hostname: HostName) -> int:
    return inventory.do_inv_check(hostname, options)


modes.register(
    Mode(
        long_option="inventory-as-check",
        handler_function=mode_inventory_as_check,
        argument=True,
        argument_descr="HOST",
        short_help="Do HW/SW-Inventory, behave like check plugin",
        sub_options=[
            Option(
                long_option="hw-changes",
                argument=True,
                argument_descr="S",
                argument_conv=int,
                short_help="Use monitoring state S for HW changes",
            ),
            Option(
                long_option="sw-changes",
                argument=True,
                argument_descr="S",
                argument_conv=int,
                short_help="Use monitoring state S for SW changes",
            ),
            Option(
                long_option="sw-missing",
                argument=True,
                argument_descr="S",
                argument_conv=int,
                short_help="Use monitoring state S for missing SW packages info",
            ),
            Option(
                long_option="inv-fail-status",
                argument=True,
                argument_descr="S",
                argument_conv=int,
                short_help="Use monitoring state S in case of error",
            ),
        ],
    ))

#.
#   .--automation----------------------------------------------------------.
#   |                   _                        _   _                     |
#   |        __ _ _   _| |_ ___  _ __ ___   __ _| |_(_) ___  _ __          |
#   |       / _` | | | | __/ _ \| '_ ` _ \ / _` | __| |/ _ \| '_ \         |
#   |      | (_| | |_| | || (_) | | | | | | (_| | |_| | (_) | | | |        |
#   |       \__,_|\__,_|\__\___/|_| |_| |_|\__,_|\__|_|\___/|_| |_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_automation(args: List[str]) -> None:
    import cmk.base.automations as automations  # pylint: disable=import-outside-toplevel

    if not args:
        raise automations.MKAutomationError("You need to provide arguments")

    # At least for the automation calls that buffer and handle the stdout/stderr on their own
    # we can now enable this. In the future we should remove this call for all automations calls and
    # handle the output in a common way.
    if args[0] not in ["restart", "reload", "start", "create-diagnostics-dump", "try-inventory"]:
        log.clear_console_logging()

    sys.exit(automations.automations.execute(args[0], args[1:]))


modes.register(
    Mode(
        long_option="automation",
        handler_function=mode_automation,
        needs_config=False,
        needs_checks=False,
        argument=True,
        argument_descr="COMMAND...",
        argument_optional=True,
        short_help="Internal helper to invoke Check_MK actions",
    ))

#.
#   .--notify--------------------------------------------------------------.
#   |                                 _   _  __                            |
#   |                     _ __   ___ | |_(_)/ _|_   _                      |
#   |                    | '_ \ / _ \| __| | |_| | | |                     |
#   |                    | | | | (_) | |_| |  _| |_| |                     |
#   |                    |_| |_|\___/ \__|_|_|  \__, |                     |
#   |                                           |___/                      |
#   '----------------------------------------------------------------------'


def mode_notify(options: Dict, args: List[str]) -> Optional[int]:
    import cmk.base.notify as notify  # pylint: disable=import-outside-toplevel
    with store.lock_checkmk_configuration():
        config.load(with_conf_d=True, validate_hosts=False)
    return notify.do_notify(options, args)


modes.register(
    Mode(
        long_option="notify",
        handler_function=mode_notify,
        needs_config=False,
        needs_checks=False,
        argument=True,
        argument_descr="MODE",
        argument_optional=True,
        short_help="Used to send notifications from core",
        # TODO: Write long help
        sub_options=[
            Option(
                long_option="log-to-stdout",
                short_help="Also write log messages to console",
            ),
            keepalive_option,
        ],
    ))

#.
#   .--discover-marked-hosts-----------------------------------------------.
#   |           _ _                                 _            _         |
#   |        __| (_)___  ___   _ __ ___   __ _ _ __| | _____  __| |        |
#   |       / _` | / __|/ __| | '_ ` _ \ / _` | '__| |/ / _ \/ _` |        |
#   |      | (_| | \__ \ (__ _| | | | | | (_| | |  |   <  __/ (_| |        |
#   |       \__,_|_|___/\___(_)_| |_| |_|\__,_|_|  |_|\_\___|\__,_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_discover_marked_hosts() -> None:
    discovery.discover_marked_hosts(create_core(config.monitoring_core))


modes.register(
    Mode(
        long_option="discover-marked-hosts",
        handler_function=mode_discover_marked_hosts,
        short_help="Run discovery for hosts known to have changed services",
        long_help=[
            "Run actual service discovery on all hosts that "
            "are known to have new/vanished services due to an earlier run of "
            "check-discovery. The results of this discovery may be activated "
            "automatically if configured.",
        ],
    ))

#.
#   .--check-discovery-----------------------------------------------------.
#   |       _     _               _ _                                      |
#   |   ___| |__ | | __        __| (_)___  ___ _____   _____ _ __ _   _    |
#   |  / __| '_ \| |/ / _____ / _` | / __|/ __/ _ \ \ / / _ \ '__| | | |   |
#   | | (__| | | |   < |_____| (_| | \__ \ (_| (_) \ V /  __/ |  | |_| |   |
#   |  \___|_| |_|_|\_(_)     \__,_|_|___/\___\___/ \_/ \___|_|   \__, |   |
#   |                                                             |___/    |
#   '----------------------------------------------------------------------'


def mode_check_discovery(hostname: HostName) -> int:
    return discovery.check_discovery(hostname, ipaddress=None)


modes.register(
    Mode(
        long_option="check-discovery",
        handler_function=mode_check_discovery,
        argument=True,
        argument_descr="HOSTNAME",
        short_help="Check for not yet monitored services",
        long_help=[
            "Make Check_MK behave as monitoring plugins that checks if an "
            "inventory would find new or vanished services for the host. "
            "If configured to do so, this will queue those hosts for automatic "
            "discover-marked-hosts"
        ],
    ))

#.
#   .--discover------------------------------------------------------------.
#   |                     _ _                                              |
#   |                  __| (_)___  ___ _____   _____ _ __                  |
#   |                 / _` | / __|/ __/ _ \ \ / / _ \ '__|                 |
#   |                | (_| | \__ \ (_| (_) \ V /  __/ |                    |
#   |                 \__,_|_|___/\___\___/ \_/ \___|_|                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'

_ChecksOption = Optional[Set[CheckPluginName]]


def _convert_checks_argument(arg: str) -> _ChecksOption:
    if arg == "@all":
        # this is the same as ommitting the option entirely.
        return None
    try:
        # kindly forgive empty strings
        return {CheckPluginName(maincheckify(n)) for n in arg.split(",") if n}
    except ValueError as exc:
        raise MKBailOut("Error in --checks argument: %s" % exc)


_option_checks = Option(
    long_option="checks",
    short_help="Restrict discovery/checking to these check plugins",
    argument=True,
    argument_descr="C",
    argument_conv=_convert_checks_argument,
)

DiscoverOptions = TypedDict(
    'DiscoverOptions',
    {
        'checks': _ChecksOption,
        'discover': int,
    },
    total=False,
)


def mode_discover(options: DiscoverOptions, args: List[str]) -> None:
    hostnames = modes.parse_hostname_list(args)
    if not hostnames:
        # In case of discovery without host restriction, use the cache file
        # by default. Otherwise Checkmk would have to connect to ALL hosts.
        # This will make Checkmk only contact hosts in case the cache is not
        # new enough.
        checkers.FileCacheFactory.reset_maybe()

    discovery.do_discovery(set(hostnames), options.get("checks"), options["discover"] == 1)


modes.register(
    Mode(long_option="discover",
         short_option="I",
         handler_function=mode_discover,
         argument=True,
         argument_descr="[-I] HOST1 HOST2...",
         argument_optional=True,
         short_help="Find new services",
         long_help=[
             "Make Check_MK behave as monitoring plugins that checks if an "
             "inventory would find new or vanished services for the host. "
             "If configured to do so, this will queue those hosts for automatic "
             "discover-marked-hosts",
             "Can be restricted to certain check types. Write '--checks df -I' if "
             "you just want to look for new filesystems. Use 'cmk -L' for a "
             "list of all check types.",
             "-II does the same as -I but deletes all existing checks of the "
             "specified types and hosts."
         ],
         sub_options=[
             Option(
                 long_option="discover",
                 short_option="I",
                 short_help="Delete existing services before starting discovery",
                 count=True,
             ),
             _option_checks,
         ]))

#.
#   .--check---------------------------------------------------------------.
#   |                           _               _                          |
#   |                       ___| |__   ___  ___| | __                      |
#   |                      / __| '_ \ / _ \/ __| |/ /                      |
#   |                     | (__| | | |  __/ (__|   <                       |
#   |                      \___|_| |_|\___|\___|_|\_\                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'

CheckingOptions = TypedDict(
    'CheckingOptions',
    {
        'no-submit': bool,
        'perfdata': bool,
        'checks': _ChecksOption,
        'keepalive': bool,
        'keepalive-fd': int,
    },
    total=False,
)


def mode_check(options: CheckingOptions, args: List[str]) -> None:
    import cmk.base.checking as checking  # pylint: disable=import-outside-toplevel
    import cmk.base.item_state as item_state  # pylint: disable=import-outside-toplevel
    try:
        import cmk.base.cee.keepalive as keepalive  # pylint: disable=import-outside-toplevel
    except ImportError:
        keepalive = None  # type: ignore[assignment]

    if keepalive and "keepalive" in options:
        # handle CMC check helper
        keepalive.enable()
        if "keepalive-fd" in options:
            keepalive.fd.set_(options["keepalive-fd"])

        keepalive.check.do_keepalive()
        return

    if "perfdata" in options:
        checking.show_perfdata()

    if "no-submit" in options:
        checking.disable_submit()
        item_state.continue_on_counter_wrap()

    # handle adhoc-check
    hostname: HostName = args[0]
    ipaddress: Optional[HostAddress] = None
    if len(args) == 2:
        ipaddress = args[1]

    return checking.do_check(hostname, ipaddress, only_check_plugin_names=options.get("checks"))


modes.register(
    Mode(long_option="check",
         handler_function=mode_check,
         argument=True,
         argument_descr="HOST [IPADDRESS]",
         argument_optional=True,
         short_help="Check all services on the given HOST",
         long_help=[
             "Execute all checks on the given HOST. Optionally you can specify "
             "a second argument, the IPADDRESS. If you don't set this, the "
             "configured IP address of the HOST is used.",
             "By default the check results are sent to the core. If you provide "
             "the option '-n', the results will not be sent to the core and the "
             "counters of the check will not be stored.",
             "You can use '-v' to see the results of the checks. Add '-p' to "
             "also see the performance data of the checks."
             "Can be restricted to certain check types. Write '--checks df -I' if "
             "you just want to look for new filesystems. Use 'check_mk -L' for a "
             "list of all check types. Use 'tcp' for all TCP based checks and "
             "'snmp' for all SNMP based checks.",
         ],
         sub_options=[
             Option(
                 long_option="no-submit",
                 short_option="n",
                 short_help="Do not submit results to core, do not save counters",
             ),
             Option(
                 long_option="perfdata",
                 short_option="p",
                 short_help="Also show performance data (use with -v)",
             ),
             _option_checks,
             keepalive_option,
             Option(
                 long_option="keepalive-fd",
                 argument=True,
                 argument_descr="I",
                 argument_conv=int,
                 short_help="File descriptor to send output to",
             ),
         ]))

#.
#   .--version-------------------------------------------------------------.
#   |                                     _                                |
#   |                 __   _____ _ __ ___(_) ___  _ __                     |
#   |                 \ \ / / _ \ '__/ __| |/ _ \| '_ \                    |
#   |                  \ V /  __/ |  \__ \ | (_) | | | |                   |
#   |                   \_/ \___|_|  |___/_|\___/|_| |_|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def mode_version() -> None:
    out.output(
        """This is Check_MK version %s %s
Copyright (C) 2009 Mathias Kettner

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; see the file COPYING.  If not, write to
    the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
    Boston, MA 02111-1307, USA.

""", cmk_version.__version__,
        cmk_version.edition_short().upper())


modes.register(
    Mode(
        long_option="version",
        short_option="V",
        handler_function=mode_version,
        short_help="Print the version of Check_MK",
        needs_config=False,
        needs_checks=False,
    ))

#.
#   .--help----------------------------------------------------------------.
#   |                         _          _                                 |
#   |                        | |__   ___| |_ __                            |
#   |                        | '_ \ / _ \ | '_ \                           |
#   |                        | | | |  __/ | |_) |                          |
#   |                        |_| |_|\___|_| .__/                           |
#   |                                     |_|                              |
#   '----------------------------------------------------------------------'


def mode_help() -> None:
    out.output("""WAYS TO CALL:
%s

OPTIONS:
%s

NOTES:
%s

""" % (
        modes.short_help(),
        modes.general_option_help(),
        modes.long_help(),
    ))


modes.register(
    Mode(
        long_option="help",
        short_option="h",
        handler_function=mode_help,
        short_help="Print this help",
        needs_config=False,
        needs_checks=False,
    ))

#.
#   .--diagnostics---------------------------------------------------------.
#   |             _ _                             _   _                    |
#   |          __| (_) __ _  __ _ _ __   ___  ___| |_(_) ___ ___           |
#   |         / _` | |/ _` |/ _` | '_ \ / _ \/ __| __| |/ __/ __|          |
#   |        | (_| | | (_| | (_| | | | | (_) \__ \ |_| | (__\__ \          |
#   |         \__,_|_|\__,_|\__, |_| |_|\___/|___/\__|_|\___|___/          |
#   |                       |___/                                          |
#   '----------------------------------------------------------------------'


def mode_create_diagnostics_dump(options: DiagnosticsModesParameters) -> None:
    cmk.base.diagnostics.create_diagnostics_dump(
        cmk.utils.diagnostics.deserialize_modes_parameters(options))


def _get_diagnostics_dump_sub_options() -> List[Option]:
    sub_options = [
        Option(
            long_option=OPT_LOCAL_FILES,
            short_help=("Pack a list of installed, unpacked, optional files below $OMD_ROOT/local. "
                        "This also includes information about installed MKPs."),
        ),
        Option(
            long_option=OPT_OMD_CONFIG,
            short_help="Pack content of 'etc/omd/site.conf'",
        ),
        Option(
            long_option=OPT_CHECKMK_OVERVIEW,
            short_help="Pack HW/SW inventory node 'Software > Applications > Checkmk'",
        ),
        Option(
            long_option=OPT_CHECKMK_CONFIG_FILES,
            short_help="Pack configuration files '*.mk' and '*.conf' from etc/check_mk",
            argument=True,
            argument_descr="FILE,FILE...",
        ),
    ]

    if not cmk_version.is_raw_edition():
        sub_options.append(
            Option(
                long_option=OPT_PERFORMANCE_GRAPHS,
                short_help=(
                    "Pack performance graphs like CPU load and utilization of Checkmk Server"),
            ))
    return sub_options


modes.register(
    Mode(
        long_option="create-diagnostics-dump",
        handler_function=mode_create_diagnostics_dump,
        short_help="Create diagnostics dump",
        long_help=[
            "Create a dump containing information for diagnostic analysis "
            "in the folder var/check_mk/diagnostics."
        ],
        needs_config=False,
        needs_checks=False,
        sub_options=_get_diagnostics_dump_sub_options(),
    ))
