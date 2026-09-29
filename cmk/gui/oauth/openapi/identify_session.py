#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.framework import (
    ApiContext,
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href

from .endpoint_family import GUI_SESSION_FAMILY
from .models.request_models import IdentifySessionRequest
from .models.response_models import IdentifySessionResponse
from .session_check import held_permissions
from .utils import live_session_user, require_site_internal_caller


def identify_session_v1(
    api_context: ApiContext, body: IdentifySessionRequest
) -> IdentifySessionResponse:
    """Find the user behind a GUI session

    Answers with the user if the session is live. The session itself is left
    untouched, so its last activity stays as it is.

    The cookie comes in the body, not as a cookie. A request that carries the
    cookie is logged in as the cookie's user, and the site-internal secret is
    then ignored. The endpoint could no longer tell a site service from the
    user's browser. The checks here also cover what that cookie login leaves
    out: a user locked after failed logins or by LDAP, and a user who may not
    use the GUI.

    A caller can name permissions in required_permissions, and the answer then
    says for each one whether the user holds it. The endpoint only reports. It
    never refuses a live session because a permission is missing, the caller
    decides what that means for its own service.
    """
    require_site_internal_caller(api_context)
    user_id = live_session_user(api_context, body.session_cookie)
    if isinstance(body.required_permissions, ApiOmitted):
        return IdentifySessionResponse(user_id=user_id)
    return IdentifySessionResponse(
        user_id=user_id,
        permissions=held_permissions(
            user_id,
            body.required_permissions,
            user_permissions=api_context.config.user_permissions(),
        ),
    )


ENDPOINT_IDENTIFY_SESSION = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("gui_session", "identify"),
        link_relation="cmk/identify_session",
        method="post",
    ),
    permissions=EndpointPermissions(required=None),
    doc=EndpointDoc(family=GUI_SESSION_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=identify_session_v1)},
)
