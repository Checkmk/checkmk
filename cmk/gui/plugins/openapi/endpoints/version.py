#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Miscellaneous

This folder collects individual endpoints not fitting into the other endpoint folders.
"""

import sys

import cmk.utils.version as cmk_version
from cmk.utils.site import omd_site

from cmk.gui.globals import request
from cmk.gui.plugins.openapi.restful_objects import Endpoint, response_schemas
from cmk.gui.plugins.openapi.utils import serve_json


@Endpoint(
    "/version",
    "cmk/show",
    tag_group="Monitoring",
    method="get",
    response_schema=response_schemas.InstalledVersions,
)
def search(param):
    """Display some version information"""
    if request.args.get("fail"):
        raise Exception("This is an intentional failure.")
    return serve_json(
        {
            "site": omd_site(),
            "group": request.environ.get("mod_wsgi.application_group", "unknown"),
            "rest_api": {
                "revision": "0",
            },
            "versions": {
                "apache": request.environ.get("apache.version", "unknown"),
                "checkmk": cmk_version.omd_version(),
                "python": sys.version,
                "mod_wsgi": request.environ.get("mod_wsgi.version", "unknown"),
                "wsgi": request.environ["wsgi.version"],
            },
            "edition": cmk_version.edition().short,
            "demo": cmk_version.is_free_edition(),
        }
    )
