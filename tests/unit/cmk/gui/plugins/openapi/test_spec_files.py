#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

import yaml
from openapi_spec_validator import validate_spec  # type: ignore[import]


# TODO(sp): This test takes ages, about 7.2s total! Improve this.
def test_yaml_file(wsgi_app):  # 0.8s
    resp = wsgi_app.get("/NO_SITE/check_mk/api/1.0/openapi-swagger-ui.yaml", status=200)  # 3.3s
    assert resp.content_type.startswith("application/x-yaml")
    data = yaml.safe_load(resp.body)  # 1.9s
    validate_spec(data)  # 1.2s


# TODO(sp): This test takes ages, about 4.1 total! Improve this.
def test_json_file(wsgi_app):  # 0.8s
    resp = wsgi_app.get("/NO_SITE/check_mk/api/1.0/openapi-doc.json", status=200)  # 2.1s
    assert resp.content_type.startswith("application/json")
    data = json.loads(resp.body)
    validate_spec(data)  # 1.2s
