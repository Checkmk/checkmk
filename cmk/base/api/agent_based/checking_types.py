#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Types and classes used by the API for check plugins
"""
from typing import List, Optional
import sys
import collections

from cmk.base.discovered_labels import ServiceLabel


class Parameters(collections.abc.Mapping):
    """Parameter objects are used to pass parameters to discover and check functions"""
    def __init__(self, data):
        if not isinstance(data, dict):
            raise TypeError("Parameters expected dict, got %r" % (data,))
        self._data = dict(data)

    def __getitem__(self, key):
        return self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._data)


class Service:
    """This class represents services that the discover function yields

    my_drive_service = Service(
        item="disc_name",
        parameters={...},
        labels=[ServiceLabel(...)],
    )
    """
    def __init__(self, *, item=None, parameters=None, labels=None):
        # type: (Optional[str], Optional[Parameters], Optional[List[ServiceLabel]]) -> None
        self._item = item
        self._parameters = parameters
        self._labels = labels or []

        self._validate_item(item)
        self._validate_parameters(parameters)
        self._validate_labels(labels)

    @staticmethod
    def _validate_item(item):
        if item is None:
            return
        if not isinstance(item, str):
            raise TypeError("'item' must be string, got %r" % (item,))

    @staticmethod
    def _validate_parameters(parameters):
        if parameters is None:
            return
        if not isinstance(parameters, dict):
            raise TypeError("'parameters' must be dict, got %r" % (parameters,))

    @staticmethod
    def _validate_labels(labels):
        if labels is None:
            return
        if not (isinstance(labels, list) and all(isinstance(l, ServiceLabel) for l in labels)):
            raise TypeError("'labels' must be list of ServiceLabels, got %r" % (labels,))

    @property
    def item(self):
        return self._item

    @property
    def parameters(self):
        return self._parameters

    @property
    def labels(self):
        return self._labels

    def __repr__(self):
        return "%s(item=%r, parameters=%r, labels=%r)" % (self.__class__.__name__, self.item,
                                                          self.parameters, self._labels)


class MetricFloat(float):
    """Extends the float representation for Infinities in such way that
    they can be parsed by eval"""
    def __repr__(self):
        # type: () -> str
        if self > sys.float_info.max:
            return '1e%d' % (sys.float_info.max_10_exp + 1)
        if self < -1 * sys.float_info.max:
            return '-1e%d' % (sys.float_info.max_10_exp + 1)
        return super(MetricFloat, self).__repr__()
