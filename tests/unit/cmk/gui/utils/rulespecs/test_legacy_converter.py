#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

from collections.abc import Callable, Mapping, Sequence
from functools import partial
from typing import Any, TypeVar

import pytest

import cmk.gui.graphing._valuespecs as legacy_graphing_valuespecs
import cmk.gui.valuespec as legacy_valuespecs
import cmk.rulesets.v1 as api_v1
from cmk.ccc.version import Edition
from cmk.gui import inventory as legacy_inventory_groups
from cmk.gui import wato as legacy_wato
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.unstable import (
    Autocompleter,
    AutocompleterData,
    AutocompleterParams,
    StringAutocompleter,
)
from cmk.gui.form_specs.unstable.legacy_converter import Tuple
from cmk.gui.i18n import _, translate_to_current_language
from cmk.gui.utils.autocompleter_config import AutocompleterConfig, ContextAutocompleterConfig
from cmk.gui.utils.rule_specs.legacy_converter import (
    _convert_to_custom_group,
    _convert_to_legacy_levels,
    _convert_to_legacy_rulespec_group,
    _to_generated_builtin_sub_group,
    convert_to_legacy_rulespec,
    convert_to_legacy_valuespec,
)
from cmk.gui.utils.rule_specs.types import RuleSpec as APIV1RuleSpec
from cmk.gui.utils.urls import DocReference
from cmk.gui.valuespec import LegacyBinaryUnit, LegacyDataSize
from cmk.gui.watolib import rulespec_groups as legacy_rulespec_groups
from cmk.gui.watolib import rulespecs as legacy_rulespecs
from cmk.gui.watolib import timeperiods as legacy_timeperiods
from cmk.gui.watolib.password_store import IndividualOrStoredPassword
from cmk.rulesets.internal.form_specs import OAuth2Connection
from cmk.rulesets.v1.form_specs import FormSpec
from cmk.utils.rulesets.definition import RuleGroup


def _v1_custom_text_validate(value: str) -> None:
    if value == "admin":
        raise api_v1.form_specs.validators.ValidationError(api_v1.Message("Forbidden"))


def _legacy_custom_text_validate(value: str, varprefix: str) -> None:
    if value == "admin":
        raise MKUserError(varprefix, _("Forbidden"))


