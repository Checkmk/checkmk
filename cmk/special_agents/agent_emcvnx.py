#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# command reference for naviseccli
# http://corpusweb130.emc.com/upd_prod_VNX/UPDFinalPDF/jp/Command_Reference_for_Block.pdf

# commands to be issued
# naviseccli -h 10.1.36.13 -User XXXX -Password XXXX -Scope0 getall < -sp>
# naviseccli -h 10.1.36.13 -User XXXX -Password XXXX -Scope0 getall < -disk>
# naviseccli -h 10.1.36.13 -User XXXX -Password XXXX -Scope0 getall < -array>
# naviseccli -h 10.1.36.13 -User XXXX -Password XXXX -Scope0 getall < -lun>

# command generic (rest less important)
# naviseccli -h 10.1.36.13 -User XXXX -Password XXXX -Scope0 getall <-host>
# < -array><-hba ><-sp><-cache><-disk><-lun><-rg><-sg>
# <-mirrorview><-snapviews><-sancopy><-reserved> <-cloneview><-metalun>
# <-migration><-ioportconfig> <-fastcache><-backendbus>

import cProfile
import getopt
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from cmk.utils.password_store import replace_passwords


def usage():
    sys.stderr.write(
        """Check_MK EMC VNX Agent

USAGE: agent_emcvnx [OPTIONS] HOST
       agent_emcvnx -h

ARGUMENTS:
  HOST                          Host name or IP address of the target SP

OPTIONS:
  -h, --help                    Show this help message and exit
  -u USER, --user USER          Username for EMC VNX login
  -p PASSWORD, --password PASSWORD  Password for EMC VNX login

                                If you do not give USER and PASSWORD:
                                We try to use naviseccli with security files.
                                These need to be created in advance by running as
                                the instance user:
                                naviseccli -AddUserSecurity -scope 0 -password PASSWORD -user USER

  --debug                       Debug mode: write some debug messages,
                                let Python exceptions come through

  --profile                     Enable performance profiling in Python source code

  -i MODULES, --modules MODULES Modules to query. This is a comma separated list of
                                which may contain the keywords "disks", "hba", "hwstatus",
                                "raidgroups", "agent" or "all" to define which information
                                should be queried from the SP. You can define to use only
                                view of them to optimize performance. The default is "all".

"""
    )


#############################################################################
# command line options
#############################################################################


def _run_cmd(debug: bool, cmd: str) -> list[str]:
    if debug:
        sys.stderr.write("executing external command: %s\n" % cmd)

    return subprocess.run(
        shlex.split(cmd),
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
        check=False,
        encoding="utf-8",
    ).stdout.splitlines(keepends=True)


def normalize_str(line: str) -> str:
    return line.rstrip("\n").rstrip("\r")


