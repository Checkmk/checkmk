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
from typing import AnyStr, Dict, List, Optional

from six import ensure_str

import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException

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
#             NA:   NodeAttribute   (interface)
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
    def __init__(self):
        super(StructuredDataTree, self).__init__()
        self._root = Container()

    #   ---building tree from plugins-------------------------------------------

    def get_dict(self, tree_path):
        return self._get_object(tree_path, Attributes())

    def get_list(self, tree_path):
        return self._get_object(tree_path, Numeration())

    def _get_object(self, tree_path, child):
        self._validate_tree_path(tree_path)
        path = self._parse_tree_path(tree_path)
        parent = self._create_hierarchy(path[:-1])
        return parent.add_child(path[-1], child, tuple(path)).get_child_data()

    def _validate_tree_path(self, tree_path: AnyStr) -> None:
        if not tree_path:
            raise MKGeneralException("Empty tree path or zero.")
        # TODO: Check if bytes/ensure_str is necessary.
        if not isinstance(tree_path, (bytes, str)):
            raise MKGeneralException("Wrong tree path format. Must be of type string.")
        tp = ensure_str(tree_path)
        if not tp.endswith((":", ".")):
            raise MKGeneralException("No valid tree path.")
        if bool(re.compile('[^a-zA-Z0-9_.:-]').search(tp)):
            raise MKGeneralException("Specified tree path contains unexpected characters.")

    def _parse_tree_path(self, tree_path):
        if tree_path.startswith("."):
            tree_path = tree_path[1:]
        if tree_path.endswith(":") or tree_path.endswith("."):
            tree_path = tree_path[:-1]
        return tree_path.split(".")

    def _create_hierarchy(self, path):
        if not path:
            return self._root
        abs_path = []
        node = self._root
        while path:
            edge = path.pop(0)
            abs_path.append(edge)
            node = node.add_child(edge, Container(), tuple(abs_path))
        return node

    #   ---loading and saving tree----------------------------------------------

    def save_to(self, path, filename, pretty=False):
        filepath = "%s/%s" % (path, filename)
        output = self.get_raw_tree()
        store.save_object_to_file(filepath, output, pretty=pretty)

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as f:
            f.write((repr(output) + "\n").encode("utf-8"))
        store.save_bytes_to_file(filepath + ".gz", buf.getvalue())

        # Inform Livestatus about the latest inventory update
        store.save_text_to_file("%s/.last" % path, u"")

    def load_from(self, filepath):
        raw_tree = store.load_object_from_file(filepath)
        return self.create_tree_from_raw_tree(raw_tree)

    def create_tree_from_raw_tree(self, raw_tree):
        if raw_tree:
            self._create_hierarchy_from_data(raw_tree, self._root, tuple())
        return self

    def _create_hierarchy_from_data(self, raw_tree, parent, parent_path):
        for edge, attrs in raw_tree.items():
            if not attrs:
                continue
            if parent_path:
                abs_path = parent_path
            else:
                abs_path = tuple()
            abs_path += (edge,)
            if isinstance(attrs, list):
                numeration = Numeration()
                numeration.set_child_data(attrs)
                parent.add_child(edge, numeration, abs_path)
            else:
                sub_raw_tree, leaf_data = self._get_child_data(attrs)
                if leaf_data:
                    attributes = Attributes()
                    attributes.set_child_data(leaf_data)
                    parent.add_child(edge, attributes, abs_path)
                if sub_raw_tree:
                    container = parent.add_child(edge, Container(), abs_path)
                    self._create_hierarchy_from_data(sub_raw_tree, container, abs_path)

    def _get_child_data(self, raw_entries):
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

    def _is_numeration(self, entries):
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

    def is_empty(self):
        return self._root.is_empty()

    def is_equal(self, struct_tree, edges=None):
        return self._root.is_equal(struct_tree._root, edges=edges)

    def count_entries(self):
        return self._root.count_entries()

    def get_raw_tree(self):
        return self._root.get_raw_tree()

    def normalize_nodes(self):
        self._root.normalize_nodes()

    def merge_with(self, struct_tree):
        self._root.merge_with(struct_tree._root)

    def has_edge(self, edge):
        return self._root.has_edge(edge)

    def get_children(self, edges=None):
        return self._root.get_children(edges=edges)

    def get_sub_container(self, path):
        return self._root.get_sub_container(path)

    def get_sub_numeration(self, path):
        return self._root.get_sub_numeration(path)

    def get_sub_attributes(self, path):
        return self._root.get_sub_attributes(path)

    def get_sub_children(self, path):
        return self._root.get_sub_children(path)

    #   ---structured tree methods----------------------------------------------

    def compare_with(self, old_tree):
        delta_tree = StructuredDataTree()
        num_new, num_changed, num_removed, delta_root_node =\
            self._root.compare_with(old_tree._root)
        delta_tree._root = delta_root_node
        return num_new, num_changed, num_removed, delta_tree

    def copy(self):
        new_tree = StructuredDataTree()
        new_tree._root = self._root.copy()
        return new_tree

    def get_root_container(self):
        return self._root

    def get_filtered_tree(self, allowed_paths):
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

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, pprint.pformat(self.get_raw_tree()))

    #   ---web------------------------------------------------------------------

    def show(self, renderer, path=None):
        self._root.show(renderer, path=path)


