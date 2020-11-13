#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
#TODO included in typing since Python >= 3.8
from typing_extensions import TypedDict

import cmk.utils.paths

DiagnosticsCLParameters = List[str]
DiagnosticsModesParameters = Dict[str, Any]
DiagnosticsOptionalParameters = Dict[str, Any]
DiagnosticsParameters = TypedDict("DiagnosticsParameters", {
    "site": str,
    "general": None,
    "opt_info": Optional[DiagnosticsOptionalParameters],
})
CheckmkFilesMap = Dict[str, Path]

OPT_LOCAL_FILES = "local-files"
OPT_OMD_CONFIG = "omd-config"
OPT_CHECKMK_OVERVIEW = "checkmk-overview"
OPT_CHECKMK_CONFIG_FILES = "checkmk-config-files"
OPT_CHECKMK_LOG_FILES = "checkmk-log-files"

# CEE specific options
OPT_PERFORMANCE_GRAPHS = "performance-graphs"

_BOOLEAN_CONFIG_OPTS = [
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
    OPT_CHECKMK_OVERVIEW,
]

_FILES_OPTS = [
    OPT_CHECKMK_CONFIG_FILES,
    OPT_CHECKMK_LOG_FILES,
]


def serialize_wato_parameters(wato_parameters: DiagnosticsParameters) -> DiagnosticsCLParameters:
    opt_info_parameters = wato_parameters.get("opt_info")
    if opt_info_parameters is None:
        return []

    serialized_parameters = []
    for key, value in opt_info_parameters.items():
        if key in _BOOLEAN_CONFIG_OPTS and value:
            serialized_parameters.append(key)

        elif key in _FILES_OPTS:
            serialized_parameters.append(key)
            _ty, list_of_files = value
            serialized_parameters.append(",".join(list_of_files))

    return serialized_parameters


def deserialize_cl_parameters(
        cl_parameters: DiagnosticsCLParameters) -> DiagnosticsOptionalParameters:
    if cl_parameters is None:
        return {}

    deserialized_parameters: DiagnosticsOptionalParameters = {}
    parameters = iter(cl_parameters)
    while True:
        try:
            parameter = next(parameters)
            if parameter in _BOOLEAN_CONFIG_OPTS:
                deserialized_parameters[parameter] = True

            elif parameter in _FILES_OPTS:
                deserialized_parameters[parameter] = next(parameters).split(",")

        except StopIteration:
            break

    return deserialized_parameters


def deserialize_modes_parameters(
        modes_parameters: DiagnosticsModesParameters) -> DiagnosticsOptionalParameters:
    deserialized_parameters = {}
    for key, value in modes_parameters.items():
        if key in _BOOLEAN_CONFIG_OPTS:
            deserialized_parameters[key] = value

        elif key in _FILES_OPTS:
            deserialized_parameters[key] = value.split(",")

    return deserialized_parameters


def get_checkmk_config_files_map() -> CheckmkFilesMap:
    files_map: CheckmkFilesMap = {}
    for root, _dirs, files in os.walk(cmk.utils.paths.default_config_dir):
        for file_name in files:
            if file_name == "ca-certificates.mk":
                continue
            filepath = Path(root).joinpath(file_name)
            if filepath.suffix in (".mk", ".conf") or filepath.name == ".wato":
                rel_filepath = str(filepath.relative_to(cmk.utils.paths.default_config_dir))
                files_map.setdefault(rel_filepath, filepath)
    return files_map


def get_checkmk_log_files_map() -> CheckmkFilesMap:
    files_map: CheckmkFilesMap = {}
    for root, _dirs, files in os.walk(cmk.utils.paths.log_dir):
        for file_name in files:
            filepath = Path(root).joinpath(file_name)
            if filepath.suffix in (".log", ".state") or filepath.name == "stats":
                rel_filepath = str(filepath.relative_to(cmk.utils.paths.log_dir))
                files_map.setdefault(rel_filepath, filepath)
    return files_map
