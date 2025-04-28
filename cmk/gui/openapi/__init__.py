#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .framework.registry import versioned_endpoint_registry
from .restful_objects.endpoint_family import endpoint_family_registry
from .restful_objects.registry import endpoint_registry

__all__ = ["endpoint_registry", "endpoint_family_registry", "versioned_endpoint_registry"]
