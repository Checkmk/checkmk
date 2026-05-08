#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
from collections.abc import Iterable

from cmk.gui.openapi.api_endpoints.downtime.models.response_models import (
    DowntimeCollectionModel,
    DowntimeExtensionsModel,
    DowntimeObjectModel,
    FixedDowntimeModeModel,
    FlexibleDowntimeModeModel,
)
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.endpoint_link import link_to_endpoint
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.shared_endpoint_families.host_config import HOST_CONFIG_FAMILY
from cmk.gui.utils import permission_verification as permissions
from cmk.livestatus_client.queries import ResultRow

PERMISSIONS = permissions.Undocumented(
    permissions.AnyPerm(
        [
            permissions.Perm("general.see_all"),
            permissions.OkayToIgnorePerm("bi.see_all"),
            permissions.OkayToIgnorePerm("mkeventd.seeall"),
            permissions.Perm("wato.see_all_folders"),
        ]
    )
)

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("action.downtimes"),
        PERMISSIONS,
    ]
)


def _downtime_mode(info: ResultRow) -> FixedDowntimeModeModel | FlexibleDowntimeModeModel:
    if info["fixed"] == 1:
        return FixedDowntimeModeModel(type="fixed")
    return FlexibleDowntimeModeModel(type="flexible", duration_minutes=info["duration"] // 60)


def serialize_single_downtime(downtime: ResultRow, *, host_url: str) -> DowntimeObjectModel:
    is_service = bool(downtime["is_service"])
    downtime_id = str(downtime["id"])
    host_name = downtime["host_name"]

    if is_service:
        downtime_detail = f"service: {downtime['service_description']}"
    else:
        downtime_detail = f"host: {host_name}"

    links: list[LinkModel] = [
        link_to_endpoint(
            family="Downtimes",
            link_relation="cmk/show",
            version=APIVersion.V1,
            host_url=host_url,
            parameters={"downtime_id": downtime_id},
            as_self=True,
        ),
        link_to_endpoint(
            family="Downtimes",
            link_relation=".../delete",
            version=APIVersion.V1,
            host_url=host_url,
            body={"delete_type": "by_id", "downtime_id": downtime_id},
            title="Delete the downtime",
        ),
    ]

    if not is_service:
        links.append(
            link_to_endpoint(
                family=HOST_CONFIG_FAMILY.name,
                link_relation="cmk/show",
                version=APIVersion.UNSTABLE,
                host_url=host_url,
                parameters={"host_name": host_name},
                title="This host of this downtime.",
            )
        )

    extensions = DowntimeExtensionsModel(
        site_id=downtime["site"],
        host_name=host_name,
        author=downtime["author"],
        is_service=is_service,
        start_time=dt.datetime.fromtimestamp(downtime["start_time"], tz=dt.UTC),
        end_time=dt.datetime.fromtimestamp(downtime["end_time"], tz=dt.UTC),
        recurring=bool(downtime["recurring"]),
        comment=downtime["comment"],
        mode=_downtime_mode(downtime),
    )
    if is_service:
        extensions.service_description = downtime["service_description"]

    return DowntimeObjectModel(
        domainType="downtime",
        id=downtime_id,
        title=f"Downtime for {downtime_detail}",
        links=links,
        extensions=extensions,
    )


def serialize_downtimes(
    downtimes: Iterable[ResultRow], *, host_url: str
) -> DowntimeCollectionModel:
    return DowntimeCollectionModel(
        id="downtime",
        domainType="downtime",
        links=[
            link_to_endpoint(
                family="Downtimes",
                link_relation=".../collection",
                version=APIVersion.V1,
                host_url=host_url,
                as_self=True,
            )
        ],
        value=[serialize_single_downtime(downtime, host_url=host_url) for downtime in downtimes],
        extensions={},
    )
