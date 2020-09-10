#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict, Optional, Sequence
import json

from ..agent_based_api.v1.type_defs import AgentStringTable


def json_get_obj(line: Sequence[str]) -> Any:
    '''return one json object (or None)'''
    try:
        return json.loads(" ".join(line))
    except ValueError:
        return None


def get_version(string_table: AgentStringTable) -> Optional[Dict]:
    try:
        if string_table[0][0] == '@docker_version_info':
            version_info = json.loads(string_table[0][1])
            assert isinstance(version_info, dict)
            return version_info
    except IndexError:
        pass
    return None


def get_short_id(string: str) -> str:
    return string.rsplit(":", 1)[-1][:12]


def format_labels(obj: Dict) -> str:
    labels = obj.get("Labels") or {}
    if isinstance(labels, dict):
        labels = iter(labels.items())
    return ", ".join("%s: %s" % item for item in sorted(labels))
