#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"

import http.client
from typing import Any

from marshmallow import Schema

from cmk.ccc.archive import (
    CheckmkTarArchive,
    NotAValidArchive,
    SecurityViolation,
    UnpackedArchiveTooLargeError,
)
from cmk.gui.http import Request
from cmk.gui.openapi.utils import (
    RestAPIRequestContentTypeException,
    RestAPIRequestDataValidationException,
)


def json_decoder(request: Request, request_schema: type[Schema] | None) -> dict[str, Any] | None:
    if not request_schema:
        return None

    json_data: dict[str, Any] = {}

    if request.get_data(cache=True):
        json_data = request.json or {}

    return request_schema().load(json_data)


def binary_decoder(request: Request) -> bytes | None:
    data = request.get_data(cache=True)
    return bytes(data) if data else None


def gzip_decoder(request: Request, request_schema: type[Schema] | None) -> Any:
    tgz = binary_decoder(request)
    try:
        assert isinstance(tgz, bytes)
        CheckmkTarArchive.validate_bytes(tgz)

    except (UnpackedArchiveTooLargeError, SecurityViolation) as err:
        raise RestAPIRequestDataValidationException(
            title=http.client.responses[400],
            detail=str(err),
        )
    except (NotAValidArchive, Exception):
        raise RestAPIRequestDataValidationException(
            title=http.client.responses[400],
            detail="Payload is not a valid .tar.gz file",
        )

    return tgz


def decode(content_type: str, request: Request, request_schema: type[Schema] | None) -> Any:
    registered_decoders = {
        "application/json": json_decoder,
        "application/gzip": gzip_decoder,
    }

    if content_type not in registered_decoders:
        raise RestAPIRequestContentTypeException(
            "Unable to decode content type",
            f"No suitable decoder for content-type '{content_type}'",
        )

    concrete_decoder = registered_decoders[content_type]

    return concrete_decoder(request, request_schema)
