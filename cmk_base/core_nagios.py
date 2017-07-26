#!/usr/bin/python
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

"""Code for support of Nagios (and compatible) cores"""

import os
import subprocess
import sys
import py_compile

import cmk.paths
import cmk.tty as tty
from cmk.exceptions import MKGeneralException

import cmk_base.utils
import cmk_base.console as console
import cmk_base.config as config
import cmk_base.checks as checks
import cmk_base.rulesets as rulesets
import cmk_base.core_config as core_config
import cmk_base.ip_lookup as ip_lookup


def do_check_nagiosconfig():
    command = [ cmk.paths.nagios_binary, "-vp", cmk.paths.nagios_config_file ]
    console.verbose("Running '%s'\n" % subprocess.list2cmdline(command))
    console.output("Validating Nagios configuration...")

    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         close_fds=True)
    exit_status = p.wait()
    if not exit_status:
        console.output(tty.ok + "\n")
        return True
    else:
        console.output("ERROR:\n")
        console.output(p.stdout.read(), stream=sys.stderr)
        return False


#   .--Create config-------------------------------------------------------.
#   |      ____                _                          __ _             |
#   |     / ___|_ __ ___  __ _| |_ ___    ___ ___  _ __  / _(_) __ _       |
#   |    | |   | '__/ _ \/ _` | __/ _ \  / __/ _ \| '_ \| |_| |/ _` |      |
#   |    | |___| | |  __/ (_| | ||  __/ | (_| (_) | | | |  _| | (_| |      |
#   |     \____|_|  \___|\__,_|\__\___|  \___\___/|_| |_|_| |_|\__, |      |
#   |                                                          |___/       |
#   +----------------------------------------------------------------------+
#   |  Create a configuration file for Nagios core with hosts + services   |
#   '----------------------------------------------------------------------'

# TODO: Move to modes?
def do_output_nagios_conf(args):
    if len(args) == 0:
        args = None
    create_config(sys.stdout, args)


def create_config(outfile = sys.stdout, hostnames = None):
    global hostgroups_to_define
    hostgroups_to_define = set([])
    global servicegroups_to_define
    servicegroups_to_define = set([])
    global contactgroups_to_define
    contactgroups_to_define = set([])
    global checknames_to_define
    checknames_to_define = set([])
    global active_checks_to_define
    active_checks_to_define = set([])
    global custom_commands_to_define
    custom_commands_to_define = set([])
    global hostcheck_commands_to_define
    hostcheck_commands_to_define = []

    if config.host_notification_periods != []:
        core_config.warning("host_notification_periods is not longer supported. Please use extra_host_conf['notification_period'] instead.")

    if config.service_notification_periods != []:
        core_config.warning("service_notification_periods is not longer supported. Please use extra_service_conf['notification_period'] instead.")

    # Map service_period to _SERVICE_PERIOD. This field das not exist in Nagios/Icinga.
    # The CMC has this field natively.
    if "service_period" in config.extra_host_conf:
        config.extra_host_conf["_SERVICE_PERIOD"] = config.extra_host_conf["service_period"]
        del config.extra_host_conf["service_period"]
    if "service_period" in config.extra_service_conf:
        config.extra_service_conf["_SERVICE_PERIOD"] = config.extra_service_conf["service_period"]
        del config.extra_service_conf["service_period"]

    _output_conf_header(outfile)
    if hostnames == None:
        hostnames = config.all_active_hosts()

    for hostname in hostnames:
        _create_nagios_config_host(outfile, hostname)

    _create_nagios_config_contacts(outfile, hostnames)
    _create_nagios_config_hostgroups(outfile)
    _create_nagios_config_servicegroups(outfile)
    _create_nagios_config_contactgroups(outfile)
    _create_nagios_config_commands(outfile)
    _create_nagios_config_timeperiods(outfile)

    if config.extra_nagios_conf:
        outfile.write("\n# extra_nagios_conf\n\n")
        outfile.write(config.extra_nagios_conf)


def _output_conf_header(outfile):
    outfile.write("""#
# Created by Check_MK. Do not edit.
#

""")


def _create_nagios_config_host(outfile, hostname):
    outfile.write("\n# ----------------------------------------------------\n")
    outfile.write("# %s\n" % hostname)
    outfile.write("# ----------------------------------------------------\n")
    host_attrs = core_config.get_host_attributes(hostname, config.tags_of_host(hostname))
    if config.generate_hostconf:
        _create_nagios_hostdefs(outfile, hostname, host_attrs)
    _create_nagios_servicedefs(outfile, hostname, host_attrs)


