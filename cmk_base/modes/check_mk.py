#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

import os
import sys
from typing import List  # pylint: disable=unused-import

import cmk
import cmk.utils.tty as tty
import cmk.utils.paths
import cmk.utils.log
import cmk.utils.debug
import cmk.utils.store
from cmk.utils.exceptions import MKBailOut

import cmk_base.data_sources as data_sources
import cmk_base.console as console
import cmk_base.config as config
import cmk_base.discovery as discovery
import cmk_base.inventory as inventory
import cmk_base.inventory_plugins as inventory_plugins
import cmk_base.check_api as check_api
import cmk_base.piggyback as piggyback
import cmk_base.snmp as snmp
import cmk_base.ip_lookup as ip_lookup
import cmk_base.profiling as profiling
import cmk_base.core
import cmk_base.data_sources.abstract
import cmk_base.core_nagios
import cmk_base.parent_scan
import cmk_base.dump_host
import cmk_base.backup
import cmk_base.packaging
import cmk_base.localize

from cmk_base.modes import (
    modes,
    Mode,
    Option,
    keepalive_option,
)
import cmk_base.check_utils
from cmk_base.core_factory import create_core

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
#   | The general options that are available for all Check_MK modes. Only  |
#   | add new general options in case they are really affecting basic      |
#   | things and used by the most of the modes.                            |
#   '----------------------------------------------------------------------'

_verbosity = 0


def option_verbosity():
    global _verbosity
    _verbosity += 1
    cmk.utils.log.set_verbosity(verbosity=_verbosity)


modes.register_general_option(
    Option(
        long_option="verbose",
        short_option="v",
        short_help="Enable verbose output (Use twice for more)",
        handler_function=option_verbosity,
    ))

_verbosity = 0


def option_cache():
    data_sources.abstract.DataSource.set_may_use_cache_file()
    data_sources.abstract.DataSource.set_use_outdated_cache_file()


modes.register_general_option(
    Option(
        long_option="cache",
        short_help="Read info from data source cache files when existant, even when it "
        "is outdated. Only contact the data sources when the cache file "
        "is absent",
        handler_function=option_cache,
    ))


def option_no_cache():
    cmk_base.data_sources.abstract.DataSource.disable_data_source_cache()


modes.register_general_option(
    Option(
        long_option="no-cache",
        short_help="Never use cached information",
        handler_function=option_no_cache,
    ))


def option_no_tcp():
    data_sources.tcp.TCPDataSource.use_only_cache()


# TODO: Check whether or not this is used only for -I as written in the help.
# Does it affect inventory/checking too?
modes.register_general_option(
    Option(
        long_option="no-tcp",
        short_help="For -I: Only use cache files. Skip hosts without cache files.",
        handler_function=option_no_tcp,
    ))


def option_usewalk():
    snmp.enforce_use_stored_walks()
    ip_lookup.enforce_localhost()


modes.register_general_option(
    Option(
        long_option="usewalk",
        short_help="Use snmpwalk stored with --snmpwalk",
        handler_function=option_usewalk,
    ))


def option_debug():
    cmk.utils.debug.enable()


modes.register_general_option(
    Option(
        long_option="debug",
        short_help="Let most Python exceptions raise through",
        handler_function=option_debug,
    ))


def option_profile():
    profiling.enable()


modes.register_general_option(
    Option(
        long_option="profile",
        short_help="Enable profiling mode",
        handler_function=option_profile,
    ))


def option_fake_dns(a):
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


def mode_list_hosts(options, args):
    hosts = _list_all_hosts(args, options)
    console.output("\n".join(hosts))
    if hosts:
        console.output("\n")


# TODO: Does not care about internal group "check_mk"
def _list_all_hosts(hostgroups, options):
    config_cache = config.get_config_cache()

    hostnames = set()

    if options.get("all-sites"):
        hostnames.update(config_cache.all_configured_hosts())  # Return all hosts, including offline
        if not "include-offline" in options:
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


