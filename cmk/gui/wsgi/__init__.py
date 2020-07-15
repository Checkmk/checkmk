#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.wsgi.middleware import apache_env
from cmk.gui.wsgi.routing import make_router


def make_app(debug=False):
    return apache_env(make_router(debug=debug))


__all__ = ['make_app']
