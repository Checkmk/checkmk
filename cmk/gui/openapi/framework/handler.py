#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import contextlib
import json
from inspect import BoundArguments

from werkzeug.datastructures import MIMEAccept
from werkzeug.http import parse_accept_header

from cmk.ccc import store

from cmk.utils.paths import configuration_lockfile

from cmk.gui.fields.fields_filter import FieldsFilter
from cmk.gui.http import HTTPMethod, Response
from cmk.gui.openapi.framework._types import ApiContext, DataclassInstance, RawRequestData
from cmk.gui.openapi.framework._utils import get_stripped_origin, iter_dataclass_fields
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
    PermissionValidator,
    ResponseValidator,
)
from cmk.gui.openapi.utils import (
    EXT,
    RestAPIResponseException,
    RestAPIWatoDisabledException,
)
from cmk.gui.watolib.activate_changes import update_config_generation
from cmk.gui.watolib.git import do_git_commit

from cmk import trace

tracer = trace.get_tracer()

type ApiResponseModel[T: DataclassInstance] = T
"""Some dataclass that was returned from the endpoint."""


def _dump_response[T: DataclassInstance](
    response_body: T | None, response_body_type: type[T] | None, *, is_testing: bool
) -> bytes | None:
    if response_body is None and response_body_type is None:
        return None

    if response_body is None:
        raise ValueError(f"Response body is None, but should be of type: {response_body_type}")

    if response_body_type is None:
        raise ValueError(f"Response body is of type: {type(response_body)}, but should be None")

    if not isinstance(response_body, get_stripped_origin(response_body_type)):
        raise ValueError(
            f"Response body is of type: {type(response_body)}, but should be {response_body_type}"
        )

    return json_dump_without_omitted(response_body_type, response_body, is_testing=is_testing)


def _create_response(
    endpoint_response: TypedResponse[ApiResponseModel | None],
    response_body_type: type[ApiResponseModel] | None,
    content_type: str | None,
    *,
    fields_filter: FieldsFilter | None,
    add_etag: bool,
    is_testing: bool,
) -> Response:
    """Create a Flask response from the endpoint response."""
    if isinstance(endpoint_response, ApiResponse):
        json_text: str | bytes | None = _dump_response(
            endpoint_response.body, response_body_type, is_testing=is_testing
        )
        status_code = endpoint_response.status_code
        headers = endpoint_response.headers
    else:
        json_text = _dump_response(endpoint_response, response_body_type, is_testing=is_testing)
        status_code = 204 if json_text is None else 200
        headers = {}

    if json_text is not None:
        json_object = json.loads(json_text)
        if fields_filter is not None:
            json_object = fields_filter.apply(json_object)

        if add_etag:
            headers["ETag"] = etag_of_dict(json_object).to_header()

        json_text = json.dumps(json_object)

    return Response(
        response=json_text,
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


def _optional_config_lock(
    skip_locking: bool, method: HTTPMethod
) -> contextlib.AbstractContextManager[None]:
    """Return a context manager which may lock the configuration."""
    if skip_locking or method == "get":
        return contextlib.nullcontext()

    return store.lock_checkmk_configuration(configuration_lockfile)


def _identify_fields_filter(
    bound_arguments: BoundArguments, has_request_schema: bool
) -> FieldsFilter | None:
    for name, value in bound_arguments.arguments.items():
        if name == "body":
            continue
        if isinstance(value, FieldsFilter):
            return value

    if has_request_schema:
        # for request body we only check on the first level
        for _, value in iter_dataclass_fields(bound_arguments.arguments["body"]):
            if isinstance(value, FieldsFilter):
                return value
    return None


@tracer.instrument("handle_endpoint_request")
def handle_endpoint_request(
    endpoint: RequestEndpoint,
    request_data: RawRequestData,
    api_context: ApiContext,
    permission_validator: PermissionValidator,
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

    # Step 4: Validate the request parameters and call the handler function
    # NOTE: exceptions will be caught in the WSGI app (including the other validation exceptions)
    with (
        permission_validator.track_permissions(),
        _optional_config_lock(endpoint.skip_locking, endpoint.method),
    ):
        bound_arguments = model.validate_request_and_identify_args(
            request_data, content_type, api_context
        )
        with tracer.span("endpoint-body-call"):
            raw_response = endpoint.handler(*bound_arguments.args, **bound_arguments.kwargs)

    with tracer.span("create-response"):
        if isinstance(raw_response, Response):
            _validate_direct_response(raw_response)
            response = raw_response
        else:
            response = _create_response(
                raw_response,
                model.response_body_type,
                endpoint.content_type,
                fields_filter=_identify_fields_filter(bound_arguments, model.has_request_schema),
                add_etag=endpoint.etag in ("output", "both"),
                is_testing=is_testing,
            )

    # Step 5: Check permissions
    if response.status_code < 400:
        ResponseValidator.validate_permissions(
            endpoint=endpoint.operation_id,
            params=request_data,
            permissions_required=endpoint.permissions_required,
            used_permissions=permission_validator.used_permissions,
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

    return response
