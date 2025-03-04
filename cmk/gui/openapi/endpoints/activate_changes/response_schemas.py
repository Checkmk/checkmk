#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Literal

from cmk.gui import fields as gui_fields
from cmk.gui.fields import Timestamp
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import Linkable

from cmk import fields

STATUS_PER_SITE_EXAMPLE = [
    {
        "site": "heute",
        "status_text": "Activating",
        "status_details": "Started at: 15:23:09. Finished at: 15:23:13.",
        "start_time": "2025-01-20T15:23:09.306846+00:00",
        "end_time": "2025-01-20T15:23:13.306846+00:00",
    },
    {
        "site": "morgen",
        "status_text": "Activating",
        "status_details": "Started at: 12:45:05. Finished at: 12:46:12.",
        "start_time": "2025-01-20T12:45:05.306846+00:00",
        "end_time": "2025-01-20T12:45:12.306846+00:00",
    },
]


def activation_example(which: Literal["activation_run", "activation_status"]) -> dict[str, Any]:
    example = {
        "changes": [
            {
                "id": "da5430a5-6d0a-48ae-9efd-0563482a3b36",
                "action_name": "edit-host",
                "text": "Modified host heute.",
                "user_id": "cmkadmin",
                "time": "2023-01-20T16:31:51.362057+00:00",
            }
        ],
        "is_running": False,
        "activate_foreign": True,
        "time_started": "2023-01-20T16:31:54.306846+00:00",
        "sites": ["heute"],
        "comment": "",
    }
    if which == "activation_status":
        example["status_per_site"] = STATUS_PER_SITE_EXAMPLE

    return example


class ChangesFields(BaseSchema):
    id = fields.UUID(
        description="The change identifier",
        example="ad9c9b13-52f2-4fb8-8f4f-7b2ae48c7984",
    )
    user_id = fields.String(
        description="The user who made the change",
        example="cmkadmin",
        allow_none=True,
    )
    action_name = fields.String(
        description="The action carried out",
        example="edit-host",
    )
    text = fields.String(
        description="",
        example="Modified host heute.",
    )
    time = Timestamp(
        description="The date and time the change was made.",
        example="2023-02-21T17:32:28+00:00",
    )


class ActivationSiteStatus(BaseSchema):
    site = gui_fields.SiteField(
        presence="ignore",
        description="The site affected by this activation",
        example="heute",
    )
    status_text = fields.String(
        description="The status text",
        example="Activating",
    )
    status_details = fields.String(
        description="The status details",
        example="Started at: 15:23:10. Finished at: 15:23:12.",
    )
    start_time = Timestamp(
        description="The date and time the activation started.",
        example="2025-03-03T17:31:24+00:00",
    )
    end_time = Timestamp(
        description="The date and time the activation ended.",
        example="2023-03-03T17:31:41+00:00",
        allow_none=True,
    )


class ActivationExtensionFields(BaseSchema):
    sites = fields.List(
        gui_fields.SiteField(presence="ignore"),
        description="Sites affected by this activation",
        example=["site1", "site2"],
    )
    is_running = fields.Boolean(
        description="If the activation is still running",
        example=False,
    )
    force_foreign_changes = fields.Boolean(
        description="A boolean flag indicating that even changes which do not originate from the user requesting the activation shall be activated",
        example=False,
    )
    time_started = Timestamp(
        description="The date and time the activation started.",
        example="2023-02-21T17:34:12+00:00",
    )
    changes = fields.List(
        fields.Nested(ChangesFields),
        description="The changes in this activation",
    )


class ActivationExtensionStatusFields(ActivationExtensionFields):
    status_per_site = fields.List(
        fields.Nested(ActivationSiteStatus),
        description="A list of sites with their activation status.",
        example=STATUS_PER_SITE_EXAMPLE,
    )


class ActivationRunBaseResponse(Linkable):
    domainType = fields.Constant(
        "activation_run",
        description="The domain type of the object.",
    )
    id = fields.UUID(
        description="The unique identifier for this activation run.",
        example="84b18e42-355e-4f13-80b6-404bd8f21149",
    )
    title = fields.String(
        description="The activation run status.",
        example="Activation status: In progress.",
    )
    members: gui_fields.Field = fields.Dict(
        description="The container for external resources, like linked foreign objects or actions.",
    )


class ActivationRunResponse(ActivationRunBaseResponse):
    extensions = fields.Nested(
        ActivationExtensionFields,
        description="The activation run attributes.",
        example=activation_example("activation_run"),
    )


class ActivationStatusResponse(ActivationRunBaseResponse):
    extensions = fields.Nested(
        ActivationExtensionStatusFields,
        description="The activation run attributes with status.",
        example=activation_example("activation_status"),
    )


class ActivationRunCollection(Linkable):
    id = fields.String(
        description="The name of this collection.",
    )
    domainType = fields.Constant(
        "activation_run",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(ActivationStatusResponse),
        description="A list of activation runs.",
        example=[
            {
                "links": [
                    {
                        "domainType": "link",
                        "rel": "self",
                        "href": "http://localhost/heute/check_mk/api/1.0/objects/activation_run/b0a0bf49-ff5f-454b-a5d5-9731cb0fb5fa",
                        "method": "GET",
                        "type": "application/json",
                    }
                ],
                "domainType": "activation_run",
                "id": "b0a0bf49-ff5f-454b-a5d5-9731cb0fb5fa",
                "title": "test-title",
                "members": {},
                "extensions": activation_example("activation_status"),
            }
        ],
    )
    extensions = fields.Dict(
        description="Additional attributes alongside the collection.",
    )


class PendingChangesCollection(Linkable):
    domainType = fields.Constant(
        "activation_run",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(ChangesFields),
        description="The changes that are pending",
        example=[
            {
                "id": "da5430a5-6d0a-48ae-9efd-0563482a3b36",
                "action_name": "create-host",
                "text": "Created new host foobar.",
                "user_id": "cmkadmin",
                "time": "2023-01-20T16:31:51.362057+00:00",
            },
            {
                "id": "4ba28393-567e-4a9a-9368-e600d28c2a7e",
                "action_name": "edit-host",
                "text": "Modified host foobar.",
                "user_id": "cmkadmin",
                "time": "2023-01-20T16:32:12.362057+00:00",
            },
        ],
    )
    extensions = fields.Dict(
        description="Additional attributes alongside the collection.",
    )
