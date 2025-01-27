#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# needs to issue a command like
# ssh USER@HOSTNAME 'echo \<\<\<ibm_svc_host:sep\(58\)\>\>\>; lshost -delim :; echo \<\<\<ibm_svc_license:sep\(58\)\>\>\>; lslicense -delim :; echo \<\<\<ibm_svc_mdisk:sep\(58\)\>\>\>; lsmdisk -delim :; echo \<\<\<ibm_svc_mdiskgrp:sep\(58\)\>\>\>; lsmdiskgrp -delim :; echo \<\<\<ibm_svc_node:sep\(58\)\>\>\>; lsnode -delim :; echo \<\<\<ibm_svc_nodestats:sep\(58\)\>\>\>; lsnodestats -delim :; echo \<\<\<ibm_svc_system:sep\(58\)\>\>\>; lssystem -delim :; echo \<\<\<ibm_svc_systemstats:sep\(58\)\>\>\>; lssystemstats -delim :'

import cProfile
import getopt
import shlex
import subprocess
import sys
from pathlib import Path


def usage():
    sys.stderr.write(
        """Check_MK SVC / V7000 Agent

USAGE: agent_ibmsvc [OPTIONS] HOST
       agent_ibmsvc -h

ARGUMENTS:
  HOST                          Host name or IP address of the target device

OPTIONS:
  -h, --help                    Show this help message and exit
  -u USER, --user USER          Username for EMC VNX login

                                We try to use SSH key authentification.
                                Private key must be pre-created in ~/.ssh/

  -k, --accept-any-hostkey      Accept any SSH Host Key
                                Please note: This might be a security issue because
                                man-in-the-middle attacks are not recognized

  --debug                       Debug mode: write some debug messages,
                                let Python exceptions come through

  --profile                     Enable performance profiling in Python source code

  -i MODULES, --modules MODULES Modules to query. This is a comma separated list of
                                which may contain the keywords "lshost", "lslicense",
                                "lsmdisk", "lsmdiskgrp", "lsnode", "lsnodestats",
                                "lssystem", "lssystemstats", "lseventlog", "lsportfc"
                                "lsenclosure", "lsenclosurestats", "lsarray", "lsportsas"
                                or "all" to define which information should be queried
                                from the device.
                                You can define to use only view of them to optimize
                                performance. The default is "all".

"""
    )


