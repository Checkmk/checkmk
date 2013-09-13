#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

# This module is needed only for SNMP based checks

OID_END    =  0
OID_STRING = -1
OID_BIN    = -2

def strip_snmp_value(value):
    v = value.strip()
    if v.startswith('"'):
        v = v[1:-1]
        if len(v) > 2 and is_hex_string(v):
            return convert_from_hex(v)
        else:
            return v.strip()
    else:
        return v.strip()

def is_hex_string(value):
    # as far as I remember, snmpwalk puts a trailing space within
    # the quotes in case of hex strings. So we require that space
    # to be present in order make sure, we really deal with a hex string.
    if value[-1] != ' ':
        return False
    hexdigits = "0123456789abcdefABCDEF"
    n = 0
    for x in value:
        if n % 3 == 2:
            if x != ' ':
                return False
        else:
            if x not in hexdigits:
                return False
        n += 1
    return True

def convert_from_hex(value):
    hexparts = value.split()
    r = ""
    for hx in hexparts:
        r += chr(int(hx, 16))
    return r

def oid_to_bin(oid):
    return u"".join([ unichr(int(p)) for p in oid.strip(".").split(".") ])

def extract_end_oid(prefix, complete):
    return complete[len(prefix):].lstrip('.')

# sort OID strings numerically
def oid_to_intlist(oid):
    if oid:
        return map(int, oid.split('.'))
    else:
        return []

def cmp_oids(o1, o2):
    return cmp(oid_to_intlist(o1), oid_to_intlist(o2))

def get_snmp_table(hostname, ip, oid_info):
    # oid_info is either ( oid, columns ) or
    # ( oid, suboids, columns )
    # suboids is a list if OID-infixes that are put between baseoid
    # and the columns and also prefixed to the index column. This
    # allows to merge distinct SNMP subtrees with a similar structure
    # to one virtual new tree (look into cmctc_temp for an example)
    if len(oid_info) == 2:
        oid, targetcolumns = oid_info
        suboids = [None]
    else:
        oid, suboids, targetcolumns = oid_info

    if not oid.startswith("."):
        raise MKGeneralException("OID definition '%s' does not begin with ." % oid)

    all_values = []
    index_column = -1
    index_format = None
    number_rows = -1
    info = []
    for suboid in suboids:
        colno = -1
        columns = []
        # Detect missing (empty columns)
        max_len = 0
        max_len_col = -1

        for column in targetcolumns:
            fetchoid = oid
            if suboid:
                fetchoid += "." + str(suboid)
            if column != "":
                fetchoid += "." + str(column)

            # column may be integer or string like "1.5.4.2.3"
            colno += 1
            # if column is 0, we do not fetch any data from snmp, but use
            # a running counter as index. If the index column is the first one,
            # we do not know the number of entries right now. We need to fill
            # in later. If the column in OID_STRING or OID_BIN we do something
            # similar: we fill in the complete OID of the entry, either as
            # string or as binary UTF-8 encoded number string
            if column in [ OID_END, OID_STRING, OID_BIN ]:
                index_column = colno
                columns.append((fetchoid, []))
                index_format = column
                continue


            if opt_use_snmp_walk or is_usewalk_host(hostname):
                rowinfo = get_stored_snmpwalk(hostname, fetchoid)
            elif has_inline_snmp and use_inline_snmp:
                rowinfo = inline_snmpwalk_on_suboid(hostname, fetchoid)
            else:
                rowinfo = snmpwalk_on_suboid(hostname, ip, fetchoid)

            columns.append((fetchoid, rowinfo))
            number_rows = len(rowinfo)
            if len(rowinfo) > max_len:
                max_len = len(rowinfo)
                max_len_col = colno

        if index_column != -1:
            index_rows = []
            # Take end-oids of non-index columns as indices
            fetchoid, max_column  = columns[max_len_col]
            for o, value in max_column:
                if index_format == OID_END:
		    eo = extract_end_oid(fetchoid, o)
                    index_rows.append((o, eo))
                elif index_format == OID_STRING:
                    index_rows.append((o, o))
                else:
                    index_rows.append((o, oid_to_bin(o)))
            columns[index_column] = fetchoid, index_rows


        # prepend suboid to first column
        if suboid and len(columns) > 0:
            fetchoid, first_column = columns[0]
            new_first_column = []
            for o, val in first_column:
                new_first_column.append((o, str(suboid) + "." + str(val)))
            columns[0] = fetchoid, new_first_column

        # Swap X and Y axis of table (we want one list of columns per item)
        # Here we have to deal with a nasty problem: Some brain-dead devices
        # omit entries in some sub OIDs. This happens e.g. for CISCO 3650
        # in the interfaces MIB with 64 bit counters. So we need to look at
        # the OIDs and watch out for gaps we need to fill with dummy values.

        # First compute the complete list of end-oids appearing in the output
        # by looping all results and putting the endoids to a flat list
        endoids = []
        for fetchoid, column in columns:
            for o, value in column:
                endoid = extract_end_oid(fetchoid, o)
                if endoid not in endoids:
                    endoids.append(endoid)

        # The list needs to be sorted to prevent problems when the first
        # column has missing values in the middle of the tree. Since we
        # work with strings of numerical components, a simple string sort
        # is not correct. 1.14 must come after 1.2!
        endoids.sort(cmp = cmp_oids)

        # Now fill gaps in columns where some endois are missing
        new_columns = []
        for fetchoid, column in columns:
            i = 0
            new_column = []
            # Loop all lines to fill holes in the middle of the list. All
            # columns check the following lines for the correct endoid. If
            # an endoid differs empty values are added until the hole is filled
            for o, value in column:
                eo = extract_end_oid(fetchoid, o)
                if len(column) != len(endoids):
                    while i < len(endoids) and endoids[i] != eo:
                        new_column.append("") # (beginoid + '.' +endoids[i], "" ) )
                        i += 1
                new_column.append(value)
                i += 1

            # At the end check if trailing OIDs are missing
            while i < len(endoids):
                new_column.append("") # (beginoid + '.' +endoids[i], "") )
                i += 1
            new_columns.append(new_column)
        columns = new_columns

        # Now construct table by swapping X and Y
        new_info = []
        index = 0
        if len(columns) > 0:
            for item in columns[0]:
                new_info.append([ c[index] for c in columns ])
                index += 1
            info += new_info

    return info


