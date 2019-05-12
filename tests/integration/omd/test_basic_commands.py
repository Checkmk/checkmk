#!/usr/bin/env python
# encoding: utf-8

import os
import stat


def test_basic_commands(site):
    commands = [
        "bin/mkp",
        "bin/check_mk",
        "bin/cmk",
        "bin/omd",
        "bin/stunnel",
        "bin/cmk-update-config",
    ]

    for rel_path in commands:
        path = os.path.join(site.root, rel_path)
        assert os.path.exists(path)
