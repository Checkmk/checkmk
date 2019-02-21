#!/usr/bin/python
# encoding: utf-8

import os
import glob
import pytest
from testlib import cmk_path, cmc_path


def test_find_debug_code():
    scanned = 0
    for base_path in [cmk_path(), cmc_path()]:
        for dirpath, dirnames, filenames in os.walk("%s/web" % base_path):
            scanned += 1
            for filename in filenames:
                path = "%s/%s" % (dirpath, filename)

                for line in open(path):
                    l = line.lstrip()
                    assert not l.startswith("html.debug("), \
                        "Found \"html.debug(...)\" call"

    assert scanned > 0
