#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
"""Special Agent to fetch Redfish data from management interfaces"""

# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>

# License: GNU General Public License v2

import time
import pickle
import logging
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import redfish
import urllib3
from cmk.special_agents.v0_unstable.agent_common import (
    SectionManager,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.v0_unstable.argument_parsing import (
    Args,
    create_default_argument_parser,
)
from cmk.utils import password_store, paths
from redfish.rest.v1 import (
    RetriesExhaustedError,
    ServerDownOrUnreachableError,
    JsonDecodingError,
)


class CachedSectionWriter(SectionManager):
    """
    >>> with SectionWriter("foo") as writer:
    ...   writer.append("str")
    ...   writer.append(char for char in "ab")
    ...   writer.append_json({"some": "dict"})
    ...   writer.append_json(char for char in "ab")
    <<<foo:sep(0)>>>
    str
    a
    b
    {"some": "dict"}
    "a"
    "b"
    """

    def __init__(
        self,
        section_name: str,
        separator: str | None = "\0",
        cachetime: int | None = None,
        validity: int | None = None,
    ) -> None:
        super().__init__()
        self.append(
            (
                f"<<<{section_name}{f':sep({ord(separator)})' if separator else ''}"
                f"{f':cached({cachetime},{validity})' if cachetime else ''}>>>"
            )
        )


def parse_arguments(argv: Sequence[str] | None) -> Args:
    """Parse arguments needed to construct an URL and for connection conditions"""
    sections = [
        "Power",
        "Thermal",
        "Memory",
        "NetworkAdapters",
        "NetworkInterfaces",
        "Processors",
        "Storage",
        "EthernetInterfaces",
        "FirmwareInventory",
        "SmartStorage",
        "ArrayControllers",
        "HostBusAdapters",
        "LogicalDrives",
        "PhysicalDrives",
        "SimpleStorage",
        "Drives",
        "Volumes",
    ]

    parser = create_default_argument_parser(description=__doc__)
    # required
    parser.add_argument(
        "-u", "--user", default=None, help="Username for Redfish Login", required=True
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-s",
        "--password",
        default=None,
        help="""Password for Redfish Login. Preferred over --password-id""",
    )
    group.add_argument(
        "--password-id",
        default=None,
        help="""Password store reference to the password for Redfish login""",
    )
    # optional
    parser.add_argument(
        "-P",
        "--proto",
        default="https",
        help="""Use 'http' or 'https' (default=https)""",
    )
    parser.add_argument(
        "-p",
        "--port",
        default=443,
        type=int,
        help="Use alternative port (default: 443)",
    )
    parser.add_argument(
        "-m",
        "--sections",
        default=",".join(sections),
        help=f"Comma separated list of data to query. \
               Possible values: {','.join(sections)} (default: all)",
    )
    parser.add_argument(
        "-n",
        "--disabled_sections",
        default="",
        help=f"Comma separated list of data to ignore. \
               Possible values: {','.join(sections)} (default: None)",
    )
    parser.add_argument(
        "-c",
        "--cached_sections",
        default="",
        help=f"Comma separated list of sections and times. \
               Possible values: {','.join(sections)} (default: None)",
    )
    parser.add_argument(
        "--verify_ssl",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--timeout",
        default=3,
        type=int,
        help="""Timeout in seconds for a connection attempt""",
    )
    parser.add_argument(
        "--retries",
        default=2,
        type=int,
        help="""Number auf connection retries before failing""",
    )
    # required
    parser.add_argument(
        "host",
        metavar="HOSTNAME",
        help="""IP address or hostname of your Redfish compatible BMC""",
    )

    return parser.parse_args(argv)


def dropnonascii(input_str):
    """Drop all non ASCII characters from string"""
    output_str = ""
    for i in input_str:
        num = ord(i)
        if num >= 0:
            if num <= 127:
                output_str = output_str + i

    return output_str


def fetch_data(redfishobj, url, component, timeout=None):
    """fetch a single data object from Redfish"""
    if timeout:
        response_url = redfishobj.redfish_connection.get(url, timeout=timeout)
    else:
        response_url = redfishobj.redfish_connection.get(url, None)
    if response_url.status == 200:
        try:
            response_dict = response_url.dict
            return response_dict
        except JsonDecodingError:
            return {"error": f"{component} data had a JSON decoding problem\n"}

    return {"error": f"{component} data could not be fetched\n"}


def fetch_collection(redfishobj, data, component):
    """fetch a whole collection from Redfish data"""
    member_list = data.get("Members")
    data_list = []
    if not member_list:
        return data_list
    for element in member_list:
        if element.get("@odata.id"):
            element_data = fetch_data(redfishobj, element.get("@odata.id"), component)
            data_list.append(element_data)
    return data_list


def fetch_entry(redfishobj, entry, section):
    """fetch a list entry and add the result"""
    result = fetch_data(redfishobj, entry.get("@odata.id"), section)
    if "error" in result.keys():
        return redfishobj
    if "Collection" in result.get("@odata.type", "No Data"):
        result = fetch_collection(redfishobj, result, section)
        if section in redfishobj.section_data.keys():
            redfishobj.section_data[section].extend(result)
        else:
            redfishobj.section_data.setdefault(section, result)
    else:
        if section in redfishobj.section_data.keys():
            redfishobj.section_data[section].append(result)
        else:
            redfishobj.section_data.setdefault(
                section,
                [
                    result,
                ],
            )
    return redfishobj


def fetch_list_of_elements(redfishobj, fetching_sections, sections, data):
    """fetch a list of single elements from Redfish"""

    for section in fetching_sections:
        if section not in sections:
            continue
        if section not in data.keys():
            continue

        fetch_result = data.get(section)
        if not fetch_result:
            continue
        if isinstance(fetch_result, dict):
            # result = fetch_data(redfishobj, fetch_result.get("@odata.id"), section)
            fetch_entry(redfishobj, fetch_result, section)
        else:
            for entry in fetch_result:
                fetch_entry(redfishobj, entry, section)
    return redfishobj


def fetch_sections(redfishobj, fetching_sections, sections, data):
    """fetch a single section of Redfish data"""
    for section in fetching_sections:
        if section not in sections:
            continue
        if section not in data.keys():
            continue
        section_data = fetch_data(
            redfishobj, data.get(section).get("@odata.id"), section
        )
        if section_data.get("Members@odata.count") == 0:
            continue
        if "Collection" in section_data.get("@odata.type", {}):
            if section_data.get("Members@odata.count", 0) != 0:
                result = fetch_collection(redfishobj, section_data, section)
                if section in redfishobj.section_data.keys():
                    redfishobj.section_data[section].extend(result)
                else:
                    redfishobj.section_data.setdefault(section, result)
        else:
            if section in redfishobj.section_data.keys():
                redfishobj.section_data[section].append(section_data)
            else:
                redfishobj.section_data.setdefault(
                    section,
                    [
                        section_data,
                    ],
                )
    return redfishobj


def fetch_hpe_smartstorage(redfishobj, link_list, sections):
    """fetch hpe smartstorage sections"""
    storage_link = link_list.get("SmartStorage", None)
    if storage_link:
        result = fetch_data(redfishobj, storage_link.get("@odata.id"), "SmartStorage")
        storage_links = result.get("Links")
        storage_sections = [
            "ArrayControllers",
            "HostBusAdapters",
        ]
        controller_sections = [
            "LogicalDrives",
            "PhysicalDrives",
        ]
        resulting_sections = list(set(storage_sections).intersection(sections))
        fetch_sections(
            redfishobj, resulting_sections, sections, storage_links
        )
        for element in redfishobj.section_data.get("ArrayControllers", []):
            contrl_links = element.get("Links", {})
            resulting_sections = list(set(controller_sections).intersection(sections))
            fetch_sections(
                redfishobj, resulting_sections, sections, contrl_links
            )
    return redfishobj


def fetch_extra_data(redfishobj, data_model, extra_links, sections, data):
    """fetch manufacturer specific data"""
    link_list = {}
    link_data = data.get("Oem", {}).get(data_model, {}).get("Links", {})
    if link_data:
        for entry in link_data:
            if entry in extra_links:
                link_list.setdefault(entry, link_data.get(entry))
        if "SmartStorage" in link_list:
            fetch_hpe_smartstorage(redfishobj, link_list, sections)
            link_list.pop("SmartStorage")
        fetch_sections(redfishobj, extra_links, sections, link_list)
    return redfishobj


def process_result(redfishobj):
    """process and output a fetched result set"""
    result = redfishobj.section_data
    for element in list(result.keys()):
        if getattr(redfishobj.cache_timestamp_per_section, element):
            with CachedSectionWriter(
                f"redfish_{element.lower()}",
                cachetime=getattr(redfishobj.cache_timestamp_per_section, element),
                validity=getattr(redfishobj.cache_per_section, element),
            ) as w:
                if isinstance(result.get(element), list):
                    for entry in result.get(element):
                        w.append_json(entry)
                else:
                    w.append_json(result.get(element))
        else:
            with SectionWriter(f"redfish_{element.lower()}") as w:
                if isinstance(result.get(element), list):
                    for entry in result.get(element):
                        w.append_json(entry)
                else:
                    w.append_json(result.get(element))


@dataclass()
class CachePerSection:
    """Cache settings for every section"""

    Memory: int | None = None
    Power: int | None = None
    Processors: int | None = None
    Thermal: int | None = None
    FirmwareInventory: int | None = 9600
    NetworkAdapters: int | None = None
    NetworkInterfaces: int | None = None
    EthernetInterfaces: int | None = None
    Storage: int | None = None
    ArrayControllers: int | None = None
    SmartStorage: int | None = None
    HostBusAdapters: int | None = None
    PhysicalDrives: int | None = None
    LogicalDrives: int | None = None
    Drives: int | None = None
    Volumes: int | None = None
    SimpleStorage: int | None = None


@dataclass()
class CacheTimestampPerSection:
    """Cache timestamp if section is cached"""

    Memory: int | None = None
    Power: int | None = None
    Processors: int | None = None
    Thermal: int | None = None
    FirmwareInventory: int | None = None
    NetworkAdapters: int | None = None
    NetworkInterfaces: int | None = None
    EthernetInterfaces: int | None = None
    Storage: int | None = None
    ArrayControllers: int | None = None
    SmartStorage: int | None = None
    HostBusAdapters: int | None = None
    PhysicalDrives: int | None = None
    LogicalDrives: int | None = None
    Drives: int | None = None
    Volumes: int | None = None
    SimpleStorage: int | None = None


@dataclass()
class VendorData:
    """Vendor data object"""

    name: str
    version: str | None = None
    firmware_version: str | None = None
    view_supported: bool | None = False
    view_select: Mapping[str, object] | None = None
    view_response: Mapping[str, object] | None = None
    expand_string: str | None = None


@dataclass()
class RedfishData:
    """Redfish data object"""

    hostname: str
    use_cache: bool
    redfish_connection: redfish.redfish_client
    sections: Sequence[str] | None = None
    cache_per_section: CachePerSection | None = None
    cache_timestamp_per_section: CacheTimestampPerSection | None = None
    manager_data: Mapping[str, object] | None = None
    chassis_data: Mapping[str, object] | None = None
    base_data: Mapping[str, object] | None = None
    vendor_data: VendorData | None = None
    section_data: Mapping[str, Sequence[Mapping[str, object]]] = field(
        default_factory=dict
    )


def detect_vendor(redfishobj):
    """Extract Vendor information from base data"""
    root_data = redfishobj.base_data
    vendor_string = ""
    if root_data.get("Oem"):
        if len(root_data.get("Oem")) > 0:
            vendor_string = list(root_data.get("Oem"))[0]
    if vendor_string == "" and root_data.get("Vendor") is not None:
        vendor_string = root_data.get("Vendor")

    if vendor_string in ["Hpe", "Hp"]:
        vendor_data = VendorData(name="HPE", expand_string="?$expand=.")
        if vendor_string in ["Hp"]:
            vendor_data.expand_string = ""
        manager_data = (
            root_data.get("Oem", {}).get(vendor_string, {}).get("Manager", {})[0]
        )
        if manager_data:
            vendor_data.version = manager_data.get("ManagerType")
            if vendor_data.version is None:
                vendor_data.version = (
                    root_data.get("Oem", {})
                    .get(vendor_string, {})
                    .get("Moniker", {})
                    .get("PRODGEN")
                )
            vendor_data.firmware_version = manager_data.get("ManagerFirmwareVersion")
            if vendor_data.firmware_version is None:
                vendor_data.firmware_version = manager_data.get("Languages", {})[0].get(
                    "Version"
                )
    elif vendor_string in ["Lenovo"]:
        vendor_data = VendorData(
            name="Lenovo", version="xClarity", expand_string="?$expand=*"
        )
    elif vendor_string in ["Dell"]:
        vendor_data = VendorData(
            name="Dell", version="iDRAC", expand_string="?$expand=*($levels=1)"
        )
    elif vendor_string in ["Huawei"]:
        vendor_data = VendorData(
            name="Huawei", version="BMC", expand_string="?$expand=.%28$levels=1%29"
        )
    elif vendor_string in ["ts_fujitsu"]:
        vendor_data = VendorData(
            name="Fujitsu", version="iRMC", expand_string="?$expand=Members"
        )
    elif vendor_string in ["Ami"]:
        vendor_data = VendorData(name="Ami")
    elif vendor_string in ["Supermicro"]:
        vendor_data = VendorData(name="Supermicro")
    elif vendor_string in ["Cisco", "Cisco Systems Inc."]:
        vendor_data = VendorData(name="Cisco", version="CIMC")
    elif vendor_string in ["Seagate"]:
        vendor_data = VendorData(name="Seagate")
    else:
        vendor_data = VendorData(name="Generic")

    redfishobj.vendor_data = vendor_data
    return redfishobj


def get_information(redfishobj):
    """get a the information from the Redfish management interface"""
    load_section_data(redfishobj)
    redfishobj.base_data = fetch_data(redfishobj, "/redfish/v1", "Base")

    detect_vendor(redfishobj)

    manager_url = redfishobj.base_data.get("Managers", {}).get("@odata.id")
    chassis_url = redfishobj.base_data.get("Chassis", {}).get("@odata.id")
    systems_url = redfishobj.base_data.get("Systems", {}).get("@odata.id")

    data_model = ""
    manager_data = False

    # fetch managers
    if manager_url:
        if redfishobj.vendor_data.expand_string:
            manager_col = fetch_data(
                redfishobj,
                manager_url + redfishobj.vendor_data.expand_string,
                "Manager",
            )
            manager_data = manager_col.get("Members", [])
        else:
            manager_col = fetch_data(redfishobj, manager_url, "Manager")
            manager_data = fetch_collection(redfishobj, manager_col, "Manager")

        for element in manager_data:
            data_model = list(element.get("Oem", {"Unknown": "Unknown model"}).keys())[
                0
            ]
            if not redfishobj.vendor_data.firmware_version:
                redfishobj.vendor_data.firmware_version = element.get(
                    "FirmwareVersion", ""
                )

    with SectionWriter("check_mk", " ") as w:
        w.append("Version: 2.3.0")
        w.append("AgentOS: redfish")
        w.append("OSType: redfish")
        w.append(f"OSName: {redfishobj.vendor_data.version}")
        w.append(f"OSVersion: {redfishobj.vendor_data.firmware_version}")
        w.append(f"OSPlatform: {redfishobj.vendor_data.name}")

    # fetch systems
    systems_col = fetch_data(redfishobj, systems_url, "System")
    systems_data = fetch_collection(redfishobj, systems_col, "System")

    if data_model in ["Hpe", "Hp"]:
        data_model_links = []
        for system in systems_data:
            system_oem_links = list(
                system.get("Oem", {"Unknown": "Unknown model"})
                .get(data_model, {"Unknown": "Unknown model"})
                .get("Links", {})
                .keys()
            )
            data_model_links.extend(system_oem_links)
        extra_links = list(set(data_model_links).intersection(redfishobj.sections))
    else:
        extra_links = []

    if data_model in ["Hp"] and ("FirmwareInventory" in redfishobj.sections):
        res_dir = (
            redfishobj.base_data.get("Oem", {"Unknown": "Unknown model"})
            .get(data_model, {"Unknown": "Unknown model"})
            .get("Links", {})
            .get("ResourceDirectory", {})
            .get("@odata.id")
        )
        if res_dir:
            res_data = fetch_data(redfishobj, res_dir, "ResourceDirectory")
            res_instances = res_data.get("Instances", [])
            for instance in res_instances:
                if "#FwSwVersionInventory." in instance.get(
                    "@odata.type", ""
                ) and "FirmwareInventory" in instance.get("@odata.id", ""):
                    firmwares = fetch_data(
                        redfishobj,
                        instance["@odata.id"] + redfishobj.vendor_data.expand_string,
                        "FirmwareDirectory",
                    )
                    if firmwares.get("Current"):
                        redfishobj.sections.remove("FirmwareInventory")
                        redfishobj.section_data.setdefault("FirmwareInventory", firmwares)

    if manager_data:
        with SectionWriter("redfish_manager") as w:
            w.append_json(manager_data)

    with SectionWriter("redfish_system") as w:
        w.append_json(systems_data)

    systems_sections = list(
        set(
            [
                "FirmwareInventory",
                "EthernetInterfaces",
                "NetworkInterfaces",
                "Processors",
                "Storage",
                "Memory",
            ]
        ).union(extra_links)
    )
    systems_sub_sections = [
        "Drives",
        "Volumes",
    ]

    resulting_sections = list(set(systems_sections).intersection(redfishobj.sections))
    if "FirmwareInventory" in resulting_sections and redfishobj.base_data.get(
        "UpdateService", {}
    ).get("@odata.id"):
        firmware_url = (
            redfishobj.base_data.get("UpdateService").get("@odata.id"),
            "/FirmwareInventory",
            (
                redfishobj.vendor_data.expand_string
                if redfishobj.vendor_data.expand_string
                else ""
            ),
        )
        if redfishobj.vendor_data.expand_string:
            firmwares = fetch_data(
                redfishobj,
                "".join(firmware_url),
                "FirmwareDirectory",
                timeout=10,
            )
            if firmwares.get("Members"):
                redfishobj.section_data.setdefault(
                    "FirmwareInventory",
                    firmwares.get("Members"),
                )
        else:
            firmware_col = fetch_data(
                redfishobj,
                "".join(firmware_url),
                "FirmwareDirectory",
            )
            firmwares = fetch_collection(redfishobj, firmware_col, "Manager")
            redfishobj.section_data.setdefault("FirmwareInventory", firmwares)

    for system in systems_data:
        if data_model in ["Hpe", "Hp"] and "SmartStorage" in resulting_sections:
            if redfishobj.vendor_data.firmware_version.startswith("3."):
                resulting_sections.remove("SmartStorage")
            elif "Storage" in resulting_sections:
                resulting_sections.remove("Storage")
        fetch_sections(redfishobj, resulting_sections, redfishobj.sections, system)
        if "Storage" in redfishobj.section_data.keys():
            storage_data = redfishobj.section_data.get("Storage")
            if isinstance(storage_data, list):
                for entry in storage_data:
                    if entry.get("error"):
                        continue
                    if (
                        entry.get("Drives@odata.count", 0) != 0
                        or len(entry.get("Drives", [])) >= 1
                    ):
                        fetch_list_of_elements(
                            redfishobj, systems_sub_sections, redfishobj.sections, entry
                        )
            else:
                fetch_list_of_elements(
                    redfishobj, systems_sub_sections, redfishobj.sections, storage_data
                )

        if extra_links:
            fetch_extra_data(
                redfishobj, data_model, extra_links, redfishobj.sections, system
            )

    # fetch chassis
    chassis_col = fetch_data(redfishobj, chassis_url, "Chassis")
    chassis_data = fetch_collection(redfishobj, chassis_col, "Chassis")
    with SectionWriter("redfish_chassis") as w:
        w.append_json(chassis_data)
    chassis_sections = [
        "NetworkAdapters",
        "Power",
        "Thermal",
    ]
    # new_environment_resources = [
    #     "Sensors",
    #     "EnvironmentMetrics",
    #     "PowerSubsystem",
    #     "ThermalSubsystem",
    # ]

    resulting_sections = list(set(chassis_sections).intersection(redfishobj.sections))
    for chassis in chassis_data:
        fetch_sections(redfishobj, resulting_sections, redfishobj.sections, chassis)
    process_result(redfishobj)
    store_section_data(redfishobj)
    return 0


def store_session_key(redfishobj):
    """save session data to file"""
    store_data = {}
    if not os.path.exists(paths.tmp_dir / "agents" / "agent_redfish"):
        os.makedirs(paths.tmp_dir / "agents" / "agent_redfish")
    store_path = (
        paths.tmp_dir / "agents" / "agent_redfish" / f"{redfishobj.hostname}.pkl"
    )
    store_data.setdefault(
        "location", redfishobj.redfish_connection.get_session_location()
    )
    store_data.setdefault("session", redfishobj.redfish_connection.get_session_key())
    with open(store_path, "wb") as file:
        pickle.dump(store_data, file)


def store_section_data(redfishobj):
    """save section data to file"""
    for section in redfishobj.section_data.keys():
        if not getattr(redfishobj.cache_per_section, section):
            continue
        store_data = {}
        store_path = (
            paths.tmp_dir
            / "agents"
            / "agent_redfish"
            / f"{redfishobj.hostname}_{section}.pkl"
        )
        if getattr(redfishobj.cache_timestamp_per_section, section):
            continue
        store_data.setdefault("timestamp", int(time.time()))
        store_data.setdefault("data", redfishobj.section_data.get(section))
        with open(store_path, "wb") as file:
            pickle.dump(store_data, file)
        file.close()


def load_section_data(redfishobj):
    """load section data from file"""
    timestamps = CacheTimestampPerSection()
    for key, value in redfishobj.cache_per_section.__dict__.items():
        if not value:
            continue
        store_path = (
            paths.tmp_dir
            / "agents"
            / "agent_redfish"
            / f"{redfishobj.hostname}_{key}.pkl"
        )
        if os.path.exists(store_path):
            with open(store_path, "rb") as file:
                store_data = pickle.load(file)
            current_time = int(time.time())
            if store_data["timestamp"] + value < current_time:
                continue
            setattr(timestamps, key, store_data["timestamp"])
            redfishobj.section_data.setdefault(key, store_data["data"])
            redfishobj.sections.remove(key)
    redfishobj.cache_timestamp_per_section = timestamps
    return redfishobj


def load_session_key(redfishobj):
    """load existing redfish session data"""
    store_path = (
        paths.tmp_dir / "agents" / "agent_redfish" / f"{redfishobj.hostname}.pkl"
    )
    try:
        with open(store_path, "rb") as file:
            # Deserialize and retrieve the variable from the file
            data = pickle.load(file)
    except Exception as e:
        print(f"Exception: {e}")
        return None

    if data.get("session") and data.get("location"):
        return data
    return None


def get_session(args: Args):
    """create a Redfish session with given arguments"""
    try:
        redfish_host = f"{args.proto}://{args.host}:{args.port}"
        if args.password_id:
            pw_id, pw_path = args.password_id.split(":")
        else:
            pw_id = None
            pw_path = None
        # Create a Redfish client object
        redfishobj = RedfishData(
            hostname=f"{args.host}_{args.port}",
            use_cache=False,
            redfish_connection=redfish.redfish_client(
                base_url=redfish_host,
                username=args.user,
                password=(
                    args.password
                    if args.password is not None
                    else password_store.lookup(Path(pw_path), pw_id)
                ),
                cafile="",
                default_prefix="/redfish/v1",
                timeout=args.timeout,
                max_retry=args.retries,
            ),
        )
        existing_session = load_session_key(redfishobj)
        # existing session with key found reuse this session instead of login
        if existing_session:
            redfishobj.redfish_connection.set_session_location(
                existing_session.get("location")
            )
            redfishobj.redfish_connection.set_session_key(
                existing_session.get("session")
            )
            response_url = redfishobj.redfish_connection.get(
                "/redfish/v1/SessionService/Sessions", None
            )
            if response_url.status == 200:
                return redfishobj
            response_url = redfishobj.redfish_connection.get(
                "/redfish/v1/Sessions", None
            )
            if response_url.status == 200:
                return redfishobj

        # Login with the Redfish client
        # cleanup old session information
        redfishobj.redfish_connection.set_session_location(None)
        redfishobj.redfish_connection.set_session_key(None)
        redfishobj.redfish_connection.login(auth="session")
    except ServerDownOrUnreachableError as excp:
        sys.stderr.write(
            f"ERROR: server not reachable or does not support RedFish. Error Message: {excp}\n"
        )
        sys.exit(1)
    except RetriesExhaustedError as excp:
        sys.stderr.write(f"ERROR: too many retries for connection attempt: {excp}\n")
        sys.exit(1)
    store_session_key(redfishobj)
    return redfishobj


def agent_redfish_main(args: Args) -> int:
    """main function for the special agent"""

    if not args.verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if args.debug:
        # Config logger used by Restful library
        logger_file = "RedfishApi.log"
        logger_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logger = redfish.redfish_logger(logger_file, logger_format, logging.INFO)
        logger.info("Redfish API")

    # Start Redfish Session Object
    redfishobj = get_session(args)
    sections = args.sections.split(",")
    sections_disabled = args.disabled_sections.split(",")
    cached_sections = CachePerSection()
    for element in args.cached_sections.split(","):
        if len(element.split("-")) != 2:
            continue
        n, m = element.split("-")
        setattr(cached_sections, n.replace("cache_time_", ""), int(m))
    redfishobj.cache_per_section = cached_sections
    redfishobj.sections = list(set(sections).difference(sections_disabled))
    get_information(redfishobj)
    # logout not needed anymore if no problem - session saved to file
    # logout is done if some query fails
    # REDFISHOBJ.logout()

    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_redfish_main)


if __name__ == "__main__":
    sys.exit(main())
