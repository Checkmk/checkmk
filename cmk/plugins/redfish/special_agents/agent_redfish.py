#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Special Agent to fetch Redfish data from management interfaces"""

import json
import logging
import sys
import time
from collections.abc import Collection, Container, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal, Self

import urllib3
from redfish import redfish_logger  # type: ignore[import-untyped]
from redfish.rest.v1 import (  # type: ignore[import-untyped]
    HttpClient,
    InvalidCredentialsError,
    JsonDecodingError,
    redfish_client,
    RestResponse,
    RetriesExhaustedError,
    ServerDownOrUnreachableError,
)

from cmk.utils import password_store, paths

from cmk.plugins.redfish.lib import REDFISH_SECTIONS
from cmk.special_agents.v0_unstable.agent_common import (
    CannotRecover,
    SectionManager,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.v0_unstable.argument_parsing import (
    Args,
    create_default_argument_parser,
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
            f"<<<{section_name}{f':sep({ord(separator)})' if separator else ''}"
            f"{f':cached({cachetime},{validity})' if cachetime else ''}>>>"
        )


@dataclass
class Vendor:
    """Vendor data object"""

    name: str
    version: str | None = None
    firmware_version: str | None = None
    expand_string: str | None = None


class ClientSession:
    """Client session data"""

    DIR = paths.tmp_dir / "agents/agent_redfish"

    def __init__(self, location: str, session: str) -> None:
        self.location: Final = location
        self.session: Final = session

    @classmethod
    def loadf(cls, hostname: str) -> Self | None:
        """Load session data from file"""
        try:
            raw = (cls.DIR / f"{hostname}.json").read_text()
        except FileNotFoundError:
            return None
        raw_json = json.loads(raw)
        return cls(location=str(raw_json["location"]), session=str(raw_json["session"]))

    def savef(self, hostname: str) -> None:
        """Save session data to file"""
        self.DIR.mkdir(parents=True, exist_ok=True)
        (self.DIR / f"{hostname}.json").write_text(
            json.dumps({"location": self.location, "session": self.session})
        )


class RedfishClient:
    """the redfish.HttpClient is completely untyped, so wrap it"""

    def __init__(self, client: HttpClient) -> None:
        self._client = client

    def get(self, url: str, timeout: int | None) -> RestResponse:
        try:
            return self._client.get(url, timeout=timeout)
        except RetriesExhaustedError as excp:
            raise CannotRecover("ERROR: too many retries for connection attempt") from excp

    def make_session(self, host_name: str, auth: Literal["session"]) -> None:
        if session := ClientSession.loadf(host_name):
            self._client.set_session_location(session.location)
            self._client.set_session_key(session.session)
            if (
                self._client.get("/redfish/v1/SessionService/Sessions", None).status == 200
                or self._client.get("/redfish/v1/Sessions", None).status == 200
            ):
                return
            # cleanup old session information
            self._client.set_session_location(None)
            self._client.set_session_key(None)

        # Login with the Redfish client
        self._client.login(auth=auth)
        ClientSession(
            str(self._client.get_session_location()), str(self._client.get_session_key())
        ).savef(host_name)


@dataclass
class RedfishData:
    """Redfish data object"""

    hostname: str
    use_cache: bool
    redfish_connection: RedfishClient
    sections: set[str] = field(default_factory=set)
    cache_per_section: Mapping[str, int] = field(default_factory=dict)
    cache_timestamp_per_section: Mapping[str, int] = field(default_factory=dict)
    manager_data: Mapping[str, object] | None = None
    chassis_data: Mapping[str, object] | None = None
    base_data: Mapping[str, Any] = field(default_factory=dict)
    vendor_data: Vendor | None = None
    section_data: dict[str, Any] = field(default_factory=dict)


def parse_arguments(argv: Sequence[str] | None) -> Args:
    """Parse arguments needed to construct an URL and for connection conditions"""
    sections = [s.name for s in REDFISH_SECTIONS]

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
        type=lambda x: x.split(",") if x else [],
        default=sections,
        help=f"Comma separated list of data to query. \
               Possible values: {','.join(sections)} (default: all)",
    )
    parser.add_argument(
        "-n",
        "--disabled_sections",
        type=lambda x: x.split(",") if x else [],
        default=(),
        help=f"Comma separated list of data to ignore. \
               Possible values: {','.join(sections)} (default: None)",
    )
    parser.add_argument(
        "-c",
        "--cached_sections",
        type=lambda x: x.split(",") if x else [],
        default=(),
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


def dropnonascii(input_str: str) -> str:
    """Drop all non ASCII characters from string"""
    output_str = ""
    for i in input_str:
        num = ord(i)
        if num >= 0:
            if num <= 127:
                output_str = output_str + i

    return output_str


def fetch_data(
    client: RedfishClient, url: str, component: object, timeout: int | None = None
) -> Any:
    """fetch a single data object from Redfish"""
    if timeout:
        response_url = client.get(url, timeout=timeout)
    else:
        response_url = client.get(url, None)
    if response_url.status == 200:
        try:
            response_dict = response_url.dict
            return response_dict
        except JsonDecodingError:
            return {"error": f"{component} data had a JSON decoding problem\n"}

    return {"error": f"{component} data could not be fetched\n"}


def fetch_collection(
    client: RedfishClient, data: Mapping[str, Any], component: object
) -> Sequence[Mapping[str, Any]]:
    """fetch a whole collection from Redfish data"""
    member_list = data.get("Members")
    data_list: list = []
    if not member_list:
        return data_list
    for element in member_list:
        if element.get("@odata.id"):
            element_data = fetch_data(client, element.get("@odata.id"), component)
            data_list.append(element_data)
    return data_list


def fetch_entry(redfishobj: RedfishData, entry: Mapping[str, Any], section: str) -> RedfishData:
    """fetch a list entry and add the result"""
    result = fetch_data(redfishobj.redfish_connection, entry["@odata.id"], section)
    if "error" in result.keys():
        return redfishobj
    if "Collection" in result.get("@odata.type", "No Data"):
        result = fetch_collection(redfishobj.redfish_connection, result, section)
        if section in redfishobj.section_data.keys():
            redfishobj.section_data[section].extend(result)
        else:
            redfishobj.section_data.setdefault(section, list(result))
    elif section in redfishobj.section_data.keys():
        redfishobj.section_data[section].append(result)
    else:
        redfishobj.section_data.setdefault(
            section,
            [
                result,
            ],
        )
    return redfishobj


def fetch_list_of_elements(
    redfishobj: RedfishData,
    fetching_sections: Iterable[str],
    sections: Container[str],
    data: Mapping[str, Any],
) -> RedfishData:
    """fetch a list of single elements from Redfish"""

    for section in fetching_sections:
        if section not in sections:
            continue
        if section not in data.keys():
            continue

        fetch_result = data.get(section)
        if not fetch_result:
            continue
        if isinstance(fetch_result, Mapping):
            # result = fetch_data(redfishobj, fetch_result.get("@odata.id"), section)
            fetch_entry(redfishobj, fetch_result, section)
        else:
            for entry in fetch_result:
                fetch_entry(redfishobj, entry, section)
    return redfishobj


def fetch_sections(
    redfishobj: RedfishData,
    fetching_sections: Iterable[str],
    sections: Container[str],
    data: Mapping[str, Any],
) -> RedfishData:
    """fetch a single section of Redfish data"""
    for section in fetching_sections:
        if section not in sections:
            continue
        if section not in data.keys():
            continue
        section_data = fetch_data(
            redfishobj.redfish_connection, data[section]["@odata.id"], section
        )
        if section_data.get("Members@odata.count") == 0:
            continue
        if "Collection" in section_data.get("@odata.type", {}):
            if section_data.get("Members@odata.count", 0) != 0:
                result = fetch_collection(redfishobj.redfish_connection, section_data, section)
                if section in redfishobj.section_data.keys():
                    redfishobj.section_data[section].extend(result)
                else:
                    redfishobj.section_data.setdefault(section, list(result))
        elif section in redfishobj.section_data.keys():
            redfishobj.section_data[section].append(section_data)
        else:
            redfishobj.section_data.setdefault(
                section,
                [
                    section_data,
                ],
            )
    return redfishobj


def fetch_hpe_smartstorage(
    redfishobj: RedfishData, link_list: Mapping[str, Mapping[str, str]], sections: Collection[str]
) -> RedfishData:
    """fetch hpe smartstorage sections"""
    storage_link = link_list.get("SmartStorage", None)
    if storage_link:
        result = fetch_data(
            redfishobj.redfish_connection, storage_link["@odata.id"], "SmartStorage"
        )
        storage_links = result["Links"]
        assert not isinstance(storage_links, str)
        storage_sections = [
            "ArrayControllers",
            "HostBusAdapters",
        ]
        controller_sections = [
            "LogicalDrives",
            "PhysicalDrives",
        ]
        resulting_sections = list(set(storage_sections).intersection(sections))
        fetch_sections(redfishobj, resulting_sections, sections, storage_links)
        for element in redfishobj.section_data.get("ArrayControllers", []):
            contrl_links = element.get("Links", {})
            assert isinstance(contrl_links, Mapping)
            resulting_sections = list(set(controller_sections).intersection(sections))
            fetch_sections(redfishobj, resulting_sections, sections, contrl_links)
    return redfishobj


def fetch_extra_data(
    redfishobj: RedfishData,
    data_model: str,
    extra_links: Collection[str],
    sections: Collection[str],
    data: Mapping[str, Any],
) -> RedfishData:
    """fetch manufacturer specific data"""
    link_list: dict = {}
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


def process_result(redfishobj: RedfishData) -> None:
    """process and output a fetched result set"""
    result = redfishobj.section_data
    for element in list(result.keys()):
        if cachetime := redfishobj.cache_timestamp_per_section.get(element):
            with CachedSectionWriter(
                f"redfish_{element.lower()}",
                cachetime=cachetime,
                validity=redfishobj.cache_per_section.get(element),
            ) as w:
                if isinstance(result.get(element), list):
                    for entry in result[element]:
                        w.append_json(entry)
                else:
                    w.append_json(result.get(element))
        else:
            with SectionWriter(f"redfish_{element.lower()}") as w:
                if isinstance(result.get(element), list):
                    for entry in result[element]:
                        w.append_json(entry)
                else:
                    w.append_json(result.get(element))


def detect_vendor(root_data: Mapping[str, Any]) -> Vendor:
    """Extract Vendor information from base data"""
    vendor_string = ""
    if root_data.get("Oem"):
        if len(root_data["Oem"]) > 0:
            vendor_string = list(root_data["Oem"])[0]
    if vendor_string == "" and root_data.get("Vendor") is not None:
        vendor_string = root_data["Vendor"]

    match vendor_string:
        case "Hpe" | "Hp":
            vendor_data = Vendor(name="HPE", expand_string="?$expand=.")
            if vendor_string in ["Hp"]:
                vendor_data.expand_string = ""
            manager_data = root_data.get("Oem", {}).get(vendor_string, {}).get("Manager", [])
            if manager_data:
                manager_data = manager_data[0]
            if isinstance(manager_data, dict):
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
            return vendor_data

        case "Lenovo":
            return Vendor(name="Lenovo", version="xClarity", expand_string="?$expand=*")

        case "Dell":
            return Vendor(name="Dell", version="iDRAC", expand_string="?$expand=*($levels=1)")

        case "Huawei":
            return Vendor(name="Huawei", version="BMC", expand_string="?$expand=.%28$levels=1%29")

        case "ts_fujitsu":
            return Vendor(name="Fujitsu", version="iRMC", expand_string="?$expand=Members")

        case "Cisco" | "Cisco Systems Inc.":
            return Vendor(name="Cisco", version="CIMC")

        case "Ami" | "Supermicro" | "Seagate" as name:
            return Vendor(name=name)

    # TODO: why not use the vendor string here?
    return Vendor(name="Generic")


def get_information(redfishobj: RedfishData) -> Literal[0]:  # pylint: disable=too-many-branches
    """get a the information from the Redfish management interface"""
    load_section_data(redfishobj)
    redfishobj.base_data = fetch_data(redfishobj.redfish_connection, "/redfish/v1", "Base")

    redfishobj.vendor_data = (vendor_data := detect_vendor(redfishobj.base_data))

    manager_url = redfishobj.base_data.get("Managers", {}).get("@odata.id")
    chassis_url = redfishobj.base_data.get("Chassis", {}).get("@odata.id")
    systems_url = redfishobj.base_data.get("Systems", {}).get("@odata.id")

    data_model = ""
    manager_data: Sequence[Mapping[str, Any]] = []

    # fetch managers
    if manager_url:
        if vendor_data.expand_string:
            manager_col = fetch_data(
                redfishobj.redfish_connection,
                manager_url + vendor_data.expand_string,
                "Manager",
            )
            manager_data = manager_col.get("Members", [])
        else:
            manager_col = fetch_data(redfishobj.redfish_connection, manager_url, "Manager")
            manager_data = fetch_collection(redfishobj.redfish_connection, manager_col, "Manager")

        for element in manager_data:
            data_model = str(list(element.get("Oem", {"Unknown": "Unknown model"}).keys())[0])
            if not vendor_data.firmware_version:
                vendor_data.firmware_version = element.get("FirmwareVersion", "")

    labels = {
        "cmk/os_family": "redfish",
        "cmk/os_name": vendor_data.version,
        "cmk/os_platform": vendor_data.name,
        "cmk/os_type": "redfish",
        "cmk/os_version": vendor_data.firmware_version,
    }
    sys.stdout.write(f"<<<labels:sep(0)>>>\n{json.dumps({k: v for k, v in labels.items() if v})}\n")

    # fetch systems
    systems_col = fetch_data(redfishobj.redfish_connection, systems_url, "System")
    systems_data = fetch_collection(redfishobj.redfish_connection, systems_col, "System")

    if data_model in ["Hpe", "Hp"]:
        data_model_links = []
        for system in systems_data:
            system_oem_links = list(
                system.get("Oem", ())
                .get(data_model, {"Unknown": "Unknown model"})
                .get("Links", {})
                .keys()
            )
            data_model_links.extend(system_oem_links)
        extra_links = list(set(data_model_links).intersection(redfishobj.sections))
    else:
        extra_links = []

    if data_model in ["Hp"] and ("FirmwareInventory" in redfishobj.sections):
        try:
            res_dir = redfishobj.base_data["Oem"][data_model]["Links"]["ResourceDirectory"][
                "@odata.id"
            ]
        except KeyError:
            res_dir = None

        if res_dir:
            res_data = fetch_data(redfishobj.redfish_connection, res_dir, "ResourceDirectory")
            res_instances = res_data.get("Instances", [])
            assert not isinstance(res_instances, str)
            for instance in res_instances:
                if "#FwSwVersionInventory." in instance.get(
                    "@odata.type", ""
                ) and "FirmwareInventory" in instance.get("@odata.id", ""):
                    firmwares = fetch_data(
                        redfishobj.redfish_connection,
                        instance["@odata.id"] + vendor_data.expand_string,
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
        {
            "FirmwareInventory",
            "EthernetInterfaces",
            "NetworkInterfaces",
            "Processors",
            "Storage",
            "Memory",
        }.union(extra_links)
    )
    systems_sub_sections = [
        "Drives",
        "Volumes",
    ]

    resulting_sections = list(set(systems_sections).intersection(redfishobj.sections))
    update_service = redfishobj.base_data.get("UpdateService")
    if (
        "FirmwareInventory" in resulting_sections
        and isinstance(update_service, Mapping)
        and "@odata.id" in update_service
    ):
        firmware_url = (
            update_service["@odata.id"],
            "/FirmwareInventory",
            (vendor_data.expand_string if vendor_data.expand_string else ""),
        )
        if vendor_data.expand_string:
            firmwares = fetch_data(
                redfishobj.redfish_connection,
                "".join(firmware_url),
                "FirmwareDirectory",
                timeout=40,
            )
            if members := firmwares.get("Members"):
                assert not isinstance(members, str)
                redfishobj.section_data.setdefault(
                    "FirmwareInventory",
                    members,
                )
        else:
            firmware_col = fetch_data(
                redfishobj.redfish_connection,
                "".join(firmware_url),
                "FirmwareDirectory",
            )
            firmwares = fetch_collection(redfishobj.redfish_connection, firmware_col, "Manager")
            redfishobj.section_data.setdefault("FirmwareInventory", list(firmwares))

    for system in systems_data:
        if data_model in ["Hpe", "Hp"] and "SmartStorage" in resulting_sections:
            if isinstance((fv := vendor_data.firmware_version), str) and fv.startswith("3."):
                resulting_sections.remove("SmartStorage")
            elif "Storage" in resulting_sections:
                resulting_sections.remove("Storage")
        fetch_sections(redfishobj, resulting_sections, redfishobj.sections, system)
        if "Storage" in redfishobj.section_data.keys():
            storage_data = redfishobj.section_data["Storage"]
            if isinstance(storage_data, list):
                for entry in storage_data:
                    if entry.get("error"):
                        continue
                    if entry.get("Drives@odata.count", 0) != 0 or len(entry.get("Drives", [])) >= 1:
                        fetch_list_of_elements(
                            redfishobj, systems_sub_sections, redfishobj.sections, entry
                        )
            else:
                fetch_list_of_elements(
                    redfishobj, systems_sub_sections, redfishobj.sections, storage_data
                )

        if extra_links:
            fetch_extra_data(redfishobj, data_model, extra_links, redfishobj.sections, system)

    # fetch chassis
    chassis_col = fetch_data(redfishobj.redfish_connection, chassis_url, "Chassis")
    chassis_data = fetch_collection(redfishobj.redfish_connection, chassis_col, "Chassis")
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


def _make_cached_section_path(hostname: str, section: str) -> Path:
    return paths.tmp_dir / "agents" / "agent_redfish" / f"{hostname}_{section}.json"


def store_section_data(redfishobj: RedfishData) -> None:
    """save section data to file"""
    for section in redfishobj.section_data.keys():
        if not redfishobj.cache_per_section.get(section):
            continue
        if redfishobj.cache_timestamp_per_section.get(section):
            continue

        store_path = _make_cached_section_path(redfishobj.hostname, section)
        store_path.parent.mkdir(parents=True, exist_ok=True)

        store_path.write_text(
            json.dumps(
                {
                    "timestamp": int(time.time()),
                    "data": redfishobj.section_data.get(section),
                }
            )
        )


def load_section_data(redfishobj: RedfishData) -> RedfishData:
    """load section data from file"""
    timestamps = {}
    for key, value in redfishobj.cache_per_section.items():
        store_path = _make_cached_section_path(redfishobj.hostname, key)
        try:
            raw = store_path.read_text()
        except FileNotFoundError:
            pass
        else:
            store_data = json.loads(raw)
            current_time = int(time.time())
            if store_data["timestamp"] + value < current_time:
                continue
            if key not in redfishobj.sections:
                continue
            timestamps[key] = store_data["timestamp"]
            redfishobj.section_data.setdefault(key, store_data["data"])
            redfishobj.sections.remove(key)

    redfishobj.cache_timestamp_per_section = timestamps
    return redfishobj


def get_session(args: Args) -> RedfishData:
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
            redfish_connection=RedfishClient(
                redfish_client(
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
                )
            ),
        )
        redfishobj.redfish_connection.make_session(redfishobj.hostname, auth="session")

    except ServerDownOrUnreachableError as excp:
        raise CannotRecover(
            f"Server not reachable or does not support RedFish. Error message: {excp}"
        ) from excp
    except RetriesExhaustedError as excp:
        raise CannotRecover(f"Too many retries for connection attempt: {excp}") from excp
    except InvalidCredentialsError as excp:
        raise CannotRecover(str(excp))

    return redfishobj


def agent_redfish_main(args: Args) -> int:
    """main function for the special agent"""

    if not args.verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if args.debug:
        # Config logger used by Restful library
        logger_file = "RedfishApi.log"
        logger_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logger = redfish_logger(logger_file, logger_format, logging.INFO)
        logger.info("Redfish API")

    # Start Redfish Session Object
    redfishobj = get_session(args)
    redfishobj.cache_per_section = {
        n: int(m) for n, m, *_ in (element.split("-") for element in args.cached_sections)
    }
    redfishobj.sections = {n for n in args.sections if n not in args.disabled_sections}
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
