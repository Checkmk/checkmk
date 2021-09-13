#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Spec/Documentation building code

This package contains several important modules. It's main purpose is
to allow functions to be used as API endpoints which will then appear
in the OpenAPI spec-file complete with code examples.

How does it work:

    The decorators contain code which registers the function to the APISpec
    instance which will generate the specification. In order for it to work
    all endpoints have to be imported once before the spec generation runs.

Recommended Entry Point:

    The `decorators` module. The other modules will be called from there.

The modules:

  * The `request_schemas` and `response_schemas` modules are special, as
    they only contain abstract models of the request and response formats
    and will be used in validation (currently only response).

  * The `specification` module is the entry point for the OpenAPI
    spec generation code and contains mostly boilerplate code and some
    useful parameter definitions.

  * The `constructors` module contains helpers which generate parts
    of the nested JSON struct that is specified by the Restful Objects
    specification.

  * The `code_examples` module contains a helper which renders Jinja2
    templates with source code examples. These are put into the spec
    by the decorator. The examples are specific to the Redoc documentation
    generator library.

"""

from cmk.gui.plugins.openapi.restful_objects.decorators import Endpoint
from cmk.gui.plugins.openapi.restful_objects.specification import SPEC

__all__ = ["Endpoint", "SPEC"]