def _create_nagios_hostdefs(outfile, hostname, attrs):
    is_clust = config.is_cluster(hostname)

    ip = attrs["address"]

    if is_clust:
        nodes = core_config.get_cluster_nodes_for_config(hostname)
        attrs.update(core_config.get_cluster_attributes(hostname, nodes))

    #   _
    #  / |
    #  | |
    #  | |
    #  |_|    1. normal, physical hosts

    alias = hostname
    outfile.write("\ndefine host {\n")
    outfile.write("  host_name\t\t\t%s\n" % hostname)
    outfile.write("  use\t\t\t\t%s\n" % (is_clust and config.cluster_template or config.host_template))
    outfile.write("  address\t\t\t%s\n" % (ip and cmk_base.utils.make_utf8(ip) or core_config.fallback_ip_for(hostname)))

    # Add custom macros
    for key, value in attrs.items():
        if key[0] == '_':
            tabs = len(key) > 13 and "\t\t" or "\t\t\t"
            outfile.write("  %s%s%s\n" % (key, tabs, value))

    # Host check command might differ from default
    command = core_config.host_check_command(hostname, ip, is_clust,
                        hostcheck_commands_to_define, custom_commands_to_define)
    if command:
        outfile.write("  check_command\t\t\t%s\n" % command)

    # Host groups: If the host has no hostgroups it gets the default
    # hostgroup (Nagios requires each host to be member of at least on
    # group.
    hgs = config.hostgroups_of(hostname)
    hostgroups = ",".join(hgs)
    if len(hgs) == 0:
        hostgroups = config.default_host_group
        hostgroups_to_define.add(config.default_host_group)
    elif config.define_hostgroups:
        hostgroups_to_define.update(hgs)
    outfile.write("  hostgroups\t\t\t%s\n" % cmk_base.utils.make_utf8(hostgroups))

    # Contact groups
    cgrs = config.contactgroups_of(hostname)
    if len(cgrs) > 0:
        outfile.write("  contact_groups\t\t%s\n" % cmk_base.utils.make_utf8(",".join(cgrs)))
        contactgroups_to_define.update(cgrs)

    if not is_clust:
        # Parents for non-clusters

        # Get parents manually defined via extra_host_conf["parents"]. Only honor
        # variable "parents" and implicit parents if this setting is empty
        extra_conf_parents = rulesets.host_extra_conf(hostname, config.extra_host_conf.get("parents", []))

        if not extra_conf_parents:
            parents_list = config.parents_of(hostname)
            if parents_list:
                outfile.write("  parents\t\t\t%s\n" % (",".join(parents_list)))

    elif is_clust:
        # Special handling of clusters
        alias = "cluster of %s" % ", ".join(nodes)
        outfile.write("  parents\t\t\t%s\n" % ",".join(nodes))

    # Output alias, but only if it's not defined in extra_host_conf
    alias = config.alias_of(hostname, None)
    if alias == None:
        outfile.write("  alias\t\t\t\t%s\n" % alias)
    else:
        alias = cmk_base.utils.make_utf8(alias)

    # Custom configuration last -> user may override all other values
    outfile.write(cmk_base.utils.make_utf8(_extra_host_conf_of(hostname, exclude=["parents"] if is_clust else [])))

    outfile.write("}\n")
    outfile.write("\n")


