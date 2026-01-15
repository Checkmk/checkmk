#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import sys
from collections.abc import Collection, Iterable, Sequence
from enum import Enum

from netapp_ontap import resources as NetAppResource
from netapp_ontap.error import NetAppRestError
from netapp_ontap.host_connection import HostConnection
from pydantic import BaseModel

from cmk.plugins.netapp import models  # pylint: disable=cmk-module-layer-violation
from cmk.special_agents.v0_unstable.agent_common import CannotRecover, special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser
from cmk.special_agents.v0_unstable.request_helper import HostnameValidationAdapter

__version__ = "2.4.0p20"

USER_AGENT = f"checkmk-special-netapp-ontap-{__version__}"


class FetchedResource(Enum):
    """Available NetApp resources for API fetching"""

    volumes = "volumes"
    volumes_counters = "volumes_counters"
    disk = "disk"
    luns = "luns"
    aggr = "aggr"
    vs_status = "vs_status"
    ports = "ports"
    interfaces = "interfaces"
    node = "node"
    fan = "fan"
    temp = "temp"
    alerts = "alerts"
    vs_traffic = "vs_traffic"
    psu = "psu"
    environment = "environment"
    qtree_quota = "qtree_quota"
    snapvault = "snapvault"
    fc_interfaces = "fc_interfaces"

    def __str__(self):
        return self.value


def write_section(
    section_name: str, generator: Iterable[BaseModel], logger: logging.Logger
) -> None:
    sys.stdout.write(f"<<<netapp_ontap_{section_name}:sep(0)>>>\n")
    for element in generator:
        json_dict = element.model_dump_json(exclude_unset=True, exclude_none=False)
        logger.debug("Element data: %r", json_dict)
        sys.stdout.write(json_dict + "\n")


def _collect_netapp_resource_volume(connection: HostConnection, is_constituent: bool) -> Iterable:
    field_query = (
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
        "space.snapshot.reserve_size",
        "space.snapshot.used",
        "space.snapshot.reserve_percent",
    )

    yield from NetAppResource.Volume.get_collection(
        connection=connection, is_constituent=is_constituent, fields=",".join(field_query)
    )


def _collect_volume_models(netapp_volumes: Iterable) -> Iterable[models.VolumeModel]:
    for netapp_resources in netapp_volumes:
        element_data = netapp_resources.to_dict()

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
            snapshot_reserve_size=element_data.get("space", {})
            .get("snapshot", {})
            .get("reserve_size"),
            snapshot_used=element_data.get("space", {}).get("snapshot", {}).get("used"),
            snapshot_reserve_percent=element_data.get("space", {})
            .get("snapshot", {})
            .get("reserve_percent"),
        )


def fetch_volumes(connection: HostConnection) -> Iterable[models.VolumeModel]:
    yield from _collect_volume_models(
        _collect_netapp_resource_volume(connection, is_constituent=True)
    )
    yield from _collect_volume_models(
        _collect_netapp_resource_volume(connection, is_constituent=False)
    )


def fetch_volumes_counters(
    connection: HostConnection, volumes: Sequence[models.VolumeModel]
) -> Iterable[models.VolumeCountersModel]:
    """
    res = NetAppResource.CounterRow.get_collection("volume", id="mcc_darz_a-01:FlexPodXCS_NFS_Frank:Test_300T:00b3e6b1-5781-11ee-b0c8-00a098c54c0b", fields="*")
    id is composed in this way: node.name:svm.name:name(volume):uuid(volume)

    - https://docs.netapp.com/us-en/ontap-pcmap-9141/volume.html#counters

    """

    volumes_counters_field_query = (
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
    )

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
            max_records=None,  # type: ignore[arg-type] # pylint disable=arg-type not working
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
    field_query = (
        "uid",
        "serial_number",
        "model",
        "vendor",
        "container_type",
        "usable_size",
        "bay",
        "bytes_per_sector",
        "sector_count",
    )

    yield from (
        models.DiskModel.model_validate(element.to_dict())
        for element in NetAppResource.Disk.get_collection(
            connection=connection, fields=",".join(field_query)
        )
    )


