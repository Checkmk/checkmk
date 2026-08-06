#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.graphing_engine import HostName, ServiceName
from cmk.gui.config import active_config
from cmk.gui.openapi.framework import (
    APIVersion,
    EndpointDoc,
    EndpointHandler,
    EndpointMetadata,
    EndpointPermissions,
    VersionedEndpoint,
)
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.gui.openapi.restful_objects.constructors import domain_type_action_href
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils import permission_verification as permissions
from cmk.livestatus_client import MKLivestatusException

from .._engine_plugins import registered_translations
from .._engine_source import RRDFetchMetricNameMapping
from ._family import GRAPH_FAMILY
from .models import MetricNameMappingResponse


@api_model
class TranslateMetricNamesRequest:
    hostname: AnnotatedHostName = api_field(description="The host name.", example="my-host")
    service_description: str = api_field(
        description="The service description.", example="CPU utilization"
    )
    site: (
        Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_be_authorized)] | None
    ) = api_field(
        description=(
            "Resolve the service on this site only. None searches every site the user may see, "
            "and folds the names of a host/service monitored on several of them into one mapping."
        ),
        example="mysite",
        default=None,
    )


def translate_metric_names_v1(body: TranslateMetricNamesRequest) -> MetricNameMappingResponse:
    """Map the raw perf-data names of a service to their canonical metric names"""
    try:
        per_service = RRDFetchMetricNameMapping(
            host_name=HostName(body.hostname),
            service_name=ServiceName(body.service_description),
            debug=active_config.debug,
            site_id=body.site,
            registered_translations=registered_translations(),
        )()
    except MKLivestatusException as exc:
        raise ProblemException(
            status=503,
            title="Monitoring data source unavailable",
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise ProblemException(
            status=500,
            title="Metric name translation failed",
            detail=f"Failed to translate the metric names: {exc}",
        ) from exc

    return MetricNameMappingResponse(
        metric_names={
            str(raw_name): str(canonical_name)
            for mapping in per_service.values()
            for raw_name, canonical_name in mapping.items()
        }
    )


ENDPOINT_TRANSLATE_METRIC_NAMES = VersionedEndpoint(
    metadata=EndpointMetadata(
        path=domain_type_action_href("graph", "translate_metric_names"),
        link_relation="cmk/translate_metric_names",
        method="post",
    ),
    # The endpoint itself needs no permissions. Opening a livestatus connection checks
    # these three (_set_livestatus_auth in cmk/gui/sites.py) to work out which objects the
    # user may see, and whatever gets checked has to be declared here.
    permissions=EndpointPermissions(
        required=permissions.Optional(
            permissions.AllPerm(
                [
                    permissions.Perm("general.see_all"),
                    permissions.OkayToIgnorePerm("bi.see_all"),
                    permissions.OkayToIgnorePerm("mkeventd.seeall"),
                ]
            )
        )
    ),
    doc=EndpointDoc(family=GRAPH_FAMILY.name),
    versions={APIVersion.INTERNAL: EndpointHandler(handler=translate_metric_names_v1)},
)
