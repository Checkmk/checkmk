#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.ctx_stack import g


def need_sidebar_reload():
    g.need_sidebar_reload = True


def is_sidebar_reload_needed():
    return "need_sidebar_reload" in g and g.need_sidebar_reload