#############################################################################
# command line options
#############################################################################


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    short_options = "hu:p:t:m:i:k"
    long_options = [
        "help",
        "user=",
        "debug",
        "timeout=",
        "profile",
        "modules=",
        "accept-any-hostkey",
    ]

    try:
        opts, args = getopt.getopt(sys_argv, short_options, long_options)
    except getopt.GetoptError as err:
        sys.stderr.write("%s\n" % err)
        return 1

    opt_debug = False
    opt_timeout = 10
    opt_any_hostkey = ""

    g_profile = None

    host_address = None
    user = None

    command_options = {
        "lshost": {"section_header": "ibm_svc_host", "command": "lshost -delim :"},
        "lslicense": {
            "section_header": "ibm_svc_license",
            "command": "lslicense -delim :",
        },
        "lsmdisk": {
            "section_header": "ibm_svc_mdisk",
            "command": "lsmdisk -delim :",
        },
        "lsmdiskgrp": {
            "section_header": "ibm_svc_mdiskgrp",
            "command": "lsmdiskgrp -delim :",
        },
        "lsnode": {"section_header": "ibm_svc_node", "command": "lsnode -delim :"},
        "lsnodestats": {
            "section_header": "ibm_svc_nodestats",
            "command": "if [ -f ./bin/shortcuts/lsnodestats ]; then lsnodestats -delim :; else lsnodecanisterstats -delim :; fi",
        },
        "lssystem": {
            "section_header": "ibm_svc_system",
            "command": "lssystem -delim :",
        },
        "lssystemstats": {
            "section_header": "ibm_svc_systemstats",
            "command": "lssystemstats -delim :",
        },
        "lseventlog": {
            "section_header": "ibm_svc_eventlog",
            "command": "lseventlog -expired no -fixed no -monitoring no -order severity -message no -delim : -nohdr",
        },
        "lsportfc": {
            "section_header": "ibm_svc_portfc",
            "command": "lsportfc -delim :",
        },
        "lsenclosure": {
            "section_header": "ibm_svc_enclosure",
            "command": "lsenclosure -delim :",
        },
        "lsenclosurestats": {
            "section_header": "ibm_svc_enclosurestats",
            "command": "lsenclosurestats -delim :",
        },
        "lsarray": {
            "section_header": "ibm_svc_array",
            "command": "lsarray -delim :",
        },
        "lsportsas": {
            "section_header": "ibm_svc_portsas",
            "command": "lsportsas -delim :",
        },
        "disks": {
            "section_header": "ibm_svc_disks",
            "command": "svcinfo lsdrive -delim :",
        },
    }
    mortypes = set(command_options)
    for o, a in opts:
        if o in ["--debug"]:
            opt_debug = True
        elif o in ["--profile"]:
            g_profile = cProfile.Profile()
            g_profile.enable()
        elif o in ["-u", "--user"]:
            user = a
        elif o in ["-i", "--modules"]:
            provided_modules = set(a.split(","))
            mortypes = (
                mortypes if provided_modules == {"all"} else provided_modules.intersection(mortypes)
            )
        elif o in ["-t", "--timeout"]:
            opt_timeout = int(a)
        elif o in ["-k", "--accept-any-hostkey"]:
            opt_any_hostkey = "-o StrictHostKeyChecking=no"
        elif o in ["-h", "--help"]:
            usage()
            sys.exit(0)

    if len(args) == 1:
        host_address = args[0]
    elif not args:
        sys.stderr.write("ERROR: No host given.\n")
        return 1
    else:
        sys.stderr.write("ERROR: Please specify exactly one host.\n")
        return 1

    if user is None:
        sys.stderr.write("ERROR: No user name given.\n")
        return 1

    #############################################################################
    # fetch information by ssh
    #############################################################################

    remote_command = ""
    for module in mortypes:
        remote_command += (
            r"echo \<\<\<%s:sep\(58\)\>\>\>;" % command_options[module]["section_header"]
        )
        remote_command += "%s || true;" % command_options[module]["command"]

    result = _execute_ssh_command(
        remote_command=remote_command,
        opt_timeout=opt_timeout,
        opt_any_hostkey=opt_any_hostkey,
        user=user,
        host_address=host_address,
        opt_debug=opt_debug,
    )

    _check_ssh_result(result)

    if g_profile:
        g_profile_path = Path("ibmsvc_profile.out")
        g_profile.dump_stats(g_profile_path)

        show_profile = g_profile_path / "show_profile.py"
        show_profile.write_text(
            "#!/usr/bin/python\n"
            "import pstats\n"
            "stats = pstats.Stats('%s')\n"
            "stats.sort_stats('cumtime').print_stats()\n" % g_profile_path
        )
        show_profile.chmod(0o755)

        sys.stderr.write(f"Profile '{g_profile_path}' written. Please run {show_profile}.\n")
    return None


def _execute_ssh_command(
    remote_command: str,
    opt_timeout: int,
    opt_any_hostkey: str,
    user: str,
    host_address: str,
    opt_debug: bool,
) -> subprocess.CompletedProcess:
    cmd = f"ssh -o ConnectTimeout={opt_timeout} {opt_any_hostkey} {shlex.quote(user)}@{shlex.quote(host_address)} '{remote_command}'"

    if opt_debug:
        sys.stderr.write(f"executing external command: {cmd}\n")

    return subprocess.run(  # nosec B602 # BNS:67522a
        cmd,
        shell=True,
        capture_output=True,
        stdin=None,
        encoding="utf-8",
        check=False,
    )


def _check_ssh_result(result: subprocess.CompletedProcess) -> None:
    if result.returncode not in [0, 1]:
        sys.stderr.write("Error connecting via ssh: %s\n" % result.stderr)
        sys.exit(2)

    lines = result.stdout.split("\n")

    if lines[0].startswith("CMMVC7016E") or (len(lines) > 1 and lines[1].startswith("CMMVC7016E")):
        sys.stderr.write(result.stdout)
        sys.exit(2)

    # Quite strange.. Why not simply print stdout?
    for line in lines:
        sys.stdout.write(line + "\n")
