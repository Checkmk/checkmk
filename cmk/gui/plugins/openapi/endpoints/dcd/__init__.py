#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Dynamic Configuration Daemon (DCD)

It is becoming increasingly common in cloud and container environments that hosts to be
monitored can not only be generated but also expire automatically. Keeping up to date with
the monitoring’s configuration in such an environment is no longer possible manually.
Classic infrastructures such as for example, VMware clusters can also be very dynamic,
and even if manual care is still possible it is in any case cumbersome.

The commercial editions of Checkmk support you in this process with a smart tool the
Dynamic Configuration Daemon or DCD for short. The dynamic configuration of hosts means that,
based on information from monitoring AWS, Azure, Kubernetes, VMware and other sources, hosts
can be added to, and removed from the monitoring in a fully-automated procedure.

You can find an introduction to DCD in the
[Checkmk guide](https://docs.checkmk.com/latest/en/dcd.html).

"""
from collections.abc import Mapping
from typing import Any

import cmk.gui.cee.plugins.watolib.dcd as dcd_store
from cmk.gui.cee.plugins.watolib.dcd import DCDConnectionSpec
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.plugins.openapi.endpoints.dcd.request_schema import CreateDCD, DcdIdField
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    permissions,
    response_schemas,
)
from cmk.gui.plugins.openapi.utils import problem, serve_json
from cmk.gui.watolib.hosts_and_folders import Folder

EXISTING_DCD_ID = {
    "dcd_id": DcdIdField(
        description="The unique ID of an existing dynamic host configuration.",
        example="MyDcd01",
        required=True,
        should_exist=True,
    )
}

PERMISSIONS_REQUIRED = permissions.AllPerm(
    [permissions.Perm("wato.edit"), permissions.Perm("wato.dcd_connections")]
)


@Endpoint(
    constructors.collection_href("dcd"),
    "cmk/create",
    method="post",
    request_schema=CreateDCD,
    response_schema=response_schemas.DomainObject,
    etag="output",
    permissions_required=PERMISSIONS_REQUIRED,
    additional_status_codes=[
        406,
    ],
)
def create_dcd(params: Mapping[str, Any]) -> Response:
    """Create a dynamic host configuration"""

    user.need_permission("wato.edit")
    user.need_permission("wato.dcd_connections")

    body = params["body"]
    dcd_id = body["dcd_id"]
    connector_type = body["connector_type"]

    match connector_type:
        case "piggyback":
            internal_record = _piggyback_schema_to_internal_record(body)

        case _:
            return problem(
                status=406,
                title="Not Acceptable",
                detail=f"The connector type '{connector_type}' is not acceptable.",
            )

    dcd_store.create_dcd(dcd_id, internal_record)

    return serve_internal_record(dcd_id, internal_record, status=200)


@Endpoint(
    constructors.object_href("dcd", "{dcd_id}"),
    "cmk/show",
    method="get",
    path_params=[EXISTING_DCD_ID],
    response_schema=response_schemas.DomainObject,
    permissions_required=PERMISSIONS_REQUIRED,
    etag="output",
)
def show_dcd(params: Mapping[str, Any]) -> Response:
    """Show a dynamic host configuration"""

    user.need_permission("wato.edit")
    user.need_permission("wato.dcd_connections")

    dcd_id = params["dcd_id"]

    internal_record = dcd_store.get_dcd(dcd_id)

    return serve_internal_record(dcd_id, internal_record, status=200)


@Endpoint(
    constructors.object_href("dcd", "{dcd_id}"),
    ".../delete",
    method="delete",
    path_params=[EXISTING_DCD_ID],
    output_empty=True,
    status_descriptions={
        404: "The dynamic host configuration was not found.",
    },
    additional_status_codes=[
        404,
    ],
    permissions_required=PERMISSIONS_REQUIRED,
)
def delete_rule(params: Mapping[str, Any]) -> Response:
    """Delete a dynamic host configuration"""
    user.need_permission("wato.edit")
    user.need_permission("wato.dcd_connections")

    dcd_id = params["dcd_id"]

    dcd_store.delete_dcd(dcd_id)

    return Response(status=204)


def serve_internal_record(dcd_id: str, dcd: Any, status: int = 200) -> Response:
    response = constructors.domain_object(
        domain_type="dcd",
        identifier=dcd_id,
        title=f"Dynamic host configuration {dcd_id}",
        extensions=dcd,
    )

    return serve_json(data=response, status=status)


def _piggyback_schema_to_internal_record(schema: Mapping[str, Any]) -> DCDConnectionSpec:
    """This function is used to convert a request parsed schema into an internal-compatible record"""

    result = {
        "title": schema["title"],
        "comment": schema["comment"],
        "docu_url": schema["documentation_url"],
        "disabled": schema["disabled"],
        "site": schema["site"],
    }
    connector = {
        "interval": schema["interval"],
        "discover_on_creation": schema["discover_on_creation"],
        "no_deletion_time_after_init": schema["no_deletion_time_after_init"],
        "max_cache_age": schema["max_cache_age"],
        "validity_period": schema["validity_period"],
    }

    if (restrict_source_hosts := schema.get("restrict_source_hosts")) is not None:
        connector["source_filters"] = restrict_source_hosts

    if (activate_changes_interval := schema.get("activate_changes_interval")) is not None:
        connector["activate_changes_interval"] = activate_changes_interval

    if exclude_time_ranges := schema.get("exclude_time_ranges"):
        etr = []
        for et in exclude_time_ranges:
            start = et["start"].strftime("%H:%M").split(":")
            end = et["end"].strftime("%H:%M").split(":")

            etr.append(((start[0], start[1]), (end[0], end[1])))

        connector["activation_exclude_times"] = etr

    creation_rules = []

    for rule in schema["creation_rules"]:
        folder = rule["folder_path"]
        parsed_rule = {
            "create_folder_path": folder.path() if isinstance(folder, Folder) else folder,
            "delete_hosts": rule["delete_hosts"],
        }

        if (
            "matching_hosts" in rule
            and rule["matching_hosts"] is not None
            and rule["matching_hosts"] != []
        ):
            parsed_rule["host_filters"] = rule["matching_hosts"]

        parsed_rule["host_attributes"] = list(
            (field, value) for field, value in rule["host_attributes"].items()
        )

        creation_rules.append(parsed_rule)

    connector["creation_rules"] = creation_rules

    result["connector"] = ("piggyback", connector)
    return result
