#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import Any, TypeVar

from cmk.gui.config import active_config
from cmk.gui.form_specs.private import CascadingSingleChoiceExtended, LegacyValueSpec
from cmk.gui.form_specs.private.cascading_single_choice_extended import (
    CascadingSingleChoiceElementExtended,
)
from cmk.gui.form_specs.private.list_extended import ListExtended
from cmk.gui.watolib.host_attributes import (
    ABCHostAttributeValueSpec,
    all_host_attributes,
    sorted_host_attribute_topics,
    sorted_host_attributes_by_topic,
)
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.shared_typing.vue_formspec_components import CascadingSingleChoiceLayout

T = TypeVar("T")


def create_host_attributes_selection(
    default_host_attributes: Sequence[tuple[str, str]] | None,
    exclude_host_attributes: Sequence[str] | None = None,
) -> ListExtended[tuple[str, object]]:
    attribute_choices: list[CascadingSingleChoiceElementExtended[Any]] = []
    host_attributes = all_host_attributes(
        active_config.wato_host_attrs, active_config.tags.get_tag_groups_by_topic()
    )
    for topic, topic_title in sorted_host_attribute_topics(
        host_attributes, for_what="host", new=False
    ):
        for attr in sorted_host_attributes_by_topic(host_attributes, topic):
            if not isinstance(attr, ABCHostAttributeValueSpec):
                continue

            if not attr.is_visible(for_what="host", new=False) or not attr.editable():
                continue

            if exclude_host_attributes is not None and attr.name() in exclude_host_attributes:
                continue

            try:
                form_spec = attr.form_spec()
            except NotImplementedError:
                form_spec = LegacyValueSpec.wrap(attr.valuespec())

            attribute_choices.append(
                CascadingSingleChoiceElementExtended(
                    name=attr.name(),
                    title=Title("%s: %s") % (topic_title, attr.title()),
                    parameter_form=form_spec,
                )
            )

    assert attribute_choices, "No host attributes found"

    def _validate_attributes(value: Sequence[tuple[str, object]]) -> None:
        seen = set()
        for attr_name, _unused in value:
            if attr_name in seen:
                raise ValidationError(Message("Each attribute may be specified only once."))
            seen.add(attr_name)

    return ListExtended[tuple[str, object]](
        title=Title("Host attributes to set"),
        help_text=Help(
            "Host attributes apply to all new hosts from that connection. Changes apply on next "
            "execution."
        ),
        add_element_label=Label("Add attribute"),
        custom_validate=(_validate_attributes,),
        element_template=CascadingSingleChoiceExtended(
            layout=CascadingSingleChoiceLayout.horizontal,
            title=Title("Attribute"),
            elements=attribute_choices,
            prefill=DefaultValue(attribute_choices[0].name),
        ),
        prefill=DefaultValue(default_host_attributes or []),
    )
