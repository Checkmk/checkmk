#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Self

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.form_specs.converter import TransformDataForLegacyFormatOrRecomposeFunction
from cmk.gui.form_specs.private import Catalog, Topic, TopicElement
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DictElement, Dictionary

Headers = Sequence[tuple[str, Sequence[str]] | tuple[str, str, Sequence[str]]]


@dataclass(frozen=True, kw_only=True)
class Dict2CatalogConverter:
    catalog: Catalog

    @classmethod
    def build_from_dictionary(cls, dictionary: Dictionary, headers: Headers | None = None) -> Self:
        use_headers: list[tuple[Title, Sequence[str]]] = []
        if headers is None:
            use_headers = [
                (dictionary.title or Title("Properties"), list(dictionary.elements.keys()))
            ]
        else:
            # Dropping css from header specification, we will see how this turns out
            for header in headers:
                if isinstance(header, tuple):
                    if len(header) == 2:
                        use_headers.append((Title(header[0]), list(header[1])))  # pylint: disable=localization-of-non-literal-string
                    elif len(header) == 3:
                        use_headers.append((Title(header[0]), list(header[2])))  # pylint: disable=localization-of-non-literal-string
                raise MKGeneralException(f"Invalid header type for catalog {headers}")

        return cls._build_from_formspec_dictionary(dictionary, use_headers)

    @classmethod
    def _build_from_formspec_dictionary(
        cls, dictionary: Dictionary, headers: Sequence[tuple[Title, Sequence[str]]]
    ) -> Self:
        topic_elements: dict[str, dict[str, DictElement[Any]]] = {}
        topic_title: dict[str, Title] = {}
        element_to_topic: dict[str, str] = {}
        # Prepare topics assignments
        for idx, header in enumerate(headers):
            title, elements_in_topic = header
            topic_name = f"topic{idx}"
            topic_elements[topic_name] = {}
            topic_title[topic_name] = title
            for topic_element in elements_in_topic:
                element_to_topic[topic_element] = topic_name

        # Split elements into topics
        for dict_name, dict_value in dictionary.elements.items():
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
        self, flat_config: object
    ) -> Mapping[str, dict[str, object]]:
        assert isinstance(flat_config, dict)
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

    def convert_catalog_to_flat_config(self, config: object) -> dict[str, Any]:
        assert isinstance(config, dict)
        return {k: v for values in config.values() for k, v in values.items()}


def create_flat_catalog_from_dictionary(
    dictionary: Dictionary, headers: Headers | None = None
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    # Allows to render a dictionary as a flat catalog (topic keys have no meaning for data model)
    converter = Dict2CatalogConverter.build_from_dictionary(dictionary, headers)

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=converter.catalog,
        to_disk=converter.convert_catalog_to_flat_config,
        from_disk=converter.convert_flat_to_catalog_config,
    )
