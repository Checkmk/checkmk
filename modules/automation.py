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

import signal

import cmk.paths
import cmk.man_pages as man_pages

import cmk_base.rulesets as rulesets
import cmk_base.config as config
import cmk_base.ip_lookup as ip_lookup
import cmk_base.snmp as snmp

# TODO: Inherit from MKGeneralException
class MKAutomationError(Exception):
    def __init__(self, reason):
        self.reason = reason
        super(MKAutomationError, self).__init__(reason)
    def __str__(self):
        return self.reason


def trigger_automation_timeout(signum, stackframe):
    raise MKTimeout("Action timed out. The timeout of %d "
                    "seconds was reached." % MKTimeout.timeout)


def do_automation(cmd, args):
    # Handle generic arguments (currently only the optional timeout argument)
    if len(args) > 1 and args[0] == "--timeout":
        args.pop(0)
        timeout = int(args.pop(0))

        if timeout:
            MKTimeout.timeout = timeout
            signal.signal(signal.SIGALRM, trigger_automation_timeout)
            signal.alarm(timeout)


    try:
        if cmd == "get-configuration":
            config.load(with_conf_d=False)
            result = automation_get_configuration()
        elif cmd == "get-check-information":
            result = automation_get_check_information()
        elif cmd == "get-real-time-checks":
            result = automation_get_real_time_checks()
        elif cmd == "get-check-manpage":
            result = automation_get_check_manpage(args)
        elif cmd == "get-package-info":
            result = automation_get_package_info(args)
        elif cmd == "get-package":
            result = automation_get_package(args)
        elif cmd == "create-package":
            result = automation_create_or_edit_package(args, "create")
        elif cmd == "edit-package":
            result = automation_create_or_edit_package(args, "edit")
        elif cmd == "install-package":
            result = automation_install_package(args)
        elif cmd == "remove-package":
            result = automation_remove_or_release_package(args, "remove")
        elif cmd == "release-package":
            result = automation_remove_or_release_package(args, "release")
        elif cmd == "remove-unpackaged-file":
            result = automation_remove_unpackaged_file(args)
        elif cmd == "notification-get-bulks":
            result = automation_get_bulks(args)
        else:
            config.load(validate_hosts=False)
            if cmd == "try-inventory":
                result = automation_try_discovery(args)
            elif cmd == "inventory":
                result = automation_discovery(args)
            elif cmd == "analyse-service":
                result = automation_analyse_service(args)
            elif cmd == "active-check":
                result = automation_active_check(args)
            elif cmd == "get-autochecks":
                result = automation_get_autochecks(args)
            elif cmd == "set-autochecks":
                result = automation_set_autochecks(args)
            elif cmd == "reload":
                result = automation_restart("reload")
            elif cmd == "restart":
                result = automation_restart("restart")
            elif cmd == "scan-parents":
                result = automation_scan_parents(args)
            elif cmd == "diag-host":
                result = automation_diag_host(args)
            elif cmd == "delete-hosts":
                result = automation_delete_hosts(args)
            elif cmd == "rename-hosts":
                result = automation_rename_hosts()
            elif cmd == "notification-replay":
                result = automation_notification_replay(args)
            elif cmd == "notification-analyse":
                result = automation_notification_analyse(args)
            elif cmd == "update-dns-cache":
                result = automation_update_dns_cache()
            elif cmd == "bake-agents":
                result = automation_bake_agents()
            elif cmd == "get-agent-output":
                result = automation_get_agent_output(args)
            else:
                raise MKAutomationError("Automation command '%s' is not implemented." % cmd)

    except (MKAutomationError, MKTimeout), e:
        sys.stderr.write("%s\n" % e)
        if cmk.debug.enabled():
            raise
        output_profile()
        sys.exit(1)

    except Exception, e:
        if cmk.debug.enabled():
            raise
        else:
            sys.stderr.write("%s\n" % make_utf8("%s" % e))
            output_profile()
            sys.exit(2)

    if cmk.debug.enabled():
        import pprint
        sys.stdout.write(pprint.pformat(result)+"\n")
    else:
        sys.stdout.write("%r\n" % (result,))
    output_profile()
    sys.exit(0)


# Does discovery for a list of hosts. Possible values for how:
# "new" - find only new services (like -I)
# "remove" - remove exceeding services
# "fixall" - find new, remove exceeding
# "refresh" - drop all services and reinventorize
# Hosts on the list that are offline (unmonitored) will
# be skipped.
def automation_discovery(args):

    # Error sensivity
    if args[0] == "@raiseerrors":
        args = args[1:]
        on_error = "raise"
        os.dup2(os.open("/dev/null", os.O_WRONLY), 2)
    else:
        on_error = "ignore"

    # perform full SNMP scan on SNMP devices?
    if args[0] == "@scan":
        do_snmp_scan = True
        args = args[1:]
    else:
        do_snmp_scan = False

    # use cache files if present?
    if args[0] == "@cache":
        args = args[1:]
        use_caches = True
    else:
        use_caches = False

    if len(args) < 2:
        raise MKAutomationError("Need two arguments: new|remove|fixall|refresh HOSTNAME")

    how = args[0]
    hostnames = args[1:]

    counts = {}
    failed_hosts = {}

    for hostname in hostnames:
        result, error = discover_on_host(how, hostname, do_snmp_scan, use_caches, on_error)
        counts[hostname] = result
        if error is not None:
            failed_hosts[hostname] = error
        else:
            trigger_discovery_check(hostname)

    return counts, failed_hosts


