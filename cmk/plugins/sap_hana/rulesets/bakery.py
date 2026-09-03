#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    List,
    migrate_to_password,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def migrate_user_and_password(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "user" in value:
        return value
    match value:
        case (str() as user, password):
            return {"user": user, "password": migrate_to_password(password)}
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def _migrate_single_credentials(value: object) -> tuple[str, object]:
    # Old credentials are recognised by their shape: a bare key or a (user, password) tuple
    # whose password is itself a tuple. This keeps a user named like one of the new variants
    # from being mistaken for an already migrated value.
    match value:
        case ("userstorekey", str() as key):
            return "userstorekey", key
        case ("user_password", dict() as credentials) if "user" in credentials:
            return "user_password", credentials
        case str() as key:
            return "userstorekey", key
        case (str(), tuple()):
            return "user_password", migrate_user_and_password(value)
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def migrate_database(value: object) -> Mapping[str, object]:
    if isinstance(value, dict) and "sid" in value:
        return value
    match value:
        case (str() as sid, str() as instance, str() as database, credentials):
            return {
                "sid": sid,
                "instance": instance,
                "database": database,
                "credentials": _migrate_single_credentials(credentials),
            }
        case _:
            raise ValueError(f"Unexpected value: {value!r}")


def migrate_credentials(value: object) -> tuple[str, object]:
    match value:
        case ("databases", list() as databases):
            return "databases", databases
        case list() as databases:
            return "databases", [migrate_database(d) for d in databases]
        case _:
            return _migrate_single_credentials(value)


def _migrate_sap_connect(value: object) -> tuple[str, object]:
    match value:
        case None | ("none", None):
            return "none", None
        case ("credentials", dict() as credentials) if "user" in credentials:
            return "credentials", credentials
        case _:
            return "credentials", migrate_user_and_password(value)


def migrate(value: object) -> Mapping[str, object]:
    if value is None:
        return {"deployment": ("do_not_deploy", None)}
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected value: {value!r}")
    if "deployment" in value:
        return value
    if "credentials" not in value:
        raise ValueError(f"Unexpected value: {value!r}")
    # Old rule ("first matching rule wins"): make all parameters explicit so that merging with
    # other rules does not change the outcome. The plug-in runs as the instance user by default.
    return {
        "deployment": ("sync", None),
        "credentials": migrate_credentials(value["credentials"]),
        "credentials_sap_connect": _migrate_sap_connect(value.get("credentials_sap_connect")),
        "runas": value.get("runas", "instance"),
    }


def _user_and_password_form() -> Dictionary:
    return Dictionary(
        migrate=migrate_user_and_password,
        elements={
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "password": DictElement(
                required=True,
                parameter_form=Password(title=Title("Password")),
            ),
        },
    )


def _single_credentials_elements() -> Sequence[
    CascadingSingleChoiceElement[Mapping[str, object]] | CascadingSingleChoiceElement[str]
]:
    return (
        CascadingSingleChoiceElement(
            name="user_password",
            title=Title("User and password"),
            parameter_form=_user_and_password_form(),
        ),
        CascadingSingleChoiceElement(
            name="userstorekey",
            title=Title("User store key"),
            parameter_form=String(
                title=Title("User store key"),
                custom_validate=(validators.LengthInRange(min_value=1),),
            ),
        ),
    )


def _database_form() -> Dictionary:
    return Dictionary(
        migrate=migrate_database,
        elements={
            "sid": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("SID"),
                    custom_validate=(
                        validators.MatchRegex(
                            r"^[A-Za-z_][A-Za-z0-9_-]*$",
                            Message(
                                "An identifier must only consist of letters, digits, dash and "
                                "underscore and it must start with a letter or underscore."
                            ),
                        ),
                    ),
                ),
            ),
            "instance": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Instance"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "database": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Database"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "credentials": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Credentials"),
                    elements=_single_credentials_elements(),
                    prefill=DefaultValue("user_password"),
                ),
            ),
        },
    )


def _form_spec() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This will deploy and configure the Checkmk agent plug-in <tt>mk_sap_hana</tt>. "
            "To make this plug-in work, you have to configure default credentials that are used "
            "for all databases or configure credentials per database. To configure credentials "
            "specify USERSTOREKEY or USER and PASSWORD, i.e. USERSTOREKEY=SVAMON and SID=I08 "
            "means we need a key for SVAMONI08 in the HDB userstore specified in "
            "$MK_CONFDIR/sap_hana.cfg. Moreover you can configure 'RUNAS' with the following "
            "values 'agent' or 'instance'. The latter one is default."
            " Use the FQDN in the query if HOSTNAME is not set, otherwise the short host name."
        ),
        migrate=migrate,
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Deployment type"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="sync",
                            title=Title("Deploy the plug-in and run it synchronously"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the plug-in"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ),
                    prefill=DefaultValue("sync"),
                ),
            ),
            "credentials": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Credentials"),
                    elements=(
                        *_single_credentials_elements(),
                        CascadingSingleChoiceElement(
                            name="databases",
                            title=Title("Credentials for selected databases"),
                            parameter_form=List(
                                title=Title("Databases"),
                                element_template=_database_form(),
                            ),
                        ),
                    ),
                    prefill=DefaultValue("user_password"),
                ),
            ),
            "credentials_sap_connect": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Credentials for connect (ODBC interface)"),
                    elements=(
                        CascadingSingleChoiceElement(
                            name="none",
                            title=Title("Do not configure connect credentials"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="credentials",
                            title=Title("Configure connect credentials"),
                            parameter_form=_user_and_password_form(),
                        ),
                    ),
                    prefill=DefaultValue("credentials"),
                ),
            ),
            "runas": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Run as"),
                    elements=[
                        SingleChoiceElement(name="instance", title=Title("Instance")),
                        SingleChoiceElement(name="agent", title=Title("Agent")),
                    ],
                    prefill=DefaultValue("instance"),
                ),
            ),
        },
    )


rule_spec_mk_sap_hana = AgentConfig(
    title=Title("SAP HANA"),
    name="mk_sap_hana",
    topic=Topic.DATABASES,
    parameter_form=_form_spec,
)
