#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import yaml
from openapi_spec_validator import validate_spec  # type: ignore[import]


def test_yaml_file(wsgi_app):
    resp = wsgi_app.get("/NO_SITE/check_mk/api/0/openapi.yaml", status=200)
    data = yaml.load(resp.body)
    validate_spec(data)


def test_json_file(wsgi_app):
    resp = wsgi_app.get("/NO_SITE/check_mk/api/0/openapi.json", status=200)
    data = json.loads(resp.body)
    validate_spec(data)
