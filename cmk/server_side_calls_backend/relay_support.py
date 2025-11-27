#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Linking to this from relay_support.bzl is quite a hack.
# I would prefer the bzl constant to be the source of truth
# and create this file during the build, but I can't figure out
# how to do that.

RELAY_SUPPORTED_PLUGIN_FAMILIES = [
    "lib",
    "netapp",
    "randomds",
]

RELAY_SUPPORTED_MODULES = ["cmk.plugins.%s" % family for family in RELAY_SUPPORTED_PLUGIN_FAMILIES]
