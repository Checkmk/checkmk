# coding=utf-8
# yapf: disable
import pytest
import os
import subprocess


def test_no_callsite():
    path = os.path.normpath(os.path.join(os.path.dirname(__file__), '../../../checks/*'))
    exit_code = subprocess.call("grep -l 'memory.include' %s" % path, shell=True)
    assert exit_code == 1  # nothing found
