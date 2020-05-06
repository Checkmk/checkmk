#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
import subprocess
from contextlib import suppress
from typing import Any, Text, cast, Iterable, Set, Tuple, Optional, Dict, List, Union  # pylint: disable=unused-import

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

import six

import cmk.utils.debug
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException, MKBailOut
import cmk.utils.store as store
import cmk.utils.snmp_cache as snmp_cache
from cmk.utils.encoding import convert_to_unicode
from cmk.utils.log import console

import cmk.base.config as config
import cmk.base.classic_snmp as classic_snmp
import cmk.base.ip_lookup as ip_lookup
import cmk.base.cleanup
import cmk.base.snmp_utils as snmp_utils
from cmk.base.api.agent_based.section_types import SNMPTree
from cmk.fetchers.snmp_backend import StoredWalkSNMPBackend, ABCSNMPBackend  # pylint: disable=cmk-module-layer-violation

from cmk.utils.type_defs import (  # noqa: F401 # pylint: disable=unused-import
    HostName, HostAddress,
)
from cmk.base.check_utils import (  # pylint: disable=unused-import
    CheckPluginName,)
from cmk.base.snmp_utils import (  # pylint: disable=unused-import
    OIDInfo, OIDWithColumns, OIDWithSubOIDsAndColumns, OID, Column, SNMPValueEncoding,
    SNMPHostConfig, SNMPRowInfo, SNMPRowInfoForStoredWalk, SNMPTable, ResultColumnsUnsanitized,
    ResultColumnsSanitized, ResultColumnsDecoded, RawValue, ContextName, DecodedBinary, SNMPContext,
    DecodedString, Columns,
)

try:
    import cmk.base.cee.inline_snmp as inline_snmp
except ImportError:
    inline_snmp = None  # type: ignore[assignment]

_enforce_stored_walks = False

SNMPWalkOptions = Dict[str, List[OID]]

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
    # type: (str) -> SNMPHostConfig
    host_config = config.get_config_cache().get_host_config(hostname)

    # ip_lookup.lookup_ipv4_address() returns Optional[str] in general, but for
    # all cases that reach the code here we seem to have "str".
    address = ip_lookup.lookup_ip_address(hostname)
    if address is None:
        raise MKGeneralException("Failed to gather IP address of %s" % hostname)

    return host_config.snmp_config(address)


def get_snmp_table(snmp_config, check_plugin_name, oid_info):
    # type: (SNMPHostConfig, CheckPluginName, Union[OIDInfo, SNMPTree]) -> SNMPTable
    return _get_snmp_table(snmp_config, check_plugin_name, oid_info, False)


def get_snmp_table_cached(snmp_config, check_plugin_name, oid_info):
    # type: (SNMPHostConfig, CheckPluginName, Union[OIDInfo, SNMPTree]) -> SNMPTable
    return _get_snmp_table(snmp_config, check_plugin_name, oid_info, True)


SPECIAL_COLUMNS = [
    snmp_utils.OID_END,
    snmp_utils.OID_STRING,
    snmp_utils.OID_BIN,
    snmp_utils.OID_END_BIN,
    snmp_utils.OID_END_OCTET_STRING,
]