def fetch_luns(connection: HostConnection) -> Iterable[models.LunModel]:
    field_query = (
        "name",
        "space.size",
        "space.used",
        "enabled",
        "status.read_only",
        "svm.name",
        "location.volume.name",
    )

    for element in NetAppResource.Lun.get_collection(
        connection=connection, fields=",".join(field_query)
    ):
        element_data = element.to_dict()

        yield models.LunModel(
            name=element_data["name"],
            space_size=element_data["space"]["size"],
            space_used=element_data["space"].get("used"),
            enabled=element_data["enabled"],
            read_only=element_data.get("status", {}).get("read_only"),
            svm_name=element_data["svm"]["name"],
            volume_name=element_data["location"]["volume"]["name"],
        )


def _aggregates_ids(connection: HostConnection, args: Args) -> Collection:
    # wee need to retrieve the uuid of the aggregates via the CLI passthrough
    # because the REST API does not return, per design, the uuid of the root aggregates
    response = connection.session.get(
        url=f"{connection.origin}/api/private/cli/aggr?fields=uuid",
        timeout=args.timeout,
    )

    records = response.json().get("records", [])
    return {record["uuid"] for record in records}


def fetch_aggr(connection: HostConnection, args: Args) -> Iterable[models.AggregateModel]:
    field_query = (
        "name",
        "space.block_storage.available",
        "space.block_storage.size",
    )

    aggregates = _aggregates_ids(connection, args)
    for aggr_uuid in aggregates:
        resource = NetAppResource.Aggregate(uuid=aggr_uuid)
        try:
            resource.get(fields=",".join(field_query))
        except NetAppRestError:
            # Aggregates data could not be retrieved
            # this can happen when the aggregate is on a defective machine
            continue
        yield models.AggregateModel.model_validate(resource.to_dict())


def fetch_vs_status(connection: HostConnection) -> Iterable[models.SvmModel]:
    field_query = (
        "name",
        "state",
        "subtype",
    )

    yield from (
        models.SvmModel.model_validate(element.to_dict())
        for element in NetAppResource.Svm.get_collection(
            connection=connection, fields=",".join(field_query)
        )
    )


def fetch_interfaces(connection: HostConnection) -> Iterable[models.IpInterfaceModel]:
    field_query = (
        "uuid",
        "name",
        "enabled",
        "state",
        "location.node.name",
        "location.port.name",
        "location.failover",
        "location.home_node.name",
        "location.home_port.name",
        "location.is_home",
    )

    for element in NetAppResource.IpInterface.get_collection(
        connection=connection, fields=",".join(field_query)
    ):
        element_data = element.to_dict()

        yield models.IpInterfaceModel(
            uuid=element_data["uuid"],
            name=element_data["name"],
            enabled=element_data["enabled"],
            state=element_data.get("state"),
            node_name=element_data["location"]["node"]["name"],
            port_name=element_data["location"]["port"]["name"],
            failover=element_data["location"]["failover"],
            home_node=element_data["location"]["home_node"]["name"],
            home_port=element_data["location"]["home_port"]["name"],
            is_home=element_data["location"]["is_home"],
        )


def fetch_ports(connection: HostConnection) -> Iterable[models.PortModel]:
    field_query = (
        "uuid",
        "name",
        "node.name",
        "state",
        "speed",
        "type",
        "mac_address",
        "broadcast_domain.name",
    )

    for element in NetAppResource.Port.get_collection(
        connection=connection, fields=",".join(field_query)
    ):
        element_data = element.to_dict()

        yield models.PortModel(
            uuid=element_data["uuid"],
            name=element_data["name"],
            node_name=element_data["node"]["name"],
            state=element_data["state"],
            speed=element_data.get("speed"),
            port_type=element_data["type"],
            mac_address=element_data["mac_address"],
            broadcast_domain=element_data.get("broadcast_domain", {}).get("name", None),
        )


