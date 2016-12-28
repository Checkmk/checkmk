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

import cmk
import cmk.tty as tty
import cmk.paths

import cmk_base.console as console
import cmk_base.config as config

from cmk_base.modes import modes, Mode

#.
#   .--list-hosts----------------------------------------------------------.
#   |              _ _     _        _               _                      |
#   |             | (_)___| |_     | |__   ___  ___| |_ ___                |
#   |             | | / __| __|____| '_ \ / _ \/ __| __/ __|               |
#   |             | | \__ \ ||_____| | | | (_) \__ \ |_\__ \               |
#   |             |_|_|___/\__|    |_| |_|\___/|___/\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def mode_list_hosts():
    hosts = _list_all_hosts(args)
    console.output("\n".join(hosts))
    if hosts:
        console.output("\n")


def _list_all_hosts(hostgroups):
    hostlist = []

    for hn in config.all_active_hosts():
        if not hostgroups:
            hostlist.append(hn)
        else:
            for hg in config.hostgroups_of(hn):
                if hg in hostgroups:
                    hostlist.append(hn)
                    break

    return sorted(hostlist)


modes.register(Mode(
    long_option="list-hosts",
    short_option="l",
    handler_function=mode_list_hosts,
    arguments=True,
    argument_descr="[G1 G2 ...]",
    short_help="Print list of all hosts or members of host groups",
    long_help=[
        "Called without argument lists all hosts. You may "
        "specify one or more host groups to restrict the output to hosts "
        "that are in at least one of those groups.",
    ]
))

#.
#   .--list-tag------------------------------------------------------------.
#   |                   _ _     _        _                                 |
#   |                  | (_)___| |_     | |_ __ _  __ _                    |
#   |                  | | / __| __|____| __/ _` |/ _` |                   |
#   |                  | | \__ \ ||_____| || (_| | (_| |                   |
#   |                  |_|_|___/\__|     \__\__,_|\__, |                   |
#   |                                             |___/                    |
#   '----------------------------------------------------------------------'

def mode_list_tag():
    hosts = _list_all_hosts_with_tags(args)
    console.output("\n".join(hosts))
    if hosts:
        console.output("\n")


def _list_all_hosts_with_tags(tags):
    hosts = []

    if "offline" in tags:
        hostlist = config.all_offline_hosts()
    else:
        hostlist = config.all_active_hosts()

    for h in hostlist:
        if rulesets.hosttags_match_taglist(tags_of_host(h), tags):
            hosts.append(h)
    return hosts


modes.register(Mode(
    long_option="list-tag",
    handler_function=mode_list_tag,
    arguments=True,
    argument_descr="[TAG1 TAG2 ...]",
    short_help="List hosts having certain tags",
    long_help=[
        "Prints all hosts that have all of the specified tags at once."
    ]
))

#.
#   .--list-checks---------------------------------------------------------.
#   |           _ _     _             _               _                    |
#   |          | (_)___| |_       ___| |__   ___  ___| | _____             |
#   |          | | / __| __|____ / __| '_ \ / _ \/ __| |/ / __|            |
#   |          | | \__ \ ||_____| (__| | | |  __/ (__|   <\__ \            |
#   |          |_|_|___/\__|     \___|_| |_|\___|\___|_|\_\___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'

import cmk.man_pages as man_pages
import cmk_base.checks as checks

def mode_list_checks():
    all_check_manuals = man_pages.all_man_pages()

    checks_sorted = checks.check_info.items() + \
       [ ("check_" + name, entry) for (name, entry) in checks.active_check_info.items() ]
    checks_sorted.sort()
    for check_type, check in checks_sorted:
        man_filename = all_check_manuals.get(check_type)
        try:
            if 'command_line' in check:
                what = 'active'
                ty_color = tty.blue
            elif checks.is_snmp_check(check_type):
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
                  (check_type, what, title))
        except Exception, e:
            console.error("ERROR in check_type %s: %s\n" % (check_type, e))


