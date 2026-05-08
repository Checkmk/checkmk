#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
from collections.abc import Callable
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, AwareDatetime, Discriminator, model_validator

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.common_fields import (
    AnnotatedHostName,
    query_expression_validator,
)
from cmk.gui.openapi.framework.model.converter import (
    GroupConverter,
    HostConverter,
    SiteIdConverter,
    TypedPlainValidator,
)
from cmk.livestatus_client.expressions import QueryExpression
from cmk.livestatus_client.tables import Hosts, Services
from cmk.livestatus_client.tables.downtimes import Downtimes

type AnnotatedSiteId = Annotated[SiteId, TypedPlainValidator(str, SiteIdConverter.should_exist)]
type AnnotatedHostGroupName = Annotated[
    str, TypedPlainValidator(str, GroupConverter(group_type="host").exists)
]
type AnnotatedServiceGroupName = Annotated[
    str, TypedPlainValidator(str, GroupConverter(group_type="service").exists)
]


# ---- Create downtime base classes ----


def _with_defaulted_timezone(
    date: dt.datetime,
    _get_local_timezone: Callable[[], dt.tzinfo | None] = lambda: (
        dt.datetime.now(dt.UTC).astimezone().tzinfo
    ),
) -> dt.datetime:
    """Default a datetime to the local timezone if it has none."""
    if date.tzinfo is None:
        date = date.replace(tzinfo=_get_local_timezone())
    return date


@api_model
class _BaseCreateDowntimeModel:
    start_time: Annotated[dt.datetime, AfterValidator(_with_defaulted_timezone)] = api_field(
        description=(
            "The start datetime of the new downtime. The format has to conform to the ISO 8601 "
            "profile."
        ),
        example="2017-07-21T17:32:28Z",
    )
    end_time: Annotated[dt.datetime, AfterValidator(_with_defaulted_timezone)] = api_field(
        description=(
            "The end datetime of the new downtime. The format has to conform to the ISO 8601 "
            "profile."
        ),
        example="2017-07-21T17:32:28Z",
    )
    recur: Literal[
        "fixed",
        "hour",
        "day",
        "week",
        "second_week",
        "fourth_week",
        "weekday_start",
        "weekday_end",
        "day_of_month",
    ] = api_field(
        description=(
            "The recurring mode of the new downtime. Available modes are:\n"
            "  * fixed\n"
            "  * hour\n"
            "  * day\n"
            "  * week\n"
            "  * second_week\n"
            "  * fourth_week\n"
            "  * weekday_start\n"
            "  * weekday_end\n"
            "  * day_of_month\n"
            "This only works in the commercial editions of Checkmk. Defaults to 'fixed'."
        ),
        example="hour",
        default="fixed",
    )
    comment: str | None = api_field(
        description="An optional comment for the downtime.",
        example="Security updates",
        default=None,
    )


@api_model
class _BaseCreateHostDowntimeModel(_BaseCreateDowntimeModel):
    duration: int = api_field(
        description=(
            "Duration in minutes. When set, the downtime does not begin automatically at a "
            "nominated time, but when a real problem status appears for the host. Consequently, "
            "the start_time/end_time is only the time window in which the scheduled downtime can "
            "begin."
        ),
        example=60,
        default=0,
    )


@api_model
class _BaseCreateServiceDowntimeModel(_BaseCreateDowntimeModel):
    duration: int = api_field(
        description=(
            "Duration in minutes. When set, the downtime does not begin automatically at a "
            "nominated time, but when a real problem status appears for the service. Consequently, "
            "the start_time/end_time is only the time window in which the scheduled downtime can "
            "begin."
        ),
        example=60,
        default=0,
    )


# ---- Create host downtime ----


@api_model
class CreateHostDowntimeModel(_BaseCreateHostDowntimeModel):
    downtime_type: Literal["host"] = api_field(
        description="Schedule downtimes for a host identified by host name or IP address",
        example="host",
    )
    host_name: Annotated[HostName, TypedPlainValidator(str, HostConverter.monitored_host_name)] = (
        api_field(
            description="The host name or IP address itself.",
            example="example.com",
        )
    )


@api_model
class CreateHostGroupDowntimeModel(_BaseCreateHostDowntimeModel):
    downtime_type: Literal["hostgroup"] = api_field(
        description="Schedule downtimes for all hosts belonging to the specified hostgroup",
        example="hostgroup",
    )
    hostgroup_name: AnnotatedHostGroupName = api_field(
        description=(
            "The name of the host group. A downtime will be scheduled for all hosts in this host "
            "group."
        ),
        example="windows",
    )


