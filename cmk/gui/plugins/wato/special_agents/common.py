#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DictionaryEntry,
    ListOf,
    RegExp,
    TextInput,
)
from cmk.gui.wato import MigrateToIndividualOrStoredPassword


def prometheus_connection() -> TextInput:
    return TextInput(
        title=_("URL server address"),
        help=_("Specify a URL to connect to your server. Do not include the protocol."),
        allow_empty=False,
    )


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
