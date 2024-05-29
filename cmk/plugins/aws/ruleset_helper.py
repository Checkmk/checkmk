#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Any, Literal

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    FormSpec,
    List,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError


def _validate_aws_tags(values: Sequence[Any]) -> object:
    used_keys = []
    for tag_dict in values:
        tag_key = tag_dict["key"]
        tag_values = tag_dict["values"]
        if tag_key not in used_keys:
            used_keys.append(tag_key)
        else:
            raise ValidationError(
                Message("Each tag key must be unique and cannot be used multiple times.")
            )
        if tag_key.startswith("aws:"):
            raise ValidationError(Message("Do not use 'aws:' prefix for the key."))
        if len(tag_key) > 128:
            raise ValidationError(Message("The maximum key length is 128 characters."))
        if len(values) > 50:
            raise ValidationError(Message("The maximum number of tags per resource is 50."))
        for tag_value in tag_values:
            if len(tag_value) > 256:
                raise ValidationError(Message("The maximum value length is 256 characters."))
            if tag_value.startswith("aws:"):
                raise ValidationError(Message("Do not use 'aws:' prefix for the value."))
    return values


def formspec_aws_tags(title: Title | None = None) -> FormSpec:
    return List(
        help_text=Help(
            "For information on AWS tag configuration, visit "
            "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Tags.html"
        ),
        title=title,
        element_template=Dictionary(
            elements={
                "key": DictElement(
                    parameter_form=String(
                        title=Title("Key"),
                    ),
                    required=True,
                ),
                "values": DictElement(
                    parameter_form=List(
                        element_template=String(label=Label("Value")),
                        add_element_label=Label("Add new value"),
                        remove_element_label=Label("Remove value"),
                        no_element_label=Label("No values defined"),
                        editable_order=False,
                    ),
                    required=True,
                ),
            },
        ),
        add_element_label=Label("Add new tag"),
        remove_element_label=Label("Remove tag"),
        no_element_label=Label("No tags defined"),
        editable_order=False,
        custom_validate=[_validate_aws_tags],
    )


def service_dict_element(
    title: Title,
    extra_elements: dict[str, DictElement],
    default_enabled: bool = True,
    filterable_by_tags: bool = True,
    filterable_by_name: bool = True,
) -> DictElement:
    elements: list[CascadingSingleChoiceElement] = [
        CascadingSingleChoiceElement(
            title=Title("Do not monitor service"),
            name="none",
            parameter_form=FixedValue(value=None),
        ),
        CascadingSingleChoiceElement(
            name="all",
            title=Title("Monitor all instances"),
            parameter_form=Dictionary(
                elements={
                    **extra_elements,
                }
            ),
        ),
    ]
    if filterable_by_tags:
        elements.append(
            CascadingSingleChoiceElement(
                name="tags",
                title=Title(
                    "Monitor instances with explicit AWS service tags ignoring overall tag filters"
                ),
                parameter_form=Dictionary(
                    elements={
                        "tags": DictElement(
                            parameter_form=formspec_aws_tags(),
                            required=True,
                        ),
                        **extra_elements,
                    },
                ),
            )
        )
    if filterable_by_name:
        elements.append(
            CascadingSingleChoiceElement(
                name="names",
                title=Title(
                    "Monitor instances with explicit service names ignoring overall tag filters"
                ),
                parameter_form=Dictionary(
                    elements={
                        "names": DictElement(
                            parameter_form=List(
                                element_template=String(label=Label("Service name")),
                                add_element_label=Label("Add new name"),
                                remove_element_label=Label("Remove name"),
                                no_element_label=Label("No names defined"),
                                editable_order=False,
                            ),
                            required=True,
                        ),
                        **extra_elements,
                    },
                ),
            )
        )

    return DictElement(
        parameter_form=CascadingSingleChoice(
            help_text=Help(
                "<b>Monitor all instances:</b> "
                "<br>If overall tags are specified below, then all "
                "service instances will be filtered by those tags. Otherwise, "
                "all instances will be collected.<br><br><b>Monitor instances "
                "with explicit AWS service tags ignoring overall tag "
                "filters:</b><br>Specify explicit tags for these services. The "
                "overall tags will be ignored for these services.<br><br><b>Monitor "
                "instances with explicit service names ignoring overall tag "
                "filters:</b><br>Use this option to specify explicit names. "
                "The overall tags will be ignored for these services."
            ),
            title=title,
            elements=elements,
            prefill=DefaultValue("all" if default_enabled else "none"),
        ),
        required=True,
    )


def formspec_aws_limits() -> dict[str, DictElement]:
    return {
        "limits": DictElement(
            required=True,
            parameter_form=SingleChoice(
                title=Title("Service limits"),
                elements=[
                    SingleChoiceElement(
                        title=Title("Monitor limits"),
                        name="limits",
                    ),
                    SingleChoiceElement(
                        title=Title("Do not monitor limits"),
                        name="no_limits",
                    ),
                ],
                prefill=DefaultValue("limits"),
                help_text=Help(
                    "If limits are monitored, all instances will be fetched "
                    "regardless of any name or tag restrictions that may have been "
                    "configured."
                ),
            ),
        )
    }


def convert_tag_list(tags: list[tuple[str, list[str] | str]]) -> list[dict[str, list[str] | str]]:
    return [
        {"key": key, "values": values if isinstance(values, list) else [values]}
        for key, values in tags
    ]


def _convert_selection(
    selection: Any,
) -> tuple[Literal["all", "tags", "names"], dict[str, object]]:
    if selection == "all":
        return "all", {}
    selection_type, selection_values = selection
    if selection_type == "tags":
        assert isinstance(selection_values, list)
        return selection_type, {"tags": convert_tag_list(selection_values)}
    if selection_type == "names":
        return selection_type, {"names": selection_values}

    raise ValueError(f"Unknown selection type: {selection_type}")


def migrate_global_service(values: dict, service: str) -> None:
    if service not in values:
        values[service] = ("none", None)

    if isinstance(values[service], dict):
        selection, selection_vars = _convert_selection(values[service].pop("selection"))
        values[service] = (
            selection,
            {**selection_vars, **values[service]},
        )


def migrate_regional_service(
    values: dict, service: str, selection_vs_str: str = "selection"
) -> None:
    if service not in values:
        values[service] = ("none", None)

    if isinstance(values[service], dict):
        if "limits" in values[service]:
            values[service]["limits"] = "limits"
        else:
            values[service]["limits"] = "no_limits"

        selection, selection_vars = _convert_selection(values[service].pop(selection_vs_str))
        values[service] = (
            selection,
            {**selection_vars, **values[service]},
        )
