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
import subprocess
from typing import Tuple, Optional, Any, Dict, List  # pylint: disable=unused-import

import cmk.utils.debug
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException, MKBailOut
import cmk.utils.store as store

import cmk_base.utils
import cmk_base.config as config
import cmk_base.console as console
import cmk_base.classic_snmp as classic_snmp
import cmk_base.ip_lookup as ip_lookup
import cmk_base.agent_simulator
from cmk_base.exceptions import MKSNMPError
import cmk_base.cleanup
import cmk_base.snmp_utils as snmp_utils

try:
    import cmk_base.cee.inline_snmp as inline_snmp
except ImportError:
    inline_snmp = None  # type: ignore

_enforce_stored_walks = False

# TODO: Replace this by generic caching
_g_single_oid_hostname = None
_g_single_oid_ipaddress = None
_g_single_oid_cache = None
# TODO: Move to StoredWalkSNMPBackend?
_g_walk_cache = {}  # type: Dict[str, List[str]]

#.
#   .--caching-------------------------------------------------------------.
#   |                                _     _                               |
#   |                  ___ __ _  ___| |__ (_)_ __   __ _                   |
#   |                 / __/ _` |/ __| '_ \| | '_ \ / _` |                  |
#   |                | (_| (_| | (__| | | | | | | | (_| |                  |
#   |                 \___\__,_|\___|_| |_|_|_| |_|\__, |                  |
#   |                                              |___/                   |
#   '----------------------------------------------------------------------'

#TODO CACHING


def initialize_single_oid_cache(snmp_config, from_disk=False):
    # type: (snmp_utils.SNMPHostConfig, bool) -> None
    global _g_single_oid_cache, _g_single_oid_ipaddress, _g_single_oid_hostname

    if not (_g_single_oid_hostname == snmp_config.hostname \
       and _g_single_oid_ipaddress == snmp_config.ipaddress) \
       or _g_single_oid_cache is None:
        _g_single_oid_hostname = snmp_config.hostname
        _g_single_oid_ipaddress = snmp_config.ipaddress
        if from_disk:
            _g_single_oid_cache = _load_single_oid_cache(snmp_config)
        else:
            _g_single_oid_cache = {}


def write_single_oid_cache(snmp_config):
    # type: (snmp_utils.SNMPHostConfig) -> None
    if not _g_single_oid_cache:
        return

    cache_dir = cmk.utils.paths.snmp_scan_cache_dir
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    cache_path = "%s/%s.%s" % (cache_dir, snmp_config.hostname, snmp_config.ipaddress)
    store.save_data_to_file(cache_path, _g_single_oid_cache, pretty=False)


def set_single_oid_cache(snmp_config, oid, value):
    _g_single_oid_cache[oid] = value


def _is_in_single_oid_cache(snmp_config, oid):
    return oid in _g_single_oid_cache


def _get_oid_from_single_oid_cache(snmp_config, oid):
    return _g_single_oid_cache.get(oid)


def _load_single_oid_cache(snmp_config):
    # type: (snmp_utils.SNMPHostConfig) -> Dict[str, str]
    cache_path = "%s/%s.%s" % (cmk.utils.paths.snmp_scan_cache_dir, snmp_config.hostname,
                               snmp_config.ipaddress)
    return store.load_data_from_file(cache_path, {})


def cleanup_host_caches():
    # type: () -> None
    global _g_walk_cache
    _g_walk_cache = {}
    _clear_other_hosts_oid_cache(None)
    if inline_snmp:
        inline_snmp.cleanup_inline_snmp_globals()


def _clear_other_hosts_oid_cache(hostname):
    # type: (Optional[str]) -> None
    global _g_single_oid_cache, _g_single_oid_ipaddress, _g_single_oid_hostname
    if _g_single_oid_hostname != hostname:
        _g_single_oid_cache = None
        _g_single_oid_hostname = hostname
        _g_single_oid_ipaddress = None


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