def _create_nagios_servicedefs(outfile, hostname, host_attrs):
    import cmk_base.check_table as check_table

    #   _____
    #  |___ /
    #    |_ \
    #   ___) |
    #  |____/   3. Services


    def do_omit_service(hostname, description):
        if config.service_ignored(hostname, None, description):
            return True
        if hostname != config.host_of_clustered_service(hostname, description):
            return True
        return False

    def get_dependencies(hostname,servicedesc):
        result = ""
        for dep in check_table.service_deps(hostname, servicedesc):
            result += """
define servicedependency {
  use\t\t\t\t%s
  host_name\t\t\t%s
  service_description\t%s
  dependent_host_name\t%s
  dependent_service_description %s
}\n
""" % (config.service_dependency_template, hostname, dep, hostname, servicedesc)

        return result

    host_checks = check_table.get_check_table(hostname, remove_duplicates=True).items()
    host_checks.sort() # Create deterministic order
    have_at_least_one_service = False
    used_descriptions = {}
    for ((checkname, item), (params, description, deps)) in host_checks:
        if checkname not in checks.check_info:
            continue # simply ignore missing checks

        description = config.get_final_service_description(hostname, description)
        # Make sure, the service description is unique on this host
        if description in used_descriptions:
            cn, it = used_descriptions[description]
            core_config.warning(
                    "ERROR: Duplicate service description '%s' for host '%s'!\n"
                    " - 1st occurrance: checktype = %s, item = %r\n"
                    " - 2nd occurrance: checktype = %s, item = %r\n" %
                    (description, hostname, cn, it, checkname, item))
            continue

        else:
            used_descriptions[description] = ( checkname, item )
        if checks.check_info[checkname].get("has_perfdata", False):
            template = config.passive_service_template_perf
        else:
            template = config.passive_service_template

        # Services Dependencies
        for dep in deps:
            outfile.write("define servicedependency {\n"
                         "    use\t\t\t\t%s\n"
                         "    host_name\t\t\t%s\n"
                         "    service_description\t%s\n"
                         "    dependent_host_name\t%s\n"
                         "    dependent_service_description %s\n"
                         "}\n\n" % (config.service_dependency_template, hostname, dep, hostname, description))


        # Add the check interval of either the Check_MK service or
        # (if configured) the snmp_check_interval for snmp based checks
        check_interval = 1 # default hardcoded interval
        # Customized interval of Check_MK service
        values = rulesets.service_extra_conf(hostname, "Check_MK", config.extra_service_conf.get('check_interval', []))
        if values:
            try:
                check_interval = int(values[0])
            except:
                check_interval = float(values[0])
        value = config.check_interval_of(hostname, checkname)
        if value is not None:
            check_interval = value

        # Add custom user icons and actions
        actions = core_config.icons_and_actions_of('service', hostname, description, checkname, params)
        action_cfg = actions and '  _ACTIONS\t\t\t%s\n' % ','.join(actions) or ''

        outfile.write("""define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
  service_description\t\t%s
  check_interval\t\t%d
%s%s  check_command\t\t\tcheck_mk-%s
}

""" % ( template, hostname, description.encode("utf-8"), check_interval,
        _extra_service_conf_of(hostname, description), action_cfg, checkname ))

        checknames_to_define.add(checkname)
        have_at_least_one_service = True

    # Active check for check_mk
    if have_at_least_one_service:
        outfile.write("""
# Active checks

define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
%s  service_description\t\tCheck_MK
}
""" % (config.active_service_template, hostname, _extra_service_conf_of(hostname, "Check_MK")))

    # legacy checks via legacy_checks
    legchecks = rulesets.host_extra_conf(hostname, config.legacy_checks)
    if len(legchecks) > 0:
        outfile.write("\n\n# Legacy checks\n")
    for command, description, has_perfdata in legchecks:
        description = config.get_final_service_description(hostname, description)
        if do_omit_service(hostname, description):
            continue

        if description in used_descriptions:
            cn, it = used_descriptions[description]
            core_config.warning(
                    "ERROR: Duplicate service description (legacy check) '%s' for host '%s'!\n"
                    " - 1st occurrance: checktype = %s, item = %r\n"
                    " - 2nd occurrance: checktype = legacy(%s), item = None\n" %
                    (description, hostname, cn, it, command))
            continue

        else:
            used_descriptions[description] = ( "legacy(" + command + ")", description )

        extraconf = _extra_service_conf_of(hostname, description)
        if has_perfdata:
            template = "check_mk_perf,"
        else:
            template = ""
        outfile.write("""
define service {
  use\t\t\t\t%scheck_mk_default
  host_name\t\t\t%s
  service_description\t\t%s
  check_command\t\t\t%s
  active_checks_enabled\t\t1
%s}
""" % (template, hostname, cmk_base.utils.make_utf8(description), _simulate_command(command), extraconf))

        # write service dependencies for legacy checks
        outfile.write(get_dependencies(hostname,description))

    # legacy checks via active_checks
    actchecks = []
    for acttype, rules in config.active_checks.items():
        entries = rulesets.host_extra_conf(hostname, rules)
        if entries:
            # Skip Check_MK HW/SW Inventory for all ping hosts, even when the user has enabled
            # the inventory for ping only hosts
            if acttype == "cmk_inv" and config.is_ping_host(hostname):
                continue

            active_checks_to_define.add(acttype)
            act_info = checks.active_check_info[acttype]
            for params in entries:
                actchecks.append((acttype, act_info, params))

    if actchecks:
        outfile.write("\n\n# Active checks\n")
        for acttype, act_info, params in actchecks:
            # Make hostname available as global variable in argument functions
            checks.set_hostname(hostname)

            has_perfdata = act_info.get('has_perfdata', False)
            description = core_config.active_check_service_description(hostname, act_info, params)

            if do_omit_service(hostname, description):
                continue

            # compute argument, and quote ! and \ for Nagios
            args = core_config.active_check_arguments(hostname, description,
                                          act_info["argument_function"](params)).replace("\\", "\\\\").replace("!", "\\!")

            if description in used_descriptions:
                cn, it = used_descriptions[description]
                # If we have the same active check again with the same description,
                # then we do not regard this as an error, but simply ignore the
                # second one. That way one can override a check with other settings.
                if cn == "active(%s)" % acttype:
                    continue

                core_config.warning(
                        "ERROR: Duplicate service description (active check) '%s' for host '%s'!\n"
                        " - 1st occurrance: checktype = %s, item = %r\n"
                        " - 2nd occurrance: checktype = active(%s), item = None\n" %
                        (description, hostname, cn, it, acttype))
                continue

            else:
                used_descriptions[description] = ( "active(" + acttype + ")", description )

            template = has_perfdata and "check_mk_perf," or ""
            extraconf = _extra_service_conf_of(hostname, description)

            if host_attrs["address"] in [ "0.0.0.0", "::" ]:
                command_name = "check-mk-custom"
                command = command_name + "!echo \"Failed to lookup IP address and no explicit IP address configured\" && exit 3"
                custom_commands_to_define.add(command_name)
            else:
                command = "check_mk_active-%s!%s" % (acttype, args)

            outfile.write("""
define service {
  use\t\t\t\t%scheck_mk_default
  host_name\t\t\t%s
  service_description\t\t%s
  check_command\t\t\t%s
  active_checks_enabled\t\t1
%s}
""" % (template, hostname, cmk_base.utils.make_utf8(description), cmk_base.utils.make_utf8(_simulate_command(command)), extraconf))

            # write service dependencies for active checks
            outfile.write(get_dependencies(hostname,description))

    # Legacy checks via custom_checks
    custchecks = rulesets.host_extra_conf(hostname, config.custom_checks)
    if custchecks:
        outfile.write("\n\n# Custom checks\n")
        for entry in custchecks:
            # entries are dicts with the following keys:
            # "service_description"        Service description to use
            # "command_line"  (optional)   Unix command line for executing the check
            #                              If this is missing, we create a passive check
            # "command_name"  (optional)   Name of Monitoring command to define. If missing,
            #                              we use "check-mk-custom"
            # "has_perfdata"  (optional)   If present and True, we activate perf_data
            description = config.get_final_service_description(hostname, entry["service_description"])
            has_perfdata = entry.get("has_perfdata", False)
            command_name = entry.get("command_name", "check-mk-custom")
            command_line = entry.get("command_line", "")

            if do_omit_service(hostname, description):
                continue

            if command_line:
                command_line = core_config.autodetect_plugin(command_line).replace("\\", "\\\\").replace("!", "\\!")

            if "freshness" in entry:
                freshness = "  check_freshness\t\t1\n" + \
                            "  freshness_threshold\t\t%d\n" % (60 * entry["freshness"]["interval"])
                command_line = "echo %s && exit %d" % (
                       _quote_nagios_string(entry["freshness"]["output"]), entry["freshness"]["state"])
            else:
                freshness = ""

            custom_commands_to_define.add(command_name)

            if description in used_descriptions:
                cn, it = used_descriptions[description]
                # If we have the same active check again with the same description,
                # then we do not regard this as an error, but simply ignore the
                # second one.
                if cn == "custom(%s)" % command_name:
                    continue
                core_config.warning(
                        "ERROR: Duplicate service description (custom check) '%s' for host '%s'!\n"
                        " - 1st occurrance: checktype = %s, item = %r\n"
                        " - 2nd occurrance: checktype = custom(%s), item = %r\n" %
                        (description, hostname, cn, it, command_name, description))
                continue
            else:
                used_descriptions[description] = ( "custom(%s)" % command_name, description )

            template = has_perfdata and "check_mk_perf," or ""
            extraconf = _extra_service_conf_of(hostname, description)
            command = "%s!%s" % (command_name, command_line)
            outfile.write("""
define service {
  use\t\t\t\t%scheck_mk_default
  host_name\t\t\t%s
  service_description\t\t%s
  check_command\t\t\t%s
  active_checks_enabled\t\t%d
%s%s}
""" % (template, hostname, cmk_base.utils.make_utf8(description), _simulate_command(command),
       (command_line and not freshness) and 1 or 0, extraconf, freshness))

            # write service dependencies for custom checks
            outfile.write(get_dependencies(hostname,description))

    # FIXME: Remove old name one day
    service_discovery_name = 'Check_MK inventory'
    if 'cmk-inventory' in config.use_new_descriptions_for:
        service_discovery_name = 'Check_MK Discovery'

    import cmk_base.discovery as discovery
    params = discovery.discovery_check_parameters(hostname) or \
             discovery.default_discovery_check_parameters()

    # Inventory checks - if user has configured them.
    if params["check_interval"] \
        and not config.service_ignored(hostname, None, service_discovery_name) \
        and not "ping" in config.tags_of_host(hostname): # FIXME/TODO: Why not user is_ping_host()?
        outfile.write("""
define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
  normal_check_interval\t\t%d
  retry_check_interval\t\t%d
%s  service_description\t\t%s
}
""" % (config.inventory_check_template, hostname, params["check_interval"],
       params["check_interval"],
       _extra_service_conf_of(hostname, service_discovery_name),
       service_discovery_name))

        if have_at_least_one_service:
            outfile.write("""
define servicedependency {
  use\t\t\t\t%s
  host_name\t\t\t%s
  service_description\t\tCheck_MK
  dependent_host_name\t\t%s
  dependent_service_description\t%s
}
""" % (config.service_dependency_template, hostname, hostname, service_discovery_name))

    # No check_mk service, no legacy service -> create PING service
    if not have_at_least_one_service and not legchecks and not actchecks and not custchecks:
        _add_ping_service(outfile, hostname, host_attrs["address"], config.is_ipv6_primary(hostname) and 6 or 4,
                         "PING", host_attrs.get("_NODEIPS"))

    if config.is_ipv4v6_host(hostname):
        if config.is_ipv6_primary(hostname):
            _add_ping_service(outfile, hostname, host_attrs["_ADDRESS_4"], 4,
                             "PING IPv4", host_attrs.get("_NODEIPS_4"))
        else:
            _add_ping_service(outfile, hostname, host_attrs["_ADDRESS_6"], 6,
                             "PING IPv6", host_attrs.get("_NODEIPS_6"))


