#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging

import pytest
import schemathesis
from hypothesis import given, seed, strategies

from tests.schemathesis_openapi import settings
from tests.schemathesis_openapi.runners import run_crud_test, run_state_machine_test
from tests.schemathesis_openapi.schema import get_schema, parametrize_crud_endpoints

logger = logging.getLogger(__name__)
schema = get_schema()


@pytest.mark.type("schemathesis_openapi")
@schema.parametrize(endpoint="")
def test_openapi_stateless(case: schemathesis.models.Case) -> None:
    """Run default, stateless schemathesis testing."""
    if case.path == "/domain-types/notification_rule/collections/all" and case.method in (
        "GET",
        "POST",
    ):
        pytest.skip(reason="Currently fails due to CMK-14375.")
    case.call_and_validate(allow_redirects=settings.allow_redirects)


@pytest.mark.skip(reason="Currently fails due to recursive schema references")
@pytest.mark.type("schemathesis_openapi")
def test_openapi_stateful() -> None:
    """Run stateful schemathesis testing."""
    run_state_machine_test(schema)


@seed(314159265358979323846)  # crud causes flaky data generation errors with random seed
@pytest.mark.type("schemathesis_openapi")
@given(data=strategies.data())
@pytest.mark.parametrize(
    "endpoint", **parametrize_crud_endpoints(schema, ignore="site_connection|rule")
)
def test_openapi_crud(
    data: strategies.SearchStrategy,
    endpoint: dict[str, str],
) -> None:
    """Run schemathesis based CRUD testing."""
    run_crud_test(
        schema,
        data,
        endpoint["target"],
        endpoint["source"],
    )
