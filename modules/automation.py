#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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
        else:
            read_config_files()
            if cmd == "try-inventory":
                result = automation_try_inventory(args)
            elif cmd == "inventory":
                result = automation_inventory(args)
            elif cmd == "get-autochecks":
                result = automation_get_autochecks(args)
            elif cmd == "set-autochecks":
                result = automation_set_autochecks(args)
            elif cmd == "reload":
                result = automation_restart("reload")
            elif cmd == "restart":
                result = automation_restart("restart")
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
def automation_inventory(args):
    if len(args) < 2:
        raise MKAutomationError("Need two arguments: [new|remove|fixall|refresh] HOSTNAME")

    how = args[0]
    hostname = args[1]

    count_added = 0
    count_removed = 0
    count_kept = 0
    if how == "refresh":
        count_removed = remove_autochecks_of(hostname) # checktype could be added here
        reread_autochecks()

    # Compute current state of new and existing checks
    table = automation_try_inventory([hostname])
    # Create new list of checks
    new_items = []
    for entry in table:
        state_type, ct, checkgroup, item, paramstring = entry[:5]
        if state_type in [ "legacy", "manual", "ignored" ]:
            continue # this is not an autocheck or ignored and currently not checked

        if state_type == "new":
            if how in [ "new", "fixall", "refresh" ]:
                count_added += 1
                new_items.append((ct, item, paramstring))

        elif state_type == "old":
            # keep currently existing valid services in any case
            new_items.append((ct, item, paramstring))
            count_kept += 1

        elif state_type in [ "obsolete", "vanished" ]:
            # keep item, if we are currently only looking for new services
            # otherwise fix it: remove ignored and non-longer existing services
            if how not in [ "fixall", "remove" ]:
                new_items.append((ct, item, paramstring))
                count_kept += 1
            else:
                count_removed += 1

    automation_write_autochecks_file(hostname, new_items)
    return (count_added, count_removed, count_kept, len(new_items))


def automation_try_inventory(args):
    global opt_use_cachefile, opt_no_tcp, opt_dont_submit, \
            inventory_max_cachefile_age, check_max_cachefile_age
    if args[0] == '--cache':
        opt_use_cachefile = True
        check_max_cachefile_age = 1000000000
        inventory_max_cachefile_age = 1000000000
        args = args[1:]

    hostname = args[0]

    # hostname might be a cluster. In that case we compute the clustered
    # services of that cluster.
    services = []
    if is_cluster(hostname):
        descriptions = set([])
        for node in nodes_of(hostname):
            new_services = automation_try_inventory_node(node)
            for entry in new_services:
                if host_of_clustered_service(node, entry[6]) == hostname:
                    if entry[6] not in descriptions:
                        services.append(entry)
                        descriptions.add(entry[6]) # make it unique

    else:
        new_services = automation_try_inventory_node(hostname)
        for entry in new_services:
            if host_of_clustered_service(hostname, entry[6]) == hostname:
                services.append(entry)

    return services

        