def _add_ping_service(outfile, hostname, ipaddress, family, descr, node_ips):
    arguments = core_config.check_icmp_arguments_of(hostname, family=family)

    ping_command = 'check-mk-ping'
    if config.is_cluster(hostname):
        arguments += ' -m 1 ' + node_ips
    else:
        arguments += ' ' + ipaddress

    outfile.write("""
define service {
  use\t\t\t\t%s
  service_description\t\t%s
  check_command\t\t\t%s!%s
%s  host_name\t\t\t%s
}

""" % (config.pingonly_template, descr, ping_command, arguments, _extra_service_conf_of(hostname, descr), hostname))


def _simulate_command(command):
    if config.simulation_mode:
        custom_commands_to_define.add("check-mk-simulation")
        return "check-mk-simulation!echo 'Simulation mode - cannot execute real check'"
    else:
        return command


def _create_nagios_config_hostgroups(outfile):
    if config.define_hostgroups:
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Host groups (controlled by define_hostgroups)\n")
        outfile.write("# ------------------------------------------------------------\n")
        hgs = list(hostgroups_to_define)
        hgs.sort()
        for hg in hgs:
            try:
                alias = config.define_hostgroups[hg]
            except:
                alias = hg
            outfile.write("""
define hostgroup {
  hostgroup_name\t\t%s
  alias\t\t\t\t%s
}
""" % (cmk_base.utils.make_utf8(hg), cmk_base.utils.make_utf8(alias)))

    # No creation of host groups but we need to define
    # default host group
    elif config.default_host_group in hostgroups_to_define:
        outfile.write("""
define hostgroup {
  hostgroup_name\t\t%s
  alias\t\t\t\tCheck_MK default hostgroup
}
""" % config.default_host_group)


