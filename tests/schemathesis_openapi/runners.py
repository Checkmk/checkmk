#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
from json.decoder import JSONDecodeError
from typing import Any

import hypothesis
import hypothesis.stateful
import schemathesis
from requests import Response
from schemathesis.specs.openapi import schemas
from schemathesis.stateful.state_machine import APIStateMachine

from tests.schemathesis_openapi import settings

logger = logging.getLogger(__name__)


def _init_case(
    schema: schemas.BaseOpenAPISchema,
    data: Any,
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


def _case_json(case: schemathesis.models.Case) -> dict[str, Any]:
    if not isinstance(case.body, dict):
        return {"error": f"INVALID JSON BODY: {case.body!r}"}
    return case.body


def _response_json(response: Response) -> dict[str, Any]:
    try:
        return response.json()
    except (AttributeError, ValueError, JSONDecodeError):
        return {"error": f"INVALID JSON RESPONSE: {response.content!r}"}


def _response_reason(response: Response, value: str | None = "detail") -> str:
    try:
        if value:
            return response.reason + f" ({response.json().get(value, 'N/A')})"
        return response.reason + f" ({response.json()})"
    except (AttributeError, ValueError, JSONDecodeError):
        return response.reason


def run_crud_test(
    schema: schemas.BaseOpenAPISchema,
    data: Any,
    object_endpoint: str,
    post_endpoint: str,
    post_body: dict[str, Any] | None = None,
    put_body: dict[str, Any] | None = None,
    variables: dict[str, Any] | None = None,
    object_parameter_name: str | None = None,
    post_object_id_key: str = "name",
    post_response_id_key: str = "id",
) -> None:
    """Execute API CRUD testing."""
    object_type = (
        object_endpoint.split("/")[2]
        if object_endpoint.count("/") >= 2
        else object_endpoint.replace("/", "")
    )
    object_parameter_name = (
        object_parameter_name or object_endpoint.split("{", 1)[-1].split("}", 1)[0]
    )

    if post_endpoint == "/domain-types/rule/collections/all" and post_body is None:
        _init_case(
            schema,
            data,
            "/domain-types/folder_config/collections/all",
            "POST",
            {"title": "schemathesis", "parent": "~"},
        ).call_and_validate(allow_redirects=settings.allow_redirects)
        post_body = {"folder": "~schemathesis", "ruleset": "custom_checks"}
    post_case = _init_case(
        schema,
        data,
        post_endpoint,
        "POST",
        post_body,
        variables,
    )
    logger.info('Creating "%s" object: %s', object_type, _case_json(post_case))
    post_response = post_case.call_and_validate(allow_redirects=settings.allow_redirects)
    post_response_id = _response_json(post_response).get(post_response_id_key)
    logger.debug('Response "%s" object id: %s', object_type, post_response_id)
    post_object_id_keys = [
        key
        for key in [
            post_object_id_key,
            post_response_id_key,
            object_parameter_name,
            next(iter(_case_json(post_case))),
        ]
        if key
    ]
    post_object_id_key = next(key for key in post_object_id_keys if key in _case_json(post_case))
    post_object_id = (
        post_case.body.get(post_object_id_key)
        if hasattr(post_case, "body") and isinstance(post_case.body, dict)
        else post_response_id
    )
    object_id = post_response_id or post_object_id

    # first assert the post either returned HTTP200 or HTTP400
    assert post_response.status_code in (
        200,
        400,
    ), f'Unexpected error creating {object_type} object "{post_object_id}"!'

    # then bail out if the post failed
    if post_response.status_code != 200:
        logger.warning(
            'Failed to create "%s" object: %s with ID %s\nReason: %s',
            object_type,
            json.dumps(post_case.body),
            post_object_id,
            _response_reason(post_response),
        )
        return

    logger.debug(
        'Created "%s" object: %s\nResponse: %s',
        object_type,
        _case_json(post_case),
        _response_json(post_response),
    )

    if post_object_id == post_response_id:
        logger.debug(
            'Created "%s" object! (%s==%s==%s)',
            object_type,
            post_object_id_key,
            post_response_id_key,
            post_object_id,
        )
    else:
        logger.warning(
            'Created "%s" object but detected ID mismatch! (%s=%s != %s=%s)',
            object_type,
            post_object_id_key,
            post_object_id,
            post_response_id_key,
            post_response_id,
        )
    get_case = _init_case(
        schema,
        data,
        object_endpoint,
        "GET",
        None,
        None,
        {object_parameter_name: object_id},
    )
    logger.info('Retrieving "%s" object...', object_type)
    get_response = get_case.call_and_validate(allow_redirects=settings.allow_redirects)
    get_done = get_response.status_code == 200
    if get_done:
        logger.info('Retrieved "%s" object: %s', object_type, _response_json(get_response))
        put_case = _init_case(
            schema,
            data,
            object_endpoint,
            "PUT",
            put_body,
            variables,
            {object_parameter_name: object_id},
        )
        put_response = put_case.call_and_validate(allow_redirects=settings.allow_redirects)
        put_done = put_response.status_code in (200, 204)
        if put_done:
            get_response = get_case.call_and_validate(allow_redirects=settings.allow_redirects)
            logger.info(
                'Updated "%s" object: %s\nUpdate: %s',
                object_type,
                _response_json(get_response),
                _case_json(put_case),
            )
        else:
            logger.warning(
                'Failed to update "%s" object: %s\nUpdate: %s\nReason: %s',
                object_type,
                _response_json(get_response),
                _case_json(put_case),
                _response_reason(put_response),
            )
    else:
        logger.warning('Failed to retrieve "%s" object: %s', object_type, _case_json(post_case))
        put_done = False

    logger.info('Deleting "%s" object...', object_type)
    delete_case = _init_case(
        schema,
        data,
        object_endpoint,
        "DELETE",
        None,
        None,
        {object_parameter_name: object_id},
    )
    delete_response = delete_case.call_and_validate(allow_redirects=settings.allow_redirects)
    if any(
        _ in ("/", "%2F", "\\", "%5C", "~", ".", "%2E")
        for _ in dict(delete_case.path_parameters or {}).values()
    ):
        # expect 4xx error on single slash, tilde or dot object names (i.e. "/", "~" or ".")
        assert delete_response.status_code in (400, 401, 404), (
            f'Unexpected status code trying to delete "{object_type}" object "{object_id}"!'
            f" Reason: {_response_reason(delete_response)}"
        )
    else:
        # expect success but ignore bad requests
        assert delete_response.status_code in (200, 204, 400), (
            f'Failed to delete "{object_type}" object "{object_id}"!'
            f" Reason: {_response_reason(delete_response)}"
        )
    logger.debug('Deleted "%s" object: %s', object_type, _case_json(post_case))

    if get_done:
        assert get_response.status_code == 200, (
            f'Failed to retrieve "{object_type}" object "{object_id}"!'
            f" Reason: {_response_reason(get_response)}"
        )
    if put_done:
        assert put_response.status_code in (
            200,
            204,
            400,
        ), (
            f'Failed to update "{object_type}" object "{object_id}"!'
            f" Reason: {_response_reason(put_response)}"
        )


def run_state_machine_test(schema: schemas.BaseOpenAPISchema) -> None:
    """Get a state machine for stateful testing."""
    state_machine: type[APIStateMachine]
    state_machine = schema.as_state_machine()
    hypothesis.stateful.run_state_machine_as_test(state_machine)
