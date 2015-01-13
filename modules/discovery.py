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


# Changes from previous behaviour
#  - Syntax with hostname/ipaddress has been dropped

# Create a table of autodiscovered services of a host. Do not save
# this table anywhere. Do not read any previously discovered
# services.
# check_types: None -> try all check types, list -> omit scan in any case
# use_caches: True is cached agent data is being used (for -I without hostnames)
# do_snmp_scan: True if SNMP scan should be done (WATO: Full scan)
# Error situation (unclear what to do):
# - IP address cannot be looked up
#
# This function does not handle:
# - clusters
# - ignored services
#
# This function *does* handle:
# - ignored check typess
# 
def discover_services(hostname, check_types, use_caches, do_snmp_scan):
    ipaddress = lookup_ipaddress(hostname)

    # Check types not specified (via --checks=)? Determine automatically
    if not check_types:
        check_types = []
        if is_snmp_host(hostname):

            # May we do an SNMP scan? 
            if do_snmp_scan:
                check_types = snmp_scan(hostname, ipaddress)
                print check_types

            # Otherwise use all check types that we already have discovered
            # previously
            else:
                for check_type, item, params in read_autochecks_of(hostname):
                    if check_type not in check_types and check_uses_snmp(check_type):
                        check_types.append(check_type)

        if is_tcp_host(hostname):
            check_types += discoverable_check_types('tcp')

    # Make hostname available as global variable in discovery functions
    # (used e.g. by ps-discovery)
    global g_hostname
    g_hostname = hostname

    discovered_services = []
    try:
        for check_type in check_types:
            for item, paramstring in discover_check_type(hostname, ipaddress, check_type, use_caches):
                discovered_services.append((check_type, item, paramstring))

        return discovered_services
    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")


def discover_check_type(hostname, ipaddress, check_type, use_caches):
    # Skip this check type if is ignored for that host
    if service_ignored(hostname, check_type, None):
        return []

    # Skip SNMP checks on non-SNMP hosts
    if check_uses_snmp(check_type) and not is_snmp_host(hostname):
        return []

    try:
        discovery_function = check_info[check_type]["inventory_function"]
        if discovery_function == None:
            discovery_function = no_discovery_possible
    except KeyError:
        raise MKGeneralException("No such check type '%s'" % check_type)

    section_name = check_type.split('.')[0]    # make e.g. 'lsi' from 'lsi.arrays'

    try:
        info = None
        info = get_realhost_info(hostname, ipaddress, section_name, use_caches and inventory_max_cachefile_age or 0, ignore_check_interval=True)

    except MKAgentError, e:
        if str(e):
            raise

    except MKSNMPError, e:
        if str(e):
            raise

    if info == None: # No data for this check type
        return []

    # Add information about nodes if check wants this
    if check_info[check_type]["node_info"]:
        if clusters_of(hostname):
            add_host = hostname
        else:
            add_host = None
        info = [ [add_host] + line for line in info ]

    # Now do the actual inventory
    try:
        # Convert with parse function if available
        if section_name in check_info: # parse function must be define for base check
            parse_function = check_info[section_name]["parse_function"]
            if parse_function:
                info = check_info[section_name]["parse_function"](info)

        # Check number of arguments of discovery function. Note: This
        # check for the legacy API will be removed after 1.2.6.
        if len(inspect.getargspec(discovery_function)[0]) == 2:
            discovered_items = discovery_function(check_type, info) # discovery is a list of pairs (item, current_value)
        else:
            # New preferred style since 1.1.11i3: only one argument: info
            discovered_items = discovery_function(info)

        # tolerate function not explicitely returning []
        if discovered_items == None:
            discovered_items = []

        # New yield based api style
        elif type(discovered_items) != list:
            discovered_items = list(discovered_items)

        result = []
        for entry in discovered_items:
            if not isinstance(entry, tuple):
                sys.stderr.write("%s: Check %s returned invalid discovery data (entry not a tuple): %r\n" %
                                                                     (hostname, check_type, repr(entry)))
                continue

            if len(entry) == 2: # comment is now obsolete
                item, paramstring = entry
            else:
                try:
                    item, comment, paramstring = entry
                except ValueError:
                    sys.stderr.write("%s: Check %s returned invalid discovery data (not 2 or 3 elements): %r\n" %
                                                                           (hostname, check_type, repr(entry)))
                    continue

            description = service_description(check_type, item)
            # make sanity check
            if len(description) == 0:
                sys.stderr.write("%s: Check %s returned empty service description - ignoring it.\n" %
                                                (hostname, check_type))
                continue

            result.append((item, paramstring))

    except Exception, e:
        if opt_debug:
            sys.stderr.write("Exception in discovery function of check type %s\n" % check_type)
            raise
        if opt_verbose:
            sys.stderr.write("%s: Invalid output from agent or invalid configuration: %s\n" % (hostname, e))
        return []

    print "DISC OF %s: %r" % (check_type, result)
    return result



