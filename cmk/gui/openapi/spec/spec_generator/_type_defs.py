#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from marshmallow import Schema

from cmk.gui.http import HTTPMethod
from cmk.gui.openapi.restful_objects.api_error import ApiError
from cmk.gui.openapi.restful_objects.type_defs import (
    ErrorStatusCodeInt,
    ETagBehaviour,
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
    func: Callable
    path: str
    operation_id: str
    family_name: str | None
    etag: ETagBehaviour | None
    expected_status_codes: set[StatusCodeInt]
    content_type: str
    method: HTTPMethod
    status_descriptions: Mapping[StatusCodeInt, str]
    tag_group: TagGroup
    permissions_required: permissions.BasePerm | None
    permissions_description: Mapping[str, str] | None
    does_redirects: bool
