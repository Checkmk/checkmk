#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass

import pytest

from tests.unit.cmk.gui.openapi.framework.factories import EndpointDefinitionFactory

from cmk.gui.openapi import versioned_endpoint_registry
from cmk.gui.openapi.framework.registry import validate_endpoint_definition
from cmk.gui.openapi.framework.versioned_endpoint import HandlerFunction


def test_verify_registered_endpoints() -> None:
    """Test that all registered endpoints are valid"""
    seen_endpoints = set()
    versioned_endpoints = [endpoint for endpoint in versioned_endpoint_registry]
    for endpoint in versioned_endpoints:
        validate_endpoint_definition(endpoint)
        endpoint_key = (endpoint.family.name, endpoint.metadata.link_relation)
        seen_endpoints.add(endpoint_key)
    assert len(seen_endpoints) == len(versioned_endpoints)


@dataclass
class _Body:
    pass


def _error_body_parameter_kind_endpoint_handler(body: _Body, /) -> None:
    raise NotImplementedError


def _error_no_body_annotation_endpoint_handler(body) -> None:  # type: ignore[no-untyped-def]
    raise NotImplementedError


def _error_body_parameter_type_endpoint_handler(body: object) -> None:
    raise NotImplementedError


@pytest.mark.parametrize(
    "handler, match",
    [
        (
            _error_body_parameter_kind_endpoint_handler,
            "Invalid parameter kind for request body",
        ),
        (
            _error_no_body_annotation_endpoint_handler,
            "Missing annotation for request body",
        ),
        (
            _error_body_parameter_type_endpoint_handler,
            "Request body annotation must be a dataclass",
        ),
    ],
)
def test_invalid_body_parameter(handler: HandlerFunction, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        validate_endpoint_definition(EndpointDefinitionFactory.build(handler={"handler": handler}))
