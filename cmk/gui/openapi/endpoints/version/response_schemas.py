#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk import fields
from cmk.gui.fields.utils import BaseSchema


class InstalledVersions(BaseSchema):
    site = fields.String(
        description="The site where this API call was made on.", example="production"
    )
    group = fields.String(
        description="The Apache WSGI application group this call was made on.", example="de"
    )
    rest_api = fields.Dict(description="The REST-API version", example={"revision": "1.0.0"})
    versions = fields.Dict(description="Some version numbers", example={"checkmk": "1.8.0p1"})
    edition = fields.String(description="The Checkmk edition.", example="raw")
    demo = fields.Boolean(description="Whether this is a demo version or not.", example=False)
