#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterable, Sequence

from netapp_ontap import resources as NetAppResource
from netapp_ontap.host_connection import HostConnection

from cmk.plugins.netapp import models  # pylint: disable=cmk-module-layer-violation
from cmk.special_agents.v0_unstable.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser

__version__ = "2.3.0b1"

USER_AGENT = f"checkmk-special-netapp-ontap-{__version__}"


def write_section(section_header: str, generator: Iterable, logger: logging.Logger) -> None:
    section_header = f"netapp_ontap_{section_header}"
    with SectionWriter(section_header) as writer:
        for element in generator:
            logger.debug(
                "Element data: %r", element.model_dump_json(exclude_unset=True, exclude_none=False)
            )
            writer.append_json(element.model_dump(exclude_unset=True, exclude_none=False))


def fetch_volumes(connection: HostConnection) -> Iterable[models.VolumeModel]:
    field_query = {
        "uuid",
        "state",
        "name",
        "msid",
        "space.available",
        "space.afs_total",
        "space.logical_space.enforcement",
        "space.logical_space.used",
        "svm.name",
        "svm.uuid",
        "files.maximum",
        "files.used",
    }

    for element in NetAppResource.Volume.get_collection(
        connection=connection, fields=",".join(field_query)
    ):
        element_data = element.to_dict()

        yield models.VolumeModel(
            uuid=element_data["uuid"],
            state=element_data.get("state"),
            name=element_data["name"],
            msid=element_data["msid"],
            space_available=element_data.get("space", {}).get("available"),
            space_total=element_data.get("space", {}).get("afs_total"),
            logical_enforcement=element_data.get("space", {})
            .get("logical_space", {})
            .get("enforcement"),
            logical_used=element_data.get("space", {}).get("logical_space", {}).get("used"),
            svm_name=element_data.get("svm", {}).get("name"),
            svm_uuid=element_data.get("svm", {}).get("uuid"),
            files_maximum=element_data.get("files", {}).get("maximum"),
            files_used=element_data.get("files", {}).get("used"),
        )


