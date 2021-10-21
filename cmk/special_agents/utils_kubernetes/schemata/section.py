#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
The schemas contained in this file are used to serialize data in the agent output.

This file should not contain any code and should not import from anywhere
except the python standard library or pydantic.
"""

from pydantic import BaseModel


class PodResources(BaseModel):
    """section: k8s_pods_resources"""

    running: int = 0
    pending: int = 0
    succeeded: int = 0
    failed: int = 0
    unknown: int = 0
    capacity: int = 0
    allocatable: int = 0


class NodeCount(BaseModel):
    """section: k8s_node_count_v1"""

    worker: int = 0
    control_plane: int = 0