def automation_try_discovery(args):
    use_caches = False
    do_snmp_scan = False
    if args[0] == '@noscan':
        args = args[1:]
        do_snmp_scan = False
        use_caches = True
    elif args[0] == '@scan':
        args = args[1:]
        do_snmp_scan = True
        use_caches = False

    if args[0] == '@raiseerrors':
        on_error = "raise"
        args = args[1:]
    else:
        on_error = "ignore"

    # TODO: Remove this unlucky option opt_use_cachefile. At least do not
    # handle this option so deep in the code. It should only be handled
    # by top-level functions.
    agent_data.set_use_cachefile(use_caches)
    if use_caches:
        config.check_max_cachefile_age = config.inventory_max_cachefile_age
    hostname = args[0]
    table = get_check_preview(hostname, use_caches=use_caches,
                              do_snmp_scan=do_snmp_scan, on_error=on_error)
    return table


# Set the new list of autochecks. This list is specified by a
# table of (checktype, item). No parameters are specified. Those
# are either (1) kept from existing autochecks or (2) computed
# from a new inventory. Note: we must never convert check parameters
# from python source code to actual values.
def automation_set_autochecks(args):
    hostname = args[0]
    new_items = eval(sys.stdin.read())
    set_autochecks_of(hostname, new_items)
    trigger_discovery_check(hostname)
    return None


# if required, schedule an inventory check
def trigger_discovery_check(hostname):
    if (config.inventory_check_autotrigger and config.inventory_check_interval) and\
            (not is_cluster(hostname) or nodes_of(hostname)):
        schedule_inventory_check(hostname)


def automation_get_autochecks(args):
    hostname = args[0]
    result = []
    for ct, item, paramstring in parse_autochecks_file(hostname):
        result.append((ct, item, eval(paramstring), paramstring))
    return result


# Determine the type of the check, and how the parameters are being
# constructed
def automation_analyse_service(args):
    hostname = args[0]
    servicedesc = args[1].decode("utf-8")
    checks.set_hostname(hostname)

    # We just consider types of checks that are managed via WATO.
    # We have the following possible types of services:
    # 1. manual checks (static_checks) (currently overriding inventorized checks)
    # 2. inventorized check
    # 3. classical checks
    # 4. active checks

    # Compute effective check table, in order to remove SNMP duplicates
    check_table = get_check_table(hostname, remove_duplicates = True)

    # 1. Manual checks
    for nr, (checkgroup, entries) in enumerate(config.static_checks.items()):
        for entry in entries:
            entry, rule_options = rulesets.get_rule_options(entry)
            if rule_options.get("disabled"):
                continue

            # Parameters are optional
            if len(entry[0]) == 2:
                checktype, item = entry[0]
                params = None
            else:
                checktype, item, params = entry[0]
            if len(entry) == 3:
                taglist, hostlist = entry[1:3]
            else:
                hostlist = entry[1]
                taglist = []

            if rulesets.hosttags_match_taglist(tags_of_host(hostname), taglist) and \
               rulesets.in_extraconf_hostlist(hostlist, hostname):
               descr = service_description(hostname, checktype, item)
               if descr == servicedesc:
                   return {
                       "origin"       : "static",
                       "checkgroup"   : checkgroup,
                       "checktype"    : checktype,
                       "item"         : item,
                       "rule_nr"      : nr,
                       "parameters"   : params,
                  }


    # 2. Load all autochecks of the host in question and try to find
    # our service there
    try:
        path = "%s/%s.mk" % (cmk.paths.autochecks_dir, hostname)
        if os.path.exists(path):
            for entry in eval(file(path).read()):
                if len(entry) == 4: # old format
                    hn, ct, item, params = entry
                else:
                    ct, item, params = entry # new format without host name
                    hn = hostname

                if (ct, item) not in check_table:
                    continue # this is a removed duplicate or clustered service
                descr = service_description(hn, ct, item)
                if hn == hostname and descr == servicedesc:
                    dlv = checks.check_info[ct].get("default_levels_variable")
                    if dlv:
                        fs = checks.factory_settings.get(dlv, None)
                    else:
                        fs = None

                    return {
                        "origin"           : "auto",
                        "checktype"        : ct,
                        "checkgroup"       : checks.check_info[ct].get("group"),
                        "item"             : item,
                        "inv_parameters"   : params,
                        "factory_settings" : fs,
                        "parameters"       : compute_check_parameters(hostname, ct, item, params),
                    }
    except:
        if cmk.debug.enabled():
            raise

    # 3. Classical checks
    for nr, entry in enumerate(config.custom_checks):
        if len(entry) == 4:
            rule, tags, hosts, options = entry
            if options.get("disabled"):
                continue
        else:
            rule, tags, hosts = entry

        matching_hosts = rulesets.all_matching_hosts(tags, hosts, with_foreign_hosts = True)
        if hostname in matching_hosts:
            desc = rule["service_description"]
            if desc == servicedesc:
                result = {
                    "origin"       : "classic",
                    "rule_nr"      : nr,
                }
                if "command_line" in rule: # Only active checks have a command line
                    result["command_line"] = rule["command_line"]
                return result

    # 4. Active checks
    for acttype, rules in config.active_checks.items():
        entries = rulesets.host_extra_conf(hostname, rules)
        if entries:
            act_info = checks.active_check_info[acttype]
            for params in entries:
                description = act_info["service_description"](params)
                if description == servicedesc:
                    return {
                        "origin"     : "active",
                        "checktype"  : acttype,
                        "parameters" : params,
                    }

    return {} # not found
    # TODO: Was ist mit Clustern???
    # TODO: Klappt das mit automatischen verschatten von SNMP-Checks (bei dual Monitoring)


