#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from typing import Callable, List, Optional, Set, Tuple, Union

from six import ensure_binary

import cmk.utils.debug
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.type_defs import HostName, SectionName

from .type_defs import (
    ABCSNMPBackend,
    OID,
    OID_BIN,
    OID_END,
    OID_END_BIN,
    OID_END_OCTET_STRING,
    OID_STRING,
    OIDBytes,
    OIDCached,
    OIDSpec,
    SNMPDecodedValues,
    SNMPHostConfig,
    SNMPRawValue,
    SNMPRowInfo,
    SNMPTable,
    SNMPTree,
    SNMPValueEncoding,
)

ResultColumnsUnsanitized = List[Tuple[OID, SNMPRowInfo, SNMPValueEncoding]]
ResultColumnsSanitized = List[Tuple[List[SNMPRawValue], SNMPValueEncoding]]
ResultColumnsDecoded = List[List[SNMPDecodedValues]]


def get_snmp_table(section_name: Optional[SectionName], oid_info: SNMPTree, *,
                   backend: ABCSNMPBackend) -> SNMPTable:
    return _get_snmp_table(section_name, oid_info, False, backend=backend)


def get_snmp_table_cached(section_name: Optional[SectionName], oid_info: SNMPTree, *,
                          backend: ABCSNMPBackend) -> SNMPTable:
    return _get_snmp_table(section_name, oid_info, True, backend=backend)


SPECIAL_COLUMNS = [
    OID_END,
    OID_STRING,
    OID_BIN,
    OID_END_BIN,
    OID_END_OCTET_STRING,
]


# TODO: OID_END_OCTET_STRING is not used at all. Drop it.
def _get_snmp_table(section_name: Optional[SectionName], tree: SNMPTree, use_snmpwalk_cache: bool,
                    *, backend: ABCSNMPBackend) -> SNMPTable:

    index_column = -1
    index_format = None
    columns: ResultColumnsUnsanitized = []
    # Detect missing (empty columns)
    max_len = 0
    max_len_col = -1

    for column in tree.oids:
        fetchoid: OID = "%s.%s" % (tree.base, column)
        value_encoding = _value_encoding(column)
        # column may be integer or string like "1.5.4.2.3"
        # if column is 0, we do not fetch any data from snmp, but use
        # a running counter as index. If the index column is the first one,
        # we do not know the number of entries right now. We need to fill
        # in later. If the column is OID_STRING or OID_BIN we do something
        # similar: we fill in the complete OID of the entry, either as
        # string or as binary UTF-8 encoded number string
        if column in SPECIAL_COLUMNS:
            if index_column >= 0 and index_column != len(columns):
                raise MKGeneralException(
                    "Invalid SNMP OID specification in implementation of check. "
                    "You can only use one of OID_END, OID_STRING, OID_BIN, OID_END_BIN "
                    "and OID_END_OCTET_STRING.")
            rowinfo = []
            index_column = len(columns)
            index_format = column
        else:
            rowinfo = _get_snmpwalk(
                section_name,
                tree.base,
                fetchoid,
                use_snmpwalk_cache,
                save_to_cache=isinstance(column, OIDCached),
                backend=backend,
            )
            if len(rowinfo) > max_len:
                max_len_col = len(columns)

        max_len = max(max_len, len(rowinfo))
        columns.append((fetchoid, rowinfo, value_encoding))

    if index_column != -1:
        # Take end-oids of non-index columns as indices
        fetchoid, max_column, value_encoding = columns[max_len_col]

        index_rows = _make_index_rows(max_column, index_format, fetchoid)
        index_encoding = columns[index_column][-1]
        columns[index_column] = fetchoid, index_rows, index_encoding

    return _make_table(columns, backend.config)


def _value_encoding(column: Union[OIDSpec, int]) -> SNMPValueEncoding:
    return "binary" if isinstance(column, OIDBytes) else "string"


def _make_index_rows(
    max_column: SNMPRowInfo,
    index_format: Optional[Union[OIDSpec, int]],
    fetchoid: OID,
) -> SNMPRowInfo:
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


def _make_table(columns: ResultColumnsUnsanitized, snmp_config: SNMPHostConfig) -> SNMPTable:
    # Here we have to deal with a nasty problem: Some brain-dead devices
    # omit entries in some sub OIDs. This happens e.g. for CISCO 3650
    # in the interfaces MIB with 64 bit counters. So we need to look at
    # the OIDs and watch out for gaps we need to fill with dummy values.
    sanitized_columns = _sanitize_snmp_table_columns(columns)

    # From all SNMP data sources (stored walk, classic SNMP, inline SNMP) we
    # get python byte strings. But for Checkmk we need unicode strings now.
    # Convert them by using the standard Checkmk approach for incoming data
    decoded_columns = _sanitize_snmp_encoding(sanitized_columns, snmp_config)

    return _construct_snmp_table_of_rows(decoded_columns)


