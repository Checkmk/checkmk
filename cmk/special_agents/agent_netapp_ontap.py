#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import logging
from collections.abc import Iterable, Sequence

from netapp_ontap.host_connection import HostConnection

from cmk.plugins.netapp import models  # pylint: disable=cmk-module-layer-violation
from cmk.special_agents.v0_unstable.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser

__version__ = "2.3.0b1"

USER_AGENT = f"checkmk-special-netapp-ontap-{__version__}"


def section(section_header: str, generator: Iterable, logger: logging.Logger) -> None:
    section_header = f"netapp_ontap_{section_header}"
    with SectionWriter(section_header) as writer:
        for element in generator:
            logger.debug(
                "Element data: %r", element.model_dump_json(exclude_unset=True, exclude_none=False)
            )
            writer.append_json(element.model_dump(exclude_unset=True, exclude_none=False))


def fetch_volumes(connection: HostConnection) -> Iterable[models.VolumeModel]:
    yield from models.get_volumes(connection)


def fetch_volumes_counters(
    connection: HostConnection, volumes: Sequence[models.VolumeModel]
) -> Iterable[models.VolumeCountersRowModel]:
    """
    res = NetAppResource.CounterRow.get_collection("volume", id="mcc_darz_a-01:FlexPodXCS_NFS_Frank:Test_300T:00b3e6b1-5781-11ee-b0c8-00a098c54c0b", fields="*")
    id is composed in this way: node.name:svm.name:name(volume):uuid(volume)

    - https://docs.netapp.com/us-en/ontap-pcmap-9141/volume.html#counters

    """

    for volume in volumes:
        volume_counters = list(
            models.get_volume_counters(
                connection=connection, volume_id=f"*:{volume.svm.name}:{volume.name}:{volume.uuid}"
            )
        )

        yield from volume_counters


def fetch_disks(connection: HostConnection) -> Iterable[models.DiskModel]:
    yield from models.get_disks(connection)


def write_sections(connection: HostConnection, logger: logging.Logger) -> None:
    volumes = list(fetch_volumes(connection))
    section("volumes", volumes, logger)
    section("volumes_counters", fetch_volumes_counters(connection, volumes), logger)
    # section("disks_rest", fetch_disks(connection), logger)


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument("--hostname", help="Hostname or IP-address of NetApp Filer.")
    parser.add_argument("--username", help="Username for NetApp login")
    parser.add_argument("--password", help="Secret/Password for NetApp login")

    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=120,
        help=(
            "Set the network timeout to the NetApp filer to TIMEOUT seconds. "
            "Note: the timeout is not only applied to the connection, but also "
            "to each individual subquery. (Default is %(default)s seconds)"
        ),
    )
    parser.add_argument("--no-tls-verify", action="store_true", help="Don't verify TLS certificate")

    return parser.parse_args(argv)


def _setup_logging(verbose: bool) -> logging.Logger:
    logging.basicConfig(
        level={0: logging.WARN, 1: logging.INFO, 2: logging.DEBUG}.get(verbose, logging.DEBUG),
    )
    return logging.getLogger(__name__)


def agent_netapp_main(args: Args) -> int:
    logger = _setup_logging(args.verbose)
    with HostConnection(
        args.hostname,
        args.username,
        args.password,
        verify=False,  # TODO: check
        headers={"User-Agent": USER_AGENT},
    ) as connection:
        logger.debug("Connection estabilished. Start writing sections")
        write_sections(connection, logger)
        logger.debug("Sections have been written")

    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_netapp_main)


if __name__ == "__main__":
    # TODO: Remove this
    main()