#.
#   .--NodeAttribute-------------------------------------------------------.
#   |  _   _           _         _   _   _        _ _           _          |
#   | | \ | | ___   __| | ___   / \ | |_| |_ _ __(_) |__  _   _| |_ ___    |
#   | |  \| |/ _ \ / _` |/ _ \ / _ \| __| __| '__| | '_ \| | | | __/ _ \   |
#   | | |\  | (_) | (_| |  __// ___ \ |_| |_| |  | | |_) | |_| | ||  __/   |
#   | |_| \_|\___/ \__,_|\___/_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___|   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class NodeAttribute:
    """Interface for all node attributes"""
    def is_empty(self):
        raise NotImplementedError()

    def is_equal(self, foreign, edges=None):
        """At the moment 'edges' argument just allowed for root node."""
        raise NotImplementedError()

    def count_entries(self):
        raise NotImplementedError()

    def compare_with(self, other, keep_identical=False):
        """Compares new tree with old one: new_tree.compare_with(old_tree)."""
        raise NotImplementedError()

    def encode_for_delta_tree(self, encode_as):
        raise NotImplementedError()

    def get_raw_tree(self):
        raise NotImplementedError()

    def normalize_nodes(self):
        raise NotImplementedError()

    def merge_with(self, foreign):
        raise NotImplementedError()

    def copy(self):
        raise NotImplementedError()

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, pprint.pformat(self.get_raw_tree()))

    #   ---web------------------------------------------------------------------

    def show(self, renderer, path=None):
        raise NotImplementedError()


