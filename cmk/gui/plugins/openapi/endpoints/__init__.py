#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE:
#   We need to import the endpoints before importing the spec, lest we don't have a guarantee
#   that all endpoints will be registered in the spec when this module (openapi.endpoints) is
#   being imported by the "specgen" module, to generate spec-file and the documentation.
from cmk.gui.plugins.openapi.endpoints import (
    contact_group,
    folder,
    host,
    host_group,
    service_group,
    version,
)

__all__ = [
    'contact_group',
    'folder',
    'host',
    'host_group',
    'service_group',
    'version',
]
