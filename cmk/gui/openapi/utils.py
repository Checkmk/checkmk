#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from typing import Any, Literal, NewType
from wsgiref.types import StartResponse, WSGIEnvironment

import docstring_parser
from werkzeug.exceptions import HTTPException

from cmk.utils.encoding import json_encode

from cmk.gui.http import Response
from cmk.gui.openapi.restful_objects.type_defs import Serializable

FIELDS = NewType("FIELDS", dict[str, Any])
EXT = NewType("EXT", dict[str, Any])


def problem(
    status: int = 400,
    title: str = "A problem occurred.",
    detail: str = "",
    type_: str | None = None,
    fields: FIELDS | None = None,
    ext: EXT | None = None,
) -> Response:
    problem_dict = {
        "title": title,
        "status": status,
        "detail": detail,
    }
    if type_ is not None:
        problem_dict["type"] = type_

    if fields is not None:
        problem_dict["fields"] = fields

    if ext is not None:
        problem_dict["ext"] = ext

    return serve_json(
        problem_dict,
        status=status,
        content_type="application/problem+json",
    )


class GeneralRestAPIException(HTTPException):
    def __init__(
        self,
        status: int,
        title: str,
        detail: str,
        fields: FIELDS | None = None,
        ext: EXT | None = None,
    ) -> None:
        self.code: int = status
        self.description: str = title
        self.detail = detail
        self.fields = fields
        self.ext = ext
        super().__init__(description=title)

    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> Iterable[bytes]:
        return self.to_problem()(environ, start_response)

    def to_problem(self) -> Response:
        return problem(
            status=self.code,
            title=self.description,
            detail=self.detail,
            fields=self.fields,
            ext=self.ext,
        )


# ==================================================== REQUEST exceptions
class RestAPIRequestGeneralException(GeneralRestAPIException):
    def __init__(
        self,
        status: Literal[400, 401, 403, 404, 406, 415],
        title: str,
        detail: str,
        fields: FIELDS | None = None,
        ext: EXT | None = None,
    ) -> None:
        super().__init__(status, title, detail, fields, ext)


class RestAPIRequestContentTypeException(RestAPIRequestGeneralException):
    status: Literal[415] = 415

    def __init__(
        self,
        title: str,
        detail: str,
        *,
        fields: FIELDS | None = None,
        ext: EXT | None = None,
    ) -> None:
        super().__init__(RestAPIRequestContentTypeException.status, title, detail, fields, ext)


class RestAPIPathValidationException(RestAPIRequestGeneralException):
    status: Literal[404] = 404

    def __init__(
        self,
        title: str,
        detail: str,
        *,
        fields: FIELDS | None = None,
        ext: EXT | None = None,
    ) -> None:
        super().__init__(RestAPIPathValidationException.status, title, detail, fields, ext)


class RestAPIHeaderSchemaValidationException(RestAPIRequestGeneralException):
    status: Literal[400] = 400

    def __init__(
        self,
        title: str,
        detail: str,
        *,
        fields: FIELDS | None = None,
        ext: EXT | None = None,
    ) -> None:
        super().__init__(RestAPIHeaderSchemaValidationException.status, title, detail, fields, ext)


class RestAPIHeaderValidationException(RestAPIRequestGeneralException):
    status: Literal[406] = 406

    def __init__(
        self,
        title: str,
        detail: str,
        *,
        fields: FIELDS | None = None,
        ext: EXT | None = None,
    ) -> None:
        super().__init__(RestAPIHeaderValidationException.status, title, detail, fields, ext)


class RestAPIQueryPathValidationException(RestAPIRequestGeneralException):
    status: Literal[400] = 400

    def __init__(
        self,
        title: str,
        detail: str,
        *,
        fields: FIELDS | None = None,
        ext: EXT | None = None,
    ) -> None:
        super().__init__(RestAPIQueryPathValidationException.status, title, detail, fields, ext)


class RestAPIRequestDataValidationException(RestAPIRequestGeneralException):
    status: Literal[400] = 400

    def __init__(
        self,
        title: str,
        detail: str,
        *,
        fields: FIELDS | None = None,
        ext: EXT | None = None,
    ) -> None:
        super().__init__(RestAPIRequestDataValidationException.status, title, detail, fields, ext)


class RestAPIWatoDisabledException(RestAPIRequestGeneralException):
    status: Literal[403] = 403

    def __init__(
        self,
        title: str,
        detail: str,
        *,
        fields: FIELDS | None = None,
        ext: EXT | None = None,
    ) -> None:
        super().__init__(RestAPIWatoDisabledException.status, title, detail, fields, ext)


