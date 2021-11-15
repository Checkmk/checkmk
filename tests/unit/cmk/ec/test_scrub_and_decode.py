#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.ec.main


def test_scrub_and_decode():
    result = cmk.ec.main.scrub_and_decode("0123bla\nbla\tbla\0blub\1buh\2boh\3")
    assert result == "0123blabla blablubbuhboh\3"
    assert isinstance(result, str)

    result = cmk.ec.main.scrub_and_decode("0123bla\nbla\tbla\0blub\1buh\2boh\3")
    assert result == "0123blabla blablubbuhboh\3"
    assert isinstance(result, str)
