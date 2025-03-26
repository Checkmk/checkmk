#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import astroid  # type: ignore[import-untyped]
import pytest
from pylint.lint import PyLinter
from pytest_mock import MockerFixture

from tests.pylint.checker_localization import HTMLTagsChecker, LiteralStringChecker


# Using astroid within a pytest context causes recursion errors. This fixture avoids these errors,
# but with unknown side effects.
# https://github.com/schemathesis/schemathesis/issues/2170
# https://github.com/pylint-dev/astroid/issues/2427
@pytest.fixture(autouse=True)
def deactivate_astroid_bootstrapping(mocker: MockerFixture) -> None:
    mocker.patch.object(astroid.raw_building.InspectBuilder, "bootstrapped", True)


@pytest.mark.parametrize(
    ["code", "is_error"],
    [
        pytest.param("_('abc')", False),
        pytest.param("_(x)", True),
        pytest.param("_l('%s' % '123')", True),
        pytest.param("_l('%s text')", False),
        pytest.param("_l('{argl} text')", False),
        pytest.param("_(f'{argl} text')", True),
    ],
)
def test_literal_string_checker(
    code: str,
    is_error: bool,
) -> None:
    assert bool(LiteralStringChecker(PyLinter()).check(astroid.extract_node(code))) is is_error


@pytest.mark.parametrize(
    ["code", "is_error"],
    [
        pytest.param("_('abc')", False),
        pytest.param("_l('<tt>bold</tt>')", False),
        pytest.param("_('* ? <a href=\"%s\">%s</a>')", False),
        pytest.param(
            '_(\'&copy; <a target="_blank" href="https://checkmk.com">Checkmk GmbH</a>\')', False
        ),
        pytest.param("_('123 <script>injection</script>')", True),
    ],
)
def test_html_tags_checker(
    code: str,
    is_error: bool,
) -> None:
    assert bool(HTMLTagsChecker(PyLinter()).check(astroid.extract_node(code))) is is_error