# TODO: OID_END_OCTET_STRING is not used at all. Drop it.
def _get_snmp_table(snmp_config, check_plugin_name, oid_info, use_snmpwalk_cache):
    # type: (SNMPHostConfig, CheckPluginName, Union[OIDInfo,SNMPTree], bool) -> SNMPTable
    oid, suboids, targetcolumns = _make_target_columns(oid_info)

    index_column = -1
    index_format = None
    info = []  # type: SNMPTable
    for suboid in suboids:
        columns = []  # type: ResultColumnsUnsanitized
        # Detect missing (empty columns)
        max_len = 0
        max_len_col = -1

        for column in targetcolumns:
            fetchoid = _compute_fetch_oid(oid, suboid, column)
            value_encoding = _value_encoding(column)
            # column may be integer or string like "1.5.4.2.3"
            # if column is 0, we do not fetch any data from snmp, but use
            # a running counter as index. If the index column is the first one,
            # we do not know the number of entries right now. We need to fill
            # in later. If the column is OID_STRING or OID_BIN we do something
            # similar: we fill in the complete OID of the entry, either as
            # string or as binary UTF-8 encoded number string
            if column in SPECIAL_COLUMNS and index_column >= 0 and index_column != len(columns):
                raise MKGeneralException(
                    "Invalid SNMP OID specification in implementation of check. "
                    "You can only use one of OID_END, OID_STRING, OID_BIN, OID_END_BIN and OID_END_OCTET_STRING."
                )

            rowinfo = _get_snmpwalk(snmp_config, check_plugin_name, oid, fetchoid, column,
                                    use_snmpwalk_cache)

            if column in SPECIAL_COLUMNS:
                index_column = len(columns)
                index_format = column
            elif len(rowinfo) > max_len:
                max_len_col = len(columns)
            max_len = max(max_len, len(rowinfo))
            columns.append((fetchoid, rowinfo, value_encoding))

        if index_column != -1:
            # Take end-oids of non-index columns as indices
            fetchoid, max_column, value_encoding = columns[max_len_col]

            index_rows = _make_index_rows(max_column, index_format, fetchoid)
            index_encoding = columns[index_column][-1]
            columns[index_column] = fetchoid, index_rows, index_encoding

        # prepend suboid to first column
        if suboid and columns:
            fetchoid, first_column, value_encoding = columns[0]
            new_first_column = []
            for o, col_val in first_column:
                new_first_column.append((o, six.ensure_binary(suboid) + b"." + col_val))
            columns[0] = fetchoid, new_first_column, value_encoding

        info += _make_table(columns, snmp_config)

    return info


def _value_encoding(column):
    # type: (Column) -> SNMPValueEncoding
    return "binary" if isinstance(column, snmp_utils.OIDBytes) else "string"


def _make_target_columns(oid_info):
    # type: (Union[OIDInfo, SNMPTree]) -> Tuple[OID, List[Any], Columns]
    # oid_info is either ( oid, columns ) or
    # ( oid, suboids, columns )
    # suboids is a list if OID-infixes that are put between baseoid
    # and the columns and also prefixed to the index column. This
    # allows to merge distinct SNMP subtrees with a similar structure
    # to one virtual new tree (look into cmctc_temp for an example)
    suboids = [None]  # type: List
    if isinstance(oid_info, SNMPTree):
        # TODO (mo): Via SNMPTree is the way to go. Remove all other cases
        #            once we have the auto-conversion of SNMPTrees in place.
        #            In particular:
        #              * remove all 'suboids' related code (index_column!)
        #              * remove all casts, and extend the livetime of the
        #                 SNMPTree Object as far as possible.
        #             * I think the below code can be improved by making
        #               SNMPTree an iterable.
        tmp_base = str(oid_info.base)
        oid, targetcolumns = cast(OIDWithColumns, (tmp_base, oid_info.oids))
    elif len(oid_info) == 2:
        oid, targetcolumns = cast(OIDWithColumns, oid_info)
    else:
        oid, suboids, targetcolumns = cast(OIDWithSubOIDsAndColumns, oid_info)

    if not oid.startswith("."):
        raise MKGeneralException("OID definition '%s' does not begin with ." % oid)

    return oid, suboids, targetcolumns


def _make_index_rows(max_column, index_format, fetchoid):
    # type: (SNMPRowInfo, Optional[Column], OID) -> SNMPRowInfo
    index_rows = []
    for o, _unused_value in max_column:
        if index_format == snmp_utils.OID_END:
            val = six.ensure_binary(_extract_end_oid(fetchoid, o))
        elif index_format == snmp_utils.OID_STRING:
            val = six.ensure_binary(o)
        elif index_format == snmp_utils.OID_BIN:
            val = _oid_to_bin(o)
        elif index_format == snmp_utils.OID_END_BIN:
            val = _oid_to_bin(_extract_end_oid(fetchoid, o))
        elif index_format == snmp_utils.OID_END_OCTET_STRING:
            val = _oid_to_bin(_extract_end_oid(fetchoid, o))[1:]
        else:
            raise MKGeneralException("Invalid index format %r" % (index_format,))
        index_rows.append((o, val))
    return index_rows


