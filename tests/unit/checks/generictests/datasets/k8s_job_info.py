#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore


checkname = "k8s_job_info"


parsed = {"active": 1, "failed": 1, "succeeded": 1}


discovery = {"": [(None, {})]}


checks = {"": [(None, {}, [(2, "Running: 1/3, Failed: 1, Succeeded: 1", [])])]}
