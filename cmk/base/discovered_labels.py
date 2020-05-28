#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import MutableMapping
from typing import Iterator, Any, Union, Optional, List, Dict

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import Labels, CheckPluginName

HostLabelValueDict = Dict[str, Union[str, Optional[CheckPluginName]]]
DiscoveredHostLabelsDict = Dict[str, HostLabelValueDict]


class ABCDiscoveredLabels(MutableMapping, object, metaclass=abc.ABCMeta):
    def __init__(self, *args):
        # type: (ABCLabel) -> None
        super(ABCDiscoveredLabels, self).__init__()
        self._labels = {}  # type: Dict[str, Any]
        for entry in args:
            self.add_label(entry)

    @abc.abstractmethod
    def add_label(self, label):
        # type: (ABCLabel) -> None
        raise NotImplementedError()

    def is_empty(self):
        # type: () -> bool
        return not self._labels

    def __getitem__(self, key):
        # type: (str) -> Any
        return self._labels[key]

    def __setitem__(self, key, value):
        # type: (str, Any) -> None
        self._labels[key] = value

    def __delitem__(self, key):
        # type: (str) -> None
        del self._labels[key]

    def __iter__(self):
        # type: () -> Iterator
        return iter(self._labels)

    def __len__(self):
        # type: () -> int
        return len(self._labels)

    def to_dict(self):
        # type: () -> Dict
        return self._labels


class DiscoveredHostLabels(ABCDiscoveredLabels):  # pylint: disable=too-many-ancestors
    """Encapsulates the discovered labels of a single host during runtime"""
    @classmethod
    def from_dict(cls, dict_labels):
        # type: (DiscoveredHostLabelsDict) -> DiscoveredHostLabels
        labels = cls()
        for k, v in dict_labels.items():
            labels.add_label(HostLabel.from_dict(k, v))
        return labels

    def __init__(self, *args):
        # type: (HostLabel) -> None
        self._labels = {}  # type: Dict[str, HostLabel]
        super(DiscoveredHostLabels, self).__init__(*args)

    def add_label(self, label):
        # type: (ABCLabel) -> None
        assert isinstance(label, HostLabel)
        self._labels[label.name] = label

    def to_dict(self):
        # type: () -> DiscoveredHostLabelsDict
        return {
            label.name: label.to_dict()
            for label in sorted(self._labels.values(), key=lambda x: x.name)
        }

    def to_list(self):
        # type: () -> List[HostLabel]
        return sorted(self._labels.values(), key=lambda x: x.name)

    def __add__(self, other):
        # type: (DiscoveredHostLabels) -> DiscoveredHostLabels
        if not isinstance(other, DiscoveredHostLabels):
            raise TypeError('%s not type DiscoveredHostLabels' % other)
        data = self.to_dict().copy()
        data.update(other.to_dict())
        return DiscoveredHostLabels.from_dict(data)

    def __repr__(self):
        # type: () -> str
        return "DiscoveredHostLabels(%s)" % ", ".join(repr(arg) for arg in self.to_list())


class ABCLabel(object):  # pylint: disable=useless-object-inheritance
    """Representing a label in Checkmk
    """

    __slots__ = ["_name", "_value"]

    def __init__(self, name, value):
        # type: (str, str) -> None

        if not isinstance(name, str):
            raise MKGeneralException("Invalid label name given: Only unicode strings are allowed")
        self._name = name

        if not isinstance(value, str):
            raise MKGeneralException("Invalid label value given: Only unicode strings are allowed")
        self._value = value

    @property
    def name(self):
        # type: () -> str
        return self._name

    @property
    def value(self):
        # type: () -> str
        return self._value

    @property
    def label(self):
        # type: () -> str
        return "%s:%s" % (self._name, self._value)

    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self._name, self._value)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError("cannot compare %s to %s" % (type(self), type(other)))
        return self.__dict__ == other.__dict__


class ServiceLabel(ABCLabel):
    # This docstring is exposed by the agent_based API!
    """Representing a service label in Checkmk

    This class creates a service label that can be passed to a 'Service' object.
    It can be used in the discovery function to create a new label like this:

    my_label = ServiceLabel(u"my_label_key", u"my_value")
    """


class HostLabel(ABCLabel):
    """Representing a host label in Checkmk during runtime

    Besides the label itself it keeps the information which plugin discovered the host label
    """
    __slots__ = ["_plugin_name"]

    @classmethod
    def from_dict(cls, name, dict_label):
        # type: (str, HostLabelValueDict) -> HostLabel
        value = dict_label["value"]
        assert isinstance(value, str)

        plugin_name = dict_label["plugin_name"]
        assert isinstance(plugin_name, str) or plugin_name is None

        return cls(name, value, plugin_name)

    def __init__(self, name, value, plugin_name=None):
        # type: (str, str, Optional[CheckPluginName]) -> None
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
        # type: () -> HostLabelValueDict
        return {
            "value": self.value,
            "plugin_name": self.plugin_name,
        }

    def __repr__(self):
        # type: () -> str
        return "HostLabel(%r, %r, plugin_name=%r)" % (self.name, self.value, self.plugin_name)

    def __eq__(self, other):
        # type: (Any) -> bool
        if not isinstance(other, HostLabel):
            raise TypeError('%s not type HostLabel' % other)
        return (self.name == other.name and self.value == other.value and
                self.plugin_name == other.plugin_name)

    def __ne__(self, other):
        # type: (Any) -> bool
        return not self.__eq__(other)


class DiscoveredServiceLabels(ABCDiscoveredLabels):  # pylint: disable=too-many-ancestors
    """Encapsulates the discovered labels of a single service during runtime"""
    def __init__(self, *args):
        # type: (ServiceLabel) -> None
        self._labels = {}  # type: Labels
        super(DiscoveredServiceLabels, self).__init__(*args)

    def add_label(self, label):
        # type: (ABCLabel) -> None
        assert isinstance(label, ServiceLabel)
        self._labels[label.name] = label.value
