#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from datetime import datetime, timedelta

from marshmallow_oneofschema import OneOfSchema

from cmk.gui.fields import Timestamp
from cmk.gui.fields.base import BaseSchema
from cmk.gui.plugins.openapi.endpoints.sla.common import CustomTimeRange, PreDefinedTimeRange

from cmk import fields

SLA_AGREEMENT = fields.String(
    required=True,
    enum=["broken", "fulfilled"],
    description="Whether the SLA agreement was broken or fulfilled during this period."
    "The agreement is considered broken if at least one agreement of the "
    "defined state configurations was broken.",
    example=False,
)


class SLATimeRange(OneOfSchema):
    type_field = "range_type"
    type_field_remove = False
    type_schemas = {
        "pre_defined": PreDefinedTimeRange,
        "custom": CustomTimeRange,
    }

    def get_obj_type(self, obj):
        range_definition = obj.get("range_type")
        if range_definition in self.type_schemas:
            return range_definition

        raise Exception("Unknown object type: %s" % repr(obj))


class StateDurations(BaseSchema):
    ok_indowntime = fields.Float(
        description="The time duration for how long the service was in the OK state or "
        "in downtime.",
        example=10.0,
    )
    warn = fields.Float(
        description="The time duration for how long the service was in the WARN state.",
        example=10.0,
    )
    crit = fields.Float(
        description="The time duration for how long the service was in the CRIT state.",
        example=10.0,
    )
    unknown_unmonitored = fields.Float(
        description="The time duration for how long the service was in the UNKNOWN state or "
        "unmonitored.",
        example=10.0,
    )


class StateSubResult(BaseSchema):
    deviation_value = fields.Float(
        description="The deviation value of the SLA agreement. The deviation value is the "
        "difference between the observed and computed value. The meaning differs "
        "depending on the configured SLA computation type.",
        example=1.0,
    )
    deviation_state = fields.String(
        description="The deviation state of the SLA agreement. The deviation state is respective "
        "to the configured warn and crit levels and the determined deviation value.",
        enum=["ok", "warn", "crit"],
        example="ok",
    )
    sla_agreement = SLA_AGREEMENT


class SubResultBase(BaseSchema):
    state = fields.Nested(
        StateSubResult,
        description="The state of the SLA agreement",
        example={
            "deviation_value": 1.0,
            "deviation_state": "ok",
            "sla_agreement": "fulfilled",
        },
    )


class ServiceStatePercentageStateRequirement(BaseSchema):
    observed_state = fields.String(
        enum=["ok", "warn", "crit", "unknown"],
        description="The configured state for which the SLA agreement is checked.",
        example="ok",
    )
    condition = fields.String(
        enum=["more_than", "less_than"],  # this corresponds to min, max in the UI
        description="The reference condition for which the observed state is compared to.",
        example="more_than",
    )
    observed_percentage = fields.Float(
        description="The reference percentage value for which the condition is checked.",
        example=10.0,
    )


class Levels(BaseSchema):
    warn = fields.Float(
        description="The warning level of the SLA agreement.",
        example=10.0,
    )
    crit = fields.Float(
        description="The critical level of the SLA agreement.",
        example=10.0,
    )


class MonitoringLevels(BaseSchema):
    levels = fields.Nested(
        Levels,
        description="The levels of the SLA agreement.",
        example={"warn": 10.0, "crit": 10.0},
    )
    limit = fields.Float(
        description="The limit of the SLA agreement.",
        example=10.0,
    )


class ServiceStatePercentageConfig(BaseSchema):
    state_requirement = fields.Nested(
        ServiceStatePercentageStateRequirement,
        description="The configured state for which the SLA agreement is checked.",
    )
    monitoring_levels = fields.Nested(
        MonitoringLevels,
        description="The monitoring levels for which the SLA agreement is checked.",
        example={"levels": {"warn": 10.0, "crit": 10.0}, "limit": 10.0},
    )


class ServiceOutageCountStateRequirement(BaseSchema):
    observed_state = fields.String(
        enum=["ok", "warn", "crit", "unknown"],
        description="The state for which the requirement is checked",
        example="ok",
    )
    threshold_count = fields.String(
        enum=["more_than", "less_than"],  # this corresponds to min, max in the UI
        description="The threshold count for which the service is allowed to break the requirement "
        "condition before the SLA agreement is considered broken.",
        example="more_than",
    )
    allowed_duration = fields.Float(
        description="The duration in second for which the service is allowed to be in the "
        "observed state.",
        example=10.0,
    )


