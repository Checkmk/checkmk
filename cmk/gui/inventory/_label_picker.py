#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Mapping

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DropdownChoice,
    FixedValue,
    ListOf,
    RegExp,
    TextInput,
)


def _required_text(title: str, placeholder: str) -> TextInput:
    return TextInput(title=title, placeholder=placeholder, allow_empty=False)


def _regex_match(placeholder: str) -> RegExp:
    return RegExp(
        title=_("Regular expression"),
        mode=RegExp.infix,
        placeholder=placeholder,
        allow_empty=False,
    )


def _validate_replacement_rule(rule: Mapping[str, object], varprefix: str) -> None:
    try:
        re.compile(str(rule["value_match"])).sub(str(rule["value_replacement"]), "")
    except (re.error, IndexError) as e:
        raise MKUserError(varprefix, _("Invalid replacement: %(error)s") % {"error": e}) from e


def _value_match(*, matching: str, replaced: str, replacement: str) -> CascadingDropdown:
    return CascadingDropdown(
        title=_("Label value"),
        help=_(
            "Regular expressions are searched anywhere in the raw value converted to a "
            "string, e.g. <tt>True</tt> or <tt>1073741824</tt>. Anchor them with "
            "<tt>^</tt> and <tt>$</tt>, and prefix them with <tt>(?i)</tt> to ignore the "
            "case. A replacement replaces the whole value; <tt>\\1</tt>, <tt>\\2</tt>, "
            "... refer to the groups. A missing, empty or non-matching value picks no label."
        ),
        choices=[
            (
                "use_value",
                _("The value"),
                FixedValue(value=None, totext=""),
            ),
            (
                "use_value_if_matches",
                _("The value, if it matches"),
                Dictionary(
                    optional_keys=False,
                    elements=[
                        ("value_match", _regex_match(matching)),
                    ],
                ),
            ),
            (
                "match_and_replace_value",
                _("A replacement (first matching rule wins)"),
                ListOf(
                    title=_("Replacement rules"),
                    valuespec=Dictionary(
                        optional_keys=False,
                        elements=[
                            ("value_match", _regex_match(replaced)),
                            ("value_replacement", _required_text(_("Replacement"), replacement)),
                        ],
                        validate=_validate_replacement_rule,
                    ),
                ),
            ),
        ],
    )


def _letter_case_choice(title: str) -> DropdownChoice[str]:
    return DropdownChoice(
        title=title,
        choices=[
            ("no_conversion", _("Keep")),
            ("lower", _("Lowercase")),
            ("upper", _("Uppercase")),
        ],
        default_value="no_conversion",
    )


def _row_filter() -> CascadingDropdown:
    return CascadingDropdown(
        title=_("Rows"),
        help=_(
            "Use only the rows whose column matches, e.g. match on <tt>name</tt> and use "
            "the value of <tt>version</tt>."
        ),
        choices=[
            (
                "all_rows",
                _("All rows"),
                FixedValue(value=None, totext=""),
            ),
            (
                "matching_rows",
                _("Rows where a column matches"),
                Dictionary(
                    optional_keys=False,
                    elements=[
                        ("column", _required_text(_("Column to match"), "name")),
                        ("value_match", _regex_match("(apache|nginx|httpd)")),
                    ],
                ),
            ),
        ],
    )


def _source_group() -> Dictionary:
    return Dictionary(
        title=_("Inventory source"),
        help=_(
            "Paths, keys and columns are matched exactly and case-sensitively, not as "
            "regular expressions."
        ),
        optional_keys=False,
        elements=[
            ("path", _required_text(_("Inventory categories"), "software.os")),
            (
                "attributes",
                ListOf(
                    title=_("Labels from single values"),
                    valuespec=Dictionary(
                        optional_keys=False,
                        elements=[
                            ("key_match", _required_text(_("Key of the value"), "name")),
                            (
                                "value_match",
                                _value_match(
                                    matching="Microsoft Windows Server",
                                    replaced="Microsoft Windows Server (.*)",
                                    replacement="Win Server \\1",
                                ),
                            ),
                            ("label_name", _required_text(_("Label name"), "os_name")),
                        ],
                    ),
                ),
            ),
            (
                "columns",
                ListOf(
                    title=_("Labels from table columns (first row with a value wins)"),
                    valuespec=Dictionary(
                        optional_keys=False,
                        elements=[
                            ("column", _required_text(_("Column of the value"), "name")),
                            ("row_filter", _row_filter()),
                            (
                                "value_match",
                                _value_match(
                                    matching="(apache|nginx|httpd)",
                                    replaced="(apache|nginx|httpd)",
                                    replacement="\\1",
                                ),
                            ),
                            ("label_name", _required_text(_("Label name"), "webserver")),
                        ],
                    ),
                ),
            ),
        ],
    )


def _labeling_group() -> Dictionary:
    return Dictionary(
        title=_("Label naming"),
        optional_keys=False,
        elements=[
            (
                "label_prefix",
                TextInput(
                    title=_("Label name prefix (empty for none)"),
                    default_value="cmk/inventory",
                    allow_empty=True,
                ),
            ),
            (
                "case_conversion",
                Dictionary(
                    title=_("Letter case"),
                    help=_(
                        "Applied after matching, to the label name and value; the prefix "
                        "is kept as entered."
                    ),
                    optional_keys=False,
                    elements=[
                        ("label", _letter_case_choice(_("Label name"))),
                        ("value", _letter_case_choice(_("Label value"))),
                    ],
                ),
            ),
        ],
    )


def _single_config() -> Dictionary:
    return Dictionary(
        optional_keys=False,
        elements=[
            ("source", _source_group()),
            ("labeling", _labeling_group()),
        ],
    )


def parameter_form() -> Dictionary:
    return Dictionary(
        title=_("HW/SW inventory label picker"),
        help=_(
            "Picks host labels from the HW/SW inventory tree of a host. The "
            "<i>Check_MK HW/SW Inventory</i> service picks them on each successful run and "
            "reports new, vanished and changed labels until the service discovery accepts "
            "them. A periodic service discovery that updates host labels accepts them "
            "automatically. A label of a discovery plug-in with the same name takes "
            "precedence. To look up paths, keys and columns, open the HW/SW inventory page "
            "of a host and enable <tt>Modify display options > Show internal tree "
            "paths</tt>. They are then shown in brackets behind the titles (a trailing "
            "<tt>*</tt> only marks key columns), and the raw value is shown in brackets "
            "behind each value."
        ),
        optional_keys=False,
        elements=[
            (
                "configs",
                ListOf(
                    title=_("Label sources"),
                    help=_(
                        "If several entries yield the same label name, the first one wins; "
                        "single values come before table columns."
                    ),
                    add_label=_("Add label source"),
                    valuespec=_single_config(),
                ),
            ),
        ],
    )