def _make_table(columns, snmp_config):
    # type: (ResultColumnsUnsanitized, SNMPHostConfig) -> SNMPTable
    # Here we have to deal with a nasty problem: Some brain-dead devices
    # omit entries in some sub OIDs. This happens e.g. for CISCO 3650
    # in the interfaces MIB with 64 bit counters. So we need to look at
    # the OIDs and watch out for gaps we need to fill with dummy values.
    sanitized_columns = _sanitize_snmp_table_columns(columns)

    # From all SNMP data sources (stored walk, classic SNMP, inline SNMP) we
    # get python byte strings. But for Check_MK we need unicode strings now.
    # Convert them by using the standard Check_MK approach for incoming data
    decoded_columns = _sanitize_snmp_encoding(snmp_config, sanitized_columns)

    return _construct_snmp_table_of_rows(decoded_columns)


# Contextes can only be used when check_plugin_name is given.
def get_single_oid(snmp_config, oid, check_plugin_name=None, do_snmp_scan=True):
    # type: (SNMPHostConfig, str, Optional[str], bool) -> Optional[DecodedString]
    # The OID can end with ".*". In that case we do a snmpgetnext and try to
    # find an OID with the prefix in question. The *cache* is working including
    # the X, however.
    if oid[0] != '.':
        if cmk.utils.debug.enabled():
            raise MKGeneralException("OID definition '%s' does not begin with a '.'" % oid)
        oid = '.' + oid

    # TODO: Use generic cache mechanism
    if snmp_cache.is_in_single_oid_cache(oid):
        console.vverbose("       Using cached OID %s: " % oid)
        cached_value = snmp_cache.get_oid_from_single_oid_cache(oid)
        console.vverbose("%s%s%r%s\n" % (tty.bold, tty.green, cached_value, tty.normal))
        return cached_value

    # get_single_oid() can only return a single value. When SNMPv3 is used with multiple
    # SNMP contexts, all contextes will be queried until the first answer is received.
    if check_plugin_name is not None and snmp_utils.is_snmpv3_host(snmp_config):
        snmp_contexts = _snmpv3_contexts_of(snmp_config, check_plugin_name)
    else:
        snmp_contexts = [None]

    console.vverbose("       Getting OID %s: " % oid)
    for context_name in snmp_contexts:
        try:
            snmp_backend = SNMPBackendFactory().factory(snmp_config,
                                                        enforce_stored_walks=_enforce_stored_walks)
            value = snmp_backend.get(snmp_config, oid, context_name)

            if value is not None:
                break  # Use first received answer in case of multiple contextes
        except Exception:
            if cmk.utils.debug.enabled():
                raise
            value = None

    if value is not None:
        console.vverbose("%s%s%r%s\n" % (tty.bold, tty.green, value, tty.normal))
    else:
        console.vverbose("failed.\n")

    if value is not None:
        decoded_value = convert_to_unicode(
            value, encoding=snmp_config.character_encoding)  # type: Optional[DecodedString]
    else:
        decoded_value = value

    snmp_cache.set_single_oid_cache(oid, decoded_value)
    return decoded_value


class SNMPBackendFactory(object):  # pylint: disable=useless-object-inheritance
    @staticmethod
    def factory(snmp_config, enforce_stored_walks):
        # type: (SNMPHostConfig, bool) -> ABCSNMPBackend
        if enforce_stored_walks or snmp_config.is_usewalk_host:
            return StoredWalkSNMPBackend()

        if snmp_config.is_inline_snmp_host:
            return inline_snmp.InlineSNMPBackend()

        return classic_snmp.ClassicSNMPBackend()


def walk_for_export(snmp_config, oid):
    # type: (SNMPHostConfig, OID) -> SNMPRowInfoForStoredWalk
    if snmp_config.is_inline_snmp_host:
        backend = inline_snmp.InlineSNMPBackend()  # type: ABCSNMPBackend
    else:
        backend = classic_snmp.ClassicSNMPBackend()

    rows = backend.walk(snmp_config, oid)
    return _convert_rows_for_stored_walk(rows)


def enforce_use_stored_walks():
    # type: () -> None
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
    # type: (SNMPRowInfo) -> SNMPRowInfoForStoredWalk
    def should_be_encoded(v):
        # type: (RawValue) -> bool
        for c in bytearray(v):
            if c < 32 or c > 127:
                return True
        return False

    def hex_encode_value(v):
        # type: (RawValue) -> Text
        encoded = ""
        for c in bytearray(v):
            encoded += "%02X " % c
        return "\"%s\"" % encoded

    new_rows = []  # type: SNMPRowInfoForStoredWalk
    for oid, value in rows:
        if value == b"ENDOFMIBVIEW":
            continue

        if should_be_encoded(value):
            new_rows.append((oid, hex_encode_value(value)))
        else:
            new_rows.append((oid, six.ensure_text(value)))
    return new_rows


