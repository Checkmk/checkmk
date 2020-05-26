#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from typing import Any, List, Optional, Set, Tuple, Union, cast

from six import ensure_binary

import cmk.utils.debug
import cmk.utils.store as store
from cmk.utils.encoding import convert_to_unicode
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.type_defs import (
    OID,
    OID_BIN,
    OID_END,
    OID_END_BIN,
    OID_END_OCTET_STRING,
    OID_STRING,
    ABCSNMPBackend,
    ABCSNMPTree,
    CheckPluginName,
    Column,
    Columns,
    DecodedBinary,
    DecodedValues,
    HostName,
    OIDBytes,
    OIDCached,
    OIDInfo,
    OIDSpec,
    OIDWithColumns,
    OIDWithSubOIDsAndColumns,
    RawValue,
    SNMPHostConfig,
    SNMPRowInfo,
    SNMPTable,
    SNMPValueEncoding,
)

ResultColumnsUnsanitized = List[Tuple[OID, SNMPRowInfo, SNMPValueEncoding]]
ResultColumnsSanitized = List[Tuple[List[RawValue], SNMPValueEncoding]]
ResultColumnsDecoded = List[List[DecodedValues]]


def get_snmp_table(snmp_config, check_plugin_name, oid_info, *, backend):
    # type: (SNMPHostConfig, CheckPluginName, Union[OIDInfo, ABCSNMPTree], ABCSNMPBackend) -> SNMPTable
    return _get_snmp_table(snmp_config, check_plugin_name, oid_info, False, backend=backend)


def get_snmp_table_cached(snmp_config, check_plugin_name, oid_info, *, backend):
    # type: (SNMPHostConfig, CheckPluginName, Union[OIDInfo, ABCSNMPTree], ABCSNMPBackend) -> SNMPTable
    return _get_snmp_table(snmp_config, check_plugin_name, oid_info, True, backend=backend)


SPECIAL_COLUMNS = [
    OID_END,
    OID_STRING,
    OID_BIN,
    OID_END_BIN,
    OID_END_OCTET_STRING,
]


# TODO: OID_END_OCTET_STRING is not used at all. Drop it.
def _get_snmp_table(snmp_config, check_plugin_name, oid_info, use_snmpwalk_cache, *, backend):
    # type: (SNMPHostConfig, CheckPluginName, Union[OIDInfo, ABCSNMPTree], bool, ABCSNMPBackend) -> SNMPTable
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

            rowinfo = _get_snmpwalk(snmp_config,
                                    check_plugin_name,
                                    oid,
                                    fetchoid,
                                    column,
                                    use_snmpwalk_cache,
                                    backend=backend)

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
                new_first_column.append((o, ensure_binary(suboid) + b"." + col_val))
            columns[0] = fetchoid, new_first_column, value_encoding

        info += _make_table(columns, snmp_config)

    return info


def _value_encoding(column):
    # type: (Column) -> SNMPValueEncoding
    return "binary" if isinstance(column, OIDBytes) else "string"


def _make_target_columns(oid_info):
    # type: (Union[OIDInfo, ABCSNMPTree]) -> Tuple[OID, List[Any], Columns]
    #
    # OIDInfo is one of:
    #   - OIDWithColumns = Tuple[OID, Columns]
    #   - OIDWithSubOIDsAndColumns = Tuple[OID, List[OID], Columns]
    #     where List[OID] is a list if OID-infixes that are put between the
    #     baseoid and the columns and prefixed with the index column.
    #
    # TODO: The Union[OIDWithColumns, OIDWithSubOIDsAndColumns] dance is absurd!
    #       Here, we should just have OIDWithSubOIDsAndColumns and
    #       replace `OIDWithColumns` with `Tuple[OID, [], Columns]`.
    #
    # This allows to merge distinct SNMP subtrees with a similar structure
    # to one virtual new tree (look into cmctc_temp for an example)
    suboids = [None]  # type: List
    if isinstance(oid_info, ABCSNMPTree):
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
        if index_format == OID_END:
            val = ensure_binary(_extract_end_oid(fetchoid, o))
        elif index_format == OID_STRING:
            val = ensure_binary(o)
        elif index_format == OID_BIN:
            val = _oid_to_bin(o)
        elif index_format == OID_END_BIN:
            val = _oid_to_bin(_extract_end_oid(fetchoid, o))
        elif index_format == OID_END_OCTET_STRING:
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


def _oid_to_bin(oid):
    # type: (OID) -> RawValue
    return ensure_binary("".join([chr(int(p)) for p in oid.strip(".").split(".")]))


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


def _get_snmpwalk(snmp_config, check_plugin_name, oid, fetchoid, column, use_snmpwalk_cache, *,
                  backend):
    # type: (SNMPHostConfig, CheckPluginName, OID, OID, Column, bool, ABCSNMPBackend) -> SNMPRowInfo
    if column in SPECIAL_COLUMNS:
        return []

    save_to_cache = isinstance(column, OIDCached)
    get_from_cache = save_to_cache and use_snmpwalk_cache
    cached = _get_cached_snmpwalk(snmp_config.hostname, fetchoid) if get_from_cache else None
    if cached is not None:
        return cached
    rowinfo = _perform_snmpwalk(snmp_config, check_plugin_name, oid, fetchoid, backend=backend)
    if save_to_cache:
        _save_snmpwalk_cache(snmp_config.hostname, fetchoid, rowinfo)
    return rowinfo


def _perform_snmpwalk(snmp_config, check_plugin_name, base_oid, fetchoid, *, backend):
    # type: (SNMPHostConfig, CheckPluginName, OID, OID, ABCSNMPBackend) -> SNMPRowInfo
    added_oids = set([])  # type: Set[OID]
    rowinfo = []  # type: SNMPRowInfo

    for context_name in snmp_config.snmpv3_contexts_of(check_plugin_name):
        rows = backend.walk(snmp_config,
                            oid=fetchoid,
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
    # type: (Union[OID, OIDSpec], Optional[OID], Column) -> OID
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