def fetch_interfaces_counters(
    connection: HostConnection, interfaces: Sequence[models.IpInterfaceModel]
) -> Iterable[models.InterfaceCounters]:
    """
    id is composed in this way: {node_name}:{interface_name}:{unique_id}

    - https://docs.netapp.com/us-en/ontap-pcmap-9141/lif.html

    """
    interfaces_counters_field_query = (
        "received_data",
        "received_packets",
        "received_errors",
        "sent_data",
        "sent_packets",
        "sent_errors",
    )

    # Create a lookup set of interface identifiers for filtering
    # Format: {node_name}:{interface_name}
    interface_lookup = {f"{interface.node_name}:{interface.name}" for interface in interfaces}

    # Use bulk query with wildcard to fetch all LIF counters in a single API call
    for element in NetAppResource.CounterRow.get_collection(
        "lif",
        id="*",
        connection=connection,
        fields="counters",
        max_records=None,  # type: ignore[arg-type] # pylint disable=arg-type not working
        **{"counters.name": "|".join(interfaces_counters_field_query)},
    ):
        element_data = element.to_dict()
        element_id = element_data["id"]

        # Extract node_name:interface_name from the full ID
        # Full ID format: node_name:interface_name:unique_id
        id_parts = element_id.split(":", 2)
        if len(id_parts) >= 2:
            node_interface_key = f"{id_parts[0]}:{id_parts[1]}"

            # Only yield data for interfaces we're monitoring
            if node_interface_key in interface_lookup:
                counters = {el["name"]: el["value"] for el in element_data["counters"]}

                yield models.InterfaceCounters(
                    id=element_id,
                    recv_data=counters["received_data"],
                    recv_packet=counters["received_packets"],
                    recv_errors=counters["received_errors"],
                    send_data=counters["sent_data"],
                    send_packet=counters["sent_packets"],
                    send_errors=counters["sent_errors"],
                )


def fetch_nodes(connection: HostConnection) -> Iterable[models.NodeModel]:
    field_query = (
        "name",
        "version",
        "controller.cpu.count",
        "nvram.battery_state",
        "model",
        "system_machine_type",
        "serial_number",
        "system_id",
        "controller.cpu.processor",
        "metric.processor_utilization",
        "metric.timestamp",
        "date",
    )

    for element in NetAppResource.Node.get_collection(
        connection=connection, fields=",".join(field_query)
    ):
        element_data = element.to_dict()

        yield models.NodeModel(
            name=element_data["name"],
            uuid=element_data["uuid"],
            version=element_data["version"],
            cpu_count=element_data.get("controller", {}).get("cpu", {}).get("count"),
            battery_state=element_data["nvram"]["battery_state"],
            model=element_data["model"],
            system_machine_type=element_data.get("system_machine_type"),
            serial_number=element_data["serial_number"],
            system_id=element_data["system_id"],
            cpu_processor=element_data.get("controller", {}).get("cpu", {}).get("processor"),
            processor_utilization=element_data["metric"]["processor_utilization"],
            processor_utilization_timestamp=element_data["metric"]["timestamp"],
            date=element_data.get("date"),
        )


def fetch_fans(
    connection: HostConnection, oldest_version: models.Version
) -> Iterable[models.ShelfFanModel]:
    field_query = [
        "id",
        "fans.id",
        "fans.state",
    ]
    if oldest_version >= models.Version(generation=9, major=13, minor=1):
        field_query.append("fans.installed")

    for element in NetAppResource.Shelf.get_collection(
        connection=connection, fields=",".join(field_query)
    ):
        element_data = element.to_dict()
        list_id = element_data["id"]
        fans = element_data.get("fans", [])

        for fan in fans:
            yield models.ShelfFanModel(
                list_id=list_id,
                id=fan["id"],
                state=fan["state"],
                installed=fan.get("installed"),
            )


