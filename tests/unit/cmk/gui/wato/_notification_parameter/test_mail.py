#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.version import Edition
from cmk.gui.i18n import translate_to_current_language
from cmk.gui.rule_specs.legacy_converter import convert_to_legacy_valuespec
from cmk.gui.wato._notification_parameter._mail import form_spec_mail


@pytest.mark.xfail(strict=True, reason="crash group 4880")
@pytest.mark.usefixtures("request_context", "patch_theme")
def test_mail_parameters_with_unknown_settings_are_shown() -> None:
    valuespec = convert_to_legacy_valuespec(
        form_spec_mail(Edition.COMMUNITY), translate_to_current_language
    )

    rendered = valuespec.value_to_html(
        {
            "from": {"address": "monitoring@example.com"},
            "smtp": {"smarthosts": ["mail.example.com"], "port": 25},
        }
    )

    assert "monitoring@example.com" in str(rendered)
