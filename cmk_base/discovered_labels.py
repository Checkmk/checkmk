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
from typing import Optional, Tuple, Text, List, Dict  # pylint: disable=unused-import

from cmk.utils.exceptions import MKGeneralException


class ABCDiscoveredLabels(collections.MutableMapping, object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, *args):
        super(ABCDiscoveredLabels, self).__init__()
        self._labels = {}
        for entry in args:
            self.add_label(entry)

    @abc.abstractmethod
    def add_label(self, label):
        raise NotImplementedError()

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
    def __init__(self, *args):
        self._plugin_name = {}
        super(DiscoveredHostLabels, self).__init__(*args)

    def add_label(self, label):
        # type: (HostLabel) -> None
        self._labels[label.name] = label.value
        self._plugin_name[label.name] = label.plugin_name

    # TODO: Once we redesign the hw/sw inventory plugin API check if we can
    # move it to the inventory API.
    def add_labels_to_inventory_tree(self, inventory_tree):
        """Add a label + plugin to the inventory tree
        """
        inv_labels = inventory_tree.get_list("software.applications.check_mk.host_labels:")
        for label_id, label_value in self._labels.iteritems():
            inv_labels.append({
                "label": (label_id, label_value),
                "plugin_name": self._plugin_name[label_id],
            })


class ABCLabel(object):
    """Representing a service label in Checkmk

    This class is meant to be exposed to the check API. It will be usable in
    the discovery function to create a new label like this:

    yield ServiceLabel(u"my_label_key", u"my_value")
    """

    __slots__ = ["_name", "_value"]

    def __init__(self, name, value):
        # type: (Text, Text) -> None

        if not isinstance(name, unicode):
            raise MKGeneralException("Invalid label name given: Only unicode strings are allowed")
        self._name = name

        if not isinstance(value, unicode):
            raise MKGeneralException("Invalid label value given: Only unicode strings are allowed")
        self._value = value

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    @property
    def label(self):
        return "%s:%s" % (self._name, self._value)


class ServiceLabel(ABCLabel):
    pass


class HostLabel(ABCLabel):
    """Representing a host label in Checkmk during runtime

    Besides the label itself it keeps the information which plugin discovered the host label
    """
    __slots__ = ["_plugin_name"]

    def __init__(self, name, value, plugin_name=None):
        # type: (Text, Text, Optional[str]) -> None
        super(HostLabel, self).__init__(name, value)
        self._plugin_name = plugin_name

    @property
    def plugin_name(self):
        return self._plugin_name


class DiscoveredServiceLabels(ABCDiscoveredLabels):
    """Encapsulates the discovered labels of a single service during runtime"""
    def add_label(self, label):
        # type: (ServiceLabel) -> None
        self._labels[label.name] = label.value
