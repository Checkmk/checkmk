#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import cmk.gui.htmllib  # noqa: F401 pylint: disable=unused-import


class Bla:
    def to_json(self):
        return {"class": "Bla"}


def test_to_json():
    assert json.dumps(Bla()) == '{"class": "Bla"}'


def test_forward_slash_escape():
    assert json.dumps("<script>alert(1)</script>") == '"<script>alert(1)<\\/script>"'