# SNMP-Helper functions used in various checks

def check_snmp_misc(item, params, info):
    for line in info:
        if item == line[0]:
            value = savefloat(line[1])
            text = line[2]
            crit_low, warn_low, warn_high, crit_high = params
            # if value is negative, we have to swap >= and <=!
            perfdata=[ (item, line[1]) ]
            if not within_range(value, crit_low, crit_high):
                return (2, "CRIT - %.2f value out of crit range (%.2f .. %.2f)" % \
                        (value, crit_low, crit_high), perfdata)
            elif not within_range(value, warn_low, warn_high):
                return (2, "WARNING - %.2f value out of warning range (%.2f .. %.2f)" % \
                        (value, warn_low, warn_high), perfdata)
            else:
                return (0, "OK = %s (OK within %.2f .. %.2f)" % (text, warn_low, warn_high), perfdata)
    return (3, "Missing item %s in SNMP data" % item)

def inventory_snmp_misc(checkname, info):
    inventory = []
    for line in info:
        value = savefloat(line[1])
        params = "(%.1f, %.1f, %.1f, %.1f)" % (value*.8, value*.9, value*1.1, value*1.2)
        inventory.append( (line[0], line[2], params ) )
    return inventory

# Version with simple handling of target parameters: only
# the current value is OK, all other values are CRIT
def inventory_snmp_fixed(checkname, info):
    inventory = []
    for line in info:
        value = line[1]
        params = '"%s"' % (value,)
        inventory.append( (line[0], line[2], params ) )
    return inventory

def check_snmp_fixed(item, targetvalue, info):
    for line in info:
        if item == line[0]:
            value = line[1]
            text = line[2]
            if value != targetvalue:
                return (2, "CRIT - %s (should be %s)" % (value, targetvalue))
            else:
                return (0, "OK - %s" % (value,))
    return (3, "Missing item %s in SNMP data" % item)

