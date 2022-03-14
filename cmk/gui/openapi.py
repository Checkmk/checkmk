#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import json
import sys
from typing import Any, Dict, List

from apispec.yaml_utils import dict_to_yaml  # type: ignore[import]
from openapi_spec_validator import validate_spec  # type: ignore[import]

from cmk.utils.site import omd_site

from cmk.gui import main_modules
from cmk.gui.plugins.openapi.restful_objects import SPEC
from cmk.gui.plugins.openapi.restful_objects.decorators import Endpoint
from cmk.gui.plugins.openapi.restful_objects.endpoint_registry import ENDPOINT_REGISTRY
from cmk.gui.plugins.openapi.restful_objects.type_defs import EndpointTarget
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.script_helpers import application_and_request_context

# TODO
#   Eventually move all of SPEC stuff in here, so we have nothing statically defined.
#   This removes variation from the code.


def generate_data(target: EndpointTarget, validate: bool = True) -> Dict[str, Any]:
    endpoint: Endpoint

    methods = ["get", "put", "post", "delete"]

    for endpoint in sorted(
        ENDPOINT_REGISTRY, key=lambda e: (e.func.__module__, methods.index(e.method))
    ):
        if target in endpoint.blacklist_in:
            continue
        SPEC.path(
            path=endpoint.path,
            operations=endpoint.to_operation_dict(),
        )

    generated_spec = SPEC.to_dict()
    #   return generated_spec
    _add_cookie_auth(generated_spec)
    if not validate:
        return generated_spec

    # NOTE: deepcopy the dict because validate_spec modifies the SPEC in-place, leaving some
    # internal properties lying around, which leads to an invalid spec-file.
    check_dict = copy.deepcopy(generated_spec)
    validate_spec(check_dict)
    # NOTE: We want to modify the thing afterwards. The SPEC object would be a global reference
    # which would make modifying the spec very awkward, so we deepcopy again.
    return generated_spec


def add_once(coll: List[Dict[str, Any]], to_add: Dict[str, Any]) -> None:
    """Add an entry to a collection, only once.

    Examples:

        >>> l = []
        >>> add_once(l, {'foo': []})
        >>> l
        [{'foo': []}]

        >>> add_once(l, {'foo': []})
        >>> l
        [{'foo': []}]

    Args:
        coll:
        to_add:

    Returns:

    """
    if to_add in coll:
        return None

    coll.append(to_add)
    return None


def _add_cookie_auth(check_dict):
    """Add the cookie authentication schema to the SPEC.

    We do this here, because every site has a different cookie name and such can't be predicted
    before this code here actually runs.
    """
    schema_name = "cookieAuth"
    add_once(check_dict["security"], {schema_name: []})
    check_dict["components"]["securitySchemes"][schema_name] = {
        "in": "cookie",
        "name": f"auth_{omd_site()}",
        "type": "apiKey",
        "description": "Any user of Checkmk, who has already logged in, and thus got a cookie "
        "assigned, can use the REST API. Some actions may or may not succeed due "
        "to group and permission restrictions. This authentication method has the"
        "least precedence.",
    }


def generate(args=None):
    if args is None:
        args = [None]

    with application_and_request_context():
        data = generate_data(target="debug")

    if args[-1] == "--json":
        output = json.dumps(data, indent=2).rstrip()
    else:
        output = dict_to_yaml(data).rstrip()

    return output


__all__ = ["ENDPOINT_REGISTRY", "generate_data", "add_once"]

if __name__ == "__main__":
    # FIXME: how to load plugins? Spec is empty.
    main_modules.load_plugins()
    if errors := get_failed_plugins():
        raise Exception(f"The following errors occurred during plugin loading: {errors}")
    print(generate(sys.argv))
