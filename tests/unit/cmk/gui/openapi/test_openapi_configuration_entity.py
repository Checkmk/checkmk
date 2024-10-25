#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from tests.testlib.rest_api_client import ClientRegistry

import cmk.gui.watolib.configuration_entity.configuration_entity
from cmk.gui.form_specs.private import DictionaryExtended, not_empty
from cmk.gui.valuespec import Dictionary as ValueSpecDictionary
from cmk.gui.wato import NotificationParameter
from cmk.gui.wato._notification_parameter._registry import NotificationParameterRegistry
from cmk.gui.watolib.configuration_entity.type_defs import ConfigEntityType
from cmk.gui.watolib.notification_parameter import (
    get_notification_parameter,
    NotificationParameterDescription,
    save_notification_parameter,
)

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    String,
)


class DummyNotificationParams(NotificationParameter):
    @property
    def ident(self) -> str:
        return "dummy_params"

    @property
    def spec(self) -> ValueSpecDictionary:
        raise NotImplementedError()

    def _form_spec(self) -> DictionaryExtended:
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
    notification_parameter_registry.register(DummyNotificationParams)
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
                "general": {"description": "foo"},
                "parameter_properties": {"test_param": "bar"},
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
            "general": {"description": "foo"},
            "parameter_properties": {"test_param": "initial_value"},
        },
        None,
    )
    assert isinstance(entity, NotificationParameterDescription), "type guard"

    # WHEN
    clients.ConfigurationEntity.update_configuration_entity(
        {
            "entity_type": ConfigEntityType.notification_parameter.value,
            "entity_type_specifier": "dummy_params",
            "entity_id": entity.ident,
            "data": {
                "general": {"description": "foo"},
                "parameter_properties": {"test_param": "bar"},
            },
        }
    )

    # THEN
    updated_entity = get_notification_parameter(registry, entity.ident)
    assert updated_entity["parameter_properties"]["test_param"] == "bar"


@pytest.mark.parametrize(
    "data, num_expected_error_fields",
    [
        ({}, {"general": 1, "parameter_properties": 1}),
        (
            {"general": {}, "parameter_properties": {}},
            {"general": {"description": 1}, "parameter_properties": 1},
        ),
        (
            {"general": {"description": "foo"}, "parameter_properties": {"test_param": {}}},
            {"parameter_properties": {"test_param": 1}},
        ),
    ],
)
def test_save_configuration_validation(
    clients: ClientRegistry, data: dict, num_expected_error_fields: dict
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

    def error_fields_present(error_fields: dict, _num_expected_error_fields: dict | int) -> bool:
        if isinstance(_num_expected_error_fields, int):
            return len(error_fields) == _num_expected_error_fields

        for key in _num_expected_error_fields.keys():
            if key not in error_fields:
                return False
            return error_fields_present(error_fields[key], _num_expected_error_fields[key])

        return True

    # THEN
    assert resp.json["ext"]["validation_errors"]
    assert error_fields_present(resp.json["fields"]["data"], num_expected_error_fields)


def test_list_configuration_entities(
    clients: ClientRegistry, registry: NotificationParameterRegistry
) -> None:
    # GIVEN
    entity = save_notification_parameter(
        registry,
        "dummy_params",
        {"general": {"description": "foo"}, "parameter_properties": {"test_param": "some_value"}},
        None,
    )
    assert isinstance(entity, NotificationParameterDescription), "type guard"

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
        {"general": {"description": "foo"}, "parameter_properties": {"test_param": "some_value"}},
        None,
    )
    assert isinstance(entity, NotificationParameterDescription), "type guard"

    # WHEN
    resp = clients.ConfigurationEntity.get_configuration_entity(
        entity_type=ConfigEntityType.notification_parameter,
        entity_id=entity.ident,
    )

    # THEN
    assert resp.json["extensions"]["general"]["description"] == "foo"
    assert resp.json["extensions"]["parameter_properties"]["test_param"] == "some_value"


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
    assert schema["topics"][1]["dictionary"]["elements"][0]["parameter_form"]["type"] == "string"
    assert default_values["parameter_properties"]["test_param"] == "some_default_value"