def _oid_to_bin(oid):
    # type: (OID) -> RawValue
    return six.ensure_binary("".join([chr(int(p)) for p in oid.strip(".").split(".")]))


def _extract_end_oid(prefix, complete):
    # type: (OID, OID) -> OID
    return complete[len(prefix):].lstrip('.')


# sort OID strings numerically
def _oid_to_intlist(oid):
    # type: (OID) -> List[int]
    if oid:
        return list(map(int, oid.split('.')))
    return []


def _cmp_oids(o1, o2):
    # type: (OID, OID) -> int
    return (_oid_to_intlist(o1) > _oid_to_intlist(o2)) - (_oid_to_intlist(o1) < _oid_to_intlist(o2))


def _key_oids(o1):
    # type: (OID) -> List[int]
    return _oid_to_intlist(o1)


def _key_oid_pairs(pair1):
    # type: (Tuple[OID, RawValue]) -> List[int]
    return _oid_to_intlist(pair1[0].lstrip('.'))


def _snmpv3_contexts_of(snmp_config, check_plugin_name):
    # type: (SNMPHostConfig, CheckPluginName) -> List[SNMPContext]
    for ty, rules in snmp_config.snmpv3_contexts:
        if ty is None or ty == check_plugin_name:
            return rules
    return [None]


def _get_snmpwalk(snmp_config, check_plugin_name, oid, fetchoid, column, use_snmpwalk_cache):
    # type: (SNMPHostConfig, CheckPluginName, OID, OID, Column, bool) -> SNMPRowInfo
    if column in SPECIAL_COLUMNS:
        return []

    save_to_cache = isinstance(column, snmp_utils.OIDCached)
    get_from_cache = save_to_cache and use_snmpwalk_cache
    cached = _get_cached_snmpwalk(snmp_config.hostname, fetchoid) if get_from_cache else None
    if cached is not None:
        return cached
    rowinfo = _perform_snmpwalk(snmp_config, check_plugin_name, oid, fetchoid)
    if save_to_cache:
        _save_snmpwalk_cache(snmp_config.hostname, fetchoid, rowinfo)
    return rowinfo


def _perform_snmpwalk(snmp_config, check_plugin_name, base_oid, fetchoid):
    # type: (SNMPHostConfig, CheckPluginName, OID, OID) -> SNMPRowInfo
    added_oids = set([])  # type: Set[OID]
    rowinfo = []  # type: SNMPRowInfo
    if snmp_utils.is_snmpv3_host(snmp_config):
        snmp_contexts = _snmpv3_contexts_of(snmp_config, check_plugin_name)
    else:
        snmp_contexts = [None]

    for context_name in snmp_contexts:
        snmp_backend = SNMPBackendFactory().factory(snmp_config,
                                                    enforce_stored_walks=_enforce_stored_walks)

        rows = snmp_backend.walk(snmp_config,
                                 fetchoid,
                                 check_plugin_name=check_plugin_name,
                                 table_base_oid=base_oid,
                                 context_name=context_name)

        # I've seen a broken device (Mikrotik Router), that broke after an
        # update to RouterOS v6.22. It would return 9 time the same OID when
        # .1.3.6.1.2.1.1.1.0 was being walked. We try to detect these situations
        # by removing any duplicate OID information
        if len(rows) > 1 and rows[0][0] == rows[1][0]:
            console.vverbose("Detected broken SNMP agent. Ignoring duplicate OID %s.\n" %
                             rows[0][0])
            rows = rows[:1]

        for row_oid, val in rows:
            if row_oid in added_oids:
                console.vverbose("Duplicate OID found: %s (%r)\n" % (row_oid, val))
            else:
                rowinfo.append((row_oid, val))
                added_oids.add(row_oid)

    return rowinfo


def _compute_fetch_oid(oid, suboid, column):
    # type: (Union[OID,snmp_utils.OIDSpec], Optional[OID], Column) -> OID
    if suboid:
        fetchoid = "%s.%s" % (oid, suboid)
    else:
        fetchoid = str(oid)

    if str(column) != "":
        fetchoid += "." + str(column)

    return fetchoid


