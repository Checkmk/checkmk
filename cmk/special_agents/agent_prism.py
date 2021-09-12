#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import csv
import logging
import sys
from typing import Any, Generator, Optional, Sequence, Tuple

from cmk.special_agents.utils.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser
from cmk.special_agents.utils.request_helper import HTTPSAuthRequester, Requester

SectionLine = Tuple[Any, ...]

LOGGING = logging.getLogger("agent_prism")

# TODO: get rid of all this..
# >>>>
FIELD_SEPARATOR = "|"


def gen_csv_writer() -> Any:
    return csv.writer(sys.stdout, delimiter=FIELD_SEPARATOR)


def write_title(section: str) -> None:
    sys.stdout.write("<<<prism_%s:sep(%d)>>>\n" % (section, ord(FIELD_SEPARATOR)))


# <<<<


def parse_arguments(argv: Optional[Sequence[str]]) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout in seconds for network connects (default=10)",
    )
    parser.add_argument(
        "--server", type=str, required=True, metavar="ADDRESS", help="host to connect to"
    )
    parser.add_argument("--port", type=int, metavar="PORT", default=9440)
    parser.add_argument(
        "--username", type=str, required=True, metavar="USER", help="user account on prism"
    )
    parser.add_argument(
        "--password", type=str, required=True, metavar="PASSWORD", help="password for that account"
    )

    return parser.parse_args(argv)


# TODO: get rid of CSV and write JSON
def output_containers(requester: Requester) -> None:
    LOGGING.debug("do request..")
    obj = requester.get("containers")
    LOGGING.debug("got %d containers", len(obj["entities"]))

    write_title("containers")
    writer = gen_csv_writer()
    writer.writerow(["name", "usage", "capacity"])
    for entity in obj["entities"]:
        writer.writerow(
            [
                entity["name"],
                entity["usageStats"]["storage.user_usage_bytes"],
                entity["usageStats"]["storage.user_capacity_bytes"],
            ]
        )


def output_alerts(requester: Requester) -> Generator[SectionLine, None, None]:
    needed_context_keys = {"vm_type"}

    LOGGING.debug("do request..")
    obj = requester.get(
        "alerts",
        parameters={"resolved": "false", "acknowledged": "false"},
    )
    LOGGING.debug("got %d alerts", len(obj["entities"]))

    yield ("timestamp", "severity", "message", "context")

    for entity in obj["entities"]:
        # The message is stored as a pattern with placeholders, the
        # actual values are stored in context_values, the keys in
        # context_types
        full_context = dict(zip(entity["contextTypes"], entity["contextValues"]))

        # create a thinned out context we can provide together with the alert data in order to
        # provide more sophisticated checks in the future (this could be made a cli option, too)
        thin_context = {k: v for k, v in full_context.items() if k in needed_context_keys}

        # We have seen informational messages in format:
        # {dev_type} drive {dev_name} on host {ip_address} has the following problems: {err_msg}
        # In this case the keys have no values so we can not assign it to the message
        # To handle this, we output a message without assigning the keys
        try:
            message = entity["message"].format(**full_context)
        except KeyError:
            message = entity["message"]

        # message can contain line breaks which confuses the parser.
        message = message.replace("\n", r"\n")
        yield (entity["createdTimeStampInUsecs"], entity["severity"], message, thin_context)


# TODO: get rid of CSV and write JSON
def output_cluster(requester: Requester) -> None:
    LOGGING.debug("do request..")
    obj = requester.get("cluster")
    LOGGING.debug("got %d keys", len(obj.keys()))

    write_title("info")
    writer = gen_csv_writer()
    writer.writerow(["name", "version"])
    writer.writerow([obj["name"], obj["version"]])


# TODO: get rid of CSV and write JSON
def output_storage_pools(requester: Requester) -> None:
    LOGGING.debug("do request..")
    obj = requester.get("storage_pools")
    LOGGING.debug("got %d entities", len(obj["entities"]))

    write_title("storage_pools")
    writer = gen_csv_writer()
    writer.writerow(["name", "usage", "capacity"])

    for entity in obj["entities"]:
        writer.writerow(
            [
                entity["name"],
                entity["usageStats"]["storage.usage_bytes"],
                entity["usageStats"]["storage.capacity_bytes"],
            ]
        )


def agent_prism_main(args: Args) -> None:
    """Establish a connection to a Prism server and process containers, alerts, clusters and
    storage_pools"""
    LOGGING.info("setup HTTPS connection..")
    requester = HTTPSAuthRequester(
        args.server,
        args.port,
        "PrismGateway/services/rest/v1",
        args.username,
        args.password,
    )

    LOGGING.info("fetch and write container info..")
    output_containers(requester)

    LOGGING.info("fetch and write alerts..")
    with SectionWriter("prism_alerts") as writer:
        writer.append_json(output_alerts(requester))

    LOGGING.info("fetch and write cluster info..")
    output_cluster(requester)

    LOGGING.info("fetch and write storage_pools..")
    output_storage_pools(requester)

    LOGGING.info("all done. bye.")


def main() -> None:
    """Main entry point to be used"""
    special_agent_main(parse_arguments, agent_prism_main)


if __name__ == "__main__":
    main()