def create_snmp_host_config(hostname):
    # type: (str) -> snmp_utils.SNMPHostConfig
    host_config = config.get_config_cache().get_host_config(hostname)

    # ip_lookup.lookup_ipv4_address() returns Optional[str] in general, but for
    # all cases that reach the code here we seem to have "str".
    address = ip_lookup.lookup_ip_address(hostname)
    if address is None:
        raise MKGeneralException("Failed to gather IP address of %s" % hostname)

    return host_config.snmp_config(address)


# TODO: OID_END_OCTET_STRING is not used at all. Drop it.
def get_snmp_table(snmp_config, check_plugin_name, oid_info, use_snmpwalk_cache):
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
        columns = []
        # Detect missing (empty columns)
        max_len = 0
        max_len_col = -1

        for colno, column in enumerate(targetcolumns):
            fetchoid, value_encoding = _compute_fetch_oid(oid, suboid, column)

            # column may be integer or string like "1.5.4.2.3"
            # if column is 0, we do not fetch any data from snmp, but use
            # a running counter as index. If the index column is the first one,
            # we do not know the number of entries right now. We need to fill
            # in later. If the column is OID_STRING or OID_BIN we do something
            # similar: we fill in the complete OID of the entry, either as
            # string or as binary UTF-8 encoded number string
            if column in [
                    snmp_utils.OID_END, snmp_utils.OID_STRING, snmp_utils.OID_BIN,
                    snmp_utils.OID_END_BIN, snmp_utils.OID_END_OCTET_STRING
            ]:
                if index_column >= 0 and index_column != colno:
                    raise MKGeneralException(
                        "Invalid SNMP OID specification in implementation of check. "
                        "You can only use one of OID_END, OID_STRING, OID_BIN, OID_END_BIN and OID_END_OCTET_STRING."
                    )
                index_column = colno
                columns.append((fetchoid, [], "string"))
                index_format = column
                continue

            rowinfo = _get_snmpwalk(snmp_config, check_plugin_name, oid, fetchoid, column,
                                    use_snmpwalk_cache)

            columns.append((fetchoid, rowinfo, value_encoding))
            number_of_rows = len(rowinfo)
            if number_of_rows > max_len:
                max_len = number_of_rows
                max_len_col = colno

        if index_column != -1:
            index_rows = []
            # Take end-oids of non-index columns as indices
            fetchoid, max_column, value_encoding = columns[max_len_col]
            for o, _unused_value in max_column:
                if index_format == snmp_utils.OID_END:
                    index_rows.append((o, _extract_end_oid(fetchoid, o)))
                elif index_format == snmp_utils.OID_STRING:
                    index_rows.append((o, o))
                elif index_format == snmp_utils.OID_BIN:
                    index_rows.append((o, _oid_to_bin(o)))
                elif index_format == snmp_utils.OID_END_BIN:
                    index_rows.append((o, _oid_to_bin(_extract_end_oid(fetchoid, o))))
                elif index_format == snmp_utils.OID_END_OCTET_STRING:
                    index_rows.append((o, _oid_to_bin(_extract_end_oid(fetchoid, o))[1:]))
                else:
                    raise MKGeneralException("Invalid index format %s" % index_format)

            index_encoding = columns[index_column][-1]
            columns[index_column] = fetchoid, index_rows, index_encoding

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
        sanitized_columns = _sanitize_snmp_encoding(snmp_config, new_columns)

        info += _construct_snmp_table_of_rows(sanitized_columns)

    return info