def _sanitize_snmp_encoding(snmp_config, columns):
    # type: (SNMPHostConfig, ResultColumnsSanitized) -> ResultColumnsDecoded
    snmp_encoding = snmp_config.character_encoding

    def decode_string_func(s):
        return convert_to_unicode(s, encoding=snmp_encoding)

    new_columns = []  # type: ResultColumnsDecoded
    for column, value_encoding in columns:
        if value_encoding == "string":
            new_columns.append(list(map(decode_string_func, column)))
        else:
            new_columns.append(list(map(_snmp_decode_binary, column)))
    return new_columns


def _snmp_decode_binary(text):
    # type: (RawValue) -> DecodedBinary
    return list(bytearray(text))


def _sanitize_snmp_table_columns(columns):
    # type: (ResultColumnsUnsanitized) -> ResultColumnsSanitized
    # First compute the complete list of end-oids appearing in the output
    # by looping all results and putting the endoids to a flat list
    endoids = []  # type: List[OID]
    for fetchoid, row_info, value_encoding in columns:
        for o, value in row_info:
            endoid = _extract_end_oid(fetchoid, o)
            if endoid not in endoids:
                endoids.append(endoid)

    # The list needs to be sorted to prevent problems when the first
    # column has missing values in the middle of the tree.
    if not _are_ascending_oids(endoids):
        endoids.sort(key=_key_oids)
        need_sort = True
    else:
        need_sort = False

    # Now fill gaps in columns where some endois are missing
    new_columns = []  # type: ResultColumnsSanitized
    for fetchoid, row_info, value_encoding in columns:
        # It might happen that end OIDs are not ordered. Fix the OID sorting to make
        # it comparable to the already sorted endoids list. Otherwise we would get
        # some mixups when filling gaps
        if need_sort:
            row_info.sort(key=_key_oid_pairs)

        i = 0
        new_column = []
        # Loop all lines to fill holes in the middle of the list. All
        # columns check the following lines for the correct endoid. If
        # an endoid differs empty values are added until the hole is filled
        for o, value in row_info:
            eo = _extract_end_oid(fetchoid, o)
            if len(row_info) != len(endoids):
                while i < len(endoids) and endoids[i] != eo:
                    new_column.append(b"")  # (beginoid + '.' +endoids[i], "" ) )
                    i += 1
            new_column.append(value)
            i += 1

        # At the end check if trailing OIDs are missing
        while i < len(endoids):
            new_column.append(b"")  # (beginoid + '.' +endoids[i], "") )
            i += 1
        new_columns.append((new_column, value_encoding))

    return new_columns


def _are_ascending_oids(oid_list):
    # type: (List[OID]) -> bool
    for a in range(len(oid_list) - 1):
        if _cmp_oids(oid_list[a], oid_list[a + 1]) > 0:  # == 0 should never happen
            return False
    return True


def _construct_snmp_table_of_rows(columns):
    # type: (ResultColumnsDecoded) -> SNMPTable
    if not columns:
        return []

    # Now construct table by swapping X and Y.
    new_info = []
    for index in range(len(columns[0])):
        row = [c[index] for c in columns]
        new_info.append(row)
    return new_info


def _get_cached_snmpwalk(hostname, fetchoid):
    # type: (HostName, OID) -> Optional[SNMPRowInfo]
    path = _snmpwalk_cache_path(hostname, fetchoid)
    try:
        console.vverbose("  Loading %s from walk cache %s\n" % (fetchoid, path))
        return store.load_object_from_file(path)
    except Exception:
        if cmk.utils.debug.enabled():
            raise
        console.verbose("  Failed loading walk cache from %s. Continue without it.\n" % path)
        return None


def _save_snmpwalk_cache(hostname, fetchoid, rowinfo):
    # type: (HostName, OID, SNMPRowInfo) -> None
    path = _snmpwalk_cache_path(hostname, fetchoid)

    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    console.vverbose("  Saving walk of %s to walk cache %s\n" % (fetchoid, path))
    store.save_object_to_file(path, rowinfo, pretty=False)


