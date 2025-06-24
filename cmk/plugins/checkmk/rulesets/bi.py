#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping

from cmk.gui import bi  # pylint: disable=cmk-module-layer-violation
from cmk.gui.form_specs.private import (  # pylint: disable=cmk-module-layer-violation
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.gui.form_specs.private.user_selection import (  # pylint: disable=cmk-module-layer-violation
    UserSelection,
    UserSelectionFilter,
)

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    List,
    MatchingScope,
    migrate_to_password,
    Password,
    RegularExpression,
    ServiceState,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _credential_vs() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        elements=[
            CascadingSingleChoiceElement(
                name="automation",
                title=Title("Use the credentials of an automation user"),
                parameter_form=UserSelection(
                    filter=UserSelectionFilter.AUTOMATION,
                    help_text=Help(
                        "Only automation users with passwords that are currently stored in cleartext will be displayed here."
                    ),
                ),
            ),
            CascadingSingleChoiceElement(
                name="configured",
                title=Title("Use the following credentials"),
                parameter_form=Dictionary(
                    elements={
                        "username": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("User name"),
                                custom_validate=(validators.LengthInRange(min_value=0),),
                            ),
                        ),
                        "password": DictElement(
                            required=True,
                            parameter_form=Password(
                                title=Title("Password"),
                                migrate=migrate_to_password,
                                custom_validate=(validators.LengthInRange(min_value=0),),
                            ),
                        ),
                    },
                    migrate=_tuple_do_dict_with_keys(
                        "username",
                        "password",
                    ),
                ),
            ),
        ],
        help_text=Help("Here you can configure the credentials to be used."),
        title=Title("Login credentials"),
        prefill=DefaultValue("automation"),
    )


