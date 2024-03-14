#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DictionaryEntry,
    ListOf,
    Migrate,
    NetworkPort,
    RegExp,
    TextInput,
)
from cmk.gui.wato import MigrateToIndividualOrStoredPassword

from cmk.plugins.aws import constants as aws_constants  # pylint: disable=cmk-module-layer-violation


def prometheus_connection() -> Migrate[TextInput]:
    valuespec = TextInput(
        title=_("URL server address"),
        help=_("Specify a URL to connect to your server. Do not include the protocol."),
        allow_empty=False,
    )

    def migrate(value: object) -> str:
        match value:
            case ("url_custom", {"url_address": str(v)}):
                return v
            case str(v):
                return v
        raise MKUserError(
            None, _("The options IP Address and Host name have been removed - Werk #14573.")
        )

    return Migrate(valuespec=valuespec, migrate=migrate)  # type: ignore[arg-type]


def api_request_authentication() -> DictionaryEntry:
    return (
        "auth_basic",
        CascadingDropdown(
            title=_("Authentication"),
            choices=[
                (
                    "auth_login",
                    _("Basic authentication"),
                    Dictionary(
                        elements=[
                            (
                                "username",
                                TextInput(
                                    title=_("Login username"),
                                    allow_empty=False,
                                ),
                            ),
                            (
                                "password",
                                MigrateToIndividualOrStoredPassword(
                                    title=_("Password"),
                                    allow_empty=False,
                                ),
                            ),
                        ],
                        optional_keys=[],
                    ),
                ),
                (
                    "auth_token",
                    _("Token authentication"),
                    Dictionary(
                        elements=[
                            (
                                "token",
                                MigrateToIndividualOrStoredPassword(
                                    title=_("Login token"),
                                    allow_empty=False,
                                ),
                            ),
                        ],
                        optional_keys=[],
                    ),
                ),
            ],
        ),
    )


def api_request_connection_elements(  # type: ignore[no-untyped-def]
    help_text: str, default_port: int
):
    return [
        ("port", NetworkPort(title=_("Port"), default_value=default_port)),
        (
            "path-prefix",
            TextInput(title=_("Custom path prefix"), help=help_text, allow_empty=False),
        ),
    ]


def filter_kubernetes_namespace_element():
    return (
        "namespace_include_patterns",
        ListOf(
            valuespec=RegExp(
                mode=RegExp.complete,
                title=_("Pattern"),
                allow_empty=False,
            ),
            title=_("Monitor namespaces matching"),
            add_label=_("Add new pattern"),
            allow_empty=False,
            help=_(
                "If your cluster has multiple namespaces, you can specify "
                "a list of regex patterns. Only matching namespaces will "
                "be monitored. Note that this concerns everything which "
                "is part of the matching namespaces such as pods for "
                "example."
            ),
        ),
    )


def validate_aws_tags(value, varprefix):
    used_keys = []
    # KEY:
    # ve_p_services_p_ec2_p_choice_1_IDX_0
    # VALUES:
    # ve_p_services_p_ec2_p_choice_1_IDX_1_IDX
    for idx_tag, (tag_key, tag_values) in enumerate(value):
        tag_field = f"{varprefix}_{idx_tag + 1}_0"
        if tag_key not in used_keys:
            used_keys.append(tag_key)
        else:
            raise MKUserError(
                tag_field, _("Each tag must be unique and cannot be used multiple times")
            )
        if tag_key.startswith("aws:"):
            raise MKUserError(tag_field, _("Do not use 'aws:' prefix for the key."))
        if len(tag_key) > 128:
            raise MKUserError(tag_field, _("The maximum key length is 128 characters."))
        if len(tag_values) > 50:
            raise MKUserError(tag_field, _("The maximum number of tags per resource is 50."))

        for idx_values, v in enumerate(tag_values):
            values_field = f"{varprefix}_{idx_tag + 1}_1_{idx_values + 1}"
            if len(v) > 256:
                raise MKUserError(values_field, _("The maximum value length is 256 characters."))
            if v.startswith("aws:"):
                raise MKUserError(values_field, _("Do not use 'aws:' prefix for the values."))


def aws_region_to_monitor() -> list[tuple[str, str]]:
    def key(regionid_display: tuple[str, str]) -> str:
        return regionid_display[1]

    regions_by_display_order = [
        *sorted((r for r in aws_constants.AWSRegions if "GovCloud" not in r[1]), key=key),
        *sorted((r for r in aws_constants.AWSRegions if "GovCloud" in r[1]), key=key),
    ]
    return [(id_, " | ".join((region, id_))) for id_, region in regions_by_display_order]
