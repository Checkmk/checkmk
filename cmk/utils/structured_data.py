#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This module handles tree structures for HW/SW inventory system and
structured monitoring data of Check_MK.
"""

import io
import gzip
import re
import pprint
from typing import (
    Dict,
    List,
    Optional,
    Any,
    Union,
    Tuple,
    Set,
    Callable,
    NamedTuple,
    Literal,
    Counter as TCounter,
)
from pathlib import Path
from collections import Counter

from cmk.utils import store
from cmk.utils.exceptions import MKGeneralException

# TODO
# - Cleanup path in utils, base, gui, find ONE place (type defs or similar)
# - rename Numeration -> Table

SDRawPath = str
SDRawTree = Dict

SDKey = str
SDKeys = List[SDKey]
# SDValue needs only to support __eq__
SDValue = Any

SDAttributes = Dict[SDKey, SDValue]

#SDTableRowIdent = str
#SDTable = Dict[SDTableRowIdent, SDAttributes]
SDTable = List[SDAttributes]

# TODO Cleanup int: May be an indexed node
SDNodeName = Union[str, int]
SDPath = List[SDNodeName]

SDNodePath = Tuple[SDNodeName, ...]
SDNodes = Dict[SDNodeName, "StructuredDataNode"]

SDEncodeAs = Callable

SDDeltaCounter = TCounter[Literal["new", "changed", "removed"]]


class SDDeltaResult(NamedTuple):
    counter: SDDeltaCounter
    delta: "StructuredDataNode"


class NDeltaResult(NamedTuple):
    counter: SDDeltaCounter
    delta: "Numeration"


class TDeltaResult(NamedTuple):
    counter: SDDeltaCounter
    delta: SDTable


class ADeltaResult(NamedTuple):
    counter: SDDeltaCounter
    delta: "Attributes"


class DDeltaResult(NamedTuple):
    counter: SDDeltaCounter
    delta: SDAttributes


AllowedPaths = List[Tuple[SDPath, Optional[List[str]]]]


def save_tree_to(
    tree: "StructuredDataNode",
    path: str,
    filename: str,
    pretty: bool = False,
) -> None:
    filepath = "%s/%s" % (path, filename)
    output = tree.get_raw_tree()
    store.save_object_to_file(filepath, output, pretty=pretty)

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        f.write((repr(output) + "\n").encode("utf-8"))
    store.save_bytes_to_file(filepath + ".gz", buf.getvalue())

    # Inform Livestatus about the latest inventory update
    store.save_text_to_file("%s/.last" % path, u"")


def load_tree_from(filepath: Union[Path, str]) -> "StructuredDataNode":
    raw_tree = store.load_object_from_file(filepath)
    if raw_tree:
        return StructuredDataNode().create_tree_from_raw_tree(raw_tree)
    return StructuredDataNode()


#   .--Structured DataNode-------------------------------------------------.
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
    def __init__(self) -> None:
        self.path: SDNodePath = tuple()
        self.attributes = Attributes()
        self.table = Numeration()
        self._nodes: SDNodes = {}

    def __repr__(self) -> str:
        return "%s(%s)" % (self.__class__.__name__, pprint.pformat(self.get_raw_tree()))

    #   ---building tree from plugins-------------------------------------------

    def get_dict(self, tree_path: Optional[SDRawPath]) -> SDAttributes:
        return self.setdefault_node(_parse_tree_path(tree_path)).attributes.data

    def get_list(self, tree_path: Optional[SDRawPath]) -> SDTable:
        return self.setdefault_node(_parse_tree_path(tree_path)).table.data

    def set_path(self, path: SDNodePath) -> None:
        self.path = path
        self.attributes.set_path(path)
        self.table.set_path(path)

    def is_empty(self) -> bool:
        if not (self.attributes.is_empty() and self.table.is_empty()):
            return False

        for node in self._nodes.values():
            if not node.is_empty():
                return False
        return True

    def is_equal(self, other: object, edges: Optional[SDPath] = None) -> bool:
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
        return sum([
            self.attributes.count_entries(),
            self.table.count_entries(),
        ] + [node.count_entries() for node in self._nodes.values()])

    def compare_with(self, other: object, keep_identical: bool = False) -> SDDeltaResult:
        if not isinstance(other, StructuredDataNode):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        counter: SDDeltaCounter = Counter()
        delta_node = StructuredDataNode()

        # Attributes
        delta_attributes_result = self.attributes.compare_with(other.attributes)
        counter.update(delta_attributes_result.counter)
        delta_node.add_attributes(delta_attributes_result.delta.data)

        # Table
        delta_table_result = self.table.compare_with(other.table)
        counter.update(delta_table_result.counter)
        delta_node.add_table(delta_table_result.delta.data)

        # Nodes
        compared_keys = _compare_dict_keys(old_dict=other._nodes, new_dict=self._nodes)

        for key in compared_keys.only_new:
            node = self._nodes[key]
            new_entries = node.count_entries()
            if new_entries:
                counter.update(new=new_entries)
                delta_node.add_node(
                    key,
                    node.encode_for_delta_tree(encode_as=_new_delta_tree_node),
                )

        for key in compared_keys.both:
            node = self._nodes[key]
            other_node = other._nodes[key]

            if node.is_equal(other_node):
                if keep_identical:
                    delta_node.add_node(
                        key,
                        node.encode_for_delta_tree(encode_as=_identical_delta_tree_node),
                    )
                continue

            delta_node_result = node.compare_with(
                other_node,
                keep_identical=keep_identical,
            )

            if (delta_node_result.counter['new'] or delta_node_result.counter['changed'] or
                    delta_node_result.counter['removed']):
                counter.update(delta_node_result.counter)
                delta_node.add_node(key, delta_node_result.delta)

        for key in compared_keys.only_old:
            other_node = other._nodes[key]
            removed_entries = other_node.count_entries()
            if removed_entries:
                counter.update(removed=removed_entries)
                delta_node.add_node(
                    key,
                    other_node.encode_for_delta_tree(encode_as=_removed_delta_tree_node),
                )

        return SDDeltaResult(counter=counter, delta=delta_node)

    def encode_for_delta_tree(self, encode_as: SDEncodeAs) -> "StructuredDataNode":
        delta_node = StructuredDataNode()

        delta_node.add_attributes(self.attributes.encode_for_delta_tree(encode_as).data)
        delta_node.add_table(self.table.encode_for_delta_tree(encode_as).data)

        for edge, node in self._nodes.items():
            delta_node.add_node(edge, node.encode_for_delta_tree(encode_as))
        return delta_node

    # Deserializing

    def create_tree_from_raw_tree(self, raw_tree: SDRawTree) -> "StructuredDataNode":
        raw_attributes: SDAttributes = {}
        for key, value in raw_tree.items():
            if isinstance(value, dict):
                self.setdefault_node([key]).create_tree_from_raw_tree(value)
                continue

            if isinstance(value, list):
                if self._is_numeration(value):
                    self.setdefault_node([key]).add_table(value)
                else:
                    self._add_indexed_nodes(key, value)
                continue

            raw_attributes.setdefault(key, value)
        self.add_attributes(raw_attributes)
        return self

    def _is_numeration(self, entries: List) -> bool:
        for entry in entries:
            # Skipping invalid entries such as
            # {u'KEY': [LIST OF STRINGS], ...}
            try:
                for v in entry.values():
                    if isinstance(v, list):
                        return False
            except AttributeError:
                return False
        return True

    def _add_indexed_nodes(self, key, value):
        for idx, entry in enumerate(value):
            idx_attributes: SDAttributes = {}
            node = self.setdefault_node([key, idx])
            for idx_key, idx_entry in entry.items():
                if isinstance(idx_entry, list):
                    node.setdefault_node([idx_key]).add_table(idx_entry)
                else:
                    idx_attributes.setdefault(idx_key, idx_entry)
            node.add_attributes(idx_attributes)

    def normalize_nodes(self):
        """
        After the execution of plugins there may remain empty
        nodes which will be removed within this method.
        Moreover we have to deal with nested numerations, eg.
        at paths like "hardware.memory.arrays:*.devices:" where
        we obtain: 'memory': {'arrays': [{'devices': [...]}, {}, ... ]}.
        In this case we have to convert this
        'list-composed-of-dicts-containing-lists' structure into
        numerated nodes ('arrays') containing real numerations ('devices').
        """
        remove_table = False
        for idx, entry in enumerate(self.table.data):
            for k, v in entry.items():
                if isinstance(v, list):
                    self.setdefault_node([idx, k]).add_table(v)
                    remove_table = True

        if remove_table:
            self.table = Numeration()
            self.table.set_path(self.path)

        for node in self._nodes.values():
            node.normalize_nodes()

    # Serializing

    def get_raw_tree(self) -> Union[Dict, List]:
        if self._has_indexed_nodes():
            return [self._nodes[k].get_raw_tree() for k in sorted(self._nodes)]

        if not self.table.is_empty():
            return self.table.get_raw_tree()

        tree: Dict = {}
        tree.update(self.attributes.get_raw_tree())

        for edge, node in self._nodes.items():
            node_raw_tree = node.get_raw_tree()
            if isinstance(node_raw_tree, list):
                tree.setdefault(edge, node_raw_tree)
                continue

            tree.setdefault(edge, {}).update(node_raw_tree)
        return tree

    def _has_indexed_nodes(self) -> bool:
        for key in self._nodes:
            if isinstance(key, int):
                return True
        return False

    def merge_with(self, other: object) -> None:
        if not isinstance(other, StructuredDataNode):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        self.attributes.merge_with(other.attributes)
        self.table.merge_with(other.table)

        compared_keys = _compare_dict_keys(old_dict=other._nodes, new_dict=self._nodes)

        for key in compared_keys.both:
            self._nodes[key].merge_with(other._nodes[key])

        for key in compared_keys.only_old:
            self.add_node(key, other._nodes[key])

    def copy(self) -> "StructuredDataNode":
        new_node = StructuredDataNode()

        new_node.add_attributes(self.attributes.data)
        new_node.add_table(self.table.data)

        for edge, node in self._nodes.items():
            new_node.add_node(edge, node.copy())
        return new_node

    #   ---container methods----------------------------------------------------

    def setdefault_node(self, path: SDPath) -> "StructuredDataNode":
        if not path:
            return self
        edge = path[0]
        node = self._nodes.setdefault(edge, StructuredDataNode())
        node.set_path(self.path + (edge,))
        return node.setdefault_node(path[1:])

    def add_node(self, edge: SDNodeName, node: "StructuredDataNode") -> "StructuredDataNode":
        the_node = self._nodes.setdefault(edge, StructuredDataNode())
        the_node.set_path(self.path + (edge,))
        the_node.merge_with(node)
        return the_node

    def add_attributes(self, attributes: SDAttributes) -> None:
        self.attributes.add_attributes(attributes)

    def add_table(self, table: SDTable) -> None:
        self.table.add_table(table)

    def has_edge(self, edge: SDNodeName) -> bool:
        return bool(self._nodes.get(edge))

    def get_filtered_node(
        self,
        allowed_paths: Optional[AllowedPaths],
    ) -> "StructuredDataNode":
        if allowed_paths is None:
            return self

        filtered = StructuredDataNode()
        for path, keys in allowed_paths:
            # First check if node exists
            node = self._get_node(path)
            if node is None:
                continue

            filtered_node = filtered.setdefault_node(path)
            filtered_node.add_attributes(
                (node.attributes.get_filtered_data(keys) if keys else node.attributes.data))
            filtered_node.add_table(node.table.get_filtered_data(keys) if keys else node.table.data)

        return filtered

    #   ---getting [sub] nodes/node attributes----------------------------------

    def get_sub_container(self, path: SDPath) -> Optional["StructuredDataNode"]:
        return self._get_node(path)

    def get_sub_numeration(self, path: SDPath) -> Optional["Numeration"]:
        node = self._get_node(path)
        return None if node is None else node.table

    def get_sub_attributes(self, path: SDPath) -> Optional["Attributes"]:
        node = self._get_node(path)
        return None if node is None else node.attributes

    def _get_node(self, path: SDPath) -> Optional["StructuredDataNode"]:
        if not path:
            return self
        node = self._nodes.get(path[0])
        return None if node is None else node._get_node(path[1:])

    #   ---web------------------------------------------------------------------

    def show(self, renderer):
        # TODO
        if not self.attributes.is_empty():
            renderer.show_attributes(self.attributes)

        if not self.table.is_empty():
            renderer.show_numeration(self.table)

        for edge in sorted(self._nodes):
            renderer.show_container(self._nodes[edge])


#.
#   .--Numeration----------------------------------------------------------.
#   |       _   _                                _   _                     |
#   |      | \ | |_   _ _ __ ___   ___ _ __ __ _| |_(_) ___  _ __          |
#   |      |  \| | | | | '_ ` _ \ / _ \ '__/ _` | __| |/ _ \| '_ \         |
#   |      | |\  | |_| | | | | | |  __/ | | (_| | |_| | (_) | | | |        |
#   |      |_| \_|\__,_|_| |_| |_|\___|_|  \__,_|\__|_|\___/|_| |_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Numeration:
    def __init__(self) -> None:
        self.path: SDNodePath = tuple()
        self.data: SDTable = []

    def set_path(self, path: SDNodePath) -> None:
        self.path = path

    def is_empty(self) -> bool:
        return self.data == []

    def is_equal(self, other: object, edges: Optional[SDPath] = None) -> bool:
        if not isinstance(other, Numeration):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        for row in self.data:
            if row not in other.data:
                return False
        for row in other.data:
            if row not in self.data:
                return False
        return True

    def count_entries(self) -> int:
        return sum(map(len, self.data))

    def compare_with(self, other: object, keep_identical: bool = False) -> NDeltaResult:
        if not isinstance(other, Numeration):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        counter: SDDeltaCounter = Counter()
        delta_table = Numeration()

        remaining_own_rows, remaining_other_rows, identical_rows = self._get_categorized_rows(other)
        new_rows: List = []
        removed_rows: List = []

        if not remaining_other_rows and remaining_own_rows:
            new_rows.extend(remaining_own_rows)

        elif remaining_other_rows and not remaining_own_rows:
            removed_rows.extend(remaining_other_rows)

        elif remaining_other_rows and remaining_own_rows:
            if len(remaining_other_rows) == len(remaining_own_rows):
                delta_rows_result = self._compare_remaining_rows_with_same_length(
                    remaining_own_rows,
                    remaining_other_rows,
                    keep_identical=keep_identical,
                )
                counter.update(delta_rows_result.counter)
                delta_table.add_table(delta_rows_result.delta)
            else:
                new_rows.extend(remaining_own_rows)
                removed_rows.extend(remaining_other_rows)

        delta_table.add_table(
            [{k: _new_delta_tree_node(v) for k, v in row.items()} for row in new_rows])
        delta_table.add_table(
            [{k: _removed_delta_tree_node(v) for k, v in row.items()} for row in removed_rows])

        if keep_identical:
            delta_table.add_table([
                {k: _identical_delta_tree_node(v) for k, v in row.items()} for row in identical_rows
            ])

        counter.update(new=len(new_rows), removed=len(removed_rows))
        return NDeltaResult(counter=counter, delta=delta_table)

    def _get_categorized_rows(self, other: "Numeration") -> Tuple[SDTable, SDTable, SDTable]:
        identical_rows = []
        remaining_other_rows = []
        remaining_new_rows = []
        for row in other.data:
            if row in self.data:
                if row not in identical_rows:
                    identical_rows.append(row)
            else:
                remaining_other_rows.append(row)
        for row in self.data:
            if row in other.data:
                if row not in identical_rows:
                    identical_rows.append(row)
            else:
                remaining_new_rows.append(row)
        return remaining_new_rows, remaining_other_rows, identical_rows

    def _compare_remaining_rows_with_same_length(
        self,
        own_rows: SDTable,
        other_rows: SDTable,
        keep_identical: bool = False,
    ) -> TDeltaResult:
        # In this case we assume that each entry corresponds to the
        # other one with the same index.
        counter: SDDeltaCounter = Counter()
        compared_rows = []
        for own_row, other_row in zip(own_rows, other_rows):
            delta_dict_result = _compare_dicts(
                old_dict=other_row,
                new_dict=own_row,
                keep_identical=keep_identical,
            )

            counter.update(delta_dict_result.counter)
            if delta_dict_result.delta:
                compared_rows.append(delta_dict_result.delta)
        return TDeltaResult(counter=counter, delta=compared_rows)

    def encode_for_delta_tree(self, encode_as: SDEncodeAs) -> "Numeration":
        delta_table = Numeration()
        for entry in self.data:
            delta_table.data.append({k: encode_as(v) for k, v in entry.items()})
        return delta_table

    def get_raw_tree(self) -> SDTable:
        return self.data

    def merge_with(self, other: object) -> None:
        if not isinstance(other, Numeration):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        other_keys = other._get_numeration_keys()
        my_keys = self._get_numeration_keys()
        intersect_keys = my_keys.intersection(other_keys)

        # In case there is no intersection, append all other rows without
        # merging with own rows
        if not intersect_keys:
            self.add_table(other.data)
            return

        # Try to match rows of both trees based on the keys that are found in
        # both. Matching rows are updated. Others are appended.
        other_num = {other._prepare_key(entry, intersect_keys): entry for entry in other.data}

        for entry in self.data:
            key = self._prepare_key(entry, intersect_keys)
            if key in other_num:
                entry.update(other_num[key])
                del other_num[key]

        self.add_table(list(other_num.values()))

    def _get_numeration_keys(self) -> Set[SDKey]:
        return {key for row in self.data for key in row}

    def _prepare_key(self, entry: Dict, keys: Set[SDKey]) -> Tuple[SDKey, ...]:
        return tuple(entry[key] for key in sorted(keys) if key in entry)

    def copy(self) -> "Numeration":
        new = Numeration()
        new.add_table(self.data)
        return new

    #   ---leaf methods---------------------------------------------------------

    def add_table(self, table: SDTable) -> None:
        self.data.extend(table)

    def get_filtered_data(self, keys: SDKeys) -> SDTable:
        return [
            filtered_row for row in self.data if (filtered_row := _get_filtered_dict(row, keys))
        ]

    #   ---web------------------------------------------------------------------

    def show(self, renderer):
        # TODO
        renderer.show_numeration(self)


#.
#   .--Attributes----------------------------------------------------------.
#   |              _   _   _        _ _           _                        |
#   |             / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___             |
#   |            / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|            |
#   |           / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \            |
#   |          /_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Attributes:
    def __init__(self) -> None:
        self.path: SDNodePath = tuple()
        self.data: SDAttributes = {}

    def set_path(self, path: SDNodePath) -> None:
        self.path = path

    def is_empty(self) -> bool:
        return self.data == {}

    def is_equal(self, other: object, edges: Optional[SDPath] = None) -> bool:
        if not isinstance(other, Attributes):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        return self.data == other.data

    def count_entries(self) -> int:
        return len(self.data)

    def compare_with(self, other: object, keep_identical: bool = False) -> ADeltaResult:
        if not isinstance(other, Attributes):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        delta_dict_result = _compare_dicts(
            old_dict=other.data,
            new_dict=self.data,
            keep_identical=keep_identical,
        )

        delta_attributes = Attributes()
        delta_attributes.add_attributes(delta_dict_result.delta)

        return ADeltaResult(
            counter=delta_dict_result.counter,
            delta=delta_attributes,
        )

    def encode_for_delta_tree(self, encode_as: SDEncodeAs) -> "Attributes":
        delta_attributes = Attributes()
        delta_attributes.add_attributes({k: encode_as(v) for k, v in self.data.items()})
        return delta_attributes

    def get_raw_tree(self) -> SDAttributes:
        return self.data

    def merge_with(self, other: object) -> None:
        if not isinstance(other, Attributes):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        self.add_attributes(other.data)

    def copy(self) -> "Attributes":
        new = Attributes()
        new.add_attributes(self.data)
        return new

    #   ---leaf methods---------------------------------------------------------

    def add_attributes(self, attributes: SDAttributes) -> None:
        self.data.update(attributes)

    def get_filtered_data(self, keys: SDKeys) -> SDAttributes:
        return _get_filtered_dict(self.data, keys)

    #   ---web------------------------------------------------------------------

    def show(self, renderer):
        # TODO
        renderer.show_attributes(self)


#.
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

    return DDeltaResult(
        counter=Counter(new=len(new), changed=len(changed), removed=len(removed)),
        delta=delta_dict,
    )


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


def _get_filtered_dict(entries: Dict, keys: SDKeys) -> Dict:
    filtered: Dict = {}
    for k, v in entries.items():
        if k in keys:
            filtered.setdefault(k, v)
    return filtered


def _new_delta_tree_node(value: SDValue) -> Tuple[None, SDValue]:
    return (None, value)


def _removed_delta_tree_node(value: SDValue) -> Tuple[SDValue, None]:
    return (value, None)


def _changed_delta_tree_node(old_value: SDValue, new_value: SDValue) -> Tuple[SDValue, SDValue]:
    return (old_value, new_value)


def _identical_delta_tree_node(value: SDValue) -> Tuple[SDValue, SDValue]:
    return (value, value)


def _parse_tree_path(tree_path: Optional[SDRawPath]) -> SDPath:
    if not tree_path:
        raise MKGeneralException("Empty tree path or zero.")

    if not isinstance(tree_path, str):
        raise MKGeneralException("Wrong tree path format. Must be of type string.")

    if not tree_path.endswith((":", ".")):
        raise MKGeneralException("No valid tree path.")

    if bool(re.compile('[^a-zA-Z0-9_.:-]').search(tree_path)):
        raise MKGeneralException("Specified tree path contains unexpected characters.")

    if tree_path.startswith("."):
        tree_path = tree_path[1:]

    if tree_path.endswith(":") or tree_path.endswith("."):
        tree_path = tree_path[:-1]

    # TODO merge with cmk.gui.inventory::_parse_visible_raw_inventory_path
    parsed_path: SDPath = []
    for part in tree_path.split("."):
        if not part:
            continue
        try:
            parsed_path.append(int(part))
        except ValueError:
            parsed_path.append(part)
    return parsed_path
