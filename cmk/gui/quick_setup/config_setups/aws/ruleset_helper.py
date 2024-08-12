#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Any

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary, FormSpec, List, String
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
