#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi._openapi import add_once, ENDPOINT_REGISTRY, generate_data

__all__ = ["ENDPOINT_REGISTRY", "generate_data", "add_once"]
