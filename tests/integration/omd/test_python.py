#!/usr/bin/env python
# encoding: utf-8

import os
import sys
import subprocess

def test_01_python_interpreter_exists(site):
    assert os.path.exists(site.root + "/bin/python")


def test_02_python_interpreter_path(site):
    p = site.execute(["which", "python"],
                     stdout=subprocess.PIPE)
    path = p.stdout.read().strip()
    assert path == "/omd/sites/%s/bin/python" % site.id


def test_03_python_interpreter_version(site):
    p = site.execute(["python", "-V"],
                     stderr=subprocess.PIPE)
    version = p.stderr.read()
    assert version.startswith("Python 2.7.16")


def test_03_python_path(site):
    p = site.execute(["python", "-c", "import sys ; print(sys.path)"],
                     stdout=subprocess.PIPE)
    sys_path = eval(p.stdout.read())
    assert sys_path[0] == ""
    assert site.root + "/local/lib/python" in sys_path
    assert site.root + "/lib/python" in sys_path
    assert site.root + "/lib/python2.7" in sys_path

    for p in sys_path:
        if p != "" and not p.startswith(site.root):
            raise Exception("Found non site path %s in sys.path" % p)


def test_01_pip_exists(site):
    assert os.path.exists(site.root + "/bin/pip")


def test_02_pip_path(site):
    p = site.execute(["which", "pip"],
                     stdout=subprocess.PIPE)
    path = p.stdout.read().strip()
    assert path == "/omd/sites/%s/bin/pip" % site.id


def test_03_pip_interpreter_version(site):
    p = site.execute(["pip", "-V"],
                     stdout=subprocess.PIPE)
    version = p.stdout.read()
    assert version.startswith("pip 10.")


def test_python_modules(site):
    test_modules = [
        "netsnmp",
        "pysphere",
        "ldap",
        "cryptography",
    ]

    import importlib
    for test_module_name in test_modules:
        module = importlib.import_module(test_module_name)
        assert module.__file__.startswith(site.root)
