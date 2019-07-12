#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

import abc
import collections


class ABCDiscoveredLabels(collections.MutableMapping, object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, **kwargs):
        super(ABCDiscoveredLabels, self).__init__()
        self._labels = kwargs

    def is_empty(self):
        return not self._labels

    def __getitem__(self, key):
        return self._labels[key]

    def __setitem__(self, key, value):
        self._labels[key] = value

    def __delitem__(self, key):
        del self._labels[key]

    def __iter__(self):
        return iter(self._labels)

    def __len__(self):
        return len(self._labels)

    def to_dict(self):
        return self._labels


class DiscoveredHostLabels(ABCDiscoveredLabels):
    """Encapsulates the discovered labels of a single host during runtime"""
    def __init__(self, inventory_tree, **kwargs):
        super(DiscoveredHostLabels, self).__init__(**kwargs)
        self._inventory_tree = inventory_tree

    # TODO: Once we redesign the hw/sw inventory plugin API check if we can move it to the
    # inventory API.
    def add_label(self, key, value, plugin_name):
        """Add a label to the collection of discovered labels and inventory tree

        Add it to the inventory tree for debugging purposes
        """
        self[key] = value
        labels = self._inventory_tree.get_list("software.applications.check_mk.host_labels:")
        labels.append({
            "label": (key, value),
            "inventory_plugin_name": plugin_name,
        })


class DiscoveredServiceLabels(ABCDiscoveredLabels):
    """Encapsulates the discovered labels of a single service during runtime"""
    pass
