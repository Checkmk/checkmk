#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk import fields
from cmk.gui.fields.base import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, Linkable


class ServiceDiscoveryRunLogs(BaseSchema):
    result = fields.List(
        fields.String(),
        description="The result messages",
        required=True,
    )
    progress = fields.List(
        fields.String(),
        description="The progress messages",
        required=True,
    )


class ServiceDiscoveryRunExtensions(BaseSchema):
    active = fields.Boolean(
        description="Whether the service discovery run is active",
        required=True,
    )
    state = fields.String(
        description="Current state of the service discovery run",
        enum=["initialized", "running", "finished", "stopped", "exception"],
        required=True,
    )
    logs = fields.Nested(
        ServiceDiscoveryRunLogs,
        description="The logs of the service discovery run",
        required=True,
    )


class ServiceDiscoveryRunSchema(DomainObject):
    extensions = fields.Nested(
        ServiceDiscoveryRunExtensions,
        description="Additional information about the service discovery run",
        required=True,
    )


class ServiceDiscoveryResultCheckTableValueExtensions(BaseSchema):
    host_name = fields.String(
        description="The name of the host",
        required=True,
    )
    check_plugin_name = fields.String(
        description="The name of the check plugin",
        required=True,
    )
    service_name = fields.String(
        description="The name of the service",
        required=True,
    )
    service_item = fields.String(
        description="The name of the service item",
    )
    service_phase = fields.String(
        description="The name of the service phase",
        required=True,
    )


class ServiceDiscoveryResultCheckTableValue(Linkable):
    id = fields.String(
        description="The name of the check",
        required=True,
    )
    memberType = fields.Constant("property", required=True)
    value = fields.String(
        description="Current service phase of the check",
        required=True,
    )
    format = fields.Constant("string", required=True)
    title = fields.String(
        description="Current service phase of the check",
        required=True,
    )
    extensions = fields.Nested(
        ServiceDiscoveryResultCheckTableValueExtensions,
        description="Additional information about the check",
        required=True,
    )


class ServiceDiscoveryResultHostLabelValue(BaseSchema):
    value = fields.String(
        description="The value of the host label",
        required=True,
    )
    plugin_name = fields.String(
        description="The name of the plugin that discovered the host label",
    )


class ServiceDiscoveryResultExtensions(BaseSchema):
    check_table = fields.Dict(
        keys=fields.String(),
        values=fields.Nested(ServiceDiscoveryResultCheckTableValue),
        description="The changed checks for this host",
        required=True,
    )
    host_labels = fields.Dict(
        keys=fields.String(),
        values=fields.Nested(ServiceDiscoveryResultHostLabelValue),
        description="The labels of the host",
        required=True,
    )
    vanished_labels = fields.Dict(
        keys=fields.String(),
        values=fields.Nested(ServiceDiscoveryResultHostLabelValue),
        description="The labels that have vanished",
        required=True,
    )
    changed_labels = fields.Dict(
        keys=fields.String(),
        values=fields.Nested(ServiceDiscoveryResultHostLabelValue),
        description="The labels that have changed",
        required=True,
    )


class ServiceDiscoveryResultSchema(DomainObject):
    extensions = fields.Nested(
        ServiceDiscoveryResultExtensions,
        description="Additional information about the service discovery result",
        required=True,
    )
