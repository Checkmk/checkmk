#!/usr/bin/env python
# encoding: utf-8

import subprocess


def test_locales(site):
    p = site.execute(["locale"], stdout=subprocess.PIPE)
    output = p.communicate()[0]

    assert "LANG=C.UTF-8" in output \
        or "LANG=en_US.utf8" in output

    assert "LC_ALL=C.UTF-8" in output \
        or "LC_ALL=en_US.utf8" in output
