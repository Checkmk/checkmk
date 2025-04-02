#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Act as a datasource program for a Checkmk site.

'stdout' text-encoding must be 'utf-8' for the script to run.
This module can be used to populate a host with desired number of services.
Thus, overriding / faking the Checkmk agent which takes care of discovering services.

Additionally, data corresponding to piggyback hosts can be generated as well.
Monitoring piggyback hosts and corresponding services can be enabled by configuring
"Dynamic host management" / DCD or "Piggyback mechanism".

Thank you 'mimimi'! Your efforts inspired this script's development!
"""

import sys
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path
from random import randrange
from typing import Any, Final, TextIO

DIR_MODULE = Path(__file__).parent
ENCODING = "utf-8"
PREFIX = "dummy_agent_dump"
SUFFIX = "out"
SEPARATOR = "\n"


def generate_data(
    hostname: str, number_of_services: int, payload: int, debug: bool = False
) -> list[str]:
    stdout = ["<<<local>>>"]
    stdout += _generate_local_services(hostname, number_of_services)
    if payload > 0:
        stdout += _generate_payload(payload)
    if debug:
        debug_filepath = DIR_MODULE / f"{PREFIX}.{hostname}.{SUFFIX}"
        with open(debug_filepath, encoding=ENCODING, mode="w") as debug_file:
            print_data(*stdout, file=debug_file)
    return stdout


def _generate_local_services(hostname: str, number_of_services: int) -> list[str]:
    """Generate text to simulate service data, corresponding to a host.

    Services are prefixed with the 'hostname'. Out of all the services created,
    * ~10% remain with CRIT status
    * ~20% remain with WARN status
    * ~70% remain with OK status
    (works reliably for >= 10 services)

    All the services initialize 'state' as a variable,
    which can be monitored over a period of time within the Checkmk site.
    Value of 'state' depends on the service status.
    """

    class ServiceData:
        """Dataclass to store data related to a service."""

        def __init__(self, status_code: int, count: int, value_range: tuple[int, int]) -> None:
            self.status: Final = status_code
            self.count: Final = count
            self.value_range: Final = value_range

    def _local_services(start_idx: int, service_data_: ServiceData, prefix_: str) -> list[str]:
        stdout_ = []
        for idx in range(start_idx, start_idx + service_data_.count):
            random_percent = randrange(service_data_.value_range[0], service_data_.value_range[1])
            stdout_.append(
                f"{service_data_.status} {prefix_}-service-{idx} state={random_percent} "
                f"{datetime.now()} state: {random_percent}%"
            )
        return stdout_

    # ~10% of the total services have CRIT state
    crit = ServiceData(2, (number_of_services * 10) // 100, (1, 29))
    # ~20% of the total services have WARN state
    warn = ServiceData(1, (number_of_services * 20) // 100, (30, 69))
    # ~70% of the total services have OK state
    ok = ServiceData(0, number_of_services - (crit.count + warn.count), (70, 100))

    stdout = []
    start_idx = 1
    for service_data in (crit, warn, ok):
        stdout += _local_services(start_idx, service_data, hostname)
        start_idx = start_idx + service_data.count
    return stdout


def _generate_payload(units: int) -> list[str]:
    """Add extra text information within the data, corresponding to a host.

    Data is increased by 'units' x 10 bytes.
    Text-encoding is assumed to be 'utf-8'.
    """
    stdout = ["<<<extra data>>>"]
    # on STDOUT, 'Ten bytes\n'  has a size of 10 bytes.
    # '\n' character is added when 'list[str]' is converted to 'str'.
    stdout += ["Ten bytes"] * units
    return stdout


def generate_piggyback_hosts(
    parent_host: str,
    number_hosts: int,
    number_services_per_host: int,
    payload: int,
    new_hosts: bool,
    debug: bool,
) -> list[str]:
    """Generate data to simulate piggyback hosts and corresponding services.

    Piggyback data is generated within data meant for a 'parent_host'.
    Piggyback hosts named as '<parent_host>-pb-<idx>'.

    'new_hosts' enables generation of new set of piggyback hosts.
    It is used to simulate vanishing hosts and services and addition of new ones.
    """
    count_filename = DIR_MODULE / f"{PREFIX}.{parent_host}.piggyback_idx.{SUFFIX}"
    stdout = []
    if new_hosts:
        start_idx = 0 if not count_filename.exists() else int(count_filename.read_text())
    else:
        start_idx = 0

    for host_idx in range(start_idx, start_idx + number_hosts):
        pb_hostname = f"{parent_host}-pb-{host_idx + 1}"
        stdout += [f"<<<<{pb_hostname}>>>>"]
        stdout += generate_data(pb_hostname, number_services_per_host, payload)
        stdout.append("<<<<>>>>")

    if new_hosts:
        count_filename.write_text(str(host_idx + 1))

    if debug:
        debug_filepath = DIR_MODULE / f"{PREFIX}.{parent_host}.piggyback_data.{SUFFIX}"
        with open(debug_filepath, encoding=ENCODING, mode="w") as debug_file:
            print_data(*stdout, file=debug_file)

    return stdout


def print_data(*data: object, file: TextIO | None = None, **kwargs: Any) -> None:
    """Override  arguments to `print` statement with script specific constraints."""
    kwargs["sep"] = SEPARATOR
    kwargs["end"] = SEPARATOR
    kwargs["file"] = file
    print(*data, **kwargs)


class TypeCliArgs(Namespace):
    debug: bool
    host_name: str
    service_count: int
    payload: int
    piggyback_hosts: int
    piggyback_services: int
    piggyback_new_hosts: bool


def parse_cli_args() -> type[TypeCliArgs]:
    """Document CLI arguments."""

    parser = ArgumentParser(description=__doc__)
    # script specific args
    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        help=(
            "Enable debug mode. Store the generated data in a text-file, additionally. "
            "Text-file is always appended with information."
        ),
    )
    # host and services specific args
    classic_parser = parser.add_argument_group(title="Generate agent data")
    classic_parser.add_argument(
        "-n",
        "--host-name",
        dest="host_name",
        type=str,
        required=True,
        help="Hostname for which data is generated. This is a required field.",
    )
    classic_parser.add_argument(
        "-s",
        "--service-count",
        dest="service_count",
        type=int,
        default=10,
        help=(
            "Number of services to be generated, corresponding to the host. "
            "By default, 10 services are generated."
        ),
    )
    # add additional payload to the agent output to validate data fetching mechanism.
    classic_parser.add_argument(
        "-p",
        "--payload",
        dest="payload",
        type=int,
        default=0,
        help=(
            "Increase the amount of information present within the data "
            "per host(normal or piggyback). By default, 0 units of additional data are added. "
            "One unit is 10 bytes in size."
        ),
    )
    # piggyback hosts
    pb_parser = parser.add_argument_group(title="Generate piggyback data")
    pb_parser.add_argument(
        "-ph",
        "--piggyback-hosts",
        dest="piggyback_hosts",
        help="Number of piggyback hosts to be generated. By default, this is set to 0.",
        type=int,
        default=0,
    )
    pb_parser.add_argument(
        "-ps",
        "--piggyback-services",
        dest="piggyback_services",
        help=(
            "Number of piggyback services per piggyback'd host to be generated. "
            "Example usage: '... -ph 1 -ps 2' will result in 1 piggyback host with 2 services. "
            "By default, this is set to 10."
        ),
        type=int,
        default=10,
    )
    # simulate vanishing of older hosts and addition of new ones.
    pb_parser.add_argument(
        "-pnh",
        "--new-piggyback-hosts",
        dest="piggyback_new_hosts",
        help=(
            "Create data for new batch of hosts in the next execution. "
            "By default, disabled; data is generated for same set of hosts."
        ),
        action="store_true",
    )
    args, _ = parser.parse_known_args(namespace=TypeCliArgs)
    return args


if __name__ == "__main__":
    assert sys.stdout.encoding == ENCODING, (
        f"Expected 'stdout' text-encoding to be '{ENCODING}'! Observed: '{sys.stdout.encoding}'"
    )
    args = parse_cli_args()
    entries = []
    # generate piggyback data
    if args.piggyback_hosts > 0:
        entries += generate_piggyback_hosts(
            parent_host=args.host_name,
            number_hosts=args.piggyback_hosts,
            number_services_per_host=args.piggyback_services,
            payload=args.payload,
            new_hosts=args.piggyback_new_hosts,
            debug=args.debug,
        )

    # generate host data
    entries += generate_data(args.host_name, args.service_count, args.payload, args.debug)

    # list to string conversion
    print_data(*entries)
