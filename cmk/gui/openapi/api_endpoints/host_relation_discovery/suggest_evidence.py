#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.logged_in import user
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
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.watolib.host_relation_discovery import scan_for_evidence
from cmk.gui.watolib.hosts_and_folders import folder_tree

from ._family import HOST_RELATION_DISCOVERY_FAMILY
from ._shared import (
    as_suggestions_model,
    need_discovery_permissions,
    parsed_values,
    parsed_words,
    PERMISSIONS,
)
from .models.request_models import SuggestEvidenceRequestModel
from .models.response_models import SuggestionsModel


def suggest_host_relation_evidence(
    api_context: ApiContext, body: SuggestEvidenceRequestModel
) -> SuggestionsModel:
    """Show what the hosts in Setup could be related by

    Reads every host the user may see and reports the words that turn one host name into another and the
    labels and attributes whose values each sit on a handful of hosts - what a scan could
    look for. ``look_in`` narrows it to either. Changes nothing.
    """
    need_discovery_permissions()
    return as_suggestions_model(
        scan_for_evidence(
            folder_tree(),
            attribute_names=[attribute["name"] for attribute in api_context.config.wato_host_attrs],
            acting_user=user,
            words=parsed_words(body),
            values=parsed_values(body),
            in_names="names" in body.look_in,
            in_values="values" in body.look_in,
        )
    )


ENDPOINT_SUGGEST_EVIDENCE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("host_relation_discovery", "suggest"),
        link_relation="cmk/fetch",
        method="post",
    ),
    permissions=EndpointPermissions(required=PERMISSIONS),
    doc=EndpointDoc(family=HOST_RELATION_DISCOVERY_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=suggest_host_relation_evidence)},
)
