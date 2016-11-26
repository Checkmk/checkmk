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

# Code for support of Nagios (and compatible) cores

import cmk.tty as tty
import cmk.paths

import cmk_base.console as console

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

def do_output_nagios_conf(args):
    if len(args) == 0:
        args = None
    create_nagios_config(sys.stdout, args)


def output_conf_header(outfile):
    outfile.write("""#
# Created by Check_MK. Do not edit.
#

""")


def create_nagios_config(outfile = sys.stdout, hostnames = None):
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
        configuration_warning("host_notification_periods is not longer supported. Please use extra_host_conf['notification_period'] instead.")

    if config.summary_host_notification_periods != []:
        configuration_warning("summary_host_notification_periods is not longer supported. Please use extra_summary_host_conf['notification_period'] instead.")

    if config.service_notification_periods != []:
        configuration_warning("service_notification_periods is not longer supported. Please use extra_service_conf['notification_period'] instead.")

    if config.summary_service_notification_periods != []:
        configuration_warning("summary_service_notification_periods is not longer supported. Please use extra_summary_service_conf['notification_period'] instead.")

    # Map service_period to _SERVICE_PERIOD. This field das not exist in Nagios/Icinga.
    # The CMC has this field natively.
    if "service_period" in config.extra_host_conf:
        config.extra_host_conf["_SERVICE_PERIOD"] = config.extra_host_conf["service_period"]
        del config.extra_host_conf["service_period"]
    if "service_period" in config.extra_service_conf:
        config.extra_service_conf["_SERVICE_PERIOD"] = config.extra_service_conf["service_period"]
        del config.extra_service_conf["service_period"]

    output_conf_header(outfile)
    if hostnames == None:
        hostnames = config.all_active_hosts()

    for hostname in hostnames:
        create_nagios_config_host(outfile, hostname)

    create_nagios_config_contacts(outfile, hostnames)
    create_nagios_config_hostgroups(outfile)
    create_nagios_config_servicegroups(outfile)
    create_nagios_config_contactgroups(outfile)
    create_nagios_config_commands(outfile)
    create_nagios_config_timeperiods(outfile)

    if config.extra_nagios_conf:
        outfile.write("\n# extra_nagios_conf\n\n")
        outfile.write(config.extra_nagios_conf)


def create_nagios_config_host(outfile, hostname):
    outfile.write("\n# ----------------------------------------------------\n")
    outfile.write("# %s\n" % hostname)
    outfile.write("# ----------------------------------------------------\n")
    host_attrs = get_host_attributes(hostname, tags_of_host(hostname))
    if config.generate_hostconf:
        create_nagios_hostdefs(outfile, hostname, host_attrs)
    create_nagios_servicedefs(outfile, hostname, host_attrs)


