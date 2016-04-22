#!/usr/bin/python
# Library for pylint checks of Check_MK

import os
import shutil
import tempfile

def ordered_module_files():
    modules = [
        "../defaults",
        "../modules/check_mk_base.py",
        "../modules/check_mk.py",
        "../modules/config.py",
        "../modules/discovery.py",
        "../modules/snmp.py",
        "../modules/agent_simulator.py",
        "../modules/notify.py",
        "../modules/events.py",
        "../modules/nagios.py",
        "../modules/catalog.py",
        "../modules/packaging.py",
        "../modules/prediction.py",
        "../modules/automation.py",
        "../modules/inventory.py",
        "../modules/compresslog.py",
        "../modules/localize.py",
        "../../cmc/modules/real_time_checks.py",
        "../../cmc/modules/alert_handling.py",
        "../../cmc/modules/keepalive.py",
        "../../cmc/modules/cmc.py",
        "../../cmc/modules/inline_snmp.py",
        "../../cmc/modules/agent_bakery.py",
        "../../cmc/modules/cap.py",
        "../../cmc/modules/rrd.py",
    ]

    # Add modules which are not specified above
    for path in module_files():
        if path not in modules:
            modules.append(path)

    return modules


def module_files():
    modules = sorted([ "../modules/" + f for f in os.listdir("../modules")
                         if not f.startswith(".") ])
    modules += sorted([ "../../cmc/modules/" + f for f in os.listdir("../../cmc/modules")
                         if not f.startswith(".") ])
    return modules


def check_files():
    filelist = sorted([ "../checks/" + f for f in os.listdir("../checks")
                         if not f.startswith(".") ])

    # Sort: first includes, then other
    filelist = [ f for f in filelist if f.endswith(".include") ] + \
               [ f for f in filelist if not f.endswith(".include") ]

    return filelist


def add_file(f, path):
    f.write("\n")
    f.write("#\n")
    f.write("# " + path + "\n")
    f.write("#\n")
    f.write("\n")
    f.write(file(path).read())


def get_test_dir():
    base_path = tempfile.mkdtemp(prefix="cmk_pylint")
    print("Prepare check in %s..." % base_path)
    return base_path


def run_pylint(cfg_file, base_path):
    cmd = "pylint --rcfile=\"%s\" %s/*.py" % (cfg_file, base_path)
    print("Starting pylint with: %s" % cmd)
    exit_code = os.system(cmd) >> 8

    if exit_code == 0:
        print("Removing build path...")
        shutil.rmtree(base_path)

    return exit_code

