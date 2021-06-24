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
from typing import Dict, List, Optional, Any, Union, Tuple, Set, Callable, overload
from pathlib import Path

import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException

# TODO
# - Cleanup path in utils, base, gui, find ONE place (type defs or similar)
# - remove intermediate class Node
# - rename Numeration -> Table
# - rename Container -> Node
# - merge Container (resp. Node) and StructuredDataTree

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
SDNodes = Dict[SDNodeName, "Node"]

SDChild = Union["Container", "Numeration", "Attributes"]

SDNodeChildren = Set[SDChild]
SDCompNodeChildren = Set[Tuple[SDChild, SDChild]]

SDChildren = Set[Tuple[SDNodeName, SDChild]]
SDCompChildren = Set[Tuple[SDNodeName, SDChild, SDChild]]

SDEncodeAs = Callable

SDDeltaResult = Tuple[int, int, int, "StructuredDataTree"]
CDeltaResult = Tuple[int, int, int, "Container"]
NDeltaResult = Tuple[int, int, int, "Numeration"]
ADeltaResult = Tuple[int, int, int, "Attributes"]

#     ____            ____
#    /    \          /    \     max. 1 per type
#    | SD | -------> | NA | ------------------------.
#    \____/          \____/                         |
#                      |                            |
#    CLIENT            |                            |
#                  ____|____                        |
#                 /    |    \                       |
#              ___    ___    ___             ___    |
#             /   \  /   \  /   \   PATH  * /   \   |
#             | A |  | E |  | C | --------- | N | --'
#             \___/  \___/  \___/           \___/
#
#             N:    Node:           ()
#             C:    Container       (parent)
#             A:    Attributes      (leaf)
#             E:    Numeration      (leaf)