def create_nagios_hostdefs(outfile, hostname, attrs):
    is_clust = is_cluster(hostname)

    ip = attrs["address"]

    if is_clust:
        nodes = get_cluster_nodes_for_config(hostname)
        attrs.update(get_cluster_attributes(hostname, nodes))

    #   _
    #  / |
    #  | |
    #  | |
    #  |_|    1. normal, physical hosts

    alias = hostname
    outfile.write("\ndefine host {\n")
    outfile.write("  host_name\t\t\t%s\n" % hostname)
    outfile.write("  use\t\t\t\t%s\n" % (is_clust and config.cluster_template or config.host_template))
    outfile.write("  address\t\t\t%s\n" % (ip and make_utf8(ip) or fallback_ip_for(hostname)))

    # Add custom macros
    for key, value in attrs.items():
        if key[0] == '_':
            tabs = len(key) > 13 and "\t\t" or "\t\t\t"
            outfile.write("  %s%s%s\n" % (key, tabs, value))

    # Host check command might differ from default
    command = host_check_command(hostname, ip, is_clust)
    if command:
        outfile.write("  check_command\t\t\t%s\n" % command)

    # Host groups: If the host has no hostgroups it gets the default
    # hostgroup (Nagios requires each host to be member of at least on
    # group.
    hgs = hostgroups_of(hostname)
    hostgroups = ",".join(hgs)
    if len(hgs) == 0:
        hostgroups = config.default_host_group
        hostgroups_to_define.add(config.default_host_group)
    elif config.define_hostgroups:
        hostgroups_to_define.update(hgs)
    outfile.write("  hostgroups\t\t\t%s\n" % make_utf8(hostgroups))

    # Contact groups
    cgrs = host_contactgroups_of([hostname])
    if len(cgrs) > 0:
        outfile.write("  contact_groups\t\t%s\n" % make_utf8(",".join(cgrs)))
        contactgroups_to_define.update(cgrs)

    if not is_clust:
        # Parents for non-clusters

        # Get parents manually defined via extra_host_conf["parents"]. Only honor
        # variable "parents" and implicit parents if this setting is empty
        extra_conf_parents = rulesets.host_extra_conf(hostname, config.extra_host_conf.get("parents", []))

        if not extra_conf_parents:
            parents_list = parents_of(hostname)
            if parents_list:
                outfile.write("  parents\t\t\t%s\n" % (",".join(parents_list)))

    elif is_clust:
        # Special handling of clusters
        alias = "cluster of %s" % ", ".join(nodes)
        outfile.write("  parents\t\t\t%s\n" % ",".join(nodes))

    # Output alias, but only if it's not defined in extra_host_conf
    alias = alias_of(hostname, None)
    if alias == None:
        outfile.write("  alias\t\t\t\t%s\n" % alias)
    else:
        alias = make_utf8(alias)

    # Custom configuration last -> user may override all other values
    outfile.write(make_utf8(extra_host_conf_of(hostname, exclude=["parents"] if is_clust else [])))

    outfile.write("}\n")

    #   ____
    #  |___ \
    #   __) |
    #  / __/
    #  |_____|  2. summary hosts

    if host_is_aggregated(hostname):
        outfile.write("\ndefine host {\n")
        outfile.write("  host_name\t\t\t%s\n" % summary_hostname(hostname))
        outfile.write("  use\t\t\t\t%s-summary\n" % (is_clust and config.cluster_template or config.host_template))
        outfile.write("  alias\t\t\t\tSummary of %s\n" % alias)
        outfile.write("  address\t\t\t%s\n" % (ip and ip or fallback_ip_for(hostname)))
        outfile.write("  __REALNAME\t\t\t%s\n" % hostname)
        outfile.write("  parents\t\t\t%s\n" % hostname)

        # Add custom macros
        for key, value in attrs.items():
            if key[0] == '_':
                outfile.write("  %s\t\t\t%s\n" % (key, value))

        hgs = summary_hostgroups_of(hostname)
        hostgroups = ",".join(hgs)
        if len(hgs) == 0:
            hostgroups = config.default_host_group
            hostgroups_to_define.add(config.default_host_group)
        elif config.define_hostgroups:
            hostgroups_to_define.update(hgs)
        outfile.write("  hostgroups\t\t\t+%s\n" % hostgroups)

        # host gets same contactgroups as real host
        if len(cgrs) > 0:
            outfile.write("  contact_groups\t\t+%s\n" % make_utf8(",".join(cgrs)))

        if is_clust:
            outfile.write("  _NODEIPS\t\t\t%s\n" % " ".join(attrs.get("_NODEIPS")))
        outfile.write(extra_summary_host_conf_of(hostname))
        outfile.write("}\n")
    outfile.write("\n")

