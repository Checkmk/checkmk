#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Request models for the Maps SPA's internal endpoints.

Only the reads whose input is structured or unbounded take a body; everything
addressable by a name or a handful of scalars stays a GET with query parameters.
"""

import base64
import binascii
from collections.abc import Callable
from typing import Annotated

from pydantic import Field

from cmk.ccc.site import SiteId
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import AnnotatedHostName
from cmk.gui.openapi.framework.model.converter import SiteIdConverter, TypedPlainValidator
from cmk.maps.gui._cfg_import import MAX_CFG_BYTES
from cmk.maps.gui._commands import MapCommandVerb
from cmk.maps.gui._images import MAX_BACKGROUND_BYTES, MAX_ICON_BYTES

# A site the caller may see. ``should_be_authorized`` rather than ``should_exist``
# so a restricted user cannot enumerate the sites they may not see (werks 18993,
# 18994) -- this is a monitoring endpoint.
type AnnotatedSiteId = Annotated[
    SiteId, TypedPlainValidator(str, SiteIdConverter.should_be_authorized)
]

# The SPA truncates deep BI trees for rendering; the server caps too so a crafted
# request cannot force an unbounded walk of the compiled aggregation.
MAX_TREE_DEPTH = 10


@api_model
class MapsMetricInfoRequest:
    perf_data: str = api_field(
        description="The raw perfdata string to resolve.",
        example="rta=0.5ms;200;500;0; pl=0%;80;100;;",
    )
    check_command: str = api_field(
        description="The check command that produced the perfdata; drives the metric translation.",
        example="check_mk_active-icmp",
        default="",
    )
    graphs: bool = api_field(
        description=(
            "Also resolve the applicable graph plug-ins. Requires the object "
            "context below — walking every registered plug-in is too costly for "
            "the per-tick Perf-O-Meter lookups that do not need it."
        ),
        default=False,
    )
    host_name: str = api_field(
        description="Host the perfdata belongs to. Required when ``graphs`` is set.",
        example="heute",
        default="",
    )
    service_description: str = api_field(
        description="Service the perfdata belongs to (empty for host perfdata).",
        example="CPU load",
        default="",
    )
    site_id: str = api_field(description="Site the object lives on.", example="heute", default="")


@api_model
class MapsAggregationTreeRequest:
    aggregation_id: str = api_field(
        description="The resolved BI aggregation (branch) name.", example="Host heute"
    )
    depth: Annotated[int, Field(ge=0, le=MAX_TREE_DEPTH)] = api_field(
        description="How many levels of the hierarchy to return.", example=2, default=2
    )


@api_model
class MapsAggregationStatesRequest:
    aggregation_ids: list[str] = api_field(
        description="Resolved BI aggregation names to compute the state for.",
        example=["Host heute"],
    )


def _base64_decoder(decoded_limit: int) -> Callable[[str], bytes]:
    """Decode an uploaded file's payload, refusing an oversized one up front.

    Files travel base64-encoded inside the JSON body. The versioned endpoint
    framework has a seam for other request media types, but nothing in the tree
    drives it yet, and every Maps upload is small and capped, so the ~33%
    encoding overhead buys the typed JSON model instead.

    The length check is on the *encoded* text, so a body over the limit is
    refused before it is decoded into a second copy. What the operator is told
    ("max 2 MB") still comes from the handler, against the decoded size.
    """
    encoded_limit = -(-decoded_limit // 3) * 4

    def decode(value: str) -> bytes:
        if len(value) > encoded_limit:
            raise ValueError(f"Content exceeds {decoded_limit} bytes.")
        try:
            return base64.b64decode(value, validate=True)
        except binascii.Error:
            raise ValueError("Not valid base64 content.") from None

    return decode


type IconBytes = Annotated[bytes, TypedPlainValidator(str, _base64_decoder(MAX_ICON_BYTES))]
type BackgroundBytes = Annotated[
    bytes, TypedPlainValidator(str, _base64_decoder(MAX_BACKGROUND_BYTES))
]
type CfgBytes = Annotated[bytes, TypedPlainValidator(str, _base64_decoder(MAX_CFG_BYTES))]


@api_model
class MapsImageUploadRequest:
    filename: str = api_field(
        description="Name the file was uploaded under; drives the stored name and suffix.",
        example="server.svg",
    )
    content_type: str = api_field(
        description="The file's media type, as the browser reported it.",
        example="image/svg+xml",
    )
    content: IconBytes = api_field(
        description="The file's bytes, base64-encoded.", example="PHN2Zy8+"
    )


@api_model
class MapsBackgroundUploadRequest:
    filename: str = api_field(
        description="Name the file was uploaded under; drives the stored suffix.",
        example="floorplan.png",
    )
    content_type: str = api_field(
        description="The file's media type, as the browser reported it.",
        example="image/png",
    )
    content: BackgroundBytes = api_field(
        description="The file's bytes, base64-encoded.", example="iVBORw0KGgo="
    )


@api_model
class MapsCfgImportRequest:
    filename: str = api_field(
        description="Name of the uploaded ``.cfg``; the map's name is derived from it.",
        example="datacenter.cfg",
    )
    content: CfgBytes = api_field(
        description="The file's bytes, base64-encoded.", example="ZGVmaW5lIGdsb2JhbCB7fQ=="
    )


@api_model
class MapsFormValuesRequest:
    data: dict[str, object] | ApiOmitted = api_field(
        description=(
            "The form's value bag. Omit it on a schema read to render the form "
            "spec's own prefills, which is what a new map and the empty bulk-edit "
            "dialog want."
        ),
        default_factory=ApiOmitted,
        example={},
    )


@api_model
class MapsCommandRequest:
    """One monitoring command for one map object."""

    action: MapCommandVerb = api_field(description="The command to run.", example="force_check")
    host_name: AnnotatedHostName = api_field(
        description="Host the command targets.", example="heute"
    )
    service_description: str | ApiOmitted = api_field(
        description="Service the command targets. Omit it to target the host itself.",
        default_factory=ApiOmitted,
        example="CPU load",
    )
    site_id: AnnotatedSiteId | ApiOmitted = api_field(
        description=(
            "Site the object lives on. Required for the toggles; a rescheduled check "
            "without it goes to the local site."
        ),
        default_factory=ApiOmitted,
        example="heute",
    )
