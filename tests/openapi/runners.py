#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
from json.decoder import JSONDecodeError
from typing import Any

import hypothesis
import schemathesis  # typing: ignore[name-defined]
from requests import Response

from tests.openapi import settings
from tests.openapi.conftest import hook_after_call

logger = logging.getLogger(__name__)


def run_crud_test(  # pylint: disable=too-many-branches
    schema: schemathesis.schemas.BaseSchema,
    data: Any,
    object_endpoint: str,
    post_endpoint: str,
    post_body: dict[str, Any] | None = None,
    put_body: dict[str, Any] | None = None,
    variables: dict[str, Any] | None = None,
    object_parameter_name: str | None = None,
    post_object_id_key: str | None = None,
    post_response_id_key: str = "id",
) -> None:
    """Execute API CRUD testing."""
    if object_endpoint.count("/") >= 2:
        object_type = object_endpoint.split("/")[2]
    else:
        object_type = object_endpoint.replace("/", "")

    def init_case(
        endpoint: str,
        method: str,
        body: dict[str, Any] | None = None,
        variables: dict[str, Any] | None = None,
        parameters: dict[str, Any] | None = None,
        draw: bool | None = True,
    ) -> schemathesis.models.Case:
        """Draw a test data strategy and return a callable Case object."""
        method = method.lower()
        if draw is None:
            draw = method != "delete"
        if method not in schema[endpoint]:
            alt_endpoint = f"{endpoint}/actions/{method}/invoke"
            if alt_endpoint in schema:
                endpoint = alt_endpoint
                method = list(schema[endpoint])[0]
        if draw:
            case = data.draw(schema[endpoint][method].as_strategy())
        else:
            case = schema[endpoint][method].make_case()
        if body:
            if variables:
                for key in body:
                    body[key] = body[key].format(**variables)
            case.body.update(body)
        if parameters:
            if case.path_parameters:
                case.path_parameters.update(parameters)
            else:
                case.path_parameters = parameters
        return case

    def case_json(case: schemathesis.Case) -> dict[str, Any]:
        if not isinstance(case.body, dict):
            return {"error": f"INVALID JSON BODY: {case.body!r}"}
        return case.body

    def response_json(response: Response) -> dict[str, Any]:
        try:
            return response.json()
        except (AttributeError, ValueError, JSONDecodeError):
            return {"error": f"INVALID JSON RESPONSE: {response.content!r}"}

    def response_reason(response: Response, value: str | None = "detail") -> str:
        try:
            if value:
                return response.reason + f" ({response.json().get(value, 'N/A')})"
            return response.reason + f" ({response.json()})"
        except (AttributeError, ValueError, JSONDecodeError):
            return response.reason

    if object_parameter_name is None:
        object_parameter_name = object_endpoint.split("{", 1)[-1].split("}", 1)[0]
    if post_endpoint == "/domain-types/rule/collections/all" and post_body is None:
        init_case(
            "/domain-types/folder_config/collections/all", "POST", {"name": "schemathesis"}
        ).call_and_validate()
        post_body = {"folder": "~schemathesis", "ruleset": "custom_checks"}
    post_case = init_case(post_endpoint, "POST", post_body, variables)
    post_object_id_keys = [
        key
        for key in [
            post_object_id_key,
            post_response_id_key,
            object_parameter_name,
            next(iter(case_json(post_case))),
        ]
        if key
    ]
    post_object_id_key = next(key for key in post_object_id_keys if key in case_json(post_case))
    if hasattr(post_case, "body") and isinstance(post_case.body, dict):
        post_object_id = post_case.body.get(post_object_id_key)
    logger.info('Creating "%s" object: %s', object_type, case_json(post_case))
    post_response = post_case.call_and_validate()
    if post_response.status_code == 200:
        logger.debug(
            'Created "%s" object: %s\nResponse: %s',
            object_type,
            case_json(post_case),
            response_json(post_response),
        )
        post_response_id = response_json(post_response).get(post_response_id_key)
        if (
            post_response_id is None
            and post_endpoint == "/domain-types/time_period/collections/all"
            and "CMK-12044" in settings.suppressed_issues
        ):
            post_response_id = post_object_id

        if post_object_id == post_response_id:
            logger.debug(
                "Object ID match! (post_object_id == post_response_id == %s)",
                post_object_id,
            )
            get_case = init_case(
                object_endpoint, "GET", None, None, {object_parameter_name: post_object_id}
            )
            logger.info('Retrieving "%s" object...', object_type)
            get_response = get_case.call_and_validate()
            get_done = get_response.status_code == 200
            if get_done:
                logger.info('Retrieved "%s" object: %s', object_type, response_json(get_response))
                put_case = init_case(
                    object_endpoint,
                    "PUT",
                    put_body,
                    variables,
                    {object_parameter_name: post_object_id},
                )
                put_response = put_case.call_and_validate()
                put_done = put_response.status_code in (200, 204)
                if put_done:
                    get_response = get_case.call_and_validate()
                    logger.info(
                        'Updated "%s" object: %s\nUpdate: %s',
                        object_type,
                        response_json(get_response),
                        case_json(put_case),
                    )
                else:
                    logger.warning(
                        'Failed to update "%s" object: %s\nUpdate: %s\nReason: %s',
                        object_type,
                        response_json(get_response),
                        case_json(put_case),
                        response_reason(put_response),
                    )
            else:
                logger.warning(
                    'Failed to retrieve "%s" object: %s', object_type, case_json(post_case)
                )
                put_done = False
        else:
            logger.warning(
                'Created "%s" object but detected ID mismatch! (%s=%s != %s=%s)',
                object_type,
                post_object_id_key,
                post_object_id,
                post_response_id_key,
                post_response_id,
            )
            get_done = False
            put_done = False
        logger.info('Deleting "%s" object...', object_type)
        delete_case = init_case(
            object_endpoint, "DELETE", None, None, {object_parameter_name: post_object_id}
        )
        delete_response = delete_case.call_and_validate()

        assert delete_response.status_code in (
            200,
            204,
        ), (
            f'Failed to delete "{object_type}" object "{post_object_id}"!'
            f" Reason: {response_reason(delete_response)}"
        )
        logger.debug('Deleted "%s" object: %s', object_type, case_json(post_case))

        if get_done:
            assert get_response.status_code == 200, (
                f'Failed to retrieve "{object_type}" object "{post_object_id}"!'
                f" Reason: {response_reason(get_response)}"
            )
        if put_done:
            assert put_response.status_code in (
                200,
                204,
                400,
            ), (
                f'Failed to update "{object_type}" object "{post_object_id}"!'
                f" Reason: {response_reason(put_response)}"
            )
    else:
        logger.warning(
            'Failed to create "%s" object: %s with ID %s\nReason: %s',
            object_type,
            json.dumps(post_case.body),
            post_object_id,
            response_reason(post_response),
        )

    assert post_response.status_code in (
        200,
        400,
    ), f'Unexpected error creating {object_type} object "{post_object_id}"!'


def run_state_machine_test(
    schema: schemathesis.schemas.BaseSchema,
    endpoint: str | None = None,
    method: Any | None = None,
    checks: Any | None = None,
) -> None:
    """Get a state machine for stateful testing."""
    if endpoint or checks or method:
        cloned_schema = schema.clone(endpoint=endpoint, method=method)
        state_machine: Any = cloned_schema.as_state_machine()

        class APIWorkflow(state_machine):
            def validate_response(self, response, case):
                case.validate_response(response, checks=checks)

            def after_call(self, response, case):
                hook_after_call(None, case, response)

        state_machine = APIWorkflow
    else:
        state_machine = schema.as_state_machine()
    hypothesis.stateful.run_state_machine_as_test(state_machine)
