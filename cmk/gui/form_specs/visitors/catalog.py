#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any, override

from cmk.gui.form_specs.unstable import Catalog, Topic, TopicElement, TopicGroup
from cmk.gui.i18n import _
from cmk.shared_typing import vue_formspec_components as shared_type_defs

from ._base import FormSpecVisitor
from ._registry import get_visitor
from ._type_defs import (
    DEFAULT_VALUE,
    DefaultValue,
    IncomingData,
    InvalidValue,
    RawDiskData,
    RawFrontendData,
)
from ._utils import (
    create_validation_error,
    get_title_and_help,
    localize,
)

ModelTopic = str
ModelTopicElement = str
_ParsedValueModel = Mapping[ModelTopic, Mapping[ModelTopicElement, IncomingData]]
_FallbackModel = Mapping[ModelTopic, Mapping[ModelTopicElement, RawDiskData]]


class CatalogVisitor(FormSpecVisitor[Catalog, _ParsedValueModel, _FallbackModel]):
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
        self,
        raw_value: DefaultValue | dict[str, dict[str, object]],
        DataWrapper: type[RawDiskData | RawFrontendData],
    ) -> _ParsedValueModel:
        # The catalog can be treated as a dictionary of dictionaries
        # Because of this, the default value are resolved one level deeper
        tmp_value: dict[str, Any]
        if isinstance(raw_value, DefaultValue):
            tmp_value = {topic_name: DEFAULT_VALUE for topic_name in self.form_spec.elements.keys()}
        else:
            tmp_value = raw_value

        # Specific topics can be set to DefaultValue, too
        resolved_value: dict[str, dict[str, IncomingData]] = {}
        for topic_name, topic in self.form_spec.elements.items():
            topic_value = tmp_value.get(topic_name, DEFAULT_VALUE)
            if isinstance(topic_value, DefaultValue):
                resolved_value[topic_name] = {
                    element_name: DEFAULT_VALUE
                    for element_name, element in self._resolve_topic_to_elements(topic).items()
                    if element.required
                }
            else:
                resolved_value[topic_name] = {
                    str(k): v if isinstance(v, DefaultValue) else DataWrapper(v)
                    for k, v in topic_value.items()
                }

        return resolved_value

    @override
    def _parse_value(
        self, raw_value: IncomingData
    ) -> _ParsedValueModel | InvalidValue[_FallbackModel]:
        DataWrapper = RawFrontendData if isinstance(raw_value, RawFrontendData) else RawDiskData
        if isinstance(raw_value, DefaultValue):
            value = self._resolve_default_values(raw_value, DataWrapper=DataWrapper)
        elif not isinstance(raw_value.value, dict):
            return InvalidValue(reason=_("Invalid catalog data"), fallback_value={})
        else:
            value = self._resolve_default_values(raw_value.value, DataWrapper=DataWrapper)

        if not all(topic_name in value for topic_name in self.form_spec.elements.keys()):
            return InvalidValue(reason=_("Invalid catalog data"), fallback_value={})

        return value

    def _compute_topic_group_spec(
        self,
        topic_group: TopicGroup,
        element_lookup: dict[str, tuple[shared_type_defs.FormSpec, object]],
    ) -> shared_type_defs.TopicGroup:
        elements = []
        for element_name, element in topic_group.elements.items():
            spec, value = element_lookup[element_name]
            element_spec = self._compute_topic_element_spec(element, element_name, spec, value)
            elements.append(element_spec)
        return shared_type_defs.TopicGroup(
            title=localize(topic_group.title),
            elements=elements,
        )

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

    @override
    def _to_vue(
        self, parsed_value: _ParsedValueModel | InvalidValue[_FallbackModel]
    ) -> tuple[shared_type_defs.Catalog, object]:
        title, help_text = get_title_and_help(self.form_spec)
        if isinstance(parsed_value, InvalidValue):
            parsed_value = parsed_value.fallback_value

        catalog_elements = []
        vue_value: dict[str, dict[str, object]] = {}
        for topic_name, topic in self.form_spec.elements.items():
            vue_value[topic_name] = {}
            actual_elements = self._resolve_topic_to_elements(topic)

            # Compute vue value
            topic_values = parsed_value.get(topic_name, {})

            element_lookup: dict[str, tuple[shared_type_defs.FormSpec, object]] = {}
            for element_name, element in actual_elements.items():
                element_visitor = get_visitor(element.parameter_form, self.visitor_options)
                is_active = element_name in topic_values
                spec, value = element_visitor.to_vue(
                    topic_values[element_name] if is_active else DEFAULT_VALUE
                )
                element_lookup[element_name] = (spec, value)
                if is_active or element.required:
                    vue_value[topic_name][element_name] = value

            # Compute vue spec, either a list of TopicElements or a list of TopicGroup
            elements: list[shared_type_defs.TopicGroup] | list[shared_type_defs.TopicElement] = []

            # tmp_group_element / tmp_element is required since mypy can differentiate
            # between list[TopicElement] and list[TopicGroup]
            if isinstance(topic.elements, list):
                tmp_group_elements: list[shared_type_defs.TopicGroup] = []
                for topic_group in topic.elements:
                    vue_topic_group = self._compute_topic_group_spec(topic_group, element_lookup)
                    tmp_group_elements.append(vue_topic_group)
                elements = tmp_group_elements
            else:
                tmp_elements: list[shared_type_defs.TopicElement] = []
                for element_name, element in topic.elements.items():
                    spec, value = element_lookup[element_name]
                    element_spec = self._compute_topic_element_spec(
                        element, element_name, spec, value
                    )
                    tmp_elements.append(element_spec)
                elements = tmp_elements

            catalog_elements.append(
                shared_type_defs.Topic(
                    name=topic_name,
                    title=localize(topic.title),
                    elements=elements,
                    locked=(
                        None
                        if topic.locked is None
                        else shared_type_defs.Locked(message=topic.locked.message)
                    ),
                )
            )

        return (
            shared_type_defs.Catalog(
                title=title,
                help=help_text,
                elements=catalog_elements,
                validators=[],
            ),
            vue_value,
        )

    @override
    def _validate(
        self, parsed_value: _ParsedValueModel
    ) -> list[shared_type_defs.ValidationMessage]:
        element_validations: list[shared_type_defs.ValidationMessage] = []
        for topic_name, topic in self.form_spec.elements.items():
            topic_values = parsed_value[topic_name]
            for element_name, element in self._resolve_topic_to_elements(topic).items():
                element_visitor = get_visitor(element.parameter_form, self.visitor_options)
                if element_name not in topic_values:
                    if element.required:
                        _spec, element_default_value = element_visitor.to_vue(DEFAULT_VALUE)
                        return create_validation_error(
                            element_default_value,
                            f"Required element '{element_name}' missing in topic {topic_name}",
                            location=[topic_name, element_name],
                        )
                    continue

                for validation in element_visitor.validate(topic_values[element_name]):
                    element_validations.append(
                        shared_type_defs.ValidationMessage(
                            location=[topic_name, element_name] + list(validation.location),
                            message=validation.message,
                            replacement_value=validation.replacement_value,
                        )
                    )
        return element_validations

    @override
    def _to_disk(self, parsed_value: _ParsedValueModel) -> Mapping[str, dict[str, object]]:
        disk_values: dict[str, dict[str, object]] = {}
        for topic_name, topic in self.form_spec.elements.items():
            disk_values[topic_name] = {}
            topic_values = parsed_value[topic_name]
            for element_name, element in self._resolve_topic_to_elements(topic).items():
                if element_name in topic_values:
                    element_visitor = get_visitor(element.parameter_form, self.visitor_options)
                    disk_values[topic_name][element_name] = element_visitor.to_disk(
                        topic_values[element_name]
                    )
        return disk_values
