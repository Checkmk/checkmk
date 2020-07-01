#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Types and classes used by the API for check plugins
"""
import enum
from collections.abc import Mapping
from typing import Any, Callable, Dict, Generator, List, NamedTuple, Optional, Tuple, Union

from cmk.utils import pnp_cleanup as quote_pnp_string
from cmk.utils.type_defs import EvalableFloat, ParsedSectionName, CheckPluginName, RuleSetName

from cmk.base.discovered_labels import ServiceLabel

# we may have 0/None for min/max for instance.
_OptionalPair = Optional[Tuple[Optional[float], Optional[float]]]


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
    def __init__(self,
                 *,
                 item: Optional[str] = None,
                 parameters: Optional[Dict] = None,
                 labels: Optional[List[ServiceLabel]] = None) -> None:
        self._item = item
        self._parameters: Dict[str, Any] = parameters or {}
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


def state_worst(*args: state) -> state:
    """Returns the worst of all passed states

    You can pass an arbitrary number of arguments, and the return value will be
    the "worst" of them, where

        `OK < WARN < UNKNOWN < CRIT`
    """
    # we are nice, and handle ints and None as well (although mypy wouldn't allow it)
    if state.CRIT in args or 2 in args:  # type: ignore[comparison-overlap]
        return state.CRIT
    return state(max(int(s or 0) for s in args))


class Metric:
    @staticmethod
    def validate_name(metric_name):
        if not metric_name:
            raise TypeError("metric name must not be empty")

        # this is not very elegant, but it ensures consistency to cmk.utils.misc.pnp_cleanup
        pnp_name = quote_pnp_string(metric_name)
        if metric_name != pnp_name:
            offenders = ''.join(set(metric_name) - set(pnp_name))
            raise TypeError("invalid character(s) in metric name: %r" % offenders)

    @staticmethod
    def _sanitize_single_value(field: str, value: Optional[float]) -> Optional[EvalableFloat]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return EvalableFloat(value)
        raise TypeError("%s values for metric must be float, int or None" % field)

    def _sanitize_optionals(
        self,
        field: str,
        values: _OptionalPair,
    ) -> Tuple[Optional[EvalableFloat], Optional[EvalableFloat]]:
        if values is None:
            return None, None

        if not isinstance(values, tuple) or len(values) != 2:
            raise TypeError("%r for metric must be a 2-tuple" % field)

        return (
            self._sanitize_single_value(field, values[0]),
            self._sanitize_single_value(field, values[1]),
        )

    def __init__(
        self,
        name: str,
        value: float,
        *,
        levels: _OptionalPair = None,
        boundaries: _OptionalPair = None,
    ) -> None:
        self.validate_name(name)

        if not isinstance(value, (int, float)):
            raise TypeError("value for metric must be float or int, got %r" % (value,))

        self._name = name
        self._value = EvalableFloat(value)
        self._levels = self._sanitize_optionals('levels', levels)
        self._boundaries = self._sanitize_optionals('boundaries', boundaries)

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> EvalableFloat:
        return self._value

    @property
    def levels(self):
        # () -> Tuple[Optional[EvalableFloat], Optional[EvalableFloat]]
        return self._levels

    @property
    def boundaries(self):
        # () -> Tuple[Optional[EvalableFloat], Optional[EvalableFloat]]
        return self._boundaries

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError("cannot compare %s to %s" %
                            (self.__class__.__name__, other.__class__.__name__))
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

    def __new__(  # pylint: disable=redefined-outer-name
        cls,
        *,
        state: state,
        summary: Optional[str] = None,
        notice: Optional[str] = None,
        details: Optional[str] = None,
    ) -> 'Result':
        if not isinstance(state, cls._state_class):
            raise TypeError("'state' must be a checkmk state constant, got %r" % (state,))

        for var, name in (
            (summary, "summary"),
            (notice, "notice"),
            (details, "details"),
        ):
            if var is not None and not isinstance(var, str):
                raise TypeError("%r must be non-empty str or None, got %r" % (name, var))
            if var == "":
                raise ValueError("%r must be non-empty str or None, got %r" % (name, var))

        if summary and notice:
            raise TypeError("'summary' and 'notice' are mutually exclusive arguments")

        if not any((summary, notice, details)):
            raise TypeError("at least 'summary', 'notice' or 'details' is required")

        if summary and '\n' in summary:
            raise ValueError("'\n' not allowed in 'summary'")

        if notice and '\n' in notice:
            raise ValueError("'\n' not allowed in 'notice'")

        if not details:
            details = summary or notice

        if not summary:
            summary = notice if notice and state != cls._state_class.OK else ""

        assert details is not None  # makes mypy happy

        return super(Result, cls).__new__(
            cls,
            state=state,
            summary=summary,
            details=details,
        )


class IgnoreResultsError(RuntimeError):
    pass


class IgnoreResults:
    def __init__(self, value: str = "currently no results") -> None:
        self._value = value

    def __repr__(self) -> str:
        return "%s(%r)" % (self.__class__.__name__, self._value)

    def __str__(self) -> str:
        return self._value if isinstance(self._value, str) else repr(self._value)


DiscoveryFunction = Callable[..., Generator[Service, None, None]]

CheckFunction = Callable[..., Generator[Union[Result, Metric, IgnoreResults], None, None]]

CheckPlugin = NamedTuple("CheckPlugin", [
    ("name", CheckPluginName),
    ("sections", List[ParsedSectionName]),
    ("service_name", str),
    ("discovery_function", DiscoveryFunction),
    ("discovery_default_parameters", Dict[str, Any]),
    ("discovery_ruleset_name", Optional[RuleSetName]),
    ("check_function", CheckFunction),
    ("check_default_parameters", Dict[str, Any]),
    ("check_ruleset_name", Optional[RuleSetName]),
    ("cluster_check_function", CheckFunction),
])
