#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from functools import partial
from typing import assert_never, TypeVar

import pytest

from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.version import Edition

import cmk.gui.graphing._valuespecs as legacy_graphing_valuespecs
import cmk.gui.valuespec as legacy_valuespecs
from cmk.gui import inventory as legacy_inventory_groups
from cmk.gui import wato as legacy_wato
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.mkeventd import wato as legacy_mkeventd_groups
from cmk.gui.utils.autocompleter_config import ContextAutocompleterConfig
from cmk.gui.utils.rule_specs.legacy_converter import (
    _convert_to_custom_group,
    _convert_to_legacy_levels,
    _convert_to_legacy_rulespec_group,
    _convert_to_legacy_valuespec,
    _to_generated_builtin_sub_group,
    convert_to_legacy_rulespec,
)
from cmk.gui.utils.rule_specs.loader import RuleSpec as APIV1RuleSpec
from cmk.gui.wato import _check_mk_configuration as legacy_cmk_config_groups
from cmk.gui.wato import _rulespec_groups as legacy_wato_groups
from cmk.gui.watolib import rulespec_groups as legacy_rulespec_groups
from cmk.gui.watolib import rulespecs as legacy_rulespecs

import cmk.rulesets.v1 as api_v1


def _v1_custom_text_validate(value: str) -> None:
    api_v1.validators.DisallowEmpty(error_msg=api_v1.Localizable("Fill this"))(value)
    api_v1.validators.MatchRegex(
        regex=r"^[^.\r\n]+$", error_msg=api_v1.Localizable("No dot allowed")
    )(value)

    if value == "admin":
        raise api_v1.validators.ValidationError(api_v1.Localizable("Forbidden"))


def _legacy_custom_text_validate(value: str, varprefix: str) -> None:
    if value == "admin":
        raise MKUserError(varprefix, _("Forbidden"))


