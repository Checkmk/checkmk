#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Self

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.form_specs.private import Catalog, Topic, TopicElement, TopicGroup
from cmk.gui.i18n import _

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement
from cmk.rulesets.v1.form_specs import Dictionary as FormSpecDictionary
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._registry import get_visitor
from ._type_defs import DataOrigin, DEFAULT_VALUE, DefaultValue, InvalidValue, VisitorOptions
from ._utils import (
    base_i18n_form_spec,
    create_validation_error,
    get_title_and_help,
    localize,
)

ModelTopic = str
ModelTopicElement = str
_ParsedValueModel = Mapping[ModelTopic, Mapping[ModelTopicElement, object]]
_FrontendModel = Mapping[ModelTopic, Mapping[ModelTopicElement, object]]


class CatalogVisitor(FormSpecVisitor[Catalog, _ParsedValueModel, _FrontendModel]):
    def _resolve_topic_to_elements(self, topic: Topic) -> Mapping[str, TopicElement]:
        topic_to_elements: dict[str, TopicElement] = {}
        if isinstance(topic.elements, list):
            # A list of TopicGroups
            for topic_group in topic.elements:
                for element_name, element in topic_group.elements.items():
                    topic_to_elements[element_name] = element
            return topic_to_elements

        # This topic only has TopicElements
        return topic.elements

    def _resolve_default_values(
        self, raw_value: DefaultValue | dict[str, dict[str, object] | DefaultValue]
    ) -> _ParsedValueModel:
        # The catalog can be treated as a dictionary of dictionaries
        # Because of this, the default value are resolved one level deeper
        tmp_value: dict[str, Any]
        if isinstance(raw_value, DefaultValue):
            tmp_value = {topic_name: DEFAULT_VALUE for topic_name in self.form_spec.elements.keys()}
        else:
            tmp_value = raw_value

        # Specific topics can be set to DefaultValue, too
        resolved_value: dict[str, dict[str, object]] = {}
        for topic_name, topic in self.form_spec.elements.items():
            topic_value = tmp_value.get(topic_name, DEFAULT_VALUE)
            resolved_value[topic_name] = (
                {
                    element_name: DEFAULT_VALUE
                    for element_name, element in self._resolve_topic_to_elements(topic).items()
                    if element.required
                }
                if isinstance(topic_value, DefaultValue)
                else topic_value
            )

        return resolved_value

    def _parse_value(self, raw_value: object) -> _ParsedValueModel | InvalidValue[_FrontendModel]:
        if not isinstance(raw_value, dict) and not isinstance(raw_value, DefaultValue):
            return InvalidValue(reason=_("Invalid catalog data"), fallback_value={})

        raw_value = self._resolve_default_values(raw_value)

        if not all(topic_name in raw_value for topic_name in self.form_spec.elements.keys()):
            return InvalidValue(reason=_("Invalid catalog data"), fallback_value={})

        return raw_value

    def _compute_topic_group_spec(
        self,
        topic_group: TopicGroup,
        element_lookup: dict[str, tuple[shared_type_defs.FormSpec, object]],
    ) -> shared_type_defs.TopicGroup:
        vue_topic_group = shared_type_defs.TopicGroup(
            title=localize(topic_group.title),
            elements=[],
        )
        for element_name, element in topic_group.elements.items():
            spec, value = element_lookup[element_name]
            element_spec = self._compute_topic_element_spec(element, element_name, spec, value)
            vue_topic_group.elements.append(element_spec)
        return vue_topic_group

    def _compute_topic_element_spec(
        self,
        element: TopicElement,
        element_name: str,
        element_spec: shared_type_defs.FormSpec,
        element_value: object,
    ) -> shared_type_defs.TopicElement:
        return shared_type_defs.TopicElement(
            name=element_name,
            required=element.required,
            parameter_form=element_spec,
            default_value=element_value,
        )

    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FrontendModel]
    ) -> tuple[shared_type_defs.Catalog, _FrontendModel]:
        title, help_text = get_title_and_help(self.form_spec)
        if isinstance(parsed_value, InvalidValue):
            parsed_value = parsed_value.fallback_value

        vue_value: dict[str, dict[str, object]] = {}
        vue_catalog = shared_type_defs.Catalog(
            title=title,
            help=help_text,
            elements=[],
            validators=[],
            i18n_base=base_i18n_form_spec(),
        )
        for topic_name, topic in self.form_spec.elements.items():
            vue_value[topic_name] = {}
            actual_elements = self._resolve_topic_to_elements(topic)

            # Compute vue value
            topic_values = parsed_value.get(topic_name, {})

            element_lookup: dict[str, tuple[shared_type_defs.FormSpec, object]] = {}
            for element_name, element in actual_elements.items():
                element_visitor = get_visitor(element.parameter_form, self.options)
                is_active = element_name in topic_values
                spec, value = element_visitor.to_vue(
                    topic_values[element_name] if is_active else DEFAULT_VALUE
                )
                element_lookup[element_name] = (spec, value)
                if is_active or element.required:
                    vue_value[topic_name][element_name] = value

            # Compute vue spec, either a list of TopicElements or a list of TopicGroup
            vue_topic = shared_type_defs.Topic(
                name=topic_name, title=localize(topic.title), elements=[]
            )

            # tmp_group_element / tmp_element is required since mypy can differentiate
            # between list[TopicElement] and list[TopicGroup]
            if isinstance(topic.elements, list):
                tmp_group_elements: list[shared_type_defs.TopicGroup] = []
                for topic_group in topic.elements:
                    vue_topic_group = self._compute_topic_group_spec(topic_group, element_lookup)
                    tmp_group_elements.append(vue_topic_group)
                vue_topic.elements = tmp_group_elements
            else:
                tmp_elements: list[shared_type_defs.TopicElement] = []
                for element_name, element in topic.elements.items():
                    spec, value = element_lookup[element_name]
                    element_spec = self._compute_topic_element_spec(
                        element, element_name, spec, value
                    )
                    tmp_elements.append(element_spec)
                vue_topic.elements = tmp_elements

            vue_catalog.elements.append(vue_topic)

        return vue_catalog, vue_value

    def _validate(
        self, parsed_value: _ParsedValueModel
    ) -> list[shared_type_defs.ValidationMessage]:
        element_validations: list[shared_type_defs.ValidationMessage] = []
        for topic_name, topic in self.form_spec.elements.items():
            topic_values = parsed_value[topic_name]
            for element_name, element in self._resolve_topic_to_elements(topic).items():
                element_visitor = get_visitor(element.parameter_form, self.options)
                if element_name not in topic_values:
                    if element.required:
                        default_value_visitor = get_visitor(
                            element.parameter_form, VisitorOptions(DataOrigin.DISK)
                        )
                        _spec, element_default_value = default_value_visitor.to_vue(DEFAULT_VALUE)
                        return create_validation_error(
                            element_default_value,
                            f"Required element {element_name} missing in topic {topic_name}",
                            location=[topic_name, element_name],
                        )
                    continue

                for validation in element_visitor.validate(topic_values[element_name]):
                    element_validations.append(
                        shared_type_defs.ValidationMessage(
                            location=[topic_name, element_name] + validation.location,
                            message=validation.message,
                            replacement_value=validation.replacement_value,
                        )
                    )
        return element_validations

    def _to_disk(self, parsed_value: _ParsedValueModel) -> Mapping[str, dict[str, object]]:
        disk_values: dict[str, dict[str, object]] = {}
        for topic_name, topic in self.form_spec.elements.items():
            disk_values[topic_name] = {}
            topic_values = parsed_value[topic_name]
            for element_name, element in self._resolve_topic_to_elements(topic).items():
                if element_name in topic_values:
                    element_visitor = get_visitor(element.parameter_form, self.options)
                    disk_values[topic_name][element_name] = element_visitor.to_disk(
                        topic_values[element_name]
                    )
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

        topics = {}
        for topic_name, elements in topic_elements.items():
            topics[topic_name] = Topic(
                title=topic_title[topic_name],
                elements={
                    element_name: TopicElement(parameter_form=element.parameter_form, required=True)
                    for element_name, element in elements.items()
                },
            )

        return cls(catalog=Catalog(elements=topics))

    def convert_flat_to_catalog_config(
        self, flat_config: dict[str, object]
    ) -> Mapping[str, dict[str, object]]:
        topic_for_element: dict[str, str] = {}
        for topic_name, topic in self.catalog.elements.items():
            if isinstance(topic.elements, list):
                for topic_group in topic.elements:
                    for element_name, _element_value in topic_group.elements.items():
                        topic_for_element[element_name] = topic_name
            else:
                for element_name, _element_value in topic.elements.items():
                    topic_for_element[element_name] = topic_name

        catalog_config: dict[str, dict[str, object]] = {}
        for name, value in flat_config.items():
            if (target_topic := topic_for_element.get(name)) is None:
                raise MKGeneralException(
                    f"Cannot convert to catalog config. Key {name} has no topic"
                )
            catalog_config.setdefault(target_topic, {})[name] = value

        return catalog_config

    def convert_catalog_to_flat_config(
        self, config: dict[str, dict[str, object]]
    ) -> dict[str, object]:
        return {k: v for values in config.values() for k, v in values.items()}
