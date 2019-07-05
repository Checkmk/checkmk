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
from typing import Text, List, Dict  # pylint: disable=unused-import

from cmk.utils.exceptions import MKGeneralException


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


class ServiceLabel(object):
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


class DiscoveredServiceLabels(ABCDiscoveredLabels):
    """Encapsulates the discovered labels of a single service during runtime"""
    def add_label(self, label):
        # type: (ServiceLabel) -> None
        self._labels[label.name] = label.value


class DiscoveredServiceLabelsOfHost(object):
    """Manages the discovered labels of all services of one host

    During the service discovery in Checkmk base code, this class
    is used to collect all discovered labels.
    """
    __slots__ = ["_service_labels"]

    def __init__(self, **kwargs):
        super(DiscoveredServiceLabelsOfHost, self).__init__()
        self._service_labels = kwargs  # type: Dict[Text, DiscoveredServiceLabels]

    def add_label(self, service_desc, label):
        # type: (Text, ServiceLabel) -> None
        if service_desc not in self._service_labels:
            service_labels = self._service_labels[service_desc] = DiscoveredServiceLabels()
        else:
            service_labels = self._service_labels[service_desc]
        service_labels.add_label(label)

    def to_dict(self):
        return {
            service_descr: service_labels.to_dict()
            for service_descr, service_labels in self._service_labels.items()
        }