#.
#   .--Container-----------------------------------------------------------.
#   |              ____            _        _                              |
#   |             / ___|___  _ __ | |_ __ _(_)_ __   ___ _ __              |
#   |            | |   / _ \| '_ \| __/ _` | | '_ \ / _ \ '__|             |
#   |            | |__| (_) | | | | || (_| | | | | |  __/ |                |
#   |             \____\___/|_| |_|\__\__,_|_|_| |_|\___|_|                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Container(NodeAttribute):
    def __init__(self):
        super(Container, self).__init__()
        self._edges = {}

    def is_empty(self):
        for _, __, child in self.get_children():
            if not child.is_empty():
                return False
        return True

    def is_equal(self, foreign, edges=None):
        for _, __, my_child, foreign_child in self._get_comparable_children(foreign, edges=edges):
            if not my_child.is_equal(foreign_child):
                return False
        return True

    def count_entries(self):
        return sum([child.count_entries() for _, __, child in self.get_children()])

    def compare_with(self, other, keep_identical=False):
        removed_keys, kept_keys, new_keys = _compare_dict_keys(other._edges, self._edges)

        delta_node = Container()
        num_new, num_changed, num_removed = 0, 0, 0
        for edge, abs_path, my_child in self.get_children(edges=new_keys):
            new_entries = my_child.count_entries()
            if new_entries:
                num_new += new_entries
                delta_node.add_child(edge,
                                     my_child.encode_for_delta_tree(encode_as=_new_delta_tree_node),
                                     abs_path)

        for edge, abs_path, my_child, other_child in \
            self._get_comparable_children(other, edges=kept_keys):
            if my_child.is_equal(other_child):
                if keep_identical:
                    delta_node.add_child(
                        edge, my_child.encode_for_delta_tree(encode_as=_identical_delta_tree_node),
                        abs_path)
                continue
            new_entries, changed_entries, removed_entries, delta_child = \
                my_child.compare_with(other_child, keep_identical=keep_identical)
            if new_entries or changed_entries or removed_entries:
                num_new += new_entries
                num_changed += changed_entries
                num_removed += removed_entries
                delta_node.add_child(edge, delta_child, abs_path)

        for edge, abs_path, other_child in other.get_children(edges=removed_keys):
            removed_entries = other_child.count_entries()
            if removed_entries:
                num_removed += removed_entries
                delta_node.add_child(
                    edge, other_child.encode_for_delta_tree(encode_as=_removed_delta_tree_node),
                    abs_path)

        return num_new, num_changed, num_removed, delta_node

    def encode_for_delta_tree(self, encode_as):
        delta_node = Container()
        for edge, abs_path, child in self.get_children():
            delta_node.add_child(edge, child.encode_for_delta_tree(encode_as), abs_path)
        return delta_node

    def get_raw_tree(self):
        tree: Dict = {}
        for edge, _, child in self.get_children():
            child_tree = child.get_raw_tree()
            if self._is_nested_numeration_tree(child):
                # Sort by index but forget index afterwards => nested sub nodes as before
                sorted_values = [child_tree[k] for k in sorted(child_tree.keys())]
                tree.setdefault(edge, sorted_values)
            elif isinstance(child, Numeration):
                tree.setdefault(edge, child_tree)
            else:
                tree.setdefault(edge, {}).update(child_tree)
        return tree

    def _is_nested_numeration_tree(self, child):
        if isinstance(child, Container):
            for key in child._edges:
                if isinstance(key, int):
                    return True
        return False

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
        for edge, abs_path, child in self.get_children():
            if isinstance(child, Numeration) and \
               self._has_nested_numeration_node(child.get_child_data()):
                self._set_nested_numeration_node(edge, child.get_child_data(), abs_path)
            if child.is_empty():
                self._edges[edge].remove_node_child(child)
                continue
            child.normalize_nodes()

    def _has_nested_numeration_node(self, node_data):
        for entry in node_data:
            for v in entry.values():
                if isinstance(v, list):
                    return True
        return False

    def _set_nested_numeration_node(self, edge, child_data, abs_path):
        del self._edges[edge]
        parent = self.add_child(edge, Container(), abs_path)
        for nr, entry in enumerate(child_data):
            attrs: Dict = {}
            for k, v in entry.items():
                if isinstance(v, list):
                    numeration = parent.add_child(nr, Container(), abs_path+(nr,))\
                                       .add_child(k, Numeration(), abs_path+(nr,k))
                    numeration.set_child_data(v)
                else:
                    attrs.setdefault(k, v)
            if attrs:
                attributes = parent.add_child(nr, Attributes(), abs_path + (nr,))
                attributes.set_child_data(attrs)

    def merge_with(self, foreign):
        for edge, abs_path, my_child, foreign_child in \
            self._get_comparable_children(foreign):
            my_child = self.add_child(edge, my_child, abs_path)
            my_child.merge_with(foreign_child)

    def copy(self):
        new_node = Container()
        for edge, abs_path, child in self.get_children():
            new_node.add_child(edge, child.copy(), abs_path)
        return new_node

    #   ---container methods----------------------------------------------------

    def add_child(self, edge, child, abs_path=None):
        node = self._edges.setdefault(edge, Node(abs_path))
        return node.add_node_child(child)

    def has_edge(self, edge):
        return bool(self._edges.get(edge))

    def get_filtered_branch(self, path, keys, parent):
        sub_node = self._get_sub_node(path[:1])
        if sub_node is None:
            return None

        edge = path.pop(0)
        sub_node_abs_path = sub_node.get_absolute_path()
        if path:
            container = sub_node.get_node_container()
            if container is not None:
                filtered = container.get_filtered_branch(path, keys, Container())
                if filtered is not None:
                    parent.add_child(edge, filtered, sub_node_abs_path)
            return parent

        if keys is None:
            for child in sub_node.get_node_children():
                parent.add_child(edge, child, sub_node_abs_path)
            return parent

        numeration = sub_node.get_node_numeration()
        if numeration is not None:
            if keys:
                numeration = numeration.get_filtered_data(keys)
            parent.add_child(edge, numeration, sub_node_abs_path)

        attributes = sub_node.get_node_attributes()
        if attributes is not None:
            if keys:
                attributes = attributes.get_filtered_data(keys)
            parent.add_child(edge, attributes, sub_node_abs_path)

        return parent

    #   ---getting [sub] nodes/node attributes----------------------------------

    def get_edge_nodes(self):
        return list(self._edges.items())

    def get_children(self, edges=None):
        """Returns a flatten list of tuples (edge, absolute path, child)"""
        children = set()
        if edges is None:
            for edge, node in self._edges.items():
                node_abs_path = node.get_absolute_path()
                for child in node.get_node_children():
                    children.add((edge, node_abs_path, child))
        else:
            for edge, node in self._edges.items():
                if edge not in edges:
                    continue
                node_abs_path = node.get_absolute_path()
                for child in node.get_node_children():
                    children.add((edge, node_abs_path, child))
        return children

    def _get_comparable_children(self, foreign, edges=None):
        """Returns a flatten list of tuples (edge, absolute path, my child, foreign child)"""
        comparable_children = set()
        if edges is None:
            edges = set(self._edges).union(foreign._edges)
        for edge in edges:
            my_node = self._edges.get(edge, Node())
            foreign_node = foreign._edges.get(edge, Node())
            for abs_path, my_child, foreign_child in \
                my_node.get_comparable_node_children(foreign_node):
                comparable_children.add((edge, abs_path, my_child, foreign_child))
        return comparable_children

    def get_sub_container(self, path):
        sub_node = self._get_sub_node(path)
        if sub_node is None:
            return None
        return sub_node.get_node_container()

    def get_sub_numeration(self, path):
        sub_node = self._get_sub_node(path)
        if sub_node is None:
            return None
        return sub_node.get_node_numeration()

    def get_sub_attributes(self, path):
        sub_node = self._get_sub_node(path)
        if sub_node is None:
            return None
        return sub_node.get_node_attributes()

    def get_sub_children(self, path):
        sub_node = self._get_sub_node(path)
        if sub_node is None:
            return None
        return sub_node.get_node_children()

    def _get_sub_node(self, path):
        if not path:
            return None

        edge, path = path[0], path[1:]

        sub_node = self._edges.get(edge)
        if sub_node is None:
            return None

        if path:
            container = sub_node.get_node_container()
            if container is None:
                return None
            return container._get_sub_node(path)

        return sub_node

    #   ---web------------------------------------------------------------------

    def show(self, renderer, path=None):
        renderer.show_container(self, path=path)