def _snmpwalk_cache_path(hostname, fetchoid):
    # type: (HostName, OID) -> str
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
    # type: (str) -> None
    if not walk_filename:
        raise MKGeneralException("Please provide the name of a SNMP walk file")

    walk_path = "%s/%s" % (cmk.utils.paths.snmpwalks_dir, walk_filename)
    if not os.path.exists(walk_path):
        raise MKGeneralException("The walk '%s' does not exist" % walk_path)

    def translate(lines):
        # type: (List[bytes]) -> List[Tuple[bytes, bytes]]
        result_lines = []
        try:
            oids_for_command = []
            for line in lines:
                oids_for_command.append(line.split(b" ")[0])

            command = [b"snmptranslate", b"-m", b"ALL",
                       b"-M+%s" % cmk.utils.paths.local_mib_dir] + oids_for_command
            p = subprocess.Popen(command,
                                 stdout=subprocess.PIPE,
                                 stderr=open(os.devnull, "w"),
                                 close_fds=True)
            p.wait()
            if p.stdout is None:
                raise RuntimeError()
            output = p.stdout.read()
            result = output.split(b"\n")[0::2]
            for idx, line in enumerate(result):
                result_lines.append((line.strip(), lines[idx].strip()))

        except Exception as e:
            console.error("%s\n" % e)

        return result_lines

    # Translate n-oid's per cycle
    entries_per_cycle = 500
    translated_lines = []  # type: List[Tuple[bytes, bytes]]

    walk_lines = open(walk_path).readlines()
    console.error("Processing %d lines.\n" % len(walk_lines))

    i = 0
    while i < len(walk_lines):
        console.error("\r%d to go...    " % (len(walk_lines) - i))
        process_lines = walk_lines[i:i + entries_per_cycle]
        # FIXME: This encoding ping-pong os horrible...
        translated = translate([six.ensure_binary(pl) for pl in process_lines])
        i += len(translated)
        translated_lines += translated
    console.error("\rfinished.                \n")

    with suppress(IOError):
        sys.stdout.write("\n".join("%s --> %s" % (six.ensure_str(line), six.ensure_str(translation))
                                   for translation, line in translated_lines) + "\n")


def do_snmpwalk(options, hostnames):
    # type: (SNMPWalkOptions, List[HostName]) -> None
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
        cmk.base.cleanup.cleanup_globals()


def _do_snmpwalk_on(snmp_config, options, filename):
    # type: (SNMPHostConfig, SNMPWalkOptions, str) -> None
    console.verbose("%s:\n" % snmp_config.hostname)

    oids = oids_to_walk(options)

    with Path(filename).open("w", encoding="utf-8") as file:
        for rows in _execute_walks_for_dump(snmp_config, oids):
            for oid, value in rows:
                file.write(six.ensure_text("%s %s\n" % (oid, value)))
            console.verbose("%d variables.\n" % len(rows))

    console.verbose("Wrote fetched data to %s%s%s.\n" % (tty.bold, filename, tty.normal))


def _execute_walks_for_dump(snmp_config, oids):
    # type: (SNMPHostConfig, List[OID]) -> Iterable[SNMPRowInfoForStoredWalk]
    for oid in oids:
        try:
            console.verbose("Walk on \"%s\"..." % oid)
            yield walk_for_export(snmp_config, oid)
        except Exception as e:
            console.error("Error: %s\n" % e)
            if cmk.utils.debug.enabled():
                raise


def oids_to_walk(options=None):
    # type: (Optional[SNMPWalkOptions]) -> List[OID]
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

    return sorted(oids, key=lambda x: list(map(int, x.strip(".").split("."))))


def do_snmpget(oid, hostnames):
    # type: (OID, List[HostName]) -> None
    config_cache = config.get_config_cache()

    if not hostnames:
        hostnames = []
        for host in config_cache.all_active_realhosts():
            host_config = config_cache.get_host_config(host)
            if host_config.is_snmp_host:
                hostnames.append(host)

    for hostname in hostnames:
        #TODO what about SNMP management boards?
        snmp_config = create_snmp_host_config(hostname)
        snmp_cache.initialize_single_oid_cache(snmp_config)

        value = get_single_oid(snmp_config, oid)
        sys.stdout.write("%s (%s): %r\n" % (hostname, snmp_config.ipaddress, value))
        cmk.base.cleanup.cleanup_globals()


cmk.base.cleanup.register_cleanup(snmp_cache.cleanup_host_caches)
if inline_snmp:
    cmk.base.cleanup.register_cleanup(inline_snmp.cleanup_inline_snmp_globals)
