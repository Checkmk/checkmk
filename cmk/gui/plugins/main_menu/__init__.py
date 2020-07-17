#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Ignore issues related to unused variables in this plugin namespace
# flake8: noqa
# pylint: disable=unused-import

from cmk.utils.plugin_loader import load_plugins

from cmk.gui.plugins.main_menu.utils import (
    mega_menu_registry,
    MegaMenu,
    TopicMenuTopic,
    TopicMenuItem,
    any_advanced_items,
)

load_plugins(__file__, __package__)
