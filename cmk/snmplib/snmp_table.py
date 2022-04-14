#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Provide methods to get an snmp table with or without caching
"""
from pathlib import Path
from typing import (
    Callable,
    Iterable,
    Iterator,
    List,
    MutableMapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

import cmk.utils.debug
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.type_defs import HostName, SectionName

from .type_defs import (
    BackendSNMPTree,
    OID,
    SNMPBackend,
    SNMPDecodedValues,
    SNMPHostConfig,
    SNMPRawValue,
    SNMPRowInfo,
    SNMPTable,
    SNMPValueEncoding,
    SpecialColumn,
)

ResultColumnsUnsanitized = List[Tuple[OID, SNMPRowInfo, SNMPValueEncoding]]
ResultColumnsSanitized = List[Tuple[List[SNMPRawValue], SNMPValueEncoding]]
ResultColumnsDecoded = List[List[SNMPDecodedValues]]


class WalkCache(
    MutableMapping[str, Tuple[bool, SNMPRowInfo]]
):  # pylint: disable=too-many-ancestors
    """A cache on a per-fetchoid basis

    This cache is different from section stores in that is per-fetchoid,
    which means it deduplicates fetch operations across section definitions.

    The fetched data is always saved to a file *if* the respective OID is marked as being cached
    by the plugin using `OIDCached` (that is: if the save_to_cache attribute of the OID object
    is true).
    """

    __slots__ = ("_store", "_path")

    def __init__(self, host_name: HostName):
        self._store: MutableMapping[str, Tuple[bool, SNMPRowInfo]] = {}
        self._path = Path(cmk.utils.paths.var_dir, "snmp_cache", host_name)

    def _read_row(self, path: Path) -> SNMPRowInfo:
        return store.load_object_from_file(path, default=None)

    def _write_row(self, path: Path, rowinfo: SNMPRowInfo) -> None:
        return store.save_object_to_file(path, rowinfo, pretty=False)

    @staticmethod
    def _oid2name(fetchoid: str) -> str:
        return f"OID{fetchoid}"

    @staticmethod
    def _name2oid(basename: str) -> str:
        return basename[3:]

    def _iterfiles(self) -> Iterable[Path]:
        if not self._path.is_dir():
            return ()
        return self._path.iterdir()

    def __repr__(self) -> str:
        return "%s(%r)" % (type(self).__name__, self._store)

    def __getitem__(self, key: str) -> Tuple[bool, SNMPRowInfo]:
        return self._store.__getitem__(key)

    def __setitem__(self, key: str, value: Tuple[bool, SNMPRowInfo]) -> None:
        return self._store.__setitem__(key, value)

    def __delitem__(self, key: str) -> None:
        return self._store.__delitem__(key)

    def __iter__(self) -> Iterator[str]:
        return self._store.__iter__()

    def __len__(self) -> int:
        return self._store.__len__()

    def clear(self) -> None:
        for path in self._iterfiles():
            path.unlink(missing_ok=True)

    def load(
        self,
        *,
        trees: Iterable[BackendSNMPTree],
    ) -> None:
        """Try to read the OIDs data from cache files"""
        # Do not load the cached data if *any* plugin needs live data
        do_not_load = {
            f"{tree.base}.{oid.column}"
            for tree in trees
            for oid in tree.oids
            if not oid.save_to_cache
        }

        for path in self._iterfiles():
            fetchoid = self._name2oid(path.name)
            if fetchoid in do_not_load:
                continue

            console.vverbose(f"  Loading {fetchoid} from walk cache {path}\n")
            try:
                read_walk = self._read_row(path)
            except Exception:
                console.vverbose(f"  Failed to load {fetchoid} from walk cache {path}\n")
                if cmk.utils.debug.enabled():
                    raise
                continue

            if read_walk is not None:
                # 'False': no need to store this value: it is already stored!
                self._store[fetchoid] = (False, read_walk)

    def save(self) -> None:
        self._path.mkdir(parents=True, exist_ok=True)

        for fetchoid, (save_flag, rowinfo) in self._store.items():
            if not save_flag:
                continue

            path = self._path / self._oid2name(fetchoid)
            console.vverbose(f"  Saving walk of {fetchoid} to walk cache {path}\n")
            self._write_row(path, rowinfo)


def get_snmp_table(
    *,
    section_name: Optional[SectionName],
    tree: BackendSNMPTree,
    walk_cache: MutableMapping[str, Tuple[bool, SNMPRowInfo]],
    backend: SNMPBackend,
) -> Sequence[SNMPTable]:

    index_column = -1
    index_format: Optional[SpecialColumn] = None
    columns: ResultColumnsUnsanitized = []
    # Detect missing (empty columns)
    max_len = 0
    max_len_col = -1

    for oid in tree.oids:
        fetchoid: OID = "%s.%s" % (tree.base, oid.column)
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

    return _make_table(columns, backend.config)


def _make_index_rows(
    max_column: SNMPRowInfo,
    index_format: SpecialColumn,
    fetchoid: OID,
) -> SNMPRowInfo:
    index_rows = []
    for o, _unused_value in max_column:
        if index_format is SpecialColumn.END:
            val = _extract_end_oid(fetchoid, o).encode()
        elif index_format is SpecialColumn.STRING:
            val = o.encode()
        elif index_format is SpecialColumn.BIN:
            val = _oid_to_bin(o)
        elif index_format is SpecialColumn.END_BIN:
            val = _oid_to_bin(_extract_end_oid(fetchoid, o))
        elif index_format is SpecialColumn.END_OCTET_STRING:
            val = _oid_to_bin(_extract_end_oid(fetchoid, o))[1:]
        else:
            raise MKGeneralException("Invalid index format %r" % (index_format,))
        index_rows.append((o, val))
    return index_rows


def _make_table(
    columns: ResultColumnsUnsanitized, snmp_config: SNMPHostConfig
) -> Sequence[SNMPTable]:
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
    return bytes(int(p) for p in oid.split(".") if p)


def _extract_end_oid(prefix: OID, complete: OID) -> OID:
    return complete[len(prefix) :].lstrip(".")


# sort OID strings numerically
def _oid_to_intlist(oid: OID) -> List[int]:
    if oid:
        return list(map(int, oid.split(".")))
    return []


def _cmp_oids(o1: OID, o2: OID) -> int:
    return (_oid_to_intlist(o1) > _oid_to_intlist(o2)) - (_oid_to_intlist(o1) < _oid_to_intlist(o2))


def _key_oids(o1: OID) -> List[int]:
    return _oid_to_intlist(o1)


def _key_oid_pairs(pair1: Tuple[OID, SNMPRawValue]) -> List[int]:
    return _oid_to_intlist(pair1[0].lstrip("."))


def _get_snmpwalk(
    section_name: Optional[SectionName],
    base: str,
    fetchoid: OID,
    *,
    walk_cache: MutableMapping[str, Tuple[bool, SNMPRowInfo]],
    save_walk_cache: bool,
    backend: SNMPBackend,
) -> SNMPRowInfo:
    try:
        rowinfo = walk_cache[fetchoid][1]
        console.vverbose(f"Already fetched OID: {fetchoid}\n")
        return rowinfo
    except KeyError:
        pass

    rowinfo = _perform_snmpwalk(section_name, base, fetchoid, backend=backend)
    walk_cache[fetchoid] = (save_walk_cache, rowinfo)
    return rowinfo


def _perform_snmpwalk(
    section_name: Optional[SectionName],
    base_oid: str,
    fetchoid: OID,
    *,
    backend: SNMPBackend,
) -> SNMPRowInfo:
    added_oids: Set[OID] = set([])
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
                console.vverbose("Duplicate OID found: %s (%r)\n" % (row_oid, val))
            else:
                rowinfo.append((row_oid, val))
                added_oids.add(row_oid)

    return rowinfo


def _sanitize_snmp_encoding(
    columns: ResultColumnsSanitized, snmp_config: SNMPHostConfig
) -> ResultColumnsDecoded:
    return [
        _decode_column(column, value_encoding, snmp_config) for column, value_encoding in columns  #
    ]


def _decode_column(
    column: List[SNMPRawValue], value_encoding: SNMPValueEncoding, snmp_config: SNMPHostConfig
) -> List[SNMPDecodedValues]:
    if value_encoding == "string":
        # ? ensure_str is used with potentially different encodings
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


def _construct_snmp_table_of_rows(columns: ResultColumnsDecoded) -> Sequence[SNMPTable]:
    if not columns:
        return []

    # Now construct table by swapping X and Y.
    new_info = []
    for index in range(len(columns[0])):
        row = [c[index] for c in columns]
        new_info.append(row)
    return new_info
