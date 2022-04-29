#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This module handles tree structures for HW/SW Inventory system and
structured monitoring data of Check_MK.
"""

from __future__ import annotations

import gzip
import io
import pprint
from collections import Counter
from pathlib import Path
from typing import Any, Callable
from typing import Counter as TCounter
from typing import (
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from cmk.utils import store
from cmk.utils.type_defs import HostName

# TODO Cleanup path in utils, base, gui, find ONE place (type defs or similar)
# TODO
# - is_empty -> __bool__
# - is_equal -> __eq__/__ne__
# - merge_with -> __add__
# - count_entries -> __len__?
# TODO Improve/clarify adding Attributes/Table while deserialization/filtering/merging/...

SDRawPath = str
# TODO improve this
SDRawTree = Dict

SDNodeName = str
SDPath = List[SDNodeName]

SDKey = str
SDKeys = List[SDKey]
# TODO be more specific (None, str, float, int, DeltaValue:Tuple of previous)
SDValue = Any  # needs only to support __eq__

SDPairs = Dict[SDKey, SDValue]
# TODO merge with cmk.base.api.agent_based.inventory_classes.py::AttrDict
SDPairsFromPlugins = Mapping[SDKey, SDValue]
LegacyPairs = Dict[SDKey, SDValue]

# TODO SDRows and LegacyRows are the same for now, but SDRows will change in the future
# adapt werk 12389 if inner table structure changes from List[SDRow] to Dict[SDRowIdent, SDRow]
SDKeyColumns = List[SDKey]
SDRowIdent = Tuple[SDValue, ...]
SDRow = Dict[SDKey, SDValue]
SDRows = Dict[SDRowIdent, SDRow]
LegacyRows = List[SDRow]

SDNodePath = Tuple[SDNodeName, ...]
SDNodes = Dict[SDNodeName, "StructuredDataNode"]

SDEncodeAs = Callable
SDDeltaCounter = TCounter[Literal["new", "changed", "removed"]]

# Used for de/serialization and retentions
ATTRIBUTES_KEY = "Attributes"
TABLE_KEY = "Table"

_PAIRS_KEY = "Pairs"
_KEY_COLUMNS_KEY = "KeyColumns"
_ROWS_KEY = "Rows"
_NODES_KEY = "Nodes"
_RETENTIONS_KEY = "Retentions"


class SDDeltaResult(NamedTuple):
    counter: SDDeltaCounter
    delta: StructuredDataNode


class TDeltaResult(NamedTuple):
    counter: SDDeltaCounter
    delta: Table


class ADeltaResult(NamedTuple):
    counter: SDDeltaCounter
    delta: Attributes


class DDeltaResult(NamedTuple):
    counter: SDDeltaCounter
    delta: SDPairs


SDFilterFunc = Callable[[SDKey], bool]


class SDFilter(NamedTuple):
    path: SDPath
    filter_nodes: SDFilterFunc
    filter_attributes: SDFilterFunc
    filter_columns: SDFilterFunc


RawIntervalsFromConfig = List[Dict]
RawRetentionIntervals = Tuple[int, int, int]


class RetentionIntervals(NamedTuple):
    cached_at: int
    cache_interval: int
    retention_interval: int

    @property
    def valid_until(self) -> int:
        return self.cached_at + self.cache_interval

    @property
    def keep_until(self) -> int:
        return self.cached_at + self.cache_interval + self.retention_interval

    def serialize(self) -> RawRetentionIntervals:
        return self.cached_at, self.cache_interval, self.retention_interval

    @classmethod
    def deserialize(cls, raw_intervals: RawRetentionIntervals) -> RetentionIntervals:
        return cls(*raw_intervals)


RawRetentionIntervalsByKeys = Dict[SDKey, RawRetentionIntervals]
RetentionIntervalsByKeys = Dict[SDKey, RetentionIntervals]


class UpdateResult(NamedTuple):
    save_tree: bool
    reason: str


#   .--IO------------------------------------------------------------------.
#   |                              ___ ___                                 |
#   |                             |_ _/ _ \                                |
#   |                              | | | | |                               |
#   |                              | | |_| |                               |
#   |                             |___\___/                                |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# TODO cleanup store: better method names for saving/loading current tree,
# archive files or delta caches.


class StructuredDataStore:
    @staticmethod
    def load_file(file_path: Path) -> StructuredDataNode:
        if raw_tree := store.load_object_from_file(file_path, default=None):
            return StructuredDataNode.deserialize(raw_tree)
        return StructuredDataNode()

    def __init__(self, path: Union[Path, str]) -> None:
        self._path = Path(path)

    def _host_file(self, host_name: HostName) -> Path:
        return self._path / str(host_name)

    def _gz_file(self, host_name: HostName) -> Path:
        return self._path / f"{host_name}.gz"

    def save(self, *, host_name: HostName, tree: StructuredDataNode, pretty: bool = False) -> None:

        self._path.mkdir(parents=True, exist_ok=True)

        filepath = self._host_file(host_name)

        output = tree.serialize()
        store.save_object_to_file(filepath, output, pretty=pretty)

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as f:
            f.write((repr(output) + "\n").encode("utf-8"))
        store.save_bytes_to_file(self._gz_file(host_name), buf.getvalue())

        # Inform Livestatus about the latest inventory update
        store.save_text_to_file(filepath.with_name(".last"), "")

    def load(self, *, host_name: HostName) -> StructuredDataNode:
        return self.load_file(self._host_file(host_name))

    def remove_files(self, *, host_name: HostName) -> None:
        self._host_file(host_name).unlink(missing_ok=True)
        self._gz_file(host_name).unlink(missing_ok=True)

    def archive(self, *, host_name: HostName, archive_dir: Union[Path, str]) -> None:
        target_dir = Path(archive_dir, str(host_name))
        target_dir.mkdir(parents=True, exist_ok=True)

        filepath = self._host_file(host_name)
        filepath.rename(target_dir / str(int(filepath.stat().st_mtime)))


# .
#   .--filters-------------------------------------------------------------.
#   |                       __ _ _ _                                       |
#   |                      / _(_) | |_ ___ _ __ ___                        |
#   |                     | |_| | | __/ _ \ '__/ __|                       |
#   |                     |  _| | | ||  __/ |  \__ \                       |
#   |                     |_| |_|_|\__\___|_|  |___/                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# TODO filter table rows?

_use_all = lambda key: True
_use_nothing = lambda key: False


def _make_choices_filter(choices: Sequence[Union[str, int]]) -> SDFilterFunc:
    return lambda key: key in choices


def make_filter(entry: Union[Tuple[SDPath, Optional[SDKeys]], Dict]) -> SDFilter:
    if isinstance(entry, tuple):
        path, keys = entry
        return (
            SDFilter(
                path=path,
                filter_nodes=_use_all,
                filter_attributes=_use_all,
                filter_columns=_use_all,
            )
            if keys is None
            else SDFilter(
                path=path,
                filter_nodes=_use_nothing,
                filter_attributes=_make_choices_filter(keys) if keys else _use_all,
                filter_columns=_make_choices_filter(keys) if keys else _use_all,
            )
        )

    return SDFilter(
        path=parse_visible_raw_path(entry["visible_raw_path"]),
        filter_attributes=make_filter_from_choice(entry.get("attributes")),
        filter_columns=make_filter_from_choice(entry.get("columns")),
        filter_nodes=make_filter_from_choice(entry.get("nodes")),
    )


def make_filter_from_choice(choice: Union[Tuple[str, List[str]], str, None]) -> SDFilterFunc:
    # choice is of the form:
    #   - ('choices', ['some', 'keys'])
    #   - 'nothing'
    #   - None means _use_all
    if isinstance(choice, tuple):
        return _make_choices_filter(choice[-1])
    if choice == "nothing":
        return _use_nothing
    return _use_all


# .
#   .--StructuredDataNode--------------------------------------------------.
#   |         ____  _                   _                      _           |
#   |        / ___|| |_ _ __ _   _  ___| |_ _   _ _ __ ___  __| |          |
#   |        \___ \| __| '__| | | |/ __| __| | | | '__/ _ \/ _` |          |
#   |         ___) | |_| |  | |_| | (__| |_| |_| | | |  __/ (_| |          |
#   |        |____/ \__|_|   \__,_|\___|\__|\__,_|_|  \___|\__,_|          |
#   |                                                                      |
#   |             ____        _        _   _           _                   |
#   |            |  _ \  __ _| |_ __ _| \ | | ___   __| | ___              |
#   |            | | | |/ _` | __/ _` |  \| |/ _ \ / _` |/ _ \             |
#   |            | |_| | (_| | || (_| | |\  | (_) | (_| |  __/             |
#   |            |____/ \__,_|\__\__,_|_| \_|\___/ \__,_|\___|             |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class StructuredDataNode:
    def __init__(self, *, name: SDNodeName = "", path: Optional[SDNodePath] = None) -> None:
        # Only root node has no name or path
        self.name = name

        if path:
            self.path = path
        else:
            self.path = tuple()

        self.attributes = Attributes(path=path)
        self.table = Table(path=path)
        self._nodes: SDNodes = {}

    def set_path(self, path: SDNodePath) -> None:
        self.path = path
        self.attributes.set_path(path)
        self.table.set_path(path)

    #   ---common methods-------------------------------------------------------

    def is_empty(self) -> bool:
        if not (self.attributes.is_empty() and self.table.is_empty()):
            return False

        for node in self._nodes.values():
            if not node.is_empty():
                return False
        return True

    def is_equal(self, other: object) -> bool:
        if not isinstance(other, StructuredDataNode):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        if not (self.attributes.is_equal(other.attributes) and self.table.is_equal(other.table)):
            return False

        compared_keys = _compare_dict_keys(old_dict=other._nodes, new_dict=self._nodes)
        if compared_keys.only_old or compared_keys.only_new:
            return False

        for key in compared_keys.both:
            if not self._nodes[key].is_equal(other._nodes[key]):
                return False
        return True

    def count_entries(self) -> int:
        return sum(
            [
                self.attributes.count_entries(),
                self.table.count_entries(),
            ]
            + [node.count_entries() for node in self._nodes.values()]
        )

    def merge_with(self, other: object) -> StructuredDataNode:
        if not isinstance(other, StructuredDataNode):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        node = StructuredDataNode(name=self.name, path=self.path)

        node.add_attributes(self.attributes.merge_with(other.attributes))
        node.add_table(self.table.merge_with(other.table))

        compared_keys = _compare_dict_keys(old_dict=other._nodes, new_dict=self._nodes)

        for key in compared_keys.only_old:
            node.add_node(other._nodes[key])

        for key in compared_keys.both:
            node.add_node(self._nodes[key].merge_with(other._nodes[key]))

        for key in compared_keys.only_new:
            node.add_node(self._nodes[key])

        return node

    def remove_retentions(self) -> None:
        self.attributes.remove_retentions()
        self.table.remove_retentions()
        for node in self._nodes.values():
            node.remove_retentions()

    #   ---node methods---------------------------------------------------------

    def setdefault_node(self, path: SDPath) -> StructuredDataNode:
        if not path:
            return self

        name = path[0]
        node = self._nodes.setdefault(name, StructuredDataNode(name=name, path=self.path + (name,)))
        return node.setdefault_node(path[1:])

    def add_node(self, node: StructuredDataNode) -> StructuredDataNode:
        if not node.name:
            raise ValueError("Root cannot be added.")

        path = self.path + (node.name,)
        if node.name in self._nodes:
            the_node = self._nodes[node.name]
            the_node.set_path(path)
        else:
            dflt_node = StructuredDataNode(name=node.name, path=path)
            the_node = self._nodes.setdefault(node.name, dflt_node)

        the_node.add_attributes(node.attributes)
        the_node.add_table(node.table)

        for sub_node in node._nodes.values():
            the_node.add_node(sub_node)

        return the_node

    def add_attributes(self, attributes: Attributes) -> None:
        self.attributes.set_retentions(attributes.retentions)
        self.attributes.add_pairs(attributes.pairs)

    def add_table(self, table: Table) -> None:
        self.table.set_retentions(table.retentions)
        self.table.add_key_columns(table.key_columns)
        for ident, row in table._rows.items():
            self.table.add_row(ident, row)

    def get_node(self, path: SDPath) -> Optional[StructuredDataNode]:
        return self._get_node(path)

    def get_table(self, path: SDPath) -> Optional[Table]:
        node = self._get_node(path)
        return None if node is None else node.table

    def get_attributes(self, path: SDPath) -> Optional[Attributes]:
        node = self._get_node(path)
        return None if node is None else node.attributes

    def _get_node(self, path: SDPath) -> Optional[StructuredDataNode]:
        if not path:
            return self
        node = self._nodes.get(path[0])
        return None if node is None else node._get_node(path[1:])

    #   ---representation-------------------------------------------------------

    def __repr__(self) -> str:
        return "%s(%s)" % (self.__class__.__name__, pprint.pformat(self._format()))

    def _format(self) -> Dict:
        # Only used for repr/debug purposes
        return {
            ATTRIBUTES_KEY: self.attributes._format(),
            TABLE_KEY: self.table._format(),
            _NODES_KEY: {name: node._format() for name, node in self._nodes.items()},
        }

    #   ---de/serializing-------------------------------------------------------

    def serialize(self) -> SDRawTree:
        return {
            ATTRIBUTES_KEY: self.attributes.serialize(),
            TABLE_KEY: self.table.serialize(),
            _NODES_KEY: {name: node.serialize() for name, node in self._nodes.items()},
        }

    @classmethod
    def deserialize(cls, raw_tree: SDRawTree) -> StructuredDataNode:
        if all(key in raw_tree for key in (ATTRIBUTES_KEY, TABLE_KEY, _NODES_KEY)):
            return cls._deserialize(name="", path=tuple(), raw_tree=raw_tree)
        return cls._deserialize_legacy(name="", path=tuple(), raw_tree=raw_tree)

    @classmethod
    def _deserialize(
        cls,
        *,
        name: SDNodeName,
        path: SDNodePath,
        raw_tree: SDRawTree,
    ) -> StructuredDataNode:
        node = cls(name=name, path=path)

        node.add_attributes(Attributes.deserialize(path=path, raw_pairs=raw_tree[ATTRIBUTES_KEY]))
        node.add_table(Table.deserialize(path=path, raw_rows=raw_tree[TABLE_KEY]))

        for raw_name, raw_node in raw_tree[_NODES_KEY].items():
            node.add_node(
                cls._deserialize(
                    name=raw_name,
                    path=path + (raw_name,),
                    raw_tree=raw_node,
                )
            )

        return node

    @classmethod
    def _deserialize_legacy(
        cls,
        *,
        name: SDNodeName,
        path: SDNodePath,
        raw_tree: SDRawTree,
    ) -> StructuredDataNode:
        node = cls(name=name, path=path)
        raw_pairs: SDPairs = {}

        for key, value in raw_tree.items():
            the_path = path + (key,)
            if isinstance(value, dict):
                if not value:
                    continue
                node.add_node(cls._deserialize_legacy(name=key, path=the_path, raw_tree=value))

            elif isinstance(value, list):
                if not value:
                    continue

                inst = node.setdefault_node([key])
                if node._is_table(value):
                    inst.add_table(Table._deserialize_legacy(path=the_path, legacy_rows=value))
                    continue

                for idx, entry in enumerate(value):
                    inst.add_node(
                        cls._deserialize_legacy(
                            name=str(idx),
                            path=the_path + (str(idx),),
                            raw_tree=entry,
                        )
                    )

            else:
                raw_pairs.setdefault(key, value)

        node.add_attributes(Attributes._deserialize_legacy(path=path, legacy_pairs=raw_pairs))
        return node

    @staticmethod
    def _is_table(entries: List) -> bool:
        # Either we get:
        #   [
        #       {"column1": "value 11", "column2": "value 12",...},
        #       {"column1": "value 11", "column2": "value 12",...},
        #       ...
        #   ]
        # Or:
        #   [
        #       {"attr": "attr1", "table": [...], "node": {...}, "idx-node": [...]},
        #       ...
        #   ]
        return all(not isinstance(v, (list, dict)) for row in entries for v in row.values())

    #   ---delta----------------------------------------------------------------

    def compare_with(self, other: object, keep_identical: bool = False) -> SDDeltaResult:
        if not isinstance(other, StructuredDataNode):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        counter: SDDeltaCounter = Counter()
        delta_node = StructuredDataNode(name=self.name, path=self.path)

        # Attributes
        delta_attributes_result = self.attributes.compare_with(other.attributes)
        counter.update(delta_attributes_result.counter)
        delta_node.add_attributes(delta_attributes_result.delta)

        # Table
        delta_table_result = self.table.compare_with(other.table)
        counter.update(delta_table_result.counter)
        delta_node.add_table(delta_table_result.delta)

        # Nodes
        compared_keys = _compare_dict_keys(old_dict=other._nodes, new_dict=self._nodes)

        for key in compared_keys.only_new:
            node = self._nodes[key]
            new_entries = node.count_entries()
            if new_entries:
                counter.update(new=new_entries)
                delta_node.add_node(node.get_encoded_node(encode_as=_new_delta_tree_node))

        for key in compared_keys.both:
            node = self._nodes[key]
            other_node = other._nodes[key]

            if node.is_equal(other_node):
                if keep_identical:
                    delta_node.add_node(node.get_encoded_node(encode_as=_identical_delta_tree_node))
                continue

            delta_node_result = node.compare_with(
                other_node,
                keep_identical=keep_identical,
            )

            if (
                delta_node_result.counter["new"]
                or delta_node_result.counter["changed"]
                or delta_node_result.counter["removed"]
            ):
                counter.update(delta_node_result.counter)
                delta_node.add_node(delta_node_result.delta)

        for key in compared_keys.only_old:
            other_node = other._nodes[key]
            removed_entries = other_node.count_entries()
            if removed_entries:
                counter.update(removed=removed_entries)
                delta_node.add_node(other_node.get_encoded_node(encode_as=_removed_delta_tree_node))

        return SDDeltaResult(counter=counter, delta=delta_node)

    def get_encoded_node(self, encode_as: SDEncodeAs) -> StructuredDataNode:
        delta_node = StructuredDataNode(name=self.name, path=self.path)

        delta_node.add_attributes(self.attributes.get_encoded_attributes(encode_as))
        delta_node.add_table(self.table.get_encoded_table(encode_as))

        for node in self._nodes.values():
            delta_node.add_node(node.get_encoded_node(encode_as))
        return delta_node

    #   ---filtering------------------------------------------------------------

    def get_filtered_node(self, filters: List[SDFilter]) -> StructuredDataNode:
        filtered = StructuredDataNode(name=self.name, path=self.path)

        for f in filters:
            # First check if node exists
            node = self._get_node(f.path)
            if node is None:
                continue

            filtered_node = filtered.setdefault_node(f.path)

            filtered_node.add_attributes(
                node.attributes.get_filtered_attributes(f.filter_attributes)
            )
            filtered_node.add_table(node.table.get_filtered_table(f.filter_columns))

            for name, sub_node in node._nodes.items():
                # From GUI::permitted_paths: We always get a list of strs.
                if f.filter_nodes(str(name)):
                    filtered_node.add_node(sub_node)

        return filtered

    #   ---web------------------------------------------------------------------

    def show(self, renderer):
        # TODO: type hints
        if not self.attributes.is_empty():
            renderer.show_attributes(self.attributes)

        if not self.table.is_empty():
            renderer.show_table(self.table)

        for name in sorted(self._nodes):
            renderer.show_node(self._nodes[name])


# .
#   .--Table---------------------------------------------------------------.
#   |                       _____     _     _                              |
#   |                      |_   _|_ _| |__ | | ___                         |
#   |                        | |/ _` | '_ \| |/ _ \                        |
#   |                        | | (_| | |_) | |  __/                        |
#   |                        |_|\__,_|_.__/|_|\___|                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# TODO Table: {IDENT: Attributes}?

TableRetentions = Dict[SDRowIdent, RetentionIntervalsByKeys]


class Table:
    def __init__(
        self,
        *,
        path: Optional[SDNodePath] = None,
        key_columns: Optional[SDKeyColumns] = None,
        retentions: Optional[TableRetentions] = None,
    ) -> None:
        if path:
            self.path = path
        else:
            self.path = tuple()

        if key_columns:
            self.key_columns = key_columns
        else:
            self.key_columns = []

        if retentions:
            self.retentions = retentions
        else:
            self.retentions = {}

        self._rows: SDRows = {}

    def set_path(self, path: SDNodePath) -> None:
        self.path = path

    def add_key_columns(self, key_columns: SDKeyColumns) -> None:
        if not self.key_columns:
            self.key_columns = key_columns

    @property
    def rows(self) -> List[SDRow]:
        return list(self._rows.values())

    #   ---common methods-------------------------------------------------------

    def is_empty(self) -> bool:
        return not self._rows

    def is_equal(self, other: object) -> bool:
        if not isinstance(other, Table):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        compared_keys = _compare_dict_keys(old_dict=other._rows, new_dict=self._rows)
        if compared_keys.only_old or compared_keys.only_new:
            return False

        for key in compared_keys.both:
            if self._rows[key] != other._rows[key]:
                return False
        return True

    def count_entries(self) -> int:
        return sum(map(len, self._rows.values()))

    def merge_with(self, other: object) -> Table:
        if not isinstance(other, Table):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        if self.key_columns == other.key_columns:
            return self._merge_with(other)
        return self._merge_with_legacy(other)

    def _merge_with(self, other: Table) -> Table:
        table = Table(
            path=self.path,
            key_columns=self.key_columns,
            retentions={
                **self.retentions,
                **other.retentions,
            },
        )

        compared_keys = _compare_dict_keys(old_dict=other._rows, new_dict=self._rows)

        for key in compared_keys.only_old:
            table.add_row(key, other._rows[key])

        for key in compared_keys.both:
            table.add_row(key, {**self._rows[key], **other._rows[key]})

        for key in compared_keys.only_new:
            table.add_row(key, self._rows[key])

        return table

    def _merge_with_legacy(self, other: Table) -> Table:
        table = Table(
            path=self.path,
            key_columns=sorted(set(self.key_columns).intersection(other.key_columns)),
            retentions={
                **self.retentions,
                **other.retentions,
            },
        )

        # Re-calculates row identifiers
        table.add_rows(list(self._rows.values()))
        table.add_rows(list(other._rows.values()))

        return table

    #   ---table methods--------------------------------------------------------

    def add_rows(self, rows: Iterable[SDRow]) -> None:
        for row in rows:
            self.add_row(self._make_row_ident(row), row)

    def _make_row_ident(self, row) -> SDRowIdent:
        return tuple(self._get_row_value(row[k]) for k in self.key_columns if k in row)

    @staticmethod
    def _get_row_value(value: Union[SDValue, Tuple[SDValue, SDValue]]) -> SDValue:
        if isinstance(value, tuple):
            # Delta trees are also de/serialized: for these trees we have to
            # extract the value from (old, new) tuple, see als '_*_delta_tree_node'.
            old, new = value
            return old if new is None else new
        return value

    def add_row(self, ident: SDRowIdent, row: SDRow) -> None:
        if not self.key_columns:
            raise ValueError("Cannot add row due to missing key_columns")

        if not row:
            return

        self._rows.setdefault(ident, {}).update(row)

    def get_row(self, row: SDRow) -> SDRow:
        ident = self._make_row_ident(row)
        if ident in self.retentions:
            return {k: row[k] for k in self.retentions[ident] if k in row}
        return row

    #   ---retentions-----------------------------------------------------------

    def update_from_previous(
        self,
        now: int,
        other: object,
        filter_func: SDFilterFunc,
        inv_intervals: RetentionIntervals,
    ) -> UpdateResult:
        if not isinstance(other, Table):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        # TODO cleanup

        reasons = []
        retentions: TableRetentions = {}

        compared_idents = _compare_dict_keys(old_dict=other._rows, new_dict=self._rows)
        self.add_key_columns(other.key_columns)

        for ident in compared_idents.only_old:
            old_row: SDRow = {}
            for key, value in other._rows[ident].items():
                # If a key is part of the row ident then retention info is not added.
                # These keys are mandatory and added later if non-ident-key-values are found.
                if (
                    key not in other.key_columns
                    and filter_func(key)
                    and (previous_intervals := other.retentions.get(ident, {}).get(key))
                    and now <= previous_intervals.keep_until
                ):
                    retentions.setdefault(ident, {})[key] = previous_intervals
                    old_row.setdefault(key, value)

            if old_row:
                # Update row with ident-key-values.
                old_row.update({k: other._rows[ident][k] for k in other.key_columns})
                self.add_row(ident, old_row)
                reasons.append("added row below %r" % (ident,))

        for ident in compared_idents.both:
            compared_keys = _compare_dict_keys(
                old_dict=other._rows[ident], new_dict=self._rows[ident]
            )

            row: SDRow = {}
            for key in compared_keys.only_old:
                # If a key is part of the row ident then retention info is not added.
                # These keys are mandatory and added later if non-ident-key-values are found.
                if (
                    key not in self.key_columns
                    and filter_func(key)
                    and (previous_intervals := other.retentions.get(ident, {}).get(key))
                    and now <= previous_intervals.keep_until
                ):
                    retentions.setdefault(ident, {})[key] = previous_intervals
                    row.setdefault(key, other._rows[ident][key])

            for key in compared_keys.both.union(compared_keys.only_new):
                if key not in self.key_columns and filter_func(key):
                    retentions.setdefault(ident, {})[key] = inv_intervals

            if row:
                # Update row with ident-key-values.
                row.update(
                    {
                        **{
                            k: other._rows[ident][k]
                            for k in other.key_columns
                            if k in other._rows[ident][k]
                        },
                        **{
                            k: self._rows[ident][k]
                            for k in self.key_columns
                            if k in self._rows[ident][k]
                        },
                    }
                )
                self.add_row(ident, row)
                reasons.append("added row below %r" % (ident,))

        for ident in compared_idents.only_new:
            for key in self._rows[ident]:
                if key not in self.key_columns and filter_func(key):
                    retentions.setdefault(ident, {})[key] = inv_intervals

        if retentions:
            self.set_retentions(retentions)
            reasons.append("retention intervals %r" % retentions)

        return UpdateResult(
            save_tree=bool(reasons),
            reason=", ".join(reasons),
        )

    def set_retentions(self, table_retentions: TableRetentions) -> None:
        self.retentions = table_retentions

    def get_retention_intervals(self, key: SDKey, row: SDRow) -> Optional[RetentionIntervals]:
        return self.retentions.get(self._make_row_ident(row), {}).get(key)

    def remove_retentions(self) -> None:
        self.retentions = {}

    #   ---representation-------------------------------------------------------

    def __repr__(self) -> str:
        return "%s(%s)" % (self.__class__.__name__, pprint.pformat(self._format()))

    def _format(self) -> Dict:
        # Only used for repr/debug purposes
        return {
            _KEY_COLUMNS_KEY: self.key_columns,
            _ROWS_KEY: self._rows,
            _RETENTIONS_KEY: self.retentions,
        }

    #   ---de/serializing-------------------------------------------------------

    def serialize(self) -> SDRawTree:
        raw_table = {}
        if self._rows:
            raw_table.update(
                {
                    _KEY_COLUMNS_KEY: self.key_columns,
                    _ROWS_KEY: list(self._rows.values()),
                }
            )

        if self.retentions:
            raw_table[_RETENTIONS_KEY] = {
                ident: _serialize_retentions(intervals)
                for ident, intervals in self.retentions.items()
            }
        return raw_table

    @classmethod
    def deserialize(cls, *, path: SDNodePath, raw_rows: SDRawTree) -> Table:
        rows = raw_rows.get(_ROWS_KEY, [])
        if _KEY_COLUMNS_KEY in raw_rows:
            key_columns = raw_rows[_KEY_COLUMNS_KEY]
        else:
            key_columns = cls._get_default_key_columns(rows)

        table = cls(
            path=path,
            key_columns=key_columns,
            retentions={
                ident: _deserialize_retentions(raw_intervals)
                for ident, raw_intervals in raw_rows.get(_RETENTIONS_KEY, {}).items()
            },
        )
        table.add_rows(rows)
        return table

    @classmethod
    def _deserialize_legacy(cls, *, path: SDNodePath, legacy_rows: LegacyRows) -> Table:
        table = cls(
            path=path,
            key_columns=cls._get_default_key_columns(legacy_rows),
        )
        table.add_rows(legacy_rows)
        return table

    @staticmethod
    def _get_default_key_columns(rows: List[SDRow]) -> SDKeyColumns:
        return sorted(set(k for r in rows for k in r))

    #   ---delta----------------------------------------------------------------

    def compare_with(self, other: object, keep_identical: bool = False) -> TDeltaResult:
        if not isinstance(other, Table):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        counter: SDDeltaCounter = Counter()
        key_columns = sorted(set(self.key_columns).union(other.key_columns))
        delta_table = Table(path=self.path, key_columns=key_columns, retentions=self.retentions)

        compared_keys = _compare_dict_keys(old_dict=other._rows, new_dict=self._rows)
        for key in compared_keys.only_old:
            removed_row = {k: _removed_delta_tree_node(v) for k, v in other._rows[key].items()}
            counter.update(removed=len(removed_row))
            delta_table.add_row(key, removed_row)

        for key in compared_keys.both:
            delta_dict_result = _compare_dicts(
                old_dict=other._rows[key],
                new_dict=self._rows[key],
                keep_identical=keep_identical,
            )
            counter.update(delta_dict_result.counter)
            delta_table.add_row(key, delta_dict_result.delta)

        for key in compared_keys.only_new:
            new_row = {k: _new_delta_tree_node(v) for k, v in self._rows[key].items()}
            counter.update(new=len(new_row))
            delta_table.add_row(key, new_row)

        return TDeltaResult(counter=counter, delta=delta_table)

    def get_encoded_table(self, encode_as: SDEncodeAs) -> Table:
        table = Table(path=self.path, key_columns=self.key_columns, retentions=self.retentions)
        for ident, row in self._rows.items():
            table.add_row(ident, {k: encode_as(v) for k, v in row.items()})
        return table

    #   ---filtering------------------------------------------------------------

    def get_filtered_table(self, filter_func: SDFilterFunc) -> Table:
        table = Table(path=self.path, key_columns=self.key_columns, retentions=self.retentions)
        for ident, row in self._rows.items():
            table.add_row(ident, _get_filtered_dict(row, filter_func))
        return table

    #   ---web------------------------------------------------------------------

    def show(self, renderer):
        # TODO: type hints
        renderer.show_table(self)


# .
#   .--Attributes----------------------------------------------------------.
#   |              _   _   _        _ _           _                        |
#   |             / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___             |
#   |            / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|            |
#   |           / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \            |
#   |          /_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Attributes:
    def __init__(
        self,
        *,
        path: Optional[SDNodePath] = None,
        retentions: Optional[RetentionIntervalsByKeys] = None,
    ) -> None:
        if path:
            self.path = path
        else:
            self.path = tuple()

        if retentions:
            self.retentions = retentions
        else:
            self.retentions = {}

        self.pairs: SDPairs = {}

    def set_path(self, path: SDNodePath) -> None:
        self.path = path

    #   ---common methods-------------------------------------------------------

    def is_empty(self) -> bool:
        return self.pairs == {}

    def is_equal(self, other: object) -> bool:
        if not isinstance(other, Attributes):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        return self.pairs == other.pairs

    def count_entries(self) -> int:
        return len(self.pairs)

    def merge_with(self, other: object) -> Attributes:
        if not isinstance(other, Attributes):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        attributes = Attributes(
            path=self.path,
            retentions={
                **self.retentions,
                **other.retentions,
            },
        )
        attributes.add_pairs(self.pairs)
        attributes.add_pairs(other.pairs)

        return attributes

    #   ---attributes methods---------------------------------------------------

    def add_pairs(self, pairs: Union[SDPairs, SDPairsFromPlugins]) -> None:
        self.pairs.update(pairs)

    #   ---retentions-----------------------------------------------------------

    def update_from_previous(
        self,
        now: int,
        other: object,
        filter_func: SDFilterFunc,
        inv_intervals: RetentionIntervals,
    ) -> UpdateResult:
        if not isinstance(other, Attributes):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        reasons = []
        retentions: RetentionIntervalsByKeys = {}
        compared_keys = _compare_dict_keys(old_dict=other.pairs, new_dict=self.pairs)

        pairs: SDPairs = {}
        for key in compared_keys.only_old:
            if (
                filter_func(key)
                and (previous_intervals := other.retentions.get(key))
                and now <= previous_intervals.keep_until
            ):
                retentions[key] = previous_intervals
                pairs.setdefault(key, other.pairs[key])

        for key in compared_keys.both.union(compared_keys.only_new):
            if filter_func(key):
                retentions[key] = inv_intervals

        if pairs:
            self.add_pairs(pairs)
            reasons.append("added pairs")

        if retentions:
            self.set_retentions(retentions)
            reasons.append("retention intervals %r" % retentions)

        return UpdateResult(
            save_tree=bool(reasons),
            reason=", ".join(reasons),
        )

    def set_retentions(self, intervals_by_keys: RetentionIntervalsByKeys) -> None:
        self.retentions = intervals_by_keys

    def get_retention_intervals(self, key: SDKey) -> Optional[RetentionIntervals]:
        return self.retentions.get(key)

    def remove_retentions(self) -> None:
        self.retentions = {}

    #   ---representation-------------------------------------------------------

    def __repr__(self) -> str:
        return "%s(%s)" % (self.__class__.__name__, pprint.pformat(self._format()))

    def _format(self) -> Dict:
        # Only used for repr/debug purposes
        return {
            _PAIRS_KEY: self.pairs,
            _RETENTIONS_KEY: self.retentions,
        }

    #   ---de/serializing-------------------------------------------------------

    def serialize(self) -> SDRawTree:
        raw_attributes = {}
        if self.pairs:
            raw_attributes[_PAIRS_KEY] = self.pairs

        if self.retentions:
            raw_attributes[_RETENTIONS_KEY] = _serialize_retentions(self.retentions)
        return raw_attributes

    @classmethod
    def deserialize(cls, *, path: SDNodePath, raw_pairs: SDRawTree) -> Attributes:
        attributes = cls(
            path=path,
            retentions=_deserialize_retentions(raw_pairs.get(_RETENTIONS_KEY)),
        )
        attributes.add_pairs(raw_pairs.get(_PAIRS_KEY, {}))
        return attributes

    @classmethod
    def _deserialize_legacy(cls, *, path: SDNodePath, legacy_pairs: LegacyPairs) -> Attributes:
        attributes = cls(path=path)
        attributes.add_pairs(legacy_pairs)
        return attributes

    #   ---delta----------------------------------------------------------------

    def compare_with(self, other: object, keep_identical: bool = False) -> ADeltaResult:
        if not isinstance(other, Attributes):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        delta_dict_result = _compare_dicts(
            old_dict=other.pairs,
            new_dict=self.pairs,
            keep_identical=keep_identical,
        )

        delta_attributes = Attributes(path=self.path, retentions=self.retentions)
        delta_attributes.add_pairs(delta_dict_result.delta)

        return ADeltaResult(
            counter=delta_dict_result.counter,
            delta=delta_attributes,
        )

    def get_encoded_attributes(self, encode_as: SDEncodeAs) -> Attributes:
        attributes = Attributes(path=self.path, retentions=self.retentions)
        attributes.add_pairs({k: encode_as(v) for k, v in self.pairs.items()})
        return attributes

    #   ---filtering------------------------------------------------------------

    def get_filtered_attributes(self, filter_func: SDFilterFunc) -> Attributes:
        attributes = Attributes(path=self.path, retentions=self.retentions)
        attributes.add_pairs(_get_filtered_dict(self.pairs, filter_func))
        return attributes

    #   ---web------------------------------------------------------------------

    def show(self, renderer):
        # TODO: type hints
        renderer.show_attributes(self)


# .
#   .--helpers-------------------------------------------------------------.
#   |                  _          _                                        |
#   |                 | |__   ___| |_ __   ___ _ __ ___                    |
#   |                 | '_ \ / _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 | | | |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


def _compare_dicts(*, old_dict: Dict, new_dict: Dict, keep_identical: bool) -> DDeltaResult:
    """
    Format of compared entries:
      new:          {k: (None, new_value), ...}
      changed:      {k: (old_value, new_value), ...}
      removed:      {k: (old_value, None), ...}
      identical:    {k: (value, value), ...}
    """
    compared_keys = _compare_dict_keys(old_dict=old_dict, new_dict=new_dict)

    identical: Dict = {}
    changed: Dict = {}
    for k in compared_keys.both:
        new_value = new_dict[k]
        old_value = old_dict[k]
        if new_value == old_value:
            identical.setdefault(k, _identical_delta_tree_node(old_value))
        else:
            changed.setdefault(k, _changed_delta_tree_node(old_value, new_value))

    new = {k: _new_delta_tree_node(new_dict[k]) for k in compared_keys.only_new}
    removed = {k: _removed_delta_tree_node(old_dict[k]) for k in compared_keys.only_old}

    delta_dict: Dict = {}
    delta_dict.update(new)
    delta_dict.update(changed)
    delta_dict.update(removed)
    if keep_identical:
        delta_dict.update(identical)

    # We have to help mypy a little bit to figure out the Literal.
    cnt: Mapping[Literal["new", "changed", "removed"], int] = {
        "new": len(new),
        "changed": len(changed),
        "removed": len(removed),
    }
    return DDeltaResult(counter=Counter(cnt), delta=delta_dict)


class ComparedDictKeys(NamedTuple):
    only_old: Set
    both: Set
    only_new: Set


def _compare_dict_keys(*, old_dict: Dict, new_dict: Dict) -> ComparedDictKeys:
    """
    Returns the set relationships of the keys between two dictionaries:
    - relative complement of new_dict in old_dict
    - intersection of both
    - relative complement of old_dict in new_dict
    """
    old_keys, new_keys = set(old_dict), set(new_dict)
    return ComparedDictKeys(
        only_old=old_keys - new_keys,
        both=old_keys.intersection(new_keys),
        only_new=new_keys - old_keys,
    )


def _get_filtered_dict(dict_: Dict, filter_func: SDFilterFunc) -> Dict:
    return {k: v for k, v in dict_.items() if filter_func(k)}


def _new_delta_tree_node(value: SDValue) -> Tuple[None, SDValue]:
    return (None, value)


def _removed_delta_tree_node(value: SDValue) -> Tuple[SDValue, None]:
    return (value, None)


def _changed_delta_tree_node(old_value: SDValue, new_value: SDValue) -> Tuple[SDValue, SDValue]:
    return (old_value, new_value)


def _identical_delta_tree_node(value: SDValue) -> Tuple[SDValue, SDValue]:
    return (value, value)


def parse_visible_raw_path(raw_path: SDRawPath) -> SDPath:
    return [part for part in raw_path.split(".") if part]


def _serialize_retentions(
    intervals_by_keys: RetentionIntervalsByKeys,
) -> RawRetentionIntervalsByKeys:
    return {key: intervals.serialize() for key, intervals in intervals_by_keys.items()}


def _deserialize_retentions(
    raw_intervals_by_keys: Optional[RawRetentionIntervalsByKeys],
) -> RetentionIntervalsByKeys:
    if not raw_intervals_by_keys:
        return {}
    return {
        key: RetentionIntervals.deserialize(intervals)
        for key, intervals in raw_intervals_by_keys.items()
    }
