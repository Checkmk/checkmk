#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Common operations for API endpoints."""

from __future__ import annotations

import contextlib
import dataclasses
import http.client
import json
import logging
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from typing import Any, NoReturn, Self
from urllib import parse

import pydantic
from marshmallow import fields as ma_fields
from marshmallow import Schema, ValidationError
from werkzeug.datastructures import MIMEAccept, MultiDict
from werkzeug.http import parse_options_header

from cmk.gui import hooks
from cmk.gui import http as cmk_http
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import HTTPMethod, Request
from cmk.gui.openapi.permission_tracking import (
    enable_permission_tracking,
    is_permission_tracking_enabled,
)
from cmk.gui.openapi.restful_objects.content_decoder import decode
from cmk.gui.openapi.restful_objects.params import path_parameters
from cmk.gui.openapi.restful_objects.type_defs import StatusCodeInt
from cmk.gui.openapi.utils import (
    EXT,
    FIELDS,
    RestAPIForbiddenException,
    RestAPIHeaderSchemaValidationException,
    RestAPIHeaderValidationException,
    RestAPIPathValidationException,
    RestAPIPermissionException,
    RestAPIQueryPathValidationException,
    RestAPIRequestContentTypeException,
    RestAPIRequestDataValidationException,
    RestAPIResponseException,
)
from cmk.gui.utils import permission_verification as permissions

from cmk import trace

tracer = trace.get_tracer()
_logger = logging.getLogger(__name__)


ArgDict = dict[str, str | list[str]]


class ContentTypeValidator:
    @staticmethod
    def validate(
        has_schema: bool,
        content_type: str | None,
        accepted_types: Sequence[str],
        method: HTTPMethod,
    ) -> None:
        """Validate the request content type"""
        inbound_method = method in ("post", "put")

        # If we have a schema, we need a content-type
        if has_schema and not content_type:
            raise RestAPIRequestContentTypeException(
                detail=f"No content-type specified. Possible value is: {', '.join(accepted_types)}",
                title="Content type not valid for this endpoint.",
            )

        if not content_type:
            return

        content_type_, options = parse_options_header(content_type)

        if content_type_ not in accepted_types:
            raise RestAPIRequestContentTypeException(
                detail=f"Content-Type {content_type_!r} not supported for this endpoint.",
                title="Content type not valid for this endpoint.",
            )

        if (
            inbound_method
            and has_schema
            and content_type_ == "application/json"
            and "charset" in options
            and options["charset"] is not None
            and options["charset"].lower() != "utf-8"
        ):
            # but there are options.
            if options["charset"].lower() != "utf-8":
                raise RestAPIRequestContentTypeException(
                    detail=f"Character set {options['charset']!r} not supported "
                    f"for content-type {content_type_!r}.",
                    title="Content type not valid for this endpoint.",
                )


