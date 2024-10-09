#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import NamedTuple, Sequence

from cmk.ccc.i18n import _

from cmk.utils.notify_types import (
    NotificationParameterGeneralInfos,
    NotificationParameterID,
    NotificationParameterItem,
    NotificationParameterMethod,
)

from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.form_specs.vue.visitors import (
    DataOrigin,
    DEFAULT_VALUE,
    get_visitor,
    VisitorOptions,
)
from cmk.gui.wato._notification_parameter._registry import NotificationParameterRegistry
from cmk.gui.watolib.notifications import NotificationParameterConfigFile
from cmk.gui.watolib.sample_config import new_notification_parameter_id

INTERNAL_TRANSFORM_ERROR = _("FormSpec and internal data structure mismatch")


def _to_param_item(data: object) -> NotificationParameterItem:
    if not isinstance(data, dict):
        raise ValueError(INTERNAL_TRANSFORM_ERROR)

    try:
        general = data["general"]
        if not isinstance(general, dict):
            raise ValueError(INTERNAL_TRANSFORM_ERROR)

        return NotificationParameterItem(
            general=NotificationParameterGeneralInfos(
                description=general["description"],
                comment=general.get("comment", ""),
                docu_url=general.get("docu_url", ""),
            ),
            parameter_properties=data["parameter_properties"],
        )
    except KeyError as exc:
        raise ValueError from exc


def save_notification_parameter(
    registry: NotificationParameterRegistry,
    parameter_method: NotificationParameterMethod,
    data: object,
    object_id: NotificationParameterID | None = None,
) -> NotificationParameterID | Sequence[shared_type_defs.ValidationMessage]:
    form_spec = registry.form_spec(parameter_method)
    visitor = get_visitor(form_spec, VisitorOptions(DataOrigin.FRONTEND))

    validation_errors = visitor.validate(data)
    if validation_errors:
        return validation_errors

    disk_data = visitor.to_disk(data)

    try:
        item = _to_param_item(disk_data)
    except ValueError as exc:
        return [
            shared_type_defs.ValidationMessage(location=[], message=str(exc), invalid_value=None)
        ]

    parameter_id = (
        NotificationParameterID(object_id) if object_id else new_notification_parameter_id()
    )
    config_file = NotificationParameterConfigFile()
    notification_parameter = config_file.load_for_modification()
    notification_parameter.setdefault(parameter_method, {})[parameter_id] = item
    config_file.save(notification_parameter)

    return parameter_id


class NotificationParameterSchema(NamedTuple):
    schema: shared_type_defs.FormSpec
    default_values: object


def get_notification_parameter_schema(
    registry: NotificationParameterRegistry, parameter_method: NotificationParameterMethod
) -> NotificationParameterSchema:
    form_spec = registry.form_spec(parameter_method)
    visitor = get_visitor(form_spec, VisitorOptions(DataOrigin.FRONTEND))
    schema, default_values = visitor.to_vue(DEFAULT_VALUE)
    return NotificationParameterSchema(schema=schema, default_values=default_values)


@dataclass(frozen=True, kw_only=True)
class NotificationParameterDescription:
    ident: NotificationParameterID
    description: str


def get_list_of_notification_parameter(
    parameter_method: NotificationParameterMethod,
) -> Sequence[NotificationParameterDescription]:
    notification_parameter = NotificationParameterConfigFile().load_for_reading()
    return [
        NotificationParameterDescription(ident=k, description=v["general"]["description"])
        for k, v in notification_parameter.get(parameter_method, {}).items()
    ]


def get_notification_parameter(
    parameter_method: NotificationParameterMethod,
    parameter_id: NotificationParameterID,
) -> NotificationParameterItem:
    notification_parameter = NotificationParameterConfigFile().load_for_reading()
    return notification_parameter[parameter_method][parameter_id]