# ==================================================== PERMISSION Exceptions
class RestAPIForbiddenException(RestAPIRequestGeneralException):
    status: Literal[403] = 403

    def __init__(
        self,
        title: str,
        detail: str,
        *,
        fields: FIELDS | None = None,
        ext: EXT | None = None,
    ) -> None:
        super().__init__(RestAPIForbiddenException.status, title, detail, fields, ext)


class RestAPIPermissionException(GeneralRestAPIException):
    status: Literal[500] = 500

    def __init__(
        self,
        title: str,
        detail: str,
        *,
        fields: FIELDS | None = None,
        ext: EXT | None = None,
    ) -> None:
        super().__init__(RestAPIPermissionException.status, title, detail, fields, ext)


# ==================================================== RESPONSE Exceptions
class RestAPIResponseGeneralException(GeneralRestAPIException):
    def __init__(
        self,
        status: Literal[400, 500],
        title: str,
        detail: str,
        fields: FIELDS | None = None,
        ext: EXT | None = None,
    ) -> None:
        super().__init__(status, title, detail, fields, ext)


class RestAPIResponseException(RestAPIResponseGeneralException):
    status: Literal[500] = 500

    def __init__(
        self,
        title: str,
        detail: str,
        *,
        fields: FIELDS | None = None,
        ext: EXT | None = None,
    ) -> None:
        super().__init__(RestAPIResponseException.status, title, detail, fields, ext)


class ProblemException(HTTPException):
    def __init__(
        self,
        status: int = 400,
        title: str = "A problem occured.",
        detail: str = "",
        type_: str | None = None,
        fields: FIELDS | None = None,
        ext: EXT | None = None,
    ):
        """
        This exception is holds arguments that are going to be passed to the
        `problem` function to generate a proper response.
        """
        super().__init__(description=title)
        # These two are named as such for HTTPException compatibility.
        self.code: int = status
        self.description: str = title

        self.detail = detail
        self.type = type_
        self.ext = ext
        self.fields = fields

    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> Iterable[bytes]:
        return self.to_problem()(environ, start_response)

    def to_problem(self) -> Response:
        return problem(
            status=self.code,
            title=self.description,  # same as title
            detail=self.detail,
            type_=self.type,
            fields=self.fields,
            ext=self.ext,
        )


def param_description(
    string: str | None,
    param_name: str,
    errors: Literal["raise", "ignore"] = "raise",
) -> str | None:
    """Get a param description of a docstring.

    Args:
        string:
            The docstring from which to extract the parameter description.

        param_name:
            The name of the parameter.

        errors:
            Either 'raise' or 'ignore'.

    Examples:

        If a docstring is given, there are a few possibilities.

            >>> from cmk.gui.watolib.activate_changes import activate_changes_start
            >>> param_description(activate_changes_start.__doc__, 'force_foreign_changes')
            'Will activate changes even if the user who made those changes is not the currently logged in user.'

            >>> param_description(param_description.__doc__, 'string')
            'The docstring from which to extract the parameter description.'

            >>> param_description(param_description.__doc__, 'foo', errors='ignore')

            >>> param_description(param_description.__doc__, 'foo', errors='raise')
            Traceback (most recent call last):
            ...
            ValueError: Parameter 'foo' not found in docstring.

        There are cases, when no docstring is assigned to a function.

            >>> param_description(None, 'foo', errors='ignore')

            >>> param_description(None, 'foo', errors='raise')
            Traceback (most recent call last):
            ...
            ValueError: No docstring was given.

    Returns:
        The description of the parameter, if possible.

    """
    if string is None:
        if errors == "raise":
            raise ValueError("No docstring was given.")
        return None

    docstring = docstring_parser.parse(string)
    for param in docstring.params:
        if param.arg_name == param_name and param.description is not None:
            return param.description.replace("\n", " ")
    if errors == "raise":
        raise ValueError(f"Parameter {param_name!r} not found in docstring.")
    return None


def serve_json(
    data: Serializable,
    content_type: str = "application/json",
    status: int = 200,
    profile: dict[str, str] | None = None,
) -> Response:
    if profile is not None:
        content_type += f';profile="{profile}"'
    response = Response()
    response.status_code = status
    response.set_content_type(content_type)
    response.set_data(json_encode(data))
    return response
