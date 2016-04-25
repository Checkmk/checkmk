#!/usr/bin/python
# Library for pylint checks of Check_MK

import os
import sys
import glob
import shutil
import subprocess
import tempfile

from pylint.reporters.text import ColorizedTextReporter, ParseableTextReporter
from pylint.utils import Message


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
    # Change path to be relative to "workdir" /home/git or the workdir
    # in the build system.
    relpath = os.path.relpath(os.path.realpath(path),
                              os.path.dirname(os.path.dirname(os.getcwd())))
    f.write("\n")
    f.write("#\n")
    f.write("# ORIG-FILE: " + relpath + "\n")
    f.write("#\n")
    f.write("\n")
    f.write(file(path).read())


def get_test_dir():
    base_path = os.environ.get("WORKDIR")
    if base_path:
        base_path += "/" + os.path.basename(sys.argv[0])
        os.makedirs(base_path)
    else:
        base_path = tempfile.mkdtemp(prefix="cmk_pylint")

    print("Prepare check in %s ..." % base_path)
    return base_path


def run_pylint(base_path):
    pylint_args = os.environ.get("PYLINT_ARGS", "")
    if pylint_args:
        pylint_args += " "
    pylint_output = os.environ.get("PYLINT_OUTPUT")

    pylint_cfg = os.getcwd() + "/pylintrc"

    os.putenv("PYLINT_PATH", os.getcwd())
    cmd = "pylint --rcfile=\"%s\" %s*.py" % (pylint_cfg, pylint_args)
    print("Running pylint with: %s" % cmd)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         shell=True, cwd=base_path)
    stdout = p.communicate()[0]

    if stdout.strip():
        if pylint_output:
            file(pylint_output, "a").write(stdout)
        else:
            print(stdout)

    exit_code = p.returncode
    print("Finished with exit code: %d" % exit_code)

    if exit_code == 0:
        # Don't remove directory when specified via WORKDIR env
        if not os.environ.get("WORKDIR"):
            print("Removing build path...")
            shutil.rmtree(base_path)

    return exit_code


def ensure_equal_branches():
    cmk_branch = os.popen("git rev-parse --abbrev-ref HEAD").read().strip()
    cmc_branch = os.popen("cd ../../cmc ; "
                          "git rev-parse --abbrev-ref HEAD").read().strip()
    if cmk_branch != cmc_branch:
        sys.stderr.write("ERROR: Different branches (%s != %s)\n" %
                                              (cmk_branch, cmc_branch))
        sys.exit(1)



# Check_MK currently uses a packed version of it's files to
# run the pylint tests because it's not well structured in
# python modules. This custom reporter rewrites the found
# messages to tell the users the original location in the
# python sources
class CMKFixFileMixin(object):
    def handle_message(self, msg):
        lines = file(msg.abspath).readlines()

        line_nr = msg.line
        orig_file, went_back = None, -3
        while line_nr > 0:
            line_nr -= 1
            went_back += 1
            line = lines[line_nr]
            if line.startswith("# ORIG-FILE: "):
                orig_file = line.split(": ", 1)[1].strip()
                break

        if orig_file != None:
            msg = msg._replace(line=went_back, path=orig_file)

        super(CMKFixFileMixin, self).handle_message(msg)



class CMKColorizedTextReporter(CMKFixFileMixin, ColorizedTextReporter):
    name = "cmk_colorized"



class CMKParseableTextReporter(CMKFixFileMixin, ParseableTextReporter):
    name = "cmk_parseable"



# Is called by pylint to load this plugin
def register(linter):
    sys.path = glob.glob("/omd/versions/default/lib/python/*.egg") \
               + [ "/omd/versions/default/lib/python" ] \
               + sys.path

    linter.register_reporter(CMKColorizedTextReporter)
    linter.register_reporter(CMKParseableTextReporter)