@pytest.mark.parametrize(
    ["new_valuespec", "expected"],
    [
        pytest.param(
            api_v1.form_specs.HostState(),
            legacy_valuespecs.HostState(),
            id="minimal HostState",
        ),
        pytest.param(
            api_v1.form_specs.HostState(
                title=api_v1.Title("title"),
                help_text=api_v1.Help("help text"),
                prefill=api_v1.form_specs.DefaultValue(1),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.HostState(
                sorted=False,
                title=_("title"),
                help=_("help text"),
                default_value=1,
                validate=lambda x, y: None,
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
                title=api_v1.Title("title"),
                help_text=api_v1.Help("help text"),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.MonitoringState(
                title=_("title"),
                help=_("help text"),
                default_value=0,
                validate=lambda x, y: None,
            ),
            id="MonitoringState",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(elements={}),
            legacy_valuespecs.Transform(legacy_valuespecs.Dictionary(elements=[])),
            id="minimal Dictionary",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "key_req": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.ServiceState(title=api_v1.Title("title")),
                        required=True,
                    ),
                    "key_read_only": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.ServiceState(title=api_v1.Title("title")),
                        render_only=True,
                    ),
                },
                title=api_v1.Title("Configuration title"),
                help_text=api_v1.Help("Helpful description"),
                ignored_elements=("old_key", "another_old_key"),
                no_elements_text=api_v1.Message("No elements specified"),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.Transform(
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
                    validate=lambda x, y: None,
                )
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
                title=api_v1.Title("title"),
                help_text=api_v1.Help("help"),
                label=api_v1.Label("label"),
                unit_symbol="d",
                prefill=api_v1.form_specs.DefaultValue(-1),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.Integer(
                title=_("title"),
                help=_("help"),
                label=_("label"),
                unit="d",
                default_value=-1,
                validate=lambda x, y: None,
            ),
            id="Integer",
        ),
        pytest.param(
            api_v1.form_specs.Float(),
            legacy_valuespecs.Float(display_format="%r"),
            id="minimal Float",
        ),
        pytest.param(
            api_v1.form_specs.Float(
                title=api_v1.Title("title"),
                help_text=api_v1.Help("help"),
                label=api_v1.Label("label"),
                unit_symbol="1/s",
                prefill=api_v1.form_specs.DefaultValue(-1.0),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.Float(
                title=_("title"),
                help=_("help"),
                label=_("label"),
                display_format="%r",
                unit="1/s",
                default_value=-1.0,
                validate=lambda x, y: None,
            ),
            id="Float",
        ),
        pytest.param(
            api_v1.form_specs.DataSize(
                displayed_magnitudes=tuple(api_v1.form_specs.SIMagnitude)[:5]
            ),
            LegacyDataSize(
                units=[
                    LegacyBinaryUnit.Byte,
                    LegacyBinaryUnit.KB,
                    LegacyBinaryUnit.MB,
                    LegacyBinaryUnit.GB,
                    LegacyBinaryUnit.TB,
                ],
            ),
            id="minimal DataSize",
        ),
        pytest.param(
            api_v1.form_specs.DataSize(
                title=api_v1.Title("title"),
                help_text=api_v1.Help("help"),
                label=api_v1.Label("label"),
                displayed_magnitudes=(
                    api_v1.form_specs.SIMagnitude.KILO,
                    api_v1.form_specs.SIMagnitude.EXA,
                ),
                prefill=api_v1.form_specs.DefaultValue(-1),
                custom_validate=(lambda x: None,),
            ),
            LegacyDataSize(
                title=_("title"),
                help=_("help"),
                label=_("label"),
                units=[
                    LegacyBinaryUnit.KB,
                    LegacyBinaryUnit.EB,
                ],
                default_value=-1,
                validate=lambda x, y: None,
            ),
            id="DataSize",
        ),
        pytest.param(
            api_v1.form_specs.Percentage(),
            legacy_valuespecs.Percentage(
                display_format="%r",
                minvalue=None,
                maxvalue=None,
            ),
            id="minimal Percentage",
        ),
        pytest.param(
            api_v1.form_specs.Percentage(
                title=api_v1.Title("title"),
                help_text=api_v1.Help("help"),
                label=api_v1.Label("label"),
                prefill=api_v1.form_specs.DefaultValue(-1.0),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.Percentage(
                title=_("title"),
                help=_("help"),
                label=_("label"),
                display_format="%r",
                default_value=-1.0,
                minvalue=None,
                maxvalue=None,
                validate=lambda x, y: None,
            ),
            id="Percentage",
        ),
        pytest.param(
            api_v1.form_specs.String(),
            legacy_valuespecs.TextInput(placeholder="", size=35),
            id="minimal TextInput",
        ),
        pytest.param(
            api_v1.form_specs.String(
                field_size=api_v1.form_specs.FieldSize.SMALL,
            ),
            legacy_valuespecs.TextInput(placeholder="", size=7),
            id="small TextInput",
        ),
        pytest.param(
            api_v1.form_specs.String(
                field_size=api_v1.form_specs.FieldSize.MEDIUM,
            ),
            legacy_valuespecs.TextInput(placeholder="", size=35),
            id="medium size TextInput",
        ),
        pytest.param(
            api_v1.form_specs.String(
                field_size=api_v1.form_specs.FieldSize.LARGE,
            ),
            legacy_valuespecs.TextInput(placeholder="", size=100),
            id="large size TextInput",
        ),
        pytest.param(
            api_v1.form_specs.String(
                custom_validate=(api_v1.form_specs.validators.LengthInRange(min_value=1),)
            ),
            legacy_valuespecs.TextInput(
                size=35,
                placeholder="",
                allow_empty=False,
                empty_text=_("The minimum allowed length is 1."),
                validate=lambda _x, _y: None,  # ignored by test
            ),
            id="TextInput empty disallowed",
        ),
        pytest.param(
            api_v1.form_specs.String(
                title=api_v1.Title("spec title"),
                label=api_v1.Label("spec label"),
                macro_support=True,
                help_text=api_v1.Help("help text"),
                prefill=api_v1.form_specs.InputHint("myname"),
                custom_validate=(
                    api_v1.form_specs.validators.LengthInRange(
                        min_value=1, error_msg=api_v1.Message("Fill this")
                    ),
                    api_v1.form_specs.validators.MatchRegex(
                        regex=r"^[^.\r\n]+$", error_msg=api_v1.Message("No dot allowed")
                    ),
                    _v1_custom_text_validate,
                ),
            ),
            legacy_valuespecs.TextInput(
                title=_("spec title"),
                label=_("spec label"),
                placeholder="myname",
                help=_(
                    "help text This field supports the use of macros. The corresponding plug-in replaces the macros with the actual values. The most common ones are $HOSTNAME$, $HOSTALIAS$ or $HOSTADDRESS$."
                ),
                validate=_legacy_custom_text_validate,
                allow_empty=False,
                empty_text=_("Fill this"),
                size=35,
            ),
            id="TextInput",
        ),
        pytest.param(
            api_v1.form_specs.RegularExpression(
                predefined_help_text=api_v1.form_specs.MatchingScope.INFIX,
            ),
            legacy_valuespecs.RegExp(
                mode=legacy_valuespecs.RegExp.infix, case_sensitive=True, placeholder=""
            ),
            id="minimal RegularExpression",
        ),
        pytest.param(
            api_v1.form_specs.RegularExpression(
                predefined_help_text=api_v1.form_specs.MatchingScope.PREFIX,
                title=api_v1.Title("spec title"),
                label=api_v1.Label("spec label"),
                help_text=api_v1.Help("help text"),
                prefill=api_v1.form_specs.DefaultValue("mypattern$"),
                custom_validate=(
                    api_v1.form_specs.validators.LengthInRange(
                        min_value=1, error_msg=api_v1.Message("Fill this")
                    ),
                    api_v1.form_specs.validators.MatchRegex(
                        regex=r"^[^.\r\n]+$", error_msg=api_v1.Message("No dot allowed")
                    ),
                    _v1_custom_text_validate,
                ),
            ),
            legacy_valuespecs.RegExp(
                mode=legacy_valuespecs.RegExp.prefix,
                case_sensitive=True,
                title=_("spec title"),
                label=_("spec label"),
                help=_("help text"),
                default_value="mypattern$",
                validate=_legacy_custom_text_validate,
                allow_empty=False,
                empty_text=_("Fill this"),
            ),
            id="RegularExpression",
        ),
        pytest.param(
            api_v1.form_specs.SingleChoice(elements=[]),
            legacy_valuespecs.DropdownChoice(
                choices=[], invalid_choice="complain", no_preselect_title="Please choose"
            ),
            id="minimal DropdownChoice",
        ),
        pytest.param(
            api_v1.form_specs.SingleChoice(
                elements=[
                    api_v1.form_specs.SingleChoiceElement(
                        name="true", title=api_v1.Title("Enabled")
                    ),
                    api_v1.form_specs.SingleChoiceElement(
                        name="false", title=api_v1.Title("Disabled")
                    ),
                ],
                no_elements_text=api_v1.Message("No elements"),
                ignored_elements=(),
                frozen=True,
                title=api_v1.Title("title"),
                label=api_v1.Label("label"),
                help_text=api_v1.Help("help text"),
                prefill=api_v1.form_specs.DefaultValue("true"),
                invalid_element_validation=api_v1.form_specs.InvalidElementValidator(
                    mode=api_v1.form_specs.InvalidElementMode.KEEP,
                    display=api_v1.Title("invalid choice title"),
                    error_msg=api_v1.Message("invalid choice msg"),
                ),
                custom_validate=(lambda x: None,),
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
                validate=lambda x, y: None,
            ),
            id="DropdownChoice",
        ),
        pytest.param(
            api_v1.form_specs.CascadingSingleChoice(elements=[]),
            legacy_valuespecs.CascadingDropdown(choices=[], no_preselect_title="Please choose"),
            id="minimal CascadingDropdown",
        ),
        pytest.param(
            api_v1.form_specs.CascadingSingleChoice(
                elements=[
                    api_v1.form_specs.CascadingSingleChoiceElement(
                        name="first",
                        title=api_v1.Title("Spec title"),
                        parameter_form=api_v1.form_specs.String(),
                    )
                ],
                title=api_v1.Title("parent title"),
                help_text=api_v1.Help("parent help"),
                label=api_v1.Label("parent label"),
                prefill=api_v1.form_specs.DefaultValue("first"),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.CascadingDropdown(
                choices=[
                    ("first", _("Spec title"), legacy_valuespecs.TextInput(placeholder="", size=35))
                ],
                title=_("parent title"),
                help=_("parent help"),
                label=_("parent label"),
                default_value=("first", ""),
                validate=lambda x, y: None,
            ),
            id="CascadingDropdown",
        ),
        pytest.param(
            api_v1.form_specs.List(element_template=api_v1.form_specs.Dictionary(elements={})),
            legacy_valuespecs.ListOf(
                valuespec=legacy_valuespecs.Transform(legacy_valuespecs.Dictionary(elements=[])),
                add_label="Add new entry",
                del_label="Remove this entry",
                text_if_empty="No entries",
            ),
            id="minimal ListOf",
        ),
        pytest.param(
            api_v1.form_specs.List(
                element_template=api_v1.form_specs.Dictionary(
                    elements={
                        "key1": api_v1.form_specs.DictElement(
                            parameter_form=api_v1.form_specs.String()
                        ),
                        "key2": api_v1.form_specs.DictElement(
                            parameter_form=api_v1.form_specs.Integer(unit_symbol="km")
                        ),
                    }
                ),
                title=api_v1.Title("list title"),
                help_text=api_v1.Help("list help"),
                editable_order=False,
                add_element_label=api_v1.Label("Add item"),
                remove_element_label=api_v1.Label("Remove item"),
                no_element_label=api_v1.Label("No items"),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.ListOf(
                valuespec=legacy_valuespecs.Transform(
                    legacy_valuespecs.Dictionary(
                        elements=[
                            ("key1", legacy_valuespecs.TextInput(placeholder="", size=35)),
                            ("key2", legacy_valuespecs.Integer(unit="km")),
                        ]
                    )
                ),
                title="list title",
                help="list help",
                add_label="Add item",
                del_label="Remove item",
                movable=False,
                text_if_empty="No items",
                validate=lambda x, y: None,
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
                title=api_v1.Title("Enable the option"),
                label=api_v1.Label("The option is enabled"),
                help_text=api_v1.Help("Help text"),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.FixedValue(
                value="enabled",
                title=_("Enable the option"),
                totext=_("The option is enabled"),
                help=_("Help text"),
                validate=lambda x, y: None,
            ),
            id="FixedValue",
        ),
        pytest.param(
            api_v1.form_specs.TimeSpan(
                # reverse just to keep the test simple
                displayed_magnitudes=tuple(reversed(api_v1.form_specs.TimeMagnitude))
            ),
            legacy_valuespecs.TimeSpan(),
            id="minimal TimeSpan",
        ),
        pytest.param(
            api_v1.form_specs.TimeSpan(
                title=api_v1.Title("age title"),
                label=api_v1.Label("age label"),
                help_text=api_v1.Help("help text"),
                displayed_magnitudes=[
                    api_v1.form_specs.TimeMagnitude.DAY,
                    api_v1.form_specs.TimeMagnitude.HOUR,
                    api_v1.form_specs.TimeMagnitude.MINUTE,
                    api_v1.form_specs.TimeMagnitude.SECOND,
                ],
                prefill=api_v1.form_specs.DefaultValue(100),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.TimeSpan(
                title=_("age title"),
                label=_("age label"),
                help=_("help text"),
                display=["days", "hours", "minutes", "seconds"],
                default_value=100,
                validate=lambda x, y: None,
            ),
            id="TimeSpan",
        ),
        pytest.param(
            api_v1.form_specs.Proxy(),
            legacy_valuespecs.Transform(
                legacy_valuespecs.CascadingDropdown(
                    title=_("HTTP proxy"),
                    default_value=("environment", "environment"),
                    choices=[
                        (
                            "environment",
                            _("Auto-detect proxy settings for this network"),
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
                            _("No proxy"),
                            legacy_valuespecs.FixedValue(
                                value=None,
                                totext=_(
                                    "Connect directly to the destination instead of using a proxy."
                                ),
                            ),
                        ),
                        (
                            "global",
                            _("Globally configured proxy"),
                            legacy_valuespecs.DropdownChoice(
                                choices=lambda: [],
                                sorted=True,
                            ),
                        ),
                        (
                            "url",
                            _("Manual proxy configuration"),
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
            ),
            id="minimal HTTPProxy",
        ),
        pytest.param(
            api_v1.form_specs.Proxy(
                allowed_schemas=frozenset(
                    {
                        api_v1.form_specs.ProxySchema.HTTP,
                        api_v1.form_specs.ProxySchema.HTTPS,
                    }
                ),
                title=api_v1.Title("age title"),
                help_text=api_v1.Help("help text"),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.CascadingDropdown(
                    title=_("HTTP proxy"),
                    default_value=("environment", "environment"),
                    choices=[
                        (
                            "environment",
                            _("Auto-detect proxy settings for this network"),
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
                            _("No proxy"),
                            legacy_valuespecs.FixedValue(
                                value=None,
                                totext=_(
                                    "Connect directly to the destination instead of using a proxy."
                                ),
                            ),
                        ),
                        (
                            "global",
                            _("Globally configured proxy"),
                            legacy_valuespecs.DropdownChoice(
                                choices=lambda: [],
                                sorted=True,
                            ),
                        ),
                        (
                            "url",
                            _("Manual proxy configuration"),
                            legacy_valuespecs.Url(
                                title=_("Proxy URL"),
                                default_scheme="http",
                                allowed_schemes=frozenset({"http", "https"}),
                            ),
                        ),
                    ],
                    sorted=False,
                ),
                validate=lambda x, y: None,
            ),
            id="HTTPProxy",
        ),
        pytest.param(
            api_v1.form_specs.BooleanChoice(),
            legacy_valuespecs.Checkbox(default_value=False),
            id="minimal BooleanChoice",
        ),
        pytest.param(
            api_v1.form_specs.BooleanChoice(
                title=api_v1.Title("boolean choice title"),
                label=api_v1.Label("boolean choice label"),
                help_text=api_v1.Help("help text"),
                prefill=api_v1.form_specs.DefaultValue(True),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.Checkbox(
                title=_("boolean choice title"),
                label=_("boolean choice label"),
                help=_("help text"),
                default_value=True,
                validate=lambda x, y: None,
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
                title=api_v1.Title("my title"),
                help_text=api_v1.Help("help text"),
                extensions=("txt", "rst"),
                mime_types=("text/plain",),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.FileUpload(
                title=_("my title"),
                help=_("help text"),
                allowed_extensions=("txt", "rst"),
                mime_types=("text/plain",),
                allow_empty=True,
                validate=lambda x, y: None,
            ),
            id="FileUpload",
        ),
        pytest.param(
            api_v1.form_specs.Metric(),
            legacy_graphing_valuespecs.MetricName(
                title=_("Metric"),
                help=_("Select from a list of metrics known to Checkmk"),
            ),
            id="minimal Metric",
        ),
        pytest.param(
            api_v1.form_specs.Metric(
                title=api_v1.Title("metric title"),
                help_text=api_v1.Help("help text"),
                custom_validate=(lambda x: None,),
            ),
            legacy_graphing_valuespecs.MetricName(
                title=_("metric title"),
                help=_("help text"),
                validate=lambda x, y: None,
            ),
            id="Metric",
        ),
        pytest.param(
            api_v1.form_specs.MonitoredHost(),
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
            api_v1.form_specs.MonitoredHost(
                title=api_v1.Title("host title"),
                help_text=api_v1.Help("help text"),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.MonitoredHostname(
                title=_("host title"),
                help=_("help text"),
                autocompleter=ContextAutocompleterConfig(
                    ident=legacy_valuespecs.MonitoredHostname.ident,
                    strict=True,
                    show_independent_of_context=True,
                ),
                validate=lambda x, y: None,
            ),
            id="MonitoredHost",
        ),
        pytest.param(
            api_v1.form_specs.MonitoredService(),
            legacy_valuespecs.MonitoredServiceDescription(
                title=_("Service name"),
                help=_("Select from a list of service names known to Checkmk"),
                autocompleter=ContextAutocompleterConfig(
                    ident=legacy_valuespecs.MonitoredServiceDescription.ident,
                    strict=True,
                    show_independent_of_context=True,
                ),
            ),
            id="minimal MonitoredService",
        ),
        pytest.param(
            api_v1.form_specs.MonitoredService(
                title=api_v1.Title("service title"),
                help_text=api_v1.Help("help text"),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.MonitoredServiceDescription(
                title=_("service title"),
                help=_("help text"),
                autocompleter=ContextAutocompleterConfig(
                    ident=legacy_valuespecs.MonitoredServiceDescription.ident,
                    strict=True,
                    show_independent_of_context=True,
                ),
                validate=lambda x, y: None,
            ),
            id="MonitoredService",
        ),
        pytest.param(
            api_v1.form_specs.Password(),
            legacy_valuespecs.Transform(
                IndividualOrStoredPassword(allow_empty=False),
            ),
            id="minimal Password",
        ),
        pytest.param(
            api_v1.form_specs.Password(
                title=api_v1.Title("password title"),
                help_text=api_v1.Help("help text"),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.Transform(
                IndividualOrStoredPassword(
                    title=_("password title"),
                    help=_("help text"),
                    allow_empty=False,
                ),
                validate=lambda x, y: None,
            ),
            id="Password",
        ),
        pytest.param(
            api_v1.form_specs.MultipleChoice(
                elements=[
                    api_v1.form_specs.MultipleChoiceElement(
                        name="first", title=api_v1.Title("First")
                    )
                ]
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.ListChoice(choices=[("first", _("First"))], default_value=())
            ),
            id="minimal MultipleChoice",
        ),
        pytest.param(
            api_v1.form_specs.MultipleChoice(
                title=api_v1.Title("my title"),
                help_text=api_v1.Help("help text"),
                elements=[
                    api_v1.form_specs.MultipleChoiceElement(
                        name="first", title=api_v1.Title("First")
                    ),
                    api_v1.form_specs.MultipleChoiceElement(
                        name="second", title=api_v1.Title("Second")
                    ),
                ],
                show_toggle_all=True,
                prefill=api_v1.form_specs.DefaultValue(("first", "second")),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.ListChoice(
                    choices=[("first", _("First")), ("second", _("Second"))],
                    toggle_all=True,
                    title=_("my title"),
                    help=_("help text"),
                    default_value=["first", "second"],
                    validate=lambda x, y: None,
                )
            ),
            id="MultipleChoice",
        ),
        pytest.param(
            api_v1.form_specs.MultipleChoice(
                title=api_v1.Title("my title"),
                help_text=api_v1.Help("help text"),
                elements=[
                    api_v1.form_specs.MultipleChoiceElement(
                        name="first", title=api_v1.Title("First")
                    ),
                    api_v1.form_specs.MultipleChoiceElement(
                        name="second", title=api_v1.Title("Second")
                    ),
                    api_v1.form_specs.MultipleChoiceElement(
                        name="third", title=api_v1.Title("Third")
                    ),
                    api_v1.form_specs.MultipleChoiceElement(
                        name="fourth", title=api_v1.Title("Fourth")
                    ),
                    api_v1.form_specs.MultipleChoiceElement(
                        name="fifth", title=api_v1.Title("Fifth")
                    ),
                    api_v1.form_specs.MultipleChoiceElement(
                        name="sixth", title=api_v1.Title("Sixth")
                    ),
                    api_v1.form_specs.MultipleChoiceElement(
                        name="seventh", title=api_v1.Title("Seventh")
                    ),
                    api_v1.form_specs.MultipleChoiceElement(
                        name="eight", title=api_v1.Title("Eight")
                    ),
                    api_v1.form_specs.MultipleChoiceElement(
                        name="ninth", title=api_v1.Title("Ninth")
                    ),
                    api_v1.form_specs.MultipleChoiceElement(
                        name="tenth", title=api_v1.Title("Tenth")
                    ),
                    api_v1.form_specs.MultipleChoiceElement(
                        name="eleventh", title=api_v1.Title("Eleventh")
                    ),
                ],
                show_toggle_all=True,
                prefill=api_v1.form_specs.DefaultValue(("first", "third")),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.DualListChoice(
                    choices=[
                        ("first", _("First")),
                        ("second", _("Second")),
                        ("third", _("Third")),
                        ("fourth", _("Fourth")),
                        ("fifth", _("Fifth")),
                        ("sixth", _("Sixth")),
                        ("seventh", _("Seventh")),
                        ("eight", _("Eight")),
                        ("ninth", _("Ninth")),
                        ("tenth", _("Tenth")),
                        ("eleventh", _("Eleventh")),
                    ],
                    toggle_all=True,
                    title=_("my title"),
                    help=_("help text"),
                    default_value=["first", "third"],
                    rows=11,
                    validate=lambda x, y: None,
                ),
            ),
            id="large MultipleChoice",
        ),
        pytest.param(
            api_v1.form_specs.MultilineText(),
            legacy_valuespecs.TextAreaUnicode(),
            id="minimal MultilineText",
        ),
        pytest.param(
            api_v1.form_specs.MultilineText(
                monospaced=True,
                title=api_v1.Title("my title"),
                help_text=api_v1.Help("help text"),
                label=api_v1.Label("label"),
                prefill=api_v1.form_specs.DefaultValue("default text"),
                macro_support=True,
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.TextAreaUnicode(
                monospaced=True,
                title=_("my title"),
                help=_(
                    "help text This field supports the use of macros. The corresponding plug-in replaces the macros with the actual values."
                ),
                label=_("label"),
                default_value="default text",
                validate=lambda x, y: None,
            ),
            id="MultilineText",
        ),
        pytest.param(
            api_v1.form_specs.TimePeriod(),
            legacy_valuespecs.Transform(legacy_timeperiods.TimeperiodSelection()),
            id="minimal TimePeriod",
        ),
        pytest.param(
            api_v1.form_specs.TimePeriod(
                title=api_v1.Title("title"),
                help_text=api_v1.Help("help text"),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.Transform(
                legacy_timeperiods.TimeperiodSelection(
                    title="title",
                    help="help text",
                ),
                validate=lambda x, y: None,
            ),
            id="TimePeriod",
        ),
        pytest.param(
            Tuple(
                elements=[
                    api_v1.form_specs.String(),
                    api_v1.form_specs.Integer(),
                ],
            ),
            legacy_valuespecs.Tuple(
                elements=[
                    legacy_valuespecs.TextInput(placeholder="", size=35),
                    legacy_valuespecs.Integer(),
                ],
            ),
            id="Minimal Tuple",
        ),
        pytest.param(
            Tuple(
                title=api_v1.Title("title"),
                help_text=api_v1.Help("help text"),
                show_titles=False,
                layout="float",
                elements=[
                    api_v1.form_specs.String(),
                    api_v1.form_specs.Integer(),
                ],
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.Tuple(
                title="title",
                help="help text",
                show_titles=False,
                orientation="float",
                elements=[
                    legacy_valuespecs.TextInput(placeholder="", size=35),
                    legacy_valuespecs.Integer(),
                ],
                validate=lambda x, y: None,
            ),
            id="Tuple",
        ),
        pytest.param(
            StringAutocompleter(),
            legacy_valuespecs.AjaxDropdownChoice(),
            id="minimal StringAutocompleter",
        ),
        pytest.param(
            StringAutocompleter(
                title=api_v1.Title("title"),
                help_text=api_v1.Help("help text"),
                autocompleter=Autocompleter(
                    data=AutocompleterData(ident="test-autocompleter", params=AutocompleterParams())
                ),
                custom_validate=(lambda x: None,),
            ),
            legacy_valuespecs.AjaxDropdownChoice(
                title="title",
                help="help text",
                autocompleter=AutocompleterConfig(
                    ident="test-autocompleter",
                ),
                validate=lambda x, y: None,
            ),
            id="StringAutocompleter",
        ),
        pytest.param(
            OAuth2Connection(
                title=api_v1.Title("title"),
                help_text=api_v1.Help("help text"),
                connector_type="microsoft_entra_id",
            ),
            legacy_valuespecs.Transform(
                valuespec=legacy_valuespecs.DropdownChoice(
                    title="title",
                    help="help text",
                    choices=[],
                    no_preselect_title="Please select an element",
                ),
            ),
            id="OAuth2Connection",
        ),
    ],
)
def test_convert_to_legacy_valuespec(
    new_valuespec: FormSpec, expected: legacy_valuespecs.ValueSpec
) -> None:
    _compare_specs(
        convert_to_legacy_valuespec(new_valuespec, translate_to_current_language), expected
    )


def _get_cascading_single_choice_with_prefill_selection(
    prefill_selection: str,
) -> api_v1.form_specs.CascadingSingleChoice:
    return api_v1.form_specs.CascadingSingleChoice(
        elements=[
            api_v1.form_specs.CascadingSingleChoiceElement(
                name="no_prefill",
                title=api_v1.Title("no prefill"),
                parameter_form=api_v1.form_specs.Integer(),
            ),
            api_v1.form_specs.CascadingSingleChoiceElement(
                name="simple_prefill",
                title=api_v1.Title("simple prefill"),
                parameter_form=api_v1.form_specs.String(
                    prefill=api_v1.form_specs.DefaultValue("prefill_text")
                ),
            ),
            api_v1.form_specs.CascadingSingleChoiceElement(
                name="nested",
                title=api_v1.Title("nested"),
                parameter_form=api_v1.form_specs.Dictionary(
                    elements={
                        "key1": api_v1.form_specs.DictElement(
                            parameter_form=api_v1.form_specs.Integer()
                        ),
                        "key2": api_v1.form_specs.DictElement(
                            parameter_form=api_v1.form_specs.Integer()
                        ),
                    }
                ),
            ),
            api_v1.form_specs.CascadingSingleChoiceElement(
                name="nested_prefill",
                title=api_v1.Title("nested prefill"),
                parameter_form=api_v1.form_specs.Dictionary(
                    elements={
                        "key1": api_v1.form_specs.DictElement(
                            parameter_form=api_v1.form_specs.Integer(
                                prefill=api_v1.form_specs.DefaultValue(1)
                            ),
                            required=True,
                        ),
                        "key2": api_v1.form_specs.DictElement(
                            parameter_form=api_v1.form_specs.Integer(
                                prefill=api_v1.form_specs.DefaultValue(2)
                            ),
                            required=True,
                        ),
                    }
                ),
            ),
        ],
        prefill=api_v1.form_specs.DefaultValue(prefill_selection),
    )


@pytest.mark.parametrize(
    ["prefilled_spec", "expected_default_value"],
    [
        pytest.param(
            _get_cascading_single_choice_with_prefill_selection("no_prefill"),
            ("no_prefill", 0),
            id="no_prefill",
        ),
        pytest.param(
            _get_cascading_single_choice_with_prefill_selection("simple_prefill"),
            ("simple_prefill", "prefill_text"),
            id="simple_prefill",
        ),
        pytest.param(
            _get_cascading_single_choice_with_prefill_selection("nested"),
            ("nested", {}),
            id="nested",
        ),
        pytest.param(
            _get_cascading_single_choice_with_prefill_selection("nested_prefill"),
            ("nested_prefill", {"key1": 1, "key2": 2}),
            id="nested_prefill",
        ),
    ],
)
def test_cascading_singe_choice_prefill_selection_conversion(
    prefilled_spec: api_v1.form_specs.CascadingSingleChoice, expected_default_value: tuple
) -> None:
    converted_prefilled_spec = convert_to_legacy_valuespec(prefilled_spec, lambda x: x)
    assert expected_default_value == converted_prefilled_spec.default_value()


@pytest.mark.parametrize(
    ["legacy_main_group", "new_topic", "expected"],
    [
        pytest.param(
            legacy_rulespec_groups.RulespecGroupMonitoringConfiguration,
            api_v1.rule_specs.Topic.APPLICATIONS,
            legacy_rulespec_groups.RulespecGroupCheckParametersApplications,
            id="CheckParametersApplications",
        ),
    ],
)
def test_convert_to_legacy_rulespec_group(
    legacy_main_group: type[legacy_rulespecs.RulespecGroup],
    new_topic: api_v1.rule_specs.Topic,
    expected: type[legacy_rulespecs.RulespecSubGroup],
) -> None:
    assert (
        _convert_to_legacy_rulespec_group(
            legacy_main_group, new_topic, translate_to_current_language
        )
        == expected
    )


@pytest.mark.parametrize(
    ["new_rulespec", "expected"],
    [
        pytest.param(
            api_v1.rule_specs.CheckParameters(
                name="test_rulespec",
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                parameter_form=partial(
                    api_v1.form_specs.Dictionary,
                    elements={
                        "key": api_v1.form_specs.DictElement(
                            parameter_form=api_v1.form_specs.ServiceState(
                                title=api_v1.Title("valuespec title")
                            )
                        ),
                    },
                ),
                condition=api_v1.rule_specs.HostAndItemCondition(
                    item_title=api_v1.Title("item title")
                ),
                help_text=api_v1.Help("help text"),
            ),
            legacy_rulespecs.CheckParameterRulespecWithItem(
                check_group_name="test_rulespec",
                group=legacy_rulespec_groups.RulespecGroupCheckParametersApplications,
                title=lambda: _("rulespec title"),
                item_spec=lambda: legacy_valuespecs.TextInput(
                    title=_("item title"), allow_empty=False
                ),
                parameter_valuespec=lambda: legacy_valuespecs.Transform(
                    legacy_valuespecs.Dictionary(
                        elements=[
                            ("key", legacy_valuespecs.MonitoringState(title=_("valuespec title")))
                        ],
                    )
                ),
                match_type="dict",
                create_manual_check=False,
            ),
            id="CheckParameterRuleSpec with HostAndItemCondition",
        ),
        pytest.param(
            api_v1.rule_specs.CheckParameters(
                name="test_rulespec",
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                parameter_form=partial(
                    api_v1.form_specs.Dictionary,
                    elements={
                        "key": api_v1.form_specs.DictElement(
                            parameter_form=api_v1.form_specs.ServiceState(
                                title=api_v1.Title("valuespec title")
                            )
                        ),
                    },
                ),
                condition=api_v1.rule_specs.HostCondition(),
                help_text=api_v1.Help("help text"),
            ),
            legacy_rulespecs.CheckParameterRulespecWithoutItem(
                check_group_name="test_rulespec",
                group=legacy_rulespec_groups.RulespecGroupCheckParametersApplications,
                title=lambda: _("rulespec title"),
                parameter_valuespec=lambda: legacy_valuespecs.Transform(
                    legacy_valuespecs.Dictionary(
                        elements=[
                            ("key", legacy_valuespecs.MonitoringState(title=_("valuespec title")))
                        ],
                    )
                ),
                match_type="dict",
                create_manual_check=False,
            ),
            id="CheckParameterRuleSpec with HostCondition",
        ),
        pytest.param(
            api_v1.rule_specs.EnforcedService(
                name="test_rulespec",
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                parameter_form=partial(
                    api_v1.form_specs.Dictionary,
                    elements={
                        "key": api_v1.form_specs.DictElement(
                            parameter_form=api_v1.form_specs.ServiceState(
                                title=api_v1.Title("valuespec title")
                            )
                        ),
                    },
                ),
                condition=api_v1.rule_specs.HostAndItemCondition(
                    item_title=api_v1.Title("item title")
                ),
                help_text=api_v1.Help("help text"),
            ),
            legacy_rulespecs.ManualCheckParameterRulespec(
                check_group_name="test_rulespec",
                group=legacy_rulespec_groups.RulespecGroupEnforcedServicesApplications,
                title=lambda: _("rulespec title"),
                item_spec=lambda: legacy_valuespecs.TextInput(
                    size=35,
                    title=_("item title"),
                    placeholder="",
                    allow_empty=False,
                    empty_text=_("The minimum allowed length is 1."),
                    validate=lambda x, y: None,  # text only checks it's not None.
                ),
                parameter_valuespec=lambda: legacy_valuespecs.Transform(
                    legacy_valuespecs.Dictionary(
                        elements=[
                            ("key", legacy_valuespecs.MonitoringState(title=_("valuespec title")))
                        ],
                    )
                ),
                match_type="all",
            ),
            id="EnforcedServiceRuleSpec with HostAndItemCondition",
        ),
        pytest.param(
            api_v1.rule_specs.EnforcedService(
                name="test_rulespec",
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                parameter_form=None,
                condition=api_v1.rule_specs.HostAndItemCondition(
                    item_title=api_v1.Title("item title")
                ),
                help_text=api_v1.Help("help text"),
            ),
            legacy_rulespecs.ManualCheckParameterRulespec(
                check_group_name="test_rulespec",
                group=legacy_rulespec_groups.RulespecGroupEnforcedServicesApplications,
                title=lambda: _("rulespec title"),
                item_spec=lambda: legacy_valuespecs.TextInput(
                    size=35,
                    title=_("item title"),
                    placeholder="",
                    allow_empty=False,
                    empty_text=_("The minimum allowed length is 1."),
                    validate=lambda x, y: None,  # text only checks it's not None.
                ),
                parameter_valuespec=None,
                match_type="all",
            ),
            id="EnforcedServiceRuleSpec with HostAndItemCondition no parameters",
        ),
        pytest.param(
            api_v1.rule_specs.EnforcedService(
                name="test_rulespec",
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                parameter_form=partial(
                    api_v1.form_specs.Dictionary,
                    elements={
                        "key": api_v1.form_specs.DictElement(
                            parameter_form=api_v1.form_specs.ServiceState(
                                title=api_v1.Title("valuespec title")
                            )
                        ),
                    },
                ),
                condition=api_v1.rule_specs.HostCondition(),
                help_text=api_v1.Help("help text"),
            ),
            legacy_rulespecs.ManualCheckParameterRulespec(
                check_group_name="test_rulespec",
                group=legacy_rulespec_groups.RulespecGroupEnforcedServicesApplications,
                title=lambda: _("rulespec title"),
                parameter_valuespec=lambda: legacy_valuespecs.Transform(
                    legacy_valuespecs.Dictionary(
                        elements=[
                            ("key", legacy_valuespecs.MonitoringState(title=_("valuespec title")))
                        ],
                    )
                ),
                match_type="all",
            ),
            id="EnforcedServiceRuleSpec with HostCondition",
        ),
        pytest.param(
            api_v1.rule_specs.EnforcedService(
                name="test_rulespec",
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                parameter_form=None,
                condition=api_v1.rule_specs.HostCondition(),
                help_text=api_v1.Help("help text"),
            ),
            legacy_rulespecs.ManualCheckParameterRulespec(
                check_group_name="test_rulespec",
                group=legacy_rulespec_groups.RulespecGroupEnforcedServicesApplications,
                title=lambda: _("rulespec title"),
                parameter_valuespec=None,
                match_type="all",
            ),
            id="EnforcedServiceRuleSpec with HostCondition no parameters",
        ),
        pytest.param(
            api_v1.rule_specs.ActiveCheck(
                name="test_rulespec",
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                parameter_form=lambda: api_v1.form_specs.Dictionary(elements={}),
                help_text=api_v1.Help("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name=RuleGroup.ActiveChecks("test_rulespec"),
                group=_to_generated_builtin_sub_group(
                    legacy_rulespec_groups.RulespecGroupActiveChecks,
                    "Applications",
                    lambda x: x,
                ),
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="all",
            ),
            id="ActiveCheckRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.AgentAccess(
                name="test_rulespec",
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=lambda: api_v1.form_specs.Dictionary(elements={}),
                help_text=api_v1.Help("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name="test_rulespec",
                group=_to_generated_builtin_sub_group(
                    legacy_rulespec_groups.RulespecGroupAgent,
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
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.GENERAL,
                parameter_form=lambda: api_v1.form_specs.Dictionary(elements={}),
                help_text=api_v1.Help("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name=RuleGroup.AgentConfig("test_rulespec"),
                group=legacy_rulespec_groups.RulespecGroupMonitoringAgentsGenericOptions,
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="AgentConfigRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.Host(
                name="test_rulespec",
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.NOTIFICATIONS,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=lambda: api_v1.form_specs.Dictionary(elements={}),
                help_text=api_v1.Help("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name="test_rulespec",
                group=legacy_rulespec_groups.RulespecGroupHostsMonitoringRulesNotifications,
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="HostRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.InventoryParameters(
                name="test_rulespec",
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                parameter_form=lambda: api_v1.form_specs.Dictionary(elements={}),
                help_text=api_v1.Help("help text"),
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
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.NOTIFICATIONS,
                parameter_form=lambda: api_v1.form_specs.Dictionary(elements={}),
                help_text=api_v1.Help("help text"),
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
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.APPLICATIONS,
                parameter_form=lambda: api_v1.form_specs.Dictionary(elements={}),
                help_text=api_v1.Help("help text"),
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
                match_type="varies",
            ),
            id="ServiceDiscoveryRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.Service(
                name="test_rulespec",
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.NOTIFICATIONS,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=lambda: api_v1.form_specs.Dictionary(elements={}),
                condition=api_v1.rule_specs.HostCondition(),
                help_text=api_v1.Help("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name="test_rulespec",
                group=legacy_rulespec_groups.RulespecGroupMonitoringConfigurationNotifications,
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="ServiceRuleSpec with HostCondition",
        ),
        pytest.param(
            api_v1.rule_specs.Service(
                name="test_rulespec",
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.VIRTUALIZATION,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=lambda: api_v1.form_specs.Dictionary(elements={}),
                condition=api_v1.rule_specs.HostAndServiceCondition(),
                help_text=api_v1.Help("help text"),
            ),
            legacy_rulespecs.ServiceRulespec(
                name="test_rulespec",
                item_type="service",
                group=legacy_rulespec_groups.RulespecGroupCheckParametersVirtualization,
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="dict",
            ),
            id="ServiceRuleSpec with HostAndServiceCondition",
        ),
        pytest.param(
            api_v1.rule_specs.SNMP(
                name="test_rulespec",
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.SERVER_HARDWARE,
                eval_type=api_v1.rule_specs.EvalType.MERGE,
                parameter_form=lambda: api_v1.form_specs.Dictionary(elements={}),
                help_text=api_v1.Help("help text"),
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
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.CLOUD,
                parameter_form=lambda: api_v1.form_specs.Dictionary(elements={}),
                help_text=api_v1.Help("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name=RuleGroup.SpecialAgents("test_rulespec"),
                group=legacy_rulespec_groups.RulespecGroupVMCloudContainer,
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="first",
            ),
            id="SpecialAgentRuleSpec",
        ),
        pytest.param(
            api_v1.rule_specs.SpecialAgent(
                name="gcp",
                title=api_v1.Title("rulespec title"),
                topic=api_v1.rule_specs.Topic.CLOUD,
                parameter_form=lambda: api_v1.form_specs.Dictionary(elements={}),
                help_text=api_v1.Help("help text"),
            ),
            legacy_rulespecs.HostRulespec(
                name=RuleGroup.SpecialAgents("gcp"),
                group=legacy_rulespec_groups.RulespecGroupVMCloudContainer,
                title=lambda: _("rulespec title"),
                valuespec=partial(legacy_valuespecs.TextInput),
                match_type="first",
                doc_references={DocReference.GCP: _("Monitoring Google Cloud Platform (GCP)")},
            ),
            id="RuleSpec with doc_references",
        ),
    ],
)
def test_convert_to_legacy_rulespec(
    new_rulespec: APIV1RuleSpec, expected: legacy_rulespecs.Rulespec
) -> None:
    _compare_specs(
        convert_to_legacy_rulespec(new_rulespec, Edition.COMMUNITY, translate_to_current_language),
        expected,
    )


def _compare_specs(actual: object, expected: object) -> None:
    # The form_spec fields are only available if the rulespec uses a form_spec
    ignored_attrs = {
        "__orig_class__",
        "_form_spec_definition",
    }

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
        if attr in [
            "_custom_validate",
            "_validate",
            "_render_function",
            "to_valuespec",
            "from_valuespec",
        ]:
            # testing the equality of the validation in a generic way seems very difficult
            #  check that the field was set during conversion and test behavior separately
            assert (actual_value is not None) is (expected_value is not None)
            continue

        if not callable(expected_value):
            _compare_specs(actual_value, expected_value)
            continue

        # cached access to the password store
        if "ThreadLocalLRUCache" in str(actual_value):
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
    elif isinstance(expected, legacy_rulespecs.RulespecGroup):
        assert isinstance(actual, legacy_rulespecs.RulespecGroup)
        assert expected.choice_title == actual.choice_title
        assert expected.help == actual.help
        assert expected.name == actual.name
        assert expected.title == actual.title
    else:
        raise NotImplementedError()


def test_generated_rulespec_group_single_registration():
    first_group = _convert_to_custom_group(
        legacy_rulespec_groups.RulespecGroupMonitoringConfiguration,
        api_v1.Title("test"),
        lambda x: x,
    )
    second_group = _convert_to_custom_group(
        legacy_rulespec_groups.RulespecGroupMonitoringConfiguration,
        api_v1.Title("test"),
        lambda x: x,
    )
    assert first_group == second_group


@pytest.mark.parametrize(
    ["input_value", "validate"],
    [
        pytest.param("admin", (_v1_custom_text_validate,), id="custom validation"),
        pytest.param(
            "",
            (
                api_v1.form_specs.validators.LengthInRange(
                    min_value=1, error_msg=api_v1.Message("Fill this")
                ),
            ),
            id="empty validation",
        ),
        pytest.param(
            ".",
            (
                api_v1.form_specs.validators.MatchRegex(
                    regex=r"^[^.\r\n]+$", error_msg=api_v1.Message("No dot allowed")
                ),
            ),
            id="regex validation",
        ),
    ],
)
def test_convert_validation(
    input_value: str, validate: tuple[Callable[[str], object], ...]
) -> None:
    converted_spec = convert_to_legacy_valuespec(
        api_v1.form_specs.String(custom_validate=validate),
        translate_to_current_language,
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
    ["bounds", "input_value", "value_is_valid"],
    [
        pytest.param((0, 100), 50, True, id="valid value"),
        pytest.param((0, None), 200, True, id="valid value without max"),
        pytest.param((None, 100), -1, True, id="valid value without min"),
        pytest.param((0, 100), 101, False, id="invalid value above upper bound"),
        pytest.param((0, 100), -1, False, id="invalid value below lower bound"),
    ],
)
def test_percentage_validation(
    bounds: tuple[float | None, float | None], input_value: float, value_is_valid: bool
) -> None:
    converted_spec = convert_to_legacy_valuespec(
        api_v1.form_specs.Percentage(
            custom_validate=[
                api_v1.form_specs.validators.NumberInRange(min_value=bounds[0], max_value=bounds[1])
            ]
        ),
        translate_to_current_language,
    )

    expected_spec = legacy_valuespecs.Percentage(
        display_format="%r", minvalue=bounds[0], maxvalue=bounds[1]
    )

    test_args = (input_value, "var_prefix")
    if value_is_valid:
        expected_spec.validate_value(*test_args)
        converted_spec.validate_value(*test_args)
    else:
        with pytest.raises(MKUserError):
            expected_spec.validate_value(*test_args)

        with pytest.raises(MKUserError):
            converted_spec.validate_value(*test_args)


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
        api_v1.form_specs.validators.LengthInRange(
            min_value=1, error_msg=api_v1.Message("Empty list")
        )(value)

        if len(value) > 2:
            raise api_v1.form_specs.validators.ValidationError(
                api_v1.Message("Max number of elements exceeded")
            )

        if len(set(value)) != len(value):
            raise api_v1.form_specs.validators.ValidationError(api_v1.Message("Duplicate elements"))

    v1_api_list = api_v1.form_specs.List(
        element_template=api_v1.form_specs.String(),
        custom_validate=(_v1_custom_list_validate,),
    )

    legacy_list = convert_to_legacy_valuespec(v1_api_list, translate_to_current_language)

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
            api_v1.form_specs.Integer(migrate=lambda x: _narrow_type(x, int) * 2),
            2,
            4,
            id="integer migration",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "key2": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer()
                    )
                },
                migrate=lambda x: {"key2": _narrow_type(x, dict)["key"]},
            ),
            {"key": 2},
            {"key2": 2},
            id="migrate top level element",
        ),
        pytest.param(
            api_v1.form_specs.CascadingSingleChoice(
                elements=[
                    api_v1.form_specs.CascadingSingleChoiceElement(
                        name="key_new",
                        title=api_v1.Title("Spec title"),
                        parameter_form=api_v1.form_specs.String(migrate=lambda x: f"{x}_new"),
                    )
                ],
                migrate=lambda x: (
                    f"{_narrow_type(x, tuple)[0]}_new",
                    _narrow_type(x, tuple)[1],
                ),
            ),
            ("key", "value"),
            ("key_new", "value_new"),
            id="migrate nested and top level element",
        ),
        pytest.param(
            api_v1.form_specs.CascadingSingleChoice(
                elements=[
                    api_v1.form_specs.CascadingSingleChoiceElement(
                        name="key_new",
                        title=api_v1.Title("Spec title"),
                        parameter_form=api_v1.form_specs.FixedValue(value=None),
                    )
                ],
                migrate=lambda x: ("key_new", None),
            ),
            None,
            ("key_new", None),
            id="migrate from `None` (Alterative + FixedValue(None))",
        ),
    ],
)
def test_migrate(
    parameter_form: FormSpec,
    old_value: object,
    expected_transformed_value: object,
) -> None:
    legacy_valuespec = convert_to_legacy_valuespec(parameter_form, localizer=lambda x: x)
    actual_transformed_value = legacy_valuespec.transform_value(value=old_value)
    assert expected_transformed_value == actual_transformed_value


def _exposed_form_specs() -> Sequence[FormSpec]:
    return [
        api_v1.form_specs.Integer(),
        api_v1.form_specs.Float(),
        api_v1.form_specs.DataSize(displayed_magnitudes=tuple(api_v1.form_specs.IECMagnitude)),
        api_v1.form_specs.Percentage(),
        api_v1.form_specs.String(),
        api_v1.form_specs.Dictionary(elements={}),
        api_v1.form_specs.SingleChoice(
            elements=[
                api_v1.form_specs.SingleChoiceElement(
                    name="foo",
                    title=api_v1.Title("Whatever"),
                ),
            ],
            prefill=api_v1.form_specs.DefaultValue("foo"),
        ),
        api_v1.form_specs.CascadingSingleChoice(elements=[]),
        api_v1.form_specs.ServiceState(),
        api_v1.form_specs.HostState(),
        api_v1.form_specs.List(element_template=api_v1.form_specs.Integer()),
        api_v1.form_specs.FixedValue(value=None),
        api_v1.form_specs.TimeSpan(displayed_magnitudes=tuple(api_v1.form_specs.TimeMagnitude)),
        api_v1.form_specs.SimpleLevels(
            level_direction=api_v1.form_specs.LevelDirection.UPPER,
            form_spec_template=api_v1.form_specs.Integer(),
            prefill_fixed_levels=api_v1.form_specs.DefaultValue((23.0, 42.0)),
        ),
        api_v1.form_specs.Levels(
            level_direction=api_v1.form_specs.LevelDirection.UPPER,
            predictive=api_v1.form_specs.PredictiveLevels(
                reference_metric="my_metric",
                prefill_abs_diff=api_v1.form_specs.DefaultValue((1.0, 2.0)),
            ),
            form_spec_template=api_v1.form_specs.Integer(),
            prefill_fixed_levels=api_v1.form_specs.DefaultValue((23.0, 42.0)),
        ),
        api_v1.form_specs.BooleanChoice(),
        api_v1.form_specs.FileUpload(),
        api_v1.form_specs.Proxy(),
        api_v1.form_specs.Metric(),
        api_v1.form_specs.MonitoredHost(),
        api_v1.form_specs.MonitoredService(),
        api_v1.form_specs.Password(),
        api_v1.form_specs.RegularExpression(
            predefined_help_text=api_v1.form_specs.MatchingScope.FULL
        ),
    ]


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
            api_v1.form_specs.SimpleLevels(
                title=api_v1.Title("Lower levels"),
                help_text=api_v1.Help("This is an explanation for lower levels"),
                form_spec_template=api_v1.form_specs.Integer(),
                level_direction=api_v1.form_specs.LevelDirection.LOWER,
                prefill_fixed_levels=api_v1.form_specs.DefaultValue((1, 2)),
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.CascadingDropdown(
                    title=_("Lower levels"),
                    help=_("This is an explanation for lower levels"),
                    choices=[
                        _get_legacy_no_levels_choice(),
                        _get_legacy_fixed_levels_choice("below"),
                    ],
                    default_value=("fixed", (1, 2)),
                ),
            ),
            id="lower fixed",
        ),
        pytest.param(
            api_v1.form_specs.SimpleLevels(
                form_spec_template=api_v1.form_specs.Integer(),
                level_direction=api_v1.form_specs.LevelDirection.UPPER,
                prefill_fixed_levels=api_v1.form_specs.DefaultValue((1, 2)),
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.CascadingDropdown(
                    choices=[
                        _get_legacy_no_levels_choice(),
                        _get_legacy_fixed_levels_choice("at"),
                    ],
                    default_value=("fixed", (1, 2)),
                ),
            ),
            id="upper fixed",
        ),
        pytest.param(
            api_v1.form_specs.SimpleLevels[float](
                title=api_v1.Title("Cast to super type float"),
                form_spec_template=api_v1.form_specs.TimeSpan(
                    displayed_magnitudes=[api_v1.form_specs.TimeMagnitude.SECOND]
                ),
                level_direction=api_v1.form_specs.LevelDirection.LOWER,
                prefill_fixed_levels=api_v1.form_specs.DefaultValue((1, 2)),
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.CascadingDropdown(
                    title=_("Cast to super type float"),
                    choices=(
                        _get_legacy_no_levels_choice(),
                        (
                            "fixed",
                            _("Fixed levels"),
                            legacy_valuespecs.Tuple(
                                elements=[
                                    legacy_valuespecs.TimeSpan(
                                        title=_("Warning below"),
                                        default_value=1,
                                        display=["seconds"],
                                    ),
                                    legacy_valuespecs.TimeSpan(
                                        title=_("Critical below"),
                                        default_value=2,
                                        display=["seconds"],
                                    ),
                                ],
                            ),
                        ),
                    ),
                    default_value=("fixed", (1.0, 2.0)),
                ),
            ),
            # mypy allows passing integers where a float is expected. We cast these to float, "
            # so that CascadingDropdown does not complain.",
            id="cast_to_float",
        ),
        pytest.param(
            api_v1.form_specs.Levels[int](
                title=api_v1.Title("Upper levels"),
                help_text=api_v1.Help("This is an explanation for upper levels"),
                form_spec_template=api_v1.form_specs.Integer(
                    title=api_v1.Title("I will be ignored"),
                    help_text=api_v1.Help("This is an explanation for a specific value"),
                    label=api_v1.Label("This is a label"),
                    unit_symbol="GiB",
                    prefill=api_v1.form_specs.DefaultValue(-1111),
                ),
                level_direction=api_v1.form_specs.LevelDirection.UPPER,
                prefill_fixed_levels=api_v1.form_specs.DefaultValue((1, 2)),
                predictive=api_v1.form_specs.PredictiveLevels(
                    reference_metric="my_metric",
                    prefill_abs_diff=api_v1.form_specs.DefaultValue((5, 10)),
                    prefill_rel_diff=api_v1.form_specs.DefaultValue((50.0, 80.0)),
                    prefill_stdev_diff=api_v1.form_specs.DefaultValue((2.0, 3.0)),
                ),
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.CascadingDropdown(
                    title=_("Upper levels"),
                    help=_("This is an explanation for upper levels"),
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
                                        help=_("This is an explanation for a specific value"),
                                        label=_("This is a label"),
                                    ),
                                    legacy_valuespecs.Integer(
                                        title=_("Critical at"),
                                        default_value=2,
                                        unit="GiB",
                                        help=_("This is an explanation for a specific value"),
                                        label=_("This is a label"),
                                    ),
                                ],
                            ),
                        ),
                        (
                            "predictive",
                            _("Predictive levels (only on CMC)"),
                            legacy_valuespecs.Transform(
                                valuespec=legacy_valuespecs.Dictionary(
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
                                                                    help=_(
                                                                        "This is an explanation for a specific value"
                                                                    ),
                                                                    label=_("This is a label"),
                                                                ),
                                                                legacy_valuespecs.Integer(
                                                                    title=_("Critical above"),
                                                                    unit="GiB",
                                                                    default_value=10,
                                                                    help=_(
                                                                        "This is an explanation for a specific value"
                                                                    ),
                                                                    label=_("This is a label"),
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
                                                        "stdev",
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
                                            legacy_valuespecs.Optional(
                                                title=_("Fixed limits"),
                                                label=_("Set fixed limits"),
                                                valuespec=legacy_valuespecs.Tuple(
                                                    help=_(
                                                        "Regardless of how the dynamic levels are computed according to the prediction: they will never be set below the following limits. This avoids false alarms during times where the predicted levels would be very low."
                                                    ),
                                                    elements=[
                                                        legacy_valuespecs.Integer(
                                                            title="Warning level is at least",
                                                            unit="GiB",
                                                            help=_(
                                                                "This is an explanation for a specific value"
                                                            ),
                                                            label=_("This is a label"),
                                                        ),
                                                        legacy_valuespecs.Integer(
                                                            title="Critical level is at least",
                                                            unit="GiB",
                                                            help=_(
                                                                "This is an explanation for a specific value"
                                                            ),
                                                            label=_("This is a label"),
                                                        ),
                                                    ],
                                                ),
                                            ),
                                        ),
                                    ],
                                    required_keys=["period", "horizon", "levels", "bound"],
                                ),
                                to_valuespec=lambda x: x,
                                from_valuespec=lambda x: x,
                            ),
                        ),
                    ),
                    default_value=("fixed", (1, 2)),
                ),
            ),
            id="fixed+predictive Integer",
        ),
        pytest.param(
            api_v1.form_specs.Levels(
                form_spec_template=api_v1.form_specs.TimeSpan(
                    displayed_magnitudes=[
                        api_v1.form_specs.TimeMagnitude.SECOND,
                        api_v1.form_specs.TimeMagnitude.MINUTE,
                    ]
                ),
                level_direction=api_v1.form_specs.LevelDirection.LOWER,
                prefill_fixed_levels=api_v1.form_specs.DefaultValue((1.0, 2.0)),
                predictive=api_v1.form_specs.PredictiveLevels(
                    reference_metric="my_metric",
                    prefill_abs_diff=api_v1.form_specs.DefaultValue((5.0, 10.0)),
                    prefill_rel_diff=api_v1.form_specs.DefaultValue((50.0, 80.0)),
                    prefill_stdev_diff=api_v1.form_specs.DefaultValue((2.0, 3.0)),
                ),
                title=api_v1.Title("Lower levels"),
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.CascadingDropdown(
                    title=_("Lower levels"),
                    choices=(
                        _get_legacy_no_levels_choice(),
                        (
                            "fixed",
                            _("Fixed levels"),
                            legacy_valuespecs.Tuple(
                                elements=[
                                    legacy_valuespecs.TimeSpan(
                                        title=_("Warning below"),
                                        default_value=1,
                                        display=["seconds", "minutes"],
                                    ),
                                    legacy_valuespecs.TimeSpan(
                                        title=_("Critical below"),
                                        default_value=2,
                                        display=["seconds", "minutes"],
                                    ),
                                ],
                            ),
                        ),
                        (
                            "predictive",
                            _("Predictive levels (only on CMC)"),
                            legacy_valuespecs.Transform(
                                valuespec=legacy_valuespecs.Dictionary(
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
                                                                legacy_valuespecs.TimeSpan(
                                                                    title=_("Warning below"),
                                                                    display=["seconds", "minutes"],
                                                                    default_value=5,
                                                                ),
                                                                legacy_valuespecs.TimeSpan(
                                                                    title=_("Critical below"),
                                                                    display=["seconds", "minutes"],
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
                                                                    title=_("Warning below"),
                                                                    unit="%",
                                                                    default_value=50.0,
                                                                ),
                                                                legacy_valuespecs.Percentage(
                                                                    title=_("Critical below"),
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
                                                        "stdev",
                                                        _("Standard deviation difference"),
                                                        legacy_valuespecs.Tuple(
                                                            elements=[
                                                                legacy_valuespecs.Float(
                                                                    title=_("Warning below"),
                                                                    unit=_(
                                                                        "times the standard deviation"
                                                                    ),
                                                                    default_value=2.0,
                                                                ),
                                                                legacy_valuespecs.Float(
                                                                    title=_("Critical below"),
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
                                            legacy_valuespecs.Optional(
                                                title=_("Fixed limits"),
                                                label=_("Set fixed limits"),
                                                valuespec=legacy_valuespecs.Tuple(
                                                    help=_(
                                                        "Regardless of how the dynamic levels are computed according to the prediction: they will never be set above the following limits. This avoids false alarms during times where the predicted levels would be very high."
                                                    ),
                                                    elements=[
                                                        legacy_valuespecs.TimeSpan(
                                                            title="Warning level is at most",
                                                            display=["seconds", "minutes"],
                                                        ),
                                                        legacy_valuespecs.TimeSpan(
                                                            title="Critical level is at most",
                                                            display=["seconds", "minutes"],
                                                        ),
                                                    ],
                                                ),
                                            ),
                                        ),
                                    ],
                                    required_keys=["period", "horizon", "levels", "bound"],
                                ),
                                to_valuespec=lambda x: x,
                                from_valuespec=lambda x: x,
                            ),
                        ),
                    ),
                    default_value=("fixed", (1, 2)),
                ),
            ),
            id="fixed+predictive TimeSpan",
        ),
    ],
)
def test_level_conversion(
    api_levels: api_v1.form_specs.Levels,
    legacy_levels: legacy_valuespecs.Dictionary,
) -> None:
    _compare_specs(
        _convert_to_legacy_levels(api_levels, translate_to_current_language), legacy_levels
    )


def test_levels_formspec_template_custom_validate() -> None:
    api_v1_levels = api_v1.form_specs.SimpleLevels(
        form_spec_template=api_v1.form_specs.Float(
            custom_validate=(api_v1.form_specs.validators.NumberInRange(0, None),)
        ),
        level_direction=api_v1.form_specs.LevelDirection.UPPER,
        prefill_fixed_levels=api_v1.form_specs.DefaultValue((23.0, 42.0)),
    )
    legacy_levels = convert_to_legacy_valuespec(api_v1_levels, translate_to_current_language)
    with pytest.raises(MKUserError, match="The minimum allowed value is 0"):
        legacy_levels.validate_value(("fixed", (-10.0, -5.0)), "var_prefix")


def test_simple_levels_custom_validate() -> None:
    def _simple_levels_example_validator(
        x: api_v1.form_specs.SimpleLevelsConfigModel[float],
    ) -> None:
        match x:
            case ("fixed", (float(warn), float(crit))):
                if warn > crit:
                    raise api_v1.form_specs.validators.ValidationError(
                        message=api_v1.Message("Warning level must be lower than critical level")
                    )
            case _:
                pass

    api_v1_levels = api_v1.form_specs.SimpleLevels(
        form_spec_template=api_v1.form_specs.Float(),
        level_direction=api_v1.form_specs.LevelDirection.UPPER,
        prefill_fixed_levels=api_v1.form_specs.DefaultValue((23.0, 42.0)),
        custom_validate=(_simple_levels_example_validator,),
    )
    legacy_levels = convert_to_legacy_valuespec(api_v1_levels, translate_to_current_language)
    with pytest.raises(MKUserError, match="Warning level must be lower than critical level"):
        legacy_levels.validate_value(("fixed", (10.0, 5.0)), "var_prefix")


def test_levels_custom_validate() -> None:
    def _levels_example_validator(x: api_v1.form_specs.LevelsConfigModel[float]) -> None:
        match x:
            case ("fixed", (float(warn), float(crit))):
                if warn > crit:
                    raise api_v1.form_specs.validators.ValidationError(
                        message=api_v1.Message("Warning level must be lower than critical level")
                    )
            case _:
                pass

    api_v1_levels = api_v1.form_specs.Levels(
        form_spec_template=api_v1.form_specs.Float(),
        level_direction=api_v1.form_specs.LevelDirection.UPPER,
        prefill_fixed_levels=api_v1.form_specs.DefaultValue((23.0, 42.0)),
        predictive=api_v1.form_specs.PredictiveLevels(
            reference_metric="my_metric",
            prefill_abs_diff=api_v1.form_specs.DefaultValue((5.0, 10.0)),
            prefill_rel_diff=api_v1.form_specs.DefaultValue((10.0, 20.0)),
            prefill_stdev_diff=api_v1.form_specs.DefaultValue((2.0, 4.0)),
        ),
        custom_validate=(_levels_example_validator,),
    )
    legacy_levels = convert_to_legacy_valuespec(api_v1_levels, translate_to_current_language)

    with pytest.raises(MKUserError, match="Warning level must be lower than critical level"):
        legacy_levels.validate_value(("fixed", (10.0, 5.0)), "var_prefix")


@pytest.mark.parametrize(
    ["input_elements", "consumer_model", "form_model"],
    [
        pytest.param(
            {
                "a": api_v1.form_specs.DictElement(
                    parameter_form=api_v1.form_specs.Integer(),
                    group=api_v1.form_specs.DictGroup(title=api_v1.Title("Group title")),
                ),
                "b": api_v1.form_specs.DictElement(
                    parameter_form=api_v1.form_specs.Integer(),
                    group=api_v1.form_specs.DictGroup(title=api_v1.Title("Group title")),
                ),
                "c": api_v1.form_specs.DictElement(
                    parameter_form=api_v1.form_specs.Integer(),
                ),
            },
            {"a": 1, "b": 2, "c": 3},
            {"DictGrouptitleTitleGrouptitlehelptextNone": {"a": 1, "b": 2}, "c": 3},
            id="some elements grouped, some not",
        ),
        pytest.param(
            {
                "a": api_v1.form_specs.DictElement(
                    parameter_form=api_v1.form_specs.Integer(),
                    group=api_v1.form_specs.DictGroup(title=api_v1.Title("Group title")),
                ),
                "b": api_v1.form_specs.DictElement(
                    parameter_form=api_v1.form_specs.Integer(),
                    group=api_v1.form_specs.DictGroup(
                        title=api_v1.Title("Group title"),
                        help_text=api_v1.Help("Help text"),
                    ),
                ),
            },
            {"a": 1, "b": 2},
            {
                "DictGrouptitleTitleGrouptitlehelptextNone": {"a": 1},
                "DictGrouptitleTitleGrouptitlehelptextHelpHelptext": {"b": 2},
            },
            id="different groups",
        ),
        pytest.param(
            {
                "a": api_v1.form_specs.DictElement(
                    parameter_form=api_v1.form_specs.Integer(),
                    group=api_v1.form_specs.DictGroup(title=api_v1.Title("Group title")),
                ),
                "b": api_v1.form_specs.DictElement(
                    parameter_form=api_v1.form_specs.Dictionary(
                        elements={
                            "a_nested": api_v1.form_specs.DictElement(
                                parameter_form=api_v1.form_specs.Integer(),
                                group=api_v1.form_specs.DictGroup(
                                    title=api_v1.Title("Nested group title")
                                ),
                            ),
                            "b_nested": api_v1.form_specs.DictElement(
                                parameter_form=api_v1.form_specs.Integer(),
                                group=api_v1.form_specs.DictGroup(
                                    title=api_v1.Title("Nested group title")
                                ),
                            ),
                            "c_nested": api_v1.form_specs.DictElement(
                                parameter_form=api_v1.form_specs.Integer(),
                            ),
                        }
                    ),
                    group=api_v1.form_specs.DictGroup(title=api_v1.Title("Group title")),
                ),
            },
            {"a": 1, "b": {"a_nested": 2, "b_nested": 3, "c_nested": 4}},
            {
                "DictGrouptitleTitleGrouptitlehelptextNone": {
                    "a": 1,
                    "b": {
                        "DictGrouptitleTitleNestedgrouptitlehelptextNone": {
                            "a_nested": 2,
                            "b_nested": 3,
                        },
                        "c_nested": 4,
                    },
                },
            },
            id="groups in nested dictionary",
        ),
    ],
)
def test_dictionary_groups_datamodel_transformation(
    input_elements: Mapping[str, api_v1.form_specs.DictElement],
    consumer_model: Mapping[str, object],
    form_model: Mapping[str, object],
) -> None:
    to_convert = api_v1.form_specs.Dictionary(elements=input_elements)

    converted = convert_to_legacy_valuespec(to_convert, translate_to_current_language)
    assert isinstance(converted, legacy_valuespecs.Transform)

    assert converted.to_valuespec(consumer_model) == form_model
    assert converted.from_valuespec(form_model) == consumer_model


def test_dictionary_groups_ignored_elements() -> None:
    to_convert = api_v1.form_specs.Dictionary(
        elements={
            "a": api_v1.form_specs.DictElement(
                parameter_form=api_v1.form_specs.Integer(),
                group=api_v1.form_specs.DictGroup(title=api_v1.Title("Group title")),
            ),
            "b": api_v1.form_specs.DictElement(
                parameter_form=api_v1.form_specs.Dictionary(
                    elements={
                        "a_nested": api_v1.form_specs.DictElement(
                            parameter_form=api_v1.form_specs.Integer(),
                            group=api_v1.form_specs.DictGroup(
                                title=api_v1.Title("Nested group title")
                            ),
                        ),
                        "b_nested": api_v1.form_specs.DictElement(
                            parameter_form=api_v1.form_specs.Integer(),
                            group=api_v1.form_specs.DictGroup(
                                title=api_v1.Title("Nested group title")
                            ),
                        ),
                        "c_nested": api_v1.form_specs.DictElement(
                            parameter_form=api_v1.form_specs.Integer(),
                        ),
                    },
                    ignored_elements=("d_nested",),
                ),
                group=api_v1.form_specs.DictGroup(title=api_v1.Title("Group title")),
            ),
        },
        ignored_elements=("c",),
    )
    consumer_model = {
        "a": 1,
        "b": {"a_nested": 2, "b_nested": 3, "c_nested": 4, "d_nested": 5},
        "c": 6,
    }
    form_model = {
        "DictGrouptitleTitleGrouptitlehelptextNone": {
            "a": 1,
            "b": {
                "DictGrouptitleTitleNestedgrouptitlehelptextNone": {
                    "a_nested": 2,
                    "b_nested": 3,
                },
                "c_nested": 4,
                "d_nested": 5,
            },
        },
        "c": 6,
    }

    converted = convert_to_legacy_valuespec(to_convert, translate_to_current_language)
    assert isinstance(converted, legacy_valuespecs.Transform)

    assert converted.to_valuespec(consumer_model) == form_model
    assert converted.from_valuespec(form_model) == consumer_model


@pytest.mark.parametrize(
    ["to_convert", "expected"],
    [
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "a": api_v1.form_specs.DictElement(parameter_form=api_v1.form_specs.Integer()),
                    "b": api_v1.form_specs.DictElement(parameter_form=api_v1.form_specs.Integer()),
                }
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.Dictionary(
                    elements=[
                        ("a", legacy_valuespecs.Integer()),
                        ("b", legacy_valuespecs.Integer()),
                    ]
                )
            ),
            id="no groups/dictelement props",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "a": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                    ),
                    "b": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                    ),
                }
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.Dictionary(
                    elements=[
                        (
                            "DictGrouptitleTitleABChelptextNone",
                            legacy_valuespecs.Dictionary(
                                title=_("ABC"),
                                elements=[
                                    ("a", legacy_valuespecs.Integer()),
                                    ("b", legacy_valuespecs.Integer()),
                                ],
                            ),
                        ),
                    ],
                    required_keys=["DictGrouptitleTitleABChelptextNone"],
                ),
            ),
            id="no dictelement props",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "a": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                        required=False,
                    ),
                    "b": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                        required=True,
                    ),
                }
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.Dictionary(
                    elements=[
                        (
                            "DictGrouptitleTitleABChelptextNone",
                            legacy_valuespecs.Dictionary(
                                title=_("ABC"),
                                elements=[
                                    ("a", legacy_valuespecs.Integer()),
                                    ("b", legacy_valuespecs.Integer()),
                                ],
                                required_keys=["b"],
                            ),
                        ),
                    ],
                    required_keys=["DictGrouptitleTitleABChelptextNone"],
                ),
            ),
            id="some required dictelements/vertical rendering",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "a": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                        required=True,
                    ),
                    "b": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                        required=True,
                    ),
                }
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.Dictionary(
                    elements=[
                        (
                            "DictGrouptitleTitleABChelptextNone",
                            legacy_valuespecs.Dictionary(
                                title=_("ABC"),
                                elements=[
                                    ("a", legacy_valuespecs.Integer()),
                                    ("b", legacy_valuespecs.Integer()),
                                ],
                                required_keys=["a", "b"],
                                horizontal=True,
                            ),
                        ),
                    ],
                    required_keys=["DictGrouptitleTitleABChelptextNone"],
                ),
            ),
            id="all required dictelements/horizontal rendering",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "a": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                        render_only=True,
                    ),
                    "b": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                    ),
                }
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.Dictionary(
                    elements=[
                        (
                            "DictGrouptitleTitleABChelptextNone",
                            legacy_valuespecs.Dictionary(
                                title=_("ABC"),
                                elements=[
                                    ("a", legacy_valuespecs.Integer()),
                                    ("b", legacy_valuespecs.Integer()),
                                ],
                                hidden_keys=["a"],
                            ),
                        ),
                    ],
                    required_keys=["DictGrouptitleTitleABChelptextNone"],
                ),
            ),
            id="render_only dictelements",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "a": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                        render_only=True,
                    ),
                    "b": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                        render_only=True,
                    ),
                }
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.Dictionary(
                    elements=[
                        (
                            "DictGrouptitleTitleABChelptextNone",
                            legacy_valuespecs.Dictionary(
                                title=_("ABC"),
                                elements=[
                                    ("a", legacy_valuespecs.Integer()),
                                    ("b", legacy_valuespecs.Integer()),
                                ],
                                hidden_keys=["a", "b"],
                            ),
                        ),
                    ],
                    required_keys=[],
                    hidden_keys=["DictGrouptitleTitleABChelptextNone"],
                ),
            ),
            id="render_only all dictelements",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "a": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC hidden")),
                        render_only=True,
                    ),
                    "b": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC hidden")),
                        render_only=True,
                    ),
                    "c": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC shown")),
                        render_only=False,
                    ),
                    "d": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC shown")),
                        render_only=True,
                    ),
                }
            ),
            legacy_valuespecs.Transform(
                legacy_valuespecs.Dictionary(
                    elements=[
                        (
                            "DictGrouptitleTitleABChiddenhelptextNone",
                            legacy_valuespecs.Dictionary(
                                title=_("ABC hidden"),
                                elements=[
                                    ("a", legacy_valuespecs.Integer()),
                                    ("b", legacy_valuespecs.Integer()),
                                ],
                                hidden_keys=["a", "b"],
                            ),
                        ),
                        (
                            "DictGrouptitleTitleABCshownhelptextNone",
                            legacy_valuespecs.Dictionary(
                                title=_("ABC shown"),
                                elements=[
                                    ("c", legacy_valuespecs.Integer()),
                                    ("d", legacy_valuespecs.Integer()),
                                ],
                                hidden_keys=["d"],
                            ),
                        ),
                    ],
                    required_keys=["DictGrouptitleTitleABCshownhelptextNone"],
                    hidden_keys=["DictGrouptitleTitleABChiddenhelptextNone"],
                ),
            ),
            id="render_only some dictelements",
        ),
    ],
)
def test_dictionary_groups_dict_element_properties(
    to_convert: api_v1.form_specs.Dictionary, expected: legacy_valuespecs.Dictionary
) -> None:
    _compare_specs(convert_to_legacy_valuespec(to_convert, translate_to_current_language), expected)


