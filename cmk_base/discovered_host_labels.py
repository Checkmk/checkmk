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

import collections
from typing import Dict  # pylint: disable=unused-import
from pathlib2 import Path  # pylint: disable=unused-import

import cmk.utils.paths
import cmk.utils.store


class DiscoveredHostLabelsStore(object):
    """Managing persistance of discovered host labels"""

    def __init__(self, hostname):
        # type: (str) -> None
        self._hostname = hostname

    @property
    def file_path(self):
        # type () -> Path
        return (cmk.utils.paths.discovered_host_labels_dir / self._hostname).with_suffix(".mk")

    def load(self):
        # type: () -> Dict
        return cmk.utils.store.load_data_from_file(str(self.file_path), default={})

    def save(self, labels):
        # type: (Dict) -> None
        if not labels and self.file_path.exists():  # pylint: disable=no-member
            self.file_path.unlink()  # pylint: disable=no-member
            return

        self.file_path.parent.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member
        cmk.utils.store.save_data_to_file(str(self.file_path), labels)


class DiscoveredHostLabels(collections.MutableMapping, object):
    """Encapsulates the discovered labels of a single host during runtime"""

    def __init__(self, inventory_tree, **kwargs):
        super(DiscoveredHostLabels, self).__init__()
        self._inventory_tree = inventory_tree
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
