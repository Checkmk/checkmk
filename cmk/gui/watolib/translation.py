#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from typing import Literal

from cmk.gui.form_specs.generators.regex_utils import make_help
from cmk.gui.form_specs.unstable import not_empty
from cmk.gui.form_specs.unstable.legacy_converter import Tuple as FSTuple
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
from cmk.rulesets.internal.form_specs import (
    ListExtended,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    MatchingScope,
    RegularExpression,
    String,
)

type _LocalizedStr = str
type _Case = Literal["lower", "upper"] | None


# NOTE: When changing this keep it in sync with cmk.ccc.translations.translate()
def HostnameTranslation(
    *, title: _LocalizedStr, help_txt: _LocalizedStr | None = None
) -> Dictionary:
    return Dictionary(
        title=title,
        help=help_txt,
        elements=[_get_drop_domain_element(), *translation_elements()],
    )


def ServiceDescriptionTranslation(title: _LocalizedStr, help_txt: _LocalizedStr) -> Dictionary:
    return Dictionary(
        title=title,
        help=help_txt,
        elements=translation_elements(),
    )


def translation_elements() -> tuple[
    tuple[Literal["case"], DropdownChoice],
    tuple[Literal["regex"], MigrateNotUpdated],
    tuple[Literal["mapping"], ListOf],
]:
    return (
        (
            "case",
            DropdownChoice(
                title=_("Case translation"),
                choices=[
                    (None, _("Do not convert case")),
                    ("upper", _("Convert to upper case")),
                    ("lower", _("Convert to lower case")),
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
                                mode=RegExp.complete,
                                case_sensitive=True,
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
                        "In the second field you specify the desired outcome of the translation. "
                        "You can refer to the first matched group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on,"
                        " for example <tt>\\1.example.org</tt>. "
                    ),
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
                            title=_("Original name"),
                            size=30,
                            allow_empty=False,
                        ),
                        TextInput(
                            title=_("Translated name"),
                            size=30,
                            allow_empty=False,
                        ),
                    ],
                ),
                title=_("Explicit name mapping"),
                help=_(
                    "If case conversion and regular expression do not work for all cases then you can "
                    "specify explicit pairs of original and translated names here. This "
                    "mapping is being applied <b>after</b> the case conversion and <b>after</b> a regular "
                    "expression conversion (if that matches)."
                ),
                add_label=_("Add new mapping"),
                movable=False,
            ),
        ),
    )


def translation_form_spec_elements() -> tuple[
    tuple[Literal["case"], SingleChoiceExtended[_Case]],
    tuple[Literal["regex"], ListExtended[tuple[object, ...]]],
    tuple[Literal["mapping"], ListExtended[tuple[object, ...]]],
]:
    """FormSpec counterpart of translation_elements()."""
    return (
        (
            "case",
            SingleChoiceExtended[_Case](
                title=Title("Case translation"),
                elements=[
                    SingleChoiceElementExtended[_Case](
                        name=None,
                        title=Title("Do not convert case"),
                    ),
                    SingleChoiceElementExtended[_Case](
                        name="upper",
                        title=Title("Convert to upper case"),
                    ),
                    SingleChoiceElementExtended[_Case](
                        name="lower",
                        title=Title("Convert to lower case"),
                    ),
                ],
                prefill=DefaultValue(None),
            ),
        ),
        (
            "regex",
            ListExtended(
                title=Title("Multiple regular expressions"),
                help_text=Help(
                    "You can add any number of expressions here which are executed succesively"
                    " until the first match. Please specify a regular expression in the first"
                    " field. This expression should at least contain one subexpression exclosed"
                    " in brackets - for example <tt>vm_(.*)_prod</tt>. In the second field you"
                    " specify the desired outcome of the translation. You can refer to the first"
                    " matched group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on,"
                    " for example <tt>\\1.example.org</tt>. "
                ),
                element_template=FSTuple(
                    layout="horizontal",
                    elements=[
                        RegularExpression(
                            title=Title("Regular expression"),
                            predefined_help_text=MatchingScope.PREFIX,
                            help_text=make_help(
                                Help("Must contain at least one subgroup <tt>(...)</tt>"),
                                case_sensitive=False,
                            ),
                            custom_validate=[not_empty()],
                        ),
                        String(
                            title=Title("Replacement"),
                            help_text=Help(
                                "Use <tt>\\1</tt>, <tt>\\2</tt> etc. to replace matched subgroups"
                            ),
                            custom_validate=[not_empty()],
                        ),
                    ],
                ),
                add_element_label=Label("Add expression"),
                editable_order=False,
                prefill=DefaultValue([]),
            ),
        ),
        (
            "mapping",
            ListExtended(
                title=Title("Explicit name mapping"),
                help_text=Help(
                    "If case conversion and regular expression do not work for all cases then you"
                    " can specify explicit pairs of original and translated names here. This"
                    " mapping is being applied <b>after</b> the case conversion and <b>after</b>"
                    " a regular expression conversion (if that matches)."
                ),
                element_template=FSTuple(
                    layout="horizontal",
                    elements=[
                        String(title=Title("Original name"), custom_validate=[not_empty()]),
                        String(title=Title("Translated name"), custom_validate=[not_empty()]),
                    ],
                ),
                add_element_label=Label("Add new mapping"),
                editable_order=False,
                prefill=DefaultValue([]),
            ),
        ),
    )


def _get_drop_domain_element() -> tuple[str, ValueSpec]:
    return (
        "drop_domain",
        FixedValue(
            value=True,
            title=_("Convert FQHN"),
            totext=_("Drop domain part (<tt>host123.foobar.de</tt> → <tt>host123</tt>)"),
        ),
    )