def fetch_volumes_counters(
    connection: HostConnection, volumes: Sequence[models.VolumeModel]
) -> Iterable[models.VolumeCountersModel]:
    """
    res = NetAppResource.CounterRow.get_collection("volume", id="mcc_darz_a-01:FlexPodXCS_NFS_Frank:Test_300T:00b3e6b1-5781-11ee-b0c8-00a098c54c0b", fields="*")
    id is composed in this way: node.name:svm.name:name(volume):uuid(volume)

    - https://docs.netapp.com/us-en/ontap-pcmap-9141/volume.html#counters

    """

    volumes_counters_field_query = {
        "fcp.write_data",
        "fcp.read_latency",
        "iscsi.write_latency",
        "read_latency",
        "nfs.write_ops",
        "fcp.read_ops",
        "fcp.read_data",
        "cifs.write_ops",
        "iscsi.read_latency",
        "nfs.write_latency",
        "iscsi.read_ops",
        "total_read_ops",
        "cifs.read_latency",
        "nfs.read_latency",
        "iscsi.read_data",
        "bytes_written",
        "cifs.write_data",
        "iscsi.write_data",
        "iscsi.write_ops",
        "fcp.write_latency",
        "fcp.write_ops",
        "nfs.read_ops",
        "bytes_read",
        "cifs.read_ops",
        "write_latency",
        "cifs.read_data",
        "nfs.read_data",
        "total_write_ops",
        "nfs.write_data",
        "cifs.write_latency",
    }

    for volume in volumes:
        # fcp_write_data -> fcp.write_data
        # fcp_read_latency -> fcp.read_latency
        # iscsi_write_latency -> iscsi.write_latency
        # read_latency -> read_latency
        # nfs_write_ops -> nfs.write_ops
        # fcp_read_ops -> fcp.read_ops
        # fcp_read_data -> fcp.read_data
        # cifs_write_ops -> cifs.write_ops
        # iscsi_read_latency -> iscsi.read_latency
        # nfs_write_latency -> nfs.write_latency
        # iscsi_read_ops -> iscsi.read_ops
        # read_ops -> total_read_ops
        # cifs_read_latency -> cifs.read_latency
        # nfs_read_latency -> nfs.read_latency
        # iscsi_read_data -> iscsi.read_data
        # san_read_ops  # ! missing
        # san_read_data # ! missing
        # san_read_latency # ! missing
        # write_data -> bytes_written
        # cifs_write_data -> cifs.write_data
        # iscsi_write_data -> iscsi.write_data
        # san_write_latency # ! missing
        # san_write_data # ! missing
        # iscsi_write_ops -> iscsi.write_ops
        # san_write_ops # ! missing
        # fcp_write_latency -> fcp.write_latency
        # fcp_write_ops -> fcp.write_ops
        # nfs_read_ops -> nfs.read_ops
        # read_data -> bytes_read
        # cifs_read_ops -> cifs.read_ops
        # write_latency -> write_latency
        # cifs_read_data -> cifs.read_data
        # nfs_read_data -> nfs.read_data
        # write_ops -> total_write_ops
        # nfs_write_data -> nfs.write_data
        # cifs_write_latency -> cifs.write_latency

        volume_id = f"*:{volume.svm_name}:{volume.name}:{volume.uuid}"

        for element in NetAppResource.CounterRow.get_collection(
            "volume",
            id=volume_id,
            connection=connection,
            fields="counters",
            max_records=None,  # type: ignore # pylint disable=arg-type not working
            **{"counters.name": "|".join(volumes_counters_field_query)},
        ):
            element_serialized = element.to_dict()

            counters_collection = {}
            counters = element_serialized["counters"]
            for counter in counters:
                counters_collection[counter["name"]] = counter["value"]

            yield models.VolumeCountersModel(
                id=element_serialized["id"],
                fcp_write_data=counters_collection["fcp.write_data"],
                fcp_read_latency=counters_collection["fcp.read_latency"],
                iscsi_write_latency=counters_collection["iscsi.write_latency"],
                read_latency=counters_collection["read_latency"],
                nfs_write_ops=counters_collection["nfs.write_ops"],
                fcp_read_ops=counters_collection["fcp.read_ops"],
                fcp_read_data=counters_collection["fcp.read_data"],
                cifs_write_ops=counters_collection["cifs.write_ops"],
                iscsi_read_latency=counters_collection["iscsi.read_latency"],
                nfs_write_latency=counters_collection["nfs.write_latency"],
                iscsi_read_ops=counters_collection["iscsi.read_ops"],
                total_read_ops=counters_collection["total_read_ops"],
                cifs_read_latency=counters_collection["cifs.read_latency"],
                nfs_read_latency=counters_collection["nfs.read_latency"],
                iscsi_read_data=counters_collection["iscsi.read_data"],
                bytes_written=counters_collection["bytes_written"],
                cifs_write_data=counters_collection["cifs.write_data"],
                iscsi_write_data=counters_collection["iscsi.write_data"],
                iscsi_write_ops=counters_collection["iscsi.write_ops"],
                fcp_write_latency=counters_collection["fcp.write_latency"],
                fcp_write_ops=counters_collection["fcp.write_ops"],
                nfs_read_ops=counters_collection["nfs.read_ops"],
                bytes_read=counters_collection["bytes_read"],
                cifs_read_ops=counters_collection["cifs.read_ops"],
                write_latency=counters_collection["write_latency"],
                cifs_read_data=counters_collection["cifs.read_data"],
                nfs_read_data=counters_collection["nfs.read_data"],
                total_write_ops=counters_collection["total_write_ops"],
                nfs_write_data=counters_collection["nfs.write_data"],
                cifs_write_latency=counters_collection["cifs.write_latency"],
            )


def fetch_disks(connection: HostConnection) -> Iterable[models.DiskModel]:
    field_query = {
        "uid",
        "serial_number",
        "model",
        "vendor",
        "container_type",
        "usable_size",
        "bay",
    }
    yield from (
        models.DiskModel.model_validate(element.to_dict())
        for element in NetAppResource.Disk.get_collection(
            connection=connection, fields=",".join(field_query)
        )
    )


