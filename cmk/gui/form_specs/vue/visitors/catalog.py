#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast, Self

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.private.catalog import Catalog, Topic
from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.i18n import _

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement
from cmk.rulesets.v1.form_specs import Dictionary as FormSpecDictionary

from ._base import FormSpecVisitor
from ._registry import get_visitor
from ._type_defs import DEFAULT_VALUE, DefaultValue, EMPTY_VALUE, EmptyValue
from ._utils import (
    base_i18n_form_spec,
    compute_validation_errors,
    compute_validators,
    create_validation_error,
    get_title_and_help,
)


class CatalogVisitor(FormSpecVisitor[Catalog, Mapping[str, object]]):
    def _compute_default_values(self) -> Mapping[str, object]:
        return {topic.name: DEFAULT_VALUE for topic in self.form_spec.topics}

    def _parse_value(self, raw_value: object) -> Mapping[str, object] | EmptyValue:
        if isinstance(raw_value, DefaultValue):
            raw_value = self._compute_default_values()
        if not isinstance(raw_value, dict):
            return EMPTY_VALUE
        return raw_value

    def _to_vue(
        self, raw_value: object, parsed_value: Mapping[str, object] | EmptyValue
    ) -> tuple[shared_type_defs.Catalog, Mapping[str, object]]:
        title, help_text = get_title_and_help(self.form_spec)
        if isinstance(parsed_value, EmptyValue):
            parsed_value = {}
        topics = []
        topic_values = {}
        for topic in self.form_spec.topics:
            topic_value = parsed_value.get(topic.name, {})
            dict_visitor = get_visitor(topic.dictionary, self.options)
            topic_schema, topic_vue_value = dict_visitor.to_vue(topic_value)
            topics.append(
                shared_type_defs.Topic(
                    name=topic.name,
                    dictionary=cast(shared_type_defs.Dictionary, topic_schema),
                )
            )
            topic_values[topic.name] = topic_vue_value

        return (
            shared_type_defs.Catalog(
                title=title,
                help=help_text,
                i18n_base=base_i18n_form_spec(),
                topics=topics,
            ),
            topic_values,
        )

    def _validate(
        self, raw_value: object, parsed_value: Mapping[str, object] | EmptyValue
    ) -> list[shared_type_defs.ValidationMessage]:
        if isinstance(parsed_value, EmptyValue):
            return create_validation_error(
                "" if isinstance(raw_value, DefaultValue) else raw_value,
                Title("Invalid integer number"),
            )
        validations = [*compute_validation_errors(compute_validators(self.form_spec), parsed_value)]

        for topic in self.form_spec.topics:
            if topic.name not in parsed_value:
                validations.append(
                    shared_type_defs.ValidationMessage(
                        location=[topic.name],
                        message=_("Missing catalog topic."),
                        invalid_value=None,
                    )
                )
                continue

            element_visitor = get_visitor(topic.dictionary, self.options)
            for validation in element_visitor.validate(parsed_value[topic.name]):
                validations.append(
                    shared_type_defs.ValidationMessage(
                        location=[topic.name] + validation.location,
                        message=validation.message,
                        invalid_value=validation.invalid_value,
                    )
                )
        return validations

    def _to_disk(
        self, raw_value: object, parsed_value: Mapping[str, object]
    ) -> Mapping[str, object]:
        disk_values = {}
        for topic in self.form_spec.topics:
            element_visitor = get_visitor(topic.dictionary, self.options)
            if (topic_value := parsed_value.get(topic.name)) is not None:
                disk_values[topic.name] = element_visitor.to_disk(topic_value)
        return disk_values


Headers = Sequence[tuple[str, Sequence[str]] | tuple[str, str, Sequence[str]]]


@dataclass(frozen=True, kw_only=True)
class Dict2CatalogConverter:
    catalog: Catalog

    @classmethod
    def build_from_dictionary(cls, dictionary: FormSpecDictionary, headers: Headers) -> Self:
        return cls._build_from_formspec_dictionary(dictionary, headers)

    @staticmethod
    def _normalize_header(
        header: tuple[str, Sequence[str]] | tuple[str, str, Sequence[str]],
    ) -> tuple[str, str | None, Sequence[str]]:
        # normalized various header configurations
        # title / css classes / elements
        if isinstance(header, tuple):
            if len(header) == 2:
                return header[0], None, header[1]
            if len(header) == 3:
                return header[0], header[1], header[2]
            raise ValueError("invalid header tuple length")
        raise ValueError("invalid header type")

    @classmethod
    def _build_from_formspec_dictionary(
        cls, dictionary: FormSpecDictionary, headers: Headers
    ) -> Self:
        topic_elements: dict[str, dict[str, DictElement[Any]]] = {}
        topic_title: dict[str, Title] = {}
        element_to_topic: dict[str, str] = {}
        # Prepare topics assignments
        for idx, header in enumerate(headers):
            title, _css, elements_in_topic = cls._normalize_header(header)
            topic_name = f"topic{idx}"
            topic_elements[topic_name] = {}
            topic_title[topic_name] = Title(  # pylint: disable=localization-of-non-literal-string
                title
            )
            for topic_element in elements_in_topic:
                element_to_topic[topic_element] = topic_name

        # Split elements into topics
        for dict_name, dict_value in dictionary.elements.items():
            # TODO: names not mentioned in header?
            topic_name = element_to_topic[dict_name]
            topic_elements[topic_name][dict_name] = dict_value

        topics = []
        for topic_name, elements in topic_elements.items():
            topics.append(
                Topic(
                    name=topic_name,
                    dictionary=FormSpecDictionary(title=topic_title[topic_name], elements=elements),
                )
            )

        return cls(catalog=Catalog(topics=topics))

    def convert_flat_to_catalog_config(
        self, flat_config: dict[str, object]
    ) -> Mapping[str, dict[str, object]]:
        topic_for_name: dict[str, str] = {}
        for topic in self.catalog.topics:
            for element_name, _element_value in topic.dictionary.elements.items():
                topic_for_name[element_name] = topic.name

        catalog_config: dict[str, dict[str, object]] = {}
        for name, value in flat_config.items():
            if (target_topic := topic_for_name.get(name)) is None:
                raise MKGeneralException(
                    f"Cannot convert to catalog config. Key {name} has no topic"
                )
            catalog_config.setdefault(target_topic, {})[name] = value

        return catalog_config

    def convert_catalog_to_flat_config(
        self, config: dict[str, dict[str, object]]
    ) -> dict[str, object]:
        return {k: v for values in config.values() for k, v in values.items()}