# Contextes can only be used when check_plugin_name is given.
def get_single_oid(snmp_config, oid, check_plugin_name=None, do_snmp_scan=True):
    # type: (snmp_utils.SNMPHostConfig, str, Optional[str], bool) -> Optional[str]
    # The OID can end with ".*". In that case we do a snmpgetnext and try to
    # find an OID with the prefix in question. The *cache* is working including
    # the X, however.
    if oid[0] != '.':
        if cmk.utils.debug.enabled():
            raise MKGeneralException("OID definition '%s' does not begin with a '.'" % oid)
        else:
            oid = '.' + oid

    # TODO: Use generic cache mechanism
    if _is_in_single_oid_cache(snmp_config, oid):
        console.vverbose("       Using cached OID %s: " % oid)
        value = _get_oid_from_single_oid_cache(snmp_config, oid)
        console.vverbose("%s%s%s%s\n" % (tty.bold, tty.green, value, tty.normal))
        return value

    # get_single_oid() can only return a single value. When SNMPv3 is used with multiple
    # SNMP contexts, all contextes will be queried until the first answer is received.
    if check_plugin_name is not None and snmp_utils.is_snmpv3_host(snmp_config):
        snmp_contexts = _snmpv3_contexts_of(snmp_config, check_plugin_name)
    else:
        snmp_contexts = [None]

    console.vverbose("       Getting OID %s: " % oid)
    for context_name in snmp_contexts:
        try:
            snmp_backend = SNMPBackendFactory().factory(
                snmp_config, enforce_stored_walks=_enforce_stored_walks)
            value = snmp_backend.get(snmp_config, oid, context_name)

            if value is not None:
                break  # Use first received answer in case of multiple contextes
        except Exception:
            if cmk.utils.debug.enabled():
                raise
            value = None

    if value is not None:
        console.vverbose("%s%s%s%s\n" % (tty.bold, tty.green, value, tty.normal))
    else:
        console.vverbose("failed.\n")

    set_single_oid_cache(snmp_config, oid, value)
    return value


class SNMPBackendFactory(object):
    @staticmethod
    def factory(snmp_config, enforce_stored_walks):
        # type: (snmp_utils.SNMPHostConfig, bool) -> snmp_utils.ABCSNMPBackend
        if enforce_stored_walks or snmp_config.is_usewalk_host:
            return StoredWalkSNMPBackend()

        if snmp_config.is_inline_snmp_host:
            return inline_snmp.InlineSNMPBackend()

        return classic_snmp.ClassicSNMPBackend()


class StoredWalkSNMPBackend(snmp_utils.ABCSNMPBackend):
    def get(self, snmp_config, oid, context_name=None):
        walk = self.walk(snmp_config, oid)

        # get_stored_snmpwalk returns all oids that start with oid but here
        # we need an exact match
        if len(walk) == 1 and oid == walk[0][0]:
            return walk[0][1]

        elif oid.endswith(".*") and len(walk) > 0:
            return walk[0][1]

        return None

    def walk(self, snmp_config, oid, check_plugin_name=None, table_base_oid=None,
             context_name=None):
        # type: (snmp_utils.SNMPHostConfig, str, Optional[str], Optional[str], Optional[str]) -> snmp_utils.SNMPRowInfo
        if oid.startswith("."):
            oid = oid[1:]

        if oid.endswith(".*"):
            oid_prefix = oid[:-2]
            dot_star = True
        else:
            oid_prefix = oid
            dot_star = False

        path = cmk.utils.paths.snmpwalks_dir + "/" + snmp_config.hostname

        console.vverbose("  Loading %s from %s\n" % (oid, path))

        rowinfo = []  # type: List[Tuple[str, str]]

        if snmp_config.hostname in _g_walk_cache:
            lines = _g_walk_cache[snmp_config.hostname]
        else:
            try:
                lines = file(path).readlines()
            except IOError:
                raise MKSNMPError("No snmpwalk file %s" % path)
            _g_walk_cache[snmp_config.hostname] = lines

        begin = 0
        end = len(lines)
        hit = None
        while end - begin > 0:
            current = (begin + end) / 2
            parts = lines[current].split(None, 1)
            comp = parts[0]
            hit = self._compare_oids(oid_prefix, comp)
            if hit == 0:
                break
            elif hit == 1:  # we are too low
                begin = current + 1
            else:
                end = current

        if hit != 0:
            return []  # not found

        rowinfo = self._collect_until(oid, oid_prefix, lines, current, -1)
        rowinfo.reverse()
        rowinfo += self._collect_until(oid, oid_prefix, lines, current + 1, 1)

        if dot_star:
            return [rowinfo[0]]

        return rowinfo

    def _compare_oids(self, a, b):
        aa = self._to_bin_string(a)
        bb = self._to_bin_string(b)
        if len(aa) <= len(bb) and bb[:len(aa)] == aa:
            result = 0
        else:
            result = cmp(aa, bb)
        return result

    def _to_bin_string(self, oid):
        try:
            return tuple(map(int, oid.strip(".").split(".")))
        except:
            raise MKGeneralException("Invalid OID %s" % oid)

    def _collect_until(self, oid, oid_prefix, lines, index, direction):
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
                    value = cmk_base.agent_simulator.process(parts[1])
                else:
                    value = ""
                # Fix for missing starting oids
                rows.append(('.' + o, classic_snmp.strip_snmp_value(value)))
                index += direction
                if index < 0 or index >= len(lines):
                    break
            else:
                break
        return rows