def mode_list_tag(args):
    hosts = _list_all_hosts_with_tags(args)
    console.output("\n".join(hosts))
    if hosts:
        console.output("\n")


def _list_all_hosts_with_tags(tags):
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


def mode_list_checks():
    import cmk.utils.man_pages as man_pages
    all_check_manuals = man_pages.all_man_pages()

    checks_sorted = config.check_info.items() + \
       [ ("check_" + name, entry) for (name, entry) in config.active_check_info.items() ]
    checks_sorted.sort()
    for check_plugin_name, check in checks_sorted:
        man_filename = all_check_manuals.get(check_plugin_name)
        try:
            if 'command_line' in check:
                what = 'active'
                ty_color = tty.blue
            elif cmk_base.check_utils.is_snmp_check(check_plugin_name):
                what = 'snmp'
                ty_color = tty.magenta
            else:
                what = 'tcp'
                ty_color = tty.yellow

            if man_filename:
                title = file(man_filename).readlines()[0].split(":", 1)[1].strip()
            else:
                title = "(no man page present)"

            console.output((tty.bold + "%-44s" + tty.normal
                   + ty_color + " %-6s " + tty.normal
                   + "%s\n") % \
                  (check_plugin_name, what, title))
        except Exception as e:
            console.error("ERROR in check %r: %s\n" % (check_plugin_name, e))


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


def mode_dump_agent(hostname):
    try:
        config_cache = config.get_config_cache()
        host_config = config_cache.get_host_config(hostname)

        if host_config.is_cluster:
            raise MKBailOut("Can not be used with cluster hosts")

        ipaddress = ip_lookup.lookup_ip_address(hostname)

        output = ""

        sources = data_sources.DataSources(hostname, ipaddress)
        sources.set_max_cachefile_age(config.check_max_cachefile_age)

        for source in sources.get_data_sources():
            if isinstance(source, data_sources.abstract.CheckMKAgentDataSource):
                output += source.run_raw()

        # Show errors of problematic data sources
        has_errors = False
        for source in sources.get_data_sources():
            source_state, source_output, _source_perfdata = source.get_summary_result_for_checking()
            if source_state != 0:
                console.error("ERROR [%s]: %s\n" % (source.id(), source_output))
                has_errors = True

        console.output(output)
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


def mode_dump_hosts(hostlist):
    config_cache = config.get_config_cache()
    if not hostlist:
        hostlist = config_cache.all_active_hosts()

    for hostname in sorted(hostlist):
        cmk_base.dump_host.dump_host(hostname)


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


def mode_paths():
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
        (cmk.utils.paths.notifications_dir, directory, inst, "Notification scripts"),
        (cmk.utils.paths.inventory_dir, directory, inst, "Inventory plugins"),
        (cmk.utils.paths.agents_dir, directory, inst, "Agents for operating systems"),
        (cmk.utils.paths.doc_dir, directory, inst, "Documentation files"),
        (cmk.utils.paths.web_dir, directory, inst, "Check_MK's web pages"),
        (cmk.utils.paths.check_manpages_dir, directory, inst, "Check manpages (for check_mk -M)"),
        (cmk.utils.paths.lib_dir, directory, inst, "Binary plugins (architecture specific)"),
        (cmk.utils.paths.pnp_templates_dir, directory, inst, "Templates for PNP4Nagios"),
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
        (cmk.utils.paths.local_checks_dir, directory, local, "Locally installed checks"),
        (cmk.utils.paths.local_notifications_dir, directory, local,
         "Locally installed notification scripts"),
        (cmk.utils.paths.local_inventory_dir, directory, local,
         "Locally installed inventory plugins"),
        (cmk.utils.paths.local_check_manpages_dir, directory, local,
         "Locally installed check man pages"),
        (cmk.utils.paths.local_agents_dir, directory, local,
         "Locally installed agents and plugins"),
        (cmk.utils.paths.local_web_dir, directory, local, "Locally installed Multisite addons"),
        (cmk.utils.paths.local_pnp_templates_dir, directory, local,
         "Locally installed PNP templates"),
        (cmk.utils.paths.local_doc_dir, directory, local, "Locally installed documentation"),
        (cmk.utils.paths.local_locale_dir, directory, local, "Locally installed localizations"),
    ]

    def show_paths(title, t):
        if t != inst:
            console.output("\n")
        console.output(tty.bold + title + tty.normal + "\n")
        for path, filedir, typp, descr in paths:
            if typp == t:
                if filedir == directory:
                    path += "/"
                console.output("  %-47s: %s%s%s\n" % (descr, tty.bold + tty.blue, path, tty.normal))

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


