#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Activate changes

When changes are activated, Checkmk transfers the current configuration status to the ongoing
monitoring.

Changes in the configuration - adding a new host, for example - will initially have no effect
on the monitoring. Changes must first be activated, which will bring all changes that you have
accumulated since the last activation as a "bundle" into the operational monitoring.

You can find an introduction to the configuration of Checkmk including activation of changes in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato.html).
"""

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any
from urllib.parse import urlparse

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.http import request, Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.activate_changes.request_schemas import ActivateChanges
from cmk.gui.openapi.endpoints.activate_changes.response_schemas import (
    ActivationRunCollection,
    ActivationRunResponse,
    ActivationStatusResponse,
    PendingChangesCollection,
)
from cmk.gui.openapi.endpoints.utils import may_fail
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject, LinkType
from cmk.gui.openapi.utils import ProblemException, serve_json
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.activate_changes import (
    activate_changes_start,
    ActivationRestAPIResponseExtensions,
    get_activation_ids,
    get_pending_changes,
    get_restapi_response_for_activation_id,
    load_activate_change_manager_with_id,
    MKLicensingError,
)

from cmk import fields

ACTIVATION_ID = {
    "activation_id": fields.String(
        description="The activation-id.",
        example="d3b07384d113e0ec49eaa6238ad5ff00",
        required=True,
    ),
}

# NOTE: These are not needed for the activation of changes, but are asked for different queries
RO_PERMISSIONS = permissions.Undocumented(
    permissions.AnyPerm(
        [
            permissions.Perm("general.see_all"),
            permissions.OkayToIgnorePerm("bi.see_all"),
            permissions.OkayToIgnorePerm("mkeventd.seeall"),
        ]
    ),
)

PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.activate"),
        RO_PERMISSIONS,  # to make perm system happy
    ]
)


@Endpoint(
    constructors.domain_type_action_href("activation_run", "activate-changes"),
    "cmk/activate",
    method="post",
    status_descriptions={
        200: "Activation has been started, but not completed (if you need to wait for completion, see documentation for this endpoint).",
        303: (
            "The activation has been started and is still running. Redirecting to the "
            "'Wait for completion' endpoint."
        ),
        401: (
            "The API user may not activate another users changes, "
            "or the user may and activation was not forced explicitly."
        ),
        403: "Activation not possible because of licensing issues.",
        409: "Some sites could not be activated.",
        422: "There are no changes to be activated.",
        423: "There is already an activation running.",
    },
    additional_status_codes=[303, 401, 403, 409, 422, 423],
    etag="input",
    request_schema=ActivateChanges,
    response_schema=ActivationRunResponse,
    permissions_required=permissions.AllPerm(
        [
            permissions.Perm("wato.activate"),
            permissions.Optional(permissions.Perm("wato.activateforeign")),
            RO_PERMISSIONS,  # to make perm system happy
        ]
    ),
)
def activate_changes(params: Mapping[str, Any]) -> Response:
    """Activate pending changes

    This endpoint will start an asynchronous background job that will activate all pending changes.
    It will either return a response immediately (when redirect=False) which includes the ID for
    the just triggered activation run or will redirect (when redirect=True) to the "Wait for
    completion" endpoint and only return a response when the background job is completed.
    The relevant ETag for the current set of pending changes can be obtained from the 'Show all
    pending changes' endpoint. However, if there are alterations to the list of pending changes, a
    new query to the endpoint will be needed to acquire the updated ETag.
    """
    user.need_permission("wato.activate")
    body = params["body"]
    sites = body["sites"]
    constructors.require_etag(constructors.hash_of_dict(get_pending_changes()))
    with (
        may_fail(MKUserError),
        may_fail(MKAuthException, status=401),
        may_fail(MKLicensingError, status=403),
    ):
        activation_response = activate_changes_start(
            sites=sites,
            source="REST API",
            comment=None,
            force_foreign_changes=body["force_foreign_changes"],
            debug=active_config.debug,
        )

    if body["redirect"]:
        wait_for = _completion_link(activation_response.activation_id)
        response = Response(status=303)
        response.location = urlparse(wait_for["href"]).path
        return response

    return serve_json(_activation_run_domain_object(activation_response))


def _completion_link(activation_id: str) -> LinkType:
    return constructors.link_endpoint(
        "cmk.gui.openapi.endpoints.activate_changes",
        "cmk/wait-for-completion",
        parameters={"activation_id": activation_id},
    )


def _activation_run_domain_object(
    activation_response: ActivationRestAPIResponseExtensions,
) -> DomainObject:
    return constructors.domain_object(
        domain_type="activation_run",
        identifier=activation_response.activation_id,
        title=(
            "Activation status: In progress."
            if activation_response.is_running
            else "Activation status: Complete."
        ),
        extensions=asdict(activation_response),
        deletable=False,
        editable=False,
        links=(
            [_completion_link(activation_response.activation_id)]
            if activation_response.is_running
            else []
        ),
    )


@Endpoint(
    constructors.object_action_href("activation_run", "{activation_id}", "wait-for-completion"),
    "cmk/wait-for-completion",
    method="get",
    status_descriptions={
        204: "The activation has been completed.",
        302: (
            "The activation is still running. Redirecting to the 'Wait for completion' endpoint."
        ),
        404: "There is no running activation with this activation_id.",
    },
    path_params=[ACTIVATION_ID],
    additional_status_codes=[302],
    permissions_required=PERMISSIONS,
    output_empty=True,
)
def activate_changes_wait_for_completion(params: Mapping[str, Any]) -> Response:
    """Wait for activation completion

    This endpoint will periodically redirect on itself to prevent timeouts.
    """
    user.need_permission("wato.activate")
    activation_id = params["activation_id"]

    try:
        manager = load_activate_change_manager_with_id(activation_id)
    except MKUserError:
        raise ProblemException(
            status=404,
            title="The requested activation was not found",
            detail=f"Could not find an activation with id {activation_id!r}.",
        )

    if manager.is_running():
        response = Response(status=302)
        response.location = urlparse(request.url).path
        return response

    return Response(status=204)


@Endpoint(
    constructors.object_href("activation_run", "{activation_id}"),
    "cmk/show",
    method="get",
    path_params=[ACTIVATION_ID],
    status_descriptions={
        404: "There is no running activation with this activation_id.",
    },
    permissions_required=PERMISSIONS,
    response_schema=ActivationStatusResponse,
)
def show_activation(params: Mapping[str, Any]) -> Response:
    """Show the activation status

    If the activation is still running a link to the wait-for-completion resource for the activation job is included.
    """
    user.need_permission("wato.activate")
    activation_id = params["activation_id"]

    try:
        activation_response = get_restapi_response_for_activation_id(activation_id)
    except MKUserError:
        raise ProblemException(
            status=404,
            title="The requested activation was not found",
            detail=f"Could not find an activation with id {activation_id!r}.",
        )

    return serve_json(_activation_run_domain_object(activation_response))


@Endpoint(
    constructors.collection_href("activation_run", "running"),
    "cmk/run",
    method="get",
    permissions_required=RO_PERMISSIONS,
    response_schema=ActivationRunCollection,
)
def list_activations(params: Mapping[str, Any]) -> Response:
    """Show all currently running activations"""

    value = []
    for activation_id in get_activation_ids():
        try:
            value.append(
                _activation_run_domain_object(get_restapi_response_for_activation_id(activation_id))
            )
        except MKUserError:
            pass

    return serve_json(constructors.collection_object(domain_type="activation_run", value=value))


@Endpoint(
    constructors.collection_href("activation_run", "pending_changes"),
    "cmk/pending-activation-changes",
    method="get",
    etag="output",
    permissions_required=RO_PERMISSIONS,
    response_schema=PendingChangesCollection,
)
def list_pending_changes(params: Mapping[str, Any]) -> Response:
    """Show all pending changes"""

    pending_changes = get_pending_changes()
    response = serve_json(
        {
            "id": "activation_run",
            "domainType": "activation_run",
            "links": [
                constructors.link_endpoint(
                    module_name="cmk.gui.openapi.endpoints.activate_changes",
                    rel="cmk/activate",
                    parameters={},
                )
            ],
            "value": [asdict(change) for change in pending_changes.values()],
        }
    )
    return constructors.response_with_etag_created_from_dict(response, pending_changes)


def register(endpoint_registry: EndpointRegistry, ignore_duplicates: bool) -> None:
    endpoint_registry.register(activate_changes, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(
        activate_changes_wait_for_completion, ignore_duplicates=ignore_duplicates
    )
    endpoint_registry.register(show_activation, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(list_activations, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(list_pending_changes, ignore_duplicates=ignore_duplicates)
