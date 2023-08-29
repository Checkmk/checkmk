#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _, _u
from cmk.gui.valuespec import (
    ABCPageListOfMultipleGetChoice,
    CascadingDropdown,
    DropdownChoice,
    FixedValue,
    Labels,
    ListOf,
    ListOfMultiple,
    SingleLabel,
    Transform,
    Tuple,
)


class DictHostTagCondition(Transform):
    def __init__(self, title, help_txt) -> None:  # type: ignore[no-untyped-def]
        super().__init__(
            valuespec=ListOfMultiple(
                title=title,
                help=help_txt,
                choices=self._get_cached_tag_group_choices(),
                choice_page_name="ajax_dict_host_tag_condition_get_choice",
                add_label=_("Add tag condition"),
                del_label=_("Remove tag condition"),
            ),
            to_valuespec=self._to_valuespec,
            from_valuespec=self._from_valuespec,
        )

    @request_memoize()
    def _get_cached_tag_group_choices(self):
        # In case one has configured a lot of tag groups / id recomputing this for
        # every DictHostTagCondition instance takes a lot of time
        return self._get_tag_group_choices()

    def _get_tag_group_choices(self):
        choices = []
        all_topics = active_config.tags.get_topic_choices()
        tag_groups_by_topic = dict(active_config.tags.get_tag_groups_by_topic())
        aux_tags_by_topic = dict(active_config.tags.get_aux_tags_by_topic())
        for topic_id, _topic_title in all_topics:
            for tag_group in tag_groups_by_topic.get(topic_id, []):
                choices.append(self._get_tag_group_choice(tag_group))

            for aux_tag in aux_tags_by_topic.get(topic_id, []):
                choices.append(self._get_aux_tag_choice(aux_tag))

        return choices

    def _to_valuespec(self, host_tag_conditions):
        valuespec_value = {}
        for tag_group_id, tag_condition in host_tag_conditions.items():
            if isinstance(tag_condition, dict) and "$or" in tag_condition:
                value = self._ored_tags_to_valuespec(tag_condition["$or"])
            elif isinstance(tag_condition, dict) and "$nor" in tag_condition:
                value = self._nored_tags_to_valuespec(tag_condition["$nor"])
            else:
                value = self._single_tag_to_valuespec(tag_condition)

            valuespec_value[tag_group_id] = value

        return valuespec_value

    def _ored_tags_to_valuespec(self, tag_conditions):
        return ("or", tag_conditions)

    def _nored_tags_to_valuespec(self, tag_conditions):
        return ("nor", tag_conditions)

    def _single_tag_to_valuespec(self, tag_condition):
        if isinstance(tag_condition, dict):
            if "$ne" in tag_condition:
                return ("is_not", tag_condition["$ne"])
            raise NotImplementedError()
        return ("is", tag_condition)

    def _from_valuespec(self, valuespec_value):
        tag_conditions = {}
        for tag_group_id, (operator, operand) in valuespec_value.items():
            if operator in ["is", "is_not"]:
                tag_group_value = self._single_tag_from_valuespec(operator, operand)
            elif operator in ["or", "nor"]:
                tag_group_value = {
                    "$%s" % operator: operand,
                }
            else:
                raise NotImplementedError()

            tag_conditions[tag_group_id] = tag_group_value
        return tag_conditions

    def _single_tag_from_valuespec(self, operator, tag_id):
        if operator == "is":
            return tag_id
        if operator == "is_not":
            return {"$ne": tag_id}
        raise NotImplementedError()

    def _get_tag_group_choice(self, tag_group):
        tag_choices = tag_group.get_tag_choices()

        if len(tag_choices) == 1:
            return self._single_tag_choice(
                tag_group_id=tag_group.id,
                choice_title=tag_group.choice_title,
                tag_id=tag_group.tags[0].id,
                title=tag_group.tags[0].title,
            )

        tag_id_choice = ListOf(
            valuespec=DropdownChoice(
                choices=tag_choices,
            ),
            style=ListOf.Style.FLOATING,
            add_label=_("Add tag"),
            del_label=_("Remove tag"),
            magic="@@#!#@@",
            movable=False,
            validate=lambda value, varprefix: self._validate_tag_list(
                value, varprefix, tag_choices
            ),
        )

        return (
            tag_group.id,
            CascadingDropdown(
                label=tag_group.choice_title + " ",
                title=tag_group.choice_title,
                choices=[
                    ("is", _("is"), DropdownChoice(choices=tag_choices)),
                    ("is_not", _("is not"), DropdownChoice(choices=tag_choices)),
                    ("or", _("one of"), tag_id_choice),
                    ("nor", _("none of"), tag_id_choice),
                ],
                orientation="horizontal",
                default_value=("is", tag_choices[0][0]),
            ),
        )

    def _validate_tag_list(self, value, varprefix, tag_choices):
        seen = set()
        for tag_id in value:
            if tag_id in seen:
                raise MKUserError(
                    varprefix,
                    _("The tag '%s' is selected multiple times. A tag may be selected only once.")
                    % dict(tag_choices)[tag_id],
                )
            seen.add(tag_id)

    def _get_aux_tag_choice(self, aux_tag):
        return self._single_tag_choice(
            tag_group_id=aux_tag.id,
            choice_title=aux_tag.choice_title,
            tag_id=aux_tag.id,
            title=aux_tag.title,
        )

    def _single_tag_choice(self, tag_group_id, choice_title, tag_id, title):
        return (
            tag_group_id,
            Tuple(
                title=choice_title,
                elements=[
                    self._is_or_is_not(
                        label=choice_title + " ",
                    ),
                    FixedValue(
                        value=tag_id,
                        title=_u(title),
                        totext=_u(title),
                    ),
                ],
                show_titles=False,
                orientation="horizontal",
            ),
        )

    def _tag_choice(self, tag_group):
        return Tuple(
            title=_u(tag_group.choice_title),
            elements=[
                self._is_or_is_not(),
                DropdownChoice(choices=tag_group.get_tag_choices()),
            ],
            show_titles=False,
            orientation="horizontal",
        )

    def _is_or_is_not(self, **kwargs) -> DropdownChoice:  # type: ignore[no-untyped-def]
        return DropdownChoice(
            choices=[
                ("is", _("is")),
                ("is_not", _("is not")),
            ],
            **kwargs,
        )


