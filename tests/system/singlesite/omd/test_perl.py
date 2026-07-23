#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import subprocess
from pathlib import Path

from tests.testlib.site import Site


def test_perl_modules(site: Site) -> None:
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
        "RRDs",
    ]

    for module in test_modules:
        try:
            _ = site.run(["perl", "-e", "use %s" % module])
        except subprocess.CalledProcessError as excp:
            excp.add_note(f"Failed to load module: %{module}!")
            raise excp


def test_utils_pm(site: Site) -> None:
    symlink = Path(site.root) / "lib/perl5/utils.pm"
    lib_path = Path(site.root) / "lib"
    target = lib_path.resolve() / "nagios/plugins/utils.pm"
    assert symlink.is_symlink(), "utils.pm is not a symlink"
    assert symlink.resolve() == target, "utils.pm does not point to the expect file"
