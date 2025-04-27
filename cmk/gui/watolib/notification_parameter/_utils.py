#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import NamedTuple

from cmk.ccc.i18n import _

from cmk.utils.notify_types import (
    NotificationParameterGeneralInfos,
    NotificationParameterID,
    NotificationParameterItem,
    NotificationParameterMethod,
)

from cmk.gui.form_specs.vue.form_spec_visitor import process_validation_messages
from cmk.gui.form_specs.vue.visitors import (
    DataOrigin,
    get_visitor,
    VisitorOptions,
)
from cmk.gui.watolib.notifications import NotificationParameterConfigFile
from cmk.gui.watolib.sample_config import new_notification_parameter_id

from ._registry import NotificationParameterRegistry

INTERNAL_TRANSFORM_ERROR = _("FormSpec and internal data structure mismatch")


@dataclass(frozen=True, kw_only=True)
class NotificationParameterDescription:
    ident: NotificationParameterID
    description: str


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
    *,
    object_id: NotificationParameterID | None,
    pprint_value: bool,
) -> NotificationParameterDescription:
    """Save a notification parameter set.

    Raises:
        FormSpecValidationError: if the data does not match the form spec
    """
    form_spec = registry.form_spec(parameter_method)
    visitor = get_visitor(form_spec, VisitorOptions(DataOrigin.FRONTEND))

    validation_errors = visitor.validate(data)
    process_validation_messages(validation_errors)

    disk_data = visitor.to_disk(data)
    item = _to_param_item(disk_data)

    parameter_id = (
        NotificationParameterID(object_id) if object_id else new_notification_parameter_id()
    )
    config_file = NotificationParameterConfigFile()
    notification_parameter = config_file.load_for_modification()
    notification_parameter.setdefault(parameter_method, {})[parameter_id] = item
    config_file.save(notification_parameter, pprint_value)

    return NotificationParameterDescription(
        ident=parameter_id, description=item["general"]["description"]
    )


def get_list_of_notification_parameter(
    parameter_method: NotificationParameterMethod,
) -> Sequence[NotificationParameterDescription]:
    notification_parameter = NotificationParameterConfigFile().load_for_reading()
    return [
        NotificationParameterDescription(ident=k, description=v["general"]["description"])
        for k, v in notification_parameter.get(parameter_method, {}).items()
    ]


class NotificationParameter(NamedTuple):
    description: str
    data: Mapping


def get_notification_parameter(
    registry: NotificationParameterRegistry,
    parameter_id: NotificationParameterID,
) -> NotificationParameter:
    """Get notification parameter to supply to frontend.

    Raises:
        KeyError: if notification parameter with parameter_id doesn't exist.
    """
    notification_parameter = NotificationParameterConfigFile().load_for_reading()
    method, item = next(
        (
            (method, item.get(parameter_id))
            for method, item in notification_parameter.items()
            if parameter_id in item
        ),
        (None, None),
    )
    if item is None or method is None:
        raise KeyError(parameter_id)
    form_spec = registry.form_spec(method)
    visitor = get_visitor(form_spec, VisitorOptions(DataOrigin.DISK))
    _, values = visitor.to_vue(item)
    assert isinstance(values, Mapping)
    assert isinstance(item, Mapping)
    assert isinstance(item["general"], Mapping)
    return NotificationParameter(description=item["general"]["description"], data=values)
