#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated, get_args, get_origin

from werkzeug.datastructures import MIMEAccept
from werkzeug.http import parse_accept_header

from cmk.gui.http import Response
from cmk.gui.openapi.framework._types import DataclassInstance, RawRequestData
from cmk.gui.openapi.framework.endpoint_model import EndpointModel
from cmk.gui.openapi.framework.model import json_dump_without_omitted
from cmk.gui.openapi.framework.model.response import ApiResponse, TypedResponse
from cmk.gui.openapi.framework.registry import RequestEndpoint
from cmk.gui.openapi.restful_objects.constructors import etag_of_dict
from cmk.gui.openapi.restful_objects.utils import (
    identify_expected_status_codes,
)
from cmk.gui.openapi.restful_objects.validators import (
    ContentTypeValidator,
    HeaderValidator,
    ResponseValidator,
)
from cmk.gui.openapi.utils import (
    EXT,
    GeneralRestAPIException,
    ProblemException,
    RestAPIResponseException,
    RestAPIWatoDisabledException,
)
from cmk.gui.watolib.activate_changes import update_config_generation
from cmk.gui.watolib.git import do_git_commit

type ApiResponseModel[T: DataclassInstance] = T
"""Some dataclass that was returned from the endpoint."""


def _strip_annotated(t: type) -> type:
    while get_origin(t) is Annotated:
        t = get_args(t)[0]
    return t


def _dump_response[T: DataclassInstance](
    response_body: T | None, response_body_type: type[T] | None
) -> dict | None:
    if response_body is None and response_body_type is None:
        return None

    if response_body is None:
        raise ValueError(f"Response body is None, but should be of type: {response_body_type}")

    if response_body_type is None:
        raise ValueError(f"Response body is of type: {type(response_body)}, but should be None")

    if not isinstance(response_body, _strip_annotated(response_body_type)):
        raise ValueError(
            f"Response body is of type: {type(response_body)}, but should be {response_body_type}"
        )

    json_object = json_dump_without_omitted(response_body_type, response_body)
    if not isinstance(json_object, dict):
        raise ValueError(
            f"Serialized response is of type: {type(json_object)}, but should be a dict"
        )
    return json_object


def _create_response(
    endpoint_response: TypedResponse[ApiResponseModel | None],
    response_body_type: ApiResponseModel | None,
    content_type: str,
    add_etag: bool,
) -> Response:
    """Create a Flask response from the endpoint response."""
    if isinstance(endpoint_response, ApiResponse):
        response_json = _dump_response(endpoint_response.body, response_body_type)
        status_code = endpoint_response.status_code
        headers = endpoint_response.headers
    else:
        response_json = _dump_response(endpoint_response, response_body_type)
        status_code = 204 if response_json is None else 200
        headers = {}

    if add_etag and response_json is not None:
        headers["ETag"] = etag_of_dict(response_json).to_header()

    return Response(
        response=response_json,
        status=status_code,
        headers=headers,
        content_type=content_type,
    )


def _validate_direct_response(response: Response) -> None:
    if not response.data:
        return

    if response.headers.get("Content-Type") == "application/problem+json":
        ResponseValidator.validate_problem_json(response)
        return

    # TODO: we should probably allow other response types. maybe use special response classes that handle serialization?
    if response.status_code < 300:
        raise RestAPIResponseException(
            title="Server was about to send an invalid response.",
            detail="This is an error of the implementation.",
            ext=EXT(
                {
                    "error": "OK response data should be returned directly, not as a Response object",
                    "orig": response.get_data(as_text=True),
                },
            ),
        )


def handle_endpoint_request(
    endpoint: RequestEndpoint,
    request_data: RawRequestData,
    *,
    wato_enabled: bool = True,
    wato_use_git: bool = False,
    is_testing: bool = False,
) -> Response:
    # Step 1: Check WATO enabled for relevant endpoints
    if endpoint.doc_group == "Setup" and not wato_enabled:
        raise RestAPIWatoDisabledException(
            title="Forbidden: Setup is disabled",
            detail="This endpoint is currently disabled via the "
            "'Disable remote configuration' option in 'Distributed Monitoring'. "
            "You may be able to query the central site.",
        )

    # Step 2: Build the endpoint model
    model = EndpointModel.build(endpoint.handler)

    # Step 3: Validate content type
    content_type = request_data["headers"].get("Content-Type")
    ContentTypeValidator.validate(
        has_schema=model.has_request_schema,
        content_type=content_type,
        accepted_types=endpoint.accept if isinstance(endpoint.accept, list) else [endpoint.accept],
        method=endpoint.method,
    )

    accept_mimetypes = parse_accept_header(request_data["headers"].get("Accept"), MIMEAccept)
    HeaderValidator.validate_accept_header(endpoint.content_type, accept_mimetypes)

    # Create the permission checker
    used_permissions: set[str] = set()
    # TODO: permission tracking requires GUI context, which IMO we should avoid as much as possible
    #       so maybe move this out to the WSGI app (similar to the old endpoint decorator)
    # permission_checker = PermissionValidator.create_permission_checker(
    #     permissions_required=endpoint.permissions_required,
    #     register_permission=used_permissions.add,
    #     endpoint_repr=endpoint.operation_id,
    #     is_testing_context=is_testing,
    # )

    # Step 4: Validate the request parameters and call the handler function
    # TODO: this is not explicitly catching marshmallow ValidationErrors anymore - investigate where that would happen
    try:
        # TODO: this used to be in the wsgi app, any reason not to move it here? -> GUI context
        # with PermissionValidator.register_permission_tracking(permission_checker):
        raw_response = model.validate_request_and_call_handler(request_data, content_type)
    except ProblemException as problem_exception:
        response = problem_exception.to_problem()
    except GeneralRestAPIException as general_api_exception:
        response = general_api_exception.to_problem()
    else:
        if isinstance(raw_response, Response):
            _validate_direct_response(raw_response)
            response = raw_response
        else:
            response = _create_response(
                raw_response,
                model.response_body_type,
                endpoint.content_type,
                add_etag=endpoint.etag in ("output", "both"),
            )

    # Step 5: Check permissions
    if response.status_code < 400:
        ResponseValidator.validate_permissions(
            endpoint=endpoint.operation_id,
            params=request_data,
            permissions_required=endpoint.permissions_required,
            used_permissions=used_permissions,
            is_testing=is_testing,
        )

    # Step 6: Validate response status code
    allowed_status_codes = identify_expected_status_codes(
        endpoint.method,
        endpoint.doc_group,
        endpoint.content_type,
        endpoint.etag,
        has_response=model.has_response_schema,
        has_path_params=model.has_path_parameters,
        has_query_params=model.has_query_parameters,
        has_request_schema=model.has_request_schema,
        additional_status_codes=endpoint.additional_status_codes,
    )
    ResponseValidator.validate_response_constraints(
        response=response,
        output_empty=not model.has_response_schema,
        operation_id=endpoint.operation_id,
        expected_status_codes=list(allowed_status_codes),
    )

    # Step 7: Update config generation if needed
    if (
        endpoint.method != "get"
        and response.status_code < 300
        and endpoint.update_config_generation
    ):
        update_config_generation()
        if wato_use_git:
            do_git_commit()

    # Finalize response
    # TODO: validate if this is required? would allow us to remove the 204 handling as well
    # response.freeze()

    # # Response code 204 needs special handling
    # if response.status_code == 204:
    #     for key in ["Content-Type", "Etag"]:
    #         if key in response.headers:
    #             del response.headers[key]

    return response