class PathParamsValidator:
    """Utility class for validating path parameters in API endpoints."""

    @staticmethod
    def validate_marshmallow_schema(
        path_schema: type[Schema],
        path_params: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate path parameters against a Marshmallow schema."""
        try:
            # URL decode the path parameters before validation
            unquoted_params = {k: parse.unquote(v) for k, v in path_params.items()}
            return path_schema().load(unquoted_params)
        except ValidationError as exc:
            raise PathParamsValidator._schema_validation_exception(exc.messages)
        except MKAuthException as exc:
            raise PathParamsValidator._auth_validation_exception(exc.args[0])

    @staticmethod
    def verify_marshmallow_params_presence(path: str, path_schema: type[Schema] | None) -> None:
        """Verifies that URL template parameters match the Marshmallow schema fields

        This works both ways, ensuring that no schema field is defined which is not used in the path and that
        each template-variable in the URL-template has a corresponding field in the schema,
        either globally or locally.

        Args:
            path:
                The URL-Template, for eample: '/user/{username}'

            path_schema:
                A marshmallow schema which is used for path parameter validation.

        Examples:

            In case of success, this function will return nothing.

              >>> from cmk.fields import String
              >>> class Params(Schema):
              ...      bar = String()

              >>> PathParamsValidator.verify_marshmallow_params_presence('/foo/{bar}', Params)
              >>> PathParamsValidator.verify_marshmallow_params_presence('/foo', None)

            Yet, when problems are found, ValueErrors are raised.

              >>> PathParamsValidator.verify_marshmallow_params_presence('/foo', Params)
              Traceback (most recent call last):
              ...
              ValueError: Params {'bar'} not used in path /foo. Found params: set()

              >>> PathParamsValidator.verify_marshmallow_params_presence('/foo/{bar}', None)
              Traceback (most recent call last):
              ...
              ValueError: Params {'bar'} of path /foo/{bar} were not given in schema parameters set()

        Returns:
            Nothing.

        Raises:
            ValueError in case of a mismatch.
        """
        if path_schema is None:
            schema_params = set()
        else:
            schema = path_schema()
            schema_params = set(schema.declared_fields.keys())

        PathParamsValidator.verify_path_params_presence(path, schema_params)

    @staticmethod
    def verify_path_params_presence(path: str, specified_path_params: set[str]) -> None:
        path_params = set(path_parameters(path))
        missing_in_schema = path_params - specified_path_params
        missing_in_path = specified_path_params - path_params

        if missing_in_schema:
            raise PathParamsValidator._missing_schema_parameters_exception(
                missing_in_schema, path, specified_path_params
            )

        if missing_in_path:
            raise PathParamsValidator._unused_schema_parameters_exception(
                missing_in_path, path, path_params
            )

    @staticmethod
    def _missing_schema_parameters_exception(
        missing_params: set[str], path: str, schema_params: set[str]
    ) -> ValueError:
        return ValueError(
            f"Params {missing_params!r} of path {path} were not given in schema parameters "
            f"{schema_params!r}"
        )

    @staticmethod
    def _unused_schema_parameters_exception(
        unused_params: set[str], path: str, path_params: set[str]
    ) -> ValueError:
        return ValueError(
            f"Params {unused_params!r} not used in path {path}. Found params: {path_params!r}"
        )

    @staticmethod
    def _schema_validation_exception(error_messages: list | dict) -> RestAPIPathValidationException:
        return RestAPIPathValidationException(
            title=http.client.responses[404],
            detail=f"These fields have problems: {_format_fields(error_messages)}",
            fields=FIELDS(
                error_messages if isinstance(error_messages, dict) else {"exc": error_messages},
            ),
        )

    @staticmethod
    def _auth_validation_exception(message: str) -> RestAPIForbiddenException:
        return RestAPIForbiddenException(
            title=http.client.responses[403],
            detail=message,
        )


class QueryParamsValidator:
    """Utility class for validating query parameters in API endpoints."""

    @staticmethod
    def validate_marshmallow_schema(
        query_schema: type[Schema],
        query_args: MultiDict,
    ) -> dict[str, Any]:
        """Validate query parameters against a Marshmallow schema."""
        try:
            list_fields = tuple(
                {k for k, v in query_schema().fields.items() if isinstance(v, ma_fields.List)}
            )

            processed_args = _filter_profile_headers(_from_multi_dict(query_args, list_fields))

            # Validate with the schema
            return query_schema().load(processed_args)
        except ValidationError as exc:
            raise QueryParamsValidator._schema_validation_exception(exc.messages)
        except MKAuthException as exc:
            raise QueryParamsValidator._auth_validation_exception(exc.args[0])

    @staticmethod
    def _schema_validation_exception(
        error_messages: dict | list,
    ) -> RestAPIQueryPathValidationException:
        return RestAPIQueryPathValidationException(
            title=http.client.responses[400],
            detail=f"These fields have problems: {_format_fields(error_messages)}",
            fields=FIELDS(
                error_messages if isinstance(error_messages, dict) else {"exc": error_messages},
            ),
        )

    @staticmethod
    def _auth_validation_exception(message: str) -> RestAPIForbiddenException:
        return RestAPIForbiddenException(
            title=http.client.responses[403],
            detail=message,
        )


class RequestDataValidator:
    """Utility class for validating request body data in API endpoints."""

    @staticmethod
    def _data_validation_exception(
        error_messages: list | dict,
    ) -> RestAPIRequestDataValidationException:
        """Create a request data validation exception with consistent formatting"""
        return RestAPIRequestDataValidationException(
            title=http.client.responses[400],
            detail=f"These fields have problems: {_format_fields(error_messages)}",
            fields=FIELDS(
                error_messages if isinstance(error_messages, dict) else {"exc": error_messages},
            ),
        )

    @staticmethod
    def _auth_exception(exc_detail: str) -> RestAPIForbiddenException:
        return RestAPIForbiddenException(
            title=http.client.responses[403],
            detail=exc_detail,
        )

    @staticmethod
    def decode_marshmallow_schema(
        content_type: str,
        request_obj: Request,
        request_schema: type[Schema] | None,
    ) -> tuple[Any, str]:
        """Decode and validate request body data."""
        try:
            return decode(content_type, request_obj, request_schema)
        except ValidationError as exc:
            raise RequestDataValidator._data_validation_exception(
                exc.messages,
            )
        except MKAuthException as exc:
            raise RequestDataValidator._auth_exception(exc.args[0])

    @staticmethod
    def _format_pydantic_location(location: Iterable[str | int]) -> str:
        return ".".join(str(loc) for loc in location)

    @staticmethod
    def raise_formatted_pydantic_error(
        validation_error: pydantic.ValidationError,
    ) -> NoReturn:
        """Convert a Pydantic validation error to a RestAPIRequestDataValidationException."""
        # the context may contain the actual exception, which is usually not serializable
        # the msg contains the exception details, which is hopefully enough to understand the issue
        errors = {
            RequestDataValidator._format_pydantic_location(error["loc"]): error
            for error in validation_error.errors(include_context=False)
        }
        raise RestAPIRequestDataValidationException(
            title=http.client.responses[400],
            detail=f"These fields have problems: {_format_fields(errors)}",
            fields=FIELDS(errors),
        ) from validation_error


class HeaderValidator:
    """Utility class for validating HTTP headers in API endpoints."""

    @staticmethod
    def validate_marshmallow_schema(
        header_schema: type[Schema],
        headers: dict,
    ) -> dict:
        """Validate headers against a Marshmallow schema."""
        try:
            return header_schema().load(headers)
        except ValidationError as exc:
            raise HeaderValidator._schema_validation_exception(exc.messages)

    @staticmethod
    def _schema_validation_exception(error_messages: Any) -> RestAPIHeaderSchemaValidationException:
        return RestAPIHeaderSchemaValidationException(
            title=http.client.responses[400],
            detail=f"These fields have problems: {_format_fields(error_messages)}",
            fields=FIELDS(
                error_messages if isinstance(error_messages, dict) else {"exc": error_messages},
            ),
        )

    @staticmethod
    def validate_accept_header(content_type: str | None, accept_mimetypes: MIMEAccept) -> None:
        """Validate the Accept header in the request."""
        if not content_type:
            return  # ignore the accept header, if this endpoint does not return any data

        if not accept_mimetypes:
            raise RestAPIHeaderValidationException(
                title="Not Acceptable",
                detail="Please specify an Accept Header.",
            )

        if not accept_mimetypes.best_match([content_type]):
            raise RestAPIHeaderValidationException(
                title="Not Acceptable",
                detail="Can not send a response with the content type specified in the 'Accept' Header."
                f" Accept Header: {accept_mimetypes}."
                f" Supported content types: [{content_type}]",
            )


class ResponseValidator:
    @staticmethod
    def validate_permissions(
        endpoint: str,
        params: Mapping[str, object],
        permissions_required: permissions.BasePerm | None,
        used_permissions: set[str],
        is_testing: bool = False,
    ) -> None:
        """Validate that all required permissions were used correctly."""
        if permissions_required is None or permissions_required.validate(list(used_permissions)):
            return

        required_permissions = list(used_permissions)
        declared_permissions = permissions_required

        _logger.error(
            "Permission mismatch: %r Params: %s Required: %s Declared: %s",
            endpoint,
            params,
            required_permissions,
            declared_permissions,
        )

        if is_testing:
            raise RestAPIPermissionException(
                title="Permission mismatch",
                detail="There can be some causes for this error:\n"
                "* a permission which was required (successfully) was not declared\n"
                "* a permission which was declared (not optional) was not required\n"
                "* No permission was required at all, although permission were declared\n"
                f"Endpoint: {endpoint}\n"
                f"Params: {params!r}\n"
                f"Required: {required_permissions}\n"
                f"Declared: {declared_permissions}\n",
            )

        raise RestAPIPermissionException(
            title="Permission mismatch",
            detail="See the server logs for more information.",
        )

    @staticmethod
    def validate_response_constraints(
        response: cmk_http.Response,
        output_empty: bool,
        operation_id: str,
        expected_status_codes: list[StatusCodeInt],
    ) -> None:
        """Validate that the response meets all defined constraints."""
        if output_empty and response.status_code < 400 and response.data:
            raise RestAPIResponseException(
                title="Unexpected data was sent.",
                detail=f"Endpoint {operation_id}\nThis is a bug, please report.",
                ext=EXT({"data_sent": str(response.data)}),
            )

        if response.status_code == 204:
            del response.content_type

        if response.status_code not in expected_status_codes:
            raise RestAPIResponseException(
                title=f"Unexpected status code returned: {response.status_code}",
                detail=f"Endpoint {operation_id}",
                ext=EXT(
                    {
                        "The following status codes are allowed for this endpoint": expected_status_codes
                    }
                ),
            )

    @staticmethod
    def validate_marshmallow_schema(
        response: cmk_http.Response,
        response_schema: type[Schema],
    ) -> cmk_http.Response:
        """Validate JSON response against schema and optionally convert it."""
        with tracer.span("response-to-json"):
            try:
                data = json.loads(response.data.decode("utf-8"))
            except json.decoder.JSONDecodeError as exc:
                raise RestAPIResponseException(
                    title="Server was about to send invalid JSON data.",
                    detail="This is an error of the implementation.",
                    ext=EXT(
                        {
                            "errors": str(exc),
                            "orig": response.data,
                        },
                    ),
                )

        with tracer.span("response-schema-validation"):
            try:
                outbound = response_schema().dump(data)
            except ValidationError as exc:
                raise RestAPIResponseException(
                    title="Mismatch between endpoint and internal data format.",
                    detail="This could be due to invalid or outdated configuration, or be an error of the implementation. "
                    "Please check your *.mk files in case you have modified them by hand and run cmk-update-config. "
                    "If the problem persists afterwards, please report a bug.",
                    ext=EXT(
                        {
                            "errors": exc.messages,
                            "debug_data": {"orig": data},
                        },
                    ),
                )

        return outbound

    @staticmethod
    def validate_problem_json(response: cmk_http.Response) -> None:
        """Validate that problem+json responses contain valid JSON."""
        data = response.data.decode("utf-8")
        try:
            json.loads(data)
        except json.JSONDecodeError as exc:
            raise RestAPIResponseException(
                title="Server was about to send an invalid response.",
                detail="This is an error of the implementation.",
                ext=EXT(
                    {
                        "error": str(exc),
                        "orig": data,
                    },
                ),
            )


@dataclasses.dataclass(slots=True)
class PermissionValidator:
    _on_permission_checked: Callable[[str], None]
    """Callback function for when a permission is checked"""
    used_permissions: set[str] = dataclasses.field(default_factory=set)
    """All used permissions during the endpoint execution"""

    @classmethod
    def create(
        cls,
        required_permissions: permissions.BasePerm | None,
        endpoint_repr: str,
        is_testing: bool,
    ) -> Self:
        """Create a permission checker

        Args:
            required_permissions:
                The endpoint's declared required permissions

            endpoint_repr:
                A string representation of the endpoint.

            is_testing:
                Whether the endpoint is executed in a testing context.
        """
        used_permissions = set()

        def on_permission_checked(pname: str) -> None:
            """Collect all checked permissions during execution"""
            if not is_permission_tracking_enabled():
                return

            used_permissions.add(pname)

            if required_permissions is None or pname not in required_permissions:
                _logger.error(
                    "Permission mismatch: Endpoint %r Use of undeclared permission %s",
                    endpoint_repr,
                    pname,
                )

                if is_testing:
                    raise RestAPIPermissionException(
                        title=f"Required permissions ({pname}) not declared for this endpoint.",
                        detail=f"Endpoint: {endpoint_repr}\n"
                        f"Permission: {pname}\n"
                        f"Used permission: {pname}\n"
                        f"Declared: {required_permissions}\n",
                    )

        return cls(_on_permission_checked=on_permission_checked, used_permissions=used_permissions)

    @contextlib.contextmanager
    def track_permissions(self) -> Iterator[None]:
        """Track permissions for the duration of the context."""
        hooks.register_builtin("permission-checked", self._on_permission_checked)
        try:
            with enable_permission_tracking():
                yield
        finally:
            hooks.unregister("permission-checked", self._on_permission_checked)


def _filter_profile_headers(arg_dict: ArgDict) -> ArgDict:
    """Filter the _profile variable from the query string

    Args:
        arg_dict:
            A dict of query string arguments

    Returns:
        A new dict without the '_profile' parameter.


    Examples:

        >>> _filter_profile_headers({'foo': 'bar', '_profile': '1'})
        {'foo': 'bar'}

    """
    return {key: value for key, value in arg_dict.items() if not key.startswith("_profile")}


def _from_multi_dict(multi_dict: MultiDict, list_fields: tuple[str, ...]) -> ArgDict:
    """Transform a MultiDict to a non-heterogenous dict

    Meaning: lists are lists and lists of lenght 1 are scalars.

    Examples:
        >>> _from_multi_dict(MultiDict([('a', '1'), ('a', '2'), ('c', '3'), ('d', '4')]), ('d',))
        {'a': ['1', '2'], 'c': '3', 'd': ['4']}

    Args:
        multi_dict:
            A Werkzeug MultiDict instance.

    Returns:
        A dict.

    """

    ret = {}
    for key, values in multi_dict.to_dict(flat=False).items():
        if len(values) == 1 and key not in list_fields:
            ret[key] = values[0]
        else:
            ret[key] = values
    return ret


def _format_fields(_messages: Iterable[str]) -> str:
    return ", ".join(_messages)