@api_model
class CreateHostQueryDowntimeModel(_BaseCreateHostDowntimeModel):
    downtime_type: Literal["host_by_query"] = api_field(
        description="Schedule downtimes for all host matching the query",
        example="host_by_query",
    )
    query: Annotated[QueryExpression, query_expression_validator(Hosts)] = api_field(
        description="A Livestatus filter expression for hosts.",
        example='{"op": "=", "left": "name", "right": "example.com"}',
    )


# ---- Create service downtime ----


@api_model
class CreateServiceDowntimeModel(_BaseCreateServiceDowntimeModel):
    downtime_type: Literal["service"] = api_field(
        description=(
            "Schedule downtimes for services whose names are listed in service_descriptions and "
            "belongs to the host identified by name or IP address in host_name."
        ),
        example="service",
    )
    # We don't check existence here — the user may not have visibility to the host
    # but may still be able to access specific services on it.
    host_name: AnnotatedHostName = api_field(
        description="The host name or IP address of the host.",
        example="example.com",
    )
    service_descriptions: list[str] = api_field(
        description="The service descriptions to schedule downtimes for.",
        example=["CPU utilization", "Memory"],
    )


@api_model
class CreateServiceGroupDowntimeModel(_BaseCreateServiceDowntimeModel):
    downtime_type: Literal["servicegroup"] = api_field(
        description="Schedule downtimes for all services in a given service group",
        example="servicegroup",
    )
    servicegroup_name: AnnotatedServiceGroupName = api_field(
        description=(
            "The name of the service group. A downtime will be scheduled for all services in this "
            "group."
        ),
        example="windows",
    )


@api_model
class CreateServiceQueryDowntimeModel(_BaseCreateServiceDowntimeModel):
    downtime_type: Literal["service_by_query"] = api_field(
        description="Schedule downtimes for services matching the query",
        example="service_by_query",
    )
    query: Annotated[QueryExpression, query_expression_validator(Services)] = api_field(
        description="A Livestatus filter expression for services.",
        example='{"op": "=", "left": "description", "right": "Service description"}',
    )


# ---- Delete downtime ----


@api_model
class DeleteDowntimeByIdModel:
    delete_type: Literal["by_id"] = api_field(
        description="The option how to delete a downtime.",
        example="by_id",
    )
    site_id: AnnotatedSiteId = api_field(
        description="The site from which you want to delete a downtime.",
        example="mysite",
    )
    downtime_id: str = api_field(
        description="The id of the downtime",
        example="54",
    )


@api_model
class DeleteDowntimeByNameModel:
    delete_type: Literal["params"] = api_field(
        description="The option how to delete a downtime.",
        example="params",
    )
    host_name: AnnotatedHostName = api_field(
        description="If set alone, then all downtimes of the host will be removed.",
        example="example.com",
    )
    service_descriptions: list[str] | None = api_field(
        description=(
            "If set, the downtimes of the listed services of the specified host will be "
            "removed. If a service has multiple downtimes then all will be removed"
        ),
        example=["CPU load", "Memory"],
        default=None,
    )


@api_model
class DeleteDowntimeByQueryModel:
    delete_type: Literal["query"] = api_field(
        description="The option how to delete a downtime.",
        example="query",
    )
    query: Annotated[QueryExpression, query_expression_validator(Downtimes)] = api_field(
        description="A Livestatus filter expression for downtimes.",
        example='{"op": "=", "left": "host_name", "right": "example.com"}',
    )


@api_model
class DeleteDowntimeByHostGroupModel:
    delete_type: Literal["hostgroup"] = api_field(
        description="The option how to delete a downtime.",
        example="hostgroup",
    )
    hostgroup_name: AnnotatedHostGroupName = api_field(
        description=(
            "Name of a valid hostgroup, all current downtimes for hosts in this group will be "
            "deleted."
        ),
        example="windows",
    )


@api_model
class DeleteDowntimeByServiceGroupModel:
    delete_type: Literal["servicegroup"] = api_field(
        description="The option how to delete a downtime.",
        example="servicegroup",
    )
    servicegroup_name: AnnotatedServiceGroupName = api_field(
        description=(
            "Name of a valid servicegroup, all current downtimes for services in this group will be"
            " deleted."
        ),
        example="windows",
    )