def _create_nagios_config_servicegroups(outfile):
    if config.define_servicegroups:
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Service groups (controlled by define_servicegroups)\n")
        outfile.write("# ------------------------------------------------------------\n")
        sgs = list(servicegroups_to_define)
        sgs.sort()
        for sg in sgs:
            try:
                alias = config.define_servicegroups[sg]
            except:
                alias = sg
            outfile.write("""
define servicegroup {
  servicegroup_name\t\t%s
  alias\t\t\t\t%s
}
""" % (cmk_base.utils.make_utf8(sg), cmk_base.utils.make_utf8(alias)))

def _create_nagios_config_contactgroups(outfile):
    if config.define_contactgroups == False:
        return

    cgs = list(contactgroups_to_define)
    if not cgs:
        return

    outfile.write("\n# ------------------------------------------------------------\n")
    outfile.write("# Contact groups (controlled by define_contactgroups)\n")
    outfile.write("# ------------------------------------------------------------\n\n")
    for name in sorted(cgs):
        if type(config.define_contactgroups) == dict:
            alias = config.define_contactgroups.get(name, name)
        else:
            alias = name

        outfile.write("\ndefine contactgroup {\n"
                "  contactgroup_name\t\t%s\n"
                "  alias\t\t\t\t%s\n" % (cmk_base.utils.make_utf8(name), cmk_base.utils.make_utf8(alias)))

        members = config.contactgroup_members.get(name)
        if members:
            outfile.write("  members\t\t\t%s\n" % ",".join(members))

        outfile.write("}\n")


def _create_nagios_config_commands(outfile):
    if config.generate_dummy_commands:
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Dummy check commands and active check commands\n")
        outfile.write("# ------------------------------------------------------------\n\n")
        for checkname in checknames_to_define:
            outfile.write("""define command {
  command_name\t\t\tcheck_mk-%s
  command_line\t\t\t%s
}

""" % ( checkname, config.dummy_check_commandline ))

    # active_checks
    for acttype in active_checks_to_define:
        act_info = checks.active_check_info[acttype]
        outfile.write("""define command {
  command_name\t\t\tcheck_mk_active-%s
  command_line\t\t\t%s
}

""" % ( acttype, act_info["command_line"]))

    # custom_checks
    for command_name in custom_commands_to_define:
        outfile.write("""define command {
  command_name\t\t\t%s
  command_line\t\t\t$ARG1$
}

""" % command_name)

    # custom host checks
    for command_name, command_line in hostcheck_commands_to_define:
        outfile.write("""define command {
  command_name\t\t\t%s
  command_line\t\t\t%s
}

""" % (command_name, command_line))


def _create_nagios_config_timeperiods(outfile):
    if len(config.timeperiods) > 0:
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Timeperiod definitions (controlled by variable 'timeperiods')\n")
        outfile.write("# ------------------------------------------------------------\n\n")
        tpnames = config.timeperiods.keys()
        tpnames.sort()
        for name in tpnames:
            tp = config.timeperiods[name]
            outfile.write("define timeperiod {\n  timeperiod_name\t\t%s\n" % name)
            if "alias" in tp:
                outfile.write("  alias\t\t\t\t%s\n" % cmk_base.utils.make_utf8(tp["alias"]))
            for key, value in tp.items():
                if key not in [ "alias", "exclude" ]:
                    times = ",".join([ ("%s-%s" % (fr, to)) for (fr, to) in value ])
                    if times:
                        outfile.write("  %-20s\t\t%s\n" % (key, times))
            if "exclude" in tp:
                outfile.write("  exclude\t\t\t%s\n" % ",".join(tp["exclude"]))
            outfile.write("}\n\n")


