#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

from flask import request


class PrependURLFilter(logging.Filter):
    def filter(self, record):
        if record.levelno >= logging.ERROR:
            record.msg = f"{request.url} {record.msg}"
        return True
