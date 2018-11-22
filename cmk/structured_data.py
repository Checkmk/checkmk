#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2017             mk@mathias-kettner.de |
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

"""This module handles tree structures for HW/SW inventory system and
structured monitoring data of Check_MK."""

import gzip
import re
# Just for tests
import pprint

import cmk.store as store
from cmk.exceptions import MKGeneralException, MKTimeout

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

class StructuredDataTree(object):
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


    def _validate_tree_path(self, tree_path):
        if not tree_path:
            raise MKGeneralException("Empty tree path or zero.")
        if not (isinstance(tree_path, str) or isinstance(tree_path, unicode)):
            raise MKGeneralException("Wrong tree path format. Must be of type string.")
        if not (tree_path.endswith(":") or tree_path.endswith(".")):
            raise MKGeneralException("No valid tree path.")
        if bool(re.compile('[^a-zA-Z0-9_.:-]').search(tree_path)):
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
        store.save_data_to_file(filepath, output, pretty=pretty)
        gzip.open(filepath + ".gz", "w").write(repr(output) + "\n")
        # Inform Livestatus about the latest inventory update
        store.save_file("%s/.last" % path, "")


    def load_from(self, filepath):
        raw_tree = store.load_data_from_file(filepath)
        return self.create_tree_from_raw_tree(raw_tree)


    def create_tree_from_raw_tree(self, raw_tree):
        if raw_tree:
            self._create_hierarchy_from_data(raw_tree, self._root, tuple())
        return self


    def _create_hierarchy_from_data(self, raw_tree, parent, parent_path):
        for edge, attrs in raw_tree.iteritems():
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
        leaf_data = {}
        sub_raw_tree = {}
        for k, v in raw_entries.iteritems():
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
                for k, v in entry.iteritems():
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

    def compare_with(self, old_struct_tree):
        delta = StructuredDataTree()
        new, changed, removed, delta_tree = self._root.compare_with(old_struct_tree._root)
        delta._root = delta_tree
        return new, changed, removed, delta


    def copy(self):
        new = StructuredDataTree()
        new._root = self._root.copy()
        return new


    def get_root_container(self):
        return self._root


    def get_filtered_tree(self, allowed_paths):
        if allowed_paths is None:
            return self
        filtered = StructuredDataTree()
        for path, keys in allowed_paths:
            sub_tree = self._root.get_filtered_branch(path, keys, Container())
            if sub_tree is None:
                continue
            filtered._root.merge_with(sub_tree)
        return filtered

    #   ---testing--------------------------------------------------------------

    def get_tree_repr(self):
        # Just for testing
        return self._root.get_tree_repr()


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

