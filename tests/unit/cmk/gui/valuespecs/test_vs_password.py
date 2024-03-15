#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import base64
import hashlib

import pytest

import cmk.gui.valuespec as vs
from cmk.gui.http import request
from cmk.gui.utils.encrypter import Encrypter

from .utils import request_var


class TestValueSpecPassword:
    def test_mask(self) -> None:
        assert vs.Password().mask("elon") == "******"
        assert vs.Password().mask(None) == "******"

    def test_value_to_html(self) -> None:
        assert vs.Password().value_to_html("elon") == "******"
        assert vs.Password().value_to_html(None) == "none"

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(p="smth"):
            assert vs.Password(encrypt_value=False).from_html_vars("p") == "smth"

        with request_var(p_orig=base64.b64encode(Encrypter.encrypt("smth")).decode("ascii")):
            assert vs.Password().from_html_vars("p") == "smth"


def test_password_from_html_vars_initial_pw(request_context: None) -> None:
    request.set_var("pw_orig", "")
    request.set_var("pw", "abc")
    pw = vs.Password()
    assert pw.from_html_vars("pw") == "abc"


@pytest.mark.skipif(
    not hasattr(hashlib, "scrypt"), reason="OpenSSL version too old, must be >= 1.1"
)
def test_password_from_html_vars_unchanged_pw(request_context: None) -> None:
    request.set_var("pw_orig", base64.b64encode(Encrypter.encrypt("abc")).decode("ascii"))
    request.set_var("pw", "")
    pw = vs.Password()
    assert pw.from_html_vars("pw") == "abc"


@pytest.mark.skipif(
    not hasattr(hashlib, "scrypt"), reason="OpenSSL version too old, must be >= 1.1"
)
def test_password_from_html_vars_change_pw(request_context: None) -> None:
    request.set_var("pw_orig", base64.b64encode(Encrypter.encrypt("abc")).decode("ascii"))
    request.set_var("pw", "xyz")
    pw = vs.Password()
    assert pw.from_html_vars("pw") == "xyz"
