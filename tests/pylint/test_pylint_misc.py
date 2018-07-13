#!/usr/bin/python
# encoding: utf-8

import os
import sys

from testlib import cmk_path, cmc_path, cme_path
import testlib.pylint_cmk as pylint_cmk

def test_pylint_misc():
    # Only specify the path to python packages or modules here
    modules_or_packages = [
        # Check_MK base
        "cmk_base",
        "cmk_base/modes",
        "cmk_base/automations",
        "cmk_base/default_config",
        "cmk_base/data_sources",
        "enterprise/cmk_base/cee",
        "enterprise/cmk_base/modes/cee.py",
        "enterprise/cmk_base/automations/cee.py",
        "enterprise/cmk_base/default_config/cee.py",
        "managed/cmk_base/default_config/cme.py",

        # cmk module level
        "cmk",
        "cmk/ec",
        "enterprise/cmk/cee",
        "enterprise/cmk/cee/liveproxy",

        # GUI specific
        "web/app/index.wsgi",
        "cmk/gui",
        "enterprise/cmk/gui/cee",
        "managed/cmk/gui/cme",
    ]

    # We use our own search logic to find scripts without python extension
    search_paths = [
        "omd/packages/omd",
        "bin",
        "notifications",
        "agents/plugins",
        "agents/special",
        "active_checks",
        "enterprise/agents/plugins",
        "enterprise/bin",
        "enterprise/misc",
    ]

    for path in search_paths:
        for fname in pylint_cmk.get_pylint_files(path, "*"):
           modules_or_packages.append(path + "/" + fname)

    exit_code = pylint_cmk.run_pylint(cmk_path(), modules_or_packages)
    assert exit_code == 0, "PyLint found an error"
