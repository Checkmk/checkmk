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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.


class MKAutomationError(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason

def do_automation(cmd, args):
    try:
        if cmd == "get-configuration":
            read_config_files(with_autochecks=False, with_conf_d=False)
            result = automation_get_configuration()
        elif cmd == "get-check-information":
            result = automation_get_check_information()
        elif cmd == "delete-host":
            read_config_files(with_autochecks=False)
            result = automation_delete_host(args)
        elif cmd == "notification-get-bulks":
            result = automation_get_bulks(args)
        elif cmd == "update-dns-cache":
            read_config_files(with_autochecks=False)
            result = automation_update_dns_cache()
        else:
            read_config_files()
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
            elif cmd == "rename-host":
                result = automation_rename_host(args)
            elif cmd == "create-snapshot":
                result = automation_create_snapshot(args)
	    elif cmd == "notification-replay":
		result = automation_notification_replay(args)
	    elif cmd == "notification-analyse":
		result = automation_notification_analyse(args)
            elif cmd == "bake-agents":
                result = automation_bake_agents()
            else:
                raise MKAutomationError("Automation command '%s' is not implemented." % cmd)

    except MKAutomationError, e:
        sys.stderr.write("%s\n" % e)
        if opt_debug:
            raise
        output_profile()
        sys.exit(1)

    except Exception, e:
        if opt_debug:
            raise
        else:
            sys.stderr.write("%s\n" % e)
            output_profile()
            sys.exit(2)

    if opt_debug:
        import pprint
        sys.stdout.write(pprint.pformat(result)+"\n")
    else:
        sys.stdout.write("%r\n" % (result,))
    output_profile()
    sys.exit(0)

# Does inventory for *one* host. Possible values for how:
# "new" - find only new services (like -I)
# "remove" - remove exceeding services
# "fixall" - find new, remove exceeding
# "refresh" - drop all services and reinventorize
def automation_discovery(args):

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
        counts.setdefault(hostname, [0, 0, 0, 0]) # added, removed, kept, total
        try:
            # in "refresh" mode we first need to remove all previously discovered
            # checks of the host, so that get_host_services() does show us the
            # new discovered check parameters.
            if how == "refresh":
                counts[hostname][1] += remove_autochecks_of(hostname) # this is cluster-aware!

            # Compute current state of new and existing checks
            services = get_host_services(hostname, use_caches=use_caches, do_snmp_scan=do_snmp_scan)

            # Create new list of checks
            new_items = {}
            for (check_type, item), (check_source, paramstring) in services.items():
                if check_source in ("custom", "legacy", "active", "manual"):
                    continue # this is not an autocheck or ignored and currently not checked
                    # Note discovered checks that are shadowed by manual checks will vanish
                    # that way.

                if check_source in ("new"):
                    if how in ("new", "fixall", "refresh"):
                        counts[hostname][0] += 1 # added
                        counts[hostname][3] += 1 # total
                        new_items[(check_type, item)] = paramstring

                elif check_source in ("old", "ignored"):
                    # keep currently existing valid services in any case
                    new_items[(check_type, item)] = paramstring
                    counts[hostname][2] += 1 # kept
                    counts[hostname][3] += 1 # total

                elif check_source in ("obsolete", "vanished"):
                    # keep item, if we are currently only looking for new services
                    # otherwise fix it: remove ignored and non-longer existing services
                    if how not in ("fixall", "remove"):
                        new_items[(check_type, item)] = paramstring
                        counts[hostname][2] += 1 # kept
                        counts[hostname][3] += 1 # total
                    else:
                        counts[hostname][1] += 1 # removed

                # Silently keep clustered services
                elif check_source.startswith("clustered_"):
                    new_items[(check_type, item)] = paramstring

                else:
                    raise MKGeneralException("Unknown check source '%s'" % check_source)

            set_autochecks_of(hostname, new_items)

        except Exception, e:
	    if opt_debug:
                raise
            failed_hosts[hostname] = str(e)

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

    # TODO: Remove this unlucky option opt_use_cachefile. At least do not
    # handle this option so deep in the code. It should only be handled
    # by top-level functions.
    global opt_use_cachefile, check_max_cachefile_age
    opt_use_cachefile = use_caches
    if use_caches:
        check_max_cachefile_age = inventory_max_cachefile_age
    hostname = args[0]
    table = get_check_preview(hostname, use_caches=use_caches, do_snmp_scan=do_snmp_scan)
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

def set_autochecks_of(hostname, new_items):
    # A Cluster does not have an autochecks file
    # All of its services are located in the nodes instead
    # So we cycle through all nodes remove all clustered service
    # and add the ones we've got from stdin
    if is_cluster(hostname):
        for node in nodes_of(hostname):
            new_autochecks = []
            existing = parse_autochecks_file(node)
            for check_type, item, paramstring in existing:
                descr = service_description(check_type, item)
                if hostname != host_of_clustered_service(node, descr):
                    new_autochecks.append((check_type, item, paramstring))
            for (check_type, item), paramstring in new_items.items():
                new_autochecks.append((check_type, item, paramstring))
            # write new autochecks file for that host
            automation_write_autochecks_file(node, new_autochecks)
    else:
        existing = parse_autochecks_file(hostname)
        # write new autochecks file, but take paramstrings from existing ones
        # for those checks which are kept
        new_autochecks = []
        for ct, item, paramstring in existing:
            if (ct, item) in new_items:
                new_autochecks.append((ct, item, paramstring))
                del new_items[(ct, item)]

        for (ct, item), paramstring in new_items.items():
            new_autochecks.append((ct, item, paramstring))

        # write new autochecks file for that host
        automation_write_autochecks_file(hostname, new_autochecks)


def automation_write_autochecks_file(hostname, table):
    if not os.path.exists(autochecksdir):
        os.makedirs(autochecksdir)
    path = "%s/%s.mk" % (autochecksdir, hostname)
    f = file(path, "w")
    f.write("[\n")
    for check_type, item, paramstring in table:
        f.write("  (%r, %r, %s),\n" % (check_type, item, paramstring))
    f.write("]\n")
    if inventory_check_autotrigger and inventory_check_interval:
        schedule_inventory_check(hostname)


def automation_get_autochecks(args):
    hostname = args[0]
    result = []
    for ct, item, paramstring in parse_autochecks_file(hostname):
        result.append((ct, item, eval(paramstring), paramstring))
    return result


def schedule_inventory_check(hostname):
    try:
        import socket
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(livestatus_unix_socket)
        now = int(time.time())
        if 'cmk-inventory' in use_new_descriptions_for:
            command = "SCHEDULE_FORCED_SVC_CHECK;%s;Check_MK Discovery;%d" % (hostname, now)
        else:
            # FIXME: Remove this old name handling one day
            command = "SCHEDULE_FORCED_SVC_CHECK;%s;Check_MK inventory;%d" % (hostname, now)
        s.send("COMMAND [%d] %s\n" % (now, command))
    except Exception, e:
        if opt_debug:
            raise



# Determine the type of the check, and how the parameters are being
# constructed
def automation_analyse_service(args):
    global g_hostname
    hostname = args[0]
    servicedesc = args[1]
    g_hostname = hostname # To be sure for all subfunctions

    # We just consider types of checks that are managed via WATO.
    # We have the following possible types of services:
    # 1. manual checks (static_checks) (currently overriding inventorized checks)
    # 2. inventorized check
    # 3. classical checks
    # 4. active checks

    # Compute effective check table, in order to remove SNMP duplicates
    check_table = get_check_table(hostname, remove_duplicates = True)

    # 1. Manual checks
    for nr, (checkgroup, entries) in enumerate(static_checks.items()):
        for entry in entries:
            entry, rule_options = get_rule_options(entry)
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

            if hosttags_match_taglist(tags_of_host(hostname), taglist) and \
               in_extraconf_hostlist(hostlist, hostname):
               descr = service_description(checktype, item)
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
        path = "%s/%s.mk" % (autochecksdir, hostname)
        for entry in eval(file(path).read()):
            if len(entry) == 4: # old format
                hn, ct, item, params = entry
            else:
                ct, item, params = entry # new format without host name
                hn = hostname

            if (ct, item) not in check_table:
                continue # this is a removed duplicate or clustered service
            descr = service_description(ct, item)
            if hn == hostname and descr == servicedesc:
                dlv = check_info[ct].get("default_levels_variable")
                if dlv:
                    fs = factory_settings.get(dlv, None)
                else:
                    fs = None

                return {
                    "origin"           : "auto",
                    "checktype"        : ct,
                    "checkgroup"       : check_info[ct].get("group"),
                    "item"             : item,
                    "inv_parameters"   : params,
                    "factory_settings" : fs,
                    "parameters"       : compute_check_parameters(hostname, ct, item, params),
                }
    except:
        if opt_debug:
            raise

    # 3. Classical checks
    custchecks = host_extra_conf(hostname, custom_checks)
    for nr, entry in enumerate(custchecks):
        desc = entry["service_description"]
        if desc == servicedesc:
            result = {
                "origin"       : "classic",
                "rule_nr"      : nr,
            }
            if "command_line" in entry: # Only active checks have a command line
                result["command_line"] = entry["command_line"]
            return result

    # 4. Active checks
    for acttype, rules in active_checks.items():
        entries = host_extra_conf(hostname, rules)
        if entries:
            act_info = active_check_info[acttype]
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


def automation_delete_host(args):
    hostname = args[0]
    for path in [
        "%s/%s"    % (precompiled_hostchecks_dir, hostname),
        "%s/%s.py" % (precompiled_hostchecks_dir, hostname),
        "%s/%s.mk" % (autochecksdir, hostname),
        "%s/%s"    % (logwatch_dir, hostname),
        "%s/%s"    % (counters_directory, hostname),
        "%s/%s"    % (tcp_cache_dir, hostname),
        "%s/%s.*"  % (tcp_cache_dir, hostname)]:
        os.system("rm -rf '%s'" % path)

def automation_restart(job = "restart", use_rushd = True):
    # make sure, Nagios does not inherit any open
    # filedescriptors. This really happens, e.g. if
    # check_mk is called by WATO via Apache. Nagios inherits
    # the open file where Apache is listening for incoming
    # HTTP connections. Really.
    if monitoring_core == "nagios":
        objects_file = nagios_objects_file
        for fd in range(3, 256):
            try:
                os.close(fd)
            except:
                pass
    else:
        objects_file = var_dir + "/core/config"
        if job == "restart":
            job = "reload" # force reload for CMC

    # os.closerange(3, 256) --> not available in older Python versions

    class null_file:
        def write(self, stuff):
           pass
        def flush(self):
           pass

    # Deactivate stdout by introducing fake file without filedescriptor
    old_stdout = sys.stdout
    sys.stdout = null_file()

    try:
        backup_path = None
        if not lock_objects_file():
            raise MKAutomationError("Cannot activate changes. "
                  "Another activation process is currently in progresss")

        if os.path.exists(objects_file):
            backup_path = objects_file + ".save"
            os.rename(objects_file, backup_path)
        else:
            backup_path = None

        try:
            if monitoring_core == "nagios":
                create_nagios_config(file(objects_file, "w"))
            else:
                do_create_cmc_config(opt_cmc_relfilename, use_rushd = use_rushd)

            if "do_bake_agents" in globals() and bake_agents_on_restart:
                do_bake_agents()

        except Exception, e:
	    if backup_path:
		os.rename(backup_path, objects_file)
            if opt_debug:
                raise
	    raise MKAutomationError("Error creating configuration: %s" % e)

        if do_check_nagiosconfig():
            if backup_path:
                os.remove(backup_path)
            if monitoring_core == "cmc":
                do_pack_config()
            else:
                do_precompile_hostchecks()
            do_core_action(job)
        else:
            if backup_path:
                os.rename(backup_path, objects_file)
            else:
                os.remove(objects_file)
            raise MKAutomationError("Configuration for monitoring core is invalid. Rolling back.")

    except Exception, e:
        if backup_path and os.path.exists(backup_path):
            os.remove(backup_path)
        if opt_debug:
            raise
        raise MKAutomationError(str(e))

    sys.stdout = old_stdout

def automation_get_configuration():
    # We read the list of variable names from stdin since
    # that could be too much for the command line
    variable_names = eval(sys.stdin.read())
    result = {}
    for varname in variable_names:
        if varname in globals():
            if not hasattr(globals()[varname], '__call__'):
                result[varname] = globals()[varname]
    return result

def automation_get_check_information():
    manuals = all_manuals()
    checks = {}
    for check_type, check in check_info.items():
        manfile = manuals.get(check_type)
        if manfile:
            title = file(manfile).readline().strip().split(":", 1)[1].strip()
        else:
            title = check_type
        checks[check_type] = { "title" : title }
        if check["group"]:
            checks[check_type]["group"] = check["group"]
        checks[check_type]["service_description"] = check.get("service_description","%s")
        checks[check_type]["snmp"] = check_uses_snmp(check_type)
    return checks

def automation_scan_parents(args):
    settings = {
        "timeout"     : int(args[0]),
        "probes"      : int(args[1]),
        "max_ttl"     : int(args[2]),
        "ping_probes" : int(args[3]),
    }
    hostnames = args[4:]
    traceroute_prog = find_bin_in_path('traceroute')
    if not traceroute_prog:
        raise MKAutomationError("Cannot find binary <tt>traceroute</tt> in search path.")

    try:
        gateways = scan_parents_of(hostnames, silent=True, settings=settings)
        return gateways
    except Exception, e:
        raise MKAutomationError(str(e))

def automation_diag_host(args):
    import subprocess

    hostname, test, ipaddress, snmp_community = args[:4]
    agent_port, snmp_timeout, snmp_retries = map(int, args[4:7])
    cmd = args[7]

    if not ipaddress:
        try:
            ipaddress = lookup_ipaddress(hostname)
        except:
            raise MKGeneralException("Cannot resolve hostname %s into IP address" % hostname)

    try:
        if test == 'ping':
            p = subprocess.Popen('ping -A -i 0.2 -c 2 -W 5 %s 2>&1' % ipaddress, shell = True, stdout = subprocess.PIPE)
            response = p.stdout.read()
            return (p.wait(), response)

        elif test == 'agent':
            if not cmd:
                cmd = get_datasource_program(hostname, ipaddress)

            if cmd:
                return 0, get_agent_info_program(cmd)
            else:
                return 0, get_agent_info_tcp(hostname, ipaddress, agent_port or None)

        elif test == 'traceroute':
            traceroute_prog = find_bin_in_path('traceroute')
            if not traceroute_prog:
                return 1, "Cannot find binary <tt>traceroute</tt>."
            else:
                p = subprocess.Popen('traceroute -n %s 2>&1' % ipaddress, shell = True, stdout = subprocess.PIPE)
                response = p.stdout.read()
                return (p.wait(), response)

        elif test.startswith('snmp'):
            if snmp_community:
                explicit_snmp_communities[hostname] = snmp_community

            # override timing settings if provided
            if snmp_timeout or snmp_retries:
                timing = {}
                if snmp_timeout:
                    timing['timeout'] = snmp_timeout
                if snmp_retries:
                    timing['retries'] = snmp_retries
                snmp_timing.insert(0, (timing, [], [hostname]))

            # SNMP versions
            global bulkwalk_hosts, snmpv2c_hosts
            if test == 'snmpv2':
                bulkwalk_hosts = [hostname]

            elif test == 'snmpv2_nobulk':
                bulkwalk_hosts = []
                snmpv2c_hosts  = [hostname]
            elif test == 'snmpv1':
                bulkwalk_hosts = []
                snmpv2c_hosts  = []

            else:
                return 1, "SNMP command not implemented"

            data = get_snmp_table(hostname, ipaddress, None, ('.1.3.6.1.2.1.1', ['1.0', '4.0', '5.0', '6.0']))
            if data:
                return 0, 'sysDescr:\t%s\nsysContact:\t%s\nsysName:\t%s\nsysLocation:\t%s\n' % tuple(data[0])
            else:
                return 1, 'Got empty SNMP response'

        else:
            return 1, "Command not implemented"

    except Exception, e:
        if opt_debug:
            raise
        return 1, str(e)

# WATO calls this automation when a host has been renamed. We need to change
# several file and directory names.
# HIRN: Hier auch das neue Format berücksichtigen! Andererseits sollte
# eigentlich auch nix Schlimmes passieren, wenn der Hostname *nicht* in
# der Datei steht.
def automation_rename_host(args):
    oldname = args[0]
    newname = args[1]
    actions = []

    # Autochecks: simply read and write out the file again. We do
    # not store a host name here anymore - but old versions did.
    # by rewriting we get rid of the host name.

    acpath = autochecksdir + "/" + oldname + ".mk"
    if os.path.exists(acpath):
        old_autochecks = parse_autochecks_file(oldname)
        out = file(autochecksdir + "/" + newname + ".mk", "w")
        out.write("[\n")
        for ct, item, paramstring in old_autochecks:
            out.write("  (%r, %r, %s),\n" % (ct, item, paramstring))
        out.write("]\n")
        out.close()
        os.remove(acpath) # Remove old file
        actions.append("autochecks")

    # At this place WATO already has changed it's configuration. All further
    # data might be changed by the still running core. So we need to stop
    # it now.
    core_was_running = core_is_running()
    if core_was_running:
        do_core_action("stop", quiet=True)

    # Rename temporary files of the host
    for d in [ "cache", "counters" ]:
        if rename_host_file(tmp_dir + "/" + d + "/", oldname, newname):
            actions.append(d)

    if rename_host_dir(tmp_dir + "/piggyback/", oldname, newname):
        actions.append("piggyback-load")

    # Rename piggy files *created* by the host
    piggybase = tmp_dir + "/piggyback/"
    if os.path.exists(piggybase):
        for piggydir in os.listdir(piggybase):
            if rename_host_file(piggybase + piggydir, oldname, newname):
                actions.append("piggyback-pig")

    # Logwatch
    if rename_host_dir(logwatch_dir, oldname, newname):
        actions.append("logwatch")

    # SNMP walks
    if rename_host_file(snmpwalks_dir, oldname, newname):
        actions.append("snmpwalk")

    # OMD-Stuff. Note: The question really is whether this should be
    # included in Check_MK. The point is - however - that all these
    # actions need to take place while the core is stopped.
    if omd_root:
        actions += omd_rename_host(oldname, newname)

    # Start monitoring again. In case of CMC we need to ignore
    # any configuration created by the CMC Rushahead daemon
    if core_was_running:
        global ignore_ip_lookup_failures
        ignore_ip_lookup_failures = True # force config generation to succeed. The core *must* start.
        automation_restart("start", use_rushd = False)
        if monitoring_core == "cmc":
            try:
                os.remove(var_dir + "/core/config.rush")
                os.remove(var_dir + "/core/config.rush.id")
            except:
                pass

        if failed_ip_lookups:
            actions.append("ipfail")

    return actions


def rename_host_dir(basedir, oldname, newname):
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
    npcd_running = os.path.exists(omd_root + "/tmp/pnp4nagios/run/npcd.pid")
    if npcd_running:
        os.system("omd stop npcd >/dev/null 2>&1 </dev/null")

    rrdcache_running = os.path.exists(omd_root + "/tmp/run/rrdcached.sock")
    if rrdcache_running:
        os.system("omd stop rrdcached >/dev/null 2>&1 </dev/null")

    # Fix pathnames in XML files
    dirpath = omd_root + "/var/pnp4nagios/perfdata/" + oldname
    os.system("sed -i 's@/perfdata/%s/@/perfdata/%s/@' %s/*.xml 2>/dev/null" % (oldname, newname, dirpath))

    # RRD files
    if rename_host_dir(rrd_path, oldname, newname):
        actions.append("rrd")

    # entries of rrdcached journal
    dirpath = omd_root + "/var/rrdcached/"
    if not os.system("sed -i 's@/perfdata/%s/@/perfdata/%s/@' "
        "%s/var/rrdcached/rrd.journal.* 2>/dev/null" % ( oldregex, newregex, omd_root)):
        actions.append("rrdcached")

    # Spoolfiles of NPCD
    if not os.system("sed -i 's/HOSTNAME::%s	/HOSTNAME::%s	/' "
                     "%s/var/pnp4nagios/perfdata.dump %s/var/pnp4nagios/spool/perfdata.* 2>/dev/null" % (
                     oldregex, newregex, omd_root, omd_root)):
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
        command = "sed -ri --file=/dev/fd/0 %s/%s >/dev/null 2>&1" % (omd_root, pattern)
        p = os.popen(command, "w")
        p.write(sed_commands)
        if not p.close():
            one_matched = True
    if one_matched:
        actions.append("history")

    # State retention (important for Downtimes, Acknowledgements, etc.)
    if monitoring_core == "nagios":
        if not os.system("sed -ri 's/^host_name=%s$/host_name=%s/' %s/var/nagios/retention.dat" % (
                    oldregex, newregex, omd_root)):
            actions.append("retention")

    else: # CMC
        # Create a file "renamed_hosts" with the information about the
        # renaming of the hosts. The core will honor this file when it
        # reads the status file with the saved state.
        file(var_dir + "/core/renamed_hosts", "w").write("%s\n%s\n" % (oldname, newname))
        actions.append("retention")

    # NagVis maps
    if not os.system("sed -i 's/^[[:space:]]*host_name=%s[[:space:]]*$/host_name=%s/' "
                     "%s/etc/nagvis/maps/*.cfg 2>/dev/null" % (
                     oldregex, newregex, omd_root)):
        actions.append("nagvis")

    return actions



def automation_create_snapshot(args):
    try:
        import tarfile, time, cStringIO, shutil, subprocess, thread, traceback, threading
        from hashlib import sha256
        the_data = sys.stdin.read()
        data = eval(the_data)

        snapshot_name = data["snapshot_name"]
        snapshot_dir  = var_dir + "/wato/snapshots"
        work_dir       = snapshot_dir + "/workdir/%s" % snapshot_name
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)

        # Open / initialize files
        filename_target = "%s/%s"        % (snapshot_dir, snapshot_name)
        filename_work   = "%s/%s.work"   % (work_dir, snapshot_name)
        filename_status = "%s/%s.status" % (work_dir, snapshot_name)
        filename_pid    = "%s/%s.pid"    % (work_dir, snapshot_name)
        filename_subtar = ""
        current_domain  = ""

        file(filename_target, "w").close()
        file(filename_status, "w").close()

        def wipe_directory(path):
            for entry in os.listdir(path):
                if entry not in [ '.', '..' ]:
                    p = path + "/" + entry
                    if os.path.isdir(p):
                        shutil.rmtree(p)
                    else:
                        os.remove(p)

        lock_status_file = threading.Lock()
        def update_status_file(domain = None, infotext = None):
            lock_status_file.acquire()
            if os.path.exists(filename_status):
                if domain:
                    statusinfo[domain] = infotext
                statusfile = file(filename_status, "w")
                statusfile.write("comment:%s\n" % data.get("comment"," ").encode("utf-8"))
                status_list = list(statusinfo.items())
                status_list.sort()
                for status in status_list:
                    statusfile.write("%s.tar.gz:%s\n" % status)
            lock_status_file.release()

        # Set initial status info
        statusinfo = {}
        for name in data.get("domains", {}).keys():
            statusinfo[name] = "TODO:0"
        update_status_file()

        # Now fork into our own process to have an asynchronous backup creation
        try:
            pid = os.fork()
            if pid > 0:
                # Exit parent process
                return
            # Decouple from parent environment
            os.chdir("/")
            os.umask(0)
            os.setsid()

            # Close all fd except stdin,out,err
            for fd in range(3, 256):
                try:
                    os.close(fd)
                except OSError:
                    pass

            sys.stdout.flush()
            sys.stderr.flush()

            si = os.open("/dev/null", os.O_RDONLY)
            so = os.open("/dev/null", os.O_WRONLY)
            os.dup2(si, 0)
            os.dup2(so, 1)
            os.dup2(so, 2)
            os.close(si)
            os.close(so)

        except OSError, e:
            raise MKAutomationError(str(e))

        # Save pid of working process.
        file(filename_pid, "w").write("%d" % os.getpid())

        def cleanup():
            wipe_directory(work_dir)
            os.rmdir(work_dir)

        def check_should_abort():
            if not os.path.exists(filename_target):
                cleanup()
                sys.exit(0)

        def get_basic_tarinfo(name):
            tarinfo = tarfile.TarInfo(name)
            tarinfo.mtime = time.time()
            tarinfo.uid   = 0
            tarinfo.gid   = 0
            tarinfo.mode  = 0644
            tarinfo.type  = tarfile.REGTYPE
            return tarinfo

        def update_subtar_size(seconds):
            while current_domain != None:
                try:
                    if current_domain:
                        if os.path.exists(path_subtar):
                            update_status_file(current_domain, "Processing:%d" % os.stat(path_subtar).st_size)
                except:
                    pass
                time.sleep(seconds)

        def snapshot_secret():
            path = default_config_dir + '/snapshot.secret'
            try:
                return file(path).read()
            except IOError:
                # create a secret during first use
                try:
                    s = os.urandom(256)
                except NotImplementedError:
                    s = sha256(time.time())
                file(path, 'w').write(s)
                return s

        #
        # Initialize the snapshot tar file and populate with initial information
        #

        tar_in_progress = tarfile.open(filename_work, "w")

        # Add comment to tar file
        if data.get("comment"):
            tarinfo       = get_basic_tarinfo("comment")
            tarinfo.size  = len(data.get("comment").encode("utf-8"))
            tar_in_progress.addfile(tarinfo, cStringIO.StringIO(data.get("comment").encode("utf-8")))

        if data.get("created_by"):
            tarinfo       = get_basic_tarinfo("created_by")
            tarinfo.size  = len(data.get("created_by"))
            tar_in_progress.addfile(tarinfo, cStringIO.StringIO(data.get("created_by")))

        # Add snapshot type
        snapshot_type = data.get("type")
        tarinfo       = get_basic_tarinfo("type")
        tarinfo.size  = len(snapshot_type)
        tar_in_progress.addfile(tarinfo, cStringIO.StringIO(snapshot_type))

        # Close tar in progress, all other files are included via command line tar
        tar_in_progress.close()

        #
        # Process domains (sorted)
        #

        subtar_update_thread = thread.start_new_thread(update_subtar_size, (1,))
        domains = map(lambda x: x, data.get("domains").items())
        domains.sort()

        subtar_info = {}
        for name, info in domains:
            current_domain = name # Set name for update size thread
            prefix          = info.get("prefix","")
            exclude_options = ""
            for entry in info.get("exclude", []):
                exclude_options += "--exclude=%s " % entry

            check_should_abort()

            filename_subtar = "%s.tar.gz" % name
            path_subtar = "%s/%s" % (work_dir, filename_subtar)

            if info.get("backup_command"):
                command = info.get("backup_command") % {
                    "prefix"      : prefix,
                    "path_subtar" : path_subtar,
                    "work_dir"    : work_dir
                }
            else:
                paths = map(lambda x: x[1] == "" and "." or x[1], info.get("paths", []))
                command = "tar czf %s --ignore-failed-read --force-local %s -C %s %s" % \
                                        (path_subtar, exclude_options, prefix, " ".join(paths))

            proc = subprocess.Popen(command, shell=True, stdin=None, close_fds=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=prefix)
            stdout, stderr = proc.communicate()
            exit_code      = proc.wait()
            # Allow exit codes 0 and 1 (files changed during backup)
            if exit_code not in [0, 1]:
                raise MKAutomationError("Error while creating backup of %s (Exit Code %d) - %s.\n%s" %
							(current_domain, exit_code, stderr, command))

            subtar_size   = os.stat(path_subtar).st_size
            subtar_hash   = sha256(file(path_subtar).read()).hexdigest()
            subtar_signed = sha256(subtar_hash + snapshot_secret()).hexdigest()
            subtar_info[filename_subtar] = (subtar_hash, subtar_signed)

            # Append tar.gz subtar to snapshot
            command = "tar --append --file=%s %s ; rm %s" % \
                    (filename_work, filename_subtar, filename_subtar)
            proc = subprocess.Popen(command, shell=True, cwd = work_dir)
            proc.communicate()
            exit_code = proc.wait()
            if exit_code != 0:
                raise MKAutomationError("Error on adding backup domain %s to tarfile" % current_domain)

            current_domain = ""
            update_status_file(name, "Finished:%d" % subtar_size)

        # Now add the info file which contains hashes and signed hashes for
        # each of the subtars
        info = ''.join([ '%s %s %s\n' % (k, v[0], v[1]) for k, v in subtar_info.items() ]) + '\n'
        tar_in_progress = tarfile.open(filename_work, "a")
        tarinfo      = get_basic_tarinfo("checksums")
        tarinfo.size = len(info)
        tar_in_progress.addfile(tarinfo, cStringIO.StringIO(info))
        tar_in_progress.close()

        current_domain = None

        shutil.move(filename_work, filename_target)
        cleanup()

    except Exception, e:
        cleanup()
        raise MKAutomationError(str(e))


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
    actchecks = []
    needed_commands = []

    if plugin == "custom":
        custchecks = host_extra_conf(hostname, custom_checks)
        for entry in custchecks:
            if entry["service_description"] == item:
                command_line = replace_core_macros(hostname, entry.get("command_line", ""))
                if command_line:
                    command_line = autodetect_plugin(command_line)
                    return execute_check_plugin(command_line)
                else:
                    return -1, "Passive check - cannot be executed"
    else:
        rules = active_checks.get(plugin)
        if rules:
            entries = host_extra_conf(hostname, rules)
            if entries:
                act_info = active_check_info[plugin]
                for params in entries:
                    description = act_info["service_description"](params).replace('$HOSTNAME$', hostname)
                    if description == item:
                        args = act_info["argument_function"](params)
                        command_line = replace_core_macros(hostname, act_info["command_line"].replace("$ARG1$", args))
                        return execute_check_plugin(command_line)


def load_resource_file(macros):
    try:
        for line in file(omd_root + "/etc/nagios/resource.cfg"):
            line = line.strip()
            if not line or line[0] == '#':
                continue
            varname, value = line.split('=', 1)
            macros[varname] = value
    except:
        if opt_debug:
            raise

# Simulate replacing some of the more important macros of hosts. We
# cannot use dynamic macros, of course. Note: this will not work
# without OMD, since we do not know the value of $USER1$ and $USER2$
# here. We could read the Nagios resource.cfg file, but we do not
# know for sure the place of that either.
def replace_core_macros(hostname, commandline):
    macros  = {
        "$HOSTNAME$"    : hostname,
        "$HOSTADDRESS$" : lookup_ipaddress(hostname),
    }
    load_resource_file(macros)
    for varname, value in macros.items():
        commandline = commandline.replace(varname, value)
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
        if opt_debug:
            raise
        return 3, "UNKNOWN - Cannot execute command: %s" % e


def automation_update_dns_cache():
    return do_update_dns_cache()

def automation_bake_agents():
    if "do_bake_agents" in globals():
        return do_bake_agents()