def create_nagios_servicedefs(outfile, hostname, host_attrs):
    #   _____
    #  |___ /
    #    |_ \
    #   ___) |
    #  |____/   3. Services


    def do_omit_service(hostname, description):
        if service_ignored(hostname, None, description):
            return True
        if hostname != host_of_clustered_service(hostname, description):
            return True
        return False

    def get_dependencies(hostname,servicedesc):
        result = ""
        for dep in service_deps(hostname, servicedesc):
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

    host_checks = get_check_table(hostname, remove_duplicates=True).items()
    host_checks.sort() # Create deterministic order
    aggregated_services_conf = set([])
    do_aggregation = host_is_aggregated(hostname)
    have_at_least_one_service = False
    used_descriptions = {}
    for ((checkname, item), (params, description, deps)) in host_checks:
        if checkname not in checks.check_info:
            continue # simply ignore missing checks

        # Make sure, the service description is unique on this host
        if description in used_descriptions:
            cn, it = used_descriptions[description]
            configuration_warning(
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


        # Handle aggregated services. If this service belongs to an aggregation,
        # remember, that the aggregated service must be configured. We cannot
        # do this here, because each aggregated service must occur only once
        # in the configuration.
        if do_aggregation:
            asn = aggregated_service_name(hostname, description)
            if asn != "":
                aggregated_services_conf.add(asn)

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
        value = check_interval_of(hostname, checkname)
        if value is not None:
            check_interval = value

        # Add custom user icons and actions
        actions = icons_and_actions_of('service', hostname, description, checkname, params)
        action_cfg = actions and '  _ACTIONS\t\t\t%s\n' % ','.join(actions) or ''

        outfile.write("""define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
  service_description\t\t%s
  check_interval\t\t%d
%s%s  check_command\t\t\tcheck_mk-%s
}

""" % ( template, hostname, description.encode("utf-8"), check_interval,
        extra_service_conf_of(hostname, description), action_cfg, checkname ))

        checknames_to_define.add(checkname)
        have_at_least_one_service = True


    # Now create definitions of the aggregated services for this host
    if do_aggregation and config.service_aggregations:
        outfile.write("\n# Aggregated services\n\n")

    aggr_descripts = aggregated_services_conf
    if config.aggregate_check_mk and host_is_aggregated(hostname) and have_at_least_one_service:
        aggr_descripts.add("Check_MK")

    # If a ping-only-host is aggregated, the summary host gets it's own
    # copy of the ping - as active check. We cannot aggregate the result
    # from the ping of the real host since no Check_MK is running during
    # the check.
    elif host_is_aggregated(hostname) and not have_at_least_one_service:
        outfile.write("""
define service {
  use\t\t\t\t%s
%s  host_name\t\t\t%s
}

""" % (config.pingonly_template, extra_service_conf_of(hostname, "PING"), summary_hostname(hostname)))

    for description in aggr_descripts:
        sergr = rulesets.service_extra_conf(hostname, description, config.summary_service_groups)
        if len(sergr) > 0:
            sg = "  service_groups\t\t\t+" + make_utf8(",".join(sergr)) + "\n"
            if config.define_servicegroups:
                servicegroups_to_define.update(sergr)
        else:
            sg = ""

        sercgr = rulesets.service_extra_conf(hostname, description, config.summary_service_contactgroups)
        contactgroups_to_define.update(sercgr)
        if len(sercgr) > 0:
            scg = "  contact_groups\t\t\t+" + ",".join(sercgr) + "\n"
        else:
            scg = ""

        outfile.write("""define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
%s%s%s  service_description\t\t%s
}

""" % ( config.summary_service_template, summary_hostname(hostname), sg, scg,
extra_summary_service_conf_of(hostname, description), description  ))

    # Active check for check_mk
    if have_at_least_one_service:
        outfile.write("""
# Active checks

define service {
  use\t\t\t\t%s
  host_name\t\t\t%s
%s  service_description\t\tCheck_MK
}
""" % (config.active_service_template, hostname, extra_service_conf_of(hostname, "Check_MK")))

    # legacy checks via legacy_checks
    legchecks = rulesets.host_extra_conf(hostname, config.legacy_checks)
    if len(legchecks) > 0:
        outfile.write("\n\n# Legacy checks\n")
    for command, description, has_perfdata in legchecks:
        description = sanitize_service_description(description)
        if do_omit_service(hostname, description):
            continue

        if description in used_descriptions:
            cn, it = used_descriptions[description]
            configuration_warning(
                    "ERROR: Duplicate service description (legacy check) '%s' for host '%s'!\n"
                    " - 1st occurrance: checktype = %s, item = %r\n"
                    " - 2nd occurrance: checktype = legacy(%s), item = None\n" %
                    (description, hostname, cn, it, command))
            continue

        else:
            used_descriptions[description] = ( "legacy(" + command + ")", description )

        extraconf = extra_service_conf_of(hostname, description)
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
""" % (template, hostname, make_utf8(description), simulate_command(command), extraconf))

        # write service dependencies for legacy checks
        outfile.write(get_dependencies(hostname,description))

    # legacy checks via active_checks
    actchecks = []
    for acttype, rules in config.active_checks.items():
        entries = rulesets.host_extra_conf(hostname, rules)
        if entries:
            # Skip Check_MK HW/SW Inventory for all ping hosts, even when the user has enabled
            # the inventory for ping only hosts
            if acttype == "cmk_inv" and is_ping_host(hostname):
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
            description = active_check_service_description(act_info, params)

            if do_omit_service(hostname, description):
                continue

            # compute argument, and quote ! and \ for Nagios
            args = active_check_arguments(hostname, description,
                                          act_info["argument_function"](params)).replace("\\", "\\\\").replace("!", "\\!")

            if description in used_descriptions:
                cn, it = used_descriptions[description]
                # If we have the same active check again with the same description,
                # then we do not regard this as an error, but simply ignore the
                # second one. That way one can override a check with other settings.
                if cn == "active(%s)" % acttype:
                    continue

                configuration_warning(
                        "ERROR: Duplicate service description (active check) '%s' for host '%s'!\n"
                        " - 1st occurrance: checktype = %s, item = %r\n"
                        " - 2nd occurrance: checktype = active(%s), item = None\n" %
                        (description, hostname, cn, it, acttype))
                continue

            else:
                used_descriptions[description] = ( "active(" + acttype + ")", description )

            template = has_perfdata and "check_mk_perf," or ""
            extraconf = extra_service_conf_of(hostname, description)

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
""" % (template, hostname, make_utf8(description), make_utf8(simulate_command(command)), extraconf))

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
            description = sanitize_service_description(entry["service_description"])
            has_perfdata = entry.get("has_perfdata", False)
            command_name = entry.get("command_name", "check-mk-custom")
            command_line = entry.get("command_line", "")

            if do_omit_service(hostname, description):
                continue

            if command_line:
                command_line = autodetect_plugin(command_line).replace("\\", "\\\\").replace("!", "\\!")

            if "freshness" in entry:
                freshness = "  check_freshness\t\t1\n" + \
                            "  freshness_threshold\t\t%d\n" % (60 * entry["freshness"]["interval"])
                command_line = "echo %s && exit %d" % (
                       quote_nagios_string(entry["freshness"]["output"]), entry["freshness"]["state"])
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
                configuration_warning(
                        "ERROR: Duplicate service description (custom check) '%s' for host '%s'!\n"
                        " - 1st occurrance: checktype = %s, item = %r\n"
                        " - 2nd occurrance: checktype = custom(%s), item = %r\n" %
                        (description, hostname, cn, it, command_name, description))
                continue
            else:
                used_descriptions[description] = ( "custom(%s)" % command_name, description )

            template = has_perfdata and "check_mk_perf," or ""
            extraconf = extra_service_conf_of(hostname, description)
            command = "%s!%s" % (command_name, command_line)
            outfile.write("""
define service {
  use\t\t\t\t%scheck_mk_default
  host_name\t\t\t%s
  service_description\t\t%s
  check_command\t\t\t%s
  active_checks_enabled\t\t%d
%s%s}
""" % (template, hostname, make_utf8(description), simulate_command(command),
       (command_line and not freshness) and 1 or 0, extraconf, freshness))

            # write service dependencies for custom checks
            outfile.write(get_dependencies(hostname,description))

    # FIXME: Remove old name one day
    service_discovery_name = 'Check_MK inventory'
    if 'cmk-inventory' in config.use_new_descriptions_for:
        service_discovery_name = 'Check_MK Discovery'

    params = discovery_check_parameters(hostname) or \
             default_discovery_check_parameters()

    # Inventory checks - if user has configured them.
    if params["check_interval"] \
        and not service_ignored(hostname, None, service_discovery_name) \
        and not "ping" in tags_of_host(hostname): # FIXME/TODO: Why not user is_ping_host()?
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
       extra_service_conf_of(hostname, service_discovery_name),
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
        add_ping_service(outfile, hostname, host_attrs["address"], is_ipv6_primary(hostname) and 6 or 4,
                         "PING", host_attrs.get("_NODEIPS"))

    if is_ipv4v6_host(hostname):
        if is_ipv6_primary(hostname):
            add_ping_service(outfile, hostname, host_attrs["_ADDRESS_4"], 4,
                             "PING IPv4", host_attrs.get("_NODEIPS_4"))
        else:
            add_ping_service(outfile, hostname, host_attrs["_ADDRESS_6"], 6,
                             "PING IPv6", host_attrs.get("_NODEIPS_6"))


