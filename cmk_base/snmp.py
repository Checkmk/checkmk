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

import os

import cmk.debug
import cmk.tty as tty
from cmk.exceptions import MKGeneralException

import cmk_base.config as config
import cmk_base.console as console
import cmk_base.classic_snmp as classic_snmp
import cmk.cpu_tracking as cpu_tracking
import cmk_base.agent_simulator
from cmk_base.exceptions import MKSNMPError

try:
    import cmk_base.cee.inline_snmp as inline_snmp
except ImportError:
    inline_snmp = None


OID_END              =  0  # Suffix-part of OID that was not specified
OID_STRING           = -1  # Complete OID as string ".1.3.6.1.4.1.343...."
OID_BIN              = -2  # Complete OID as binary string "\x01\x03\x06\x01..."
OID_END_BIN          = -3  # Same, but just the end part
OID_END_OCTET_STRING = -4  # yet same, but omit first byte (assuming that is the length byte)

_enforce_stored_walks = False

# TODO: Replace this by generic caching
g_single_oid_hostname        = None
g_single_oid_cache           = {}
g_walk_cache                 = {}

#.
#   .--CheckHelpers--------------------------------------------------------.
#   |      ____ _               _    _   _      _                          |
#   |     / ___| |__   ___  ___| | _| | | | ___| |_ __   ___ _ __ ___      |
#   |    | |   | '_ \ / _ \/ __| |/ / |_| |/ _ \ | '_ \ / _ \ '__/ __|     |
#   |    | |___| | | |  __/ (__|   <|  _  |  __/ | |_) |  __/ |  \__ \     |
#   |     \____|_| |_|\___|\___|_|\_\_| |_|\___|_| .__/ \___|_|  |___/     |
#   |                                            |_|                       |
#   +----------------------------------------------------------------------+
#   | Some SNMP related check helping code. Offered to the checks by the   |
#   | check API.                                                           |
#   '----------------------------------------------------------------------'

def BINARY(oid):
    return "binary", oid


# Wrapper to mark OIDs as being cached for regular checks, but not for discovery
def CACHED_OID(oid):
    return "cached", oid


# Convert a string to an integer. This is done by consideren the string to by a
# little endian byte string.  Such strings are sometimes used by SNMP to encode
# 64 bit counters without needed COUNTER64 (which is not available in SNMP v1)
def binstring_to_int(binstring):
    value = 0
    mult = 1
    for byte in binstring[::-1]:
        value += mult * ord(byte)
        mult *= 256
    return value


#.
#   .--Generic SNMP--------------------------------------------------------.
#   |     ____                      _        ____  _   _ __  __ ____       |
#   |    / ___| ___ _ __   ___ _ __(_) ___  / ___|| \ | |  \/  |  _ \      |
#   |   | |  _ / _ \ '_ \ / _ \ '__| |/ __| \___ \|  \| | |\/| | |_) |     |
#   |   | |_| |  __/ | | |  __/ |  | | (__   ___) | |\  | |  | |  __/      |
#   |    \____|\___|_| |_|\___|_|  |_|\___| |____/|_| \_|_|  |_|_|         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Top level functions to realize SNMP functionality for Check_MK.      |
#   '----------------------------------------------------------------------'

