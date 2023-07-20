#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Provide methods to get an snmp table with or without caching
"""

import contextlib
from collections.abc import Callable, MutableMapping, Sequence
from typing import assert_never

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.sectionname import SectionMap as _HostSection
from cmk.utils.sectionname import SectionName

from ._typedefs import (
    BackendSNMPTree,
    OID,
    SNMPBackend,
    SNMPRawValue,
    SNMPRowInfo,
    SNMPValueEncoding,
    SpecialColumn,
)

SNMPDecodedString = str
SNMPDecodedBinary = Sequence[int]
SNMPDecodedValues = SNMPDecodedString | SNMPDecodedBinary
SNMPTable = Sequence[SNMPDecodedValues]
SNMPRawDataElem = Sequence[SNMPTable | Sequence[SNMPTable]]
SNMPRawData = _HostSection[SNMPRawDataElem]
OIDFunction = Callable[
    [OID, SNMPDecodedString | None, SectionName | None], SNMPDecodedString | None
]
SNMPScanFunction = Callable[[OIDFunction], bool]

_ResultColumnsUnsanitized = list[tuple[OID, SNMPRowInfo, SNMPValueEncoding]]
_ResultColumnsSanitized = list[tuple[list[SNMPRawValue], SNMPValueEncoding]]
_ResultColumnsDecoded = list[list[SNMPDecodedValues]]


def get_snmp_table(
    *,
    section_name: SectionName | None,
    tree: BackendSNMPTree,
    walk_cache: MutableMapping[str, tuple[bool, SNMPRowInfo]],
    backend: SNMPBackend,
) -> Sequence[SNMPTable]:
    index_column = -1
    index_format: SpecialColumn | None = None
    columns: _ResultColumnsUnsanitized = []
    # Detect missing (empty columns)
    max_len = 0
    max_len_col = -1

    for oid in tree.oids:
        fetchoid: OID = f"{tree.base}.{oid.column}"
        # column may be integer or string like "1.5.4.2.3"
        # if column is 0, we do not fetch any data from snmp, but use
        # a running counter as index. If the index column is the first one,
        # we do not know the number of entries right now. We need to fill
        # in later. If the column is OID_STRING or OID_BIN we do something
        # similar: we fill in the complete OID of the entry, either as
        # string or as binary UTF-8 encoded number string
        if isinstance(oid.column, SpecialColumn):
            if index_column >= 0 and index_column != len(columns):
                raise MKGeneralException(
                    "Invalid SNMP OID specification in implementation of check. "
                    "You can only use one of OID_END, OID_STRING, OID_BIN, OID_END_BIN "
                    "and OID_END_OCTET_STRING."
                )
            rowinfo = []
            index_column = len(columns)
            index_format = oid.column
        else:
            rowinfo = _get_snmpwalk(
                section_name,
                tree.base,
                fetchoid,
                walk_cache=walk_cache,
                save_walk_cache=oid.save_to_cache,
                backend=backend,
            )
            if len(rowinfo) > max_len:
                max_len_col = len(columns)

        max_len = max(max_len, len(rowinfo))
        columns.append((fetchoid, rowinfo, oid.encoding))

    if index_format is not None:
        # Take end-oids of non-index columns as indices
        fetchoid, max_column, _value_encoding = columns[max_len_col]

        index_rows = _make_index_rows(max_column, index_format, fetchoid)
        index_encoding = columns[index_column][-1]
        columns[index_column] = fetchoid, index_rows, index_encoding

    return _make_table(columns, backend.config.ensure_str)


def _make_index_rows(
    max_column: SNMPRowInfo,
    index_format: SpecialColumn,
    fetchoid: OID,
) -> SNMPRowInfo:
    index_rows = []
    for o, _unused_value in max_column:
        match index_format:
            case SpecialColumn.END:
                val = _extract_end_oid(fetchoid, o).encode()
            case SpecialColumn.STRING:
                val = o.encode()
            case SpecialColumn.BIN:
                val = _oid_to_bin(o)
            case SpecialColumn.END_BIN:
                val = _oid_to_bin(_extract_end_oid(fetchoid, o))
            case SpecialColumn.END_OCTET_STRING:
                val = _oid_to_bin(_extract_end_oid(fetchoid, o))[1:]
            case _:
                assert_never(index_format)
        index_rows.append((o, val))
    return index_rows


def _make_table(
    columns: _ResultColumnsUnsanitized, ensure_str: Callable[[str | bytes], str]
) -> Sequence[SNMPTable]:
    # Here we have to deal with a nasty problem: Some brain-dead devices
    # omit entries in some sub OIDs. This happens e.g. for CISCO 3650
    # in the interfaces MIB with 64 bit counters. So we need to look at
    # the OIDs and watch out for gaps we need to fill with dummy values.
    sanitized_columns = _sanitize_snmp_table_columns(columns)

    # From all SNMP data sources (stored walk, classic SNMP, inline SNMP) we
    # get python byte strings. But for Checkmk we need unicode strings now.
    # Convert them by using the standard Checkmk approach for incoming data
    decoded_columns = _sanitize_snmp_encoding(sanitized_columns, ensure_str)

    return _construct_snmp_table_of_rows(decoded_columns)


def _oid_to_bin(oid: OID) -> SNMPRawValue:
    return bytes(int(p) for p in oid.split(".") if p)


def _extract_end_oid(prefix: OID, complete: OID) -> OID:
    return complete[len(prefix) :].lstrip(".")


def _oid_to_intlist(oid: OID) -> list[int]:
    return list(map(int, oid.split("."))) if oid else []


def _cmp_oids(o1: OID, o2: OID) -> int:
    return (_oid_to_intlist(o1) > _oid_to_intlist(o2)) - (_oid_to_intlist(o1) < _oid_to_intlist(o2))


def _key_oids(o1: OID) -> list[int]:
    return _oid_to_intlist(o1)


def _key_oid_pairs(pair1: tuple[OID, SNMPRawValue]) -> list[int]:
    return _oid_to_intlist(pair1[0].lstrip("."))


def _get_snmpwalk(
    section_name: SectionName | None,
    base: str,
    fetchoid: OID,
    *,
    walk_cache: MutableMapping[str, tuple[bool, SNMPRowInfo]],
    save_walk_cache: bool,
    backend: SNMPBackend,
) -> SNMPRowInfo:
    with contextlib.suppress(KeyError):
        cache_info = walk_cache[fetchoid][1]
        console.vverbose(f"Already fetched OID: {fetchoid}\n")
        return cache_info
    info = _perform_snmpwalk(section_name, base, fetchoid, backend=backend)
    walk_cache[fetchoid] = (save_walk_cache, info)
    return info


def _perform_snmpwalk(
    section_name: SectionName | None,
    base_oid: str,
    fetchoid: OID,
    *,
    backend: SNMPBackend,
) -> SNMPRowInfo:
    added_oids: set[OID] = set()
    rowinfo: SNMPRowInfo = []

    for context_name in backend.config.snmpv3_contexts_of(section_name):
        rows = backend.walk(
            oid=fetchoid,
            section_name=section_name,
            table_base_oid=base_oid,
            context_name=context_name,
        )

        # I've seen a broken device (Mikrotik Router), that broke after an
        # update to RouterOS v6.22. It would return 9 time the same OID when
        # .1.3.6.1.2.1.1.1.0 was being walked. We try to detect these situations
        # by removing any duplicate OID information
        if len(rows) > 1 and rows[0][0] == rows[1][0]:
            console.vverbose(
                "Detected broken SNMP agent. Ignoring duplicate OID %s.\n" % rows[0][0]
            )
            rows = rows[:1]

        for row_oid, val in rows:
            if row_oid in added_oids:
                console.vverbose(f"Duplicate OID found: {row_oid} ({val!r})\n")
            else:
                rowinfo.append((row_oid, val))
                added_oids.add(row_oid)

    return rowinfo


def _sanitize_snmp_encoding(
    columns: _ResultColumnsSanitized, ensure_str: Callable[[str | bytes], str]
) -> _ResultColumnsDecoded:
    return [
        _decode_column(column, value_encoding, ensure_str) for column, value_encoding in columns  #
    ]


def _decode_column(
    column: list[SNMPRawValue],
    value_encoding: SNMPValueEncoding,
    ensure_str: Callable[[SNMPRawValue], SNMPDecodedValues],
) -> list[SNMPDecodedValues]:
    if value_encoding == "string":
        # ? ensure_str is used with potentially different encodings
        decode = ensure_str
    else:

        def decode(v: SNMPRawValue) -> SNMPDecodedValues:
            return list(bytearray(v))

    return [decode(v) for v in column]


def _sanitize_snmp_table_columns(columns: _ResultColumnsUnsanitized) -> _ResultColumnsSanitized:
    # First compute the complete list of end-oids appearing in the output
    # by looping all results and putting the endoids to a flat list
    endoids: list[OID] = []
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
    new_columns: _ResultColumnsSanitized = []
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


def _are_ascending_oids(oid_list: list[OID]) -> bool:
    for a in range(len(oid_list) - 1):
        if _cmp_oids(oid_list[a], oid_list[a + 1]) > 0:  # == 0 should never happen
            return False
    return True


def _construct_snmp_table_of_rows(columns: _ResultColumnsDecoded) -> Sequence[SNMPTable]:
    if not columns:
        return []

    # Now construct table by swapping X and Y.
    new_info = []
    for index in range(len(columns[0])):
        row = [c[index] for c in columns]
        new_info.append(row)
    return new_info