def add_ping_service(outfile, hostname, ipaddress, family, descr, node_ips):
    arguments = check_icmp_arguments_of(hostname, family=family)

    ping_command = 'check-mk-ping'
    if is_cluster(hostname):
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

""" % (config.pingonly_template, descr, ping_command, arguments, extra_service_conf_of(hostname, descr), hostname))


def simulate_command(command):
    if config.simulation_mode:
        custom_commands_to_define.add("check-mk-simulation")
        return "check-mk-simulation!echo 'Simulation mode - cannot execute real check'"
    else:
        return command

def create_nagios_config_hostgroups(outfile):
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
""" % (make_utf8(hg), make_utf8(alias)))

    # No creation of host groups but we need to define
    # default host group
    elif config.default_host_group in hostgroups_to_define:
        outfile.write("""
define hostgroup {
  hostgroup_name\t\t%s
  alias\t\t\t\tCheck_MK default hostgroup
}
""" % config.default_host_group)


def create_nagios_config_servicegroups(outfile):
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
""" % (make_utf8(sg), make_utf8(alias)))

def create_nagios_config_contactgroups(outfile):
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
                "  alias\t\t\t\t%s\n" % (make_utf8(name), make_utf8(alias)))

        members = config.contactgroup_members.get(name)
        if members:
            outfile.write("  members\t\t\t%s\n" % ",".join(members))

        outfile.write("}\n")


def create_nagios_config_commands(outfile):
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


def create_nagios_config_timeperiods(outfile):
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
                outfile.write("  alias\t\t\t\t%s\n" % make_utf8(tp["alias"]))
            for key, value in tp.items():
                if key not in [ "alias", "exclude" ]:
                    times = ",".join([ ("%s-%s" % (fr, to)) for (fr, to) in value ])
                    if times:
                        outfile.write("  %-20s\t\t%s\n" % (key, times))
            if "exclude" in tp:
                outfile.write("  exclude\t\t\t%s\n" % ",".join(tp["exclude"]))
            outfile.write("}\n\n")

def create_nagios_config_contacts(outfile, hostnames):
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

            outfile.write("define contact {\n  contact_name\t\t\t%s\n" % make_utf8(cname))
            if "alias" in contact:
                outfile.write("  alias\t\t\t\t%s\n" % make_utf8(contact["alias"]))
            if "email" in contact:
                outfile.write("  email\t\t\t\t%s\n" % make_utf8(contact["email"]))
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
def quote_nagios_string(s):
    return "'" + s.replace('\\', '\\\\').replace("'", "'\"'\"'").replace('!', '\\!') + "'"

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

# Find files to be included in precompile host check for a certain
# check (for example df or mem.used). In case of checks with a period
# (subchecks) we might have to include both "mem" and "mem.used". The
# subcheck *may* be implemented in a separate file.
def find_check_plugins(checktype):
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
            precompile_hostcheck(host)
        except Exception, e:
            if cmk.debug.enabled():
                raise
            sys.stderr.write("Error precompiling checks for host %s: %s\n" % (host, e))
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


def precompile_hostcheck(hostname):
    console.verbose("%s%s%-16s%s:", tty.bold, tty.blue, hostname, tty.normal, stream=sys.stderr)

    compiled_filename = cmk.paths.precompiled_hostchecks_dir + "/" + hostname
    source_filename = compiled_filename + ".py"
    for fname in [ compiled_filename, source_filename ]:
        try:
            os.remove(fname)
        except:
            pass

    # check table, enriched with addition precompiled information.
    check_table = get_precompiled_check_table(hostname)
    if len(check_table) == 0:
        console.verbose("(no Check_MK checks)\n")
        return

    output = file(source_filename + ".new", "w")
    output.write("#!/usr/bin/python\n")
    output.write("# encoding: utf-8\n")

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

    output.write(stripped_python_file(cmk.paths.modules_dir + "/check_mk_base.py"))

    # Register default Check_MK signal handler
    output.write("register_sigint_handler()\n")

    # initialize global variables
    output.write("""