class ServiceOutageCountConfig(BaseSchema):
    state_requirement = fields.Nested(
        ServiceOutageCountStateRequirement,
        description="The state requirement for which the SLA agreement is checked.",
        example={
            "observed_state": "ok",
            "threshold_count": "more_than",
            "allowed_duration": 10.0,
        },
    )


class ServiceStatePercentageSubResult(SubResultBase):
    config = fields.Nested(ServiceStatePercentageConfig)


class ServiceOutageCountSubResult(SubResultBase):
    config = fields.Nested(ServiceOutageCountConfig)


class TimeRange(BaseSchema):
    start = Timestamp(
        description="The start time of the period",
        example=str(datetime.now() - timedelta(minutes=1)),
        required=True,
    )
    end = Timestamp(
        description="The end time of the period",
        example=str(datetime.now()),
        required=True,
    )


class PeriodResultBase(BaseSchema):
    duration = fields.Float(
        description="The duration of the time range in seconds.",
        example=3600.0,
    )
    time_range = fields.Nested(
        TimeRange,
        description="The time range of the period.",
    )
    sla_agreement = SLA_AGREEMENT


class ServicePercentagePeriodResult(PeriodResultBase):
    state_durations = fields.Nested(
        StateDurations,
        description="The percentage of the duration for which the service was in the "
        "underlying states",
        example={"ok": 10.0, "warn": 10.0, "crit": 10.0, "unknown": 10.0},
    )
    sub_results = fields.List(
        fields.Nested(ServiceStatePercentageSubResult),
        description="The sub results of the service state percentage period result.",
    )


class ServiceOutageCountPeriodResult(PeriodResultBase):
    sub_results = fields.List(
        fields.Nested(ServiceOutageCountSubResult),
        description="The sub results of the service outage count period result.",
    )


class PluginResultBase(BaseSchema):
    plugin_id = fields.String(
        description="The id of the plugin.",
        enum=["service_state_percentage", "service_outage_count"],
        example="service_state_percentage",
    )
    time_range_sla_duration = fields.Float(
        required=True,
        description="The duration of the time range in seconds.",
        example=3600.0,
    )


class PluginPercentageStateComputedResult(PluginResultBase):
    period_results = fields.List(
        fields.Nested(ServicePercentagePeriodResult),
        description="The period results of the service percentage state computation plugin.",
    )


class PluginOutageCountComputedResult(PluginResultBase):
    period_results = fields.List(
        fields.Nested(ServiceOutageCountPeriodResult),
        description="The period results of the service outage count computation plugin.",
    )


class PluginResult(OneOfSchema):
    type_field = "plugin_id"
    type_schemas = {
        "service_state_percentage": PluginPercentageStateComputedResult,
        "service_outage_count": PluginPercentageStateComputedResult,
    }

    def get_obj_type(self, obj):
        plugin_id = obj.get("plugin_id")
        if plugin_id in self.type_schemas:
            return plugin_id

        raise Exception("Unknown object type: %s" % repr(obj))


class Service(BaseSchema):
    site = fields.String(
        description="The ID of the site.",
        example="production",
    )
    host_name = fields.String(
        description="The name of the host.",
        example="heute",
    )
    service_description = fields.String(
        description="The description of the service for which the SLA is computed.",
        example="CPU load",
    )


class SLAComputeResult(BaseSchema):
    service = fields.Nested(
        Service,
        description="The service entity for which the SLA is computed.",
        example={"site_id": "production", "host_name": "heute", "service_description": "CPU load"},
    )
    sla_id = fields.String(
        description="The ID of the SLA.",
        example="sla_configuration_1",
    )
    time_range = fields.Nested(
        SLATimeRange,
        description="The time range for which the SLA is computed.",
    )
    sla_period = fields.String(
        enum=["monthly", "weekly", "daily"],
        description="The configured SLA period.",
        example="monthly",
    )
    results = fields.List(
        fields.Nested(PluginResult),
        description="The period results of the SLA computation.",
    )


class SLAComputedResultCollection(BaseSchema):
    domainType = fields.Constant(
        "sla_computed",
        description="The domain type of the objects in the collection",
    )
    value = fields.List(
        fields.Nested(SLAComputeResult),
        description="The list of SLA computed results.",
    )
