#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | "_ \ / _ \/ __| |/ /   | |\/| | " /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
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

from collections import namedtuple
import argparse
import json
import sys
import requests

from cmk.special_agents.utils import vcrtrace

Section = namedtuple('Section', ['name', 'key', 'uri'])


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = parse_arguments(argv)

    # Add new queries here
    sections = [
        Section(name="instance",
                key=None,
                uri="/api/json?tree=mode,nodeDescription,useSecurity,quietingDown"),
        Section(
            name="jobs",
            key="jobs",
            uri=
            "/api/json?tree=jobs[displayNameOrNull,name,color,lastBuild[number,duration,timestamp,result],healthReport[score],lastSuccessfulBuild[timestamp],jobs[displayNameOrNull,name,color,lastBuild[number,duration,timestamp,result],healthReport[score],lastSuccessfulBuild[timestamp],jobs[displayNameOrNull,name,color,lastBuild[number,duration,timestamp,result],healthReport[score],lastSuccessfulBuild[timestamp],jobs[displayNameOrNull,name,color,lastBuild[number,duration,timestamp,result],healthReport[score],lastSuccessfulBuild[timestamp]]]]]"
        ),
        Section(
            name="nodes",
            key="computer",
            uri=
            "/computer/api/json?tree=displayName,busyExecutors,totalExecutors,computer[description,displayName,idle,jnlpAgent,numExecutors,assignedLabels[busyExecutors,idleExecutors,nodes[mode],name],offline,offlineCause,temporarilyOffline,monitorData[*]]"
        ),
        Section(
            name="queue",
            key="items",
            uri=
            "/queue/api/json?tree=items[blocked,id,inQueueSince,stuck,pending,why,buildableStartMilliseconds,task[name,color]]"
        ),
    ]

    try:
        handle_request(args, sections)
    except Exception:
        if args.debug:
            return 1

    return 0


def handle_request(args, sections):
    url_base = "%s://%s:%s" % (args.proto, args.hostname, args.port)
    #labels = {}

    for section in sections:
        if section.name not in args.sections:
            continue

        sys.stdout.write("<<<jenkins_%s:sep(0)>>>\n" % section.name)

        url = url_base + section.uri
        try:
            response = requests.get(url, auth=(args.user, args.password))
        except requests.exceptions.RequestException as e:
            sys.stderr.write("Error: %s\n" % e)
            if args.debug:
                raise

        if section.name == "instance":
            value = response.json()
        else:
            value = response.json()[section.key]

        # if piggyback for nodes is implemented,
        # use this section for Host labels
        #
        #if section.name == "nodes":
        #    for line in value:
        #        node_name = line.get("displayName")
        #        label_data = line.get("assignedLabels")
        #        if label_data is None or node_name is None:
        #            continue
        #
        #        for label in label_data:
        #            label_name = label.get("name")
        #            if label_name is None:
        #                continue
        #
        #            if label_name != node_name:
        #                labels.update({"cmk/jenkins_node_label_%s" % label_name: "yes"})

        sys.stdout.write("%s\n" % json.dumps(value))

    #if labels:
    #    sys.stdout.write("<<<labels:sep(0)>>>\n")
    #    sys.stdout.write("%s\n" % json.dumps(labels))


def parse_arguments(argv):
    sections = ["instance", "jobs", "nodes", "queue"]

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("--vcrtrace", action=vcrtrace(filter_headers=[('authorization', '****')]))
    parser.add_argument("-u", "--user", default=None, help="Username for jenkins login")
    parser.add_argument("-s", "--password", default=None, help="Password for jenkins login")
    parser.add_argument("-P",
                        "--proto",
                        default="https",
                        help="Use 'http' or 'https' for connection to jenkins (default=https)")
    parser.add_argument("-p",
                        "--port",
                        default=443,
                        type=int,
                        help="Use alternative port (default: 443)")
    parser.add_argument(
        "-m",
        "--sections",
        default=sections,
        help="Comma separated list of data to query. Possible values: %s (default: all)" %
        ",".join(sections))
    parser.add_argument("--debug",
                        action="store_true",
                        help="Debug mode: let Python exceptions come through")

    parser.add_argument("hostname",
                        metavar="HOSTNAME",
                        help="Name of the jenkins instance to query.")

    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