def automation_delete_hosts(args):
    for hostname in args:
        delete_host_files(hostname)
    return None


def delete_host_files(hostname):
    # The inventory_archive as well as the performance data is kept
    # we do not want to loose any historic data for accidently deleted hosts.
    #
    # These files are cleaned up by the disk space mechanism.

    # single files
    for path in [
        "%s/%s"                  % (cmk.paths.precompiled_hostchecks_dir, hostname),
        "%s/%s.py"               % (cmk.paths.precompiled_hostchecks_dir, hostname),
        "%s/%s.mk"               % (cmk.paths.autochecks_dir, hostname),
        "%s/%s"                  % (cmk.paths.counters_dir, hostname),
        "%s/%s"                  % (cmk.paths.tcp_cache_dir, hostname),
        "%s/persisted/%s"        % (cmk.paths.var_dir, hostname),
        "%s/inventory/%s"        % (cmk.paths.var_dir, hostname),
        "%s/inventory/%s.gz"     % (cmk.paths.var_dir, hostname),
        "%s/agent_deployment/%s" % (cmk.paths.var_dir, hostname),
        ]:
        if os.path.exists(path):
            os.unlink(path)

    # files from snmp devices
    for filename in os.listdir(cmk.paths.tcp_cache_dir):
        if filename.startswith("%s." % hostname):
            os.unlink("%s/%s" % (cmk.paths.tcp_cache_dir, filename))

    # softlinks for baked agents. obsolete packages are removed upon next bake action
    # TODO: Move to bakery code
    baked_agents_dir = cmk.paths.var_dir + "/agents/"
    if os.path.exists(baked_agents_dir):
        for folder in os.listdir(baked_agents_dir):
            if os.path.exists("%s/%s" % (folder, hostname)):
                os.unlink("%s/%s" % (folder, hostname))

    # logwatch and piggyback folders
    import shutil
    for what_dir in [ "%s/%s" % (cmk.paths.logwatch_dir, hostname),
                      "%s/piggyback/%s" % (cmk.paths.tmp_dir, hostname), ]:
        if os.path.exists(what_dir):
            shutil.rmtree(what_dir)

    return None


def automation_restart(job = "restart"):
    if check_plugins_have_changed():
        forced = True
        job = "restart"
    else:
        forced = False


    # make sure, Nagios does not inherit any open
    # filedescriptors. This really happens, e.g. if
    # check_mk is called by WATO via Apache. Nagios inherits
    # the open file where Apache is listening for incoming
    # HTTP connections. Really.
    if config.monitoring_core == "nagios":
        objects_file = cmk.paths.nagios_objects_file
        for fd in range(3, 256):
            try:
                os.close(fd)
            except:
                pass
    else:
        objects_file = cmk.paths.var_dir + "/core/config"
        if job == "restart" and not forced:
            job = "reload" # force reload for CMC

    # os.closerange(3, 256) --> not available in older Python versions

    class null_file(object):
        def write(self, stuff):
           pass
        def flush(self):
           pass

    # Deactivate stdout by introducing fake file without filedescriptor
    old_stdout = sys.stdout
    sys.stdout = null_file()

    try:
        backup_path = None
        if try_get_activation_lock():
            raise MKAutomationError("Cannot activate changes. "
                  "Another activation process is currently in progresss")

        if os.path.exists(objects_file):
            backup_path = objects_file + ".save"
            os.rename(objects_file, backup_path)
        else:
            backup_path = None

        try:
            configuration_warnings = create_core_config()

            if "do_bake_agents" in globals() and config.bake_agents_on_restart:
                do_bake_agents()

        except Exception, e:
	    if backup_path:
		os.rename(backup_path, objects_file)
            if cmk.debug.enabled():
                raise
	    raise MKAutomationError("Error creating configuration: %s" % e)

        if do_check_nagiosconfig():
            if backup_path:
                os.remove(backup_path)
            if config.monitoring_core == "cmc":
                do_pack_config()
            else:
                do_precompile_hostchecks()
            do_core_action(job)
        else:
            broken_config_path = "%s/check_mk_objects.cfg.broken" % cmk.paths.tmp_dir
            file(broken_config_path, "w").write(file(cmk.paths.nagios_objects_file).read())

            if backup_path:
                os.rename(backup_path, objects_file)
            else:
                os.remove(objects_file)
            raise MKAutomationError(
                "Configuration for monitoring core is invalid. Rolling back. "
                "The broken file has been copied to \"%s\" for analysis." % broken_config_path)

    except Exception, e:
        if backup_path and os.path.exists(backup_path):
            os.remove(backup_path)
        if cmk.debug.enabled():
            raise
        raise MKAutomationError(str(e))

    sys.stdout = old_stdout
    return configuration_warnings


