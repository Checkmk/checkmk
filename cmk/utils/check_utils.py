#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


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

    Examples:

    >>> worst_service_state(0, 0, default=0)  # OK
    0
    >>> worst_service_state(0, 1, default=0)  # WARN
    1
    >>> worst_service_state(0, 1, 2, 3, default=0)  # CRIT
    2
    >>> worst_service_state(0, 1, 3, default=0)  # UNKNOWN
    3
    >>> worst_service_state(default=0)
    0
    >>> worst_service_state(default=1)
    1
    >>> worst_service_state(default=2)
    2
    >>> worst_service_state(default=3)
    3

    """
    return 2 if 2 in states else max(states, default=default)


def section_name_of(check_plugin_name: str) -> str:
    return check_plugin_name.split(".")[0]


def maincheckify(subcheck_name: str) -> str:
    """Get new plugin name

    The new API does not know about "subchecks", so drop the dot notation.
    The validation step will prevent us from having colliding plugins.
    """
    return subcheck_name.replace(".", "_").replace(  # subchecks don't exist anymore
        "-", "_"
    )  # "sap.value-groups"


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
    if set(parameters) == {_PARAMS_WRAPPER_KEY}:
        return parameters[_PARAMS_WRAPPER_KEY]
    # Note: having *both* the wrapper key and other keys can only happen, if we
    # merge wrapped (non dict) legacy parameters with newer configured (dict) parameters.
    # In this case the the plugin can deal with dicts, and will ignore the wrapper key anyway.
    # Still: cleaning it up here is less confusing.
    return {k: v for k, v in parameters.items() if k != _PARAMS_WRAPPER_KEY}
