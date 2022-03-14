# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import TypedDict, List, Any, Dict

SearchConfig = Dict[str, Any]

ActionConfig = Dict[str, Any]

NodeDict = TypedDict(
    "NodeDict",
    {
        "search": SearchConfig,
        "action": ActionConfig,
    },
)

GroupConfigDict = TypedDict(
    "GroupConfigDict",
    {
        "names": List[str],
        "paths": List[List[str]],
    },
)

ComputationConfigDict = TypedDict(
    "ComputationConfigDict",
    {
        "disabled": bool,
        "use_hard_states": bool,
        "escalate_downtimes_as_warn": bool,
    },
)

AggrConfigDict = TypedDict(
    "AggrConfigDict",
    {
        "id": Any,
        "comment": str,
        "customer": Any,
        "groups": GroupConfigDict,
        "node": NodeDict,
        "computation_options": ComputationConfigDict,
        "aggregation_visualization": Any,
    },
    total=True,
)
