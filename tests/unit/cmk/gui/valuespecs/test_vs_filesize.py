#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.valuespec as vs
from cmk.gui.exceptions import MKUserError

from .utils import request_var


class TestFilesize:
    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(f_size="5", f_unit="2"):
            assert vs.Filesize().from_html_vars("f") == 5 * 1024 * 1024
        # TODO: either base it on Float instead of Integer, or do not allow the
        # following behaviour:
        with request_var(f_size="5.2", f_unit="2"):
            assert vs.Filesize().from_html_vars("f") == int(5.2 * 1024 * 1024)
        with request_var(f_size="not_a_number", f_unit="2"):
            with pytest.raises(MKUserError, match='The parameter "f_size" is not a float.'):
                vs.Filesize().from_html_vars("f")

    def test_to_html(self):
        assert vs.Filesize().value_to_html(2 * 1024 * 1024) == "2 MiB"
        assert vs.Filesize().value_to_html(0) == "0 Byte"
        with pytest.raises(ValueError, match="Invalid value: "):
            vs.Filesize().value_to_html(0.1)  # type: ignore[arg-type]

    def test_to_json(self):
        assert vs.Filesize().value_to_json(20) == 20

    def test_from_json(self):
        assert vs.Filesize().value_from_json(20) == 20
        # TODO: see other example with 5.2
        assert vs.Filesize().value_from_json(5.2) == 5.2
