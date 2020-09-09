#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import json
import sys

from openapi_spec_validator import validate_spec  # type: ignore[import]

from cmk.gui.plugins.openapi.restful_objects import SPEC
from cmk.gui.plugins.openapi.restful_objects.decorators import Endpoint
from cmk.gui.plugins.openapi.restful_objects.type_defs import ENDPOINT_REGISTRY
from cmk.utils import version

# NOTE
# This import needs to be here, because the decorators populate the
# ENDPOINT_REGISTRY. If this didn't happen, the SPEC would be incomplete.
import cmk.gui.plugins.openapi  # pylint: disable=unused-import

if not version.is_raw_edition():
    import cmk.gui.cee.plugins.openapi  # noqa: F401 # pylint: disable=unused-import,no-name-in-module


def generate(args=None):
    if args is None:
        args = [None]

    endpoint: Endpoint
    for endpoint in ENDPOINT_REGISTRY:
        SPEC.path(
            path=endpoint.path,
            operations={endpoint.method.lower(): endpoint.to_operation_dict()},
        )

    # NOTE: deepcopy the dict because validate_spec modifies the SPEC in-place, leaving some
    # internal properties lying around, which leads to an invalid spec-file.
    check_dict = copy.deepcopy(SPEC.to_dict())
    validate_spec(check_dict)

    if args[-1] == '--json':
        output = json.dumps(SPEC.to_dict(), indent=2).rstrip()
    else:
        output = SPEC.to_yaml().rstrip()

    return output


if __name__ == '__main__':
    print(generate(sys.argv))
