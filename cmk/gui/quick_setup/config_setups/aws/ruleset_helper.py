#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Any

from cmk.gui.form_specs.private import CascadingSingleChoiceExtended
from cmk.gui.form_specs.private.cascading_single_choice_extended import (
    CascadingSingleChoiceElementExtended,
)
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    FormSpec,
    List,
    MatchingScope,
    RegularExpression,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, ValidationError
from cmk.shared_typing.vue_formspec_components import CascadingSingleChoiceLayout


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
    return Dictionary(
        title=title,
        help_text=Help(
            "For information on AWS tag configuration, visit "
            "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Tags.html"
        ),
        elements={
            "restriction_tags": DictElement(
                parameter_form=List(
                    title=Title("Restrict monitoring services by one of these AWS tags"),
                    element_template=Dictionary(
                        elements={
                            "key": DictElement(
                                parameter_form=String(
                                    title=Title("Key"),
                                    custom_validate=[
                                        LengthInRange(
                                            min_value=1,
                                            error_msg=Message("Tags enabled but no key defined."),
                                        ),
                                    ],
                                ),
                                required=True,
                            ),
                            "values": DictElement(
                                parameter_form=List(
                                    title=Title("Values"),
                                    element_template=String(),
                                    add_element_label=Label("Add new value"),
                                    remove_element_label=Label("Remove value"),
                                    no_element_label=Label("No values defined"),
                                    editable_order=False,
                                    custom_validate=[
                                        LengthInRange(
                                            min_value=1,
                                            error_msg=Message(
                                                "Tags enabled but no values defined."
                                            ),
                                        ),
                                    ],
                                ),
                                required=True,
                            ),
                        },
                    ),
                    add_element_label=Label("Add new tag"),
                    remove_element_label=Label("Remove tag"),
                    no_element_label=Label("No tags defined"),
                    editable_order=False,
                    custom_validate=[
                        _validate_aws_tags,
                        LengthInRange(
                            min_value=1,
                            error_msg=Message("Restriction tags enabled but no tags defined."),
                        ),
                    ],
                )
            ),
            "import_tags": DictElement(
                parameter_form=CascadingSingleChoiceExtended(
                    title=Title("Import tags as host labels"),
                    elements=[
                        CascadingSingleChoiceElementExtended(
                            name="all_tags",
                            title=Title("Import all valid tags"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElementExtended(
                            name="filter_tags",
                            title=Title("Filter valid tags by key pattern"),
                            parameter_form=RegularExpression(
                                predefined_help_text=MatchingScope.INFIX,
                                custom_validate=[
                                    LengthInRange(
                                        min_value=1,
                                        error_msg=Message(
                                            "Filtering tags enabled but no tags defined."
                                        ),
                                    ),
                                ],
                            ),
                        ),
                    ],
                    layout=CascadingSingleChoiceLayout.horizontal,
                    help_text=Help(
                        "By default, Checkmk imports the AWS tags for EC2 and ELB instances as "
                        "host labels for the respective piggyback hosts. The label syntax is "
                        "'cmk/aws/tag/{key}:{value}'.<br>Additionally, the piggyback hosts for EC2 "
                        "instances are given the host label 'cmk/aws/ec2:instance', which is done "
                        "independent of this option.<br>You can further restrict the imported tags "
                        "by specifying a pattern which Checkmk searches for in the key of the AWS "
                        "tag, or you can disable the import of AWS tags altogether."
                    ),
                    prefill=DefaultValue("all_tags"),
                ),
            ),
        },
    )
