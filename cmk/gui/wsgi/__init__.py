#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pathlib

from cmk.gui.wsgi.middleware import apache_env
from cmk.gui.wsgi.routing import make_router
from cmk.gui.wsgi.profiling import ProfileSwitcher
import cmk.utils.paths


def make_app(debug=False):
    return ProfileSwitcher(
        apache_env(make_router(debug=debug)),
        profile_file=pathlib.Path(cmk.utils.paths.var_dir) / "multisite.profile",
    )


__all__ = ['make_app']
