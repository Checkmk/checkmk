#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TYPE_CHECKING

from cmk.gui.ctx_stack import request_local_attr

#####################################################################
# a namespace for storing data during an application context

if TYPE_CHECKING:
    # Import cycles
    from cmk.gui import htmllib


######################################################################
# TODO: This should live somewhere else...

html: htmllib.html = request_local_attr("html")
