#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

import pytest

from cmk.astrein.checkers.localization_named_placeholder import LocalizationNamedPlaceholderChecker


def _errors(code: str) -> list[str]:
    checker = LocalizationNamedPlaceholderChecker(Path("test/test.py"), Path("test"), code)
    return [error.message for error in checker.check(ast.parse(code))]


@pytest.mark.parametrize(
    ["code", "is_error"],
    [
        pytest.param('_("%s in %s")', True, id="positional_percent_s"),
        pytest.param('_("%d hosts")', True, id="positional_percent_d"),
        pytest.param('Title("%s")', True, id="formspec_title_positional"),
        pytest.param(
            'Message("added %(count)d, removed %s")', True, id="mixed_named_and_positional"
        ),
        pytest.param('ngettext("%s host", "%s hosts", n)', True, id="ngettext_plural_positional"),
        pytest.param('pgettext("ctx", "%s down")', True, id="pgettext_message_positional"),
        pytest.param('_("%(host)s in %(site)s")', False, id="named_ok"),
        pytest.param('_("no placeholder at all")', False, id="no_placeholder_ok"),
        pytest.param('_("100%% done")', False, id="escaped_percent_ok"),
        pytest.param('Title("%(count)d items")', False, id="formspec_named_ok"),
        pytest.param('logger.info("%s", x)', False, id="non_translation_call_ignored"),
        pytest.param('foo("%s")', False, id="unrelated_function_ignored"),
    ],
)
def test_named_placeholder_checker(code: str, is_error: bool) -> None:
    errors = _errors(code)
    if is_error:
        assert errors, f"Expected error for: {code}"
        assert "named `%(name)s` placeholders" in errors[0]
    else:
        assert not errors, f"Unexpected error for: {code}"


def test_reports_once_per_call() -> None:
    assert len(_errors('_("%s and %s and %s")')) == 1


@pytest.mark.parametrize(
    "code",
    [
        pytest.param(
            '_("%s in %s")  # astrein: disable=localization-named-placeholder',
            id="suppress_same_line",
        ),
        pytest.param(
            "# astrein: disable=localization-named-placeholder\n_('%s in %s')",
            id="suppress_line_above",
        ),
    ],
)
def test_suppression_comment(code: str) -> None:
    assert not _errors(code)