def _create_nagios_config_contacts(outfile, hostnames):
    if len(config.contacts) > 0:
        outfile.write("\n# ------------------------------------------------------------\n")
        outfile.write("# Contact definitions (controlled by variable 'contacts')\n")
        outfile.write("# ------------------------------------------------------------\n\n")
        cnames = config.contacts.keys()
        cnames.sort()
        for cname in cnames:
            contact = config.contacts[cname]
            # Create contact groups in nagios, even when they are empty. This is needed
            # for RBN to work correctly when using contactgroups as recipients which are
            # not assigned to any host
            contactgroups_to_define.update(contact.get("contactgroups", []))
            # If the contact is in no contact group or all of the contact groups
            # of the contact have neither hosts nor services assigned - in other
            # words if the contact is not assigned to any host or service, then
            # we do not create this contact in Nagios. It's useless and will produce
            # warnings.
            cgrs = [ cgr for cgr in contact.get("contactgroups", []) if cgr in contactgroups_to_define ]
            if not cgrs:
                continue

            outfile.write("define contact {\n  contact_name\t\t\t%s\n" % cmk_base.utils.make_utf8(cname))
            if "alias" in contact:
                outfile.write("  alias\t\t\t\t%s\n" % cmk_base.utils.make_utf8(contact["alias"]))
            if "email" in contact:
                outfile.write("  email\t\t\t\t%s\n" % cmk_base.utils.make_utf8(contact["email"]))
            if "pager" in contact:
                outfile.write("  pager\t\t\t\t%s\n" % contact["pager"])
            if config.enable_rulebased_notifications:
                not_enabled = False
            else:
                not_enabled = contact.get("notifications_enabled", True)

            for what in [ "host", "service" ]:
                no = contact.get(what + "_notification_options", "")
                if not no or not not_enabled:
                    outfile.write("  %s_notifications_enabled\t0\n" % what)
                    no = "n"
                outfile.write("  %s_notification_options\t%s\n" %
                        (what, ",".join(list(no))))
                outfile.write("  %s_notification_period\t%s\n" %
                        (what, contact.get("notification_period", "24X7")))
                outfile.write("  %s_notification_commands\t%s\n" %
                        (what, contact.get("%s_notification_commands" % what, "check-mk-notify")))
            # Add custom macros
            for macro in [ m for m in contact.keys() if m.startswith('_') ]:
                outfile.write("  %s\t%s\n" % ( macro, contact[macro] ))

            outfile.write("  contactgroups\t\t\t%s\n" % ", ".join(cgrs))
            outfile.write("}\n\n")

    if config.enable_rulebased_notifications and hostnames:
        contactgroups_to_define.add("check-mk-notify")
        outfile.write(
            "# Needed for rule based notifications\n"
            "define contact {\n"
            "  contact_name\t\t\tcheck-mk-notify\n"
            "  alias\t\t\t\tContact for rule based notifications\n"
            "  host_notification_options\td,u,r,f,s\n"
            "  service_notification_options\tu,c,w,r,f,s\n"
            "  host_notification_period\t24X7\n"
            "  service_notification_period\t24X7\n"
            "  host_notification_commands\tcheck-mk-notify\n"
            "  service_notification_commands\tcheck-mk-notify\n"
            "  contactgroups\t\t\tcheck-mk-notify\n"
            "}\n\n");


# Quote string for use in a nagios command execution.
# Please note that also quoting for ! and \ vor Nagios
# itself takes place here.
def _quote_nagios_string(s):
    return "'" + s.replace('\\', '\\\\').replace("'", "'\"'\"'").replace('!', '\\!') + "'"


def _extra_host_conf_of(hostname, exclude=None):
    if exclude == None:
        exclude = []
    return _extra_conf_of(config.extra_host_conf, hostname, None, exclude)


# Collect all extra configuration data for a service
def _extra_service_conf_of(hostname, description):
    conf = ""

    # Contact groups
    sercgr = rulesets.service_extra_conf(hostname, description, config.service_contactgroups)
    contactgroups_to_define.update(sercgr)
    if len(sercgr) > 0:
        if config.enable_rulebased_notifications:
            sercgr.append("check-mk-notify") # not nessary if not explicit groups defined
        conf += "  contact_groups\t\t" + ",".join(sercgr) + "\n"

    sergr = rulesets.service_extra_conf(hostname, description, config.service_groups)
    if len(sergr) > 0:
        conf += "  service_groups\t\t" + ",".join(sergr) + "\n"
        if config.define_servicegroups:
            servicegroups_to_define.update(sergr)
    conf += _extra_conf_of(config.extra_service_conf, hostname, description)
    return conf.encode("utf-8")


def _extra_conf_of(confdict, hostname, service, exclude=None):
    if exclude == None:
        exclude = []

    result = ""
    for key, conflist in confdict.items():
        if service != None:
            values = rulesets.service_extra_conf(hostname, service, conflist)
        else:
            values = rulesets.host_extra_conf(hostname, conflist)

        if exclude and key in exclude:
            continue

        if values:
            format = "  %-29s %s\n"
            result += format % (key, values[0])
    return result


#.
#   .--Precompile----------------------------------------------------------.
#   |          ____                                     _ _                |
#   |         |  _ \ _ __ ___  ___ ___  _ __ ___  _ __ (_) | ___           |
#   |         | |_) | '__/ _ \/ __/ _ \| '_ ` _ \| '_ \| | |/ _ \          |
#   |         |  __/| | |  __/ (_| (_) | | | | | | |_) | | |  __/          |
#   |         |_|   |_|  \___|\___\___/|_| |_| |_| .__/|_|_|\___|          |
#   |                                            |_|                       |
#   +----------------------------------------------------------------------+
#   | Precompiling creates on dedicated Python file per host, which just   |
#   | contains that code and information that is needed for executing all  |
#   | checks of that host. Also static data that cannot change during the  |
#   | normal monitoring process is being precomputed and hard coded. This  |
#   | all saves substantial CPU ressources as opposed to running Check_MK  |
#   | in adhoc mode (about 75%).                                           |
#   '----------------------------------------------------------------------'

# TODO: Move to modes
def do_precompile_hostchecks():
    console.output("Precompiling host checks...")
    precompile_hostchecks()
    console.output(tty.ok + "\n")