class PageAjaxDictHostTagConditionGetChoice(ABCPageListOfMultipleGetChoice):
    def _get_choices(self, api_request):
        condition = DictHostTagCondition("Dummy title", "Dummy help")
        return condition._get_tag_group_choices()


class LabelCondition(Transform):
    def __init__(self, title, help_txt) -> None:  # type: ignore[no-untyped-def]
        super().__init__(
            valuespec=ListOf(
                valuespec=Tuple(
                    orientation="horizontal",
                    elements=[
                        DropdownChoice(
                            choices=[
                                ("is", _("has")),
                                ("is_not", _("has not")),
                            ],
                        ),
                        SingleLabel(
                            world=Labels.World.CONFIG,
                        ),
                    ],
                    show_titles=False,
                ),
                add_label=_("Add label condition"),
                del_label=_("Remove label condition"),
                style=ListOf.Style.FLOATING,
                movable=False,
            ),
            to_valuespec=self._to_valuespec,
            from_valuespec=self._from_valuespec,
            title=title,
            help=help_txt,
        )

    def _to_valuespec(self, label_conditions):
        valuespec_value = []
        for label_id, label_value in label_conditions.items():
            valuespec_value.append(self._single_label_to_valuespec(label_id, label_value))
        return valuespec_value

    def _single_label_to_valuespec(self, label_id, label_value):
        if isinstance(label_value, dict):
            if "$ne" in label_value:
                return ("is_not", {label_id: label_value["$ne"]})
            raise NotImplementedError()
        return ("is", {label_id: label_value})

    def _from_valuespec(self, valuespec_value):
        label_conditions = {}
        for operator, label in valuespec_value:
            if label:
                label_id, label_value = list(label.items())[0]
                label_conditions[label_id] = self._single_label_from_valuespec(
                    operator, label_value
                )
        return label_conditions

    def _single_label_from_valuespec(self, operator, label_value):
        if operator == "is":
            return label_value
        if operator == "is_not":
            return {"$ne": label_value}
        raise NotImplementedError()
