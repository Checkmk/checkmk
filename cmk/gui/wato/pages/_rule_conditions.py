#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any, override, TypeVar

from cmk.utils.tags import AuxTag, TagGroup, TagGroupID, TagID

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _, _u
from cmk.gui.valuespec import (
    ABCPageListOfMultipleGetChoice,
    CascadingDropdown,
    DropdownChoice,
    FixedValue,
    ListOf,
    ListOfMultiple,
    Transform,
    Tuple,
)
from cmk.gui.valuespec.definitions import ValueSpec

_TagChoiceID = TypeVar("_TagChoiceID", TagGroupID, TagID)


def _is_or_is_not(label: str | None = None) -> DropdownChoice:
    return DropdownChoice(
        choices=[
            ("is", _("is")),
            ("is_not", _("is not")),
        ],
        label=label,
    )


def _single_tag_choice(
    tag_group_id: _TagChoiceID, choice_title: str, tag_id: TagID | None, title: str
) -> tuple[_TagChoiceID, Tuple]:
    return (
        tag_group_id,
        Tuple(
            title=choice_title,
            elements=[
                _is_or_is_not(
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


def _get_aux_tag_choice(aux_tag: AuxTag) -> tuple[TagID, Tuple]:
    return _single_tag_choice(
        tag_group_id=aux_tag.id,
        choice_title=aux_tag.choice_title,
        tag_id=aux_tag.id,
        title=aux_tag.title,
    )


def _validate_tag_list(
    value: Sequence[Any], varprefix: str, tag_choices: Sequence[tuple[TagID | None, str]]
) -> None:
    seen = set()
    for tag_id in value:
        if tag_id in seen:
            raise MKUserError(
                varprefix,
                _("The tag '%s' is selected multiple times. A tag may be selected only once.")
                % dict(tag_choices)[tag_id],
            )
        seen.add(tag_id)


def _get_tag_group_choice(tag_group: TagGroup) -> tuple[TagGroupID, Tuple | CascadingDropdown]:
    tag_choices = tag_group.get_non_empty_tag_choices()

    tag_id_choice = ListOf(
        valuespec=DropdownChoice(
            choices=tag_choices,
        ),
        style=ListOf.Style.FLOATING,
        add_label=_("Add tag"),
        del_label=_("Remove tag"),
        magic="@@#!#@@",
        movable=False,
        validate=lambda value, varprefix: _validate_tag_list(value, varprefix, tag_choices),
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


def _get_tag_group_choices() -> Sequence[tuple[TagID | TagGroupID, Tuple | CascadingDropdown]]:
    choices: list[tuple[TagID | TagGroupID, Tuple | CascadingDropdown]] = []
    all_topics = active_config.tags.get_topic_choices()
    tag_groups_by_topic = dict(active_config.tags.get_tag_groups_by_topic())
    aux_tags_by_topic = dict(active_config.tags.get_aux_tags_by_topic())
    for topic_id, _topic_title in all_topics:
        for tag_group in tag_groups_by_topic.get(topic_id, []):
            choices.append(_get_tag_group_choice(tag_group))

        for aux_tag in aux_tags_by_topic.get(topic_id, []):
            choices.append(_get_aux_tag_choice(aux_tag))

    return choices


@request_memoize()
def _get_cached_tag_group_choices() -> Sequence[
    tuple[TagID | TagGroupID, Tuple | CascadingDropdown]
]:
    # In case one has configured a lot of tag groups / id recomputing this for
    # every DictHostTagCondition instance takes a lot of time
    return _get_tag_group_choices()


class DictHostTagCondition(Transform):
    def __init__(self, title: str, help_txt: str) -> None:
        super().__init__(
            valuespec=ListOfMultiple(
                title=title,
                help=help_txt,
                choices=_get_cached_tag_group_choices(),
                choice_page_name="ajax_dict_host_tag_condition_get_choice",
                add_label=_("Add tag condition"),
                del_label=_("Remove tag condition"),
            ),
            to_valuespec=self._to_valuespec,
            from_valuespec=self._from_valuespec,
        )

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


class PageAjaxDictHostTagConditionGetChoice(ABCPageListOfMultipleGetChoice):
    @override
    def _get_choices(self, api_request: Mapping[str, str]) -> Sequence[tuple[str, ValueSpec]]:
        return _get_tag_group_choices()
