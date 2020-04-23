#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Types and classes used by the API for check plugins
"""
from typing import Any, Callable, Dict, Generator, List, NamedTuple, Optional, Tuple, Union  # pylint: disable=unused-import
import sys
import enum

try:
    from collections.abc import Mapping  # type: ignore[import]
except ImportError:
    from collections import Mapping

from cmk.utils import pnp_cleanup as quote_pnp_string
from cmk.base.api import PluginName
from cmk.base.discovered_labels import ServiceLabel


@enum.unique
class management_board(enum.Enum):
    DISABLED = "disabled"
    EXCLUSIVE = "exclusive"


class Parameters(Mapping):
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
    def __init__(self, item=None, parameters=None, labels=None):
        # type: (Optional[str], Optional[Dict], Optional[List[ServiceLabel]]) -> None
        # TODO (mo): unhack this CMK-3983
        # all arguments should be kwarg-only
        self._item = item
        self._parameters = parameters or {}  # type: Dict[str, Any]
        self._labels = labels or []

        self._validate_item(item)
        self._validate_parameters(parameters)
        self._validate_labels(labels)

    @staticmethod
    def _validate_item(item):
        if item is None:
            return
        if not (item and isinstance(item, str)):
            raise TypeError("'item' must be non empty string, got %r" % (item,))

    @staticmethod
    def _validate_parameters(parameters):
        if parameters is None:
            return
        if not isinstance(parameters, dict):
            raise TypeError("'parameters' must be dict, got %r" % (parameters,))

    @staticmethod
    def _validate_labels(labels):
        if labels and not (isinstance(labels, list) and
                           all(isinstance(l, ServiceLabel) for l in labels)):
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

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError("cannot compare %s to %s" %
                            (self.__class__.__name__, other.__class__.__name))
        return all((
            self.item == other.item,
            self.parameters == other.parameters,
            self.labels == other.labels,
        ))

    def __repr__(self):
        return "%s(item=%r, parameters=%r, labels=%r)" % (self.__class__.__name__, self.item,
                                                          self.parameters, self._labels)


@enum.unique
class state(enum.Enum):
    # Don't use IntEnum to prevent "state.CRIT < state.UNKNOWN" from evaluating to True.
    OK = 0
    WARN = 1
    CRIT = 2
    UNKNOWN = 3

    def __int__(self):
        return int(self.value)


def state_worst(*args):
    # type: (*state) -> state
    """Returns the worst of all passed states

    You can pass an arbitrary number of arguments, and the return value will be
    the "worst" of them, where

        `OK < WARN < UNKNOWN < CRIT`
    """
    # we are nice, and handle ints and None as well (although mypy wouldn't allow it)
    if state.CRIT in args or 2 in args:
        return state.CRIT
    return state(max(int(s or 0) for s in args))


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


class Metric:
    @staticmethod
    def validate_name(metric_name):
        # this is not very elegant, but it ensures consistency to cmk.utils.misc.pnp_cleanup
        pnp_name = quote_pnp_string(metric_name)
        if metric_name != pnp_name:
            offenders = ''.join(set(metric_name) - set(pnp_name))
            raise TypeError("invalid character(s) in metric name: %r" % offenders)

    @staticmethod
    def _sanitize_single_value(field, value):
        # (str, Optional[float]) -> Optional[MetricFloat]
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return MetricFloat(value)
        raise TypeError("%s values for metric must be float, int or None" % field)

    def _sanitize_optionals(self, field, values):
        # (str, Tuple[Optional[float], Optional[float]]) -> Tuple[Optional[MetricFloat], Optional[MetricFloat]]
        if not isinstance(values, tuple) or len(values) != 2:
            raise TypeError("%r for metric must be a 2-tuple" % field)

        return tuple(self._sanitize_single_value(field, v) for v in values)

    def __init__(
            self,
            name,  # type: str
            value,  # type: float
            # *args,  # type: str  # *, # type shoud be "nothing"
        levels=(None, None),  # type: Tuple[Optional[float], Optional[float]]
            boundaries=(None, None),  # type: Tuple[Optional[float], Optional[float]]
    ):
        # type: (...) -> None
        # if args:
        #    # TODO (mo): unhack this CMK-3983
        #    raise TypeError()

        self.validate_name(name)

        if not isinstance(value, (int, float)):
            raise TypeError("value for metric must be float or int, got %r" % (value,))

        self._name = name
        self._value = MetricFloat(value)
        self._levels = self._sanitize_optionals('levels', levels)
        self._boundaries = self._sanitize_optionals('boundaries', boundaries)

    @property
    def name(self):
        # type: () -> str
        return self._name

    @property
    def value(self):
        # type: () -> MetricFloat
        return self._value

    @property
    def levels(self):
        # () -> Tuple[Optional[MetricFloat], Optional[MetricFloat]]
        return self._levels

    @property
    def boundaries(self):
        # () -> Tuple[Optional[MetricFloat], Optional[MetricFloat]]
        return self._boundaries

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError("cannot compare %s to %s" %
                            (self.__class__.__name__, other.__class__.__name))
        return all((
            self.name == other.name,
            self.value == other.value,
            self.levels == other.levels,
            self.boundaries == other.boundaries,
        ))

    def __repr__(self):
        return "%s(%r, %r, levels=%r, boundaries=%r)" % (self.__class__.__name__, self.name,
                                                         self.value, self.levels, self.boundaries)


class Result(NamedTuple("ResultTuple", [
    ("state", state),
    ("summary", str),
    ("details", str),
])):

    _state_class = state  # avoid shadowing by keyword called "state"

    def __new__(cls, summary=None, details=None, state=None):  # pylint: disable=redefined-outer-name
        # type: (Optional[str], Optional[str], Optional[state]) -> Result
        # TODO (mo): unhack this CMK-3983
        # all arguments should be kwarg-only
        for var, name, type_ in (
            (summary, "summary", str),
            (details, "details", str),
            (state, "state", cls._state_class),
        ):
            if var is not None and not isinstance(var, type_):
                raise TypeError("%r must be %s or None, got %r" % (name, type_, var))
        if summary and '\n' in summary:
            raise ValueError("'\n' not allowed in 'summary'")
        if not (details or summary):
            raise ValueError("at least 'details' or 'summary' is required")
        if details and summary:
            if not len(details) > len(summary):
                raise ValueError("'summary' should be shorter than 'details'")

        return super(Result, cls).__new__(
            cls,
            state=cls._state_class(state or cls._state_class.OK),
            summary=summary or "",
            details=details or "",
        )


class IgnoreResultsError(RuntimeError):
    pass


class IgnoreResults:
    pass


DiscoveryFunction = Callable[..., Generator[Service, None, None]]

CheckFunction = Callable[..., Generator[Union[Result, Metric, IgnoreResults], None, None]]

CheckPlugin = NamedTuple("CheckPlugin", [
    ("name", PluginName),
    ("sections", List[PluginName]),
    ("service_name", str),
    ("management_board", Optional[management_board]),
    ("discovery_function", DiscoveryFunction),
    ("discovery_default_parameters", Optional[Dict]),
    ("discovery_ruleset_name", Optional[PluginName]),
    ("check_function", CheckFunction),
    ("check_default_parameters", Optional[Dict]),
    ("check_ruleset_name", Optional[PluginName]),
    ("cluster_check_function", CheckFunction),
])