def _inner_migration(values: object) -> dict[str, object]:
    assert isinstance(values, dict)
    if "a" in values:
        values["b"] = values.pop("a")
    return values


def _out_migration(values: object) -> dict[str, object]:
    assert isinstance(values, dict)
    if "foo" in values:
        values["bar"] = values.pop("foo")
    return values


@pytest.mark.parametrize(
    ["to_convert", "value_to_migrate", "expected"],
    [
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "a": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Dictionary(
                            elements={
                                "a_nested": api_v1.form_specs.DictElement(
                                    parameter_form=api_v1.form_specs.Integer(),
                                    required=True,
                                ),
                            }
                        ),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                    ),
                    "b": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                    ),
                },
                migrate=lambda x: {"a": {"a_nested": x["a"]["a_nested"] * 2}, "b": x["b"] * 2},  # type: ignore[index]
            ),
            {"a": {"a_nested": 1}, "b": 2},
            {"a": {"a_nested": 2}, "b": 4},
            id="outermost migration",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                migrate=_out_migration,
                elements={
                    "bar": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Dictionary(
                            elements={
                                "b": api_v1.form_specs.DictElement(
                                    parameter_form=api_v1.form_specs.FixedValue(value=1),
                                ),
                            },
                            migrate=_inner_migration,
                        ),
                    ),
                },
            ),
            {"foo": {"a": 1}},
            {"bar": {"b": 1}},
            id="nested key migration",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                migrate=_out_migration,
                elements={
                    "bar": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Dictionary(
                            migrate=_inner_migration,
                            elements={
                                "b": api_v1.form_specs.DictElement(
                                    parameter_form=api_v1.form_specs.Dictionary(
                                        migrate=_inner_migration,
                                        elements={
                                            "b": api_v1.form_specs.DictElement(
                                                group=api_v1.form_specs.DictGroup(),
                                                parameter_form=api_v1.form_specs.String(),
                                                required=True,
                                            )
                                        },
                                    )
                                )
                            },
                        ),
                    )
                },
            ),
            {"foo": {"a": {"a": ""}}},
            {"bar": {"b": {"b": ""}}},
            id="migration of nested dictionary with inner group",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "a": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Dictionary(
                            elements={
                                "a_nested": api_v1.form_specs.DictElement(
                                    parameter_form=api_v1.form_specs.Integer(
                                        migrate=lambda x: x * 2  # type: ignore[operator]
                                    ),
                                    required=True,
                                )
                            }
                        ),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                    ),
                    "b": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                    ),
                },
            ),
            {"a": {"a_nested": 1}, "b": 2},
            {"a": {"a_nested": 2}, "b": 2},
            id="migration in group",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "a": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Levels(
                            level_direction=api_v1.form_specs.LevelDirection.UPPER,
                            form_spec_template=api_v1.form_specs.Integer(
                                migrate=lambda x: x * 2  # type: ignore[operator]
                            ),
                            prefill_fixed_levels=api_v1.form_specs.DefaultValue((1, 2)),
                            predictive=api_v1.form_specs.PredictiveLevels(
                                reference_metric="my_metric",
                                prefill_abs_diff=api_v1.form_specs.DefaultValue((5, 10)),
                            ),
                        ),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                    ),
                    "b": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                    ),
                },
            ),
            {
                "a": (
                    "cmk_postprocessed",
                    "predictive_levels",
                    {
                        "__direction__": "upper",
                        "__reference_metric__": "my_metric",
                        "horizon": 90,
                        "levels": ("absolute", (1, 2)),
                        "period": "wday",
                        "bound": None,
                    },
                ),
                "b": 2,
            },
            {
                "a": (
                    "cmk_postprocessed",
                    "predictive_levels",
                    {
                        "__direction__": "upper",
                        "__reference_metric__": "my_metric",
                        "horizon": 90,
                        "levels": ("absolute", (2, 4)),
                        "period": "wday",
                        "bound": None,
                    },
                ),
                "b": 2,
            },
            id="migration in non-Dictionary with group",
        ),
    ],
)
def test_dictionary_groups_migrate(
    to_convert: api_v1.form_specs.Dictionary, value_to_migrate: object, expected: object
) -> None:
    converted = convert_to_legacy_valuespec(to_convert, translate_to_current_language)
    assert converted.transform_value(value_to_migrate) == expected