class NodeAttribute(object):
    """Interface for all node attributes"""

    def is_empty(self):
        raise NotImplementedError()


    def is_equal(self, foreign, edges=None):
        """At the moment 'edges' argument just allowed for root node."""
        raise NotImplementedError()


    def count_entries(self):
        raise NotImplementedError()


    def compare_with(self, old):
        """Compares new tree with old one: new_tree.compare_with(old_tree)."""
        raise NotImplementedError()


    def get_delta_tree(self, mode):
        raise NotImplementedError()


    def get_raw_tree(self):
        raise NotImplementedError()


    def normalize_nodes(self):
        raise NotImplementedError()


    def merge_with(self, node):
        raise NotImplementedError()


    def copy(self):
        raise NotImplementedError()

    #   ---testing--------------------------------------------------------------

    def get_tree_repr(self):
        # Just for testing
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
        for _, __, my_child, foreign_child in \
            self._get_comparable_children(foreign, edges=edges):
            if not my_child.is_equal(foreign_child):
                return False
        return True


    def count_entries(self):
        return sum([child.count_entries() for _, __, child in self.get_children()])


    def compare_with(self, old, keep_identical=False):
        my_edges = set(self._edges.keys())
        old_edges = set(old._edges.keys())
        new_edges = my_edges - old_edges
        removed_edges = old_edges - my_edges
        intersect_edges = my_edges.intersection(old_edges)

        delta = Container()
        new, changed, removed = 0, 0, 0
        for edge, abs_path, my_child in self.get_children(edges=new_edges):
            new_entries = my_child.count_entries()
            if new_entries:
                new += new_entries
                delta.add_child(edge, my_child.get_delta_tree(mode="new"), abs_path)

        for edge, abs_path, my_child, old_child in \
            self._get_comparable_children(old, edges=intersect_edges):
            if my_child.is_equal(old_child):
                if keep_identical:
                    delta.add_child(edge, abs_path, my_child.get_delta_tree())
                continue
            new_entries, changed_entries, removed_entries, delta_child = \
                my_child.compare_with(old_child, keep_identical=keep_identical)
            if new_entries or changed_entries or removed_entries:
                new += new_entries
                changed += changed_entries
                removed += removed_entries
                delta.add_child(edge, delta_child, abs_path)

        for edge, abs_path, old_child in old.get_children(edges=removed_edges):
            removed_entries = old_child.count_entries()
            if removed_entries:
                removed += removed_entries
                delta.add_child(edge, old_child.get_delta_tree(mode="removed"), abs_path)

        return new, changed, removed, delta


    def get_delta_tree(self, mode):
        delta = Container()
        for edge, abs_path, child in self.get_children():
            delta.add_child(edge, child.get_delta_tree(mode), abs_path)
        return delta


    def get_raw_tree(self):
        tree = {}
        for edge, _, child in self.get_children():
            child_tree = child.get_raw_tree()
            if self._is_nested_numeration_tree(child):
                tree.setdefault(edge, child_tree.values())
            elif isinstance(child, Numeration):
                tree.setdefault(edge, child_tree)
            else:
                tree.setdefault(edge, {}).update(child_tree)
        return tree


    def _is_nested_numeration_tree(self, child):
        if isinstance(child, Container):
            for key in child._edges.keys():
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
                self._set_nested_numeration_node(edge, child.get_child_data(),
                                                 abs_path)
            if child.is_empty():
                self._edges[edge].remove_node_child(child)
                continue
            child.normalize_nodes()


    def _has_nested_numeration_node(self, node_data):
        for nr, entry in enumerate(node_data):
            for k, v in entry.iteritems():
                if isinstance(v, list):
                    return True
        return False


    def _set_nested_numeration_node(self, edge, child_data, abs_path):
        del self._edges[edge]
        parent = self.add_child(edge, Container(), abs_path)
        for nr, entry in enumerate(child_data):
            attrs = {}
            for k, v in entry.iteritems():
                if isinstance(v, list):
                    numeration = parent.add_child(nr, Container(), abs_path+(nr,))\
                                       .add_child(k, Numeration(), abs_path+(nr,k))
                    numeration.set_child_data(v)
                else:
                    attrs.setdefault(k, v)
            if attrs:
                attributes = parent.add_child(nr, Attributes(), abs_path+(nr,))
                attributes.set_child_data(attrs)


    def merge_with(self, foreign):
        for edge, abs_path, my_child, foreign_child in \
            self._get_comparable_children(foreign):
            my_child = self.add_child(edge, my_child, abs_path)
            my_child.merge_with(foreign_child)


    def copy(self):
        new = Container()
        for edge, abs_path, child in self.get_children():
            new.add_child(edge, child.copy(), abs_path)
        return new

    #   ---testing--------------------------------------------------------------

    def get_tree_repr(self):
        # Just for testing
        tree = {}
        for edge, abs_path, child in self.get_children():
            tree.setdefault(edge, {'__path__': abs_path})
            key = '__%s__' % type(child).__name__[:3]
            tree[edge].setdefault(key, child.get_tree_repr())
        return tree

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
                parent.add_child(edge, filtered, sub_node_abs_path)
        else:
            if keys:
                container = sub_node.get_node_container()
                if container is not None:
                    parent.add_child(edge, container, sub_node_abs_path)

                numeration = sub_node.get_node_numeration()
                if numeration is not None:
                    filtered_numeration = numeration.get_filtered_data(keys)
                    parent.add_child(edge, filtered_numeration, sub_node_abs_path)

                attributes = sub_node.get_node_attributes()
                if attributes is not None:
                    filtered_attributes = attributes.get_filtered_data(keys)
                    parent.add_child(edge, filtered_attributes, sub_node_abs_path)
            else:
                for child in sub_node.get_node_children():
                    parent.add_child(edge, child, sub_node_abs_path)
        return parent

    #   ---getting [sub] nodes/node attributes----------------------------------

    def get_edge_nodes(self):
        return self._edges.iteritems()


    def get_children(self, edges=None):
        """Returns a flatten list of tuples (edge, absolute path, child)"""
        children = set()
        if edges is None:
            for edge, node in self._edges.iteritems():
                node_abs_path = node.get_absolute_path()
                for child in node.get_node_children():
                    children.add((edge, node_abs_path, child))
        else:
            for edge, node in self._edges.iteritems():
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
            edges = set(self._edges.keys()).union(set(foreign._edges.keys()))
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


    def _compare_entries(self, new_entries, old_entries):
        """
Format of compared entries:
  new:          {k: (None, val), ...}
  changed:      {k: (old, new), ...}
  removed:      {k: (val, None), ...}
  identical:    {k: (val, val), ...}
"""
        new_keys = set(new_entries.keys())
        old_keys = set(old_entries.keys())
        new = {k: (None, new_entries[k]) for k in (new_keys - old_keys)}
        removed = {k: (old_entries[k], None) for k in (old_keys - new_keys)}
        identical, changed = {}, {}
        for k in new_keys.intersection(old_keys):
            old_v = old_entries[k]
            new_v = new_entries[k]
            if new_v == old_v:
                identical.setdefault(k, (new_v, new_v))
            else:
                changed.setdefault(k, (old_v, new_v))
        return new, changed, removed, identical


    def _get_filtered_entries(self, entries, keys):
        filtered = {}
        for k,v in entries.iteritems():
            if k in keys:
                filtered.setdefault(k, v)
            else:
                filtered.setdefault(k, None)
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


    def is_equal(self, foreign):
        return self._numeration == foreign._numeration


    def count_entries(self):
        return sum(map(len, self._numeration))


    def compare_with(self, old, keep_identical=False):
        if len(self._numeration) == len(old._numeration):
            new, changed, removed, data = \
                self._compare_with_fixed_length(old, keep_identical=keep_identical)
        else:
            new, changed, removed, data = \
                self._compare_with_different_length(old, keep_identical=keep_identical)
        if data:
            delta = Numeration()
            delta.set_child_data(data)
        else:
            delta = None
        return new, changed, removed, delta


    def _compare_with_fixed_length(self, old, keep_identical=False):
        # In this case we assume that each entry corresponds to the
        # old one with the same index.
        new, changed, removed = 0, 0, 0
        data = []
        for my_entries, old_entries in \
            zip(self._numeration, old._numeration):
            new_entries, changed_entries, removed_entries, identical_entries = \
                self._compare_entries(my_entries, old_entries)
            new += len(new_entries)
            changed += len(changed_entries)
            removed += len(removed_entries)
            entry = {}
            for entries in [new_entries, changed_entries, removed_entries]:
                entry.update(entries)
            if keep_identical:
                entry.update(identical_entries)
            if entry:
                data.append(entry)
        return new, changed, removed, data


    def _compare_with_different_length(self, old, keep_identical=False):
        my_converted = self._convert_numeration()
        old_converted = old._convert_numeration()

        my_keys = set(my_converted.keys())
        old_keys = set(old_converted.keys())
        new_keys = my_keys - old_keys
        removed_keys = old_keys - my_keys
        intersect_keys = my_keys.intersection(old_keys)

        new, changed, removed = 0, 0, 0
        data = []
        for new_key in new_keys:
            for index in my_converted[new_key].keys():
                my_entry = self._numeration[index]
                new += len(my_entry)
                data.append({k: (None,v) for k,v in my_entry.iteritems()})

        for removed_key in removed_keys:
            for index in old_converted[removed_key].keys():
                old_entry = old._numeration[index]
                removed += len(old_entry)
                data.append({k: (v,None) for k,v in old_entry.iteritems()})

        for intersect_key in intersect_keys:
            my_entries = my_converted[intersect_key].values()
            old_entries = old_converted[intersect_key].values()
            if len(my_entries) == len(old_entries):
                data_entry = {}
                # In this case we assume that each entry corresponds to the
                # old one with the same index.
                for k, my_entry, old_entry in zip(intersect_key, my_entries, old_entries):
                    if my_entry == old_entry:
                        if keep_identical:
                            data_entry.setdefault(k, (my_entry, my_entry))
                    else:
                        data_entry.setdefault(k, (old_entry, my_entry))
                        changed += 1
                data.append(data_entry)

            else:
                my_entries = set(my_entries)
                old_entries = set(old_entries)
                new_entries = my_entries - old_entries
                removed_entries = old_entries - my_entries
                for new_entry in new_entries:
                    data.append({k: (None,v) for k,v in zip(intersect_key, new_entry)})
                for removed_entry in removed_entries:
                    data.append({k: (v,None) for k,v in zip(intersect_key, removed_entry)})
                new += len(new_entries)
                removed += len(removed_entries)
                if keep_identical:
                    for intersect_entry in my_entries.intersection(old_entries):
                        data.append({k: (v,v) for k,v in zip(intersect_key, old_entry)})
        return new, changed, removed, data


    def _convert_numeration(self):
        converted = {}
        for index, entry in enumerate(self._numeration):
            key, values = [], []
            for k,v in sorted(entry.iteritems()):
                key.append(k)
                values.append(v)
            entries = converted.setdefault(tuple(key), {})
            entries.setdefault(index, tuple(values))
        return converted


    def get_delta_tree(self, mode):
        delta = Numeration()
        data = []
        for entry in self._numeration:
            if mode == "new":
                data.append({k: (None,v) for k,v in entry.iteritems()})
            elif mode == "removed":
                data.append({k: (v,None) for k,v in entry.iteritems()})
            else:
                break
        delta.set_child_data(data)
        return delta


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
        foreign_num = {foreign._prepare_key(entry, intersect_keys): entry
                       for entry in foreign._numeration}

        for entry in self._numeration:
            key = self._prepare_key(entry, intersect_keys)
            if key in foreign_num:
                entry.update(foreign_num[key])
                del foreign_num[key]

        self._numeration += foreign_num.values()


    def _get_numeration_keys(self):
        keys = set()
        for entry in self._numeration:
            keys.update(entry.keys())
        return keys


    def _prepare_key(self, entry, keys):
        return tuple(entry[key] for key in sorted(keys) if key in entry)


    def copy(self):
        new = Numeration()
        new.set_child_data(self._numeration[:])
        return new

    #   ---testing--------------------------------------------------------------

    def get_tree_repr(self):
        # Just for testing
        return '[:]'

    #   ---leaf methods---------------------------------------------------------

    def set_child_data(self, data):
        self._numeration += data


    def get_child_data(self):
        return self._numeration


    def get_filtered_data(self, keys):
        filtered = Numeration()
        numeration = []
        for entry in self._numeration:
            numeration.append(self._get_filtered_entries(entry, keys))
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


    def is_equal(self, foreign):
        return self._attributes == foreign._attributes


    def count_entries(self):
        return len(self._attributes)


    def compare_with(self, old, keep_identical=False):
        new, changed, removed, identical = \
            self._compare_entries(self._attributes, old._attributes)
        if new or changed or removed:
            delta = Attributes()
            delta.set_child_data(new)
            delta.set_child_data(changed)
            delta.set_child_data(removed)
            if keep_identical:
                delta.set_child_data(identical)
        else:
            delta = None
        return len(new), len(changed), len(removed), delta


    def get_delta_tree(self, mode):
        delta = Attributes()
        if mode == "new":
            data = {k: (None,v) for k,v in self._attributes.iteritems()}
        elif mode == "removed":
            data = {k: (v,None) for k,v in self._attributes.iteritems()}
        else:
            data = {}
        delta.set_child_data(data)
        return delta

    def get_raw_tree(self):
        return self._attributes

    def merge_with(self, foreign):
        self._attributes.update(foreign._attributes)


    def copy(self):
        new = Attributes()
        new.set_child_data(self._attributes.copy())
        return new

    #   ---testing--------------------------------------------------------------

    def get_tree_repr(self):
        # Just for testing
        return '{:}'

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

class Node(object):
    """Node contains max. one node attribute per type."""

    CHILDREN_NAMES = [Container, Numeration, Attributes]

    def __init__(self, abs_path=None):
        super(Node, self).__init__()
        self._children = {}
        if abs_path is None:
            self._abs_path = tuple()
        else:
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
            comparable_children.add((abs_path,
                                     self._children.get(child_type, child),
                                     foreign._children.get(child_type, child)))
        return comparable_children


    def copy(self):
        new = Node(self.get_absolute_path())
        for child in self._children.values():
            new.add_node_child(child.copy())
        return new

#.
