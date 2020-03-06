#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import print_function

import copy

from openapi_spec_validator import validate_spec  # type: ignore

from cmk.gui.plugins.openapi.restful_objects import SPEC


def generate():
    # We need to import the endpoints before importing the spec, lest we don't have a guarantee that
    # all endpoints will be registered in the spec as this is done at import-time.
    import cmk.gui.plugins.openapi.endpoints  # pylint: disable=unused-import,unused-variable

    # NOTE: deepcopy the dict because validate_spec modifies the SPEC in-place, leaving some
    # internal properties lying around, which leads to an invalid spec-file.
    check_dict = copy.deepcopy(SPEC.to_dict())
    validate_spec(check_dict)
    return SPEC.to_yaml().rstrip()


if __name__ == '__main__':
    print(generate())