modes.register(Mode(
    long_option="list-checks",
    short_option="L",
    handler_function=mode_list_checks,
    needs_config=False,
    short_help="List all available check types",
))

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
    dir = 1
    fil = 2

    paths = [
        ( cmk.paths.modules_dir,                 dir, inst, "Main components of check_mk"),
        ( cmk.paths.checks_dir,                  dir, inst, "Checks"),
        ( cmk.paths.notifications_dir,           dir, inst, "Notification scripts"),
        ( cmk.paths.inventory_dir,               dir, inst, "Inventory plugins"),
        ( cmk.paths.agents_dir,                  dir, inst, "Agents for operating systems"),
        ( cmk.paths.doc_dir,                     dir, inst, "Documentation files"),
        ( cmk.paths.web_dir,                     dir, inst, "Check_MK's web pages"),
        ( cmk.paths.check_manpages_dir,          dir, inst, "Check manpages (for check_mk -M)"),
        ( cmk.paths.lib_dir,                     dir, inst, "Binary plugins (architecture specific)"),
        ( cmk.paths.pnp_templates_dir,           dir, inst, "Templates for PNP4Nagios"),
    ]
    if config.monitoring_core == "nagios":
        paths += [
            ( cmk.paths.nagios_startscript,          fil, inst, "Startscript for Nagios daemon"),
            ( cmk.paths.nagios_binary,               fil, inst, "Path to Nagios executable"),
            ( cmk.paths.nagios_config_file,          fil, conf, "Main configuration file of Nagios"),
            ( cmk.paths.nagios_conf_dir,             dir, conf, "Directory where Nagios reads all *.cfg files"),
            ( cmk.paths.nagios_objects_file,         fil, data, "File into which Nagios configuration is written"),
            ( cmk.paths.nagios_status_file,          fil, data, "Path to Nagios status.dat"),
            ( cmk.paths.nagios_command_pipe_path,    fil, pipe, "Nagios' command pipe"),
            ( cmk.paths.check_result_path,           fil, pipe, "Nagios' check results directory"),
        ]

    paths += [
        ( cmk.paths.default_config_dir,          dir, conf, "Directory that contains main.mk"),
        ( cmk.paths.check_mk_config_dir,         dir, conf, "Directory containing further *.mk files"),
        ( cmk.paths.apache_config_dir,           dir, conf, "Directory where Apache reads all config files"),
        ( cmk.paths.htpasswd_file,               fil, conf, "Users/Passwords for HTTP basic authentication"),

        ( cmk.paths.var_dir,                     dir, data, "Base working directory for variable data"),
        ( cmk.paths.autochecks_dir,              dir, data, "Checks found by inventory"),
        ( cmk.paths.precompiled_hostchecks_dir,  dir, data, "Precompiled host checks"),
        ( cmk.paths.snmpwalks_dir,               dir, data, "Stored snmpwalks (output of --snmpwalk)"),
        ( cmk.paths.counters_dir,                dir, data, "Current state of performance counters"),
        ( cmk.paths.tcp_cache_dir,               dir, data, "Cached output from agents"),
        ( cmk.paths.logwatch_dir,                dir, data, "Unacknowledged logfiles of logwatch extension"),
        ( cmk.paths.livestatus_unix_socket,     fil, pipe, "Socket of Check_MK's livestatus module"),

        ( cmk.paths.local_checks_dir,           dir, local, "Locally installed checks"),
        ( cmk.paths.local_notifications_dir,    dir, local, "Locally installed notification scripts"),
        ( cmk.paths.local_inventory_dir,        dir, local, "Locally installed inventory plugins"),
        ( cmk.paths.local_check_manpages_dir,   dir, local, "Locally installed check man pages"),
        ( cmk.paths.local_agents_dir,           dir, local, "Locally installed agents and plugins"),
        ( cmk.paths.local_web_dir,              dir, local, "Locally installed Multisite addons"),
        ( cmk.paths.local_pnp_templates_dir,    dir, local, "Locally installed PNP templates"),
        ( cmk.paths.local_doc_dir,              dir, local, "Locally installed documentation"),
        ( cmk.paths.local_locale_dir,           dir, local, "Locally installed localizations"),
    ]

    def show_paths(title, t):
        if t != inst:
            console.output("\n")
        console.output(tty.bold + title + tty.normal + "\n")
        for path, filedir, typp, descr in paths:
            if typp == t:
                if filedir == dir:
                    path += "/"
                console.output("  %-47s: %s%s%s\n" %
                    (descr, tty.bold + tty.blue, path, tty.normal))

    for title, t in [
        ( "Files copied or created during installation", inst ),
        ( "Configuration files edited by you", conf ),
        ( "Data created by Nagios/Check_MK at runtime", data ),
        ( "Sockets and pipes", pipe ),
        ( "Locally installed addons", local ),
        ]:
        show_paths(title, t)