def mode_backup(*args):
    cmk_base.backup.do_backup(*args)


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


def mode_restore(*args):
    cmk_base.backup.do_restore(*args)


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


def mode_packaging(*args):
    cmk_base.packaging.do_packaging(*args)


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


def mode_localize(*args):
    cmk_base.localize.do_localize(*args)


modes.register(
    Mode(
        long_option="localize",
        handler_function=mode_localize,
        needs_config=False,
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


def mode_update_dns_cache():
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


def mode_cleanup_piggyback():
    from cmk_base.piggyback import cleanup_piggyback_files
    cleanup_piggyback_files(config.piggyback_max_cachefile_age)


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


def mode_scan_parents(options, args):
    config.load(exclude_parents_mk=True)

    if "procs" in options:
        config.max_num_processes = options["procs"]

    cmk_base.parent_scan.do_scan_parents(args)


modes.register(
    Mode(
        long_option="scan-parents",
        handler_function=mode_scan_parents,
        needs_config=False,
        # TODO: Sadly needs to be True because the checks need to initialize the check specific
        # configuration variables before the config can be loaded.
        needs_checks=True,
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


def mode_snmptranslate(*args):
    snmp.do_snmptranslate(*args)

modes.register(Mode(
    long_option="snmptranslate",
    handler_function=mode_snmptranslate,
    needs_config=False,
    argument=True,
    argument_descr="HOST",
    short_help="Do snmptranslate on walk",
    long_help=[
        "Does not contact the host again, but reuses the hosts walk from the "
        "directory %s. You can add further MIBs to the directory %s." % \
         (cmk.utils.paths.snmpwalks_dir, cmk.utils.paths.local_mibs_dir)
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

_oids = []  # type: List[str]
_extra_oids = []  # type: List[str]


def mode_snmpwalk(options, args):
    if _oids:
        options["oids"] = _oids
    if _extra_oids:
        options["extraoids"] = _extra_oids

    snmp.do_snmpwalk(options, args)


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


def mode_snmpget(*args):
    snmp.do_snmpget(*args)


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


def mode_flush(hosts):
    config_cache = config.get_config_cache()

    if not hosts:
        hosts = config_cache.all_active_hosts()

    for host in hosts:
        host_config = config_cache.get_host_config(host)

        console.output("%-20s: " % host)
        flushed = False

        # counters
        try:
            os.remove(cmk.utils.paths.counters_dir + "/" + host)
            console.output(tty.bold + tty.blue + " counters")
            flushed = True
        except:
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
                    except:
                        pass
            if d == 1:
                console.output(tty.bold + tty.green + " cache")
            elif d > 1:
                console.output(tty.bold + tty.green + " cache(%d)" % d)

        # piggy files from this as source host
        d = piggyback.remove_source_status_file(host)
        if d:
            console.output(tty.bold + tty.magenta + " piggyback(1)")

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
                    except:
                        pass
            if d > 0:
                console.output(tty.bold + tty.magenta + " logfiles(%d)" % d)

        # autochecks
        count = discovery.remove_autochecks_of(host_config)
        if count:
            flushed = True
            console.output(tty.bold + tty.cyan + " autochecks(%d)" % count)

        # inventory
        path = cmk.utils.paths.var_dir + "/inventory/" + host
        if os.path.exists(path):
            os.remove(path)
            console.output(tty.bold + tty.yellow + " inventory")

        if not flushed:
            console.output("(nothing)")

        console.output(tty.normal + "\n")


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


def mode_dump_nagios_config(args):
    from cmk_base.core_nagios import create_config
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


def mode_update_no_precompile(options):
    from cmk_base.core_config import do_update
    do_update(create_core(options), with_precompile=False)


modes.register(
    Mode(
        long_option="update-no-precompile",
        short_option="B",
        handler_function=mode_update_no_precompile,
        short_help="Create configuration for core",
        long_help=[
            "Updates the configuration for the monitoring core. In case of Nagios, "
            "the file etc/nagios/conf.d/check_mk_objects.cfg is updated. In case of "
            "the Microcore, either the file var/check_mk/core/config or the file "
            "specified with the option --cmc-file is written.",
        ],
        sub_options=[
            Option(
                long_option="cmc-file",
                argument=True,
                argument_descr="X",
                short_help="Relative filename for CMC config file",
            ),
        ],
    ))

#.
#   .--compile-------------------------------------------------------------.
#   |                                           _ _                        |
#   |                  ___ ___  _ __ ___  _ __ (_) | ___                   |
#   |                 / __/ _ \| '_ ` _ \| '_ \| | |/ _ \                  |
#   |                | (_| (_) | | | | | | |_) | | |  __/                  |
#   |                 \___\___/|_| |_| |_| .__/|_|_|\___|                  |
#   |                                    |_|                               |
#   '----------------------------------------------------------------------'


def mode_compile():
    cmk_base.core_nagios.precompile_hostchecks()


modes.register(
    Mode(
        long_option="compile",
        short_option="C",
        handler_function=mode_compile,
        short_help="Precompile host checks",
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


def mode_update(options):
    from cmk_base.core_config import do_update
    do_update(create_core(options), with_precompile=True)


modes.register(
    Mode(
        long_option="update",
        short_option="U",
        handler_function=mode_update,
        short_help="Precompile + create config for core",
        long_help=[
            "Updates the core configuration based on the current Check_MK "
            "configuration. When using the Nagios core, the precompiled host "
            "checks are created and the nagios configuration is updated. "
            "CEE only: When using the Check_MK Microcore, the core is created "
            "and the configuration for the Check_MK check helpers is being created.",
            "The agent bakery is updating the agents.",
        ],
        sub_options=[
            Option(
                long_option="cmc-file",
                argument=True,
                argument_descr="X",
                short_help="Relative filename for CMC config file",
            ),
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


def mode_restart():
    cmk_base.core.do_restart(create_core())


modes.register(
    Mode(
        long_option="restart",
        short_option="R",
        handler_function=mode_restart,
        short_help="Precompile + config + core restart",
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


def mode_reload():
    cmk_base.core.do_reload(create_core())


modes.register(
    Mode(
        long_option="reload",
        short_option="O",
        handler_function=mode_reload,
        short_help="Precompile + config + core reload",
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


def mode_man(*args):
    import cmk.utils.man_pages as man_pages
    if args[0]:
        man_pages.print_man_page(args[0][0])
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


def mode_browse_man():
    import cmk.utils.man_pages as man_pages
    man_pages.print_man_page_browser()


modes.register(
    Mode(
        long_option="browse-man",
        short_option="m",
        handler_function=mode_browse_man,
        needs_config=False,
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


def mode_inventory(options, args):
    inventory_plugins.load_plugins(check_api.get_check_api_context, inventory.get_inventory_context)
    config_cache = config.get_config_cache()

    if args:
        hostnames = modes.parse_hostname_list(args, with_clusters=True)
        console.verbose("Doing HW/SW inventory on: %s\n" % ", ".join(hostnames))
    else:
        # No hosts specified: do all hosts and force caching
        hostnames = config_cache.all_active_hosts()
        data_sources.abstract.DataSource.set_may_use_cache_file(
            not data_sources.abstract.DataSource.is_agent_cache_disabled())
        console.verbose("Doing HW/SW inventory on all hosts\n")

    if "force" in options:
        data_sources.abstract.CheckMKAgentDataSource.use_outdated_persisted_sections()

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


def mode_inventory_as_check(options, hostname):
    inventory_plugins.load_plugins(check_api.get_check_api_context, inventory.get_inventory_context)

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


def mode_automation(args):
    import cmk_base.automations as automations

    if not args:
        raise automations.MKAutomationError("You need to provide arguments")

    sys.exit(automations.automations.execute(args[0], args[2:]))


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


def mode_notify(options, *args):
    import cmk_base.notify as notify
    with cmk.utils.store.lock_checkmk_configuration():
        config.load(with_conf_d=True, validate_hosts=False)
    # TODO: Fix the code and remove the pragma below!
    return notify.do_notify(options, *args)  # pylint: disable=no-value-for-parameter


modes.register(
    Mode(
        long_option="notify",
        handler_function=mode_notify,
        needs_config=False,
        # TODO: Sadly needs to be True because the checks need to initialize the check specific
        # configuration variables before the config can be loaded.
        needs_checks=True,
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


def mode_discover_marked_hosts():
    discovery.discover_marked_hosts(create_core())


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


def mode_check_discovery(hostname):
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


def mode_discover(options, args):
    hostnames = modes.parse_hostname_list(args)
    if not hostnames:
        # In case of discovery without host restriction, use the cache file
        # by default. Otherwise Check_MK would have to connect to ALL hosts.
        # This will make Check_MK only contact hosts in case the cache is not
        # new enough.
        data_sources.abstract.DataSource.set_may_use_cache_file(
            not data_sources.abstract.DataSource.is_agent_cache_disabled())

    discovery.do_discovery(hostnames, options.get("checks"), options["discover"] == 1)


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
             "you just want to look for new filesystems. Use 'check_mk -L' for a "
             "list of all check types. Use 'tcp' for all TCP based checks and "
             "'snmp' for all SNMP based checks.",
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
             Option(
                 long_option="checks",
                 short_help="Restrict discovery to certain check types",
                 argument=True,
                 argument_descr="C",
                 argument_conv=lambda x: config.check_info.keys() if x == "@all" else x.split(","),
             ),
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


def mode_check(options, args):
    import cmk_base.checking as checking
    import cmk_base.item_state as item_state
    try:
        import cmk_base.cee.keepalive as keepalive
    except ImportError:
        keepalive = None

    if keepalive and "keepalive" in options:
        # handle CMC check helper
        keepalive.enable()
        if "keepalive-fd" in options:
            keepalive.set_keepalive_fd(options["keepalive-fd"])

        keepalive.do_check_keepalive()
        return

    if "perfdata" in options:
        checking.show_perfdata()

    if "no-submit" in options:
        checking.disable_submit()
        item_state.continue_on_counter_wrap()

    # handle adhoc-check
    hostname = args[0]
    if len(args) == 2:
        ipaddress = args[1]
    else:
        ipaddress = None

    return checking.do_check(hostname, ipaddress, options.get("checks"))


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
             Option(
                 long_option="checks",
                 short_help="Restrict discovery to certain check types",
                 argument=True,
                 argument_descr="C",
                 argument_conv=lambda x: config.check_info.keys() if x == "@all" else x.split(","),
             ),
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


def mode_version():
    console.output("""This is Check_MK version %s %s
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

""" % (cmk.__version__, cmk.edition_short().upper()))


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


def mode_help():
    console.output("""WAYS TO CALL:
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
