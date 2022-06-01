#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def scan_ibm_tape_library(oid):
    return oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.32925.1")


def ibm_tape_library_parse_device_name(name):
    # strange name format:IBM     ULT3580-TD6     00078B5F0F
    return " ".join([part for part in name.split() if part])


def ibm_tape_library_get_device_state(avail, status):
    # check states suggested by customer
    mapping = {
        "avail": {
            "1": (1, "other"),
            "2": (3, "unknown"),
            "3": (0, "running full power"),
            "4": (1, "warning"),
            "5": (1, "in test"),
            "6": (3, "not applicable"),
            "7": (1, "power off"),
            "8": (1, "off line"),
            "9": (1, "off duty"),
            "10": (1, "degraded"),
            "11": (1, "not installed"),
            "12": (2, "install error"),
            "13": (3, "power save unknown"),
            "14": (0, "power save low power mode"),
            "15": (0, "power save standby"),
            "16": (1, "power cycle"),
            "17": (1, "power save warning"),
            "18": (1, "paused"),
            "19": (1, "not ready"),
            "20": (1, "not configured"),
            "21": (1, "quiesced"),
        },
        "status": {
            "0": (3, "unknown"),
            "1": (1, "other"),
            "2": (0, "ok"),
            "3": (1, "degraded"),
            "4": (1, "stressed"),
            "5": (1, "predictive failure"),
            "6": (2, "error"),
            "7": (2, "non-recoverable error"),
            "8": (1, "starting"),
            "9": (1, "stopping"),
            "10": (1, "stopped "),
            "11": (1, "in service"),
            "12": (3, "no contact"),
            "13": (3, "lost communication"),
            "14": (2, "aborted"),
            "15": (1, "dormant"),
            "16": (2, "supporting entity in error"),
            "17": (1, "completed"),
            "18": (1, "power mode"),
            "19": (1, "dMTF reserved"),
            "32768": (3, "vendor reserved"),
        },
    }
    for what, val, text in [("avail", avail, "Availability"), ("status", status, "Status")]:
        state, state_readable = mapping[what][val]
        yield state, "%s: %s" % (text, state_readable)
