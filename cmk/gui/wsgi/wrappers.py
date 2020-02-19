#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from connexion import ProblemException  # type: ignore[import]


class ProblemKeyError(ProblemException, KeyError):  # pylint: disable=too-many-ancestors
    """Composite Exception representing a connexion ProblemException and a dict KeyError"""
    pass


class ParameterDict(dict):
    def __getitem__(self, key):
        if key in self:
            rv = dict.__getitem__(self, key)
            if isinstance(rv, dict):
                rv = ParameterDict(rv)
            return rv
        raise ProblemKeyError(400, "Bad request", "Parameter missing: %s" % (key,))
