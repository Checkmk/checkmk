#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import sys
import argparse

import cmk.utils.password_store


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--debug", action="store_true", help="Raise Python exceptions.")
    parser.add_argument("-u", "--username", required=True, help="The username.")
    parser.add_argument("-p", "--password", required=True, help="The password.")
    parser.add_argument("--nas-db", required=True, help="The NAS-DB name.")
    parser.add_argument("hostname")
    return parser.parse_args(argv)


def get_client_connection(args):
    try:
        import paramiko  # type: ignore[import]
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(args.hostname, username=args.username, password=args.password, timeout=5)
        return client

    except Exception as e:
        raise Exception("Failed to connect to remote host: %s" % e)


def main(args=None):
    if args is None:
        cmk.utils.password_store.replace_passwords()
        args = sys.argv[1:]

    args = parse_arguments(args)
    opt_debug = args.debug
    nas_db_env = "export NAS_DB=%s; " % args.nas_db
    queries = {
        "quotas": nas_db_env + "/nas/bin/nas_fs -query:* "
                  "-fields:TreeQuotas -format:'%q' -query:* "
                  "-fields:rwvdms,filesystem,path,BlockUsage,BlockHardLimit "
                  "-format:'%L|%s|%s|%d|%L\\n'",
        "fs": nas_db_env + "/nas/bin/nas_fs -query:inuse==y:IsRoot==False "
              "-fields:Name,SizeValues -format:'%L|%s\\n'",
    }

    client = get_client_connection(args)

    sys.stdout.write("<<<vnx_version:sep(124)>>>\n")
    stdin, stdout, stderr = client.exec_command(nas_db_env + "/nas/bin/nas_version")
    stdin.close()
    sys.stdout.write("Version|%s\n" % stdout)
    if opt_debug:
        sys.stderr.write("%s\n" % repr(stderr))

    stdin, stdout, stderr = client.exec_command(nas_db_env + "/nas/sbin/model")
    stdin.close()
    sys.stdout.write("AgentOS|%s\n" % stdout)
    if opt_debug:
        sys.stderr.write("%s\n" % repr(stderr))

    results = {}
    for query_type, query in queries.items():
        stdin, stdout, stderr = client.exec_command(query)
        results.setdefault(query_type, {
            "stdin": stdin,
            "stdout": stdout,
            "stderr": stderr,
        })
        stdin.close()

    for query_type, result in results.items():
        if opt_debug:
            sys.stderr.write("%s\n" % repr(result["stderr"]))

        sys.stdout.write("<<<vnx_quotas:sep(124)>>>\n")
        sys.stdout.write("[[[%s]]]\n" % query_type)
        for line in result["stdout"].readlines():
            sys.stdout.write("%s" % line)
