#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys

import cmk
from cmk.gui.globals import request


def search(user=None, token_info=None):
    if request.args.get('fail'):
        raise Exception("This is an intentional failure.")
    return {
        "site": cmk.omd_site(),
        "group": request.environ.get('mod_wsgi.application_group', 'unknown'),
        "versions": {
            "apache": request.environ.get('apache.version', 'unknown'),
            "checkmk": cmk.omd_version(),
            "python": sys.version,
            'mod_wsgi': request.environ.get('mod_wsgi.version', 'unknown'),
            'wsgi': request.environ['wsgi.version'],
        },
        "edition": cmk.edition_short(),
        "demo": cmk.is_demo(),
    }