def _bi_aggregate() -> Dictionary:
    return Dictionary(
        elements={
            "site": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    elements=[
                        CascadingSingleChoiceElement(
                            name="local",
                            title=Title("Connect to the local site"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="remote",
                            title=Title("Connect to site url"),
                            parameter_form=Dictionary(
                                elements={
                                    "url": DictElement(
                                        required=True,
                                        parameter_form=String(
                                            help_text=Help(
                                                "URL of the remote site, for example https://10.3.1.2/testsite"
                                            ),
                                            custom_validate=(
                                                validators.Url(
                                                    protocols=[
                                                        validators.UrlProtocol.HTTP,
                                                        validators.UrlProtocol.HTTPS,
                                                    ]
                                                ),
                                            ),
                                        ),
                                    ),
                                    "credentials": DictElement(
                                        required=True,
                                        parameter_form=_credential_vs(),
                                    ),
                                },
                            ),
                        ),
                    ],
                    title=Title("Site connection"),
                ),
            ),
            "filter": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Filter aggregations"),
                    elements={
                        "aggr_name": DictElement(
                            required=False,
                            parameter_form=List(
                                element_template=String(title=Title("Pattern")),
                                title=Title("By aggregation name (exact match)"),
                                add_element_label=Label("Add new aggregation"),
                                editable_order=False,
                            ),
                        ),
                        "aggr_group_prefix": DictElement(
                            required=False,
                            parameter_form=List(
                                element_template=SingleChoiceExtended(
                                    elements=[
                                        SingleChoiceElementExtended(
                                            name=value,
                                            title=Title(title),  # pylint: disable=localization-of-non-literal-string
                                        )
                                        for value, title in bi.aggregation_group_choices()
                                    ],
                                ),
                                title=Title("By aggregation group prefix"),
                                add_element_label=Label("Add new group"),
                                editable_order=False,
                            ),
                        ),
                    },
                ),
            ),
            "assignments": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Aggregation assignment"),
                    elements={
                        "querying_host": DictElement(
                            required=False,
                            parameter_form=FixedValue(
                                title=Title("Assign to the querying host"),
                                value="querying_host",
                                label=Label(""),
                            ),
                        ),
                        "affected_hosts": DictElement(
                            required=False,
                            parameter_form=FixedValue(
                                value="affected_hosts",
                                title=Title("Assign to the affected hosts"),
                                label=Label(""),
                            ),
                        ),
                        "regex": DictElement(
                            required=False,
                            parameter_form=List(
                                element_template=Dictionary(
                                    elements={
                                        "regular_expression": DictElement(
                                            required=True,
                                            parameter_form=RegularExpression(
                                                title=Title("Regular expression"),
                                                help_text=Help(
                                                    "Must contain at least one subgroup <tt>(...)</tt>"
                                                ),
                                                custom_validate=(
                                                    validators.LengthInRange(min_value=1),
                                                    validators.RegexGroupsInRange(
                                                        min_groups=0,
                                                        max_groups=9,
                                                    ),
                                                ),
                                                predefined_help_text=MatchingScope.PREFIX,
                                            ),
                                        ),
                                        "replacement": DictElement(
                                            required=True,
                                            parameter_form=String(
                                                title=Title("Replacement"),
                                                help_text=Help(
                                                    "Use <tt>\\1</tt>, <tt>\\2</tt> etc. to replace matched subgroups"
                                                ),
                                                custom_validate=(
                                                    validators.LengthInRange(min_value=1),
                                                ),
                                            ),
                                        ),
                                    },
                                    migrate=_tuple_do_dict_with_keys(
                                        "regular_expression",
                                        "replacement",
                                    ),
                                ),
                                title=Title("Assign via regular expressions"),
                                help_text=Help(
                                    "You can add any number of expressions here which are executed succesively until the first match. "
                                    "Please specify a regular expression in the first field. This expression should at "
                                    "least contain one subexpression exclosed in brackets - for example <tt>vm_(.*)_prod</tt>. "
                                    "In the second field you specify the translated aggregation and can refer to the first matched "
                                    "group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on, for example <tt>\\1.example.org</tt>. "
                                    ""
                                ),
                                add_element_label=Label("Add expression"),
                                editable_order=False,
                            ),
                        ),
                    },
                ),
            ),
            "options": DictElement(
                required=False,
                parameter_form=Dictionary(
                    title=Title("Additional options"),
                    elements={
                        "state_scheduled_downtime": DictElement(
                            required=False,
                            parameter_form=ServiceState(
                                title=Title("State, if BI aggregate is in scheduled downtime")
                            ),
                        ),
                        "state_acknowledged": DictElement(
                            required=False,
                            parameter_form=ServiceState(
                                title=Title("State, if BI aggregate is acknowledged")
                            ),
                        ),
                    },
                ),
            ),
        },
        migrate=_migrate_to_internal_user,
    )


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("BI Aggregations"),
        elements={
            "options": DictElement(
                required=True,
                parameter_form=List(
                    element_template=_bi_aggregate(),
                    help_text=Help(
                        "This rule allows you to check multiple BI aggregations from multiple sites at once. "
                        "You can also assign aggregations to specific hosts through the piggyback mechanism."
                    ),
                ),
            ),
        },
    )


def _migrate_to_internal_user(
    params: object,
) -> dict:
    """
    We are migrating the use of custom users and the automation user for local calls via the DCD
    to use the internal user only for 2.4.
    """
    if params is None:
        return {}
    assert isinstance(params, dict)
    if params["site"] is None or params["site"][0] != "url":
        return params

    credentials = params.pop("credentials")
    credentials = (
        ("automation", "automation") if credentials == ("automation", None) else credentials
    )
    url = params["site"][1]
    params["site"] = ("remote", {"url": url, "credentials": credentials})
    return params


def _tuple_do_dict_with_keys(*keys: str) -> Callable[[object], Mapping[str, object]]:
    def _tuple_to_dict(
        param: object,
    ) -> Mapping[str, object]:
        match param:
            case tuple():
                return dict(zip(keys, param))
            case dict() as already_migrated:
                return already_migrated
        raise ValueError(param)

    return _tuple_to_dict


rule_spec_special_agent_bi = SpecialAgent(
    name="bi",
    title=Title("BI Aggregations"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form,
)
