#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os


def get_omd_config(key):
    for l in open(os.environ["OMD_ROOT"] + "/etc/omd/site.conf"):
        if l.startswith(key + "="):
            return l.split("=")[-1].strip("'\n")
    return None


def get_apache_port():
    port = get_omd_config("CONFIG_APACHE_TCP_PORT")
    if port is None:
        return 80
    return int(port)