#   .--StructuredDataTree--------------------------------------------------.
#   |         ____  _                   _                      _           |
#   |        / ___|| |_ _ __ _   _  ___| |_ _   _ _ __ ___  __| |          |
#   |        \___ \| __| '__| | | |/ __| __| | | | '__/ _ \/ _` |          |
#   |         ___) | |_| |  | |_| | (__| |_| |_| | | |  __/ (_| |          |
#   |        |____/ \__|_|   \__,_|\___|\__|\__,_|_|  \___|\__,_|          |
#   |                                                                      |
#   |               ____        _       _____                              |
#   |              |  _ \  __ _| |_ __ |_   _| __ ___  ___                 |
#   |              | | | |/ _` | __/ _` || || '__/ _ \/ _ \                |
#   |              | |_| | (_| | || (_| || || | |  __/  __/                |
#   |              |____/ \__,_|\__\__,_||_||_|  \___|\___|                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class StructuredDataTree:
    """Interface for structured data tree"""
    def __init__(self) -> None:
        self._root = Container()

    #   ---building tree from plugins-------------------------------------------

    def get_dict(self, tree_path: Optional[SDRawPath]) -> SDAttributes:
        obj = self._get_object(tree_path, Attributes())
        # TODO parse instead of validate
        assert isinstance(obj, dict)
        return obj

    def get_list(self, tree_path: Optional[SDRawPath]) -> SDTable:
        obj = self._get_object(tree_path, Numeration())
        # TODO parse instead of validate
        assert isinstance(obj, list)
        return obj

    @overload
    def _get_object(self, tree_path: Optional[SDRawPath], child: "Numeration") -> SDTable:
        ...

    @overload
    def _get_object(self, tree_path: Optional[SDRawPath], child: "Attributes") -> SDAttributes:
        ...

    def _get_object(
        self,
        tree_path: Optional[SDRawPath],
        child: Union["Attributes", "Numeration"],
    ) -> Union[SDAttributes, SDTable]:
        path = self._parse_tree_path(tree_path)
        parent = self._root._create_hierarchy(path[:-1])
        return parent.add_child(path[-1], child).get_child_data()

    def _parse_tree_path(self, tree_path: Optional[SDRawPath]) -> SDPath:
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

    #   ---loading and saving tree----------------------------------------------

    def save_to(self, path: str, filename: str, pretty: bool = False) -> None:
        filepath = "%s/%s" % (path, filename)
        output = self.get_raw_tree()
        store.save_object_to_file(filepath, output, pretty=pretty)

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as f:
            f.write((repr(output) + "\n").encode("utf-8"))
        store.save_bytes_to_file(filepath + ".gz", buf.getvalue())

        # Inform Livestatus about the latest inventory update
        store.save_text_to_file("%s/.last" % path, u"")

    def load_from(self, filepath: Union[Path, str]) -> "StructuredDataTree":
        raw_tree = store.load_object_from_file(filepath)
        return self.create_tree_from_raw_tree(raw_tree)

    def create_tree_from_raw_tree(self, raw_tree: SDRawTree) -> "StructuredDataTree":
        if raw_tree:
            self._create_hierarchy_from_data(raw_tree, self._root)
        return self

    def _create_hierarchy_from_data(
        self,
        raw_tree: SDRawTree,
        parent: "Container",
    ) -> None:
        for edge, attrs in raw_tree.items():
            if not attrs:
                continue

            if isinstance(attrs, list):
                numeration = Numeration()
                numeration.set_child_data(attrs)
                parent.add_child(edge, numeration)
            else:
                sub_raw_tree, leaf_data = self._get_child_data(attrs)
                if leaf_data:
                    attributes = Attributes()
                    attributes.set_child_data(leaf_data)
                    parent.add_child(edge, attributes)
                if sub_raw_tree:
                    container = parent.add_child(edge, Container())
                    self._create_hierarchy_from_data(sub_raw_tree, container)

    def _get_child_data(self, raw_entries: Dict) -> Tuple[Dict, Dict]:
        leaf_data: Dict = {}
        sub_raw_tree: Dict = {}
        for k, v in raw_entries.items():
            if isinstance(v, dict):
                # Dict based values mean that current key
                # is a node.
                sub_raw_tree.setdefault(k, v)
            elif isinstance(v, list):
                # Concerns "a.b:" and "a.b:*.c".
                # In the second case we have to deal with nested numerations
                # We take a look at children which may be real numerations
                # or sub trees.
                if self._is_numeration(v):
                    sub_raw_tree.setdefault(k, v)
                else:
                    sub_raw_tree.setdefault(k, dict(enumerate(v)))
            else:
                # Here we collect all other values meaning simple
                # attributes of this node.
                leaf_data.setdefault(k, v)
        return sub_raw_tree, leaf_data

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

    #   ---delegators-----------------------------------------------------------

    def is_empty(self) -> bool:
        return self._root.is_empty()

    def is_equal(self, struct_tree: "StructuredDataTree", edges: Optional[SDPath] = None) -> bool:
        return self._root.is_equal(struct_tree._root, edges=edges)

    def count_entries(self) -> int:
        return self._root.count_entries()

    def get_raw_tree(self) -> SDRawTree:
        return self._root.get_raw_tree()

    def normalize_nodes(self) -> None:
        self._root.normalize_nodes()

    def merge_with(self, struct_tree: "StructuredDataTree") -> None:
        self._root.merge_with(struct_tree._root)

    def has_edge(self, edge: SDNodeName) -> bool:
        return self._root.has_edge(edge)

    def get_sub_container(self, path: SDPath) -> Optional["Container"]:
        return self._root.get_sub_container(path)

    def get_sub_numeration(self, path: SDPath) -> Optional["Numeration"]:
        return self._root.get_sub_numeration(path)

    def get_sub_attributes(self, path: SDPath) -> Optional["Attributes"]:
        return self._root.get_sub_attributes(path)

    def get_sub_children(self, path: SDPath) -> Optional[SDNodeChildren]:
        return self._root.get_sub_children(path)

    #   ---structured tree methods----------------------------------------------

    def compare_with(self, old_tree: "StructuredDataTree") -> SDDeltaResult:
        delta_tree = StructuredDataTree()
        num_new, num_changed, num_removed, delta_root_node =\
            self._root.compare_with(old_tree._root)
        delta_tree._root = delta_root_node
        return num_new, num_changed, num_removed, delta_tree

    def copy(self) -> "StructuredDataTree":
        new_tree = StructuredDataTree()
        new_tree._root = self._root.copy()
        return new_tree

    def get_root_container(self) -> "Container":
        return self._root

    def get_filtered_tree(
            self,
            allowed_paths: Optional[List[Tuple[SDPath,
                                               Optional[List[str]]]]]) -> "StructuredDataTree":
        if allowed_paths is None:
            return self
        filtered_tree = StructuredDataTree()
        for path, keys in allowed_paths:
            # Make a copy of 'paths' which is mutable
            # later 'paths' is modified via .pop(0)
            sub_tree = self._root.get_filtered_branch(list(path), keys, Container())
            if sub_tree is None:
                continue
            filtered_tree._root.merge_with(sub_tree)
        return filtered_tree

    def __repr__(self) -> str:
        return "%s(%s)" % (self.__class__.__name__, pprint.pformat(self.get_raw_tree()))

    #   ---web------------------------------------------------------------------

    def show(self, renderer) -> None:
        # TODO
        self._root.show(renderer)