def check_plugins_have_changed():
    this_time = last_modification_in_dir(cmk.paths.local_checks_dir)
    last_time = time_of_last_core_restart()
    return this_time > last_time


def last_modification_in_dir(dir_path):
    max_time = os.stat(dir_path).st_mtime
    for file_name in os.listdir(dir_path):
        max_time = max(max_time, os.stat(dir_path + "/" + file_name).st_mtime)
    return max_time


def time_of_last_core_restart():
    if config.monitoring_core == "cmc":
        pidfile_path = cmk.paths.omd_root + "/tmp/run/cmc.pid"
    else:
        pidfile_path = cmk.paths.omd_root + "/tmp/lock/nagios.lock"
    if os.path.exists(pidfile_path):
        return os.stat(pidfile_path).st_mtime
    else:
        return 0


def automation_get_configuration():
    # We read the list of variable names from stdin since
    # that could be too much for the command line
    variable_names = eval(sys.stdin.read())
    result = {}
    for varname in variable_names:
        if hasattr(config, varname):
            value = getattr(config, varname)
            if not hasattr(value, '__call__'):
                result[varname] = value
    return result


def automation_get_check_information():
    manuals = man_pages.all_man_pages()

    check_infos = {}
    for check_type, check in checks.check_info.items():
        try:
            manfile = manuals.get(check_type)
            # TODO: Use cmk.man_pages module standard functions to read the title
            if manfile:
                title = file(manfile).readline().strip().split(":", 1)[1].strip()
            else:
                title = check_type
            check_infos[check_type] = { "title" : title.decode("utf-8") }
            if check["group"]:
                check_infos[check_type]["group"] = check["group"]
            check_infos[check_type]["service_description"] = check.get("service_description","%s")
            check_infos[check_type]["snmp"] = check.is_snmp_check(check_type)
        except Exception, e:
            if cmk.debug.enabled():
                raise
            raise MKAutomationError("Failed to parse man page '%s': %s" % (check_type, e))
    return check_infos


def automation_get_real_time_checks():
    manuals = man_pages.all_man_pages()

    rt_checks = []
    for check_type, check in checks.check_info.items():
        if check["handle_real_time_checks"]:
            title = check_type
            try:
                manfile = manuals.get(check_type)
                if manfile:
                    title = file(manfile).readline().strip().split(":", 1)[1].strip()
            except Exception:
                if cmk.debug.enabled():
                    raise

            rt_checks.append((check_type, "%s - %s" % (check_type, title)))

    return rt_checks


def automation_get_check_manpage(args):
    if len(args) != 1:
        raise MKAutomationError("Need exactly one argument.")

    check_type = args[0]
    manpage = man_pages.load_man_page(args[0])

    # Add a few informations from check_info. Note: active checks do not
    # have an entry in check_info
    if check_type in checks.check_info:
        manpage["type"] = "check_mk"
        info = checks.check_info[check_type]
        for key in [ "snmp_info", "has_perfdata", "service_description" ]:
            if key in info:
                manpage[key] = info[key]
        if "." in check_type:
            section = check_type.split(".")[0]
            if section in checks.check_info and "snmp_info" in checks.check_info[section]:
                manpage["snmp_info"] = checks.check_info[section]["snmp_info"]

        if "group" in info:
            manpage["group"] = info["group"]

    # Assume active check
    elif check_type.startswith("check_"):
        manpage["type"] = "active"
    else:
        raise MKAutomationError("Could not detect type of manpage: %s. "
                                "Maybe the check is missing." % check_type)

    return manpage


def automation_scan_parents(args):
    import cmk_base.parent_scan

    settings = {
        "timeout"     : int(args[0]),
        "probes"      : int(args[1]),
        "max_ttl"     : int(args[2]),
        "ping_probes" : int(args[3]),
    }
    hostnames = args[4:]
    if not cmk_base.parent_scan.traceroute_available():
        raise MKAutomationError("Cannot find binary <tt>traceroute</tt> in search path.")

    try:
        gateways = cmk_base.parent_scan.scan_parents_of(hostnames, silent=True,
                                                        settings=settings)
        return gateways
    except Exception, e:
        raise MKAutomationError("%s" % e)

