#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.aws_v2.constants import AWS_REGIONS
from cmk.plugins.aws_v2.rulesets.aws import (
    configuration_authentication,
    configuration_regions_and_tags,
    configuration_services,
)
from cmk.plugins.aws_v2.server_side_calls.agent_aws import (
    OrganizationAccounts,
    special_agent_aws_v2,
)
from cmk.plugins.aws_v2.special_agent.agent_aws_v2 import AWS_SERVICES
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    DictElement,
    Dictionary,
    List,
    MultipleChoice,
    String,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.server_side_calls.v1 import HostConfig, Secret


def _parameter_form[T](
    elements: Mapping[str, DictElement[object]], key: str, form_type: type[T]
) -> T:
    if not isinstance(form := elements[key].parameter_form, form_type):
        raise TypeError(form)
    return form


def _values_of(option: str, params: Mapping[str, object]) -> set[str | Secret]:
    (command,) = special_agent_aws_v2(
        {"auth": ("none", None), "piggyback_naming_convention": "ip_region_instance", **params},
        HostConfig(name="testhost"),
    )
    arguments: Sequence[str | Secret] = command.command_arguments
    return {value for name, value in zip(arguments, arguments[1:]) if name == option}


# fmt: off
@pytest.mark.parametrize(
    ("services_key", "option", "global_service"),
    [
        pytest.param("global_services", "--global-service", True, id="global services"),
        pytest.param("regional_services", "--service", False, id="regional services"),
    ],
)
# fmt: on
def test_rule_offers_exactly_the_services_of_the_agent(
    services_key: str, option: str, global_service: bool
) -> None:
    form = _parameter_form(configuration_services(), services_key, Dictionary)
    every_service: dict[str, object] = {
        name: ("all", {}) for name in (*form.elements, *form.ignored_elements)
    }

    passed_services = _values_of(option, {services_key: every_service})

    assert passed_services == {s.key for s in AWS_SERVICES if s.global_service is global_service}


def test_rule_offers_every_region_of_the_agent_by_its_aws_id() -> None:
    form = _parameter_form(configuration_regions_and_tags(), "regions", MultipleChoice)

    passed_regions = _values_of("--region", {"regions": [e.name for e in form.elements]})

    assert passed_regions == {region_id for region_id, _region_name in AWS_REGIONS}


def test_saved_ultimate_only_services_are_kept_without_the_extended_package() -> None:
    # This test target does not contain the aws_v2_extended package.
    global_form = _parameter_form(configuration_services(), "global_services", Dictionary)
    regional_form = _parameter_form(configuration_services(), "regional_services", Dictionary)

    assert set(global_form.ignored_elements) == {"route53", "cloudfront"}
    assert set(regional_form.ignored_elements) == {"aws_lambda", "sns", "ecs", "elasticache"}


def _login_forms() -> dict[str, object]:
    auth = _parameter_form(configuration_authentication(), "auth", CascadingSingleChoice)
    return {element.name: element.parameter_form for element in auth.elements}


def _account_choice_elements(choice: str) -> Mapping[str, DictElement[object]]:
    login = _login_forms()["none"]
    assert isinstance(login, Dictionary)
    accounts = _parameter_form(login.elements, "accounts", CascadingSingleChoice)
    (form,) = [e.parameter_form for e in accounts.elements if e.name == choice]
    assert isinstance(form, Dictionary)
    return form.elements


def _account_list_elements() -> Mapping[str, DictElement[object]]:
    return _account_choice_elements("list")


def test_only_logins_without_a_role_offer_an_account_list() -> None:
    offering = {
        name
        for name, form in _login_forms().items()
        if isinstance(form, Dictionary) and "accounts" in form.elements
    }

    assert offering == {"access_key", "none"}


@pytest.mark.parametrize("account_id", ["12345678901", "1234567890123", "12345678901a"])
def test_account_id_needs_exactly_twelve_digits(account_id: str) -> None:
    account_ids = _parameter_form(_account_list_elements(), "account_ids", List)
    assert isinstance(account_ids.element_template, String)

    with pytest.raises(ValidationError):
        for validate in account_ids.element_template.custom_validate or ():
            validate(account_id)


def test_role_name_with_a_path_is_rejected() -> None:
    role_name = _parameter_form(_account_list_elements(), "role_name", String)

    with pytest.raises(ValidationError):
        for validate in role_name.custom_validate or ():
            validate("monitoring/CheckmkMonitoring")


def test_account_ids_must_be_unique() -> None:
    account_ids = _parameter_form(_account_list_elements(), "account_ids", List)

    with pytest.raises(ValidationError):
        for validate in account_ids.custom_validate or ():
            validate(["333333333333", "333333333333"])


def test_organization_offers_every_option_of_the_server_side_call() -> None:
    elements = _account_choice_elements("organization")

    assert (set(elements), {key for key, element in elements.items() if element.required}) == (
        set(OrganizationAccounts.model_fields),
        {"role_name"},
    )


def test_excluded_account_id_needs_exactly_twelve_digits() -> None:
    excluded = _parameter_form(
        _account_choice_elements("organization"), "excluded_account_ids", List
    )
    assert isinstance(excluded.element_template, String)

    with pytest.raises(ValidationError):
        for validate in excluded.element_template.custom_validate or ():
            validate("12345678901")


def test_excluded_account_ids_must_be_unique() -> None:
    excluded = _parameter_form(
        _account_choice_elements("organization"), "excluded_account_ids", List
    )

    with pytest.raises(ValidationError):
        for validate in excluded.custom_validate or ():
            validate(["333333333333", "333333333333"])


@pytest.mark.parametrize(
    "arn",
    [
        pytest.param("CheckmkAccountList", id="role name only"),
        pytest.param("arn:aws:iam::888888888888:user/checkmk", id="user"),
        pytest.param("arn:aws:iam::88888888888:role/CheckmkAccountList", id="short account ID"),
    ],
)
def test_account_list_role_must_be_a_role_arn(arn: str) -> None:
    list_role = _parameter_form(
        _account_choice_elements("organization"), "account_list_role_arn", String
    )

    with pytest.raises(ValidationError):
        for validate in list_role.custom_validate or ():
            validate(arn)


def test_account_list_role_accepts_a_role_arn_with_a_path() -> None:
    list_role = _parameter_form(
        _account_choice_elements("organization"), "account_list_role_arn", String
    )

    for validate in list_role.custom_validate or ():
        validate("arn:aws-us-gov:iam::888888888888:role/monitoring/CheckmkAccountList")