#.
#   .--Container-----------------------------------------------------------.
#   |              ____            _        _                              |
#   |             / ___|___  _ __ | |_ __ _(_)_ __   ___ _ __              |
#   |            | |   / _ \| '_ \| __/ _` | | '_ \ / _ \ '__|             |
#   |            | |__| (_) | | | | || (_| | | | | |  __/ |                |
#   |             \____\___/|_| |_|\__\__,_|_|_| |_|\___|_|                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Container:
    def __init__(self) -> None:
        self._path: SDNodePath = tuple()
        self._nodes: SDNodes = {}

    def set_path(self, path: SDNodePath) -> None:
        self._path = path

    @property
    def path(self) -> SDNodePath:
        return self._path

    def is_empty(self) -> bool:
        for _, child in self._get_children():
            if not child.is_empty():
                return False
        return True

    def is_equal(self, other: object, edges: Optional[SDPath] = None) -> bool:
        if not isinstance(other, Container):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        for _, my_child, other_child in self._get_comparable_children(other, edges=edges):
            if not my_child.is_equal(other_child):
                return False
        return True

    def count_entries(self) -> int:
        return sum([child.count_entries() for _, child in self._get_children()])

    def compare_with(self, other: object, keep_identical: bool = False) -> CDeltaResult:
        if not isinstance(other, Container):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        delta_node = Container()
        num_new, num_changed, num_removed = 0, 0, 0

        removed_keys, kept_keys, new_keys = _compare_dict_keys(other._nodes, self._nodes)

        for edge, my_child in self._get_children(edges=list(new_keys)):
            new_entries = my_child.count_entries()
            if new_entries:
                num_new += new_entries
                delta_node.add_child(
                    edge,
                    my_child.encode_for_delta_tree(encode_as=_new_delta_tree_node),
                )

        for edge, my_child, other_child in self._get_comparable_children(other,
                                                                         edges=list(kept_keys)):
            if my_child.is_equal(other_child):
                if keep_identical:
                    delta_node.add_child(
                        edge,
                        my_child.encode_for_delta_tree(encode_as=_identical_delta_tree_node),
                    )
                continue
            new_entries, changed_entries, removed_entries, delta_child = \
                my_child.compare_with(other_child, keep_identical=keep_identical)
            if (new_entries or changed_entries or removed_entries) and delta_child is not None:
                num_new += new_entries
                num_changed += changed_entries
                num_removed += removed_entries
                delta_node.add_child(edge, delta_child)

        for edge, other_child in other._get_children(edges=list(removed_keys)):
            removed_entries = other_child.count_entries()
            if removed_entries:
                num_removed += removed_entries
                delta_node.add_child(
                    edge,
                    other_child.encode_for_delta_tree(encode_as=_removed_delta_tree_node),
                )

        return num_new, num_changed, num_removed, delta_node

    def encode_for_delta_tree(self, encode_as: SDEncodeAs) -> "Container":
        delta_node = Container()
        for edge, child in self._get_children():
            delta_node.add_child(edge, child.encode_for_delta_tree(encode_as))
        return delta_node

    def get_raw_tree(self) -> Dict:
        tree: Dict = {}
        for edge, child in self._get_children():
            child_tree = child.get_raw_tree()
            if self._is_nested_numeration_tree(child) and isinstance(child_tree, dict):
                # Sort by index but forget index afterwards => nested sub nodes as before
                sorted_values = [child_tree[k] for k in sorted(child_tree.keys())]
                tree.setdefault(edge, sorted_values)
            elif isinstance(child, Numeration):
                tree.setdefault(edge, child_tree)
            else:
                tree.setdefault(edge, {}).update(child_tree)
        return tree

    def _is_nested_numeration_tree(self, child: Any) -> bool:
        if isinstance(child, Container):
            for key in child._nodes:
                if isinstance(key, int):
                    return True
        return False

    def normalize_nodes(self) -> None:
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
        for edge, child in self._get_children():
            if isinstance(child, Numeration) and \
               self._has_nested_numeration_node(child.get_child_data()):
                self._set_nested_numeration_node(edge, child.get_child_data())

            if child.is_empty():
                self._nodes[edge].remove_node_child(child)
                continue

            if isinstance(child, Container):
                child.normalize_nodes()

    def _has_nested_numeration_node(self, node_data: SDTable) -> bool:
        for entry in node_data:
            for v in entry.values():
                if isinstance(v, list):
                    return True
        return False

    def _set_nested_numeration_node(
        self,
        edge: SDNodeName,
        child_data: SDTable,
    ) -> None:
        del self._nodes[edge]
        parent = self.add_child(edge, Container())
        for nr, entry in enumerate(child_data):
            attrs: Dict = {}
            for k, v in entry.items():
                if isinstance(v, list):
                    numeration = parent.add_child(nr, Container()).add_child(k, Numeration())
                    numeration.set_child_data(v)
                else:
                    attrs.setdefault(k, v)
            if attrs:
                attributes = parent.add_child(nr, Attributes())
                attributes.set_child_data(attrs)

    def merge_with(self, other: object) -> None:
        if not isinstance(other, Container):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        for edge, my_child, other_child in self._get_comparable_children(other):
            my_child = self.add_child(edge, my_child)
            my_child.merge_with(other_child)

    def copy(self) -> "Container":
        new_node = Container()
        for edge, child in self._get_children():
            new_node.add_child(edge, child.copy())
        return new_node

    #   ---container methods----------------------------------------------------

    def _create_hierarchy(self, path: SDPath) -> "Container":
        if not path:
            return self
        return self.add_child(path[0], Container())._create_hierarchy(path[1:])

    def add_child(
        self,
        edge: SDNodeName,
        child: Union["Container", "Numeration", "Attributes"],
    ):
        node = self._nodes.setdefault(edge, Node(self._path + (edge,)))
        return node.add_node_child(child)

    def has_edge(self, edge: SDNodeName) -> bool:
        return bool(self._nodes.get(edge))

    def get_filtered_branch(
        self,
        path: SDPath,
        keys: Optional[SDKeys],
        parent: "Container",
    ) -> Optional["Container"]:
        sub_node = self._get_sub_node(path[:1])
        if sub_node is None:
            return None

        edge = path.pop(0)
        if path:
            container = sub_node.get_node_container()
            if container is not None:
                filtered = container.get_filtered_branch(path, keys, Container())
                if filtered is not None:
                    parent.add_child(edge, filtered)
            return parent

        if keys is None:
            for child in sub_node.get_node_children():
                parent.add_child(edge, child)
            return parent

        numeration = sub_node.get_node_numeration()
        if numeration is not None:
            if keys:
                numeration = numeration.get_filtered_data(keys)
            parent.add_child(edge, numeration)

        attributes = sub_node.get_node_attributes()
        if attributes is not None:
            if keys:
                attributes = attributes.get_filtered_data(keys)
            parent.add_child(edge, attributes)

        return parent

    #   ---getting [sub] nodes/node attributes----------------------------------

    def get_edge_nodes(self) -> List[Tuple[SDNodeName, "Node"]]:
        return list(self._nodes.items())

    def _get_children(self, edges: Optional[SDPath] = None) -> SDChildren:
        """Returns a flatten list of tuples (edge, absolute path, child)"""
        return {(edge, child)
                for edge, node in self._nodes.items()
                for child in node.get_node_children()
                if edges is None or edge in edges}

    def _get_comparable_children(
        self,
        other: "Container",
        edges: Optional[SDPath] = None,
    ) -> SDCompChildren:
        """Returns a flatten list of tuples (edge, absolute path, my child, other child)"""
        return {(edge, child, other_child)
                for edge in (set(edges) if edges else set(self._nodes).union(other._nodes))
                for child, other_child in self._nodes.get(
                    edge, Node()).get_comparable_node_children(other._nodes.get(edge, Node()))}

    def get_sub_container(self, path: SDPath) -> Optional["Container"]:
        sub_node = self._get_sub_node(path)
        if sub_node is None:
            return None
        return sub_node.get_node_container()

    def get_sub_numeration(self, path: SDPath) -> Optional["Numeration"]:
        sub_node = self._get_sub_node(path)
        if sub_node is None:
            return None
        return sub_node.get_node_numeration()

    def get_sub_attributes(self, path: SDPath) -> Optional["Attributes"]:
        sub_node = self._get_sub_node(path)
        if sub_node is None:
            return None
        return sub_node.get_node_attributes()

    def get_sub_children(self, path: SDPath) -> Optional[SDNodeChildren]:
        sub_node = self._get_sub_node(path)
        if sub_node is None:
            return None
        return sub_node.get_node_children()

    def _get_sub_node(self, path: SDPath) -> Optional["Node"]:
        if not path:
            return None

        sub_node = self._nodes.get(path[0])
        if len(path) == 1 or sub_node is None:
            return sub_node

        container = sub_node.get_node_container()
        if container is None:
            return None

        return container._get_sub_node(path[1:])

    #   ---web------------------------------------------------------------------

    def show(self, renderer):
        # TODO
        renderer.show_container(self)


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
        self._path: SDNodePath = tuple()
        self._numeration: SDTable = []

    def set_path(self, path: SDNodePath) -> None:
        self._path = path

    @property
    def path(self) -> SDNodePath:
        return self._path

    def is_empty(self) -> bool:
        return self._numeration == []

    def is_equal(self, other: object, edges: Optional[SDPath] = None) -> bool:
        if not isinstance(other, Numeration):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        for row in self._numeration:
            if row not in other._numeration:
                return False
        for row in other._numeration:
            if row not in self._numeration:
                return False
        return True

    def count_entries(self) -> int:
        return sum(map(len, self._numeration))

    def compare_with(self, other: object, keep_identical: bool = False) -> NDeltaResult:
        if not isinstance(other, Numeration):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        delta_node = Numeration()
        num_new, num_changed, num_removed = 0, 0, 0

        remaining_own_rows, remaining_other_rows, identical_rows = self._get_categorized_rows(other)
        new_rows: List = []
        removed_rows: List = []
        compared_rows: List = []

        if not remaining_other_rows and remaining_own_rows:
            new_rows.extend(remaining_own_rows)

        elif remaining_other_rows and not remaining_own_rows:
            removed_rows.extend(remaining_other_rows)

        elif remaining_other_rows and remaining_own_rows:
            if len(remaining_other_rows) == len(remaining_own_rows):
                num_new, num_changed, num_removed, compared_rows =\
                    self._compare_remaining_rows_with_same_length(
                        remaining_own_rows,
                        remaining_other_rows,
                        keep_identical=keep_identical)
            else:
                new_rows.extend(remaining_own_rows)
                removed_rows.extend(remaining_other_rows)

        delta_node_rows = compared_rows\
                          + [{k: _new_delta_tree_node(v)
                             for k,v in row.items()}
                             for row in new_rows]\
                          + [{k: _removed_delta_tree_node(v)
                             for k,v in row.items()}
                             for row in removed_rows]

        if keep_identical:
            delta_node_rows += [
                {k: _identical_delta_tree_node(v) for k, v in row.items()} for row in identical_rows
            ]

        delta_node.set_child_data(delta_node_rows)

        return len(new_rows) + num_new, num_changed, len(removed_rows) + num_removed, delta_node

    def _get_categorized_rows(self, other: "Numeration") -> Tuple[SDTable, SDTable, SDTable]:
        identical_rows = []
        remaining_other_rows = []
        remaining_new_rows = []
        for row in other._numeration:
            if row in self._numeration:
                if row not in identical_rows:
                    identical_rows.append(row)
            else:
                remaining_other_rows.append(row)
        for row in self._numeration:
            if row in other._numeration:
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
    ) -> Tuple[int, int, int, SDTable]:
        # In this case we assume that each entry corresponds to the
        # other one with the same index.
        num_new, num_changed, num_removed = 0, 0, 0
        compared_rows = []
        for own_row, other_row in zip(own_rows, other_rows):
            new_entries, changed_entries, removed_entries, identical_entries = \
                _compare_dicts(other_row, own_row)
            num_new += len(new_entries)
            num_changed += len(changed_entries)
            num_removed += len(removed_entries)
            row: Dict = {}
            for entries in [new_entries, changed_entries, removed_entries]:
                row.update(entries)
            if keep_identical or new_entries or changed_entries or removed_entries:
                row.update(identical_entries)
            if row:
                compared_rows.append(row)
        return num_new, num_changed, num_removed, compared_rows

    def encode_for_delta_tree(self, encode_as: SDEncodeAs) -> "Numeration":
        delta_node = Numeration()
        data = []
        for entry in self._numeration:
            data.append({k: encode_as(v) for k, v in entry.items()})
        delta_node.set_child_data(data)
        return delta_node

    def get_raw_tree(self) -> SDTable:
        return self._numeration

    def merge_with(self, other: object) -> None:
        if not isinstance(other, Numeration):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        other_keys = other._get_numeration_keys()
        my_keys = self._get_numeration_keys()
        intersect_keys = my_keys.intersection(other_keys)

        # In case there is no intersection, append all other rows without
        # merging with own rows
        if not intersect_keys:
            self._numeration += other._numeration
            return

        # Try to match rows of both trees based on the keys that are found in
        # both. Matching rows are updated. Others are appended.
        other_num = {
            other._prepare_key(entry, intersect_keys): entry for entry in other._numeration
        }

        for entry in self._numeration:
            key = self._prepare_key(entry, intersect_keys)
            if key in other_num:
                entry.update(other_num[key])
                del other_num[key]

        self._numeration += list(other_num.values())

    def _get_numeration_keys(self) -> Set[SDKey]:
        return {key for row in self._numeration for key in row}

    def _prepare_key(self, entry: Dict, keys: Set[SDKey]) -> Tuple[SDKey, ...]:
        return tuple(entry[key] for key in sorted(keys) if key in entry)

    def copy(self) -> "Numeration":
        new_node = Numeration()
        new_node.set_child_data(self._numeration[:])
        return new_node

    #   ---leaf methods---------------------------------------------------------

    def set_child_data(self, data: SDTable) -> None:
        self._numeration += data

    def get_child_data(self) -> SDTable:
        return self._numeration

    def get_filtered_data(self, keys: SDKeys) -> "Numeration":
        filtered = Numeration()
        numeration = []
        for entry in self._numeration:
            filtered_entry = _get_filtered_dict(entry, keys)
            if filtered_entry:
                numeration.append(filtered_entry)
        filtered.set_child_data(numeration)
        return filtered

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
        self._path: SDNodePath = tuple()
        self._attributes: SDAttributes = {}

    def set_path(self, path: SDNodePath) -> None:
        self._path = path

    @property
    def path(self) -> SDNodePath:
        return self._path

    def is_empty(self) -> bool:
        return self._attributes == {}

    def is_equal(self, other: object, edges: Optional[SDPath] = None) -> bool:
        if not isinstance(other, Attributes):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        return self._attributes == other._attributes

    def count_entries(self) -> int:
        return len(self._attributes)

    def compare_with(self, other: object, keep_identical: bool = False) -> ADeltaResult:
        if not isinstance(other, Attributes):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        delta_node = Attributes()
        new, changed, removed, identical = _compare_dicts(other._attributes, self._attributes)

        if new or changed or removed:
            delta_node.set_child_data(new)
            delta_node.set_child_data(changed)
            delta_node.set_child_data(removed)
            if keep_identical:
                delta_node.set_child_data(identical)

        return len(new), len(changed), len(removed), delta_node

    def encode_for_delta_tree(self, encode_as: SDEncodeAs) -> "Attributes":
        delta_node = Attributes()
        data = {k: encode_as(v) for k, v in self._attributes.items()}
        delta_node.set_child_data(data)
        return delta_node

    def get_raw_tree(self) -> SDAttributes:
        return self._attributes

    def merge_with(self, other: object) -> None:
        if not isinstance(other, Attributes):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        self._attributes.update(other._attributes)

    def copy(self) -> "Attributes":
        new_node = Attributes()
        new_node.set_child_data(self._attributes.copy())
        return new_node

    #   ---leaf methods---------------------------------------------------------

    def set_child_data(self, data: SDAttributes) -> None:
        self._attributes.update(data)

    def get_child_data(self) -> SDAttributes:
        return self._attributes

    def get_filtered_data(self, keys: SDKeys) -> "Attributes":
        filtered = Attributes()
        attributes = _get_filtered_dict(self._attributes, keys)
        filtered.set_child_data(attributes)
        return filtered

    #   ---web------------------------------------------------------------------

    def show(self, renderer):
        # TODO
        renderer.show_attributes(self)


