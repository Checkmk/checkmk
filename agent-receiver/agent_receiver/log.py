#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

from agent_receiver.constants import LOG_FILE

handler = logging.FileHandler(LOG_FILE, encoding="UTF-8")
formatter = logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s")
handler.setFormatter(formatter)

logger = logging.getLogger("agent-receiver")
logger.addHandler(handler)
logger.setLevel(logging.INFO)
