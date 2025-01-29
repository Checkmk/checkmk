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
from cmk.gui.form_specs.vue.form_spec_visitor import FormSpecValidationError
from cmk.gui.form_specs.vue.visitors import SingleChoiceVisitor
from cmk.gui.valuespec import Dictionary as ValueSpecDictionary
from cmk.gui.watolib.notification_parameter import (
    get_list_of_notification_parameter,
    get_notification_parameter,
    get_notification_parameter_schema,
    NotificationParameter,
    NotificationParameterRegistry,
    save_notification_parameter,
)
from cmk.gui.watolib.notification_parameter._utils import NotificationParameterDescription
from cmk.gui.watolib.notifications import NotificationParameterConfigFile

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.shared_typing import vue_formspec_components as shared_type_defs


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
                "select_param": DictElement(
                    parameter_form=SingleChoice(
                        elements=[
                            SingleChoiceElement(name="name1", title=Title("title1")),
                            SingleChoiceElement(name="name2", title=Title("title2")),
                        ]
                    ),
                    required=False,
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
            "general": {"description": "foo", "comment": "bar", "docu_url": "baz"},
            "parameter_properties": {"method_parameters": {"test_param": "bar"}},
        },
    )

    # THEN
    assert isinstance(save_return, NotificationParameterDescription)
    param = NotificationParameterConfigFile().load_for_reading()["dummy_params"][save_return.ident]
    assert param["general"]["description"] == "foo"
    # Ignore is needed because every plugin model has different keys (and not "test_param")
    assert param["parameter_properties"]["test_param"] == "bar"  # type: ignore[typeddict-item]


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
                "general": {"description": "foo", "comment": "bar", "docu_url": "baz"},
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
    with pytest.raises(FormSpecValidationError):
        save_notification_parameter(registry, "dummy_params", params)


@pytest.mark.usefixtures("request_context")
def test_get_notification_params_schema(registry: NotificationParameterRegistry) -> None:
    # WHEN
    schema, default_values = get_notification_parameter_schema(registry, "dummy_params")

    # THEN
    assert isinstance(default_values, dict)
    assert isinstance(default_values["parameter_properties"], dict)
    assert (
        default_values["parameter_properties"]["method_parameters"]["test_param"]
        == "some_default_value"
    )
    assert isinstance(schema, shared_type_defs.Catalog)
    assert schema.elements[0].name == "general"
    assert schema.elements[1].name == "parameter_properties"
    assert schema.elements[1].elements[0].parameter_form.elements[0].name == "test_param"  # type: ignore[union-attr]
    assert isinstance(
        schema.elements[1].elements[0].parameter_form.elements[0].parameter_form,  # type: ignore[union-attr]
        shared_type_defs.String,
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
def test_get_notification_parameter(registry: NotificationParameterRegistry) -> None:
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
    param = get_notification_parameter(registry, NotificationParameterID("some-id"))

    # THEN
    assert param.description == "foo"
    assert param.data["general"]["description"] == "foo"
    # Ignore is needed because every plugin model has different keys (and not "test_param")
    assert param.data["parameter_properties"]["method_parameters"]["test_param"] == "bar"


@pytest.mark.usefixtures("request_context")
def test_get_notification_parameter_throws_keyerror(
    registry: NotificationParameterRegistry,
) -> None:
    with pytest.raises(KeyError):
        get_notification_parameter(registry, NotificationParameterID("some-id"))


@pytest.mark.usefixtures("request_context")
def test_get_notification_parameter_doesnt_just_return_from_disk(
    registry: NotificationParameterRegistry,
) -> None:
    # GIVEN
    NotificationParameterConfigFile().save(
        {
            "dummy_params": {
                NotificationParameterID("some-id"): NotificationParameterItem(
                    general=NotificationParameterGeneralInfos(
                        description="foo", comment="", docu_url=""
                    ),
                    parameter_properties={
                        "test_param": "bar",
                        "select_param": "name1",
                    },
                )
            }
        }
    )

    # WHEN
    data = get_notification_parameter(registry, NotificationParameterID("some-id")).data

    # THEN
    # Ignore is needed because every plugin model has different keys (and not "select_param")
    assert data["parameter_properties"]["method_parameters"][
        "select_param"
    ] == SingleChoiceVisitor.option_id("name1")