#.
#   .--Node----------------------------------------------------------------.
#   |                       _   _           _                              |
#   |                      | \ | | ___   __| | ___                         |
#   |                      |  \| |/ _ \ / _` |/ _ \                        |
#   |                      | |\  | (_) | (_| |  __/                        |
#   |                      |_| \_|\___/ \__,_|\___|                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Node:
    """Node contains max. one node attribute per type."""

    CHILDREN_NAMES = [Container, Numeration, Attributes]

    def __init__(self, abs_path: Optional[SDNodePath] = None) -> None:
        if abs_path is None:
            abs_path = tuple()
        self._children: Dict = {}
        self._abs_path = abs_path

    def get_absolute_path(self) -> SDNodePath:
        # Only needed in GUI::NodeRenderer, can be removed as soon as NodeRenderer is refactored.
        return self._abs_path

    def add_node_child(self, child: SDChild) -> SDChild:
        child.set_path(self._abs_path)
        return self._children.setdefault(type(child), child)

    def remove_node_child(self, child: SDChild) -> None:
        child_type = type(child)
        if child_type in self._children:
            del self._children[child_type]

    def get_node_container(self) -> Optional["Container"]:
        return self._children.get(type(Container()))

    def get_node_numeration(self) -> Optional["Numeration"]:
        return self._children.get(type(Numeration()))

    def get_node_attributes(self) -> Optional["Attributes"]:
        return self._children.get(type(Attributes()))

    def get_node_children(self) -> SDNodeChildren:
        return set(self._children.values())

    def get_comparable_node_children(self, other: object) -> SDCompNodeChildren:
        if not isinstance(other, Node):
            raise TypeError("Cannot compare %s with %s" % (type(self), type(other)))

        comparable_children = set()
        for child_name in self.CHILDREN_NAMES:
            child = child_name()
            child_type = type(child)
            if self._children.get(child_type) is None and other._children.get(child_type) is None:
                continue

            comparable_children.add(
                (self._children.get(child_type, child), other._children.get(child_type, child)))
        return comparable_children

    def copy(self) -> "Node":
        new_node = Node(self._abs_path)
        for child in self._children.values():
            new_node.add_node_child(child.copy())
        return new_node


