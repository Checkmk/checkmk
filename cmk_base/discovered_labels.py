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
import six

from cmk.utils.exceptions import MKGeneralException


class ABCDiscoveredLabels(six.with_metaclass(abc.ABCMeta, collections.MutableMapping, object)):
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
    @classmethod
    def from_dict(cls, dict_labels):
        labels = cls()
        for k, v in dict_labels.iteritems():
            labels.add_label(HostLabel.from_dict(k, v))
        return labels

    def add_label(self, label):
        # type: (HostLabel) -> None
        self._labels[label.name] = label

    def to_dict(self):
        return {
            label.name: label.to_dict()
            for label in sorted(self._labels.itervalues(), key=lambda x: x.name)
        }

    def to_list(self):
        return [label for label in sorted(self._labels.itervalues(), key=lambda x: x.name)]

    def __add__(self, other):
        if not isinstance(other, DiscoveredHostLabels):
            raise TypeError('%s not type DiscoveredHostLabels' % other)
        data = self.to_dict().copy()
        data.update(other.to_dict())
        return DiscoveredHostLabels.from_dict(data)

    def __repr__(self):
        return "DiscoveredHostLabels(%r)" % (repr(arg) for arg in self.to_list())


class ABCLabel(object):
    """Representing a service label in Checkmk

    This class is meant to be exposed to the check API. It will be usable in
    the discovery function to create a new label like this:

    yield ServiceLabel(u"my_label_key", u"my_value")
    """

    __slots__ = ["_name", "_value"]

    def __init__(self, name, value):
        # type: (Text, Text) -> None

        if not isinstance(name, six.text_type):
            raise MKGeneralException("Invalid label name given: Only unicode strings are allowed")
        self._name = name

        if not isinstance(value, six.text_type):
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

    @classmethod
    def from_dict(cls, name, dict_label):
        return cls(name, dict_label["value"], dict_label["plugin_name"])

    def __init__(self, name, value, plugin_name=None):
        # type: (Text, Text, Optional[str]) -> None
        super(HostLabel, self).__init__(name, value)
        self._plugin_name = plugin_name

    @property
    def plugin_name(self):
        # type: () -> Optional[str]
        return self._plugin_name

    @plugin_name.setter
    def plugin_name(self, plugin_name):
        # type: (str) -> None
        self._plugin_name = plugin_name

    def to_dict(self):
        return {
            "value": self.value,
            "plugin_name": self.plugin_name,
        }

    def __repr__(self):
        return "HostLabel(%r, %r)" % (self.name, self.value)

    def __eq__(self, other):
        if not isinstance(other, HostLabel):
            raise TypeError('%s not type HostLabel' % other)
        return (self.name == other.name and self.value == other.value and
                self.plugin_name == other.plugin_name)

    def __ne__(self, other):
        if not isinstance(other, HostLabel):
            raise TypeError('%s not type HostLabel' % other)
        return (self.name != other.name or self.value != other.value or
                self.plugin_name != other.plugin_name)


class DiscoveredServiceLabels(ABCDiscoveredLabels):
    """Encapsulates the discovered labels of a single service during runtime"""
    def add_label(self, label):
        # type: (ServiceLabel) -> None
        self._labels[label.name] = label.value