g_walk_cache = {}
def get_stored_snmpwalk(hostname, oid):
    if oid.startswith("."):
        oid = oid[1:]

    if oid.endswith(".*"):
        oid_prefix = oid[:-2]
        dot_star = True
    else:
        oid_prefix = oid
        dot_star = False

    path = snmpwalks_dir + "/" + hostname

    if opt_debug:
        sys.stderr.write("Getting %s from %s\n" % (oid, path))

    rowinfo = []

    # New implementation: use binary search
    def to_bin_string(oid):
        try:
            return tuple(map(int, oid.strip(".").split(".")))
        except:
            raise MKGeneralException("Invalid OID %s" % oid)

    def compare_oids(a, b):
        aa = to_bin_string(a)
        bb = to_bin_string(b)
        if len(aa) <= len(bb) and bb[:len(aa)] == aa:
            result = 0
        else:
            result = cmp(aa, bb)
        return result

    if hostname in g_walk_cache:
        lines = g_walk_cache[hostname]
    else:
        try:
            lines = file(path).readlines()
        except IOError:
            raise MKGeneralException("No snmpwalk file %s\n" % path)
        g_walk_cache[hostname] = lines

    begin = 0
    end = len(lines)
    hit = None
    while end - begin > 0:
        current = (begin + end) / 2
        parts = lines[current].split(None, 1)
        comp = parts[0]
        hit = compare_oids(oid_prefix, comp)
        if hit == 0:
            break
        elif hit == 1: # we are too low
            begin = current + 1
        else:
            end = current

    if hit != 0:
        return [] # not found


    def collect_until(index, direction):
        rows = []
        # Handle case, where we run after the end of the lines list
        if index >= len(lines):
            if direction > 0:
                return []
            else:
                index -= 1
        while True:
            line = lines[index]
            parts = line.split(None, 1)
            o = parts[0]
            if o.startswith('.'):
                o = o[1:]
            if o == oid or o.startswith(oid_prefix + "."):
                if len(parts) > 1:
                    value = parts[1]
                    if agent_simulator:
                        value = agent_simulator_process(value)
                else:
                    value = ""
                # Fix for missing starting oids
                rows.append(('.'+o, strip_snmp_value(value)))
                index += direction
                if index < 0 or index >= len(lines):
                    break
            else:
                break
        return rows


    rowinfo = collect_until(current, -1)
    rowinfo.reverse()
    rowinfo += collect_until(current + 1, 1)
    # import pprint ; pprint.pprint(rowinfo)

    if dot_star:
        return [ rowinfo[0] ]
    else:
        return rowinfo

# Helper function to be used in checks.  It applies a user-specified
# character encoding in order to tranlate e.g. latin1 to utf8
def snmp_decode_string(text):
    encoding = get_snmp_character_encoding(g_hostname)
    if encoding:
        return text.decode(encoding).encode("utf-8")
    else:
        return text

#   .--Classic SNMP--------------------------------------------------------.
#   |        ____ _               _        ____  _   _ __  __ ____         |
#   |       / ___| | __ _ ___ ___(_) ___  / ___|| \ | |  \/  |  _ \        |
#   |      | |   | |/ _` / __/ __| |/ __| \___ \|  \| | |\/| | |_) |       |
#   |      | |___| | (_| \__ \__ \ | (__   ___) | |\  | |  | |  __/        |
#   |       \____|_|\__,_|___/___/_|\___| |____/|_| \_|_|  |_|_|           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Non-inline SNMP handling code. Kept for compatibility.               |
#   '----------------------------------------------------------------------'

def snmpwalk_on_suboid(hostname, ip, oid):
    portspec = snmp_port_spec(hostname)
    command = snmp_walk_command(hostname) + \
             " -OQ -OU -On -Ot %s%s %s 2>/dev/null" % (ip, portspec, oid)
    if opt_debug:
        sys.stderr.write('   Running %s\n' % (command,))
    snmp_process = os.popen(command, "r").xreadlines()

    # Ugly(1): in some cases snmpwalk inserts line feed within one
    # dataset. This happens for example on hexdump outputs longer
    # than a few bytes. Those dumps are enclosed in double quotes.
    # So if the value begins with a double quote, but the line
    # does not end with a double quote, we take the next line(s) as
    # a continuation line.
    rowinfo = []
    try:
        while True: # walk through all lines
            line = snmp_process.next().strip()
            parts = line.split('=', 1)
            if len(parts) < 2:
                continue # broken line, must contain =
            oid = parts[0].strip()
            value = parts[1].strip()
            # Filter out silly error messages from snmpwalk >:-P
            if value.startswith('No more variables') or value.startswith('End of MIB') \
               or value.startswith('No Such Object available') or value.startswith('No Such Instance currently exists'):
                continue

            if len(value) > 0 and value[0] == '"' and value[-1] != '"': # to be continued
                while True: # scan for end of this dataset
                    nextline = snmp_process.next().strip()
                    value += " " + nextline
                    if value[-1] == '"':
                        break
            rowinfo.append((oid, strip_snmp_value(value)))

    except StopIteration:
        pass

    exitstatus = snmp_process.close()
    if exitstatus:
        if opt_verbose:
            sys.stderr.write(tty_red + tty_bold + "ERROR: " + tty_normal + "SNMP error\n")
        raise MKSNMPError("SNMP Error on %s" % ip)
    return rowinfo