#.
#   .--helpers-------------------------------------------------------------.
#   |                  _          _                                        |
#   |                 | |__   ___| |_ __   ___ _ __ ___                    |
#   |                 | '_ \ / _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 | | | |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


def _compare_dicts(old_dict: Dict, new_dict: Dict) -> Tuple[Dict, Dict, Dict, Dict]:
    """
    Format of compared entries:
      new:          {k: (None, new_value), ...}
      changed:      {k: (old_value, new_value), ...}
      removed:      {k: (old_value, None), ...}
      identical:    {k: (value, value), ...}
    """
    removed_keys, kept_keys, new_keys = _compare_dict_keys(old_dict, new_dict)
    identical: Dict = {}
    changed: Dict = {}
    for k in kept_keys:
        new_value = new_dict[k]
        old_value = old_dict[k]
        if new_value == old_value:
            identical.setdefault(k, _identical_delta_tree_node(old_value))
        else:
            changed.setdefault(k, _changed_delta_tree_node(old_value, new_value))
    return {k: _new_delta_tree_node(new_dict[k]) for k in new_keys}, changed,\
           {k: _removed_delta_tree_node(old_dict[k]) for k in removed_keys}, identical


def _compare_dict_keys(old_dict: Dict, new_dict: Dict) -> Tuple[Set, Set, Set]:
    """
    Returns the set relationships of the keys between two dictionaries:
    - relative complement of new_dict in old_dict
    - intersection of both
    - relative complement of old_dict in new_dict
    """
    old_keys, new_keys = set(old_dict), set(new_dict)
    return old_keys - new_keys, old_keys.intersection(new_keys),\
           new_keys - old_keys


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
