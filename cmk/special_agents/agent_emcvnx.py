#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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
import os
import sys
from typing import Any, Dict


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


def main(sys_argv=None):
    if sys_argv is None:
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
    g_profile_path = "emcvnx_profile.out"

    host_address = None
    user = None
    password = None
    mortypes = ["all"]
    fetch_agent_info = False

    naviseccli_options: Dict[str, Dict[str, Any]] = {
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
            _opt_timeout = int(a)  # noqa: F841
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

    #############################################################################
    # fetch information by calling naviseccli
    #############################################################################

    if (user is None or user == "") and (password is None or password == ""):
        # try using security files
        basecmd = "naviseccli -h %s " % host_address
    else:
        basecmd = "naviseccli -h %s -User %s -Password '%s' -Scope 0 " % (
            host_address,
            user,
            password,
        )

    #
    # check_mk section of agent output
    #

    cmd = basecmd + "getall -sp"
    if opt_debug:
        sys.stderr.write("executing external command: %s\n" % cmd)

    # Now read the whole output of the command
    cmdout = [l.strip() for l in os.popen(cmd + " 2>&1").readlines()]  # nosec

    if cmdout:
        if "naviseccli: not found" in cmdout[0]:
            sys.stderr.write('The command "naviseccli" could not be found. Terminating.\n')
            sys.exit(1)

        elif cmdout[0].startswith("Security file not found"):
            sys.stderr.write(
                "Could not find security file. Please provide valid user "
                "credentials if you don't have a security file.\n"
            )
            sys.exit(1)

    print("<<<emcvnx_info:sep(58)>>>")
    for line in cmdout:
        print(line)

    # if module "agent" was requested, fetch additional information about the
    # agent, e. g. Model and Revision
    if fetch_agent_info:
        print("<<<emcvnx_agent:sep(58)>>>")
        cmd = basecmd + "getagent"
        if opt_debug:
            sys.stderr.write("executing external command: %s\n" % cmd)

        for line in os.popen(cmd).readlines():  # nosec
            print(line, end=" ")

    #
    # all other sections of agent output
    #
    for module, module_options in naviseccli_options.items():
        if module_options["active"] is True:
            separator = module_options["sep"]
            if separator:
                print("<<<emcvnx_%s:sep(%s)>>>" % (module, separator))
            else:
                print("<<<emcvnx_%s>>>" % module)

            for header, cmd_option in module_options["cmd_options"]:
                if header is not None:
                    print("[[[%s]]]" % header)
                cmd = basecmd + cmd_option
                if opt_debug:
                    sys.stderr.write("executing external command: %s\n" % cmd)
                for line in os.popen(cmd).readlines():  # nosec
                    print(line, end=" ")

    if g_profile:
        g_profile.dump_stats(g_profile_path)
        show_profile = os.path.join(os.path.dirname(g_profile_path), "show_profile.py")
        open(show_profile, "w").write(  # pylint:disable=consider-using-with
            "#!/usr/bin/python\n"
            "import pstats\n"
            "stats = pstats.Stats('%s')\n"
            "stats.sort_stats('cumtime').print_stats()\n" % g_profile_path
        )
        os.chmod(show_profile, 0o755)

        sys.stderr.write("Profile '%s' written. Please run %s.\n" % (g_profile_path, show_profile))
