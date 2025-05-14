#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi import versioned_endpoint_registry
from cmk.gui.openapi.framework import validate_endpoint_definition


def test_verify_registered_endpoints() -> None:
    """Test that all registered endpoints are valid"""
    seen_endpoints = set()
    versioned_endpoints = [endpoint for endpoint in versioned_endpoint_registry]
    for endpoint in versioned_endpoints:
        validate_endpoint_definition(endpoint)
        endpoint_key = (endpoint.family.name, endpoint.metadata.link_relation)
        seen_endpoints.add(endpoint_key)
    assert len(seen_endpoints) == len(versioned_endpoints)