def automation_try_inventory_node(hostname):
    global opt_use_cachefile

    try:
        ipaddress = lookup_ipaddress(hostname)
    except:
        raise MKAutomationError("Cannot lookup IP address of host %s" % hostname)

    f = []

    # if we are using cache files, then we restrict us to existing
    # check types. SNMP scan is only done without the --cache option
    if is_snmp_host(hostname):
        if opt_use_cachefile:
            existing_checks = set([ cn for (cn, item) in get_check_table(hostname) ])
            for cn in inventorable_checktypes("snmp"):
                if cn in existing_checks:
                    f += make_inventory(cn, [hostname], True, True)
        else:
            f = do_snmp_scan([hostname], True, True)

    if is_tcp_host(hostname):
        for cn in inventorable_checktypes("tcp"):
            f += make_inventory(cn, [hostname], True, True)

    found = {}
    for hn, ct, item, paramstring, state_type in f:
       found[(ct, item)] = ( state_type, paramstring )

    # Check if already in autochecks (but not found anymore)
    for hn, ct, item, params in autochecks:
        if hn == hostname and (ct, item) not in found:
            found[(ct, item)] = ( 'vanished', repr(params) ) # This is not the real paramstring!

    # Find manual checks
    existing = get_check_table(hostname)
    for (ct, item), (params, descr, deps) in existing.items():
        if (ct, item) not in found:
            found[(ct, item)] = ('manual', repr(params) )

    # Add legacy checks with artificial type 'legacy'
    legchecks = host_extra_conf(hostname, legacy_checks)
    for cmd, descr, perf in legchecks:
        found[('legacy', descr)] = ( 'legacy', 'None' )

    table = []
    for (ct, item), (state_type, paramstring) in found.items():
        if state_type != 'legacy':
            descr = service_description(ct, item)
            infotype = ct.split('.')[0]
            opt_use_cachefile = True
            opt_no_tcp = True
            opt_dont_submit = True

            try:
                info = get_host_info(hostname, ipaddress, infotype)
            # Handle cases where agent does not output data
            except MKAgentError, e:
                if str(e) == "":
                    continue
                else:
                    raise
            except MKSNMPError, e:
                if str(e) == "":
                    continue
                else:
                    raise

            check_function = check_info[ct][0]
            # apply check_parameters
            try:
                if type(paramstring) == str:
                    params = eval(paramstring)
                else:
                    params = paramstring
            except:
                raise MKAutomationError("Invalid check parameter string '%s'" % paramstring)
            if state_type != 'manual':
                params = compute_check_parameters(hostname, ct, item, params)

            try:
                result = check_function(item, params, info)
            except MKCounterWrapped, e:
                result = (None, "WAITING - Counter based check, cannot be done offline")
            except Exception, e:
                result = (3, "UNKNOWN - invalid output from agent or error in check implementation")
            if len(result) == 2:
                result = (result[0], result[1], [])
            exitcode, output, perfdata = result
        else:
            descr = item
            exitcode = None
            output = "WAITING - Legacy check, cannot be done offline"
            perfdata = []
        checkgroup = checkgroup_of.get(ct)
        table.append((state_type, ct, checkgroup, item, paramstring, params, descr, exitcode, output, perfdata))

    return table

# Set the new list of autochecks. This list is specified by a
# table of (checktype, item). No parameters are specified. Those
# are either (1) kept from existing autochecks or (2) computed
# from a new inventory. Note: we must never convert check parameters
# from python source code to actual values.
def automation_set_autochecks(args):
    hostname = args[0]
    new_items = eval(sys.stdin.read())

    do_cleanup_autochecks()
    existing = automation_parse_autochecks_file(hostname)

    # write new autochecks file, but take paramstrings from existing ones
    # for those checks which are kept
    new_autochecks = []
    for ct, item, params, paramstring in existing:
        if (ct, item) in new_items:
            new_autochecks.append((ct, item, paramstring))
            del new_items[(ct, item)]

    for (ct, item), paramstring in new_items.items():
        new_autochecks.append((ct, item, paramstring))

    # write new autochecks file for that host
    automation_write_autochecks_file(hostname, new_autochecks)


def automation_get_autochecks(args):
    hostname = args[0]
    do_cleanup_autochecks()
    return automation_parse_autochecks_file(hostname)

def automation_write_autochecks_file(hostname, table):
    if not os.path.exists(autochecksdir):
        os.makedirs(autochecksdir)
    path = "%s/%s.mk" % (autochecksdir, hostname)
    f = file(path, "w")
    f.write("# Autochecks for host %s, created by Check_MK automation\n[\n" % hostname)
    for ct, item, paramstring in table:
        f.write("  (%r, %r, %r, %s),\n" % (hostname, ct, item, paramstring))
    f.write("]\n")

