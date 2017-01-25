#!/usr/bin/python
# encoding: utf-8

import os
import sys
import tempfile
import pytest

import testlib.pylint_cmk as pylint_cmk

# Mark all tests in this file to be pylint checks
pytestmark = pytest.mark.pylint

def test_pylint_modules():
    base_path = pylint_cmk.get_test_dir()

    f = file(base_path + "/cmk-modules.py", "w")
    for path in pylint_cmk.ordered_module_files():
        pylint_cmk.add_file(f, path)
    f.close()

    exit_code = pylint_cmk.run_pylint(base_path, cleanup_test_dir=True)
    assert exit_code == 0, "PyLint found an error in modules"