def fetch_psu(connection: HostConnection) -> Iterable[models.ShelfPsuModel]:
    field_query = (
        "id",
        "frus.id",
        "frus.state",
        "frus.installed",
    )

    for element in NetAppResource.Shelf.get_collection(
        connection=connection, fields=",".join(field_query)
    ):
        element_data = element.to_dict()
        list_id = element_data["id"]
        frus = element_data.get("frus", [])

        for fru in frus:
            yield models.ShelfPsuModel(
                list_id=list_id,
                id=fru["id"],
                state=fru["state"],
                installed=fru.get("installed"),
            )


def fetch_temperatures(
    connection: HostConnection,
    oldest_version: models.Version,
) -> Iterable[models.ShelfTemperatureModel]:
    field_query = [
        "id",
        "temperature_sensors.id",
        "temperature_sensors.state",
        "temperature_sensors.temperature",
        "temperature_sensors.ambient",
        "temperature_sensors.threshold.low.warning",
        "temperature_sensors.threshold.low.critical",
        "temperature_sensors.threshold.high.warning",
        "temperature_sensors.threshold.high.critical",
    ]
    if oldest_version >= models.Version(generation=9, major=13, minor=1):
        field_query.append("temperature_sensors.installed")

    for element in NetAppResource.Shelf.get_collection(
        connection=connection, fields=",".join(field_query)
    ):
        element_data = element.to_dict()
        list_id = element_data["id"]
        temperatures = element_data.get("temperature_sensors", [])

        for temp in temperatures:
            yield models.ShelfTemperatureModel(
                list_id=list_id,
                id=temp["id"],
                installed=temp.get("installed"),
                state=temp["state"],
                temperature=temp.get("temperature"),
                ambient=temp["ambient"],
                low_warning=temp.get("threshold", {}).get("low", {}).get("warning"),
                low_critical=temp.get("threshold", {}).get("low", {}).get("critical"),
                high_warning=temp.get("threshold", {}).get("high", {}).get("warning"),
                high_critical=temp.get("threshold", {}).get("high", {}).get("critical"),
            )


def fetch_alerts(connection: HostConnection, args: Args) -> Iterable[models.AlertModel]:
    response = connection.session.get(
        url=f"{connection.origin}/api/private/support/alerts",
        timeout=args.timeout,
    )

    records = response.json()
    yield from (models.AlertModel.model_validate(record) for record in records["records"])


def fetch_vs_traffic_counters(
    connection: HostConnection,
) -> Iterable[models.SvmTrafficCountersModel]:
    query_data = {
        # table: counters
        "lif": (
            "received_data",
            "sent_data",
            "received_errors",
            "sent_errors",
            "received_packets",
            "sent_packets",
        ),
        "fcp_lif": (
            "average_read_latency",
            "average_write_latency",
            "read_data",
            "write_data",
            "read_ops",
            "write_ops",
        ),
        "svm_cifs": (
            "average_read_latency",
            "average_write_latency",
            "total_read_ops",
            "total_write_ops",
        ),
        "iscsi_lif": (
            "average_read_latency",
            "average_write_latency",
            "read_data",
            "write_data",
            "iscsi_read_ops",
            "iscsi_write_ops",
        ),
        "svm_nfs_v3": ("read_throughput", "write_throughput", "read_ops", "write_ops", "ops"),
        "svm_nfs_v4": (
            "total.read_throughput",
            "total.write_throughput",
            "ops",
        ),
        "svm_nfs_v41": (
            "total.read_throughput",
            "total.write_throughput",
            "ops",
        ),
    }

    for key, values in query_data.items():
        for element in NetAppResource.CounterRow.get_collection(
            key,
            connection=connection,
            fields="properties,counters",
            max_records=None,  # type: ignore[arg-type] # pylint disable=arg-type not working
            **{"counters.name": "|".join(values)},
        ):
            element_data = element.to_dict()

            svm_name = None
            for prop in element["properties"]:
                if prop["name"] == "svm.name":
                    svm_name = prop["value"]
                    break

            if svm_name is None:
                continue

            yield models.SvmTrafficCountersModel(
                svm_name=svm_name, table=key, counters=element_data["counters"]
            )


