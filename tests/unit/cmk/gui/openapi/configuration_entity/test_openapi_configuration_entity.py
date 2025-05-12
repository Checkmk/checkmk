#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from unittest import mock

import pytest

from tests.testlib.unit.rest_api_client import ClientRegistry

import cmk.gui.watolib.configuration_entity.configuration_entity
from cmk.gui.form_specs.private import DictionaryExtended, not_empty
from cmk.gui.valuespec import Dictionary as ValueSpecDictionary
from cmk.gui.watolib.notification_parameter import (
    get_notification_parameter,
    NotificationParameter,
    NotificationParameterRegistry,
    save_notification_parameter,
)

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    String,
)
from cmk.shared_typing.configuration_entity import ConfigEntityType


def spec() -> ValueSpecDictionary:
    raise NotImplementedError()


def form_spec() -> DictionaryExtended:
    return DictionaryExtended(
        title=Title("Create notification with the following parameters"),
        elements={
            "test_param": DictElement(
                parameter_form=String(
                    custom_validate=[not_empty()], prefill=DefaultValue("some_default_value")
                ),
                required=True,
            ),
        },
    )


@pytest.fixture(name="registry", autouse=True)
def _registry_fixture(monkeypatch: pytest.MonkeyPatch) -> NotificationParameterRegistry:
    notification_parameter_registry = NotificationParameterRegistry()
    notification_parameter_registry.register(
        NotificationParameter(
            ident="dummy_params",
            spec=spec,
            form_spec=form_spec,
        )
    )
    monkeypatch.setattr(
        cmk.gui.watolib.configuration_entity.configuration_entity,
        "notification_parameter_registry",
        notification_parameter_registry,
    )
    return notification_parameter_registry


def test_save_configuration_entity(clients: ClientRegistry) -> None:
    # WHEN
    resp = clients.ConfigurationEntity.create_configuration_entity(
        {
            "entity_type": ConfigEntityType.notification_parameter.value,
            "entity_type_specifier": "dummy_params",
            "data": {
                "general": {"description": "foo", "comment": "bar", "docu_url": "baz"},
                "parameter_properties": {"method_parameters": {"test_param": "bar"}},
            },
        }
    )

    # THEN
    assert resp.json["title"] == "foo"


def test_update_configuration_entity(
    clients: ClientRegistry, registry: NotificationParameterRegistry
) -> None:
    # GIVEN
    entity = save_notification_parameter(
        registry,
        "dummy_params",
        {
            "general": {"description": "foo", "comment": "bar", "docu_url": "baz"},
            "parameter_properties": {"method_parameters": {"test_param": "initial_value"}},
        },
        object_id=None,
        pprint_value=False,
    )

    # WHEN
    clients.ConfigurationEntity.update_configuration_entity(
        {
            "entity_type": ConfigEntityType.notification_parameter.value,
            "entity_type_specifier": "dummy_params",
            "entity_id": entity.ident,
            "data": {
                "general": {"description": "foo", "comment": "bar", "docu_url": "baz"},
                "parameter_properties": {"method_parameters": {"test_param": "bar"}},
            },
        }
    )

    # THEN
    updated_entity = get_notification_parameter(registry, entity.ident).data
    # Ignore is needed because every plugin model has different keys (and not "test_param"
    assert updated_entity["parameter_properties"]["method_parameters"]["test_param"] == "bar"


@pytest.mark.parametrize(
    "data, expected_error_fields",
    [
        (
            {},
            {
                "general": {
                    "description": {"": [mock.ANY]},
                    "comment": {"": [mock.ANY]},
                    "docu_url": {"": [mock.ANY]},
                }
            },
        ),
        (
            {"general": {}, "parameter_properties": {}},
            {
                "general": {"description": {"": [mock.ANY]}},
            },
        ),
        (
            {
                "general": {"description": "foo", "comment": "bar", "docu_url": "baz"},
                "parameter_properties": {"method_parameters": {"test_param": {}}},
            },
            {"parameter_properties": {"method_parameters": {"test_param": {"": [mock.ANY]}}}},
        ),
    ],
)
def test_save_configuration_validation(
    clients: ClientRegistry, data: dict, expected_error_fields: dict
) -> None:
    # WHEN
    resp = clients.ConfigurationEntity.create_configuration_entity(
        {
            "entity_type": ConfigEntityType.notification_parameter.value,
            "entity_type_specifier": "dummy_params",
            "data": data,
        },
        expect_ok=False,
    )

    # THEN
    assert resp.json["ext"]["validation_errors"]
    assert resp.json["fields"]["data"] == expected_error_fields


def test_list_configuration_entities(
    clients: ClientRegistry, registry: NotificationParameterRegistry
) -> None:
    # GIVEN
    entity = save_notification_parameter(
        registry,
        "dummy_params",
        {
            "general": {"description": "foo", "comment": "bar", "docu_url": "baz"},
            "parameter_properties": {"method_parameters": {"test_param": "some_value"}},
        },
        object_id=None,
        pprint_value=False,
    )

    # WHEN
    resp = clients.ConfigurationEntity.list_configuration_entities(
        entity_type=ConfigEntityType.notification_parameter,
        entity_type_specifier="dummy_params",
    )

    # THEN
    assert len(resp.json["value"]) == 1
    assert resp.json["value"][0]["id"] == entity.ident
    assert resp.json["value"][0]["title"] == "foo"


def test_get_configuration_entity(
    clients: ClientRegistry, registry: NotificationParameterRegistry
) -> None:
    # GIVEN
    entity = save_notification_parameter(
        registry,
        "dummy_params",
        {
            "general": {"description": "foo", "comment": "bar", "docu_url": "baz"},
            "parameter_properties": {"method_parameters": {"test_param": "some_value"}},
        },
        object_id=None,
        pprint_value=False,
    )

    # WHEN
    resp = clients.ConfigurationEntity.get_configuration_entity(
        entity_type=ConfigEntityType.notification_parameter,
        entity_id=entity.ident,
    )

    # THEN
    assert resp.json["title"] == "foo"
    assert resp.json["extensions"]["general"]["description"] == "foo"
    assert (
        resp.json["extensions"]["parameter_properties"]["method_parameters"]["test_param"]
        == "some_value"
    )


def test_get_configuration_entity_throws_404(clients: ClientRegistry) -> None:
    # WHEN
    resp = clients.ConfigurationEntity.get_configuration_entity(
        entity_type=ConfigEntityType.notification_parameter, entity_id="foo_bar", expect_ok=False
    )

    # THEN
    assert resp.status_code == 404


def test_get_confguration_entity_fs_schema(clients: ClientRegistry) -> None:
    # WHEN
    resp = clients.ConfigurationEntity.get_configuration_entity_schema(
        entity_type=ConfigEntityType.notification_parameter,
        entity_type_specifier="dummy_params",
    )

    # THEN
    schema = resp.json["extensions"]["schema"]
    default_values = resp.json["extensions"]["default_values"]
    assert schema["type"] == "catalog"
    dictionary = schema["elements"][1]["elements"][0]["parameter_form"]
    assert dictionary["elements"][0]["parameter_form"]["type"] == "string"
    assert (
        default_values["parameter_properties"]["method_parameters"]["test_param"]
        == "some_default_value"
    )
