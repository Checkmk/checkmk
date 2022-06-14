#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.metrics as metrics


def test_registered_renderers() -> None:
    registered_plugins = sorted(metrics.renderer_registry.keys())
    assert registered_plugins == ["dual", "linear", "logarithmic", "stacked"]
