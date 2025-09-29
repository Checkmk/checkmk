#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Annotated

from cmk.gui.message import acknowledge_gui_message, get_gui_messages
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.user_message.api._family import USER_MESSAGE_FAMILY


def acknowledge_user_message_v1(
    message_id: Annotated[
        str,
        PathParam(description="Message id", example="id"),
    ],
) -> None:
    """Acknowledge a message"""
    messages = {m["id"]: m for m in get_gui_messages()}
    if (message := messages.get(message_id)) is None:
        raise ProblemException(404, f"Message '{message_id}' not found")

    if bool(message.get("acknowledged")):
        raise ProblemException(400, f"Message '{message_id}' is already acknowledged")

    acknowledge_gui_message(message_id)


ENDPOINT_ACKNOWLEDGE_MESSAGE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_action_href("user_message", "{message_id}", "acknowledge"),
        link_relation="cmk/acknowledge",
        method="post",
        content_type=None,
    ),
    permissions=EndpointPermissions(),
    doc=EndpointDoc(family=USER_MESSAGE_FAMILY.name),
    versions={APIVersion.UNSTABLE: EndpointHandler(handler=acknowledge_user_message_v1)},
)
