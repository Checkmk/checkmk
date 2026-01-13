#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.wato.check_parameters.ps import (
    forbid_re_delimiters_inside_groups,
    validate_process_discovery_descr_option,
)


@pytest.mark.parametrize("pattern", ["(test)$", "foo\\b", "^bar", "\\bfoo\\b", "(a)\\b"])
def test_validate_ps_allowed_regex(pattern: str) -> None:
    forbid_re_delimiters_inside_groups(pattern, "")


@pytest.mark.parametrize("pattern", ["(test$)", "(foo\\b)", "(^bar)", "(\\bfoo\\b)"])
def test_validate_ps_forbidden_regex(pattern: str) -> None:
    with pytest.raises(MKUserError):
        forbid_re_delimiters_inside_groups(pattern, "")


@pytest.mark.parametrize("description", ["%s%5"])
def test_validate_process_discovery_descr_option(
    description: str,
) -> None:
    with pytest.raises(MKUserError):
        validate_process_discovery_descr_option(description, "")