def _oid_to_bin(oid: OID) -> SNMPRawValue:
    return ensure_binary("".join([chr(int(p)) for p in oid.strip(".").split(".")]))


def _extract_end_oid(prefix: OID, complete: OID) -> OID:
    return complete[len(prefix):].lstrip('.')


# sort OID strings numerically
def _oid_to_intlist(oid: OID) -> List[int]:
    if oid:
        return list(map(int, oid.split('.')))
    return []


def _cmp_oids(o1: OID, o2: OID) -> int:
    return (_oid_to_intlist(o1) > _oid_to_intlist(o2)) - (_oid_to_intlist(o1) < _oid_to_intlist(o2))


def _key_oids(o1: OID) -> List[int]:
    return _oid_to_intlist(o1)


def _key_oid_pairs(pair1: Tuple[OID, SNMPRawValue]) -> List[int]:
    return _oid_to_intlist(pair1[0].lstrip('.'))


def _get_snmpwalk(
    section_name: Optional[SectionName],
    base: OIDSpec,
    fetchoid: OID,
    use_snmpwalk_cache: bool,
    *,
    save_to_cache: bool,
    backend: ABCSNMPBackend,
) -> SNMPRowInfo:
    get_from_cache = save_to_cache and use_snmpwalk_cache
    cached = _get_cached_snmpwalk(backend.hostname, fetchoid) if get_from_cache else None
    if cached is not None:
        return cached
    rowinfo = _perform_snmpwalk(section_name, base, fetchoid, backend=backend)
    if save_to_cache:
        _save_snmpwalk_cache(backend.hostname, fetchoid, rowinfo)
    return rowinfo


def _perform_snmpwalk(
    section_name: Optional[SectionName],
    base_oid: OIDSpec,
    fetchoid: OID,
    *,
    backend: ABCSNMPBackend,
) -> SNMPRowInfo:
    added_oids: Set[OID] = set([])
    rowinfo: SNMPRowInfo = []

    for context_name in backend.config.snmpv3_contexts_of(section_name):
        rows = backend.walk(
            oid=fetchoid,
            # revert back to legacy "possilbly-empty-string"-Type
            # TODO: pass Optional[SectionName] along!
            check_plugin_name=str(section_name) if section_name else "",
            table_base_oid=str(base_oid),
            context_name=context_name,
        )

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


def _sanitize_snmp_encoding(columns: ResultColumnsSanitized,
                            snmp_config: SNMPHostConfig) -> ResultColumnsDecoded:
    return [
        _decode_column(column, value_encoding, snmp_config)  #
        for column, value_encoding in columns
    ]


def _decode_column(column: List[SNMPRawValue], value_encoding: SNMPValueEncoding,
                   snmp_config: SNMPHostConfig) -> List[SNMPDecodedValues]:
    if value_encoding == "string":
        decode: Callable[[bytes], SNMPDecodedValues] = snmp_config.ensure_str
    else:
        decode = lambda v: list(bytearray(v))
    return [decode(v) for v in column]


def _sanitize_snmp_table_columns(columns: ResultColumnsUnsanitized) -> ResultColumnsSanitized:
    # First compute the complete list of end-oids appearing in the output
    # by looping all results and putting the endoids to a flat list
    endoids: List[OID] = []
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
    new_columns: ResultColumnsSanitized = []
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


def _are_ascending_oids(oid_list: List[OID]) -> bool:
    for a in range(len(oid_list) - 1):
        if _cmp_oids(oid_list[a], oid_list[a + 1]) > 0:  # == 0 should never happen
            return False
    return True


def _construct_snmp_table_of_rows(columns: ResultColumnsDecoded) -> SNMPTable:
    if not columns:
        return []

    # Now construct table by swapping X and Y.
    new_info = []
    for index in range(len(columns[0])):
        row = [c[index] for c in columns]
        new_info.append(row)
    return new_info


def _get_cached_snmpwalk(hostname: HostName, fetchoid: OID) -> Optional[SNMPRowInfo]:
    path = _snmpwalk_cache_path(hostname, fetchoid)
    try:
        console.vverbose("  Loading %s from walk cache %s\n" % (fetchoid, path))
        return store.load_object_from_file(path)
    except Exception:
        if cmk.utils.debug.enabled():
            raise
        console.verbose("  Failed loading walk cache from %s. Continue without it.\n" % path)
        return None


def _save_snmpwalk_cache(hostname: HostName, fetchoid: OID, rowinfo: SNMPRowInfo) -> None:
    path = _snmpwalk_cache_path(hostname, fetchoid)

    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))

    console.vverbose("  Saving walk of %s to walk cache %s\n" % (fetchoid, path))
    store.save_object_to_file(path, rowinfo, pretty=False)


def _snmpwalk_cache_path(hostname: HostName, fetchoid: OID) -> str:
    return os.path.join(cmk.utils.paths.var_dir, "snmp_cache", hostname, fetchoid)