# Find files to be included in precompile host check for a certain
# check (for example df or mem.used). In case of checks with a period
# (subchecks) we might have to include both "mem" and "mem.used". The
# subcheck *may* be implemented in a separate file.
def _find_check_plugins(checktype):
    if '.' in checktype:
        candidates = [ checktype.split('.')[0], checktype ]
    else:
        candidates = [ checktype ]

    paths = []
    for candidate in candidates:
        filename = cmk.paths.local_checks_dir + "/" + candidate
        if os.path.exists(filename):
            paths.append(filename)
            continue

        filename = cmk.paths.checks_dir + "/" + candidate
        if os.path.exists(filename):
            paths.append(filename)

    return paths


def precompile_hostchecks():
    if not os.path.exists(cmk.paths.precompiled_hostchecks_dir):
        os.makedirs(cmk.paths.precompiled_hostchecks_dir)
    for host in config.all_active_hosts():
        try:
            _precompile_hostcheck(host)
        except Exception, e:
            if cmk.debug.enabled():
                raise
            console.error("Error precompiling checks for host %s: %s\n" % (host, e))
            sys.exit(5)


# read python file and strip comments
g_stripped_file_cache = {}
def stripped_python_file(filename):
    if filename in g_stripped_file_cache:
        return g_stripped_file_cache[filename]
    a = ""
    for line in file(filename):
        l = line.strip()
        if l == "" or l[0] != '#':
            a += line # not stripped line because of indentation!
    g_stripped_file_cache[filename] = a
    return a