modes.register(Mode(
    long_option="paths",
    handler_function=mode_paths,
    needs_config=False,
    short_help="List all pathnames and directories",
))

#.
#   .--donate--------------------------------------------------------------.
#   |                       _                   _                          |
#   |                    __| | ___  _ __   __ _| |_ ___                    |
#   |                   / _` |/ _ \| '_ \ / _` | __/ _ \                   |
#   |                  | (_| | (_) | | | | (_| | ||  __/                   |
#   |                   \__,_|\___/|_| |_|\__,_|\__\___|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

def mode_donate():
    import cmk_base.donate
    cmk_base.donate.do_donation()

modes.register(Mode(
    long_option="donate",
    handler_function=mode_donate,
    short_help="Email data of configured hosts to MK",
    long_help=[
        "This is for those who decided to help the Check_MK project "
        "by donating live host data. It tars the cached agent data of "
        "those host which are configured in main.mk:donation_hosts and sends "
        "them via email to donatehosts@mathias-kettner.de. The host data "
        "is then publicly available for others and can be used for setting "
        "up demo sites, implementing checks and so on.",

        "Do this only with test data from test hosts - not with productive "
        "data! By donating real-live host data you help others trying out "
        "Check_MK and developing checks by donating hosts. This is completely "
        "voluntary and turned off by default."
    ],
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
    import cmk_base.backup
    cmk_base.backup.do_backup(*args)

modes.register(Mode(
    long_option="backup",
    handler_function=mode_backup,
    arguments=1,
    argument_descr="BACKUPFILE.tar.gz",
    short_help="make backup of configuration and data",
    long_help=[
        "Saves all configuration and runtime data to a gzip "
        "compressed tar file.",
    ],
))


def mode_restore(*args):
    import cmk_base.backup
    cmk_base.backup.do_restore(*args)

modes.register(Mode(
    long_option="restore",
    handler_function=mode_restore,
    arguments=1,
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
    import cmk_base.packaging
    cmk_base.packaging.do_packaging(*args)

modes.register(Mode(
    long_option="package",
    short_option="P",
    handler_function=mode_packaging,
    arguments=True,
    argument_descr="COMMAND",
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
    import cmk_base.localize
    cmk_base.localize.do_localize(*args)

modes.register(Mode(
    long_option="localize",
    handler_function=mode_localize,
    needs_config=False,
    arguments=True,
    argument_descr="COMMAND",
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

modes.register(Mode(
    long_option="config-check",
    short_option="X",
    handler_function=lambda: None,
    short_help=None,
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
    import cmk_base.ip_lookup
    cmk_base.ip_lookup.update_dns_cache()

modes.register(Mode(
    long_option="update-dns-cache",
    handler_function=mode_update_dns_cache,
    short_help="Update IP address lookup cache",
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
    import cmk_base.parent_scan
    config.load(exclude_parents_mk=True)

    if "procs" in options:
        config.max_num_processes = options["procs"]

    cmk_base.parent_scan.do_scan_parents(args)

modes.register(Mode(
    long_option="scan-parents",
    handler_function=mode_scan_parents,
    needs_config=False,
    arguments=True,
    argument_descr="[HOST1 HOST2...]",
    short_help="Autoscan parents, create conf.d/parents.mk",
    long_help=[
        "Uses traceroute in order to automatically detect hosts's parents. "
        "It creates the file conf.d/parents.mk which "
        "defines gateway hosts and parent declarations.",
    ],
    sub_options=[
        ("procs", "N", int, "Start up to N processes in parallel. Defaults to 50."),
    ]
))

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


modes.register(Mode(
    long_option="version",
    short_option="V",
    handler_function=mode_version,
    short_help="Print the version of Check_MK",
    needs_config=False,
))
