#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import Iterator, Any, Union, Optional, Text, List, Dict  # pylint: disable=unused-import

try:
    # Python has a totally braindead history of changes in this area:
    #   * In the dark ages: Hmmm, one can't subclass dict, so we have to provide UserDict.
    #   * Python 2.2: Well, now we can subclass dict, but let's keep UserDict.
    #   * Python 2.3: Actually, DictMixin might often be a better idea.
    #   * Python 2.6: It is recommended to use collections.MutableMapping instead of DictMixin.
    #   * Python 3.0: UserDict is gone...
    #   * Python 3.3: Let's just move the ABCs from collections to collections.abc, keeping the old stuff for now.
    #   * Python 3.8: To *really* annoy people, let's nuke the ABCs from collection! >:-)
    from collections.abc import MutableMapping  # type: ignore[import]
except ImportError:
    from collections import MutableMapping

import six

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import Labels, CheckPluginName  # pylint: disable=unused-import

HostLabelValueDict = Dict[str, Union[Text, Optional[CheckPluginName]]]
DiscoveredHostLabelsDict = Dict[Text, HostLabelValueDict]


class ABCDiscoveredLabels(six.with_metaclass(abc.ABCMeta, MutableMapping, object)):
    def __init__(self, *args):
        # type: (ABCLabel) -> None
        super(ABCDiscoveredLabels, self).__init__()
        self._labels = {}  # type: Dict[Text, Any]
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
        # type: (Text) -> Any
        return self._labels[key]

    def __setitem__(self, key, value):
        # type: (Text, Any) -> None
        self._labels[key] = value

    def __delitem__(self, key):
        # type: (Text) -> None
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
        self._labels = {}  # type: Dict[Text, HostLabel]
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
        # type: () -> Text
        return self._name

    @property
    def value(self):
        # type: () -> Text
        return self._value

    @property
    def label(self):
        # type: () -> Text
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
        # type: (Text, HostLabelValueDict) -> HostLabel
        value = dict_label["value"]
        assert isinstance(value, six.text_type)

        plugin_name = dict_label["plugin_name"]
        assert isinstance(plugin_name, str) or plugin_name is None

        return cls(name, value, plugin_name)

    def __init__(self, name, value, plugin_name=None):
        # type: (Text, Text, Optional[CheckPluginName]) -> None
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
