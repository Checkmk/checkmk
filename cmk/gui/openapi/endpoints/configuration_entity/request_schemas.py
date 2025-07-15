#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk import fields
from cmk.gui.fields.base import BaseSchema
from cmk.shared_typing.configuration_entity import ConfigEntityType


class CreateConfigurationEntity(BaseSchema):
    entity_type = fields.String(
        enum=[t.value for t in ConfigEntityType],
        required=True,
        description="Type of configuration entity",
        example=ConfigEntityType.notification_parameter.value,
    )
    entity_type_specifier = fields.String(
        required=True,
        description="Specifier for the entity type",
        example="mail",
    )
    data = fields.Dict(
        required=True,
        example={},
        description="The data of the configuration entity",
    )


class UpdateConfigurationEntity(BaseSchema):
    entity_type = fields.String(
        enum=[t.value for t in ConfigEntityType],
        required=True,
        description="Type of configuration entity",
        example=ConfigEntityType.notification_parameter.value,
    )
    entity_type_specifier = fields.String(
        required=True,
        description="Specifier for the entity type",
        example="mail",
    )
    entity_id = fields.String(
        required=True,
        description="Object id of the configuration entity",
        example="b43b060b-3b8c-41cf-8405-dddc6dd02575",
    )
    data = fields.Dict(
        required=True,
        example={},
        description="The data of the configuration entity",
    )