@pytest.mark.parametrize(
    ["form_spec", "rule"],
    [
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "key1": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Dictionary(
                            elements={
                                "key2": api_v1.form_specs.DictElement(
                                    parameter_form=api_v1.form_specs.Dictionary(
                                        elements={
                                            "key3": api_v1.form_specs.DictElement(
                                                group=api_v1.form_specs.DictGroup(),
                                                parameter_form=api_v1.form_specs.String(),
                                                required=True,
                                            )
                                        }
                                    )
                                )
                            }
                        ),
                    )
                }
            ),
            {"key1": {"key2": {"key3": ""}}},
            id="nested dictionary with inner group",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "key1": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Dictionary(
                            elements={
                                "key2": api_v1.form_specs.DictElement(
                                    group=api_v1.form_specs.DictGroup(),
                                    parameter_form=api_v1.form_specs.String(),
                                    required=True,
                                ),
                            },
                        ),
                    )
                },
                migrate=lambda x: x,  # type: ignore[arg-type, return-value]
            ),
            {"key1": {"key2": ""}},
            id="inner group with outer migrate",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "key1": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Dictionary(
                            elements={
                                "key2": api_v1.form_specs.DictElement(
                                    group=api_v1.form_specs.DictGroup(),
                                    parameter_form=api_v1.form_specs.String(),
                                    required=True,
                                ),
                            },
                        ),
                    )
                },
                custom_validate=(lambda x: None,),
            ),
            {"key1": {"key2": ""}},
            id="inner group with outer validate",
        ),
    ],
)
def test_dictionary_groups_legacy_validation(
    form_spec: api_v1.form_specs.FormSpec, rule: Mapping[str, Any]
) -> None:
    converted = convert_to_legacy_valuespec(form_spec, lambda x: x)
    converted.validate_datatype(rule, "")
    converted.validate_value(rule, "")


