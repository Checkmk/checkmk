#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Build links and paths to registered versioned endpoints.

These helpers locate an endpoint by its (family, link_relation) pair and produce
either a URL path (for redirect ``Location`` headers) or a full ``LinkModel``
(for HATEOAS response bodies).
"""

import dataclasses
import inspect
from collections.abc import Callable, Mapping
from functools import lru_cache
from typing import cast, Literal
from urllib.parse import quote, urlencode

from cmk.ccc.site import omd_site
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.endpoint_model import Parameters, SignatureParametersProcessor
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.framework.model.omitted import ApiOmitted
from cmk.gui.openapi.framework.registry import EndpointDefinition
from cmk.gui.openapi.restful_objects.type_defs import EndpointFamilyName, LinkRelation
from cmk.gui.openapi.versioned_endpoint_map import discover_endpoints


class EndpointLinkNotFoundError(LookupError):
    """No endpoint matches the requested family + link relation at any eligible version."""


class EndpointLinkParameterError(ValueError):
    """A parameter passed to link/path generation is unknown or invalid."""


@dataclasses.dataclass(frozen=True, slots=True)
class _HandlerInfo:
    """Cached parameter classification and body flag for a handler function."""

    params: Parameters
    has_body: bool


@lru_cache(maxsize=64)
def _inspect_handler(handler: Callable[..., object]) -> _HandlerInfo:
    """Extract parameter classification and body presence from handler annotations."""
    sig = inspect.signature(handler, eval_str=True)
    annotated = SignatureParametersProcessor.extract_annotated_parameters(sig)
    params = SignatureParametersProcessor.parse_parameters(annotated)
    return _HandlerInfo(params=params, has_body="body" in sig.parameters)


def _resolve(
    family: EndpointFamilyName,
    link_relation: LinkRelation,
    version: APIVersion,
) -> EndpointDefinition:
    """Look up an endpoint."""
    for endpoint in discover_endpoints(version).values():
        if (
            isinstance(endpoint, EndpointDefinition)
            and endpoint.family.name == family
            and endpoint.metadata.link_relation == link_relation
        ):
            return endpoint
    raise EndpointLinkNotFoundError(
        f"No endpoint found for {family=!r}, {link_relation=!r} at {version=!r}"
    )


def _fill(path: str, parameters: Mapping[str, str], handler_params: Parameters) -> str:
    """Fill a path template using handler-annotated parameter classification.

    Path parameters (``PathParam``) fill ``{placeholder}``s in the template — the
    template's placeholder names must match the handler's parameter names, so
    path values are keyed by the original parameter name even when a ``PathParam``
    declares an ``alias`` (the alias is only used on the user-facing side).
    Query parameters (``QueryParam``) are appended as a query string.
    Unknown parameters raise :class:`EndpointLinkParameterError`.
    """
    # Map user-facing key (alias or name) → original parameter name for the path;
    # queries can use the user-facing key directly since ``urlencode`` just
    # serializes whatever keys we hand it.
    path_key_to_name = {(param.alias or name): name for name, param in handler_params.path.items()}
    query_names = {param.alias or name for name, param in handler_params.query.items()}

    path_values: dict[str, str] = {}
    query_values: dict[str, str] = {}
    for key, value in parameters.items():
        if key in path_key_to_name:
            path_values[path_key_to_name[key]] = quote(value, safe="")
        elif key in query_names:
            query_values[key] = value
        else:
            raise EndpointLinkParameterError(
                f"Unknown parameter {key!r}. "
                f"Known path parameters: {sorted(path_key_to_name)}, "
                f"known query parameters: {sorted(query_names)}"
            )

    missing = {
        param.alias or name
        for name, param in handler_params.path.items()
        if param.default is dataclasses.MISSING and name not in path_values
    }
    if missing:
        raise EndpointLinkParameterError(f"Missing path parameters: {sorted(missing)}")

    filled = path.format(**path_values)
    if query_values:
        filled = f"{filled}?{urlencode(query_values)}"
    return filled


def _validate_no_required_headers(handler_params: Parameters) -> None:
    """Raise if the handler requires header parameters that links cannot carry."""
    required = [
        name
        for name, param in handler_params.headers.items()
        if param.default is dataclasses.MISSING
    ]
    if required:
        raise EndpointLinkParameterError(
            f"Endpoint requires header parameters {required!r} which cannot be provided via URL"
        )


def _validate_body(info: _HandlerInfo, body: Mapping[str, object] | None) -> None:
    """Ensure the provided body matches the handler's body expectation."""
    if info.has_body:
        if body is None:
            raise EndpointLinkParameterError(
                "Endpoint requires a request body but none was provided"
            )
    elif body is not None:
        raise EndpointLinkParameterError(
            "body provided but the endpoint does not accept a request body"
        )