###        # Find logical host this check belongs to. The service might belong to a cluster.
###        hn = host_of_clustered_service(hostname, description)
###        if hn != hostname:
###            hn = hostname # FAKE TEST HIRN
###            # print "AAAAAAAAAAAAAAAAAA"
###
###        # Now compare with already known checks for this host (from
###        # previous inventory or explicit checks). Also drop services
###        # the user wants to ignore via 'ignored_services'.
###        checktable = get_check_table(hn)
###        checked_items = [ i for ( (cn, i), (par, descr, deps) ) \
###                          in checktable.items() if cn == checkname ]
###        if item in checked_items:
###            if include_state:
###                state_type = "old"
###            else:
###                continue # we have that already
###
###        if service_ignored(hn, checkname, description):
###            if include_state:
###                if state_type == "old":
###                    state_type = "obsolete"
###                else:
###                    state_type = "ignored"
###            else:
###                continue # user does not want this item to be checked
###
###        newcheck = "  (%r, %r, %s)," % (checkname, item, paramstring)
###        newcheck += "\n"
###        if newcheck not in newchecks[host]: # avoid duplicates if inventory outputs item twice
###            newchecks[host].append(newcheck)
###            if include_state:
###                newitems.append( (hostname, checkname, item, paramstring, state_type) )
###            else:
###                newitems.append( (hostname, checkname, item) )
###            count_new += 1
###
###
###    if not check_only:
###        if count_new:
###            for hostname, nc in newchecks.items():
###                add_to_autochecks_of(hostname, nc)
###            sys.stdout.write('%-30s ' % (tty_cyan + tty_bold + checkname + tty_normal))
###        sys.stdout.write('%s%d new checks%s\n' % (tty_bold + tty_green, count_new, tty_normal))

####    return newitems