# very simple commandline parsing: only -v (once or twice) and -d are supported

cmk.log.setup_console_logging()
logger = cmk.log.get_logger("base")

# TODO: This is not really good parsing, because it not cares about syntax like e.g. "-nv".
#       The later regular argument parsing is handling this correctly. Try to clean this up.
cmk.log.set_verbosity(verbosity=len([ a for a in sys.argv if a in [ "-v", "--verbose"] ]))

import cmk.debug

if '-d' in sys.argv:
    cmk.debug.enable()
""")

    # Compile in all neccessary global variables
    output.write("\n# Global variables\n")
    for var in [ 'tcp_connect_timeout', 'agent_min_version',
                 'perfdata_format', 'aggregation_output_format',
                 'aggr_summary_hostname',
                 'check_submission', 'monitoring_core',
                 'cluster_max_cachefile_age', 'check_max_cachefile_age',
                 'piggyback_max_cachefile_age', 'fallback_agent_output_encoding',
                 'simulation_mode', 'agent_simulator', 'aggregate_check_mk',
                 'check_mk_perfdata_with_times',
                 'use_inline_snmp', 'record_inline_snmp_stats',
                 ]:
        output.write("%s = %r\n" % (var, getattr(config, var)))

    output.write("\n# Checks for %s\n\n" % hostname)
    output.write("def get_precompiled_check_table(hostname, remove_duplicates=False, world='config'):\n    return %r\n\n" % check_table)

    # Do we need to load the SNMP module? This is the case, if the host
    # has at least one SNMP based check. Also collect the needed check
    # types and sections.
    need_snmp_module = False
    needed_check_types = set([])
    needed_sections = set([])
    service_timeperiods = {}
    check_intervals = {}
    for check_type, _unused_item, _unused_param, descr, _unused_aggr in check_table:
        if check_type not in checks.check_info:
            sys.stderr.write('Warning: Ignoring missing check %s.\n' % check_type)
            continue
        if checks.check_info[check_type].get("extra_sections"):
            for section in checks.check_info[check_type]["extra_sections"]:
                if section in checks.check_info:
                    needed_check_types.add(section)
                needed_sections.add(section.split(".")[0])
        period = check_period_of(hostname, descr)
        if period:
            service_timeperiods[descr] = period
        interval = check_interval_of(hostname, check_type)
        if interval is not None:
            check_intervals[check_type] = interval

        needed_sections.add(check_type.split(".")[0])
        needed_check_types.add(check_type)
        if check_uses_snmp(check_type):
            need_snmp_module = True

    output.write("precompiled_check_intervals = %r\n" % check_intervals)
    output.write("def check_interval_of(hostname, checktype):\n    return precompiled_check_intervals.get(checktype)\n\n")
    output.write("precompiled_service_timeperiods = %r\n" % service_timeperiods)
    output.write("def check_period_of(hostname, service):\n    return precompiled_service_timeperiods.get(service)\n\n")

    if need_snmp_module:
        output.write(stripped_python_file(cmk.paths.modules_dir + "/snmp.py"))

        if is_inline_snmp_host(hostname):
            output.write(stripped_python_file(cmk.paths.modules_dir + "/inline_snmp.py"))
            output.write("\ndef oid_range_limits_of(hostname):\n    return %r\n" % oid_range_limits_of(hostname))
        else:
            output.write("has_inline_snmp = False\n")
    else:
        output.write("has_inline_snmp = False\n")

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
        paths = find_check_plugins(check_type)
        if not paths:
            raise MKGeneralException("Cannot find check file %s needed for check type %s" % \
                                     (basename, check_type))

        for path in paths:
            if path not in filenames:
                filenames.append(path)

    output.write("check_info = {}\n" +
                 "inv_info = {}\n" +
                 "check_includes = {}\n" +
                 "precompile_params = {}\n" +
                 "factory_settings = {}\n" +
                 "checkgroup_of = {}\n" +
                 "check_config_variables = []\n" +
                 "check_default_levels = {}\n" +
                 "snmp_info = {}\n" +
                 "snmp_scan_functions = {}\n")

    for filename in filenames:
        output.write("# %s\n" % filename)
        output.write(stripped_python_file(filename))
        output.write("\n\n")
        console.verbose(" %s%s%s", tty.green, filename.split('/')[-1], tty.normal, stream=sys.stderr)

    # Make sure all checks are converted to the new API
    output.write("convert_check_info()\n")
    output.write("initialize_check_type_caches()\n")

    # handling of clusters
    if is_cluster(hostname):
        output.write("clusters = { %r : %r }\n" %
                     (hostname, nodes_of(hostname)))
        output.write("def is_cluster(hostname):\n    return True\n\n")
    else:
        output.write("clusters = {}\ndef is_cluster(hostname):\n    return False\n\n")

    output.write("def clusters_of(hostname):\n    return %r\n\n" % clusters_of(hostname))

    has_board = has_management_board(hostname)
    output.write("def has_management_board(hostname):\n    return %r\n\n" % has_board)
    if has_board:
        output.write("def management_address(hostname):\n    return %r\n\n" % management_address(hostname))
        output.write("def management_protocol(hostname):\n    return %r\n\n" % management_protocol(hostname))

    # snmp hosts
    output.write("def is_snmp_host(hostname):\n   return    % r\n\n" % is_snmp_host(hostname))
    output.write("def is_snmpv3_host(hostname):\n   return  % r\n\n" % is_snmpv3_host(hostname))
    output.write("def is_tcp_host(hostname):\n   return     % r\n\n" % is_tcp_host(hostname))
    output.write("def is_usewalk_host(hostname):\n   return % r\n\n" % is_usewalk_host(hostname))
    output.write("def snmpv3_contexts_of_host(hostname):\n    return % r\n\n" % snmpv3_contexts_of_host(hostname))
    output.write("def is_inline_snmp_host(hostname):\n   return        % r\n\n" % is_inline_snmp_host(hostname))
    if is_inline_snmp_host(hostname):
        output.write("def is_snmpv2c_host(hostname):\n   return     % r\n\n" % is_snmpv2c_host(hostname))
        output.write("def is_bulkwalk_host(hostname):\n   return    % r\n\n" % is_bulkwalk_host(hostname))
        output.write("def snmp_timing_of(hostname):\n   return      % r\n\n" % snmp_timing_of(hostname))
        output.write("def snmp_credentials_of(hostname):\n   return % s\n\n" % pprint.pformat(snmp_credentials_of(hostname)))
        output.write("def snmp_port_of(hostname):\n   return        % r\n\n" % snmp_port_of(hostname))
    else:
        output.write("def snmp_proto_spec(hostname):\n    return   % r\n\n" % snmp_proto_spec(hostname))
        output.write("def snmp_port_spec(hostname):\n    return   % r\n\n" % snmp_port_spec(hostname))
        output.write("def snmp_walk_command(hostname):\n   return % r\n\n" % snmp_walk_command(hostname))

    # IP addresses
    needed_ipaddresses = {}
    ipv6_primary_hosts = {}
    nodes = []
    if is_cluster(hostname):
        for node in nodes_of(hostname):
            ipa = lookup_ip_address(node)
            needed_ipaddresses[node] = ipa
            ipv6_primary_hosts[node] = is_ipv6_primary(node)
            nodes.append( (node, ipa) )

        try:
            ipaddress = lookup_ip_address(hostname) # might throw exception
            needed_ipaddresses[hostname] = ipaddress
        except:
            ipaddress = None
    else:
        ipaddress = lookup_ip_address(hostname) # might throw exception
        needed_ipaddresses[hostname] = ipaddress
        nodes = [ (hostname, ipaddress) ]

    ipv6_primary_hosts[hostname] = is_ipv6_primary(hostname)

    output.write("ipaddresses = %r\n\n" % needed_ipaddresses)
    output.write("def lookup_ip_address(hostname):\n   return ipaddresses.get(hostname)\n\n");

    output.write("ipv6_primary_hosts = %r\n\n" % ipv6_primary_hosts)
    output.write("def is_ipv6_primary(hostname):\n   return ipv6_primary_hosts.get(hostname, False)\n\n");

    # datasource programs. Is this host relevant?
    # ACHTUNG: HIER GIBT ES BEI CLUSTERN EIN PROBLEM!! WIR MUESSEN DIE NODES
    # NEHMEN!!!!!

    dsprogs = {}
    for node, ipa in nodes:
        program = get_datasource_program(node, ipa)
        dsprogs[node] = program
    output.write("def get_datasource_program(hostname, ipaddress):\n" +
                 "    return %r[hostname]\n\n" % dsprogs)

    # aggregation
    output.write("def host_is_aggregated(hostname):\n    return %r\n\n" % host_is_aggregated(hostname))

    # TCP and SNMP port of agent
    output.write("def agent_port_of(hostname):\n    return %d\n\n" % agent_port_of(hostname))

    # agent encryption
    output.write("def agent_encryption_settings(hostname):\n    return %r\n\n" % agent_encryption_settings(hostname))

    # Exit code of Check_MK in case of various errors
    output.write("def exit_code_spec(hostname):\n    return %r\n\n" % exit_code_spec(hostname))

    # Piggyback translations
    output.write("def get_piggyback_translation(hostname):\n    return %r\n\n" % get_piggyback_translation(hostname))

    # Expected agent version
    output.write("def agent_target_version(hostname):\n    return %r\n\n" % (agent_target_version(hostname),))

    # SNMP character encoding
    output.write("def get_snmp_character_encoding(hostname):\n    return %r\n\n"
      % get_snmp_character_encoding(hostname))

    # Parameters for checks: Default values are defined in checks/*. The
    # variables might be overridden by the user in main.mk. We need
    # to set the actual values of those variables here. Otherwise the users'
    # settings would get lost. But we only need to set those variables that
    # influence the check itself - not those needed during inventory.
    for var in checks.check_config_variables:
        output.write("%s = %r\n" % (var, eval(var)))

    # The same for those checks that use the new API
    for check_type in needed_check_types:
        # Note: check_type might not be in checks.check_info. This is
        # the case, if "mem" has been added to "extra_sections" and thus
        # to "needed_check_types" - despite the fact that only subchecks
        # mem.* exist
        if check_type in checks.check_info:
            for var in checks.check_info[check_type].get("check_config_variables", []):
                output.write("%s = %r\n" % (var, eval(var)))


    # perform actual check with a general exception handler
    output.write("try:\n")
    output.write("    sys.exit(do_check(%r, %r))\n" % (hostname, ipaddress))
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

#.
