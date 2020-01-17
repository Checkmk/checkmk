#!/usr/bin/env python
# encoding: utf-8

import subprocess


def test_dcd_exists(site):
    assert site.file_exists("bin/dcd")


def test_dcd_path(site):
    p = site.execute(["which", "dcd"], stdout=subprocess.PIPE)
    path = p.stdout.read().strip()
    assert path == "/omd/sites/%s/bin/dcd" % site.id


def test_dcd_version(site):
    p = site.execute(["dcd", "-V"], stdout=subprocess.PIPE)
    version = p.stdout.read()
    assert version.startswith("dcd version %s" % site.version.version)


def test_dcd_daemon(site):
    p = site.execute(["omd", "status", "--bare", "dcd"], stdout=subprocess.PIPE)
    assert p.wait() == 0
    assert p.stdout.read() == "dcd 0\nOVERALL 0\n"


def test_dcd_logrotate(site):
    assert site.file_exists("etc/logrotate.d/dcd")
