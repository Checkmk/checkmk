#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import inspect
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, cast, get_args, get_origin

from cmk.gui.http import HTTPMethod
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.endpoint_model import EndpointModel, SignatureParametersProcessor
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.response import ApiErrorDataclass
from cmk.gui.openapi.framework.versioned_endpoint import (
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    HandlerFunction,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.endpoint_family import endpoint_family_registry, EndpointFamily
from cmk.gui.openapi.restful_objects.type_defs import (
    AcceptFieldType,
    EndpointKey,
    ErrorStatusCodeInt,
    ETagBehaviour,
    LinkRelation,
    StatusCodeInt,
    TagGroup,
)
from cmk.gui.openapi.restful_objects.utils import endpoint_ident, identify_expected_status_codes
from cmk.gui.openapi.restful_objects.validators import PathParamsValidator
from cmk.gui.utils.permission_verification import BasePerm


@dataclass(frozen=True, slots=True)
class RequestEndpoint:
    handler: HandlerFunction
    method: HTTPMethod
    accept: AcceptFieldType
    content_type: str
    etag: ETagBehaviour | None
    operation_id: str
    doc_group: TagGroup
    additional_status_codes: Sequence[StatusCodeInt]
    update_config_generation: bool
    skip_locking: bool
    permissions_required: BasePerm | None


@dataclass(slots=True, frozen=True)
class VersionedSpecEndpoint:
    operation_id: str
    path: str
    family: str
    doc_group: TagGroup
    doc_sort_index: int
    deprecated_werk_id: int | None
    handler: Callable
    error_schemas: Mapping[ErrorStatusCodeInt, type[ApiErrorDataclass]] | None
    status_descriptions: Mapping[StatusCodeInt, str] | None
    additional_status_codes: Sequence[StatusCodeInt] | None
    method: HTTPMethod
    content_type: str
    etag: ETagBehaviour | None
    permissions_required: BasePerm | None
    permissions_description: Mapping[str, str] | None
    accept: AcceptFieldType


@dataclass
class EndpointDefinition:
    metadata: EndpointMetadata
    permissions: EndpointPermissions
    doc: EndpointDoc
    family: EndpointFamily
    handler: EndpointHandler
    behavior: EndpointBehavior
    removed_in_version: APIVersion | None

    @property
    def ident(self) -> str:
        return endpoint_ident(
            method=self.metadata.method,
            route_path=self.metadata.path,
            content_type=self.metadata.content_type,
        )

    @property
    def doc_group(self) -> TagGroup:
        return self.doc.group or self.family.doc_group

    def request_endpoint(self) -> RequestEndpoint:
        """Representation of the endpoint with attributes needed to handle a request"""
        return RequestEndpoint(
            handler=self.handler.handler,
            method=self.metadata.method,
            accept=self.metadata.accept,
            content_type=self.metadata.content_type,
            etag=self.behavior.etag,
            operation_id=f"{self.doc.family}.{self.handler.handler.__name__}",
            doc_group=self.doc_group,
            additional_status_codes=self.handler.additional_status_codes or [],
            update_config_generation=self.behavior.update_config_generation,
            skip_locking=self.behavior.skip_locking,
            permissions_required=self.permissions.required,
        )

    def spec_endpoint(self) -> VersionedSpecEndpoint:
        # TODO: separate models from other attributes
        return VersionedSpecEndpoint(
            operation_id=f"{self.doc.family}.{self.handler.handler.__name__}",
            path=self.metadata.path,
            family=self.doc.family,
            doc_group=self.doc_group,
            doc_sort_index=self.doc.sort_index,
            deprecated_werk_id=self.doc.sort_index,
            handler=self.handler.handler,
            error_schemas=self.handler.error_schemas,
            status_descriptions=self.handler.status_descriptions,
            additional_status_codes=self.handler.additional_status_codes,
            method=self.metadata.method,
            content_type=self.metadata.content_type,
            etag=self.behavior.etag,
            permissions_required=self.permissions.required,
            permissions_description=self.permissions.descriptions,
            accept=self.metadata.accept,
        )


class VersionedEndpointRegistry:
    """Registry for versioned REST API endpoints"""

    def __init__(self):
        self._versions: dict[APIVersion, dict[EndpointKey, EndpointDefinition]] = dict()

    @staticmethod
    def create_endpoint_definition(
        endpoint: VersionedEndpoint, endpoint_family: EndpointFamily, handler: EndpointHandler
    ) -> EndpointDefinition:
        return EndpointDefinition(
            metadata=endpoint.metadata,
            permissions=endpoint.permissions,
            doc=endpoint.doc,
            family=endpoint_family,
            handler=handler,
            behavior=endpoint.behavior,
            removed_in_version=endpoint.removed_in_version,
        )

    @staticmethod
    def endpoint_key(family_name: str, link_relation: LinkRelation) -> tuple[str, LinkRelation]:
        return family_name, link_relation

    # TODO: potentially have to introduce a lookup function
    def register(self, endpoint: VersionedEndpoint) -> None:
        """Register a versioned endpoint

        Registers the endpoint with all its handlers for different API versions.
        """

        endpoint_family = endpoint_family_registry.get(endpoint.doc.family)
        assert endpoint_family is not None
        endpoint_key_ = self.endpoint_key(endpoint_family.name, endpoint.metadata.link_relation)

        for version, handler in endpoint.versions.items():
            version_endpoints = self._versions.setdefault(version, dict())

            if endpoint_key_ in version_endpoints:
                raise RuntimeError(
                    f"Endpoint with key {endpoint_key_}, already has handlers for version {version}"
                )

            version_endpoints[endpoint_key_] = self.create_endpoint_definition(
                endpoint=endpoint,
                endpoint_family=endpoint_family,
                handler=handler,
            )

    def specified_endpoints(self, version: APIVersion) -> Iterator[EndpointDefinition]:
        """Iterate over all endpoints specified for a given API version"""
        for _endpoint_key, endpoint in self._versions.get(version, dict()).items():
            yield endpoint

    def __iter__(self) -> Iterator[EndpointDefinition]:
        """Iterate over all endpoints registered in the registry"""
        for version_endpoints in self._versions.values():
            yield from version_endpoints.values()


def _validate_endpoint_parameters(handler: HandlerFunction) -> None:
    """Validate the parameters of the endpoint handler function"""
    signature = inspect.signature(handler, eval_str=True)
    annotated_parameters = SignatureParametersProcessor.extract_annotated_parameters(signature)
    SignatureParametersProcessor.validate_parameters(annotated_parameters)

    if "body" in signature.parameters:
        body = signature.parameters["body"]
        if body.kind not in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            raise ValueError("Invalid parameter kind for request body")

        if body.annotation is inspect.Parameter.empty:
            raise ValueError("Missing annotation for request body")

        body_type = body.annotation
        while get_origin(body_type) is Annotated:
            body_type = get_args(body_type)[0]

        if not dataclasses.is_dataclass(body_type):
            raise ValueError("Request body annotation must be a dataclass")


def _type_contains_api_omitted(type_: type) -> bool:
    """Check if the type contains ApiOmitted"""
    if type_ is ApiOmitted:
        return True

    for arg in get_args(type_):
        if _type_contains_api_omitted(arg):
            return True

    return False


def _validate_defaults(
    operation_id: str,
    path: str,
    schema: type,
    other_defaults_allowed: bool,
) -> None:
    """Validate the model defaults"""
    if not dataclasses.is_dataclass(schema):
        raise ValueError(f"Endpoint {operation_id}: expected a dataclass annotation for `{path}`.")

    for field in dataclasses.fields(schema):
        if isinstance(field.type, str):
            raise ValueError(
                f"Endpoint {operation_id} uses a string annotation for `{path}.{field.name}`."
            )

        # without the cast we would have to check for GenericAlias, UnionType, DataclassInstance
        # and Literal. The dataclass instance check also has no proper return type
        type_ = cast(type, field.type)
        if dataclasses.is_dataclass(type_):
            _validate_defaults(
                operation_id, f"{path}.{field.name}", field.type, other_defaults_allowed
            )
            continue

        if _type_contains_api_omitted(type_):
            if field.default is not dataclasses.MISSING:
                raise ValueError(
                    f"Endpoint {operation_id} uses `default` for `{path}.{field.name}`. Use `default_factory=ApiOmitted` instead."
                )
            if field.default_factory is dataclasses.MISSING:
                raise ValueError(
                    f"Endpoint {operation_id} must set `default_factory=ApiOmitted` for `{path}.{field.name}`."
                )
            if field.default_factory is not ApiOmitted:
                raise ValueError(
                    f"Endpoint {operation_id} uses incorrect `default_factory` for `{path}.{field.name}`. Use `default=ApiOmitted` instead."
                )
            continue

        if other_defaults_allowed:
            continue

        if field.default is not dataclasses.MISSING:
            raise ValueError(
                f"Endpoint {operation_id} uses forbidden `default` for `{path}.{field.name}`."
            )
        if field.default_factory is not dataclasses.MISSING:
            raise ValueError(
                f"Endpoint {operation_id} uses forbidden `default_factory` for `{path}.{field.name}`."
            )


def _validate_endpoint_response_schema(endpoint: RequestEndpoint, model: EndpointModel) -> None:
    """Validate the response of the endpoint"""
    if model.response_body_type is None:
        if endpoint.content_type == "application/json":
            raise ValueError(
                f"Endpoint {endpoint.operation_id} with content type {endpoint.content_type} "
                f"requires a response schema."
            )
        return

    if endpoint.content_type != "application/json":
        raise ValueError(
            f"Endpoint {endpoint.operation_id} with content type {endpoint.content_type} "
            f"should not have a response schema."
        )

    _validate_defaults(
        endpoint.operation_id, "response", model.response_body_type, other_defaults_allowed=False
    )


def _validate_endpoint_request_schema(endpoint: RequestEndpoint, model: EndpointModel) -> None:
    if model.request_body_type is None:
        return

    if endpoint.method in ("delete", "get"):
        # add an exception list if necessary but this should serve as double check that this is
        # intended
        raise ValueError(
            f"Endpoint {endpoint.operation_id} with method {endpoint.method} "
            f"should not have a request schema according to RFC"
        )

    _validate_defaults(
        endpoint.operation_id, "body", model.request_body_type, other_defaults_allowed=True
    )


def _validate_endpoint_error_schemas(
    endpoint: RequestEndpoint,
    error_schemas: Mapping[ErrorStatusCodeInt, type[ApiErrorDataclass]] | None,
) -> None:
    if not error_schemas:
        return

    for error_status_code in error_schemas:
        if error_status_code < 400:
            raise ValueError(
                f"Endpoint {endpoint.operation_id} has error schema for status code "
                f"{error_status_code} but this is not allowed."
            )


def _validate_endpoint_status_descriptions(
    endpoint: RequestEndpoint,
    model: EndpointModel,
    status_descriptions: Mapping[StatusCodeInt, str] | None,
) -> None:
    if not status_descriptions:
        return

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

    for status_code in status_descriptions:
        if status_code not in allowed_status_codes:
            raise ValueError(
                f"Endpoint {endpoint.operation_id} has custom status description for status code "
                f"{status_code}, which is not used/declared."
            )


def validate_endpoint_definition(endpoint_definition: EndpointDefinition) -> None:
    """Validate a versioned endpoint configuration"""
    # TODO: this function should be invoked for custom endpoints
    endpoint = endpoint_definition.request_endpoint()
    try:
        _validate_endpoint_parameters(endpoint.handler)
    except ValueError as e:
        raise ValueError(f"Invalid handler for endpoint {endpoint.operation_id}: {e}") from None

    model = EndpointModel.build(endpoint.handler)
    _validate_endpoint_response_schema(endpoint, model)
    _validate_endpoint_request_schema(endpoint, model)
    _validate_endpoint_error_schemas(endpoint, endpoint_definition.handler.error_schemas)
    _validate_endpoint_status_descriptions(
        endpoint, model, endpoint_definition.handler.status_descriptions
    )
    PathParamsValidator.verify_path_params_presence(
        endpoint_definition.metadata.path, set(model.path_parameters)
    )


versioned_endpoint_registry = VersionedEndpointRegistry()