def main(sys_argv=None):
    if sys_argv is None:
        replace_passwords()
        sys_argv = sys.argv[1:]

    short_options = "hu:p:t:m:i:"
    long_options = ["help", "user=", "password=", "debug", "timeout=", "profile", "modules="]

    try:
        opts, args = getopt.getopt(sys_argv, short_options, long_options)
    except getopt.GetoptError as err:
        sys.stderr.write("%s\n" % err)
        sys.exit(1)

    opt_debug = False
    _opt_timeout = 60

    g_profile = None

    host_address = None
    user = None
    password = None
    mortypes = ["all"]
    fetch_agent_info = False

    naviseccli_options: dict[str, dict[str, Any]] = {
        "disks": {"cmd_options": [(None, "getall -disk")], "active": False, "sep": None},
        "hba": {"cmd_options": [(None, "getall -hba")], "active": False, "sep": None},
        "hwstatus": {"cmd_options": [(None, "getall -array")], "active": False, "sep": None},
        "raidgroups": {"cmd_options": [(None, "getall -rg")], "active": False, "sep": None},
        #   "agent-info"    : {"cmd_options" : [(None, "-sp")],               "active" : False, "sep" : None},
        "sp_util": {"cmd_options": [(None, "getcontrol -cbt")], "active": False, "sep": 58},
        "writecache": {"cmd_options": [(None, "getcache -wst")], "active": False, "sep": None},
        "mirrorview": {"cmd_options": [(None, "mirrorview -list")], "active": False, "sep": 58},
        "storage_pools": {
            "cmd_options": [
                ("storage_pools", "storagepool -list -all"),
                ("auto_tiering", "autoTiering -info -opStatus -loadBalance"),
            ],
            "active": False,
            "sep": 58,
        },
    }

    for o, a in opts:
        if o in ["--debug"]:
            opt_debug = True
        elif o in ["--profile"]:
            g_profile = cProfile.Profile()
            g_profile.enable()
        elif o in ["-u", "--user"]:
            user = a
        elif o in ["-p", "--password"]:
            password = a
        elif o in ["-i", "--modules"]:
            mortypes = a.split(",")
        elif o in ["-t", "--timeout"]:
            _opt_timeout = int(a)
        elif o in ["-h", "--help"]:
            usage()
            sys.exit(0)

    if len(args) == 1:
        host_address = args[0]
    elif not args:
        sys.stderr.write("ERROR: No host given.\n")
        sys.exit(1)
    else:
        sys.stderr.write("ERROR: Please specify exactly one host.\n")
        sys.exit(1)

    for module, module_options in naviseccli_options.items():
        try:
            if mortypes.index("all") >= 0:
                module_options["active"] = True
                fetch_agent_info = True
        except ValueError:
            pass

        try:
            if mortypes.index(module) >= 0:
                module_options["active"] = True
        except ValueError:
            pass

    try:
        if mortypes.index("agent") >= 0:
            fetch_agent_info = True
    except ValueError:
        pass

    if not shutil.which("naviseccli"):
        sys.stderr.write('The command "naviseccli" could not be found. Terminating.\n')
        sys.exit(1)

    #############################################################################
    # fetch information by calling naviseccli
    #############################################################################

    if (user is None or user == "") and (password is None or password == ""):
        # try using security files
        basecmd = "naviseccli -h %s " % host_address
    else:
        basecmd = f"naviseccli -h {host_address} -User {user} -Password '{password}' -Scope 0 "

    #
    # check_mk section of agent output
    #

    def run(cmd):
        return _run_cmd(opt_debug, basecmd + cmd)

    # Now read the whole output of the command
    cmdout = run("getall -sp")

    if cmdout and cmdout[0].startswith("Security file not found"):
        sys.stderr.write(
            "Could not find security file. Please provide valid user "
            "credentials if you don't have a security file.\n"
        )
        sys.exit(1)

    sys.stdout.write("<<<emcvnx_info:sep(58)>>>\n")
    for line in cmdout:
        sys.stdout.write(line.strip() + "\n")

    # if module "agent" was requested, fetch additional information about the
    # agent, e. g. Model and Revision
    if fetch_agent_info:
        sys.stdout.write("<<<emcvnx_agent:sep(58)>>>\n")
        for line in run("getagent"):
            sys.stdout.write(normalize_str(line) + "\n")

    #
    # all other sections of agent output
    #
    for module, module_options in naviseccli_options.items():
        if module_options["active"] is True:
            separator = module_options["sep"]
            if separator:
                sys.stdout.write(f"<<<emcvnx_{module}:sep({separator})>>>\n")
            else:
                sys.stdout.write("<<<emcvnx_%s>>>\n" % module)

            for header, cmd_option in module_options["cmd_options"]:
                if header is not None:
                    sys.stdout.write("[[[%s]]]\n" % header)
                for line in run(cmd_option):
                    sys.stdout.write(normalize_str(line) + "\n")

    if g_profile:
        g_profile_path = Path("emcvnx_profile.out")
        g_profile.dump_stats(g_profile_path)

        show_profile = g_profile_path.parent / "show_profile.py"
        show_profile.write_text(
            "#!/usr/bin/python\n"
            "import pstats\n"
            "stats = pstats.Stats('%s')\n"
            "stats.sort_stats('cumtime').print_stats()\n" % g_profile_path
        )
        show_profile.chmod(0o755)

        sys.stderr.write(f"Profile '{g_profile_path}' written. Please run {show_profile}.\n")
