#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.form_specs.private.definitions import LegacyValueSpec
from cmk.gui.i18n import translate_to_current_language

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import FormSpec


def recompose(form_spec: FormSpec) -> LegacyValueSpec:
    # This one here requires a local import to avoid circular dependencies
    # It uses convert_to_legacy_valuespec
    # legacy_converter->legacy_wato->page_handler->ruleset page->form_spec_visitor->here->ERROR
    from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_valuespec

    valuespec = convert_to_legacy_valuespec(form_spec, translate_to_current_language)
    return LegacyValueSpec(
        title=Title(  # pylint: disable=localization-of-non-literal-string
            str(valuespec.title() or "")
        ),
        help_text=Help(  # pylint: disable=localization-of-non-literal-string
            str(valuespec.help() or "")
        ),
        valuespec=valuespec,
    )