def get_snmp_table(hostname, ip, check_type, oid_info, use_snmpwalk_cache):
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

    index_column = -1
    index_format = None
    info = []
    for suboid in suboids:
        colno = -1
        columns = []
        # Detect missing (empty columns)
        max_len = 0
        max_len_col = -1

        for column in targetcolumns:
            fetchoid, value_encoding = _compute_fetch_oid(oid, suboid, column)

            # column may be integer or string like "1.5.4.2.3"
            colno += 1
            # if column is 0, we do not fetch any data from snmp, but use
            # a running counter as index. If the index column is the first one,
            # we do not know the number of entries right now. We need to fill
            # in later. If the column is OID_STRING or OID_BIN we do something
            # similar: we fill in the complete OID of the entry, either as
            # string or as binary UTF-8 encoded number string
            if column in [ OID_END, OID_STRING, OID_BIN, OID_END_BIN, OID_END_OCTET_STRING ]:
                if index_column >= 0 and index_column != colno:
                    raise MKGeneralException("Invalid SNMP OID specification in implementation of check. "
                        "You can only use one of OID_END, OID_STRING, OID_BIN, OID_END_BIN and OID_END_OCTET_STRING.")
                index_column = colno
                columns.append((fetchoid, [], "string"))
                index_format = column
                continue

            rowinfo = _get_snmpwalk(hostname, ip, check_type, oid, fetchoid, column, use_snmpwalk_cache)

            columns.append((fetchoid, rowinfo, value_encoding))
            number_of_rows = len(rowinfo)
            if number_of_rows > max_len:
                max_len     = number_of_rows
                max_len_col = colno

        if index_column != -1:
            index_rows = []
            # Take end-oids of non-index columns as indices
            fetchoid, max_column, value_encoding  = columns[max_len_col]
            for o, _unused_value in max_column:
                if index_format == OID_END:
                    index_rows.append((o, _extract_end_oid(fetchoid, o)))
                elif index_format == OID_STRING:
                    index_rows.append((o, o))
                elif index_format == OID_BIN:
                    index_rows.append((o, _oid_to_bin(o)))
                elif index_format == OID_END_BIN:
                    index_rows.append((o, _oid_to_bin(_extract_end_oid(fetchoid, o))))
                else: # OID_END_OCTET_STRING:
                    index_rows.append((o, _oid_to_bin(_extract_end_oid(fetchoid, o))[1:]))

            columns[index_column] = fetchoid, index_rows, value_encoding


        # prepend suboid to first column
        if suboid and columns:
            fetchoid, first_column, value_encoding = columns[0]
            new_first_column = []
            for o, val in first_column:
                new_first_column.append((o, str(suboid) + "." + str(val)))
            columns[0] = fetchoid, new_first_column, value_encoding

        # Here we have to deal with a nasty problem: Some brain-dead devices
        # omit entries in some sub OIDs. This happens e.g. for CISCO 3650
        # in the interfaces MIB with 64 bit counters. So we need to look at
        # the OIDs and watch out for gaps we need to fill with dummy values.
        new_columns = _sanitize_snmp_table_columns(columns)

        # From all SNMP data sources (stored walk, classic SNMP, inline SNMP) we
        # get normal python strings. But for Check_MK we need unicode strings now.
        # Convert them by using the standard Check_MK approach for incoming data
        sanitized_columns = _sanitize_snmp_encoding(hostname, new_columns)

        info += _construct_snmp_table_of_rows(sanitized_columns)

    return info


def get_single_oid(hostname, ipaddress, oid):
    # New in Check_MK 1.1.11: oid can end with ".*". In that case
    # we do a snmpgetnext and try to find an OID with the prefix
    # in question. The *cache* is working including the X, however.

    if oid[0] != '.':
        if cmk.debug.enabled():
            raise MKGeneralException("OID definition '%s' does not begin with a '.'" % oid)
        else:
            oid = '.' + oid

    _clear_other_hosts_oid_cache(hostname)

    # TODO: Use generic cache mechanism
    if oid in g_single_oid_cache:
        return g_single_oid_cache[oid]

    console.vverbose("       Getting OID %s: " % oid)
    if _enforce_stored_walks or config.is_usewalk_host(hostname):
        walk = _get_stored_snmpwalk(hostname, oid)
        # get_stored_snmpwalk returns all oids that start with oid but here
        # we need an exact match
        if len(walk) == 1 and oid == walk[0][0]:
            value = walk[0][1]
        elif oid.endswith(".*") and len(walk) > 0:
            value = walk[0][1]
        else:
            value = None

    else:
        try:
            if config.is_inline_snmp_host(hostname):
                value = inline_snmp.get(hostname, oid, ipaddress=ipaddress)
            else:
                value = classic_snmp.get(hostname, ipaddress, oid)
        except:
            if cmk.debug.enabled():
                raise
            value = None

    if value != None:
        console.vverbose("%s%s%s%s\n" % (tty.bold, tty.green, value, tty.normal))
    else:
        console.vverbose("failed.\n")

    set_oid_cache(hostname, oid, value)
    return value


def walk_for_export(hostname, ip, oid):
    if config.is_inline_snmp_host(hostname):
        rows = inline_snmp.walk(hostname, None, oid)
        return inline_snmp.convert_rows_for_stored_walk(rows)
    else:
        return classic_snmp.walk(hostname, ip, oid, hex_plain=True)


def set_oid_cache(hostname, oid, value):
    _clear_other_hosts_oid_cache(hostname)
    g_single_oid_cache[oid] = value


def enforce_use_stored_walks():
    global _enforce_stored_walks
    _enforce_stored_walks = True


def cleanup_host_caches():
    global g_walk_cache
    g_walk_cache = {}
    _clear_other_hosts_oid_cache(None)

    if inline_snmp:
        inline_snmp.cleanup_inline_snmp_globals()


def _clear_other_hosts_oid_cache(hostname):
    global g_single_oid_hostname
    if g_single_oid_hostname != hostname:
        g_single_oid_cache.clear()
        g_single_oid_hostname = hostname