def fetch_fc_interfaces_counters(
    connection: HostConnection,
) -> Iterable[models.FcInterfaceTrafficCountersModel]:
    query_data = {
        # table: counters
        "fcp_lif:port": (
            "average_read_latency",
            "average_write_latency",
            "read_data",
            "write_data",
            "read_ops",
            "write_ops",
            "total_ops",
        ),
    }

    for key, values in query_data.items():
        for element in NetAppResource.CounterRow.get_collection(
            key,
            connection=connection,
            fields="properties,counters",
            max_records=None,  # type: ignore[arg-type] # pylint disable=arg-type not working
            **{"counters.name": "|".join(values)},
        ):
            element_data = element.to_dict()

            svm_name, name, port_wwpn = None, None, None
            for prop in element["properties"]:
                if prop["name"] == "svm.name":
                    svm_name = prop["value"]
                elif prop["name"] == "name":
                    name = prop["value"]
                elif prop["name"] == "port.wwpn":
                    port_wwpn = prop["value"]

            if svm_name is None or name is None or port_wwpn is None:
                continue

            yield models.FcInterfaceTrafficCountersModel(
                svm_name=svm_name,
                table=key,
                counters=element_data["counters"],
                name=name,
                port_wwpn=port_wwpn,
            )


def fetch_environment(connection):
    field_query = (
        "name",
        "node.name",
        "type",
        "value",
        "warning_high_threshold",
        "warning_low_threshold",
        "critical_high_threshold",
        "critical_low_threshold",
        "discrete_state",
        "discrete_value",
        "threshold_state",
        "value_units",
    )

    for element in NetAppResource.Sensors.get_collection(
        connection=connection, fields=",".join(field_query), type="thermal|fan|voltage|current"
    ):
        element_data = element.to_dict()
        yield models.EnvironmentThresholdSensorModel(
            name=element_data["name"],
            node_name=element_data["node"]["name"],
            sensor_type=element_data["type"],
            value=element_data.get("value"),
            warning_high_threshold=element_data.get("warning_high_threshold"),
            warning_low_threshold=element_data.get("warning_low_threshold"),
            critical_high_threshold=element_data.get("critical_high_threshold"),
            critical_low_threshold=element_data.get("critical_low_threshold"),
            threshold_state=element_data["threshold_state"],
            value_units=element_data.get("value_units"),
        )

    for element in NetAppResource.Sensors.get_collection(
        connection=connection, fields=",".join(field_query), type="discrete"
    ):
        element_data = element.to_dict()
        yield models.EnvironmentDiscreteSensorModel(
            name=element_data["name"],
            node_name=element_data["node"]["name"],
            sensor_type=element_data["type"],
            discrete_value=element_data.get("discrete_value"),
            discrete_state=element_data["discrete_state"],
        )


def fetch_qtree_quota(
    connection: HostConnection,
) -> Iterable[models.QtreeQuotaModel]:
    field_query = (
        "type",
        "qtree.name",
        "volume.name",
        "space.hard_limit",
        "space.used.total",
        "users",
    )

    for element in NetAppResource.QuotaReport.get_collection(
        connection=connection, fields=",".join(field_query)
    ):
        element_data = element.to_dict()

        if element_data["type"] != "tree":
            continue

        yield models.QtreeQuotaModel(
            name=element_data.get("qtree", {}).get("name"),
            volume=element_data["volume"]["name"],
            hard_limit=element_data.get("space", {}).get("hard_limit"),
            used_total=element_data.get("space", {}).get("used", {}).get("total"),
            users=[user["name"] for user in element_data.get("users", []) if "name" in user],
        )