# ---- Modify downtime ----


@api_model
class ModifyEndTimeAbsoluteModel:
    modify_type: Literal["absolute"] = api_field(
        description="How to modify the end time of a downtime.",
        example="absolute",
    )
    value: Annotated[dt.datetime, AwareDatetime] = api_field(
        description=(
            "The end datetime of the downtime. The format has to conform to the ISO 8601 profile"
        ),
        example="2017-07-21T17:32:28Z",
    )


@api_model
class ModifyEndTimeRelativeModel:
    modify_type: Literal["relative"] = api_field(
        description="How to modify the end time of a downtime.",
        example="relative",
    )
    value: int = api_field(
        description=(
            "A positive or negative number representing the amount of minutes to be added to or "
            "subtracted from the current end time. The value must be non-zero"
        ),
        example=60,
    )

    @model_validator(mode="after")
    def validate_non_zero(self) -> Self:
        if self.value == 0:
            raise ValueError("The value cannot be zero.")
        return self


ModifyEndTimeModel = Annotated[
    ModifyEndTimeAbsoluteModel | ModifyEndTimeRelativeModel, Discriminator("modify_type")
]


@api_model
class _BaseModifyDowntimeModel:
    end_time: ModifyEndTimeModel | None = api_field(
        description=(
            "The option how to modify the end time of a downtime. If modify_type is set to "
            "'absolute', then the end time will be set to the date time specified in the value "
            "field. If modify_type is set to 'relative', then the current end time will be "
            "modified by the amount of minutes specified in the value field. If this attribute "
            "is not present, then the end time will not be modified."
        ),
        example={"modify_type": "absolute", "value": "2024-03-06T12:00:00Z"},
        default=None,
    )
    comment: str | None = api_field(
        description="The comment for the downtime.",
        example="Security updates",
        default=None,
    )


@api_model
class ModifyDowntimeByIdModel(_BaseModifyDowntimeModel):
    modify_type: Literal["by_id"] = api_field(
        description="The option of how to select the downtimes to be targeted by the modification.",
        example="by_id",
    )
    site_id: AnnotatedSiteId = api_field(
        description="The site from which you want to modify a downtime.",
        example="mysite",
    )
    downtime_id: str = api_field(
        description="The id of the downtime",
        example="54",
    )


@api_model
class ModifyDowntimeByNameModel(_BaseModifyDowntimeModel):
    modify_type: Literal["params"] = api_field(
        description="The option of how to select the downtimes to be targeted by the modification.",
        example="params",
    )
    host_name: AnnotatedHostName = api_field(
        description="If set alone, then all downtimes of the host will be modified.",
        example="example.com",
    )
    service_descriptions: list[str] | None = api_field(
        description=(
            "If set, the downtimes of the listed services of the specified host will be "
            "modified. If a service has multiple downtimes then all will be modified"
        ),
        example=["CPU load", "Memory"],
        default=None,
    )


@api_model
class ModifyDowntimeByQueryModel(_BaseModifyDowntimeModel):
    modify_type: Literal["query"] = api_field(
        description="The option of how to select the downtimes to be targeted by the modification.",
        example="query",
    )
    query: Annotated[QueryExpression, query_expression_validator(Downtimes)] = api_field(
        description="A Livestatus filter expression for downtimes.",
        example='{"op": "=", "left": "host_name", "right": "example.com"}',
    )


@api_model
class ModifyDowntimeByHostGroupModel(_BaseModifyDowntimeModel):
    modify_type: Literal["hostgroup"] = api_field(
        description="The option of how to select the downtimes to be targeted by the modification.",
        example="hostgroup",
    )
    hostgroup_name: AnnotatedHostGroupName = api_field(
        description=(
            "Name of a valid hostgroup, all current downtimes for hosts in this group will be "
            "modified."
        ),
        example="windows",
    )


@api_model
class ModifyDowntimeByServiceGroupModel(_BaseModifyDowntimeModel):
    modify_type: Literal["servicegroup"] = api_field(
        description="The option of how to select the downtimes to be targeted by the modification.",
        example="servicegroup",
    )
    servicegroup_name: AnnotatedServiceGroupName = api_field(
        description=(
            "Name of a valid servicegroup, all current downtimes for services in this group will be"
            " modified."
        ),
        example="windows",
    )
