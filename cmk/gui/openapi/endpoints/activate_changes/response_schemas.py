#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui import fields as gui_fields
from cmk.gui.fields import Timestamp
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import Linkable

from cmk import fields

ACTIVATION_EXT_EXAMPLE = {
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
        description="The date and time the activation was started.",
        example="2023-02-21T17:34:12+00:00",
    )
    changes = fields.List(
        fields.Nested(ChangesFields),
        description="The changes in this activation",
    )


class ActivationRunResponse(Linkable):
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
    extensions = fields.Nested(
        ActivationExtensionFields,
        description="The activation run attributes.",
        example=ACTIVATION_EXT_EXAMPLE,
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
        fields.Nested(ActivationRunResponse),
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
                "extensions": ACTIVATION_EXT_EXAMPLE,
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