def walk_for_export(snmp_config, oid):
    # type: (snmp_utils.SNMPHostConfig, str) -> List[Tuple[str, str]]
    if snmp_config.is_inline_snmp_host:
        backend = inline_snmp.InlineSNMPBackend()  # type: snmp_utils.ABCSNMPBackend
    else:
        backend = classic_snmp.ClassicSNMPBackend()

    rows = backend.walk(snmp_config, oid)
    return _convert_rows_for_stored_walk(rows)


def enforce_use_stored_walks():
    global _enforce_stored_walks
    _enforce_stored_walks = True


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


def _convert_rows_for_stored_walk(rows):
    def should_be_encoded(v):
        for c in v:
            if ord(c) < 32 or ord(c) > 127:
                return True
        return False

    def hex_encode_value(v):
        encoded = ""
        for c in v:
            encoded += "%02X " % ord(c)
        return "\"%s\"" % encoded

    new_rows = []
    for oid, value in rows:
        if value == "ENDOFMIBVIEW":
            continue

        if should_be_encoded(value):
            new_rows.append((oid, hex_encode_value(value)))
        else:
            new_rows.append((oid, value))
    return new_rows


def _oid_to_bin(oid):
    return u"".join([unichr(int(p)) for p in oid.strip(".").split(".")])


def _extract_end_oid(prefix, complete):
    return complete[len(prefix):].lstrip('.')


# sort OID strings numerically
def _oid_to_intlist(oid):
    if oid:
        return map(int, oid.split('.'))

    return []


def _cmp_oids(o1, o2):
    return cmp(_oid_to_intlist(o1), _oid_to_intlist(o2))


def _cmp_oid_pairs(pair1, pair2):
    return cmp(_oid_to_intlist(pair1[0].lstrip('.')), _oid_to_intlist(pair2[0].lstrip('.')))


def _snmpv3_contexts_of(snmp_config, check_plugin_name):
    for ty, rules in snmp_config.snmpv3_contexts:
        if ty is None or ty == check_plugin_name:
            return rules
    return [None]


def _get_snmpwalk(snmp_config, check_plugin_name, oid, fetchoid, column, use_snmpwalk_cache):
    is_cachable = _is_snmpwalk_cachable(column)
    rowinfo = None
    if is_cachable and use_snmpwalk_cache:
        # Returns either the cached SNMP walk or None when nothing is cached
        rowinfo = _get_cached_snmpwalk(snmp_config.hostname, fetchoid)

    if rowinfo is None:
        rowinfo = _perform_snmpwalk(snmp_config, check_plugin_name, oid, fetchoid)

        if is_cachable:
            _save_snmpwalk_cache(snmp_config.hostname, fetchoid, rowinfo)

    return rowinfo


def _perform_snmpwalk(snmp_config, check_plugin_name, base_oid, fetchoid):
    added_oids = set([])
    rowinfo = []
    if snmp_utils.is_snmpv3_host(snmp_config):
        snmp_contexts = _snmpv3_contexts_of(snmp_config, check_plugin_name)
    else:
        snmp_contexts = [None]

    for context_name in snmp_contexts:
        snmp_backend = SNMPBackendFactory().factory(
            snmp_config, enforce_stored_walks=_enforce_stored_walks)

        rows = snmp_backend.walk(
            snmp_config,
            fetchoid,
            check_plugin_name=check_plugin_name,
            table_base_oid=base_oid,
            context_name=context_name)

        # I've seen a broken device (Mikrotik Router), that broke after an
        # update to RouterOS v6.22. It would return 9 time the same OID when
        # .1.3.6.1.2.1.1.1.0 was being walked. We try to detect these situations
        # by removing any duplicate OID information
        if len(rows) > 1 and rows[0][0] == rows[1][0]:
            console.vverbose(
                "Detected broken SNMP agent. Ignoring duplicate OID %s.\n" % rows[0][0])
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
        if isinstance(column, tuple):
            fetchoid += "." + str(column[1])
            if column[0] == "binary":
                value_encoding = "binary"
        else:
            fetchoid += "." + str(column)

    return fetchoid, value_encoding