####def make_inventory(checkname, hostnamelist, check_only=False, include_state=False):
####    try:
####        inventory_function = check_info[checkname]["inventory_function"]
####        if inventory_function == None:
####            inventory_function = no_inventory_possible
####    except KeyError:
####        sys.stderr.write("No such check type '%s'. Try check_mk -L.\n" % checkname)
####        sys.exit(1)
####
####    is_snmp_check = check_uses_snmp(checkname)
####
####    newchecks = {}  # dict host -> list of new checks
####    newitems = []   # used by inventory check to display unchecked items
####    count_new = 0
####    checked_hosts = []
####
####    # if no hostnamelist is specified, we use all hosts
####    if not hostnamelist or len(hostnamelist) == 0:
####        global opt_use_cachefile
####        opt_use_cachefile = True
####        hostnamelist = all_hosts_untagged
####
####    try:
####        for host in hostnamelist:
####            newchecks.setdefault(host, [])
####            if is_snmp_check:
####                # Skip SNMP check on non-SNMP hosts
####                if not is_snmp_host(host):
####                    continue
####                # Skip SNMP check if this checktype is disabled
####                if service_ignored(host, checkname, None):
####                    continue
####
####            if is_cluster(host):
####                sys.stderr.write("%s is a cluster host and cannot be inventorized.\n" % host)
####                continue
####
####            # host is either hostname or "hostname/ipaddress"
####            s = host.split("/")
####            hostname = s[0]
####            if len(s) == 2:
####                ipaddress = s[1]
####            else:
####                # try to resolve name into ip address
####                if not opt_no_tcp:
####                    try:
####                        ipaddress = lookup_ipaddress(hostname)
####                    except:
####                        sys.stderr.write("Cannot resolve %s into IP address.\n" % hostname)
####                        continue
####                else:
####                    ipaddress = None # not needed, not TCP used
####
####            # Make hostname available as global variable in inventory functions
####            # (used e.g. by ps-inventory)
####            global g_hostname
####            g_hostname = hostname
####
####            # On --no-tcp option skip hosts without cache file
####            if opt_no_tcp:
####                if opt_no_cache:
####                    sys.stderr.write("You allowed me neither TCP nor cache. Bailing out.\n")
####                    sys.exit(4)
####
####                cachefile = tcp_cache_dir + "/" + hostname
####                if not os.path.exists(cachefile):
####                    if opt_verbose:
####                        sys.stderr.write("No cachefile %s. Skipping this host.\n" % cachefile)
####                    continue
####
####            checked_hosts.append(hostname)
####
####            checkname_base = checkname.split('.')[0]    # make e.g. 'lsi' from 'lsi.arrays'
####            try:
####                info = get_realhost_info(hostname, ipaddress, checkname_base, inventory_max_cachefile_age, True)
####                # Add information about nodes if check wants this
####                if check_info[checkname]["node_info"]:
####                    if clusters_of(hostname):
####                        add_host = hostname
####                    else:
####                        add_host = None
####                    info = [ [add_host] + line for line in info ]
####
####                # Convert with parse function if available
####                if checkname_base in check_info: # parse function must be define for base check
####                    parse_function = check_info[checkname_base]["parse_function"]
####                    if parse_function:
####                        info = check_info[checkname_base]["parse_function"](info)
####
####
####            if info == None: # No data for this check type
####                continue
####            try:
####                # Check number of arguments of inventory function
####                if len(inspect.getargspec(inventory_function)[0]) == 2:
####                    inventory = inventory_function(checkname, info) # inventory is a list of pairs (item, current_value)
####                else:
####                    # New preferred style since 1.1.11i3: only one argument: info
####                    inventory = inventory_function(info)
####                if inventory == None: # tolerate if function does no explicit return
####                    inventory = []
####
####                # New yield based api style
####                if type(inventory) != list:
####                    inventory = list(inventory)
####            except Exception, e:
####                if opt_debug:
####                    sys.stderr.write("Exception in inventory function of check type %s\n" % checkname)
####                    raise
####                if opt_verbose:
####                    sys.stderr.write("%s: Invalid output from agent or invalid configuration: %s\n" % (hostname, e))
####                continue
####
####            if not isinstance(inventory, list):
####                sys.stderr.write("%s: Check %s returned invalid inventory data: %s\n" %
####                                                    (hostname, checkname, repr(inventory)))
####                continue
####
####            for entry in inventory:
####                state_type = "new" # assume new, change later if wrong
####
####                if not isinstance(entry, tuple):
####                    sys.stderr.write("%s: Check %s returned invalid inventory data (entry not a tuple): %s\n" %
####                                                                         (hostname, checkname, repr(inventory)))
####                    continue
####
####                if len(entry) == 2: # comment is now obsolete
####                    item, paramstring = entry
####                else:
####                    try:
####                        item, comment, paramstring = entry
####                    except ValueError:
####                        sys.stderr.write("%s: Check %s returned invalid inventory data (not 2 or 3 elements): %s\n" %
####                                                                               (hostname, checkname, repr(inventory)))
####                        continue
####
####                description = service_description(checkname, item)
####                # make sanity check
####                if len(description) == 0:
####                    sys.stderr.write("%s: Check %s returned empty service description - ignoring it.\n" %
####                                                    (hostname, checkname))
####                    continue
####
####                # Find logical host this check belongs to. The service might belong to a cluster.
####                hn = host_of_clustered_service(hostname, description)
####                if hn != hostname:
####                    hn = hostname # FAKE TEST HIRN
####                    # print "AAAAAAAAAAAAAAAAAA"
####
####                # Now compare with already known checks for this host (from
####                # previous inventory or explicit checks). Also drop services
####                # the user wants to ignore via 'ignored_services'.
####                checktable = get_check_table(hn)
####                checked_items = [ i for ( (cn, i), (par, descr, deps) ) \
####                                  in checktable.items() if cn == checkname ]
####                if item in checked_items:
####                    if include_state:
####                        state_type = "old"
####                    else:
####                        continue # we have that already
####
####                if service_ignored(hn, checkname, description):
####                    if include_state:
####                        if state_type == "old":
####                            state_type = "obsolete"
####                        else:
####                            state_type = "ignored"
####                    else:
####                        continue # user does not want this item to be checked
####
####                newcheck = "  (%r, %r, %s)," % (checkname, item, paramstring)
####                newcheck += "\n"
####                if newcheck not in newchecks[host]: # avoid duplicates if inventory outputs item twice
####                    newchecks[host].append(newcheck)
####                    if include_state:
####                        newitems.append( (hostname, checkname, item, paramstring, state_type) )
####                    else:
####                        newitems.append( (hostname, checkname, item) )
####                    count_new += 1
####
####
####    except KeyboardInterrupt:
####        sys.stderr.write('<Interrupted>\n')
####
####    if not check_only:
####        if count_new:
####            for hostname, nc in newchecks.items():
####                add_to_autochecks_of(hostname, nc)
####            sys.stdout.write('%-30s ' % (tty_cyan + tty_bold + checkname + tty_normal))
####            sys.stdout.write('%s%d new checks%s\n' % (tty_bold + tty_green, count_new, tty_normal))
####
####    return newitems

def discoverable_check_types(what): # snmp, tcp, all
    check_types = [ k for k in check_info.keys()
                   if check_info[k]["inventory_function"] != None
                   and (what == "all"
                        or check_uses_snmp(k) == (what == "snmp"))
                 ]
    check_types.sort()
    return check_types
