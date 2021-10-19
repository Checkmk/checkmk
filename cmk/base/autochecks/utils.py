#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, NamedTuple

from cmk.utils.type_defs import CheckPluginName, Item

from cmk.base.check_utils import LegacyCheckParameters


class AutocheckEntry(NamedTuple):
    check_plugin_name: CheckPluginName
    item: Item
    parameters: LegacyCheckParameters
    service_labels: Mapping[str, str]
