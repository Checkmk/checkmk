#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ruleset_matcher.tuple_rulesets import in_extraconf_hostlist


def test_in_extraconf_hostlist_invalid_regex_is_raised_under_debug() -> None:
    with pytest.raises(MKGeneralException, match="Invalid regular expression"):
        in_extraconf_hostlist(["~("], "host1", debug=True)


def test_in_extraconf_hostlist_invalid_regex_matches_nothing_without_debug() -> None:
    assert in_extraconf_hostlist(["~("], "host1", debug=False) is False
