#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, NamedTuple, Sequence


def section_name_of(check_plugin_name: str) -> str:
    return check_plugin_name.split(".")[0]


def maincheckify(subcheck_name: str) -> str:
    """Get new plugin name

    The new API does not know about "subchecks", so drop the dot notation.
    The validation step will prevent us from having colliding plugins.
    """
    return (subcheck_name.replace('.', '_')  # subchecks don't exist anymore
            .replace('-', '_')  # "sap.value-groups"
           )


def worst_service_state(*states: int, default: int) -> int:
    """Return the 'worst' aggregation of all states

    Integers encode service states like this:

        0 -> OK
        1 -> WARN
        2 -> CRIT
        3 -> UNKNOWN

    Unfortunately this does not reflect the order of severity, or "badness", where

        OK -> WARN -> UNKNOWN -> CRIT

    That's why this function is just not quite `max`.
    """
    return 2 if 2 in states else max(states, default=default)


class ActiveCheckResult(NamedTuple):
    state: int
    summaries: Sequence[str]
    details: Sequence[str]
    metrics: Sequence[str]

    @classmethod
    def from_subresults(cls, *subresults: 'ActiveCheckResult') -> 'ActiveCheckResult':
        states_iter, summaries_iter, details_iter, metrics_iter = zip(*subresults)
        return cls(
            state=worst_service_state(*states_iter, default=0),
            summaries=sum((list(s) for s in summaries_iter), []),
            details=sum((list(d) for d in details_iter), []),
            metrics=sum((list(m) for m in metrics_iter), []),
        )


# (un)wrap_parameters:
#
# The old "API" allowed for check plugins to discover and use all kinds of parameters:
# None, str, tuple, dict, int, ...
# The new API will only allow None and a dictionary. Since this is enforced by the API,
# we need some wrapper functions to wrap the parameters of legacy functions into a
# dictionary to pass validation. Since the merging of check parameters is quite convoluted
# (in particular if dict and non-dict values are merged), we unwrap the parameters once
# they have passed validation.
# In a brighter future all parameters ever encountered will be dicts, and these functions
# may be dropped.

_PARAMS_WRAPPER_KEY = "auto-migration-wrapper-key"


# keep return type in sync with ParametersTypeAlias
def wrap_parameters(parameters: Any) -> Mapping[str, Any]:
    """wrap the passed data structure in a dictionary, if it isn't one itself"""
    if isinstance(parameters, dict):
        return parameters
    return {_PARAMS_WRAPPER_KEY: parameters}


# keep argument parameters in sync with ParametersTypeAlias
def unwrap_parameters(parameters: Mapping[str, Any]) -> Any:
    try:
        return parameters[_PARAMS_WRAPPER_KEY]
    except KeyError:
        return parameters