def _sanitize_snmp_encoding(snmp_config, columns):
    decode_string_func = lambda s: _snmp_decode_string(snmp_config, s)

    for index, (column, value_encoding) in enumerate(columns):
        if value_encoding == "string":
            columns[index] = map(decode_string_func, column)
        else:
            columns[index] = map(_snmp_decode_binary, column)
    return columns


def _snmp_decode_string(snmp_config, text):
    encoding = snmp_config.character_encoding
    if encoding:
        return text.decode(encoding)

    # Try to determine the current string encoding. In case a UTF-8 decoding fails, we decode latin1.
    try:
        return text.decode('utf-8')
    except UnicodeDecodeError:
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
                    new_column.append("")  # (beginoid + '.' +endoids[i], "" ) )
                    i += 1
            new_column.append(value)
            i += 1

        # At the end check if trailing OIDs are missing
        while i < len(endoids):
            new_column.append("")  # (beginoid + '.' +endoids[i], "") )
            i += 1
        new_columns.append((new_column, value_encoding))

    return new_columns


def _are_ascending_oids(oid_list):
    for a in range(len(oid_list) - 1):
        if _cmp_oids(oid_list[a], oid_list[a + 1]) > 0:  # == 0 should never happen
            return False
    return True


def _construct_snmp_table_of_rows(columns):
    if not columns:
        return []

    # Now construct table by swapping X and Y.
    new_info = []
    for index in range(len(columns[0])):
        row = [c[index] for c in columns]
        new_info.append(row)
    return new_info


def _is_snmpwalk_cachable(column):
    return isinstance(column, tuple) and column[0] == "cached"


def _get_cached_snmpwalk(hostname, fetchoid):
    path = _snmpwalk_cache_path(hostname, fetchoid)
    try:
        console.vverbose("  Loading %s from walk cache %s\n" % (fetchoid, path))
        return store.load_data_from_file(path)
    except Exception:
        if cmk.utils.debug.enabled():
            raise
        console.verbose("  Failed loading walk cache. Continue without it.\n" % path)
        return None


def _save_snmpwalk_cache(hostname, fetchoid, rowinfo):
    path = _snmpwalk_cache_path(hostname, fetchoid)

    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    console.vverbose("  Saving walk of %s to walk cache %s\n" % (fetchoid, path))
    store.save_data_to_file(path, rowinfo, pretty=False)


def _snmpwalk_cache_path(hostname, fetchoid):
    return os.path.join(cmk.utils.paths.var_dir, "snmp_cache", hostname, fetchoid)


#.
#   .--Main modes----------------------------------------------------------.
#   |       __  __       _                             _                   |
#   |      |  \/  | __ _(_)_ __    _ __ ___   ___   __| | ___  ___         |
#   |      | |\/| |/ _` | | '_ \  | '_ ` _ \ / _ \ / _` |/ _ \/ __|        |
#   |      | |  | | (_| | | | | | | | | | | | (_) | (_| |  __/\__ \        |
#   |      |_|  |_|\__,_|_|_| |_| |_| |_| |_|\___/ \__,_|\___||___/        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Some main modes to help the user                                     |
#   '----------------------------------------------------------------------'


