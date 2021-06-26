#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils import password_store
from cmk.utils.exceptions import MKGeneralException

PW_STORE = "pw_from_store"
PW_EXPL = "pw_explicit"
PW_STORE_KEY = "from_store"


def load_patch():
    return {PW_STORE_KEY: PW_STORE}


@pytest.mark.parametrize("password_id, password_actual", [(("password", PW_EXPL), PW_EXPL),
                                                          (("store", PW_STORE_KEY), PW_STORE),
                                                          (PW_STORE_KEY, PW_STORE)])
def test_extract(monkeypatch, password_id, password_actual):
    monkeypatch.setattr(password_store, "load", load_patch)
    assert password_store.extract(password_id) == password_actual


def test_extract_from_unknown_valuespec():
    password_id = ("unknown", "unknown_pw")
    with pytest.raises(MKGeneralException) as excinfo:
        password_store.extract(password_id)
    assert "Unknown password type." in str(excinfo.value)