def _build_path(
    endpoint: EndpointDefinition,
    version: APIVersion,
    parameters: Mapping[str, str] | None = None,
) -> tuple[str, _HandlerInfo]:
    """Build the URL path for an already-resolved endpoint.

    Returns the path and the cached handler info so callers can inspect
    ``has_body`` without a second lookup.
    """
    info = _inspect_handler(endpoint.handler.handler)
    _validate_no_required_headers(info.params)
    href = _fill(endpoint.metadata.path, parameters or {}, info.params)
    path = f"/{omd_site()}/check_mk/api/{version.value}/{href.lstrip('/')}"
    return path, info


def path_to_endpoint(
    family: EndpointFamilyName,
    link_relation: LinkRelation,
    version: APIVersion,
    parameters: Mapping[str, str] | None = None,
) -> str:
    """Return the URL path for a registered versioned endpoint.

    Use this for ``response.location`` redirects. For a full HATEOAS link
    (with rel/method/type/absolute href) use :func:`link_to_endpoint`.

    The ``parameters`` mapping is split by inspecting the handler function's
    ``PathParam`` / ``QueryParam`` annotations: annotated path parameters fill
    ``{placeholder}``s in the path template, annotated query parameters are
    appended as a query string. Unrecognised keys are rejected.

    Raises:
        EndpointLinkNotFoundError: the requested version has no endpoint
            matching ``(family, link_relation)``.
        EndpointLinkParameterError: a parameter key is unknown, a required
            path parameter has no value in ``parameters``, the endpoint
            requires header parameters that cannot be encoded in a URL, or the
            endpoint expects a request body (which a path cannot carry — use
            :func:`link_to_endpoint` with ``body`` instead).
    """
    endpoint = _resolve(family, link_relation, version)
    path, info = _build_path(endpoint, version, parameters)
    _validate_body(info, None)
    return path


def link_to_endpoint(
    family: EndpointFamilyName,
    link_relation: LinkRelation,
    version: APIVersion,
    host_url: str,
    parameters: Mapping[str, str] | None = None,
    body: Mapping[str, object] | None = None,
) -> LinkModel:
    """Return a :class:`LinkModel` (with absolute href) for a registered endpoint.

    Use this for HATEOAS links in response bodies. For a redirect
    ``Location`` header use :func:`path_to_endpoint`.

    ``host_url`` is the scheme+host (e.g. ``https://example.com/``) that the
    returned ``href`` should be prefixed with.

    The ``parameters`` mapping is split by inspecting the handler function's
    ``PathParam`` / ``QueryParam`` annotations: annotated path parameters fill
    ``{placeholder}``s in the path template, annotated query parameters are
    appended as a query string. Unrecognised keys are rejected.

    If the endpoint expects a request body, ``body`` is included in the
    returned :class:`LinkModel`.

    Raises:
        EndpointLinkNotFoundError: the requested version has no endpoint
            matching ``(family, link_relation)``.
        EndpointLinkParameterError: a parameter key is unknown, a required
            path parameter has no value in ``parameters``, the endpoint
            requires header parameters that cannot be encoded in a URL, the
            endpoint expects a request body but ``body`` is not provided, or
            ``body`` is provided for an endpoint that has no request body.
    """
    endpoint = _resolve(family, link_relation, version)
    path, info = _build_path(endpoint, version, parameters)
    _validate_body(info, body)
    absolute = f"{host_url.rstrip('/')}{path}"
    method = cast(Literal["GET", "POST", "PUT", "DELETE"], endpoint.metadata.method.upper())
    return LinkModel(
        rel=endpoint.metadata.link_relation,
        href=absolute,
        method=method,
        type=endpoint.metadata.content_type or "application/json",
        domainType="link",
        body_params=body if body is not None else ApiOmitted(),
    )