#.
#   .--Leaf----------------------------------------------------------------.
#   |                         _                __                          |
#   |                        | |    ___  __ _ / _|                         |
#   |                        | |   / _ \/ _` | |_                          |
#   |                        | |__|  __/ (_| |  _|                         |
#   |                        |_____\___|\__,_|_|                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Leaf(NodeAttribute):
    """Interface for all primitive nodes/leaves"""
    def normalize_nodes(self):
        pass

    def set_child_data(self, data):
        raise NotImplementedError()

    def get_child_data(self):
        raise NotImplementedError()

    def get_filtered_data(self, keys):
        raise NotImplementedError()

    def _get_filtered_entries(self, entries, keys):
        filtered: Dict = {}
        for k, v in entries.items():
            if k in keys:
                filtered.setdefault(k, v)
        return filtered


#.
#   .--Numeration----------------------------------------------------------.
#   |       _   _                                _   _                     |
#   |      | \ | |_   _ _ __ ___   ___ _ __ __ _| |_(_) ___  _ __          |
#   |      |  \| | | | | '_ ` _ \ / _ \ '__/ _` | __| |/ _ \| '_ \         |
#   |      | |\  | |_| | | | | | |  __/ | | (_| | |_| | (_) | | | |        |
#   |      |_| \_|\__,_|_| |_| |_|\___|_|  \__,_|\__|_|\___/|_| |_|        |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Numeration(Leaf):
    def __init__(self):
        super(Numeration, self).__init__()
        self._numeration = []

    def is_empty(self):
        return self._numeration == []

    def is_equal(self, foreign, edges=None):
        for row in self._numeration:
            if row not in foreign._numeration:
                return False
        for row in foreign._numeration:
            if row not in self._numeration:
                return False
        return True

    def count_entries(self):
        return sum(map(len, self._numeration))

    def compare_with(self, other, keep_identical=False):
        remaining_own_rows, remaining_other_rows, identical_rows =\
            self._get_categorized_rows(other)

        new_rows: List = []
        removed_rows: List = []
        compared_rows = []
        num_new, num_changed, num_removed = 0, 0, 0
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
        delta_node: Optional[Numeration] = None
        if delta_node_rows:
            delta_node = Numeration()
            delta_node.set_child_data(delta_node_rows)
        return len(new_rows) + num_new, num_changed,\
               len(removed_rows) + num_removed, delta_node

    def _get_categorized_rows(self, other):
        identical_rows: List = []
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

    def _compare_remaining_rows_with_same_length(self, own_rows, other_rows, keep_identical=False):
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

    def encode_for_delta_tree(self, encode_as):
        delta_node = Numeration()
        data = []
        for entry in self._numeration:
            data.append({k: encode_as(v) for k, v in entry.items()})
        delta_node.set_child_data(data)
        return delta_node

    def get_raw_tree(self):
        return self._numeration

    def merge_with(self, foreign):
        foreign_keys = foreign._get_numeration_keys()
        my_keys = self._get_numeration_keys()
        intersect_keys = my_keys.intersection(foreign_keys)

        # In case there is no intersection, append all foreign rows without
        # merging with own rows
        if not intersect_keys:
            self._numeration += foreign._numeration
            return

        # Try to match rows of both trees based on the keys that are found in
        # both. Matching rows are updated. Others are appended.
        foreign_num = {
            foreign._prepare_key(entry, intersect_keys): entry for entry in foreign._numeration
        }

        for entry in self._numeration:
            key = self._prepare_key(entry, intersect_keys)
            if key in foreign_num:
                entry.update(foreign_num[key])
                del foreign_num[key]

        self._numeration += list(foreign_num.values())

    def _get_numeration_keys(self):
        return {key for row in self._numeration for key in row}

    def _prepare_key(self, entry, keys):
        return tuple(entry[key] for key in sorted(keys) if key in entry)

    def copy(self):
        new_node = Numeration()
        new_node.set_child_data(self._numeration[:])
        return new_node

    #   ---leaf methods---------------------------------------------------------

    def set_child_data(self, data):
        self._numeration += data

    def get_child_data(self):
        return self._numeration

    def get_filtered_data(self, keys):
        filtered = Numeration()
        numeration = []
        for entry in self._numeration:
            filtered_entry = self._get_filtered_entries(entry, keys)
            if filtered_entry:
                numeration.append(filtered_entry)
        filtered.set_child_data(numeration)
        return filtered

    #   ---web------------------------------------------------------------------

    def show(self, renderer, path=None):
        renderer.show_numeration(self, path=path)