def automation_diag_host(args):
    import subprocess

    hostname, test, ipaddress, snmp_community = args[:4]
    agent_port, snmp_timeout, snmp_retries = map(int, args[4:7])
    cmd = args[7]

    snmpv3_use               = None
    snmpv3_auth_proto        = None
    snmpv3_security_name     = None
    snmpv3_security_password = None
    snmpv3_privacy_proto     = None
    snmpv3_privacy_password  = None

    if len(args) > 8:
        snmpv3_use = args[8]
        if snmpv3_use in ["authNoPriv", "authPriv"]:
            snmpv3_auth_proto, snmpv3_security_name, snmpv3_security_password = args[9:12]
        else:
            snmpv3_security_name = args[10]
        if snmpv3_use == "authPriv":
            snmpv3_privacy_proto, snmpv3_privacy_password = args[12:14]

    if not ipaddress:
        try:
            ipaddress = ip_lookup.lookup_ip_address(hostname)
        except:
            raise MKGeneralException("Cannot resolve hostname %s into IP address" % hostname)

    ipv6_primary = config.is_ipv6_primary(hostname)

    try:
        if test == 'ping':
            base_cmd = ipv6_primary and "ping6" or "ping"
            p = subprocess.Popen([base_cmd, "-A", "-i", "0.2",
                                            "-c", "2", "-W", "5", ipaddress ],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            response = p.stdout.read()
            return (p.wait(), response)

        elif test == 'agent':
            if not cmd:
                cmd = agent_data.get_datasource_program(hostname, ipaddress)

            if cmd:
                return 0, agent_data.get_agent_info_program(cmd)
            else:
                return 0, agent_data.get_agent_info_tcp(hostname, ipaddress, agent_port or None)

        elif test == 'traceroute':
            family_flag = ipv6_primary and "-6" or "-4"
            try:
                p = subprocess.Popen(['traceroute', family_flag, '-n', ipaddress ],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            except OSError, e:
                if e.errno == 2:
                    return 1, "Cannot find binary <tt>traceroute</tt>."
                else:
                    raise
            response = p.stdout.read()
            return (p.wait(), response)

        elif test.startswith('snmp'):
            # SNMPv3 tuples
            # ('noAuthNoPriv', "username")
            # ('authNoPriv', 'md5', '11111111', '22222222')
            # ('authPriv', 'md5', '11111111', '22222222', 'DES', '33333333')

            # Insert preconfigured communitiy
            if test == "snmpv3":
                if snmpv3_use:
                    snmpv3_credentials = [snmpv3_use]
                    if snmpv3_use in ["authNoPriv", "authPriv"]:
                        snmpv3_credentials.extend([snmpv3_auth_proto, snmpv3_security_name, snmpv3_security_password])
                    else:
                        snmpv3_credentials.extend([snmpv3_security_name])
                    if snmpv3_use == "authPriv":
                        snmpv3_credentials.extend([snmpv3_privacy_proto, snmpv3_privacy_password])
                    config.explicit_snmp_communities[hostname] = tuple(snmpv3_credentials)
            elif snmp_community:
                config.explicit_snmp_communities[hostname] = snmp_community

            # Determine SNMPv2/v3 community
            if hostname not in config.explicit_snmp_communities:
                communities = rulesets.host_extra_conf(hostname, config.snmp_communities)
                for entry in communities:
                    if (type(entry) == tuple) == (test == "snmpv3"):
                        config.explicit_snmp_communities[hostname] = entry
                        break

            # Override timing settings if provided
            if snmp_timeout or snmp_retries:
                timing = {}
                if snmp_timeout:
                    timing['timeout'] = snmp_timeout
                if snmp_retries:
                    timing['retries'] = snmp_retries
                config.snmp_timing.insert(0, (timing, [], [hostname]))

            # SNMP versions
            if test in ['snmpv2', 'snmpv3']:
                config.bulkwalk_hosts = [hostname]
            elif test == 'snmpv2_nobulk':
                config.bulkwalk_hosts = []
                config.snmpv2c_hosts  = [hostname]
            elif test == 'snmpv1':
                config.bulkwalk_hosts = []
                config.snmpv2c_hosts  = []

            else:
                return 1, "SNMP command not implemented"

            data = snmp.get_snmp_table(hostname, ipaddress, None,
                                  ('.1.3.6.1.2.1.1', ['1.0', '4.0', '5.0', '6.0']), use_snmpwalk_cache=True)
            if data:
                return 0, 'sysDescr:\t%s\nsysContact:\t%s\nsysName:\t%s\nsysLocation:\t%s\n' % tuple(data[0])
            else:
                return 1, 'Got empty SNMP response'

        else:
            return 1, "Command not implemented"

    except Exception, e:
        if cmk.debug.enabled():
            raise
        return 1, str(e)

# WATO calls this automation when hosts have been renamed. We need to change
# several file and directory names. This function has no argument but reads
# Python pair-list from stdin:
# [("old1", "new1"), ("old2", "new2")])
def automation_rename_hosts():
    renamings = eval(sys.stdin.read())

    actions = []

    # At this place WATO already has changed it's configuration. All further
    # data might be changed by the still running core. So we need to stop
    # it now.
    core_was_running = core_is_running()
    if core_was_running:
        do_core_action("stop", quiet=True)

    for oldname, newname in renamings:
        # Autochecks: simply read and write out the file again. We do
        # not store a host name here anymore - but old versions did.
        # by rewriting we get rid of the host name.
        actions += rename_host_autochecks(oldname, newname)
        actions += rename_host_files(oldname, newname)

    # Start monitoring again. In case of CMC we need to ignore
    # any configuration created by the CMC Rushahead daemon
    if core_was_running:
        # force config generation to succeed. The core *must* start.
        # TODO: Can't we drop this hack since we have config warnings now?
        core_config.ignore_ip_lookup_failures()
        automation_restart("start")

        for hostname in core_config.failed_ip_lookups():
            actions.append("dnsfail-" + hostname)

    # Convert actions into a dictionary { "what" : count }
    action_counts = {}
    for action in actions:
        action_counts.setdefault(action, 0)
        action_counts[action] += 1

    return action_counts


def rename_host_autochecks(oldname, newname):
    actions = []
    acpath = cmk.paths.autochecks_dir + "/" + oldname + ".mk"
    if os.path.exists(acpath):
        old_autochecks = parse_autochecks_file(oldname)
        out = file(cmk.paths.autochecks_dir + "/" + newname + ".mk", "w")
        out.write("[\n")
        for ct, item, paramstring in old_autochecks:
            out.write("  (%r, %r, %s),\n" % (ct, item, paramstring))
        out.write("]\n")
        out.close()
        os.remove(acpath) # Remove old file
        actions.append("autochecks")
    return actions


def rename_host_files(oldname, newname):
    actions = []

    # Rename temporary files of the host
    for d in [ "cache", "counters" ]:
        if rename_host_file(cmk.paths.tmp_dir + "/" + d + "/", oldname, newname):
            actions.append(d)

    if rename_host_dir(cmk.paths.tmp_dir + "/piggyback/", oldname, newname):
        actions.append("piggyback-load")

    # Rename piggy files *created* by the host
    piggybase = cmk.paths.tmp_dir + "/piggyback/"
    if os.path.exists(piggybase):
        for piggydir in os.listdir(piggybase):
            if rename_host_file(piggybase + piggydir, oldname, newname):
                actions.append("piggyback-pig")

    # Logwatch
    if rename_host_dir(cmk.paths.logwatch_dir, oldname, newname):
        actions.append("logwatch")

    # SNMP walks
    if rename_host_file(cmk.paths.snmpwalks_dir, oldname, newname):
        actions.append("snmpwalk")

    # HW/SW-Inventory
    if rename_host_file(cmk.paths.var_dir + "/inventory", oldname, newname):
        rename_host_file(cmk.paths.var_dir + "/inventory", oldname + ".gz", newname + ".gz")
        actions.append("inv")

    if rename_host_dir(cmk.paths.var_dir + "/inventory_archive", oldname, newname):
        actions.append("invarch")

    # Baked agents
    baked_agents_dir = cmk.paths.var_dir + "/agents/"
    have_renamed_agent = False
    if os.path.exists(baked_agents_dir):
        for opsys in os.listdir(baked_agents_dir):
            if rename_host_file(baked_agents_dir + opsys, oldname, newname):
                have_renamed_agent = True
    if have_renamed_agent:
        actions.append("agent")

    # Agent deployment
    deployment_dir = cmk.paths.var_dir + "/agent_deployment/"
    if rename_host_file(deployment_dir, oldname, newname):
        actions.append("agent_deployment")

    actions += omd_rename_host(oldname, newname)

    return actions


def rename_host_dir(basedir, oldname, newname):
    import shutil
    if os.path.exists(basedir + "/" + oldname):
        if os.path.exists(basedir + "/" + newname):
            shutil.rmtree(basedir + "/" + newname)
        os.rename(basedir + "/" + oldname, basedir + "/" + newname)
        return 1
    return 0

def rename_host_file(basedir, oldname, newname):
    if os.path.exists(basedir + "/" + oldname):
        if os.path.exists(basedir + "/" + newname):
            os.remove(basedir + "/" + newname)
        os.rename(basedir + "/" + oldname, basedir + "/" + newname)
        return 1
    return 0

# This functions could be moved out of Check_MK.
def omd_rename_host(oldname, newname):
    oldregex = oldname.replace(".", "[.]")
    newregex = newname.replace(".", "[.]")
    actions = []

    # Temporarily stop processing of performance data
    npcd_running = os.path.exists(cmk.paths.omd_root + "/tmp/pnp4nagios/run/npcd.pid")
    if npcd_running:
        os.system("omd stop npcd >/dev/null 2>&1 </dev/null")

    rrdcache_running = os.path.exists(cmk.paths.omd_root + "/tmp/run/rrdcached.sock")
    if rrdcache_running:
        os.system("omd stop rrdcached >/dev/null 2>&1 </dev/null")

    # Fix pathnames in XML files
    dirpath = cmk.paths.omd_root + "/var/pnp4nagios/perfdata/" + oldname
    os.system("sed -i 's@/perfdata/%s/@/perfdata/%s/@' %s/*.xml 2>/dev/null" % (oldname, newname, dirpath))

    # RRD files
    if rename_host_dir(cmk.paths.omd_root + "/var/pnp4nagios/perfdata", oldname, newname):
        actions.append("rrd")

    # RRD files
    if rename_host_dir(cmk.paths.omd_root + "/var/check_mk/rrd", oldname, newname):
        actions.append("rrd")

    # entries of rrdcached journal
    dirpath = cmk.paths.omd_root + "/var/rrdcached/"
    if not os.system("sed -i 's@/perfdata/%s/@/perfdata/%s/@' "
        "%s/var/rrdcached/rrd.journal.* 2>/dev/null" % ( oldregex, newregex, cmk.paths.omd_root)):
        actions.append("rrdcached")

    # Spoolfiles of NPCD
    if not os.system("sed -i 's/HOSTNAME::%s	/HOSTNAME::%s	/' "
                     "%s/var/pnp4nagios/perfdata.dump %s/var/pnp4nagios/spool/perfdata.* 2>/dev/null" % (
                     oldregex, newregex, cmk.paths.omd_root, cmk.paths.omd_root)):
        actions.append("pnpspool")

    if rrdcache_running:
        os.system("omd start rrdcached >/dev/null 2>&1 </dev/null")

    if npcd_running:
        os.system("omd start npcd >/dev/null 2>&1 </dev/null")

    # Logfiles and history files of CMC and Nagios. Problem
    # here: the exact place of the hostname varies between the
    # various log entry lines
    sed_commands = r'''
s/(INITIAL|CURRENT) (HOST|SERVICE) STATE: %(old)s;/\1 \2 STATE: %(new)s;/
s/(HOST|SERVICE) (DOWNTIME |FLAPPING |)ALERT: %(old)s;/\1 \2ALERT: %(new)s;/
s/PASSIVE (HOST|SERVICE) CHECK: %(old)s;/PASSIVE \1 CHECK: %(new)s;/
s/(HOST|SERVICE) NOTIFICATION: ([^;]+);%(old)s;/\1 NOTIFICATION: \2;%(new)s;/
''' % { "old" : oldregex, "new" : newregex }
    patterns = [
        "var/check_mk/core/history",
        "var/check_mk/core/archive/*",
        "var/nagios/nagios.log",
        "var/nagios/archive/*",
    ]
    one_matched = False
    for pattern in patterns:
        command = "sed -ri --file=/dev/fd/0 %s/%s >/dev/null 2>&1" % (cmk.paths.omd_root, pattern)
        p = os.popen(command, "w")
        p.write(sed_commands)
        if not p.close():
            one_matched = True
    if one_matched:
        actions.append("history")

    # State retention (important for Downtimes, Acknowledgements, etc.)
    if config.monitoring_core == "nagios":
        if not os.system("sed -ri 's/^host_name=%s$/host_name=%s/' %s/var/nagios/retention.dat" % (
                    oldregex, newregex, cmk.paths.omd_root)):
            actions.append("retention")

    else: # CMC
        # Create a file "renamed_hosts" with the information about the
        # renaming of the hosts. The core will honor this file when it
        # reads the status file with the saved state.
        file(cmk.paths.var_dir + "/core/renamed_hosts", "w").write("%s\n%s\n" % (oldname, newname))
        actions.append("retention")

    # NagVis maps
    if not os.system("sed -i 's/^[[:space:]]*host_name=%s[[:space:]]*$/host_name=%s/' "
                     "%s/etc/nagvis/maps/*.cfg 2>/dev/null" % (
                     oldregex, newregex, cmk.paths.omd_root)):
        actions.append("nagvis")

    return actions


def automation_notification_replay(args):
    nr = args[0]
    return notification_replay_backlog(int(nr))


def automation_notification_analyse(args):
    nr = args[0]
    return notification_analyse_backlog(int(nr))


def automation_get_bulks(args):
    only_ripe = args[0] == "1"
    return find_bulks(only_ripe)


def automation_active_check(args):
    hostname, plugin, item = args
    item = item.decode("utf-8")

    if plugin == "custom":
        custchecks = rulesets.host_extra_conf(hostname, config.custom_checks)
        for entry in custchecks:
            if entry["service_description"] == item:
                command_line = replace_core_macros(hostname, entry.get("command_line", ""))
                if command_line:
                    command_line = core_config.autodetect_plugin(command_line)
                    return execute_check_plugin(command_line)
                else:
                    return -1, "Passive check - cannot be executed"
    else:
        rules = config.active_checks.get(plugin)
        if rules:
            entries = rulesets.host_extra_conf(hostname, rules)
            if entries:
                act_info = checks.active_check_info[plugin]
                for params in entries:
                    description = act_info["service_description"](params).replace('$HOSTNAME$', hostname)
                    if description == item:
                        args = core_config.active_check_arguments(hostname, description, act_info["argument_function"](params))
                        command_line = replace_core_macros(hostname, act_info["command_line"].replace("$ARG1$", args))
                        return execute_check_plugin(command_line)


def load_resource_file(macros):
    try:
        for line in file(cmk.paths.omd_root + "/etc/nagios/resource.cfg"):
            line = line.strip()
            if not line or line[0] == '#':
                continue
            varname, value = line.split('=', 1)
            macros[varname] = value
    except:
        if cmk.debug.enabled():
            raise


# Simulate replacing some of the more important macros of hosts. We
# cannot use dynamic macros, of course. Note: this will not work
# without OMD, since we do not know the value of $USER1$ and $USER2$
# here. We could read the Nagios resource.cfg file, but we do not
# know for sure the place of that either.
def replace_core_macros(hostname, commandline):
    macros = core_config.get_host_macros_from_attributes(hostname,
                         core_config.get_host_attributes(hostname, tags_of_host(hostname)))
    load_resource_file(macros)
    for varname, value in macros.items():
        commandline = commandline.replace(varname, "%s" % value)
    return commandline


def execute_check_plugin(commandline):
    try:
        p = os.popen(commandline + " 2>&1")
        output = p.read().strip()
        ret = p.close()
        if not ret:
            status = 0
        else:
            if ret & 0xff == 0:
                status = ret / 256
            else:
                status = 3
        if status < 0 or  status > 3:
            status = 3
        output = output.split("|",1)[0] # Drop performance data
        return status, output

    except Exception, e:
        if cmk.debug.enabled():
            raise
        return 3, "UNKNOWN - Cannot execute command: %s" % e


def automation_update_dns_cache():
    return ip_lookup.update_dns_cache()


def automation_bake_agents():
    if "do_bake_agents" in globals():
        return do_bake_agents()


def automation_get_agent_output(args):
    hostname, ty = args

    success    = True
    output     = ""
    agent_data = ""

    try:
        if ty == "agent":
            agent_data = get_plain_hostinfo(hostname)
        else:
            path = cmk.paths.snmpwalks_dir + "/" + hostname
            do_snmpwalk_on(hostname, path)
            agent_data = file(path).read()
    except Exception, e:
        success = False
        output = "Failed to fetch data from %s: %s\n" % (hostname, e)
        if cmk.debug.enabled():
            raise

    return success, output, agent_data


def automation_get_package_info(args):
    import cmk_base.packaging
    packages = {}
    for package_name in cmk_base.packaging.all_package_names():
        packages[package_name] = cmk_base.packaging.read_package_info(package_name)

    return {
        "installed"  : packages,
        "unpackaged" : cmk_base.packaging.unpackaged_files(),
        "parts"      : cmk_base.packaging.package_part_info(),
    }


def automation_get_package(args):
    import cmk_base.packaging
    package_name = args[0]
    package = cmk_base.packaging.read_package_info(package_name)
    if not package:
        raise MKAutomationError("Package not installed or corrupt")

    output_file = StringIO()
    cmk_base.packaging.create_mkp_file(package, file_object=output_file)
    return package, output_file.getvalue()


def automation_create_or_edit_package(args, mode):
    import cmk_base.packaging
    package_name = args[0]
    new_package_info = eval(sys.stdin.read())
    if mode == "create":
        cmk_base.packaging.create_package(new_package_info)
    else:
        cmk_base.packaging.edit_package(package_name, new_package_info)
    return None


def automation_install_package(args):
    import cmk_base.packaging
    input_file = StringIO(sys.stdin.read())
    try:
        return cmk_base.packaging.install_package(file_object=input_file)
    except Exception, e:
        if cmk.debug.enabled():
            raise
        raise MKAutomationError("Cannot install package: %s" % e)


def automation_remove_or_release_package(args, mode):
    import cmk_base.packaging
    package_name = args[0]
    package = cmk_base.packaging.read_package_info(package_name)
    if not package:
        raise MKAutomationError("Package not installed or corrupt")
    if mode == "remove":
        cmk_base.packaging.remove_package(package)
    else:
        cmk_base.packaging.remove_package_info(package_name)
    return None


def automation_remove_unpackaged_file(args):
    import cmk_base.packaging
    part_name = args[0]
    if part_name not in [ p[0] for p in cmk_base.packaging.package_parts ]:
        raise MKAutomationError("Invalid package part")

    rel_path = args[1]
    if "../" in rel_path or rel_path.startswith("/"):
        raise MKAutomationError("Invalid file name")

    for part, _unused_title, _unused_perm, dir in cmk_base.packaging.package_parts:
        if part == part_name:
            abspath = dir + "/" + rel_path
            if not os.path.isfile(abspath):
                raise MKAutomationError("No such file")
            os.remove(abspath)
    return None