@pytest.mark.parametrize(
    ["new_valuespec", "expected"],
    [
        pytest.param(
            api_v1.form_specs.HostState(),
            legacy_valuespecs.DropdownChoice(
                choices=[
                    (0, _("Up")),
                    (1, _("Down")),
                    (2, _("Unreachable")),
                ],
                sorted=False,
                default_value=0,
            ),
            id="minimal HostState",
        ),
        pytest.param(
            api_v1.form_specs.HostState(
                title=api_v1.Localizable("title"),
                help_text=api_v1.Localizable("help text"),
                prefill_value=1,
            ),
            legacy_valuespecs.DropdownChoice(
                choices=[
                    (0, _("Up")),
                    (1, _("Down")),
                    (2, _("Unreachable")),
                ],
                sorted=False,
                title=_("title"),
                help=_("help text"),
                default_value=1,
            ),
            id="MonitoringState",
        ),
        pytest.param(
            api_v1.form_specs.ServiceState(),
            legacy_valuespecs.MonitoringState(),
            id="minimal MonitoringState",
        ),
        pytest.param(
            api_v1.form_specs.ServiceState(
                title=api_v1.Localizable("title"),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_valuespecs.MonitoringState(
                title=_("title"),
                help=_("help text"),
                default_value=0,
            ),
            id="MonitoringState",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(elements={}),
            legacy_valuespecs.Dictionary(elements=[]),
            id="minimal Dictionary",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "key_req": api_v1.form_specs.DictElement(
                        api_v1.form_specs.ServiceState(title=api_v1.Localizable("title")),
                        required=True,
                    ),
                    "key_read_only": api_v1.form_specs.DictElement(
                        api_v1.form_specs.ServiceState(title=api_v1.Localizable("title")),
                        read_only=True,
                    ),
                },
                title=api_v1.Localizable("Configuration title"),
                help_text=api_v1.Localizable("Helpful description"),
                deprecated_elements=("old_key", "another_old_key"),
                no_elements_text=api_v1.Localizable("No elements specified"),
            ),
            legacy_valuespecs.Dictionary(
                elements=[
                    ("key_req", legacy_valuespecs.MonitoringState(title=_("title"))),
                    ("key_read_only", legacy_valuespecs.MonitoringState(title=_("title"))),
                ],
                title=_("Configuration title"),
                help=_("Helpful description"),
                empty_text=_("No elements specified"),
                required_keys=["key_req"],
                show_more_keys=[],
                hidden_keys=["key_read_only"],
                ignored_keys=["old_key", "another_old_key"],
            ),
            id="Dictionary",
        ),
        pytest.param(
            api_v1.form_specs.Integer(),
            legacy_valuespecs.Integer(),
            id="minimal Integer",
        ),
        pytest.param(
            api_v1.form_specs.Integer(
                title=api_v1.Localizable("title"),
                help_text=api_v1.Localizable("help"),
                label=api_v1.Localizable("label"),
                unit=api_v1.Localizable("days"),
                prefill_value=-1,
                custom_validate=lambda x: None,
            ),
            legacy_valuespecs.Integer(
                title=_("title"),
                help=_("help"),
                label=_("label"),
                unit=_("days"),
                default_value=-1,
                validate=lambda x, y: None,
            ),
            id="Integer",
        ),
        pytest.param(
            api_v1.form_specs.Float(),
            legacy_valuespecs.Float(),
            id="minimal Float",
        ),
        pytest.param(
            api_v1.form_specs.Float(
                title=api_v1.Localizable("title"),
                help_text=api_v1.Localizable("help"),
                label=api_v1.Localizable("label"),
                unit=api_v1.Localizable("1/s"),
                display_precision=2,
                prefill_value=-1.0,
                custom_validate=lambda x: None,
            ),
            legacy_valuespecs.Float(
                title=_("title"),
                help=_("help"),
                label=_("label"),
                display_format="%.2f",
                unit=_("1/s"),
                default_value=-1.0,
                validate=lambda x, y: None,
            ),
            id="Float",
        ),
        pytest.param(
            api_v1.form_specs.DataSize(),
            legacy_valuespecs.Filesize(),
            id="minimal DataSize",
        ),
        pytest.param(
            api_v1.form_specs.DataSize(
                title=api_v1.Localizable("title"),
                help_text=api_v1.Localizable("help"),
                label=api_v1.Localizable("label"),
                prefill_value=-1,
                custom_validate=lambda x: None,
            ),
            legacy_valuespecs.Filesize(
                title=_("title"),
                help=_("help"),
                label=_("label"),
                default_value=-1,
                validate=lambda x, y: None,
            ),
            id="DataSize",
        ),
        pytest.param(
            api_v1.form_specs.Percentage(),
            legacy_valuespecs.Percentage(),
            id="minimal Percentage",
        ),
        pytest.param(
            api_v1.form_specs.Percentage(
                title=api_v1.Localizable("title"),
                help_text=api_v1.Localizable("help"),
                label=api_v1.Localizable("label"),
                display_precision=2,
                prefill_value=-1.0,
                custom_validate=lambda x: None,
            ),
            legacy_valuespecs.Percentage(
                title=_("title"),
                help=_("help"),
                label=_("label"),
                display_format="%.2f",
                default_value=-1.0,
                validate=lambda x, y: None,
            ),
            id="Percentage",
        ),
        pytest.param(
            api_v1.form_specs.TextInput(),
            legacy_valuespecs.TextInput(),
            id="minimal TextInput",
        ),
        pytest.param(
            api_v1.form_specs.TextInput(
                title=api_v1.Localizable("spec title"),
                label=api_v1.Localizable("spec label"),
                input_hint="firstname",
                help_text=api_v1.Localizable("help text"),
                prefill_value="myname",
                custom_validate=_v1_custom_text_validate,
            ),
            legacy_valuespecs.TextInput(
                title=_("spec title"),
                label=_("spec label"),
                placeholder="firstname",
                help=_("help text"),
                default_value="myname",
                validate=_legacy_custom_text_validate,
            ),
            id="TextInput",
        ),
        pytest.param(
            api_v1.form_specs.Tuple(elements=[]),
            legacy_valuespecs.Tuple(elements=[]),
            id="minimal Tuple",
        ),
        pytest.param(
            api_v1.form_specs.Tuple(
                elements=[
                    api_v1.form_specs.TextInput(title=api_v1.Localizable("child title 1")),
                    api_v1.form_specs.TextInput(title=api_v1.Localizable("child title 2")),
                ],
                title=api_v1.Localizable("parent title"),
                help_text=api_v1.Localizable("parent help"),
            ),
            legacy_valuespecs.Tuple(
                elements=[
                    legacy_valuespecs.TextInput(title=_("child title 1")),
                    legacy_valuespecs.TextInput(title=_("child title 2")),
                ],
                title=_("parent title"),
                help=_("parent help"),
            ),
            id="Tuple",
        ),
        pytest.param(
            api_v1.form_specs.DropdownChoice(elements=[]),
            legacy_valuespecs.DropdownChoice(choices=[], invalid_choice="complain"),
            id="minimal DropdownChoice",
        ),
        pytest.param(
            api_v1.form_specs.DropdownChoice(
                elements=[
                    api_v1.form_specs.DropdownChoiceElement(
                        name="true", title=api_v1.Localizable("Enabled")
                    ),
                    api_v1.form_specs.DropdownChoiceElement(
                        name="false", title=api_v1.Localizable("Disabled")
                    ),
                ],
                no_elements_text=api_v1.Localizable("No elements"),
                deprecated_elements=(),
                frozen=True,
                title=api_v1.Localizable("title"),
                label=api_v1.Localizable("label"),
                help_text=api_v1.Localizable("help text"),
                prefill_selection="true",
                invalid_element_validation=api_v1.form_specs.InvalidElementValidator(
                    mode=api_v1.form_specs.InvalidElementMode.KEEP,
                    display=api_v1.Localizable("invalid choice title"),
                    error_msg=api_v1.Localizable("invalid choice msg"),
                ),
            ),
            legacy_valuespecs.DropdownChoice(
                choices=[("true", _("Enabled")), ("false", _("Disabled"))],
                empty_text=_("No elements"),
                deprecated_choices=[],
                read_only=True,
                title=_("title"),
                label=_("label"),
                help=_("help text"),
                default_value="true",
                invalid_choice=None,
                invalid_choice_title=_("invalid choice title"),
                invalid_choice_error=_("invalid choice msg"),
            ),
            id="DropdownChoice",
        ),
        pytest.param(
            api_v1.form_specs.CascadingDropdown(elements=[], prefill_selection=None),
            legacy_valuespecs.CascadingDropdown(choices=[], no_preselect_title=""),
            id="minimal CascadingDropdown",
        ),
        pytest.param(
            api_v1.form_specs.CascadingDropdown(
                elements=[
                    api_v1.form_specs.CascadingDropdownElement(
                        name="first",
                        title=api_v1.Localizable("Spec title"),
                        parameter_form=api_v1.form_specs.TextInput(),
                    )
                ],
                prefill_selection=None,
            ),
            legacy_valuespecs.CascadingDropdown(
                choices=[("first", "first", legacy_valuespecs.TextInput())],
                no_preselect_title="",
            ),
            id="CascadingDropdown no valuespec title",
        ),
        pytest.param(
            api_v1.form_specs.CascadingDropdown(
                elements=[
                    api_v1.form_specs.CascadingDropdownElement(
                        name="first",
                        title=api_v1.Localizable("Spec title"),
                        parameter_form=api_v1.form_specs.TextInput(
                            title=api_v1.Localizable("Spec title")
                        ),
                    )
                ],
                prefill_selection=None,
            ),
            legacy_valuespecs.CascadingDropdown(
                choices=[
                    ("first", _("Spec title"), legacy_valuespecs.TextInput(title=_("Spec title")))
                ],
                no_preselect_title="",
            ),
            id="CascadingDropdown valuespec title",
        ),
        pytest.param(
            api_v1.form_specs.CascadingDropdown(
                elements=[
                    api_v1.form_specs.CascadingDropdownElement(
                        name="first",
                        title=api_v1.Localizable("Spec title"),
                        parameter_form=api_v1.form_specs.TextInput(),
                    )
                ],
                title=api_v1.Localizable("parent title"),
                help_text=api_v1.Localizable("parent help"),
                label=api_v1.Localizable("parent label"),
                prefill_selection="first",
            ),
            legacy_valuespecs.CascadingDropdown(
                choices=[("first", _("first"), legacy_valuespecs.TextInput())],
                title=_("parent title"),
                help=_("parent help"),
                label=_("parent label"),
                default_value="first",
            ),
            id="CascadingDropdown",
        ),
        pytest.param(
            api_v1.form_specs.List(parameter_form=api_v1.form_specs.Tuple(elements=[])),
            legacy_valuespecs.ListOf(valuespec=legacy_valuespecs.Tuple(elements=[])),
            id="minimal ListOf",
        ),
        pytest.param(
            api_v1.form_specs.List(
                parameter_form=api_v1.form_specs.Tuple(
                    elements=[
                        api_v1.form_specs.TextInput(),
                        api_v1.form_specs.Integer(unit=api_v1.Localizable("km")),
                    ]
                ),
                title=api_v1.Localizable("list title"),
                help_text=api_v1.Localizable("list help"),
                prefill_value=[("first", 1), ("second", 2), ("third", 3)],
                order_editable=False,
            ),
            legacy_valuespecs.ListOf(
                valuespec=legacy_valuespecs.Tuple(
                    elements=[legacy_valuespecs.TextInput(), legacy_valuespecs.Integer(unit="km")]
                ),
                title="list title",
                help="list help",
                default_value=[("first", 1), ("second", 2), ("third", 3)],
                add_label="Add new element",
                del_label="Delete this entry",
                movable=False,
                text_if_empty="No entries",
            ),
            id="ListOf",
        ),
        pytest.param(
            api_v1.form_specs.FixedValue(value=True),
            legacy_valuespecs.FixedValue(value=True, totext=""),
            id="minimal FixedValue",
        ),
        pytest.param(
            api_v1.form_specs.FixedValue(
                value="enabled",
                title=api_v1.Localizable("Enable the option"),
                label=api_v1.Localizable("The option is enabled"),
                help_text=api_v1.Localizable("Help text"),
            ),
            legacy_valuespecs.FixedValue(
                value="enabled",
                title=_("Enable the option"),
                totext=_("The option is enabled"),
                help=_("Help text"),
            ),
            id="FixedValue",
        ),
        pytest.param(
            api_v1.form_specs.TimeSpan(),
            legacy_valuespecs.Age(),
            id="minimal Age",
        ),
        pytest.param(
            api_v1.form_specs.TimeSpan(
                title=api_v1.Localizable("age title"),
                label=api_v1.Localizable("age label"),
                help_text=api_v1.Localizable("help text"),
                displayed_units=[
                    api_v1.form_specs.DisplayUnits.DAYS,
                    api_v1.form_specs.DisplayUnits.HOURS,
                    api_v1.form_specs.DisplayUnits.MINUTES,
                    api_v1.form_specs.DisplayUnits.SECONDS,
                ],
                prefill_value=100,
            ),
            legacy_valuespecs.Age(
                title=_("age title"),
                label=_("age label"),
                help=_("help text"),
                display=["days", "hours", "minutes", "seconds"],
                default_value=100,
            ),
            id="Age",
        ),
        pytest.param(
            api_v1.preconfigured.Proxy(),
            legacy_valuespecs.CascadingDropdown(
                title=_("HTTP proxy"),
                default_value=("environment", "environment"),
                choices=[
                    (
                        "environment",
                        _("Use from environment"),
                        legacy_valuespecs.FixedValue(
                            value="environment",
                            help=_(
                                "Use the proxy settings from the environment variables. The variables <tt>NO_PROXY</tt>, "
                                "<tt>HTTP_PROXY</tt> and <tt>HTTPS_PROXY</tt> are taken into account during execution. "
                                "Have a look at the python requests module documentation for further information. Note "
                                "that these variables must be defined as a site-user in ~/etc/environment and that "
                                "this might affect other notification methods which also use the requests module."
                            ),
                            totext=_(
                                "Use proxy settings from the process environment. This is the default."
                            ),
                        ),
                    ),
                    (
                        "no_proxy",
                        _("Connect without proxy"),
                        legacy_valuespecs.FixedValue(
                            value=None,
                            totext=_(
                                "Connect directly to the destination instead of using a proxy."
                            ),
                        ),
                    ),
                    (
                        "global",
                        _("Use globally configured proxy"),
                        legacy_valuespecs.DropdownChoice(
                            choices=lambda: [],
                            sorted=True,
                        ),
                    ),
                    (
                        "url",
                        _("Use explicit proxy settings"),
                        legacy_valuespecs.Url(
                            title=_("Proxy URL"),
                            default_scheme="http",
                            allowed_schemes=frozenset(
                                {"http", "https", "socks4", "socks4a", "socks5", "socks5h"}
                            ),
                        ),
                    ),
                ],
                sorted=False,
            ),
            id="minimal HTTPProxy",
        ),
        pytest.param(
            api_v1.preconfigured.Proxy(
                allowed_schemas=frozenset(
                    {api_v1.preconfigured.ProxySchema.HTTP, api_v1.preconfigured.ProxySchema.HTTPS}
                ),
                title=api_v1.Localizable("age title"),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_valuespecs.CascadingDropdown(
                title=_("HTTP proxy"),
                default_value=("environment", "environment"),
                choices=[
                    (
                        "environment",
                        _("Use from environment"),
                        legacy_valuespecs.FixedValue(
                            value="environment",
                            help=_(
                                "Use the proxy settings from the environment variables. The variables <tt>NO_PROXY</tt>, "
                                "<tt>HTTP_PROXY</tt> and <tt>HTTPS_PROXY</tt> are taken into account during execution. "
                                "Have a look at the python requests module documentation for further information. Note "
                                "that these variables must be defined as a site-user in ~/etc/environment and that "
                                "this might affect other notification methods which also use the requests module."
                            ),
                            totext=_(
                                "Use proxy settings from the process environment. This is the default."
                            ),
                        ),
                    ),
                    (
                        "no_proxy",
                        _("Connect without proxy"),
                        legacy_valuespecs.FixedValue(
                            value=None,
                            totext=_(
                                "Connect directly to the destination instead of using a proxy."
                            ),
                        ),
                    ),
                    (
                        "global",
                        _("Use globally configured proxy"),
                        legacy_valuespecs.DropdownChoice(
                            choices=lambda: [],
                            sorted=True,
                        ),
                    ),
                    (
                        "url",
                        _("Use explicit proxy settings"),
                        legacy_valuespecs.Url(
                            title=_("Proxy URL"),
                            default_scheme="http",
                            allowed_schemes=frozenset({"http", "https"}),
                        ),
                    ),
                ],
                sorted=False,
            ),
            id="HTTPProxy",
        ),
        pytest.param(
            api_v1.form_specs.BooleanChoice(),
            legacy_valuespecs.Checkbox(),
            id="minimal BooleanChoice",
        ),
        pytest.param(
            api_v1.form_specs.BooleanChoice(
                title=api_v1.Localizable("boolean choice title"),
                label=api_v1.Localizable("boolean choice label"),
                help_text=api_v1.Localizable("help text"),
                prefill_value=True,
            ),
            legacy_valuespecs.Checkbox(
                title=_("boolean choice title"),
                label=_("boolean choice label"),
                help=_("help text"),
                default_value=True,
            ),
            id="BooleanChoice",
        ),
        pytest.param(
            api_v1.form_specs.FileUpload(),
            legacy_valuespecs.FileUpload(allow_empty=True),
            id="minimal FileUpload",
        ),
        pytest.param(
            api_v1.form_specs.FileUpload(
                title=api_v1.Localizable("my title"),
                help_text=api_v1.Localizable("help text"),
                extensions=("txt", "rst"),
                mime_types=("text/plain",),
            ),
            legacy_valuespecs.FileUpload(
                title=_("my title"),
                help=_("help text"),
                allowed_extensions=("txt", "rst"),
                mime_types=("text/plain",),
                allow_empty=True,
            ),
            id="FileUpload",
        ),
        pytest.param(
            api_v1.preconfigured.Metric(),
            legacy_graphing_valuespecs.MetricName(
                title=_("Metric"),
                help=_("Select from a list of metrics known to Checkmk"),
            ),
            id="minimal Metric",
        ),
        pytest.param(
            api_v1.preconfigured.Metric(
                title=api_v1.Localizable("metric title"),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_graphing_valuespecs.MetricName(
                title=_("metric title"),
                help=_("help text"),
            ),
            id="Metric",
        ),
        pytest.param(
            api_v1.preconfigured.MonitoredHost(),
            legacy_valuespecs.MonitoredHostname(
                title=_("Host name"),
                help=_("Select from a list of host names known to Checkmk"),
                autocompleter=ContextAutocompleterConfig(
                    ident=legacy_valuespecs.MonitoredHostname.ident,
                    strict=True,
                    show_independent_of_context=True,
                ),
            ),
            id="minimal MonitoredHost",
        ),
        pytest.param(
            api_v1.preconfigured.MonitoredHost(
                title=api_v1.Localizable("host title"),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_valuespecs.MonitoredHostname(
                title=_("host title"),
                help=_("help text"),
                autocompleter=ContextAutocompleterConfig(
                    ident=legacy_valuespecs.MonitoredHostname.ident,
                    strict=True,
                    show_independent_of_context=True,
                ),
            ),
            id="MonitoredHost",
        ),
    ],
)
def test_convert_to_legacy_valuespec(
    new_valuespec: api_v1.form_specs.FormSpec, expected: legacy_valuespecs.ValueSpec
) -> None:
    _compare_specs(_convert_to_legacy_valuespec(new_valuespec, _), expected)


@pytest.mark.parametrize(
    ["legacy_main_group", "new_topic", "expected"],
    [
        pytest.param(
            legacy_rulespec_groups.RulespecGroupMonitoringConfiguration,
            api_v1.rule_specs.Topic.APPLICATIONS,
            legacy_wato_groups.RulespecGroupCheckParametersApplications,
            id="CheckParametersApplications",
        ),
    ],
)
def test_convert_to_legacy_rulespec_group(
    legacy_main_group: type[legacy_rulespecs.RulespecGroup],
    new_topic: api_v1.rule_specs.Topic,
    expected: type[legacy_rulespecs.RulespecSubGroup],
) -> None:
    assert _convert_to_legacy_rulespec_group(legacy_main_group, new_topic, _) == expected


@pytest.mark.parametrize(
    ["new_rulespec", "expected"],
    [
        pytest.param(
            api_v1.rule_specs.CheckParameterWithItem(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                item_form=api_v1.form_specs.TextInput(title=api_v1.Localizable("item title")),
                parameter_form=partial(
                    api_v1.form_specs.Dictionary,
                    elements={
                        "key": api_v1.form_specs.DictElement(
                            api_v1.form_specs.ServiceState(
                                title=api_v1.Localizable("valuespec title")
                            )
                        ),
                    },
                ),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.CheckParameterRulespecWithItem(
                check_group_name="test_rulespec",
                group=legacy_wato_groups.RulespecGroupCheckParametersApplications,
                title=lambda: _("rulespec title"),
                item_spec=lambda: legacy_valuespecs.TextInput(title=_("item title")),
                parameter_valuespec=lambda: legacy_valuespecs.Dictionary(
                    elements=[
                        ("key", legacy_valuespecs.MonitoringState(title=_("valuespec title")))
                    ],
                ),
                match_type="dict",
                create_manual_check=False,
            ),
            id="CheckParameterRuleSpecWithItem",
        ),
        pytest.param(
            api_v1.rule_specs.CheckParameterWithoutItem(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                parameter_form=partial(
                    api_v1.form_specs.Dictionary,
                    elements={
                        "key": api_v1.form_specs.DictElement(
                            api_v1.form_specs.ServiceState(
                                title=api_v1.Localizable("valuespec title")
                            )
                        ),
                    },
                ),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.CheckParameterRulespecWithoutItem(
                check_group_name="test_rulespec",
                group=legacy_wato_groups.RulespecGroupCheckParametersApplications,
                title=lambda: _("rulespec title"),
                parameter_valuespec=lambda: legacy_valuespecs.Dictionary(
                    elements=[
                        ("key", legacy_valuespecs.MonitoringState(title=_("valuespec title")))
                    ],
                ),
                match_type="dict",
                create_manual_check=False,
            ),
            id="CheckParameterRuleSpecWithoutItem",
        ),
        pytest.param(
            api_v1.rule_specs.EnforcedServiceWithItem(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                item_form=api_v1.form_specs.TextInput(title=api_v1.Localizable("item title")),
                parameter_form=partial(
                    api_v1.form_specs.Dictionary,
                    elements={
                        "key": api_v1.form_specs.DictElement(
                            api_v1.form_specs.ServiceState(
                                title=api_v1.Localizable("valuespec title")
                            )
                        ),
                    },
                ),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.ManualCheckParameterRulespec(
                check_group_name="test_rulespec",
                group=legacy_rulespec_groups.RulespecGroupEnforcedServicesApplications,
                title=lambda: _("rulespec title"),
                item_spec=lambda: legacy_valuespecs.TextInput(title=_("item title")),
                parameter_valuespec=lambda: legacy_valuespecs.Dictionary(
                    elements=[
                        ("key", legacy_valuespecs.MonitoringState(title=_("valuespec title")))
                    ],
                ),
                match_type="dict",
            ),
            id="EnforcedServiceRuleSpecWithItem",
        ),
        pytest.param(
            api_v1.rule_specs.EnforcedServiceWithItem(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                item_form=api_v1.form_specs.TextInput(title=api_v1.Localizable("item title")),
                parameter_form=None,
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.ManualCheckParameterRulespec(
                check_group_name="test_rulespec",
                group=legacy_rulespec_groups.RulespecGroupEnforcedServicesApplications,
                title=lambda: _("rulespec title"),
                item_spec=lambda: legacy_valuespecs.TextInput(title=_("item title")),
                parameter_valuespec=None,
                match_type="dict",
            ),
            id="EnforcedServiceRuleSpecWithItem no parameters",
        ),
        pytest.param(
            api_v1.rule_specs.EnforcedServiceWithoutItem(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                parameter_form=partial(
                    api_v1.form_specs.Dictionary,
                    elements={
                        "key": api_v1.form_specs.DictElement(
                            api_v1.form_specs.ServiceState(
                                title=api_v1.Localizable("valuespec title")
                            )
                        ),
                    },
                ),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.ManualCheckParameterRulespec(
                check_group_name="test_rulespec",
                group=legacy_rulespec_groups.RulespecGroupEnforcedServicesApplications,
                title=lambda: _("rulespec title"),
                parameter_valuespec=lambda: legacy_valuespecs.Dictionary(
                    elements=[
                        ("key", legacy_valuespecs.MonitoringState(title=_("valuespec title")))
                    ],
                ),
                match_type="dict",
            ),
            id="EnforcedServiceRuleSpecWithoutItem",
        ),
        pytest.param(
            api_v1.rule_specs.EnforcedServiceWithoutItem(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                parameter_form=None,
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.ManualCheckParameterRulespec(
                check_group_name="test_rulespec",
                group=legacy_rulespec_groups.RulespecGroupEnforcedServicesApplications,
                title=lambda: _("rulespec title"),
                parameter_valuespec=None,
                match_type="dict",
            ),
            id="EnforcedServiceRuleSpecWithoutItem no parameters",
        ),
        pytest.param(
            api_v1.rule_specs.ActiveChecks(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=partial(api_v1.form_specs.TextInput),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name=RuleGroup.ActiveChecks("test_rulespec"),
                group=_to_generated_builtin_sub_group(
                    legacy_wato_groups.RulespecGroupIntegrateOtherServices,
                    "Applications",
                    lambda x: x,
                ),
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="ActiveChecksRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.AgentAccess(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=partial(api_v1.form_specs.TextInput),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name="test_rulespec",
                group=_to_generated_builtin_sub_group(
                    legacy_cmk_config_groups.RulespecGroupAgent,
                    "Applications",
                    lambda x: x,
                ),
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="AgentAccessRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.AgentConfig(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.AGENT_PLUGINS,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=partial(api_v1.form_specs.TextInput),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name=RuleGroup.AgentConfig("test_rulespec"),
                group=_to_generated_builtin_sub_group(
                    legacy_rulespec_groups.RulespecGroupMonitoringAgents,
                    "Agent plug-ins",
                    lambda x: x,
                ),
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="AgentConfigRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.ExtraHostConfHostMonitoring(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=partial(api_v1.form_specs.TextInput),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name=RuleGroup.ExtraHostConf("test_rulespec"),
                group=_to_generated_builtin_sub_group(
                    legacy_rulespec_groups.RulespecGroupHostsMonitoringRules,
                    "Applications",
                    lambda x: x,
                ),
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="ExtraHostConfHostMonitoringRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.ExtraHostConfEventConsole(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=partial(api_v1.form_specs.TextInput),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name=RuleGroup.ExtraHostConf("test_rulespec"),
                group=_to_generated_builtin_sub_group(
                    legacy_mkeventd_groups.RulespecGroupEventConsole,
                    "Applications",
                    lambda x: x,
                ),
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="ExtraHostConfEventConsoleRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.ExtraServiceConf(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=partial(api_v1.form_specs.TextInput),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.ServiceRulespec(
                name=RuleGroup.ExtraServiceConf("test_rulespec"),
                item_type="service",
                group=legacy_wato_groups.RulespecGroupCheckParametersApplications,
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="ExtraServiceConfRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.HostMonitoring(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.NOTIFICATIONS,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=partial(api_v1.form_specs.TextInput),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name="test_rulespec",
                group=legacy_rulespec_groups.RulespecGroupHostsMonitoringRulesNotifications,
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="HostMonitoringRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.InventoryParameters(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=partial(api_v1.form_specs.TextInput),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name=RuleGroup.InvParameters("test_rulespec"),
                group=_to_generated_builtin_sub_group(
                    legacy_inventory_groups.RulespecGroupInventory,
                    "Applications",
                    lambda x: x,
                ),
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="InventoryParameterRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.NotificationParameters(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.NOTIFICATIONS,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=partial(api_v1.form_specs.TextInput),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name=RuleGroup.NotificationParameters("test_rulespec"),
                group=legacy_rulespec_groups.RulespecGroupMonitoringConfigurationNotifications,
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="NotificationParametersRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.DiscoveryParameters(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=partial(api_v1.form_specs.TextInput),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name="test_rulespec",
                group=_to_generated_builtin_sub_group(
                    legacy_wato.RulespecGroupDiscoveryCheckParameters,
                    "Applications",
                    lambda x: x,
                ),
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="ServiceDiscoveryRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.ServiceMonitoringWithoutService(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.NOTIFICATIONS,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=partial(api_v1.form_specs.TextInput),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name="test_rulespec",
                group=legacy_rulespec_groups.RulespecGroupMonitoringConfigurationNotifications,
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="ServiceMonitoringRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.ServiceMonitoring(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.VIRTUALIZATION,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=partial(api_v1.form_specs.TextInput),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.ServiceRulespec(
                name="test_rulespec",
                item_type="service",
                group=legacy_wato_groups.RulespecGroupCheckParametersVirtualization,
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="ServiceRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.SNMP(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.SERVER_HARDWARE,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=partial(api_v1.form_specs.TextInput),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name="test_rulespec",
                group=_to_generated_builtin_sub_group(
                    legacy_rulespec_groups.RulespecGroupAgentSNMP,
                    "Server hardware",
                    lambda x: x,
                ),
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="SNMPRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.SpecialAgent(
                name="test_rulespec",
                title=api_v1.Localizable("rulespec title"),
                topic=api_v1.rule_specs.Topic.CLOUD,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=partial(api_v1.form_specs.TextInput),
                help_text=api_v1.Localizable("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name=RuleGroup.SpecialAgents("test_rulespec"),
                group=legacy_wato_groups.RulespecGroupDatasourceProgramsCloud,
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="SpecialAgentRuleSpec",
        ),
    ],
)
def test_convert_to_legacy_rulespec(
    new_rulespec: APIV1RuleSpec, expected: legacy_rulespecs.Rulespec
) -> None:
    _compare_specs(convert_to_legacy_rulespec(new_rulespec, Edition.CRE, _), expected)


def _compare_specs(actual: object, expected: object) -> None:
    ignored_attrs = {"__orig_class__"}

    if isinstance(expected, Sequence) and not isinstance(expected, str):
        assert isinstance(actual, Sequence) and not isinstance(actual, str)
        assert len(actual) == len(expected)
        for actual_elem, expected_elem in zip(actual, expected):
            _compare_specs(actual_elem, expected_elem)
        return

    if not hasattr(expected, "__dict__"):
        assert actual == expected
        return

    expected_keys = expected.__dict__.keys() - ignored_attrs
    actual_keys = actual.__dict__.keys() - ignored_attrs
    assert expected_keys == actual_keys

    if isinstance(expected, legacy_rulespecs.RulespecBaseGroup):
        _compare_rulespec_groups(actual, expected)

    for attr, expected_value in expected.__dict__.items():
        if attr in ignored_attrs:
            continue
        actual_value = getattr(actual, attr)
        if attr in ["_custom_validate", "_validate"]:
            # testing the equality of the validation in a generic way seems very difficult
            #  check that the field was set during conversion and test behavior separately
            assert (actual_value is not None) is (expected_value is not None)
            continue
        if not callable(expected_value):
            _compare_specs(actual_value, expected_value)
            continue

        try:
            _compare_specs(actual_value(), expected_value())
        except TypeError:  # deal with valuespec constructors
            assert actual_value == expected_value


def _compare_rulespec_groups(actual: object, expected: legacy_rulespecs.RulespecBaseGroup) -> None:
    if isinstance(expected, legacy_rulespecs.RulespecSubGroup):
        assert isinstance(actual, legacy_rulespecs.RulespecSubGroup)
        assert expected.choice_title == actual.choice_title
        assert expected.help == actual.help
        assert expected.main_group == actual.main_group
        assert expected.name == actual.name
        assert expected.sub_group_name == actual.sub_group_name
        assert expected.title == actual.title
    else:
        raise NotImplementedError()


def test_generated_rulespec_group_single_registration():
    first_group = _convert_to_custom_group(
        legacy_rulespec_groups.RulespecGroupMonitoringConfiguration,
        api_v1.Localizable("test"),
        lambda x: x,
    )
    second_group = _convert_to_custom_group(
        legacy_rulespec_groups.RulespecGroupMonitoringConfiguration,
        api_v1.Localizable("test"),
        lambda x: x,
    )
    assert first_group == second_group


@pytest.mark.parametrize(
    "input_value",
    [
        pytest.param("admin", id="custom validation"),
        pytest.param("", id="empty validation"),
        pytest.param(".", id="regex validation"),
    ],
)
def test_convert_validation(input_value: str) -> None:
    converted_spec = _convert_to_legacy_valuespec(
        api_v1.form_specs.TextInput(custom_validate=_v1_custom_text_validate), _
    )

    expected_spec = legacy_valuespecs.TextInput(
        validate=_legacy_custom_text_validate,
        regex=r"^[^.\r\n]+$",
        regex_error=_("No dot allowed"),
        allow_empty=False,
        empty_text=_("Fill this"),
    )

    test_args = (input_value, "var_prefix")
    with pytest.raises(MKUserError) as expected_error:
        expected_spec.validate_value(*test_args)

    with pytest.raises(MKUserError) as actual_error:
        converted_spec.validate_value(*test_args)

    assert actual_error.value.args == expected_error.value.args
    assert actual_error.value.message == expected_error.value.message
    assert actual_error.value.varname == expected_error.value.varname


@pytest.mark.parametrize(
    "input_value, expected_error",
    [
        pytest.param(
            ["first", "second", "third"], "Max number of elements exceeded", id="max elements"
        ),
        pytest.param([], "Empty list", id="empty validation"),
        pytest.param(["first", "first"], "Duplicate elements", id="custom validation"),
    ],
)
def test_list_custom_validate(input_value: Sequence[str], expected_error: str) -> None:
    def _v1_custom_list_validate(value: Sequence[object]) -> None:
        api_v1.validators.DisallowEmpty(error_msg=api_v1.Localizable("Empty list"))(value)

        if len(value) > 2:
            raise api_v1.validators.ValidationError(
                api_v1.Localizable("Max number of elements exceeded")
            )

        if len(set(value)) != len(value):
            raise api_v1.validators.ValidationError(api_v1.Localizable("Duplicate elements"))

    v1_api_list = api_v1.form_specs.List(
        parameter_form=api_v1.form_specs.Tuple(elements=[api_v1.form_specs.TextInput()]),
        custom_validate=_v1_custom_list_validate,
    )

    legacy_list = _convert_to_legacy_valuespec(v1_api_list, _)

    with pytest.raises(MKUserError, match=expected_error):
        legacy_list.validate_value(input_value, "var_prefix")


T = TypeVar("T")


def _narrow_type(x: object, narrow_to: type[T]) -> T:
    if isinstance(x, narrow_to):
        return x
    raise ValueError(x)


@pytest.mark.parametrize(
    ["parameter_form", "old_value", "expected_transformed_value"],
    [
        pytest.param(
            api_v1.form_specs.Integer(
                transform=api_v1.form_specs.Migrate(
                    model_to_form=lambda x: _narrow_type(x, int) * 2
                )
            ),
            2,
            4,
            id="integer migration",
        ),
        pytest.param(
            api_v1.form_specs.Tuple(
                elements=[
                    api_v1.form_specs.Integer(
                        transform=api_v1.form_specs.Migrate(
                            model_to_form=lambda x: _narrow_type(x, int) * 2
                        )
                    ),
                    api_v1.form_specs.Percentage(
                        transform=api_v1.form_specs.Migrate(
                            model_to_form=lambda x: _narrow_type(x, float) * 2
                        )
                    ),
                ]
            ),
            (2, 2.0),
            (4, 4.0),
            id="migrate nested element",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "key2": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer()
                    )
                },
                transform=api_v1.form_specs.Migrate(
                    model_to_form=lambda x: {"key2": _narrow_type(x, dict)["key"]}
                ),
            ),
            {"key": 2},
            {"key2": 2},
            id="migrate top level element",
        ),
        pytest.param(
            api_v1.form_specs.CascadingDropdown(
                elements=[
                    api_v1.form_specs.CascadingDropdownElement(
                        name="key_new",
                        title=api_v1.Localizable("Spec title"),
                        parameter_form=api_v1.form_specs.TextInput(
                            transform=api_v1.form_specs.Migrate(model_to_form=lambda x: f"{x}_new")
                        ),
                    )
                ],
                transform=api_v1.form_specs.Migrate(
                    model_to_form=lambda x: (
                        f"{_narrow_type(x, tuple)[0]}_new",
                        _narrow_type(x, tuple)[1],
                    )
                ),
            ),
            ("key", "value"),
            ("key_new", "value_new"),
            id="migrate nested and top level element",
        ),
    ],
)
def test_migrate(
    parameter_form: api_v1.form_specs.FormSpec,
    old_value: object,
    expected_transformed_value: object,
) -> None:
    legacy_valuespec = _convert_to_legacy_valuespec(parameter_form, localizer=lambda x: x)
    actual_transformed_value = legacy_valuespec.transform_value(value=old_value)
    assert expected_transformed_value == actual_transformed_value


@pytest.mark.parametrize(
    ["parameter_form", "old_value", "expected_transformed_value"],
    [
        pytest.param(
            api_v1.form_specs.Integer(
                transform=api_v1.form_specs.Transform(
                    model_to_form=lambda x: _narrow_type(x, int) * 2,
                    form_to_model=lambda x: x // 2,
                )
            ),
            2,
            2,
            id="transform same",
        ),
        pytest.param(
            api_v1.form_specs.Integer(
                transform=api_v1.form_specs.Transform(
                    model_to_form=lambda x: _narrow_type(x, int) * 2,
                    form_to_model=lambda x: x // 4,
                )
            ),
            2,
            1,
            id="transform different",
        ),
        pytest.param(
            api_v1.form_specs.Tuple(
                elements=[
                    api_v1.form_specs.Integer(
                        transform=api_v1.form_specs.Transform(
                            model_to_form=lambda x: _narrow_type(x, int) * 2,
                            form_to_model=lambda x: x // 2,
                        )
                    ),
                    api_v1.form_specs.Percentage(
                        transform=api_v1.form_specs.Transform(
                            model_to_form=lambda x: _narrow_type(x, float) * 2,
                            form_to_model=lambda x: x / 2,
                        )
                    ),
                ]
            ),
            (2, 2.0),
            (2, 2.0),
            id="transform nested element",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "key2": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer()
                    )
                },
                transform=api_v1.form_specs.Transform(
                    model_to_form=lambda x: {"key2": _narrow_type(x, dict)["key"]},
                    form_to_model=lambda x: {"key": x["key2"]},
                ),
            ),
            {"key": 2},
            {"key": 2},
            id="transform top level element",
        ),
        pytest.param(
            api_v1.form_specs.CascadingDropdown(
                elements=[
                    api_v1.form_specs.CascadingDropdownElement(
                        name="key_new",
                        title=api_v1.Localizable("Spec title"),
                        parameter_form=api_v1.form_specs.TextInput(
                            transform=api_v1.form_specs.Transform(
                                model_to_form=lambda x: f"{x}_new",
                                form_to_model=lambda x: f"{x.removesuffix('_new')}",
                            )
                        ),
                    )
                ],
                transform=api_v1.form_specs.Transform(
                    model_to_form=lambda x: (
                        f"{ _narrow_type(x, tuple)[0]}_new",
                        _narrow_type(x, tuple)[1],
                    ),
                    form_to_model=lambda x: (
                        f"{_narrow_type(x, tuple)[0].removesuffix('_new')}",
                        _narrow_type(x, tuple)[1],
                    ),
                ),
            ),
            ("key", "value"),
            ("key", "value"),
            id="transform nested and top level element",
        ),
    ],
)
def test_transform(
    parameter_form: api_v1.form_specs.FormSpec,
    old_value: object,
    expected_transformed_value: object,
) -> None:
    legacy_valuespec = _convert_to_legacy_valuespec(parameter_form, localizer=lambda x: x)
    actual_transformed_value = legacy_valuespec.transform_value(value=old_value)
    assert expected_transformed_value == actual_transformed_value


def _exposed_form_specs() -> Sequence[api_v1.form_specs.FormSpec]:
    return [
        api_v1.form_specs.Integer(),
        api_v1.form_specs.Float(),
        api_v1.form_specs.DataSize(),
        api_v1.form_specs.Percentage(),
        api_v1.form_specs.TextInput(),
        api_v1.form_specs.Tuple(elements=[]),
        api_v1.form_specs.Dictionary(elements={}),
        api_v1.form_specs.DropdownChoice(elements=[]),
        api_v1.form_specs.CascadingDropdown(elements=[]),
        api_v1.form_specs.ServiceState(),
        api_v1.form_specs.HostState(),
        api_v1.form_specs.List(parameter_form=api_v1.form_specs.Integer()),
        api_v1.form_specs.FixedValue(value=None),
        api_v1.form_specs.TimeSpan(),
        api_v1.form_specs.Levels(lower=None, upper=None, form_spec=api_v1.form_specs.Integer),
        api_v1.form_specs.BooleanChoice(),
        api_v1.form_specs.FileUpload(),
        api_v1.preconfigured.Proxy(),
        api_v1.preconfigured.Metric(),
        api_v1.preconfigured.MonitoredHost(),
    ]


@pytest.mark.parametrize("form_spec", _exposed_form_specs())
def test_form_spec_transform(form_spec: api_v1.form_specs.FormSpec) -> None:
    match form_spec:
        case api_v1.form_specs.Integer() | api_v1.form_specs.Float() | api_v1.form_specs.DataSize() | api_v1.form_specs.Percentage() | api_v1.form_specs.TextInput() | api_v1.form_specs.Tuple() | api_v1.form_specs.Dictionary() | api_v1.form_specs.DropdownChoice() | api_v1.form_specs.CascadingDropdown() | api_v1.form_specs.ServiceState() | api_v1.form_specs.HostState() | api_v1.form_specs.List() | api_v1.form_specs.FixedValue() | api_v1.form_specs.TimeSpan() | api_v1.form_specs.Levels() | api_v1.form_specs.BooleanChoice():
            try:
                _ = form_spec.transform
            except AttributeError:
                assert False
        case api_v1.form_specs.FileUpload() | api_v1.preconfigured.Metric() | api_v1.preconfigured.MonitoredHost() | api_v1.preconfigured.Proxy():
            # these don't have a transform
            assert True
        case other_form_spec:
            assert_never(other_form_spec)


@pytest.mark.parametrize("form_spec", _exposed_form_specs())
def test_form_spec_title(form_spec: api_v1.form_specs.FormSpec) -> None:
    try:
        _ = form_spec.title
    except AttributeError:
        assert False


def _get_legacy_no_levels_choice() -> tuple[str, str, legacy_valuespecs.FixedValue]:
    return (
        "no_levels",
        _("No levels"),
        legacy_valuespecs.FixedValue(
            value=None, title=_("No levels"), totext=_("Do not impose levels, always be OK")
        ),
    )


def _get_legacy_fixed_levels_choice(at_or_below: str) -> tuple[str, str, legacy_valuespecs.Tuple]:
    return (
        "fixed",
        _("Fixed levels"),
        legacy_valuespecs.Tuple(
            elements=[
                legacy_valuespecs.Integer(title=_("Warning %s") % at_or_below, default_value=1),
                legacy_valuespecs.Integer(title=_("Critical %s") % at_or_below, default_value=2),
            ]
        ),
    )


@pytest.mark.parametrize(
    ["api_levels", "legacy_levels"],
    [
        pytest.param(
            api_v1.form_specs.Levels(upper=None, lower=None, form_spec=api_v1.form_specs.Integer),
            legacy_valuespecs.Dictionary(
                elements=[
                    (
                        "levels_lower",
                        legacy_valuespecs.CascadingDropdown(
                            title=_("Lower levels"),
                            choices=[_get_legacy_no_levels_choice()],
                            default_value="no_levels",
                        ),
                    ),
                    (
                        "levels_upper",
                        legacy_valuespecs.CascadingDropdown(
                            title=_("Upper levels"),
                            choices=[_get_legacy_no_levels_choice()],
                            default_value="no_levels",
                        ),
                    ),
                ],
                required_keys=["levels_lower", "levels_upper"],
            ),
            id="empty",
        ),
        pytest.param(
            api_v1.form_specs.Levels(
                form_spec=api_v1.form_specs.Integer,
                lower=(
                    api_v1.form_specs.FixedLevels(prefill_value=(1.0, 2.0)),
                    None,
                ),
                upper=None,
            ),
            legacy_valuespecs.Dictionary(
                elements=[
                    (
                        "levels_lower",
                        legacy_valuespecs.CascadingDropdown(
                            title=_("Lower levels"),
                            choices=[
                                _get_legacy_no_levels_choice(),
                                _get_legacy_fixed_levels_choice("below"),
                            ],
                            default_value="fixed",
                        ),
                    ),
                    (
                        "levels_upper",
                        legacy_valuespecs.CascadingDropdown(
                            title=_("Upper levels"),
                            choices=[_get_legacy_no_levels_choice()],
                            default_value="no_levels",
                        ),
                    ),
                ],
                required_keys=["levels_lower", "levels_upper"],
            ),
            id="lower fixed",
        ),
        pytest.param(
            api_v1.form_specs.Levels(
                form_spec=api_v1.form_specs.Integer,
                lower=None,
                upper=(
                    api_v1.form_specs.FixedLevels(prefill_value=(1.0, 2.0)),
                    None,
                ),
            ),
            legacy_valuespecs.Dictionary(
                elements=[
                    (
                        "levels_lower",
                        legacy_valuespecs.CascadingDropdown(
                            title=_("Lower levels"),
                            choices=[
                                _get_legacy_no_levels_choice(),
                            ],
                            default_value="no_levels",
                        ),
                    ),
                    (
                        "levels_upper",
                        legacy_valuespecs.CascadingDropdown(
                            title=_("Upper levels"),
                            choices=[
                                _get_legacy_no_levels_choice(),
                                _get_legacy_fixed_levels_choice("at"),
                            ],
                            default_value="fixed",
                        ),
                    ),
                ],
                required_keys=["levels_lower", "levels_upper"],
            ),
            id="upper fixed",
        ),
        pytest.param(
            api_v1.form_specs.Levels(
                form_spec=api_v1.form_specs.Integer,
                lower=(
                    api_v1.form_specs.FixedLevels(prefill_value=(1.0, 2.0)),
                    None,
                ),
                upper=(
                    api_v1.form_specs.FixedLevels(prefill_value=(1.0, 2.0)),
                    None,
                ),
            ),
            legacy_valuespecs.Dictionary(
                elements=[
                    (
                        "levels_lower",
                        legacy_valuespecs.CascadingDropdown(
                            title=_("Lower levels"),
                            choices=[
                                _get_legacy_no_levels_choice(),
                                _get_legacy_fixed_levels_choice("below"),
                            ],
                            default_value="fixed",
                        ),
                    ),
                    (
                        "levels_upper",
                        legacy_valuespecs.CascadingDropdown(
                            title=_("Upper levels"),
                            choices=[
                                _get_legacy_no_levels_choice(),
                                _get_legacy_fixed_levels_choice("at"),
                            ],
                            default_value="fixed",
                        ),
                    ),
                ],
                required_keys=["levels_lower", "levels_upper"],
            ),
            id="lower+upper fixed",
        ),
        pytest.param(
            api_v1.form_specs.Levels(
                form_spec=api_v1.form_specs.Integer,
                lower=None,
                upper=(
                    api_v1.form_specs.FixedLevels(prefill_value=(1.0, 2.0)),
                    api_v1.form_specs.PredictiveLevels(
                        prefill_abs_diff=(5.0, 10.0),
                        prefill_rel_diff=(50.0, 80.0),
                        prefill_stddev_diff=(2.0, 3.0),
                    ),
                ),
                unit=api_v1.Localizable("GiB"),
            ),
            legacy_valuespecs.Dictionary(
                elements=[
                    (
                        "levels_lower",
                        legacy_valuespecs.CascadingDropdown(
                            title=_("Lower levels"),
                            choices=[
                                _get_legacy_no_levels_choice(),
                            ],
                            default_value="no_levels",
                        ),
                    ),
                    (
                        "levels_upper",
                        legacy_valuespecs.CascadingDropdown(
                            title=_("Upper levels"),
                            choices=(
                                _get_legacy_no_levels_choice(),
                                (
                                    "fixed",
                                    _("Fixed levels"),
                                    legacy_valuespecs.Tuple(
                                        elements=[
                                            legacy_valuespecs.Integer(
                                                title=_("Warning at"),
                                                default_value=1,
                                                unit="GiB",
                                            ),
                                            legacy_valuespecs.Integer(
                                                title=_("Critical at"),
                                                default_value=2,
                                                unit="GiB",
                                            ),
                                        ],
                                    ),
                                ),
                                (
                                    "predictive",
                                    _("Predictive levels (only on CMC)"),
                                    legacy_valuespecs.Dictionary(
                                        elements=[
                                            (
                                                "period",
                                                legacy_valuespecs.DropdownChoice(
                                                    choices=[
                                                        ("wday", _("Day of the week")),
                                                        ("day", _("Day of the month")),
                                                        ("hour", _("Hour of the day")),
                                                        ("minute", _("Minute of the hour")),
                                                    ],
                                                    title=_("Base prediction on"),
                                                    help=_(
                                                        "Define the periodicity in which the repetition of the measured data is expected (monthly, weekly, daily or hourly)"
                                                    ),
                                                ),
                                            ),
                                            (
                                                "horizon",
                                                legacy_valuespecs.Integer(
                                                    title=_("Length of historic data to consider"),
                                                    help=_(
                                                        "How many days in the past Checkmk should evaluate the measurement data"
                                                    ),
                                                    unit=_("days"),
                                                    minvalue=1,
                                                    default_value=90,
                                                ),
                                            ),
                                            (
                                                "levels",
                                                legacy_valuespecs.CascadingDropdown(
                                                    title=_(
                                                        "Level definition in relation to the predicted value"
                                                    ),
                                                    choices=[
                                                        (
                                                            "absolute",
                                                            _("Absolute difference"),
                                                            legacy_valuespecs.Tuple(
                                                                elements=[
                                                                    legacy_valuespecs.Integer(
                                                                        title=_("Warning above"),
                                                                        unit="GiB",
                                                                        default_value=5,
                                                                    ),
                                                                    legacy_valuespecs.Integer(
                                                                        title=_("Critical above"),
                                                                        unit="GiB",
                                                                        default_value=10,
                                                                    ),
                                                                ],
                                                                help=_(
                                                                    "The thresholds are calculated by increasing or decreasing the predicted value by a fixed absolute value"
                                                                ),
                                                            ),
                                                        ),
                                                        (
                                                            "relative",
                                                            _("Relative difference"),
                                                            legacy_valuespecs.Tuple(
                                                                elements=[
                                                                    legacy_valuespecs.Percentage(
                                                                        title=_("Warning above"),
                                                                        unit="%",
                                                                        default_value=50.0,
                                                                    ),
                                                                    legacy_valuespecs.Percentage(
                                                                        title=_("Critical above"),
                                                                        unit="%",
                                                                        default_value=80.0,
                                                                    ),
                                                                ],
                                                                help=_(
                                                                    "The thresholds are calculated by increasing or decreasing the predicted value by a percentage"
                                                                ),
                                                            ),
                                                        ),
                                                        (
                                                            "stddev",
                                                            _("Standard deviation difference"),
                                                            legacy_valuespecs.Tuple(
                                                                elements=[
                                                                    legacy_valuespecs.Float(
                                                                        title=_("Warning above"),
                                                                        unit=_(
                                                                            "times the standard deviation"
                                                                        ),
                                                                        default_value=2.0,
                                                                    ),
                                                                    legacy_valuespecs.Float(
                                                                        title=_("Critical above"),
                                                                        unit=_(
                                                                            "times the standard deviation"
                                                                        ),
                                                                        default_value=3.0,
                                                                    ),
                                                                ],
                                                                help=_(
                                                                    "The thresholds are calculated by increasing or decreasing the predicted value by a multiple of the standard deviation"
                                                                ),
                                                            ),
                                                        ),
                                                    ],
                                                ),
                                            ),
                                            (
                                                "bound",
                                                legacy_valuespecs.Tuple(
                                                    title=_("Fixed limits"),
                                                    help=_(
                                                        "Regardless of how the dynamic levels are computed according to the prediction: they will never be set below the following limits. This avoids false alarms during times where the predicted levels would be very low."
                                                    ),
                                                    elements=[
                                                        legacy_valuespecs.Integer(
                                                            title="Warning level is at least",
                                                            unit="GiB",
                                                        ),
                                                        legacy_valuespecs.Integer(
                                                            title="Critical level is at least",
                                                            unit="GiB",
                                                        ),
                                                    ],
                                                ),
                                            ),
                                            (
                                                "__get_predictive_levels__",
                                                legacy_valuespecs.FixedValue(None),
                                            ),
                                        ],
                                        optional_keys=["bound"],
                                        ignored_keys=["__get_predictive_levels__"],
                                        hidden_keys=["__get_predictive_levels__"],
                                    ),
                                ),
                            ),
                            default_value="fixed",
                        ),
                    ),
                ],
                required_keys=["levels_lower", "levels_upper"],
            ),
            id="upper fixed+predictive",
        ),
    ],
)
def test_level_conversion(
    api_levels: api_v1.form_specs.Levels, legacy_levels: legacy_valuespecs.Dictionary
) -> None:
    _compare_specs(_convert_to_legacy_levels(api_levels, _), legacy_levels)