def fetch_snapmirror(
    connection: HostConnection,
) -> Iterable[models.SnapMirrorModel]:
    field_query = (
        "state",
        "transfer.state",
        "policy.name",
        "policy.type",
        "source.svm.name",
        "source.svm.uuid",
        "lag_time",
        "destination.path",
        "destination.svm.name",
    )

    for element in NetAppResource.SnapmirrorRelationship.get_collection(
        connection=connection, fields=",".join(field_query)
    ):
        element_data = element.to_dict()

        yield models.SnapMirrorModel(
            destination_svm=element_data["destination"]["svm"]["name"],
            policy_name=element_data.get("policy", {}).get("name"),
            policy_type=element_data.get("policy", {}).get("type"),
            state=element_data.get("state"),
            transfer_state=element_data.get("transfer", {}).get("state"),
            source_svm_name=element_data["source"]["svm"]["name"],
            lag_time=element_data.get("lag_time"),
            destination=element_data["destination"]["path"],
        )


def fetch_fc_ports(connection: HostConnection) -> Iterable[models.FcPortModel]:
    field_query = (
        "supported_protocols",
        "wwpn",
        "wwnn",
        "physical_protocol",
        "state",
        "name",
        "description",
        "enabled",
        "node.name",
        "fabric.connected_speed",
    )

    for element in NetAppResource.FcPort.get_collection(
        connection=connection, fields=",".join(field_query)
    ):
        element_data = element.to_dict()
        yield models.FcPortModel(
            supported_protocols=element_data["supported_protocols"],
            wwpn=element_data["wwpn"],
            wwnn=element_data["wwnn"],
            physical_protocol=element_data["physical_protocol"],
            state=element_data["state"],
            name=element_data["name"],
            description=element_data["description"],
            enabled=element_data["enabled"],
            node_name=element_data["node"]["name"],
            connected_speed=element_data.get("fabric", {}).get("connected_speed"),
        )


def _pick_oldest_node_version(nodes: Iterable[models.NodeModel]) -> models.Version:
    """
    NetApp supports mixed version ONTAP clusters for limited periods of time and in specific scenarios.
    We need to support this.
    (see: https://docs.netapp.com/us-en/ontap/upgrade/concept_mixed_version_requirements.html)

    This function picks the oldest version from the list of nodes versions.
    In this way, inside fetch functions, we can query the API with the "oldest" set of fields
    to ensure a safe approach.
    """
    return min(node.version for node in nodes)


