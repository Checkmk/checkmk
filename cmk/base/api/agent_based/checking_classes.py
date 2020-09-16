#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Classes used by the API for check plugins
"""
import enum
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

from cmk.utils import pnp_cleanup as quote_pnp_string
from cmk.utils.type_defs import EvalableFloat

from cmk.base.discovered_labels import ServiceLabel

from cmk.base.api.agent_based.type_defs import ABCCheckGenerated, ABCDiscoveryGenerated

# we may have 0/None for min/max for instance.
_OptionalPair = Optional[Tuple[Optional[float], Optional[float]]]


class Service(ABCDiscoveryGenerated):
    """Class representing services that the discover function yields

    Args:
        item (str): The item of the service
        parameters (dict): The determined discovery parameters for this service
        labels (List[ServiceLabel]): A list of labels attached to this service

    Example:
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
    def item(self) -> Optional[str]:
        return self._item

    @property
    def parameters(self) -> Dict[str, Any]:
        return self._parameters

    @property
    def labels(self) -> List[ServiceLabel]:
        return self._labels

    def __repr__(self) -> str:
        return "%s(item=%r, parameters=%r, labels=%r)" % (self.__class__.__name__, self.item,
                                                          self.parameters, self._labels)


@enum.unique
class state(enum.Enum):
    """States of check results
    """
    # Don't use IntEnum to prevent "state.CRIT < state.UNKNOWN" from evaluating to True.
    OK = 0
    WARN = 1
    CRIT = 2
    UNKNOWN = 3

    def __int__(self):
        return int(self.value)

    @classmethod
    def best(cls, *args: Union['state', int]) -> 'state':
        """Returns the best of all passed states

        You can pass an arbitrary number of arguments, and the return value will be
        the "best" of them, where

            `OK -> WARN -> UNKNOWN -> CRIT`

        Args:
            args: Any number of either one of state.OK, state.WARN, state.CRIT, state.UNKNOWN or an
            integer in [0, 3].

        Returns:
            The best of the input states, one of state.OK, state.WARN, state.CRIT, state.UNKNOWN.

        Examples:
            >>> state.best(state.OK, state.WARN, state.CRIT, state.UNKNOWN)
            <state.OK: 0>
            >>> state.best(0, 1, state.CRIT)
            <state.OK: 0>
        """
        _sorted = {
            cls.OK: 0,
            cls.WARN: 1,
            cls.UNKNOWN: 2,
            cls.CRIT: 3,
        }

        # we are nice and handle ints
        best = min(
            (cls(int(s)) for s in args),
            key=_sorted.get,
        )

        return best

    @classmethod
    def worst(cls, *args: Union['state', int]) -> 'state':
        """Returns the worst of all passed states.

        You can pass an arbitrary number of arguments, and the return value will be
        the "worst" of them, where

            `OK < WARN < UNKNOWN < CRIT`

        Args:
            args: Any number of either one of state.OK, state.WARN, state.CRIT, state.UNKNOWN or an
            integer in [0, 3].

        Returns:
            The worst of the input states, one of state.OK, state.WARN, state.CRIT, state.UNKNOWN.

        Examples:
            >>> state.worst(state.OK, state.WARN, state.CRIT, state.UNKNOWN)
            <state.CRIT: 2>
            >>> state.worst(0, 1, state.CRIT)
            <state.CRIT: 2>
        """
        if cls.CRIT in args or 2 in args:
            return cls.CRIT
        return cls(max(int(s) for s in args))


class Metric(ABCCheckGenerated):
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
    def levels(self) -> Tuple[Optional[EvalableFloat], Optional[EvalableFloat]]:
        return self._levels

    @property
    def boundaries(self) -> Tuple[Optional[EvalableFloat], Optional[EvalableFloat]]:
        return self._boundaries

    def __repr__(self):
        return "%s(%r, %r, levels=%r, boundaries=%r)" % (self.__class__.__name__, self.name,
                                                         self.value, self.levels, self.boundaries)


class Result(ABCCheckGenerated,
             NamedTuple("ResultTuple", [
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
            raise ValueError("'\\n' not allowed in 'summary'")

        if notice and '\n' in notice:
            raise ValueError("'\\n' not allowed in 'notice'")

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


class IgnoreResults(ABCCheckGenerated):
    def __init__(self, value: str = "currently no results") -> None:
        self._value = value

    def __repr__(self) -> str:
        return "%s(%r)" % (self.__class__.__name__, self._value)

    def __str__(self) -> str:
        return self._value if isinstance(self._value, str) else repr(self._value)
