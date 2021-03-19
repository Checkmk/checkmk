#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# flake8: noqa

import os
import subprocess
import pytest  # type: ignore[import]


def test_01_python_interpreter_exists(site):
    assert os.path.exists(site.root + "/bin/python3")


def test_02_python_interpreter_path(site):
    p = site.execute(["which", "python3"], stdout=subprocess.PIPE)
    path = p.stdout.read().strip()
    assert path == "/omd/sites/%s/bin/python3" % site.id


def test_03_python_interpreter_version(site):
    p = site.execute(["python3", "-V"], stdout=subprocess.PIPE)
    version = p.stdout.read()
    assert version.startswith("Python 3.8.7")


def test_03_python_path(site):
    p = site.execute(["python3", "-c", "import sys ; print(sys.path)"], stdout=subprocess.PIPE)
    sys_path = eval(p.stdout.read())
    assert sys_path[0] == ""
    assert site.root + "/local/lib/python3" in sys_path
    assert site.root + "/lib/python3" in sys_path
    assert site.root + "/lib/python3.8" in sys_path

    for p in sys_path:
        if p != "" and not p.startswith(site.root):
            raise Exception("Found non site path %s in sys.path" % p)


def test_01_pip_exists(site):
    assert os.path.exists(site.root + "/bin/pip3")


def test_02_pip_path(site):
    p = site.execute(["which", "pip3"], stdout=subprocess.PIPE)
    path = p.stdout.read().strip()
    assert path == "/omd/sites/%s/bin/pip3" % site.id


def test_03_pip_interpreter_version(site):
    p = site.execute(["pip3", "-V"], stdout=subprocess.PIPE)
    version = p.stdout.read()
    assert version.startswith("pip 20.2.3")


# TODO: Improve this test to automatically adapt the expected modules from our Pipfile
@pytest.mark.parametrize("module_name", [
    "netsnmp",
    "ldap",
    "OpenSSL",
    "cryptography",
    "pysmi",
    "pysnmp",
    "ldap",
    "pymysql",
    "psycopg2",
    "dicttoxml",
    "enum",
    "PIL",
    "reportlab",
    "PyPDF2",
    "psutil",
    "ipaddress",
    "requests",
    "paramiko",
    "pyghmi",
    "typing",
    "dateutil",
    "snap7",
    "rrdtool",
    "werkzeug",
    "boto3",
    "kubernetes",
    "numpy",
])
def test_python_modules(site, module_name):
    import importlib  # pylint: disable=import-outside-toplevel
    module = importlib.import_module(module_name)
    assert module.__file__.startswith(site.root)


def test_python_preferred_encoding():
    import locale  # pylint: disable=import-outside-toplevel
    assert locale.getpreferredencoding() == "UTF-8"
