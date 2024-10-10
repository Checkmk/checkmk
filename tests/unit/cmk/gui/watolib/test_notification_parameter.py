#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.utils.notify_types import (
    NotificationParameterGeneralInfos,
    NotificationParameterID,
    NotificationParameterItem,
)

from cmk.gui.form_specs.private import DictionaryExtended, not_empty
from cmk.gui.form_specs.vue import shared_type_defs
from cmk.gui.valuespec import Dictionary as ValueSpecDictionary
from cmk.gui.wato._notification_parameter import NotificationParameter
from cmk.gui.wato._notification_parameter._registry import NotificationParameterRegistry
from cmk.gui.watolib.notification_parameter import (
    get_list_of_notification_parameter,
    get_notification_parameter,
    get_notification_parameter_schema,
    NotificationParameterDescription,
    save_notification_parameter,
)
from cmk.gui.watolib.notifications import NotificationParameterConfigFile

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, String


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


@pytest.fixture(name="registry")
def _registry() -> NotificationParameterRegistry:
    registry = NotificationParameterRegistry()
    registry.register(DummyNotificationParams)
    return registry


@pytest.mark.usefixtures("request_context")
def test_save_notification_params(registry: NotificationParameterRegistry) -> None:
    # WHEN
    save_return = save_notification_parameter(
        registry,
        "dummy_params",
        {
            "general": {"description": "foo"},
            "parameter_properties": {"test_param": "bar"},
        },
    )

    # THEN
    assert isinstance(save_return, NotificationParameterDescription)
    param = NotificationParameterConfigFile().load_for_reading()["dummy_params"][save_return.ident]
    assert param["general"]["description"] == "foo"
    assert param["parameter_properties"]["test_param"] == "bar"


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    "params",
    [
        pytest.param(
            {
                "general": {},
                "parameter_properties": {"test_param": "bar"},
            },
            id="no description",
        ),
        pytest.param(
            {
                "general": {"description": "foo"},
                "parameter_properties": {"test_param": ""},
            },
            id="empty value",
        ),
        pytest.param(
            {
                "parameter_properties": {"test_param": "bar"},
            },
            id="missing general section",
        ),
    ],
)
def test_validation_on_saving_notification_params(
    registry: NotificationParameterRegistry, params: dict
) -> None:
    # WHEN
    validation = save_notification_parameter(registry, "dummy_params", params)

    # THEN
    assert isinstance(validation, list)
    assert len(validation) > 0


@pytest.mark.usefixtures("request_context")
def test_get_notification_params_schema(registry: NotificationParameterRegistry) -> None:
    # WHEN
    schema, default_values = get_notification_parameter_schema(registry, "dummy_params")

    # THEN
    assert isinstance(default_values, dict)
    assert isinstance(default_values["parameter_properties"], dict)
    assert default_values["parameter_properties"]["test_param"] == "some_default_value"
    assert isinstance(schema, shared_type_defs.Catalog)
    assert schema.topics[0].ident == "general"
    assert schema.topics[1].ident == "parameter_properties"
    assert schema.topics[1].dictionary.elements[0].ident == "test_param"
    assert isinstance(
        schema.topics[1].dictionary.elements[0].parameter_form, shared_type_defs.String
    )


@pytest.mark.usefixtures("request_context")
def test_get_list_of_notification_parameter() -> None:
    # GIVEN
    NotificationParameterConfigFile().save(
        {
            "dummy_params": {
                NotificationParameterID("some-id"): NotificationParameterItem(
                    general=NotificationParameterGeneralInfos(
                        description="foo", comment="", docu_url=""
                    ),
                    parameter_properties={"test_param": "bar"},
                )
            }
        }
    )

    # WHEN
    params = get_list_of_notification_parameter("dummy_params")

    # THEN
    assert len(params) == 1
    assert params[0].ident == "some-id"
    assert params[0].description == "foo"


@pytest.mark.usefixtures("request_context")
def test_get_notification_parameter() -> None:
    # GIVEN
    NotificationParameterConfigFile().save(
        {
            "dummy_params": {
                NotificationParameterID("some-id"): NotificationParameterItem(
                    general=NotificationParameterGeneralInfos(
                        description="foo", comment="", docu_url=""
                    ),
                    parameter_properties={"test_param": "bar"},
                )
            }
        }
    )

    # WHEN
    param = get_notification_parameter(NotificationParameterID("some-id"))

    # THEN
    assert param["general"]["description"] == "foo"
    assert param["parameter_properties"]["test_param"] == "bar"
