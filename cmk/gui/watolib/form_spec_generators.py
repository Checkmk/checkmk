#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from cmk.gui.config import active_config
from cmk.gui.form_specs.unstable import (
    CascadingSingleChoiceExtended,
    LegacyValueSpec,
    SingleChoiceEditable,
)
from cmk.gui.form_specs.unstable.cascading_single_choice_extended import (
    CascadingSingleChoiceElementExtended,
)
from cmk.gui.i18n import translate_to_current_language
from cmk.gui.watolib.host_attributes import (
    ABCHostAttributeValueSpec,
    all_host_attributes,
    sorted_host_attribute_topics,
    sorted_host_attributes_by_topic,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.timeperiods import load_timeperiods
from cmk.rulesets.internal.form_specs import (
    ListExtended,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import DefaultValue
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.shared_typing.configuration_entity import ConfigEntityType
from cmk.shared_typing.vue_formspec_components import CascadingSingleChoiceLayout
from cmk.utils.timeperiod import TimeperiodName

T = TypeVar("T")


def create_full_path_folder_choice(
    title: Title,
    help_text: Help | None,
    custom_validate: Sequence[Callable[[str], object]] | None = None,
    allow_new_folder_creation: bool = False,
) -> SingleChoiceExtended[str] | SingleChoiceEditable:
    choices = folder_tree().folder_choices_fulltitle()

    if allow_new_folder_creation:
        return SingleChoiceEditable(
            # FormSpec
            title=title,
            help_text=help_text,
            custom_validate=custom_validate,
            # SingleChoiceEditable
            entity_type=ConfigEntityType.folder,
            entity_type_specifier="all",  # must not be empty, unused
            prefill=DefaultValue(""),
            create_element_label=Label("Create new"),
            allow_editing_existing_elements=False,
        )

    return SingleChoiceExtended[str](
        title=title,
        help_text=help_text,
        elements=[
            SingleChoiceElementExtended(
                name=choice[0],
                title=Title(choice[1]),  # astrein: disable=localization-checker
            )
            for choice in choices
        ],
        prefill=DefaultValue(""),
        custom_validate=custom_validate,
    )


def _get_timeperiod_choices() -> Sequence[SingleChoiceElementExtended[TimeperiodName]]:
    timeperiods = load_timeperiods()

    elements = [
        SingleChoiceElementExtended(
            name=name,
            title=Title(  # astrein: disable=localization-checker
                "{} - {}".format(name, tp["alias"])
            ),
        )
        for (name, tp) in timeperiods.items()
    ]
    if TimeperiodName("24X7") not in timeperiods.keys():
        always = SingleChoiceElementExtended(name=TimeperiodName("24X7"), title=Title("Always"))
        elements.insert(0, always)

    return sorted(elements, key=lambda x: x.title.localize(translate_to_current_language).lower())


def create_timeperiod_selection(
    title: Title | None = None,
    help_text: Help | None = None,
) -> SingleChoiceExtended[TimeperiodName]:
    return SingleChoiceExtended[TimeperiodName](
        title=title or Title("Select a time period"),
        help_text=help_text,
        elements=_get_timeperiod_choices(),
    )


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
