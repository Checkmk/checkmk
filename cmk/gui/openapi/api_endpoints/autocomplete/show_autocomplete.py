#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.gui.autocompleters import autocompleter_registry, AutocompleterBackendWarning
from cmk.gui.config import active_config
from cmk.gui.log import logger
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointBehavior,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    PathParam,
    VersionedEndpoint,
)
from cmk.gui.openapi.restful_objects.constructors import object_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils import permission_verification as permissions

from ._family import AUTOCOMPLETE_FAMILY
from .models.request_models import AutocompleteRequestModel
from .models.response_models import AutocompleteChoiceModel, AutocompleteResponseModel


def show_autocomplete_v1(
    body: AutocompleteRequestModel,
    autocomplete_id: Annotated[
        str,
        PathParam(description="The id of the autocompleter", example="tag_groups"),
    ],
) -> AutocompleteResponseModel:
    """Call the autocompleter specified in the url"""
    internal_autocompleter = autocomplete_id

    # This fix allows the autocompleter to be accessible by both the old and the new name,
    # thus maintaining compatibility with the Grafana datasource, which uses the old name.
    # When dropping support for Checkmk 2.3.0 we can remove these lines after updating
    # the Grafana datasource plugin.
    if internal_autocompleter == "available_graphs":
        internal_autocompleter = "available_graph_templates"

    function = autocompleter_registry.get(internal_autocompleter)

    if function is None:
        logger.error("Autocompleter %r not found", autocomplete_id)
        raise ProblemException(status=404, title=f"Autocompleter {autocomplete_id} not found.")

    try:
        choices = function(active_config, body.value, body.parameters)
    except AutocompleterBackendWarning as e:
        logger.warning(
            "Autocompleter %r backend unavailable", internal_autocompleter, exc_info=True
        )
        return AutocompleteResponseModel(
            choices=[AutocompleteChoiceModel(id=k, value=v) for k, v in e.choices if k is not None],
            warning=str(e),
        )
    except ValueError as e:
        logger.exception("Autocompleter %r received invalid input", internal_autocompleter)
        raise ProblemException(status=400, title="Invalid input", detail=str(e))
    except KeyError as e:
        logger.exception("Autocompleter %r missing field", internal_autocompleter)
        raise ProblemException(status=400, title="Missing field", detail=f"Missing field: {e}")

    return AutocompleteResponseModel(
        choices=[AutocompleteChoiceModel(id=k, value=v) for k, v in choices if k is not None],
    )


ENDPOINT_SHOW_AUTOCOMPLETE = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=object_href("autocomplete", "{autocomplete_id}"),
        link_relation="cmk/show",
        method="post",
    ),
    permissions=EndpointPermissions(
        required=permissions.DynamicRuntimePerm(
            description="Permissions are determined by the autocompleter being invoked."
        )
    ),
    doc=EndpointDoc(family=AUTOCOMPLETE_FAMILY.name),
    behavior=EndpointBehavior(skip_locking=True, update_config_generation=False),
    versions={APIVersion.V1: EndpointHandler(handler=show_autocomplete_v1)},
)