def _precompile_hostcheck(hostname):
    import cmk_base.check_table as check_table

    console.verbose("%s%s%-16s%s:", tty.bold, tty.blue, hostname, tty.normal, stream=sys.stderr)

    compiled_filename = cmk.paths.precompiled_hostchecks_dir + "/" + hostname
    source_filename = compiled_filename + ".py"
    for fname in [ compiled_filename, source_filename ]:
        try:
            os.remove(fname)
        except:
            pass

    # check table, enriched with addition precompiled information.
    check_table = check_table.get_precompiled_check_table(hostname)
    if not check_table:
        console.verbose("(no Check_MK checks)\n")
        return

    output = file(source_filename + ".new", "w")
    output.write("#!/usr/bin/python\n")
    output.write("# encoding: utf-8\n\n")

    output.write("import sys\n")
    output.write("import cmk.log\n")
    output.write("import cmk.debug\n")
    output.write("from cmk.exceptions import MKTerminate\n")
    output.write("\n")
    output.write("import cmk_base.utils\n")
    output.write("import cmk_base.checks as checks\n")
    output.write("import cmk_base.config as config\n")
    output.write("import cmk_base.console as console\n")
    output.write("import cmk_base.checking as checking\n")
    output.write("import cmk_base.ip_lookup as ip_lookup\n")

    # Self-compile: replace symlink with precompiled python-code, if
    # we are run for the first time
    if config.delay_precompile:
        output.write("""
import os
if os.path.islink(%(dst)r):
    import py_compile
    os.remove(%(dst)r)
    py_compile.compile(%(src)r, %(dst)r, %(dst)r, True)
    os.chmod(%(dst)r, 0755)

""" % { "src" : source_filename, "dst" : compiled_filename })

    # Remove precompiled directory from sys.path. Leaving it in the path
    # makes problems when host names (name of precompiled files) are equal
    # to python module names like "random"
    output.write("sys.path.pop(0)\n")

    # Register default Check_MK signal handler
    output.write("cmk_base.utils.register_sigint_handler()\n")

    # initialize global variables
    output.write("""
# very simple commandline parsing: only -v (once or twice) and -d are supported

cmk.log.setup_console_logging()
logger = cmk.log.get_logger("base")

# TODO: This is not really good parsing, because it not cares about syntax like e.g. "-nv".
#       The later regular argument parsing is handling this correctly. Try to clean this up.
cmk.log.set_verbosity(verbosity=len([ a for a in sys.argv if a in [ "-v", "--verbose"] ]))

if '-d' in sys.argv:
    cmk.debug.enable()

""")

    # Do we need to load the SNMP module? This is the case, if the host
    # has at least one SNMP based check. Also collect the needed check
    # types and sections.
    needed_check_types = set([])
    needed_sections = set([])
    for check_type, _unused_item, _unused_param, descr in check_table:
        if check_type not in checks.check_info:
            sys.stderr.write('Warning: Ignoring missing check %s.\n' % check_type)
            continue
        if checks.check_info[check_type].get("extra_sections"):
            for section in checks.check_info[check_type]["extra_sections"]:
                if section in checks.check_info:
                    needed_check_types.add(section)
                needed_sections.add(section.split(".")[0])

        needed_sections.add(check_type.split(".")[0])
        needed_check_types.add(check_type)

    # check info table
    # We need to include all those plugins that are referenced in the host's
    # check table
    filenames = []
    for check_type in needed_check_types:
        basename = check_type.split(".")[0]
        # Add library files needed by check (also look in local)
        for lib in set(checks.check_includes.get(basename, [])):
            if os.path.exists(cmk.paths.local_checks_dir + "/" + lib):
                to_add = cmk.paths.local_checks_dir + "/" + lib
            else:
                to_add = cmk.paths.checks_dir + "/" + lib

            if to_add not in filenames:
                filenames.append(to_add)

        # Now add check file(s) itself
        paths = _find_check_plugins(check_type)
        if not paths:
            raise MKGeneralException("Cannot find check file %s needed for check type %s" % \
                                     (basename, check_type))

        for path in paths:
            if path not in filenames:
                filenames.append(path)

    output.write("checks.load_checks(%r)\n" % filenames)
    for filename in filenames:
        console.verbose(" %s%s%s", tty.green, filename.split('/')[-1], tty.normal, stream=sys.stderr)

    output.write("config.load(validate_hosts=False)\n")

    # handling of clusters
    if config.is_cluster(hostname):
        cluster_nodes = config.nodes_of(hostname)
        output.write("clusters = { %r : %r }\n" %
                     (hostname, cluster_nodes))
        output.write("def is_cluster(hostname):\n    return True\n\n")

        nodes_of_map = {hostname: cluster_nodes}
        for node in config.nodes_of(hostname):
            nodes_of_map[node] = None
        output.write("def nodes_of(hostname):\n    return %r[hostname]\n\n" % nodes_of_map)
    else:
        output.write("clusters = {}\ndef is_cluster(hostname):\n    return False\n\n")
        output.write("def nodes_of(hostname):\n    return None\n")

    # IP addresses
    needed_ipaddresses = {}
    nodes = []
    if config.is_cluster(hostname):
        for node in config.nodes_of(hostname):
            ipa = ip_lookup.lookup_ip_address(node)
            needed_ipaddresses[node] = ipa
            nodes.append( (node, ipa) )

        try:
            ipaddress = ip_lookup.lookup_ip_address(hostname) # might throw exception
            needed_ipaddresses[hostname] = ipaddress
        except:
            ipaddress = None
    else:
        ipaddress = ip_lookup.lookup_ip_address(hostname) # might throw exception
        needed_ipaddresses[hostname] = ipaddress
        nodes = [ (hostname, ipaddress) ]

    output.write("config.ipaddresses = %r\n\n" % needed_ipaddresses)
    output.write("ip_lookup.lookup_ip_address = lambda hostname: ipaddresses.get(hostname)\n\n");

    # datasource programs. Is this host relevant?

    # I think this is not needed anymore. Keep it here for reference
    #
    ## Parameters for checks: Default values are defined in checks/*. The
    ## variables might be overridden by the user in main.mk. We need
    ## to set the actual values of those variables here. Otherwise the users'
    ## settings would get lost. But we only need to set those variables that
    ## influence the check itself - not those needed during inventory.
    #for var in checks.check_config_variables:
    #    output.write("%s = %r\n" % (var, getattr(config, var)))

    ## The same for those checks that use the new API
    #for check_type in needed_check_types:
    #    # Note: check_type might not be in checks.check_info. This is
    #    # the case, if "mem" has been added to "extra_sections" and thus
    #    # to "needed_check_types" - despite the fact that only subchecks
    #    # mem.* exist
    #    if check_type in checks.check_info:
    #        for var in checks.check_info[check_type].get("check_config_variables", []):
    #            output.write("%s = %r\n" % (var, getattr(config, var)))


    # perform actual check with a general exception handler
    output.write("try:\n")
    output.write("    sys.exit(checking.do_check(%r, %r))\n" % (hostname, ipaddress))
    output.write("except MKTerminate:\n")
    output.write("    console.output('<Interrupted>\\n', stream=sys.stderr)\n")
    output.write("    sys.exit(1)\n")
    output.write("except SystemExit, e:\n")
    output.write("    sys.exit(e.code)\n")
    output.write("except Exception, e:\n")
    output.write("    import traceback, pprint\n")

    # status output message
    output.write("    sys.stdout.write(\"UNKNOWN - Exception in precompiled check: %s (details in long output)\\n\" % e)\n")

    # generate traceback for long output
    output.write("    sys.stdout.write(\"Traceback: %s\\n\" % traceback.format_exc())\n")

    # debug logging
    output.write("\n")
    output.write("    l = file(cmk.paths.log_dir + \"/crashed-checks.log\", \"a\")\n")
    output.write("    l.write((\"Exception in precompiled check:\\n\"\n")
    output.write("            \"  Check_MK Version: %s\\n\"\n")
    output.write("            \"  Date:             %s\\n\"\n")
    output.write("            \"  Host:             %s\\n\"\n")
    output.write("            \"  %s\\n\") % (\n")
    output.write("            cmk.__version__,\n")
    output.write("            time.strftime(\"%Y-%d-%m %H:%M:%S\"),\n")
    output.write("            \"%s\",\n" % hostname)
    output.write("            traceback.format_exc().replace('\\n', '\\n      ')))\n")
    output.write("    l.close()\n")

    output.write("    sys.exit(3)\n")
    output.close()

    # compile python (either now or delayed), but only if the source
    # code has not changed. The Python compilation is the most costly
    # operation here.
    if os.path.exists(source_filename):
        if file(source_filename).read() == file(source_filename + ".new").read():
            console.verbose(" (%s is unchanged)\n", source_filename, stream=sys.stderr)
            os.remove(source_filename + ".new")
            return
        else:
            console.verbose(" (new content)", stream=sys.stderr)

    os.rename(source_filename + ".new", source_filename)
    if not config.delay_precompile:
        py_compile.compile(source_filename, compiled_filename, compiled_filename, True)
        os.chmod(compiled_filename, 0755)
    else:
        if os.path.exists(compiled_filename) or os.path.islink(compiled_filename):
            os.remove(compiled_filename)
        os.symlink(hostname + ".py", compiled_filename)

    console.verbose(" ==> %s.\n", compiled_filename, stream=sys.stderr)
