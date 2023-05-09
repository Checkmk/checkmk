#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
=============================
agent_based_api.v1.clusterize
=============================
"""

from cmk.base.api.agent_based.clusterize import make_node_notice_results

__all__ = [
    'make_node_notice_results',
]
