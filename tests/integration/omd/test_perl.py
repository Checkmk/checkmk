#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.site import Site


def test_perl_modules(site: Site):
    # TODO: Complete this list
    test_modules = [
        "Getopt::Long",
        "File::stat",
        "File::Find",
        "File::Path",
        "SNMP",
        "Nagios::Plugin",
        "Test::Simple",
        "Try::Tiny",
        "Params::Validate",
        "Module::Runtime",
        "Module::Metadata",
        "Module::Implementation",
        "Module::Build",
        "Math::Calc::Units",
        "Config::Tiny",
        "Class::Accessor",
    ]

    for module in test_modules:
        p = site.execute(["perl", "-e", "use %s" % module])
        assert p.wait() == 0, "Failed to load module: %s" % module
