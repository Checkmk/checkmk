#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.gui.message import delete_gui_message, get_gui_messages
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException

from ._family import USER_MESSAGE_FAMILY


def delete_user_message_v1(
    message_id: Annotated[
        str,
        PathParam(description="Message ID", example="id"),
    ],
) -> None:
    """Delete a message."""
    messages = {m["id"]: m for m in get_gui_messages()}
    if (message := messages.get(message_id)) is None:
        raise ProblemException(404, f"Message '{message_id}' not found")

    if bool(message.get("security")):
        raise ProblemException(403, "Message cannot be deleted manually, must expire")

    delete_gui_message(message_id)


ENDPOINT_DELETE_MESSAGE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("user_message", "{message_id}"),
        link_relation=".../delete",
        method="delete",
        content_type=None,
    ),
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=USER_MESSAGE_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=delete_user_message_v1)},
)