def automation_parse_autochecks_file(hostname):
    def split_python_tuple(line):
        quote = None
        bracklev = 0
        backslash = False
        for i, c in enumerate(line):
            if backslash:
                backslash = False
                continue
            elif c == '\\':
                backslash = True
            elif c == quote:
                quote = None # end of quoted string
            elif c in [ '"', "'" ]:
                quote = c # begin of quoted string
            elif quote:
                continue
            elif c in [ '(', '{', '[' ]:
                bracklev += 1
            elif c in [ ')', '}', ']' ]:
                bracklev -= 1
            elif bracklev > 0:
                continue
            elif c == ',':
                value = line[0:i]
                rest = line[i+1:]
                return value.strip(), rest
        return line.strip(), None

    path = "%s/%s.mk" % (autochecksdir, hostname)
    if not os.path.exists(path):
        return []
    lineno = 0

    table = []
    for line in file(path):
        lineno += 1
        try:
            line = line.strip()
            if not line.startswith("("):
                continue

            # drop everything after potential '#' (from older versions)
	    i = line.rfind('#')
	    if i > 0: # make sure # is not contained in string
		rest = line[i:]
		if '"' not in rest and "'" not in rest:
		    line = line[:i].strip()

            if line.endswith(","):
                line = line[:-1]
            line = line[1:-1] # drop brackets

            hostnamestring, line = split_python_tuple(line) # should be hostname
            checktypestring, line = split_python_tuple(line)
            itemstring, line = split_python_tuple(line)
            paramstring, line = split_python_tuple(line)
            table.append((eval(checktypestring), eval(itemstring), eval(paramstring), paramstring))
        except:
            if opt_debug:
                raise
            raise MKAutomationError("Invalid line %d in autochecks file %s" % (lineno, path))
    return table

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

def automation_restart(job="restart"):
    # make sure, Nagios does not inherit any open
    # filedescriptors. This really happens, e.g. if
    # check_mk is called by WATO via Apache. Nagios inherits
    # the open file where Apache is listening for incoming
    # HTTP connections. Really.
    for fd in range(3, 256):
        try:
            os.close(fd)
        except:
            pass
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
        if os.path.exists(nagios_objects_file):
            backup_path = nagios_objects_file + ".save"
            os.rename(nagios_objects_file, backup_path)
        else:
            backup_path = None

        try:
	    create_nagios_config(file(nagios_objects_file, "w"))
        except Exception, e:
	    if backup_path:
		os.rename(backup_path, nagios_objects_file)
	    raise MKAutomationError("Error creating configuration: %s" % e)

        if do_check_nagiosconfig():
            if backup_path:
                os.remove(backup_path)
            do_precompile_hostchecks()
            if job == 'restart': 
                do_restart_nagios(False) 
            elif job == 'reload':
                do_restart_nagios(True)
        else:
            if backup_path:
                os.rename(backup_path, nagios_objects_file)
            else:
                os.remove(nagios_objects_file)
            raise MKAutomationError("Nagios configuration is invalid. Rolling back.")

    except Exception, e:
        if backup_path and os.path.exists(backup_path):
            os.remove(backup_path)
        raise MKAutomationError(str(e))

    sys.stdout = old_stdout

def automation_get_configuration():
    # We read the list of variable names from stdin since
    # that could be too much for the command line
    variable_names = eval(sys.stdin.read())
    result = {}
    for varname in variable_names:
        if varname in globals():
            result[varname] = globals()[varname]
    return result

def automation_get_check_information():
    manuals = all_manuals()
    checks = {}
    for checkname in check_info:
        manfile = manuals.get(checkname)
        if manfile:
            title = file(manfile).readline().strip().split(":", 1)[1].strip()
        else:
            title = checkname
        checks[checkname] = { "title" : title }
        if checkname in checkgroup_of:
            checks[checkname]["group"] = checkgroup_of[checkname]
    return checks
