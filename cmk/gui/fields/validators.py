#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from marshmallow import ValidationError
from marshmallow.validate import Validator

import cmk.utils.regex

HOST_NAME_RE = cmk.utils.regex.regex(cmk.utils.regex.REGEX_HOST_NAME)


class ValidateHostName(Validator):
    def __call__(self, value, **kwargs):
        if HOST_NAME_RE.match(value):
            return True

        raise ValidationError(
            f"Hostname {value!r} doesn't match pattern '^{HOST_NAME_RE.pattern}$'"
        )
