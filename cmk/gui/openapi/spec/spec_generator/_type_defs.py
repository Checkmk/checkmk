#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from marshmallow import Schema

from cmk.ccc.version import Edition

from cmk.gui.http import HTTPMethod
from cmk.gui.openapi.restful_objects.api_error import ApiError
from cmk.gui.openapi.restful_objects.type_defs import (
    ErrorStatusCodeInt,
    ETagBehaviour,
    OperationObject,
    RawParameter,
    StatusCodeInt,
    TagGroup,
)
from cmk.gui.utils import permission_verification as permissions


@dataclass
class MarshmallowSchemaDefinitions:
    path_params: Sequence[RawParameter] | None
    query_params: Sequence[RawParameter] | None
    request_schema: type[Schema] | None
    response_schema: RawParameter | None
    error_schemas: Mapping[ErrorStatusCodeInt, type[ApiError]]


@dataclass
class SpecEndpoint:
    # TODO: shift the implementation to the respective endpoint implementation
    title: str
    description: str | None
    path: str
    operation_id: str
    family_name: str
    etag: ETagBehaviour | None
    expected_status_codes: set[StatusCodeInt]
    content_type: str | None
    method: HTTPMethod
    status_descriptions: Mapping[StatusCodeInt, str]
    tag_group: TagGroup
    permissions_required: permissions.BasePerm | None
    permissions_description: Mapping[str, str] | None
    does_redirects: bool
    supported_editions: set[Edition] | None


@dataclass
class DocEndpoint:
    path: str
    effective_path: str
    method: str
    family_name: str
    doc_group: TagGroup
    doc_sort_index: int
    operation_object: OperationObject
