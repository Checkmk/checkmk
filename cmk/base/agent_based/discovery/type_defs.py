#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple


class DiscoveryParameters(NamedTuple):
    on_error: str
    load_labels: bool
    save_labels: bool
    only_host_labels: bool