def do_snmptranslate(walk_filename):
    if not walk_filename:
        raise MKGeneralException("Please provide the name of a SNMP walk file")

    walk_path = "%s/%s" % (cmk.utils.paths.snmpwalks_dir, walk_filename)
    if not os.path.exists(walk_path):
        raise MKGeneralException("The walk '%s' does not exist" % walk_path)

    def translate(lines):
        result_lines = []
        try:
            oids_for_command = []
            for line in lines:
                oids_for_command.append(line.split(" ")[0])

            command = ["snmptranslate", "-m", "ALL",
                       "-M+%s" % cmk.utils.paths.local_mibs_dir] + oids_for_command
            p = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=open(os.devnull, "w"), close_fds=True)
            p.wait()
            output = p.stdout.read()
            result = output.split("\n")[0::2]
            for idx, line in enumerate(result):
                result_lines.append((line.strip(), lines[idx].strip()))

        except Exception as e:
            console.error("%s\n" % e)

        return result_lines

    # Translate n-oid's per cycle
    entries_per_cycle = 500
    translated_lines = []

    walk_lines = file(walk_path).readlines()
    console.error("Processing %d lines.\n" % len(walk_lines))

    i = 0
    while i < len(walk_lines):
        console.error("\r%d to go...    " % (len(walk_lines) - i))
        process_lines = walk_lines[i:i + entries_per_cycle]
        translated = translate(process_lines)
        i += len(translated)
        translated_lines += translated
    console.error("\rfinished.                \n")

    # Output formatted
    for translation, line in translated_lines:
        console.output("%s --> %s\n" % (line, translation))


def do_snmpwalk(options, hostnames):
    if "oids" in options and "extraoids" in options:
        raise MKGeneralException("You cannot specify --oid and --extraoid at the same time.")

    if not hostnames:
        raise MKBailOut("Please specify host names to walk on.")

    if not os.path.exists(cmk.utils.paths.snmpwalks_dir):
        os.makedirs(cmk.utils.paths.snmpwalks_dir)

    for hostname in hostnames:
        #TODO: What about SNMP management boards?
        snmp_config = create_snmp_host_config(hostname)

        try:
            _do_snmpwalk_on(snmp_config, options, cmk.utils.paths.snmpwalks_dir + "/" + hostname)
        except Exception as e:
            console.error("Error walking %s: %s\n" % (hostname, e))
            if cmk.utils.debug.enabled():
                raise
        cmk_base.cleanup.cleanup_globals()


def _do_snmpwalk_on(snmp_config, options, filename):
    console.verbose("%s:\n" % snmp_config.hostname)

    oids = oids_to_walk(options)

    with open(filename, "w") as out:
        for rows in _execute_walks_for_dump(snmp_config, oids):
            for oid, value in rows:
                out.write("%s %s\n" % (oid, value))
            console.verbose("%d variables.\n" % len(rows))

    console.verbose("Wrote fetched data to %s%s%s.\n" % (tty.bold, filename, tty.normal))


def _execute_walks_for_dump(snmp_config, oids):
    for oid in oids:
        try:
            console.verbose("Walk on \"%s\"..." % oid)
            yield walk_for_export(snmp_config, oid)
        except Exception as e:
            console.error("Error: %s\n" % e)
            if cmk.utils.debug.enabled():
                raise


def oids_to_walk(options=None):
    if options is None:
        options = {}

    oids = [
        ".1.3.6.1.2.1",  # SNMPv2-SMI::mib-2
        ".1.3.6.1.4.1"  # SNMPv2-SMI::enterprises
    ]

    if "oids" in options:
        oids = options["oids"]

    elif "extraoids" in options:
        oids += options["extraoids"]

    return sorted(oids, key=lambda x: map(int, x.strip(".").split(".")))


def do_snmpget(*args):
    if not args[0]:
        raise MKBailOut("You need to specify an OID.")
    oid = args[0][0]

    config_cache = config.get_config_cache()

    hostnames = args[0][1:]
    if not hostnames:
        hostnames = []
        for host in config_cache.all_active_realhosts():
            host_config = config_cache.get_host_config(host)
            if host_config.is_snmp_host:
                hostnames.append(host)

    for hostname in hostnames:
        #TODO what about SNMP management boards?
        snmp_config = create_snmp_host_config(hostname)

        value = get_single_oid(snmp_config, oid)
        console.output("%s (%s): %r\n" % (hostname, snmp_config.ipaddress, value))
        cmk_base.cleanup.cleanup_globals()


cmk_base.cleanup.register_cleanup(cleanup_host_caches)
