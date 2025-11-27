#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_jenkins

Checkmk special agent for monitoring Jenkins.
"""
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import argparse
import json
import sys
from collections.abc import Sequence
from contextlib import suppress
from typing import NamedTuple

import requests

from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.server_side_programs.v1_unstable import report_agent_crashes, vcrtrace

__version__ = "2.5.0b1"

AGENT = "jenkins"

PASSWORD_OPTION = "password"


class Section(NamedTuple):
    name: str
    key: str | None
    uri: str


@report_agent_crashes(AGENT, __version__)
def main() -> int:
    """Main entry point to be used"""
    return agent_jenkins_main(parse_arguments(sys.argv[1:]))


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    sections = ["instance", "jobs", "nodes", "queue", "system_metrics"]

    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(
        prog=prog, description=description, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug mode (keep some exceptions unhandled)",
    )
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument(
        "--vcrtrace",
        "--tracefile",
        default=False,
        action=vcrtrace(
            # This is the result of a refactoring.
            # I did not check if it makes sense for this special agent.
            filter_headers=[("authorization", "****")],
        ),
    )

    parser.add_argument("-u", "--user", help="Username for jenkins login", required=True)
    parser_add_secret_option(
        parser, long=f"--{PASSWORD_OPTION}", help="Password for jenkins login", required=True
    )
    parser.add_argument(
        "-P",
        "--proto",
        default="https",
        help="Use 'http' or 'https' for connection to jenkins (default=https)",
    )
    parser.add_argument(
        "-p", "--port", default=443, type=int, help="Use alternative port (default: 443)"
    )
    parser.add_argument(
        "--path", default="", help="Add (sub) path to the URI, i.e. <proto>://<host>:<port>/<path>"
    )
    parser.add_argument(
        "-m",
        "--sections",
        default=sections,
        help="Comma separated list of data to query. Possible values: %s (default: all)"
        % ",".join(sections),
    )

    parser.add_argument(
        "hostname", metavar="HOSTNAME", help="Name of the Jenkins instance to query."
    )

    return parser.parse_args(argv)


def agent_jenkins_main(args: argparse.Namespace) -> int:
    # Add new queries here
    sections = [
        Section(
            name="instance",
            key=None,
            uri="/api/json?tree=mode,nodeDescription,useSecurity,quietingDown",
        ),
        Section(
            name="jobs",
            key="jobs",
            uri="/api/json?tree=jobs[displayNameOrNull,name,color,lastBuild[number,duration,timestamp,result],healthReport[score],lastSuccessfulBuild[timestamp],jobs[displayNameOrNull,name,color,lastBuild[number,duration,timestamp,result],healthReport[score],lastSuccessfulBuild[timestamp],jobs[displayNameOrNull,name,color,lastBuild[number,duration,timestamp,result],healthReport[score],lastSuccessfulBuild[timestamp],jobs[displayNameOrNull,name,color,lastBuild[number,duration,timestamp,result],healthReport[score],lastSuccessfulBuild[timestamp]]]]]",
        ),
        Section(
            name="nodes",
            key="computer",
            uri="/computer/api/json?tree=displayName,busyExecutors,totalExecutors,computer[description,displayName,idle,jnlpAgent,numExecutors,assignedLabels[busyExecutors,idleExecutors,nodes[mode],name],offline,offlineCause,temporarilyOffline,monitorData[*]]",
        ),
        Section(
            name="queue",
            key="items",
            uri="/queue/api/json?tree=items[blocked,id,inQueueSince,stuck,pending,why,buildableStartMilliseconds,task[name,color]]",
        ),
        Section(
            name="system_metrics",
            key="items",
            uri="/metrics/currentUser/metrics",
        ),
    ]

    try:
        handle_request(args, sections)
    except Exception:
        if args.debug:
            raise

    return 0


def handle_request(args, sections):
    url_base = f"{args.proto}://{args.hostname}:{args.port}"
    if args.path:
        url_base += f"/{args.path}"

    # labels = {}

    session = requests.Session()
    session.auth = (args.user, resolve_secret_option(args, PASSWORD_OPTION).reveal())

    for section in sections:
        if section.name not in args.sections:
            continue

        sys.stdout.write("<<<jenkins_%s:sep(0)>>>\n" % section.name)

        url = url_base + section.uri
        try:
            response = session.get(url, timeout=900)
        except requests.exceptions.RequestException as e:
            sys.stderr.write("Error: %s\n" % e)
            if args.debug:
                raise

            return 1

        # Things might go wrong if authentication is missing.
        if response.status_code != 200:
            sys.stderr.write("Could not fetch data from Jenkins. Details: %s\n" % response)
            return 2

        # Jenkins will happily return a HTTP status 200 even if things go wrong.
        # If we do not receive any content we know that our request has failed.
        if not response.content:
            sys.stderr.write(
                "Jenkins did not return any data when querying for %s\n" % section.name
            )
            return 3

        if section.name == "instance":
            value = response.json()
        elif section.name == "system_metrics":
            value = response.json()

            # Historic information is huge and not interesting for this
            with suppress(KeyError):
                del value["histograms"]
            # Timers contain values we can compute ourselfs
            with suppress(KeyError):
                del value["timers"]
        else:
            value = response.json()[section.key]

        # if piggyback for nodes is implemented,
        # use this section for Host labels
        #
        # if section.name == "nodes":
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

    # if labels:
    #    sys.stdout.write("<<<labels:sep(0)>>>\n")
    #    sys.stdout.write("%s\n" % json.dumps(labels))

    return 0


if __name__ == "__main__":
    sys.exit(main())
