#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def cisco_sensor_item(description, sensor_id):
    # trial_string can be:
    # Empty
    # A single string
    # A string seperated by commas with status information
    # -> Depends on the device model
    try:
        splitted = [x.strip() for x in description.split(",")]
        if len(splitted) == 1:
            item = description
        elif "#" in splitted[-1] or "Power" in splitted[-1]:
            item = " ".join(splitted)
        elif splitted[-1].startswith("PS"):
            item = " ".join([splitted[0], splitted[-1].split(" ")[0]])
        elif splitted[-2].startswith("PS"):
            item = " ".join(splitted[:-2] + splitted[-2].split(" ")[:-1])
        elif splitted[-2].startswith("Status"):
            item = " ".join(splitted[:-2])
        else:
            item = " ".join(splitted[:-1])

        # Different sensors may have identical descriptions. To prevent
        # duplicate items the sensor_id is appended. This leads to
        # redundant information sensors are enumerated with letters like
        # e.g. "PSA" and "PSB", but to be backwards compatible we do not
        # modify this behaviour.
        if not item[-1].isdigit():
            item += " " + sensor_id

        return item.replace("#", " ")
    except Exception:
        return sensor_id