def write_sections(connection: HostConnection, logger: logging.Logger, args: Args) -> None:
    """Write monitoring sections based on selected resources"""
    fetched_resources = {obj.value for obj in args.fetched_resources}

    # Store volumes for counter sections that depend on them
    volumes = None
    nodes = list(fetch_nodes(connection))
    oldest_version = _pick_oldest_node_version(nodes)

    if FetchedResource.node.value in fetched_resources:
        write_section("node", nodes, logger)

    if (
        FetchedResource.volumes.value in fetched_resources
        or FetchedResource.volumes_counters.value in fetched_resources
    ):
        volumes = list(fetch_volumes(connection))
        write_section("volumes", volumes, logger)

    # Volume counters (depends on volumes)
    if FetchedResource.volumes_counters.value in fetched_resources:
        if volumes is None:
            volumes = list(fetch_volumes(connection))
        write_section("volumes_counters", fetch_volumes_counters(connection, volumes), logger)

    if FetchedResource.disk.value in fetched_resources:
        write_section("disk", fetch_disks(connection), logger)

    if FetchedResource.luns.value in fetched_resources:
        write_section("luns", fetch_luns(connection), logger)

    if FetchedResource.aggr.value in fetched_resources:
        write_section("aggr", fetch_aggr(connection, args), logger)

    if FetchedResource.qtree_quota.value in fetched_resources:
        write_section("qtree_quota", fetch_qtree_quota(connection), logger)

    if FetchedResource.snapvault.value in fetched_resources:
        write_section("snapvault", fetch_snapmirror(connection), logger)

    if FetchedResource.vs_status.value in fetched_resources:
        write_section("vs_status", fetch_vs_status(connection), logger)

    if FetchedResource.interfaces.value in fetched_resources:
        interfaces = list(fetch_interfaces(connection))
        write_section("if", interfaces, logger)
        write_section("if_counters", fetch_interfaces_counters(connection, interfaces), logger)

    if FetchedResource.fan.value in fetched_resources:
        write_section("fan", fetch_fans(connection, oldest_version), logger)

    if FetchedResource.temp.value in fetched_resources:
        write_section("temp", fetch_temperatures(connection, oldest_version), logger)

    if FetchedResource.alerts.value in fetched_resources:
        write_section("alerts", fetch_alerts(connection, args), logger)

    if FetchedResource.vs_traffic.value in fetched_resources:
        write_section("vs_traffic", fetch_vs_traffic_counters(connection), logger)

    if FetchedResource.psu.value in fetched_resources:
        write_section("psu", fetch_psu(connection), logger)

    if FetchedResource.environment.value in fetched_resources:
        write_section("environment", fetch_environment(connection), logger)

    if FetchedResource.fc_interfaces.value in fetched_resources:
        write_section("fc_ports", fetch_fc_ports(connection), logger)
        write_section("fc_interfaces_counters", fetch_fc_interfaces_counters(connection), logger)

    try:
        if FetchedResource.ports.value in fetched_resources:
            write_section("ports", fetch_ports(connection), logger)
    except NetAppRestError:
        raise CannotRecover("Fetch ports failed. Cluster could be in a degraded state.")


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument("--hostname", help="Hostname or IP-address of NetApp Filer.", required=True)
    parser.add_argument("--username", help="Username for NetApp login", required=True)
    parser.add_argument("--password", help="Secret/Password for NetApp login", required=True)

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
    parser.add_argument(
        "--fetched-resources",
        type=FetchedResource,
        nargs="+",
        default=[
            FetchedResource.volumes,
            FetchedResource.volumes_counters,
            FetchedResource.disk,
            FetchedResource.luns,
            FetchedResource.aggr,
            FetchedResource.vs_status,
            FetchedResource.ports,
            FetchedResource.interfaces,
            FetchedResource.node,
            FetchedResource.fan,
            FetchedResource.temp,
            FetchedResource.alerts,
            FetchedResource.vs_traffic,
            FetchedResource.psu,
            FetchedResource.environment,
            FetchedResource.qtree_quota,
            FetchedResource.snapvault,
            FetchedResource.fc_interfaces,
        ],
        help="The NetApp objects which are supposed to be fetched. Available resources: "
        + ", ".join([obj.value for obj in FetchedResource]),
    )
    cert_args = parser.add_mutually_exclusive_group()
    cert_args.add_argument(
        "--no-cert-check", action="store_true", help="Do not verify TLS certificate"
    )
    cert_args.add_argument(
        "--cert-server-name",
        help="Expect this as the servers name in the ssl certificate. Overrides '--no-cert-check'.",
    )

    return parser.parse_args(argv)


def _setup_logging(verbose: bool) -> logging.Logger:
    logging.basicConfig(
        level={0: logging.WARN, 1: logging.INFO, 2: logging.DEBUG}.get(verbose, logging.DEBUG),
    )
    return logging.getLogger(__name__)


def agent_netapp_main(args: Args) -> int:
    """
    For NetApp responses HTTP status codes:
    https://docs.netapp.com/us-en/ontap-restapi-9141//ontap/getting_started_with_the_ontap_rest_api.html#HTTP_status_codes

    """

    logger = _setup_logging(args.verbose)
    with HostConnection(
        args.hostname,
        args.username,
        args.password,
        verify=False if args.no_cert_check else True,  # pylint: disable=simplifiable-if-expression
        headers={"User-Agent": USER_AGENT},
    ) as connection:
        if isinstance(args.cert_server_name, str):
            connection.session.mount(
                connection.origin, HostnameValidationAdapter(args.cert_server_name)
            )

        logger.debug("Start writing sections")
        try:
            write_sections(connection, logger, args)
        except NetAppRestError as exc:
            if exc.status_code == 401:
                raise CannotRecover("Authentication failed. Please check the credentials.")
            raise exc
        logger.debug("All sections have been written")

    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_netapp_main)


if __name__ == "__main__":
    # TODO: Remove this
    main()
