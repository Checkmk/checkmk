#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (  # pylint: disable=unused-import
    Dict, List, Optional, Any,
)
#TODO included in typing since Python >= 3.8
from typing_extensions import TypedDict

DiagnosticsCLParameters = List[str]
DiagnosticsOptionalParameters = Dict[str, Any]
DiagnosticsParameters = TypedDict("DiagnosticsParameters", {
    "site": str,
    "general": None,
    "opt_info": Optional[DiagnosticsOptionalParameters],
})

OPT_LOCAL_FILES = "local-files"
OPT_OMD_CONFIG = "omd-config"
_BOOLEAN_CONFIG_OPTS = [
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
]


def serialize_wato_parameters(wato_parameters):
    # type: (DiagnosticsParameters) -> DiagnosticsCLParameters
    opt_info_parameters = wato_parameters.get("opt_info")
    if opt_info_parameters is None:
        return []

    serialized_parameters = []
    for key, value in opt_info_parameters.items():
        if key in _BOOLEAN_CONFIG_OPTS and value:
            serialized_parameters.append(key)

    return serialized_parameters


def deserialize_cl_parameters(cl_parameters):
    # type: (DiagnosticsCLParameters) -> DiagnosticsOptionalParameters
    if cl_parameters is None:
        return {}

    deserialized_parameters = {}
    for key in cl_parameters:
        if key in _BOOLEAN_CONFIG_OPTS:
            deserialized_parameters[key] = True

    return deserialized_parameters
