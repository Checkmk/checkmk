#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import json
import sys
from typing import Any, Dict

from apispec.yaml_utils import dict_to_yaml  # type: ignore[import]
from openapi_spec_validator import validate_spec  # type: ignore[import]

from cmk.gui import config
from cmk.gui.plugins.openapi.restful_objects import SPEC
from cmk.gui.plugins.openapi.restful_objects.decorators import Endpoint
from cmk.gui.plugins.openapi.restful_objects.endpoint_registry import ENDPOINT_REGISTRY
from cmk.gui.plugins.openapi.restful_objects.type_defs import EndpointTarget
from cmk.utils import version

# TODO
#   Eventually move all of SPEC stuff in here, so we have nothing statically defined.
#   This removes variation from the code.

# NOTE
# This import needs to be here, because the decorators populate the
# ENDPOINT_REGISTRY. If this didn't happen, the SPEC would be incomplete.
import cmk.gui.plugins.openapi  # pylint: disable=unused-import

if not version.is_raw_edition():
    import cmk.gui.cee.plugins.openapi  # noqa: F401 # pylint: disable=unused-import,no-name-in-module


def generate_data(target: EndpointTarget) -> Dict[str, Any]:
    endpoint: Endpoint
    for endpoint in ENDPOINT_REGISTRY:
        if target in endpoint.blacklist_in:
            continue
        SPEC.path(
            path=endpoint.path,
            operations=endpoint.to_operation_dict(),
        )

    # NOTE: deepcopy the dict because validate_spec modifies the SPEC in-place, leaving some
    # internal properties lying around, which leads to an invalid spec-file.
    check_dict = copy.deepcopy(SPEC.to_dict())
    _add_cookie_auth(check_dict)
    validate_spec(check_dict)
    # NOTE: We want to modify the thing afterwards. The SPEC object would be a global reference
    # which would make modifying the spec very awkward, so we deepcopy again.
    rv = copy.deepcopy(SPEC.to_dict())
    _add_cookie_auth(rv)
    return rv


def _add_cookie_auth(check_dict):
    """Add the cookie authentication schema to the SPEC.

    We do this here, because every site has a different cookie name and such can't be predicted
    before this code here actually runs.
    """
    schema_name = 'cookieAuth'
    check_dict['security'].append({schema_name: []})
    check_dict['components']['securitySchemes'][schema_name] = {
        'in': 'cookie',
        'name': f'auth_{config.omd_site()}',
        'type': 'apiKey',
        'description': 'Any user of Checkmk, who has already logged in, and thus got a cookie '
                       'assigned, can use the REST API. Some actions may or may not succeed due '
                       'to group and permission restrictions.',
    }


def generate(args=None):
    if args is None:
        args = [None]

    data = generate_data(target='debug')
    if args[-1] == '--json':
        output = json.dumps(data, indent=2).rstrip()
    else:
        output = dict_to_yaml(data).rstrip()

    return output


__all__ = ['ENDPOINT_REGISTRY', 'generate_data']

if __name__ == '__main__':
    print(generate(sys.argv))
