#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Implements a first shot at the "value_store". Quite literally only an AP*I*
"""

# TODO: this API violiation is due to the fact that this value_store
# is about to be replaced by most of the content of cmk/base/item_states.
from cmk.base.item_state import get_value_store  # pylint: disable=cmk-module-layer-violation

__all__ = ["get_value_store"]
