#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.gui.plugins.openapi.restful_objects import response_schemas
from cmk.gui.plugins.openapi.utils import problem


def test_openapi_error_response():
    fields = {
        "entries": {
            "0": {
                "attributes": {
                    "_schema": {
                        "locked_by": {
                            "instance_id": ["Missing data for required field."],
                            "connection_id": ["Unknown field."],
                        }
                    }
                }
            },
            "1": {
                "attributes": {
                    "_schema": {
                        "locked_by": {
                            "instance_id": ["Missing data for required field."],
                            "connection_id": ["Unknown field."],
                        }
                    }
                }
            },
        }
    }

    problem_response = problem(
        detail="Experienced an error",
        status=500,
        title="Internal Server Error",
        fields=fields,
        ext={"error_type": "internal_error"},
    )

    json_dict = json.loads(problem_response.data)
    schema = response_schemas.ApiError()
    loaded = schema.load(json_dict)
    dumped = schema.dump(loaded)

    assert len(dumped["fields"]["entries"]) == 2

    assert dumped["detail"] == "Experienced an error"
    assert dumped["ext"] == {"error_type": "internal_error"}
    assert dumped["status"] == 500
    assert dumped["title"] == "Internal Server Error"
    assert dumped["fields"]["entries"]["0"]["attributes"]["_schema"]["locked_by"] == {
        "instance_id": ["Missing data for required field."],
        "connection_id": ["Unknown field."],
    }
    assert dumped["fields"]["entries"]["1"]["attributes"]["_schema"]["locked_by"] == {
        "instance_id": ["Missing data for required field."],
        "connection_id": ["Unknown field."],
    }
