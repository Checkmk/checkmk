#!/usr/bin/python
# encoding: utf-8

import os
import sys
import glob
import tempfile

from testlib import cmk_path, cmc_path, cme_path
import testlib.pylint_cmk as pylint_cmk

def get_web_plugin_dirs():
    plugin_dirs = sorted(list(set(os.listdir(cmk_path() + "/web/plugins")
                                + os.listdir(cmc_path() + "/web/plugins")
                                + os.listdir(cme_path() + "/web/plugins"))))
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

            module_path = pylint_test_dir + "/" + module_name + ".py"

            # In case a module has already been moved to cmk.gui and there are plugins
            # that have not been moved yet get the main module code from cmk.gui
            if not os.path.exists(module_path):
                module = file(module_path, "a")

                if os.path.exists(cmk_path() + "/cmk/gui/" + module_name + ".py"):
                    module_main_path = cmk_path() + "/cmk/gui/" + module_name + ".py"
                elif os.path.exists(cmk_path() + "/cmk/gui/cee/" + module_name + ".py"):
                    module_main_path = cmk_path() + "/cmk/gui/cee/" + module_name + ".py"
                elif os.path.exists(cmk_path() + "/cmk/gui/cme/" + module_name + ".py"):
                    module_main_path = cmk_path() + "/cmk/gui/cme/" + module_name + ".py"
                else:
                    raise Exception()

                pylint_cmk.add_file(module, module_main_path)

            print("[%s] add %s" % (module_name, plugin_path))
            with open(module_path, "a") as module:
                pylint_cmk.add_file(module, plugin_path)

    exit_code = pylint_cmk.run_pylint(pylint_test_dir)
    assert exit_code == 0, "PyLint found an error in the web code"