#.
#   .--SNMP helpers--------------------------------------------------------.
#   |     ____  _   _ __  __ ____    _          _                          |
#   |    / ___|| \ | |  \/  |  _ \  | |__   ___| |_ __   ___ _ __ ___      |
#   |    \___ \|  \| | |\/| | |_) | | '_ \ / _ \ | '_ \ / _ \ '__/ __|     |
#   |     ___) | |\  | |  | |  __/  | | | |  __/ | |_) |  __/ |  \__ \     |
#   |    |____/|_| \_|_|  |_|_|     |_| |_|\___|_| .__/ \___|_|  |___/     |
#   |                                            |_|                       |
#   +----------------------------------------------------------------------+
#   | Internal helpers for processing SNMP things                          |
#   '----------------------------------------------------------------------'

def strip_snmp_value(value, hex_plain = False):
    v = value.strip()
    if v.startswith('"'):
        v = v[1:-1]
        if len(v) > 2 and _is_hex_string(v):
            return not hex_plain and _convert_from_hex(v) or value
        else:
            # Fix for non hex encoded string which have been somehow encoded by the
            # netsnmp command line tools. An example:
            # Checking windows systems via SNMP with hr_fs: disk names like c:\
            # are reported as c:\\, fix this to single \
            return v.strip().replace('\\\\', '\\')
    else:
        return v

def _is_hex_string(value):
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

def _convert_from_hex(value):
    hexparts = value.split()
    r = ""
    for hx in hexparts:
        r += chr(int(hx, 16))
    return r


def _oid_to_bin(oid):
    return u"".join([ unichr(int(p)) for p in oid.strip(".").split(".") ])


def _extract_end_oid(prefix, complete):
    return complete[len(prefix):].lstrip('.')

# sort OID strings numerically
def _oid_to_intlist(oid):
    if oid:
        return map(int, oid.split('.'))
    else:
        return []

def _cmp_oids(o1, o2):
    return cmp(_oid_to_intlist(o1), _oid_to_intlist(o2))

def _cmp_oid_pairs(pair1, pair2):
    return cmp(_oid_to_intlist(pair1[0].lstrip('.')),
               _oid_to_intlist(pair2[0].lstrip('.')))

def _snmpv3_contexts_of(hostname, check_type):
    for ty, rules in config.snmpv3_contexts_of(hostname):
        if ty == None or ty == check_type:
            return rules
    return [None]

def _get_snmpwalk(hostname, ip, check_type, oid, fetchoid, column, use_snmpwalk_cache):
    is_cachable = _is_snmpwalk_cachable(column)
    rowinfo = None
    if is_cachable and use_snmpwalk_cache:
        # Returns either the cached SNMP walk or None when nothing is cached
        rowinfo = _get_cached_snmpwalk(hostname, fetchoid)

    if rowinfo == None:
        if _enforce_stored_walks or config.is_usewalk_host(hostname):
            rowinfo = _get_stored_snmpwalk(hostname, fetchoid)
        else:
            rowinfo = _perform_snmpwalk(hostname, ip, check_type, oid, fetchoid)

        if is_cachable:
            _save_snmpwalk_cache(hostname, fetchoid, rowinfo)

    return rowinfo


def _perform_snmpwalk(hostname, ip, check_type, base_oid, fetchoid):
    added_oids = set([])
    rowinfo = []
    if config.is_snmpv3_host(hostname):
        snmp_contexts = _snmpv3_contexts_of(hostname, check_type)
    else:
        snmp_contexts = [None]

    for context_name in snmp_contexts:
        cpu_tracking.push_phase("snmp")
        if config.is_inline_snmp_host(hostname):
            rows = inline_snmp.walk(hostname, check_type, fetchoid, base_oid,
                                                                  context_name=context_name,
                                                                  ipaddress=ip)
        else:
            rows = classic_snmp.walk(hostname, ip, fetchoid, context_name=context_name)
        cpu_tracking.pop_phase()

        # I've seen a broken device (Mikrotik Router), that broke after an
        # update to RouterOS v6.22. It would return 9 time the same OID when
        # .1.3.6.1.2.1.1.1.0 was being walked. We try to detect these situations
        # by removing any duplicate OID information
        if len(rows) > 1 and rows[0][0] == rows[1][0]:
            console.vverbose("Detected broken SNMP agent. Ignoring duplicate OID %s.\n" % rows[0][0])
            rows = rows[:1]

        for row_oid, val in rows:
            if row_oid in added_oids:
                console.vverbose("Duplicate OID found: %s (%s)\n" % (row_oid, val))
            else:
                rowinfo.append((row_oid, val))
                added_oids.add(row_oid)

    return rowinfo


