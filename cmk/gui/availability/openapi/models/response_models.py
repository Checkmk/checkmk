#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Literal, Self

from cmk.gui.availability.type_defs import AVEntry, AVTimelineStates
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
    LinkModel,
)
from cmk.gui.openapi.restful_objects.constructors import object_href, sub_object_href


@api_model
class HostAvailabilityStates:
    up: int = api_field(
        description="Seconds the host was up.",
        example=82800,
    )
    down: int = api_field(
        description="Seconds the host was down.",
        example=0,
    )
    unreach: int = api_field(
        description="Seconds the host was unreachable.",
        example=0,
    )
    flapping: int = api_field(
        description="Seconds the host state was flapping.",
        example=0,
    )
    in_downtime: int = api_field(
        description="Seconds the host was in a scheduled downtime.",
        example=3600,
    )
    outof_notification_period: int = api_field(
        description="Seconds outside the notification period.",
        example=0,
    )
    outof_service_period: int = api_field(
        description="Seconds outside the service period.",
        example=0,
    )
    unmonitored: int = api_field(
        description="Seconds with no monitoring data.",
        example=0,
    )

    @classmethod
    def from_internal(cls, states: AVTimelineStates) -> Self:
        return cls(
            up=states.get("up", 0),
            down=states.get("down", 0),
            unreach=states.get("unreach", 0),
            flapping=states.get("flapping", 0),
            in_downtime=states.get("in_downtime", 0),
            outof_notification_period=states.get("outof_notification_period", 0),
            outof_service_period=states.get("outof_service_period", 0),
            unmonitored=states.get("unmonitored", 0),
        )


@api_model
class ServiceAvailabilityStates:
    ok: int = api_field(
        description="Seconds the service was OK.",
        example=82800,
    )
    warn: int = api_field(
        description="Seconds the service was in warning state.",
        example=0,
    )
    crit: int = api_field(
        description="Seconds the service was in critical state.",
        example=0,
    )
    unknown: int = api_field(
        description="Seconds the service was in unknown state.",
        example=0,
    )
    flapping: int = api_field(
        description="Seconds the service state was flapping.",
        example=0,
    )
    in_downtime: int = api_field(
        description="Seconds the service was in a scheduled downtime.",
        example=3600,
    )
    host_down: int = api_field(
        description="Seconds the host was down, affecting this service.",
        example=0,
    )
    outof_notification_period: int = api_field(
        description="Seconds outside the notification period.",
        example=0,
    )
    outof_service_period: int = api_field(
        description="Seconds outside the service period.",
        example=0,
    )
    unmonitored: int = api_field(
        description="Seconds with no monitoring data.",
        example=0,
    )

    @classmethod
    def from_internal(cls, states: AVTimelineStates) -> Self:
        return cls(
            ok=states.get("ok", 0),
            warn=states.get("warn", 0),
            crit=states.get("crit", 0),
            unknown=states.get("unknown", 0),
            flapping=states.get("flapping", 0),
            in_downtime=states.get("in_downtime", 0),
            host_down=states.get("host_down", 0),
            outof_notification_period=states.get("outof_notification_period", 0),
            outof_service_period=states.get("outof_service_period", 0),
            unmonitored=states.get("unmonitored", 0),
        )


@api_model
class HostAvailabilityExtension:
    site: str = api_field(
        description="The site ID the host belongs to.",
        example="mysite",
    )
    host: str = api_field(
        description="The host name.",
        example="my-host",
    )
    alias: str = api_field(
        description="The host alias.",
        example="My Host",
    )
    states: HostAvailabilityStates = api_field(
        description="Seconds spent in each monitoring state during the requested time range.",
        example={"up": 82800, "in_downtime": 3600},
    )
    total_duration: int = api_field(
        description="Total seconds in the requested time range.",
        example=86400,
    )

    @classmethod
    def from_internal(cls, entry: AVEntry) -> Self:
        return cls(
            site=str(entry["site"]),
            host=str(entry["host"]),
            alias=entry["alias"],
            states=HostAvailabilityStates.from_internal(entry["states"]),
            total_duration=entry["total_duration"],
        )


@api_model
class HostAvailabilityObject(DomainObjectModel):
    domainType: Literal["host_availability"] = api_field(
        description="The type of the domain object.",
    )
    extensions: HostAvailabilityExtension = api_field(
        description="All the attributes of the domain object.",
    )

    @classmethod
    def from_internal(cls, entry: AVEntry) -> Self:
        host_name = str(entry["host"])
        return cls(
            domainType="host_availability",
            id=f"{entry['site']}~{host_name}",
            title=host_name,
            extensions=HostAvailabilityExtension.from_internal(entry),
            links=[LinkModel.create("self", object_href("host_availability", host_name))],
        )


@api_model
class HostAvailabilityCollection(DomainObjectCollectionModel):
    domainType: Literal["host_availability"] = api_field(
        description="The domain type of the objects in the collection.",
    )
    value: list[HostAvailabilityObject] = api_field(
        description="A list of host availability objects.",
    )


@api_model
class ServiceAvailabilityExtension:
    site: str = api_field(
        description="The site ID the service belongs to.",
        example="mysite",
    )
    host: str = api_field(
        description="The host name the service runs on.",
        example="my-host",
    )
    alias: str = api_field(
        description="The host alias.",
        example="My Host",
    )
    service: str = api_field(
        description="The service name.",
        example="CPU load",
    )
    display_name: str = api_field(
        description="The display name of the service.",
        example="CPU load",
    )
    states: ServiceAvailabilityStates = api_field(
        description="Seconds spent in each monitoring state during the requested time range.",
        example={"ok": 82800, "warn": 3600},
    )
    total_duration: int = api_field(
        description="Total seconds in the requested time range.",
        example=86400,
    )

    @classmethod
    def from_internal(cls, entry: AVEntry) -> Self:
        return cls(
            site=str(entry["site"]),
            host=str(entry["host"]),
            alias=entry["alias"],
            service=str(entry["service"]),
            display_name=entry["display_name"],
            states=ServiceAvailabilityStates.from_internal(entry["states"]),
            total_duration=entry["total_duration"],
        )


@api_model
class ServiceAvailabilityObject(DomainObjectModel):
    domainType: Literal["service_availability"] = api_field(
        description="The type of the domain object.",
    )
    extensions: ServiceAvailabilityExtension = api_field(
        description="All the attributes of the domain object.",
    )

    @classmethod
    def from_internal(cls, entry: AVEntry) -> Self:
        host_name = str(entry["host"])
        service = str(entry["service"])
        return cls(
            domainType="service_availability",
            id=f"{entry['site']}~{host_name}~{service}",
            title=f"{host_name} / {service}",
            extensions=ServiceAvailabilityExtension.from_internal(entry),
            links=[
                LinkModel.create(
                    "self",
                    sub_object_href("service_availability", service, "host", host_name),
                )
            ],
        )


@api_model
class ServiceAvailabilityCollection(DomainObjectCollectionModel):
    domainType: Literal["service_availability"] = api_field(
        description="The domain type of the objects in the collection.",
    )
    value: list[ServiceAvailabilityObject] = api_field(
        description="A list of service availability objects.",
    )
