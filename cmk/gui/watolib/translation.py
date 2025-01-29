#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from cmk.ccc.exceptions import MKGeneralException

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
    FixedValue,
    ListOf,
    MigrateNotUpdated,
    RegExp,
    TextInput,
    Tuple,
    ValueSpec,
)


# NOTE: When changing this keep it in sync with cmk.utils.translations.translate_hostname()
def HostnameTranslation(**kwargs: Any) -> Dictionary:
    help_txt = kwargs.get("help")
    title = kwargs.get("title")
    return Dictionary(
        title=title,
        help=help_txt,
        elements=[_get_drop_domain_element()] + translation_elements("host"),
    )


def ServiceDescriptionTranslation(**kwargs: Any) -> Dictionary:
    help_txt = kwargs.get("help")
    title = kwargs.get("title")
    return Dictionary(
        title=title,
        help=help_txt,
        elements=translation_elements("service"),
    )


def translation_elements(what: str) -> list[tuple[str, ValueSpec]]:
    if what == "host":
        singular = "hostname"
        plural = "hostnames"

    elif what == "service":
        singular = "service name"
        plural = "service names"

    else:
        raise MKGeneralException("No translations found for %s." % what)

    return [
        (
            "case",
            DropdownChoice(
                title=_("Case translation"),
                choices=[
                    (None, _("Do not convert case")),
                    ("upper", _("Convert %s to upper case") % plural),
                    ("lower", _("Convert %s to lower case") % plural),
                ],
            ),
        ),
        (
            "regex",
            MigrateNotUpdated(
                valuespec=ListOf(
                    valuespec=Tuple(
                        orientation="horizontal",
                        elements=[
                            RegExp(
                                title=_("Regular expression"),
                                help=_("Must contain at least one subgroup <tt>(...)</tt>"),
                                mingroups=0,
                                maxgroups=9,
                                size=30,
                                allow_empty=False,
                                mode=RegExp.prefix,
                                case_sensitive=False,
                            ),
                            TextInput(
                                title=_("Replacement"),
                                help=_(
                                    "Use <tt>\\1</tt>, <tt>\\2</tt> etc. to replace matched subgroups"
                                ),
                                size=30,
                                allow_empty=False,
                            ),
                        ],
                    ),
                    title=_("Multiple regular expressions"),
                    help=_(
                        "You can add any number of expressions here which are executed succesively until the first match. "
                        "Please specify a regular expression in the first field. This expression should at "
                        "least contain one subexpression exclosed in brackets - for example <tt>vm_(.*)_prod</tt>. "
                        "In the second field you specify the translated %s and can refer to the first matched "
                        "group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on, for example <tt>\\1.example.org</tt>. "
                        ""
                    )
                    % singular,
                    add_label=_("Add expression"),
                    movable=False,
                ),
                migrate=lambda x: isinstance(x, tuple) and [x] or x,
            ),
        ),
        (
            "mapping",
            ListOf(
                valuespec=Tuple(
                    orientation="horizontal",
                    elements=[
                        TextInput(
                            title=_("Original %s") % singular,
                            size=30,
                            allow_empty=False,
                        ),
                        TextInput(
                            title=_("Translated %s") % singular,
                            size=30,
                            allow_empty=False,
                        ),
                    ],
                ),
                title=_("Explicit %s mapping") % singular,
                help=_(
                    "If case conversion and regular expression do not work for all cases then you can "
                    "specify explicity pairs of origin {0} and translated {0} here. This "
                    "mapping is being applied <b>after</b> the case conversion and <b>after</b> a regular "
                    "expression conversion (if that matches)."
                ).format(singular),
                add_label=_("Add new mapping"),
                movable=False,
            ),
        ),
    ]


def _get_drop_domain_element() -> tuple[str, ValueSpec]:
    return (
        "drop_domain",
        FixedValue(
            value=True,
            title=_("Convert FQHN"),
            totext=_("Drop domain part (<tt>host123.foobar.de</tt> → <tt>host123</tt>)"),
        ),
    )