def _compute_fetch_oid(oid, suboid, column):
    fetchoid = oid
    value_encoding = "string"

    if suboid:
        fetchoid += "." + str(suboid)

    if column != "":
        if type(column) == tuple:
            fetchoid += "." + str(column[1])
            if column[0] == "binary":
                value_encoding = "binary"
        else:
            fetchoid += "." + str(column)

    return fetchoid, value_encoding


def _sanitize_snmp_encoding(hostname, columns):
    decode_string_func = lambda s: _snmp_decode_string(hostname, s)

    for index, (column, value_encoding) in enumerate(columns):
        if value_encoding == "string":
            columns[index] = map(decode_string_func, column)
        else:
            columns[index] = map(_snmp_decode_binary, column)
    return columns


def _snmp_decode_string(hostname, text):
    encoding = config.snmp_character_encoding_of(hostname)
    if encoding:
        return text.decode(encoding)
    else:
        # Try to determine the current string encoding. In case a UTF-8 decoding fails, we decode latin1.
        try:
            return text.decode('utf-8')
        except:
            return text.decode('latin1')


def _snmp_decode_binary(text):
    return map(ord, text)


def _sanitize_snmp_table_columns(columns):
    # First compute the complete list of end-oids appearing in the output
    # by looping all results and putting the endoids to a flat list
    endoids = []
    for fetchoid, column, value_encoding in columns:
        for o, value in column:
            endoid = _extract_end_oid(fetchoid, o)
            if endoid not in endoids:
                endoids.append(endoid)

    # The list needs to be sorted to prevent problems when the first
    # column has missing values in the middle of the tree.
    if not _are_ascending_oids(endoids):
        endoids.sort(cmp=_cmp_oids)
        need_sort = True
    else:
        need_sort = False

    # Now fill gaps in columns where some endois are missing
    new_columns = []
    for fetchoid, column, value_encoding in columns:
        # It might happen that end OIDs are not ordered. Fix the OID sorting to make
        # it comparable to the already sorted endoids list. Otherwise we would get
        # some mixups when filling gaps
        if need_sort:
            column.sort(cmp=_cmp_oid_pairs)

        i = 0
        new_column = []
        # Loop all lines to fill holes in the middle of the list. All
        # columns check the following lines for the correct endoid. If
        # an endoid differs empty values are added until the hole is filled
        for o, value in column:
            eo = _extract_end_oid(fetchoid, o)
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
        new_columns.append((new_column, value_encoding))

    return new_columns


def _are_ascending_oids(oid_list):
    for a in range(len(oid_list) - 1):
        if _cmp_oids(oid_list[a], oid_list[a + 1]) > 0: # == 0 should never happen
            return False
    return True


def _construct_snmp_table_of_rows(columns):
    if not columns:
        return []

    # Now construct table by swapping X and Y.
    new_info = []
    for index in range(len(columns[0])):
        row = [ c[index] for c in columns ]
        new_info.append(row)
    return new_info


def _is_snmpwalk_cachable(column):
    return type(column) == tuple and column[0] == "cached"


def _get_cached_snmpwalk(hostname, fetchoid):
    path = cmk.paths.var_dir + "/snmp_cache/" + hostname + "/" + fetchoid

    try:
        console.vverbose("  Loading %s from walk cache %s\n" % (fetchoid, path))
        # TODO: Use store.load_data_from_file()
        return eval(file(path).read())
    except IOError:
        return None # don't print error when not cached yet
    except:
        if cmk.debug.enabled():
            raise
        console.verbose("Failed to read cached SNMP walk from %s, ignoring.\n" % path)
        return None


def _save_snmpwalk_cache(hostname, fetchoid, rowinfo):
    base_dir = cmk.paths.var_dir + "/snmp_cache/" + hostname + "/"
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    console.vverbose("  Caching walk of %s\n" % fetchoid)
    file(base_dir + fetchoid, "w").write("%r\n" % rowinfo)


def _get_stored_snmpwalk(hostname, oid):
    if oid.startswith("."):
        oid = oid[1:]

    if oid.endswith(".*"):
        oid_prefix = oid[:-2]
        dot_star = True
    else:
        oid_prefix = oid
        dot_star = False

    path = cmk.paths.snmpwalks_dir + "/" + hostname

    console.vverbose("  Loading %s from %s\n" % (oid, path))

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
            raise MKSNMPError("No snmpwalk file %s" % path)
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
                    try:
                        value = cmk_base.agent_simulator.process(parts[1])
                    except:
                        value = parts[1] # agent simulator missing in precompiled mode
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

    if dot_star:
        return [ rowinfo[0] ]
    else:
        return rowinfo
