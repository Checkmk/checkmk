#!/usr/bin/python
# encoding: utf-8

import os
import sys
import glob
import tempfile
import pytest

from testlib import cmk_path, cmc_path, cme_path
import testlib.pylint_cmk as pylint_cmk

# Mark all tests in this file to be pylint checks
pytestmark = pytest.mark.pylint

def get_web_plugin_dirs():
    plugin_dirs = sorted(list(set(os.listdir(cmk_path() + "/web/plugins")
                                + os.listdir(cmc_path() + "/web/plugins")
                                + os.listdir(cme_path() + "/web/plugins"))))

    # icons are included from a plugin of views module. Move to the end to
    # make them be imported after the views plugins. Same for perfometers.
    plugin_dirs.remove("icons")
    plugin_dirs.append("icons")
    plugin_dirs.remove("perfometer")
    plugin_dirs.append("perfometer")
    return plugin_dirs


def get_plugin_files(plugin_dir):
    files = []

    for path in [ cmk_path() + "/web/plugins/" + plugin_dir,
                  cmc_path() + "/web/plugins/" + plugin_dir,
                  cme_path() + "/web/plugins/" + plugin_dir ]:
        if os.path.exists(path):
            files += [ (f, path) for f in os.listdir(path) ]

    return sorted(files)


def test_pylint_web(pylint_test_dir):
    # Make compiled files import eachother by default
    sys.path.insert(0, pylint_test_dir)

    modules = glob.glob(cmk_path() + "/web/htdocs/*.py") \
            + glob.glob(cmc_path() + "/web/htdocs/*.py") \
            + glob.glob(cme_path() + "/web/htdocs/*.py")

    for module in modules:
        print("Copy %s to test directory" % module)
        f = open(pylint_test_dir + "/" + os.path.basename(module), "w")
        pylint_cmk.add_file(f, module)
        f.close()

    # Move the whole plugins code to their modules, then
    # run pylint only on the modules
    for plugin_dir in get_web_plugin_dirs():
        files = get_plugin_files(plugin_dir)

        for plugin_file, plugin_base in files:
            plugin_path = plugin_base +"/"+plugin_file

            if plugin_file.startswith('.'):
                continue
            elif plugin_dir in ["icons","perfometer"]:
                module_name = "views"
            elif plugin_dir == "pages":
                module_name = "modules"
            else:
                module_name = plugin_dir

            print("[%s] add %s" % (module_name, plugin_path))
            module = file(pylint_test_dir + "/" + module_name + ".py", "a")
            pylint_cmk.add_file(module, plugin_path)
            module.close()

    exit_code = pylint_cmk.run_pylint(pylint_test_dir)
    assert exit_code == 0, "PyLint found an error in the web code"