def fetch_luns(connection: HostConnection) -> Iterable[models.LunModel]:
    field_query = {
        "name",
        "space.size",
        "space.used",
        "enabled",
        "status.read_only",
        "svm.name",
        "location.volume.name",
    }

    for element in NetAppResource.Lun.get_collection(
        connection=connection, fields=",".join(field_query)
    ):
        element_data = element.to_dict()

        yield models.LunModel(
            name=element_data["name"],
            space_size=element_data["space"]["size"],
            space_used=element_data["space"]["used"],
            enabled=element_data["enabled"],
            read_only=element_data["status"]["read_only"],
            svm_name=element_data["svm"]["name"],
            volume_name=element_data["location"]["volume"]["name"],
        )


def fetch_aggr(connection: HostConnection) -> Iterable[models.AggregateModel]:
    field_query = {
        "name",
        "space.block_storage.available",
        "space.block_storage.size",
    }
    yield from (
        models.AggregateModel.model_validate(element.to_dict())
        for element in NetAppResource.Aggregate.get_collection(
            connection=connection, fields=",".join(field_query)
        )
    )


def fetch_vs_status(connection: HostConnection) -> Iterable[models.SvmModel]:
    field_query = {
        "name",
        "state",
        "subtype",
    }

    yield from (
        models.SvmModel.model_validate(element.to_dict())
        for element in NetAppResource.Svm.get_collection(
            connection=connection, fields=",".join(field_query)
        )
    )


def fetch_interfaces(connection: HostConnection) -> Iterable[models.IpInterfaceModel]:
    field_query = {
        "uuid",
        "name",
        "enabled",
        "state",
        "location.node.name",
        "location.port.name",
        "location.failover",
        # "ip",
    }

    yield from (
        models.IpInterfaceModel.model_validate(element.to_dict())
        for element in NetAppResource.IpInterface.get_collection(
            connection=connection, fields=",".join(field_query)
        )
    )


def fetch_ports(connection: HostConnection) -> Iterable[models.PortModel]:
    field_query = {
        "uuid",
        "name",
        "state",
        "speed",
        "type",
        "broadcast_domain.name",
    }

    for element in NetAppResource.Port.get_collection(
        connection=connection, fields=",".join(field_query)
    ):
        element_data = element.to_dict()

        yield models.PortModel(
            uuid=element_data["uuid"],
            name=element_data["name"],
            state=element_data["state"],
            speed=element_data.get("speed"),
            port_type=element_data["type"],
            broadcast_domain=element_data.get("broadcast_domain"),
        )


def fetch_interfaces_counters(
    connection: HostConnection, interfaces: Sequence[models.IpInterfaceModel]
) -> Iterable[models.InterfaceCountersRowModel]:
    """
    id is composed in this way: {node_name}:{interface_name}:{unique_id}

    - https://docs.netapp.com/us-en/ontap-pcmap-9141/lif.html

    """
    interfaces_counters_field_query = {"*"}

    for interface in interfaces:
        interface_id = f"{interface.location.node.name}:{interface.name}:*"

        yield from (
            models.InterfaceCountersRowModel.model_validate(element.to_dict())
            for element in NetAppResource.CounterRow.get_collection(
                "lif",
                id=interface_id,
                connection=connection,
                fields="counters",
                max_records=None,  # type: ignore # pylint disable=arg-type not working
                **{"counters.name": "|".join(interfaces_counters_field_query)},
            )
        )


def write_sections(connection: HostConnection, logger: logging.Logger) -> None:
    volumes = list(fetch_volumes(connection))
    write_section("volumes", volumes, logger)
    write_section("volumes_counters", fetch_volumes_counters(connection, volumes), logger)
    write_section("disk", fetch_disks(connection), logger)
    write_section("luns", fetch_luns(connection), logger)
    write_section("aggr", fetch_aggr(connection), logger)
    write_section("vs_status", fetch_vs_status(connection), logger)
    write_section("ports_rest", fetch_ports(connection), logger)
    interfaces = list(fetch_interfaces(connection))
    write_section("interfaces_rest", interfaces, logger)
    write_section("interfaces_counters", fetch_interfaces_counters(connection, interfaces), logger)


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