@pytest.mark.parametrize(
    ["to_convert", "value_to_validate"],
    [
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "a": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Dictionary(
                            elements={
                                "a_nested": api_v1.form_specs.DictElement(
                                    parameter_form=api_v1.form_specs.Integer(),
                                    required=True,
                                ),
                            }
                        ),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                    ),
                    "b": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                    ),
                    "c": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                    ),
                },
                custom_validate=(api_v1.form_specs.validators.LengthInRange(max_value=2),),
            ),
            {"a": {"a_nested": 1}, "b": 2, "c": 3},
            id="outermost validation",
        ),
        pytest.param(
            api_v1.form_specs.Dictionary(
                elements={
                    "a": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Dictionary(
                            elements={
                                "a_nested": api_v1.form_specs.DictElement(
                                    parameter_form=api_v1.form_specs.Integer(
                                        custom_validate=(
                                            api_v1.form_specs.validators.NumberInRange(min_value=1),
                                        )
                                    ),
                                    required=True,
                                )
                            },
                        ),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                    ),
                    "b": api_v1.form_specs.DictElement(
                        parameter_form=api_v1.form_specs.Integer(),
                        group=api_v1.form_specs.DictGroup(title=api_v1.Title("ABC")),
                    ),
                },
            ),
            {"a": {"a_nested": 0}, "b": 2},
            id="validation in group",
        ),
    ],
)
def test_dictionary_groups_validate(
    to_convert: api_v1.form_specs.Dictionary, value_to_validate: object
) -> None:
    converted = convert_to_legacy_valuespec(to_convert, translate_to_current_language)
    with pytest.raises(MKUserError):
        converted.validate_value(value_to_validate, "")


def test_agent_config_rule_spec_transformations_work_with_previous_non_dict_values() -> None:
    legacy_rulespec = convert_to_legacy_rulespec(
        api_v1.rule_specs.AgentConfig(
            name="test_rulespec",
            title=api_v1.Title("rulespec title"),
            topic=api_v1.rule_specs.Topic.GENERAL,
            parameter_form=lambda: api_v1.form_specs.Dictionary(
                elements={},
                migrate=lambda _x: {},
            ),
            help_text=api_v1.Help("help text"),
        ),
        Edition.COMMUNITY,
        translate_to_current_language,
    )
    assert legacy_rulespec.valuespec.transform_value(()) == {"cmk-match-type": "dict"}
