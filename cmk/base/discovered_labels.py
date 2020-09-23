#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import MutableMapping
from typing import Iterator, Any, Union, Optional, List, Dict

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import Labels, CheckPluginNameStr

HostLabelValueDict = Dict[str, Union[str, Optional[CheckPluginNameStr]]]
DiscoveredHostLabelsDict = Dict[str, HostLabelValueDict]


class ABCDiscoveredLabels(MutableMapping, metaclass=abc.ABCMeta):
    def __init__(self, *args: 'ABCLabel') -> None:
        super(ABCDiscoveredLabels, self).__init__()
        self._labels: Dict[str, Any] = {}
        for entry in args:
            self.add_label(entry)

    @abc.abstractmethod
    def add_label(self, label: 'ABCLabel') -> None:
        raise NotImplementedError()

    def is_empty(self) -> bool:
        return not self._labels

    def __getitem__(self, key: str) -> Any:
        return self._labels[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._labels[key] = value

    def __delitem__(self, key: str) -> None:
        del self._labels[key]

    def __iter__(self) -> Iterator:
        return iter(self._labels)

    def __len__(self) -> int:
        return len(self._labels)

    def to_dict(self) -> Dict:
        return self._labels

    def to_list(self) -> List:
        raise NotImplementedError()

    def __repr__(self) -> str:
        return "%s(%s)" % (self.__class__.__name__, ", ".join(repr(arg) for arg in self.to_list()))


class DiscoveredHostLabels(ABCDiscoveredLabels):  # pylint: disable=too-many-ancestors
    """Encapsulates the discovered labels of a single host during runtime"""
    @classmethod
    def from_dict(cls, dict_labels: DiscoveredHostLabelsDict) -> 'DiscoveredHostLabels':
        labels = cls()
        for k, v in dict_labels.items():
            labels.add_label(HostLabel.from_dict(k, v))
        return labels

    def __init__(self, *args: 'HostLabel') -> None:
        self._labels: Dict[str, HostLabel] = {}
        super(DiscoveredHostLabels, self).__init__(*args)

    def add_label(self, label: 'ABCLabel') -> None:
        assert isinstance(label, HostLabel)
        self._labels[label.name] = label

    def to_dict(self) -> DiscoveredHostLabelsDict:
        return {
            label.name: label.to_dict()
            for label in sorted(self._labels.values(), key=lambda x: x.name)
        }

    def to_list(self) -> List['HostLabel']:
        return sorted(self._labels.values(), key=lambda x: x.name)

    def __add__(self, other: 'DiscoveredHostLabels') -> 'DiscoveredHostLabels':
        if not isinstance(other, DiscoveredHostLabels):
            raise TypeError('%s not type DiscoveredHostLabels' % other)
        data = self.to_dict().copy()
        data.update(other.to_dict())
        return DiscoveredHostLabels.from_dict(data)


class ABCLabel:
    """Representing a label in Checkmk
    """

    __slots__ = ["_name", "_value"]

    def __init__(self, name: str, value: str) -> None:

        if not isinstance(name, str):
            raise MKGeneralException("Invalid label name given: Only unicode strings are allowed")
        self._name = name

        if not isinstance(value, str):
            raise MKGeneralException("Invalid label value given: Only unicode strings are allowed")
        self._value = value

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> str:
        return self._value

    @property
    def label(self) -> str:
        return "%s:%s" % (self._name, self._value)

    def __repr__(self):
        return "%s(%r, %r)" % (self.__class__.__name__, self._name, self._value)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError("cannot compare %s to %s" % (type(self), type(other)))
        return self.__dict__ == other.__dict__


class ServiceLabel(ABCLabel):
    pass


class HostLabel(ABCLabel):
    """Representing a host label in Checkmk during runtime

    Besides the label itself it keeps the information which plugin discovered the host label
    """
    __slots__ = ["_plugin_name"]

    @classmethod
    def from_dict(cls, name: str, dict_label: HostLabelValueDict) -> 'HostLabel':
        value = dict_label["value"]
        assert isinstance(value, str)

        plugin_name = dict_label["plugin_name"]
        assert isinstance(plugin_name, str) or plugin_name is None

        return cls(name, value, plugin_name)

    def __init__(self,
                 name: str,
                 value: str,
                 plugin_name: Optional[CheckPluginNameStr] = None) -> None:
        super(HostLabel, self).__init__(name, value)
        self._plugin_name = plugin_name

    @property
    def plugin_name(self) -> Optional[str]:
        return self._plugin_name

    @plugin_name.setter
    def plugin_name(self, plugin_name: str) -> None:
        self._plugin_name = plugin_name

    def to_dict(self) -> HostLabelValueDict:
        return {
            "value": self.value,
            "plugin_name": self.plugin_name,
        }

    def __repr__(self) -> str:
        return "HostLabel(%r, %r, plugin_name=%r)" % (self.name, self.value, self.plugin_name)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, HostLabel):
            raise TypeError('%s not type HostLabel' % other)
        return (self.name == other.name and self.value == other.value and
                self.plugin_name == other.plugin_name)

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)


class DiscoveredServiceLabels(ABCDiscoveredLabels):  # pylint: disable=too-many-ancestors
    """Encapsulates the discovered labels of a single service during runtime"""
    def __init__(self, *args: ServiceLabel) -> None:
        # TODO: Make self._labels also store ServiceLabel objects just like DiscoveredHostLabels
        self._labels: Labels = {}
        super(DiscoveredServiceLabels, self).__init__(*args)

    def add_label(self, label: ABCLabel) -> None:
        assert isinstance(label, ServiceLabel)
        self._labels[label.name] = label.value

    def to_list(self) -> List[ServiceLabel]:
        return sorted([ServiceLabel(k, v) for k, v in self._labels.items()], key=lambda x: x.name)
