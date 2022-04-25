#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.exceptions import MKUserError
from cmk.gui.utils.user_errors import user_errors, UserErrors


def test_user_errors_request_context_integration(request_context) -> None:
    assert not user_errors
    user_errors.add(MKUserError(None, "abc"))
    assert user_errors[None] == "abc"


def test_user_errors_non_field_specific_error() -> None:
    errors = UserErrors()
    assert not errors

    errors.add(MKUserError(None, "abc"))

    assert errors
    assert errors[None] == "abc"


def test_user_errors_get() -> None:
    errors = UserErrors()
    errors.add(MKUserError("var", "abc"))
    assert errors["var"] == "abc"
    assert errors.get("var") == "abc"


def test_user_errors_get_not_existing() -> None:
    assert UserErrors().get("not_existing") is None


def test_user_errors_iter() -> None:
    errors = UserErrors()
    errors.add(MKUserError(None, "abc"))
    errors.add(MKUserError("ding", "aaa"))
    assert sorted(list(errors.values())) == sorted(["aaa", "abc"])


def test_user_errors_convert_exception_to_str() -> None:
    errors = UserErrors()
    assert not errors
    errors.add(MKUserError("ding", "Ding"))
    assert errors["ding"] == "Ding"


def test_user_errors_overwrite() -> None:
    errors = UserErrors()
    assert not errors
    errors.add(MKUserError("varname", "Ding"))
    assert errors["varname"] == "Ding"

    errors.add(MKUserError("varname", "Dong"))
    assert errors["varname"] == "Dong"
