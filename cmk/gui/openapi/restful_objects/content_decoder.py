#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import http.client
import io
import tarfile
from typing import Any

from marshmallow import Schema

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
    """
    Please note that operating with .tar.gz archives may result in a security risk.
    Never extract files from untrusted sources without prior inspection. It is possible
    that the contained files have absolute paths (starting with `/`) or relative paths
    (starting with `..`) that escape the target directory.

    It must be verified prior to extraction that none of the following paths point
    outside the target directory:
    * Absolute paths
    * Relative paths
    * Symbolic links

    It is also possible that a malicious small .tar.gz file can become a very large tar
    file that could excess RAM or disk-space.

    Read more:
    CVE-2007-4559 - python: tarfile module directory traversal
    https://bugzilla.redhat.com/show_bug.cgi?id=263261

    """
    tgz = binary_decoder(request)

    try:
        assert isinstance(tgz, bytes)
        with tarfile.open(fileobj=io.BytesIO(tgz), mode="r:gz"):
            ...

    except Exception:
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