#.
#   .--Attributes----------------------------------------------------------.
#   |              _   _   _        _ _           _                        |
#   |             / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___             |
#   |            / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|            |
#   |           / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \            |
#   |          /_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class Attributes(Leaf):
    def __init__(self):
        super(Attributes, self).__init__()
        self._attributes = {}

    def is_empty(self):
        return self._attributes == {}

    def is_equal(self, foreign, edges=None):
        return self._attributes == foreign._attributes

    def count_entries(self):
        return len(self._attributes)

    def compare_with(self, other, keep_identical=False):
        new, changed, removed, identical = \
            _compare_dicts(other._attributes, self._attributes)
        delta_node: Optional[Attributes] = None
        if new or changed or removed:
            delta_node = Attributes()
            delta_node.set_child_data(new)
            delta_node.set_child_data(changed)
            delta_node.set_child_data(removed)
            if keep_identical:
                delta_node.set_child_data(identical)
        return len(new), len(changed), len(removed), delta_node

    def encode_for_delta_tree(self, encode_as):
        delta_node = Attributes()
        data = {k: encode_as(v) for k, v in self._attributes.items()}
        delta_node.set_child_data(data)
        return delta_node

    def get_raw_tree(self):
        return self._attributes

    def merge_with(self, foreign):
        self._attributes.update(foreign._attributes)

    def copy(self):
        new_node = Attributes()
        new_node.set_child_data(self._attributes.copy())
        return new_node

    #   ---leaf methods---------------------------------------------------------

    def set_child_data(self, data):
        self._attributes.update(data)

    def get_child_data(self):
        return self._attributes

    def get_filtered_data(self, keys):
        filtered = Attributes()
        attributes = self._get_filtered_entries(self._attributes, keys)
        filtered.set_child_data(attributes)
        return filtered

    #   ---web------------------------------------------------------------------

    def show(self, renderer, path=None):
        renderer.show_attributes(self, path=path)


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

    def __init__(self, abs_path=None):
        super(Node, self).__init__()
        if abs_path is None:
            abs_path = tuple()
        self._children = {}
        self._abs_path = abs_path

    def get_absolute_path(self):
        return self._abs_path

    def add_node_child(self, child):
        return self._children.setdefault(type(child), child)

    def remove_node_child(self, child):
        child_type = type(child)
        if child_type in self._children:
            del self._children[child_type]

    def get_node_container(self, default=None):
        return self._children.get(type(Container()), default)

    def get_node_numeration(self, default=None):
        return self._children.get(type(Numeration()), default)

    def get_node_attributes(self, default=None):
        return self._children.get(type(Attributes()), default)

    def get_node_children(self):
        return set(self._children.values())

    def get_comparable_node_children(self, foreign):
        # If we merge empty tree with existing one
        # abs_path is empty, thus we try foreign's one.
        # Eg. in get_filtered_tree
        if self._abs_path:
            abs_path = self._abs_path
        else:
            abs_path = foreign._abs_path
        comparable_children = set()
        for child_name in self.CHILDREN_NAMES:
            child = child_name()
            child_type = type(child)
            if self._children.get(child_type) is None \
               and foreign._children.get(child_type) is None:
                continue
            comparable_children.add(
                (abs_path, self._children.get(child_type,
                                              child), foreign._children.get(child_type, child)))
        return comparable_children

    def copy(self):
        new_node = Node(self.get_absolute_path())
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


def _compare_dicts(old_dict, new_dict):
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


def _compare_dict_keys(old_dict, new_dict):
    """
    Returns the set relationships of the keys between two dictionaries:
    - relative complement of new_dict in old_dict
    - intersection of both
    - relative complement of old_dict in new_dict
    """
    old_keys, new_keys = set(old_dict), set(new_dict)
    return old_keys - new_keys, old_keys.intersection(new_keys),\
           new_keys - old_keys


def _new_delta_tree_node(value):
    return (None, value)


def _removed_delta_tree_node(value):
    return (value, None)


def _changed_delta_tree_node(old_value, new_value):
    return (old_value, new_value)


def _identical_delta_tree_node(value):
    return (value, value)
