#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.config_anonymizer.interface import AnonInterface
from cmk.config_anonymizer.step import AnonymizeStep
from cmk.gui.config import Config
from cmk.gui.watolib.host_attributes import host_attribute_registry, HostAttributes
from cmk.gui.watolib.hosts_and_folders import (
    folder_tree,
    StandardWATOInfoStorage,
    WATOFolderInfo,
)
from cmk.gui.watolib.utils import wato_root_dir
from cmk.utils.host_storage import (
    ContactGroupsField,
    FolderAttributesForBase,
    HostsStorageData,
    StandardHostsStorage,
)
from cmk.utils.tags import BuiltinTagConfig, TagGroupID, TagID

KNOWN_EXPLICIT_BUILTIN_ATTRS = ["cmk_agent_connection", "alias", "parents", "metrics_association"]


def _anonymize_snmp_credentials(
    anon_interface: AnonInterface, value: str | tuple[str, ...] | None
) -> str | tuple[str, ...] | None:
    """Anonymize SNMP credentials, masking all sensitive fields.

    Handles all SNMP credential formats:
    - SNMPv1/v2c: plain string (community)
    - SNMPv3 noAuthNoPriv: ("noAuthNoPriv", security_name)
    - SNMPv3 authNoPriv: ("authNoPriv", auth_protocol, security_name, auth_password)
    - SNMPv3 authPriv: ("authPriv", auth_protocol, security_name, auth_password, priv_protocol, priv_password)
    """
    if value is None:
        return None
    if isinstance(value, str):
        # SNMPv1/v2c community string
        return anon_interface.get_secret(value)
    match len(value):
        case 2:
            # noAuthNoPriv: (security_level, security_name)
            return (value[0], anon_interface.get_generic_mapping(value[1], "snmp_security_name"))
        case 4:
            # authNoPriv: (security_level, auth_protocol, security_name, auth_password)
            return (
                value[0],
                value[1],
                anon_interface.get_generic_mapping(value[2], "snmp_security_name"),
                anon_interface.get_secret(value[3]),
            )
        case 6:
            # authPriv: (security_level, auth_protocol, security_name, auth_password, priv_protocol, priv_password)
            return (
                value[0],
                value[1],
                anon_interface.get_generic_mapping(value[2], "snmp_security_name"),
                anon_interface.get_secret(value[3]),
                value[4],
                anon_interface.get_secret(value[5]),
            )
        case _:
            raise ValueError(f"Invalid SNMP credential format with {len(value)} elements")


def _anonymize_ipmi_credentials(
    anon_interface: AnonInterface, management_ipmi_credentials: Mapping[str, str]
) -> dict[str, str]:
    return {
        "username": anon_interface.get_generic_mapping(
            management_ipmi_credentials["username"], "ipmi_username"
        ),
        "password": anon_interface.get_secret(management_ipmi_credentials["password"]),
    }


def _anonymize_attributes(
    anon_interface: AnonInterface, data: dict[str, object]
) -> dict[str, object]:
    anon_data: dict[str, object] = {}

    if (ipaddresses := data.get("ipaddresses")) is not None:
        assert isinstance(ipaddresses, Mapping)
        anon_data["ipaddresses"] = {
            anon_interface.get_host(host): anon_interface.get_ipv4_address(ip)
            for host, ip in ipaddresses.items()
        }

    if (ipv6addresses := data.get("ipv6addresses")) is not None:
        assert isinstance(ipv6addresses, Mapping)
        anon_data["ipv6addresses"] = {
            anon_interface.get_host(host): anon_interface.get_ipv6_address(ip)
            for host, ip in ipv6addresses.items()
        }

    if (snmp_community := data.get("explicit_snmp_communities")) is not None:
        assert isinstance(snmp_community, Mapping)
        anon_data["explicit_snmp_communities"] = {
            anon_interface.get_host(host): _anonymize_snmp_credentials(anon_interface, value)
            for host, value in snmp_community.items()
        }

    if (management_snmp_credentials := data.get("management_snmp_credentials")) is not None:
        assert isinstance(management_snmp_credentials, Mapping)
        anon_data["management_snmp_credentials"] = {
            anon_interface.get_host(host): _anonymize_snmp_credentials(anon_interface, value)
            for host, value in management_snmp_credentials.items()
        }

    if (management_ipmi_credentials := data.get("management_ipmi_credentials")) is not None:
        assert isinstance(management_ipmi_credentials, Mapping)
        anon_data["management_ipmi_credentials"] = _anonymize_ipmi_credentials(
            anon_interface, management_ipmi_credentials
        )

    if (management_protocol := data.get("management_protocol")) is not None:
        assert isinstance(management_protocol, Mapping)
        anon_data["management_protocol"] = {
            anon_interface.get_host(host): value for host, value in management_protocol.items()
        }

    return anon_data


def _anonymize_contact_groups(
    anon_interface: AnonInterface, data: HostsStorageData
) -> ContactGroupsField:
    anon_contact_groups: ContactGroupsField = {
        "hosts": [],
        "services": [],
        "folder_hosts": [],
        "folder_services": [],
    }
    for host_entry in data.contact_groups["hosts"]:
        anon_contact_groups["hosts"].append(
            {
                "value": [
                    anon_interface.get_contact_group(contact_group)
                    for contact_group in host_entry["value"]
                ]
                if isinstance(host_entry["value"], list)
                else anon_interface.get_contact_group(host_entry["value"]),
                "condition": {
                    "host_name": [
                        anon_interface.get_host(h) for h in host_entry["condition"]["host_name"]
                    ]
                },
            }
        )
    for host_entry in data.contact_groups["services"]:
        anon_contact_groups["services"].append(
            {
                "value": [
                    anon_interface.get_contact_group(contact_group)
                    for contact_group in host_entry["value"]
                ]
                if isinstance(host_entry["value"], list)
                else anon_interface.get_contact_group(host_entry["value"]),
                "condition": {
                    "host_name": [
                        anon_interface.get_host(h) for h in host_entry["condition"]["host_name"]
                    ]
                },
            }
        )
    for folder_entry in data.contact_groups["folder_hosts"]:
        anon_contact_groups["folder_hosts"].append(
            {
                "value": [anon_interface.get_contact_group(v) for v in folder_entry["value"]],
                "condition": {
                    "host_folder": [
                        anon_interface.get_folder_path(contact_group)
                        for contact_group in folder_entry["condition"]["host_folder"]
                    ]
                    if isinstance(folder_entry["condition"]["host_folder"], list)
                    else anon_interface.get_folder_path(folder_entry["condition"]["host_folder"]),
                },
            }
        )
    for folder_entry in data.contact_groups["folder_services"]:
        anon_contact_groups["folder_services"].append(
            {
                "value": [
                    anon_interface.get_contact_group(contact_group)
                    for contact_group in folder_entry["value"]
                ]
                if isinstance(folder_entry["value"], list)
                else anon_interface.get_contact_group(folder_entry["value"]),
                "condition": {
                    "host_folder": [
                        anon_interface.get_folder_path(contact_group)
                        for contact_group in folder_entry["condition"]["host_folder"]
                    ]
                    if isinstance(folder_entry["condition"]["host_folder"], list)
                    else anon_interface.get_folder_path(folder_entry["condition"]["host_folder"]),
                },
            }
        )
    return anon_contact_groups


def _anonymize_host_and_folder_attribute(
    anon_interface: AnonInterface,
    attr_name: str,
    attr_value: Any,
    builtin_tag_group_ids: list[TagGroupID],
) -> tuple[str, object]:
    match attr_name:
        case "alias":
            return "alias", anon_interface.get_host_alias(attr_value)
        case "ipaddress":
            return "ipaddress", anon_interface.get_ipv4_address(attr_value)
        case "additional_ipv4addresses":
            return "additional_ipv4addresses", [
                anon_interface.get_ipv4_address(ip) for ip in attr_value
            ]
        case "ipv6address":
            return "ipv6address", anon_interface.get_ipv6_address(attr_value)
        case "additional_ipv6addresses":
            return "additional_ipv6addresses", [
                anon_interface.get_ipv6_address(ip) for ip in attr_value
            ]
        case "parents":
            return "parents", [anon_interface.get_host(h) for h in attr_value]
        case "snmp_community":
            return "snmp_community", _anonymize_snmp_credentials(anon_interface, attr_value)
        case "management_address":
            return "management_address", anon_interface.get_ipv4_address(attr_value)
        case "management_protocol":
            return "management_protocol", attr_value
        case "management_snmp_community":
            return "management_snmp_community", _anonymize_snmp_credentials(
                anon_interface, attr_value
            )
        case "management_ipmi_credentials":
            return "management_ipmi_credentials", _anonymize_ipmi_credentials(
                anon_interface, attr_value
            )
        case "site":
            return "site", anon_interface.get_site(attr_value)
        case "labels":
            return "labels", {
                k_an: v_an
                for k, v in attr_value.items()
                for k_an, v_an in [anon_interface.get_host_label_groups(k, v)]
            }
        case "contactgroups":
            anon_contact_group = attr_value.copy()
            anon_contact_group["groups"] = {
                "groups": [anon_interface.get_contact_group(g) for g in attr_value["groups"]]
            }
            return "contactgroups", anon_contact_group
        case "metrics_association":
            attr_mode, attr_metric_assoc = attr_value
            if attr_mode == "disabled":
                return "metrics_association", attr_value.copy()
            else:
                return "metrics_association", _anonymize_metrics_association(
                    anon_interface,
                    attr_metric_assoc,
                )

        case "meta_data":
            if (created_by := attr_value.get("created_by")) is not None:
                created_by = anon_interface.get_user(created_by)
            return "meta_data", {
                "created_at": attr_value.get("created_at"),
                "created_by": created_by,
                "updated_at": attr_value.get("updated_at"),
            }
        case str() if attr_name.startswith("tag_"):
            tag_key = attr_name[len("tag_") :]

            if tag_key in builtin_tag_group_ids:
                return attr_name, attr_value
            else:
                return anon_interface.get_id_of_tag_group(tag_key), anon_interface.get_tag_value(
                    attr_value
                )
        case "locked_attributes":
            # only built-in attributes can be locked
            return "locked_attributes", attr_value.copy()
        case "locked_by":
            site_id, program_id, program_instance_id = attr_value
            anon_instance_id = anon_interface.get_generic_mapping(
                program_instance_id,
                "program_instance_id",
            )
            return "locked_by", [
                anon_interface.get_site(site_id),
                program_id,
                anon_instance_id,
            ]
        case "network_scan":  # just for folders
            return "network_scan", attr_value
        case "network_scan_result":  # just for folders
            return "network_scan_result", attr_value
        case "bake_agent_package":  # just for folders
            return "bake_agent_package", attr_value
        case _:
            # custom host attributes
            return anon_interface.get_custom_host_attr_name(
                attr_name
            ), anon_interface.get_custom_host_attr_value(attr_value)


def _anonymize_single_host_and_folder_attributes(
    anon_interface: AnonInterface,
    builtin_tag_group_ids: list[TagGroupID],
    attributes: dict[str, object],
) -> dict[str, object]:
    anon_attributes: dict[str, object] = {}

    for attr_name, attr_value in attributes.items():
        anonymized_attr_name, anonymized_attr_value = _anonymize_host_and_folder_attribute(
            anon_interface, attr_name, attr_value, builtin_tag_group_ids
        )
        anon_attributes[anonymized_attr_name] = anonymized_attr_value

    return anon_attributes


def _anonymize_host_attributes(
    anon_interface: AnonInterface,
    builtin_tag_group_ids: list[TagGroupID],
    data: HostsStorageData,
) -> dict[HostName, object]:
    anon_host_attributes: dict[HostName, object] = {}
    for host, attributes in list(data.host_attributes.items()):
        anon_host_attributes[HostName(anon_interface.get_host(host))] = (
            _anonymize_single_host_and_folder_attributes(
                anon_interface, builtin_tag_group_ids, attributes
            )
        )
    return anon_host_attributes


def _anonymize_metrics_association(
    anon_interface: AnonInterface,
    value: dict[str, Any],
) -> object:
    return {
        "host_name_resource_attribute_key": anon_interface.get_generic_mapping(
            value["host_name_resource_attribute_key"],
            "metrics_association",
        ),
        "attribute_filters": {
            "resource_attributes": [
                _anonymize_metrics_association_attribute_filter(anon_interface, attribute_filter)
                for attribute_filter in value["attribute_filters"]["resource_attributes"]
            ],
            "scope_attributes": [
                _anonymize_metrics_association_attribute_filter(anon_interface, attribute_filter)
                for attribute_filter in value["attribute_filters"]["scope_attributes"]
            ],
            "data_point_attributes": [
                _anonymize_metrics_association_attribute_filter(anon_interface, attribute_filter)
                for attribute_filter in value["attribute_filters"]["data_point_attributes"]
            ],
        },
    }


def _anonymize_metrics_association_attribute_filter(
    anon_interface: AnonInterface,
    value: dict[str, Any],
) -> object:
    return {
        "attribute_value": anon_interface.get_generic_mapping(
            value["attribute_value"],
            "metric_association_attr_value",
        ),
        "attribute_key": anon_interface.get_generic_mapping(
            value["attribute_key"],
            "metric_association_attr_key",
        ),
    }


def _anonymize_explicit_host_conf(
    anon_interface: AnonInterface, data: HostsStorageData
) -> dict[str, Any]:
    builtin_attrs_explicit = [
        attr_name for attr_name, attr in host_attribute_registry.items() if attr().is_explicit()
    ]

    unhandled_explicit_attrs = set(builtin_attrs_explicit) - set(KNOWN_EXPLICIT_BUILTIN_ATTRS)
    assert len(unhandled_explicit_attrs) == 0, (
        f"Please handle unhandled explicit host attributes {unhandled_explicit_attrs} "
    )

    anon_explicit_host_conf: dict[str, Any] = {}
    for attr_name, attr_conf in data.explicit_host_conf.items():
        match attr_name:
            case "cmk_agent_connection":
                anon_explicit_host_conf["cmk_agent_connection"] = {
                    anon_interface.get_host(host): value for host, value in attr_conf.items()
                }
            case "alias":
                anon_explicit_host_conf["alias"] = {
                    anon_interface.get_host(host): anon_interface.get_host_alias(value)
                    for host, value in attr_conf.items()
                }
            case "parents":
                anon_explicit_host_conf["parents"] = {
                    anon_interface.get_host(host): anon_interface.get_host(value)
                    for host, value in attr_conf.items()
                }
            case "metrics_association":
                anon_explicit_host_conf["metrics_association"] = {}
                for host, metrics_association_serialized in attr_conf.items():
                    host_metrics_association = json.loads(metrics_association_serialized)
                    anon_explicit_host_conf["metrics_association"][
                        anon_interface.get_host(host)
                    ] = json.dumps(
                        _anonymize_metrics_association(anon_interface, host_metrics_association)
                    )

            case str() if attr_name.startswith("_"):
                # custom host attributes
                anon_explicit_host_conf[
                    f"_{anon_interface.get_custom_host_attr_name(attr_name[1:])}"
                ] = {
                    anon_interface.get_host(host): anon_interface.get_custom_host_attr_value(value)
                    for host, value in attr_conf.items()
                }
            case _:
                raise NotImplementedError(f"Unhandled explicit host attribute '{attr_name}'")
    return anon_explicit_host_conf


def _anonymize(anon_interface: AnonInterface, data: HostsStorageData) -> HostsStorageData:
    anon_locked_hosts = data.locked_hosts
    anon_all_hosts = [HostAddress(anon_interface.get_host(host)) for host in data.all_hosts]
    anon_clusters: dict[HostAddress, Sequence[HostAddress]] = {
        HostAddress(anon_interface.get_host(cluster_host)): [
            HostAddress(anon_interface.get_host(h)) for h in nodes
        ]
        for cluster_host, nodes in data.clusters.items()
    }
    anon_attributes = _anonymize_attributes(anon_interface, data.attributes)

    anon_custom_macros = {}
    for macro_name, macro_entries in data.custom_macros.items():
        assert macro_name not in KNOWN_EXPLICIT_BUILTIN_ATTRS, (
            f"Builtin attr '{macro_name}' was made implicit and needs to be handled as a custom macro"
        )
        anon_custom_macros[anon_interface.get_custom_host_attr_name(macro_name)] = [
            (
                anon_interface.get_custom_host_attr_value(value),
                [anon_interface.get_host(h) for h in hosts],
            )
            for value, hosts in macro_entries
        ]

    anon_host_tags: dict[HostName, dict[TagGroupID, TagID]] = {}
    builtin_tag_group_ids = [tag_group.id for tag_group in BuiltinTagConfig().get_tag_groups()]
    for host, host_tags in data.host_tags.items():
        anon_host = anon_interface.get_host(host)
        anon_host_tags[HostName(anon_host)] = {}

        for tag_key, tag_value in host_tags.items():
            if tag_key in builtin_tag_group_ids:
                anon_host_tags[HostName(anon_host)][tag_key] = (
                    tag_value  # keep builtin tags unchanged
                )
                continue
            if tag_key == "site":
                anon_host_tags[HostName(anon_host)][TagGroupID(tag_key)] = TagID(
                    anon_interface.get_site(tag_value)
                )
                continue
            anon_key, anon_value = anon_interface.get_tags(tag_key, tag_value)
            anon_host_tags[HostName(anon_host)].update({TagGroupID(anon_key): TagID(anon_value)})

    anon_host_labels: dict[HostAddress, dict[str, str]] = {}
    for host, host_label in data.host_labels.items():
        anon_host = anon_interface.get_host(host)
        anon_host_labels[HostAddress(anon_host)] = {}
        for label_key, label_value in host_label.items():
            anon_key, anon_value = anon_interface.get_host_label_groups(label_key, label_value)
            anon_host_labels[HostAddress(anon_host)].update({anon_key: anon_value})

    anon_contact_groups = _anonymize_contact_groups(anon_interface, data)
    anon_explicit_host_conf = _anonymize_explicit_host_conf(anon_interface, data)

    anon_host_attributes = _anonymize_host_attributes(anon_interface, builtin_tag_group_ids, data)

    anon_folder_attributes: dict[str, FolderAttributesForBase] = {}
    for folder_path, folder_attrs in data.folder_attributes.items():
        assert isinstance(folder_attrs, dict)
        assert list(folder_attrs.keys()) == ["bake_agent_package"]

        anon_folder_attributes[anon_interface.get_folder_path(folder_path)] = {
            "bake_agent_package": folder_attrs["bake_agent_package"]
        }

    return HostsStorageData(
        locked_hosts=anon_locked_hosts,
        all_hosts=anon_all_hosts,
        clusters=anon_clusters,
        attributes=anon_attributes,
        custom_macros=anon_custom_macros,
        # Make typing happy: converts MutableMapping to Mapping..
        host_tags=dict(anon_host_tags.items()),
        host_labels=dict(anon_host_labels.items()),
        contact_groups=anon_contact_groups,
        explicit_host_conf=anon_explicit_host_conf,
        host_attributes=anon_host_attributes,
        folder_attributes=anon_folder_attributes,
    )


def _anonymize_folder_attributes(
    anon_interface: AnonInterface, data: WATOFolderInfo
) -> WATOFolderInfo:
    anon_data = WATOFolderInfo()
    if "__id" in data:
        anon_data["__id"] = data["__id"]
    if "title" in data:
        anon_data["title"] = anon_interface.get_generic_mapping(data["title"], "folder_title")
    if "attributes" in data:
        builtin_tag_group_ids = [tag_group.id for tag_group in BuiltinTagConfig().get_tag_groups()]
        anon_data["attributes"] = cast(
            HostAttributes,
            _anonymize_single_host_and_folder_attributes(
                anon_interface, builtin_tag_group_ids, cast(dict[str, object], data["attributes"])
            ),
        )
    if "num_hosts" in data:
        anon_data["num_hosts"] = data["num_hosts"]
    if "lock" in data:
        anon_data["lock"] = data["lock"]
    if "lock_subfolders" in data:
        anon_data["lock_subfolders"] = data["lock_subfolders"]
    return anon_data


class AnonHostsStorage(StandardHostsStorage):
    def __init__(self, anon_interface: AnonInterface) -> None:
        super().__init__()
        self.anon_interface = anon_interface

    def _write(
        self,
        hosts_mk_file_path: Path,
        data: HostsStorageData,
        value_formatter: Callable[[Any], str],
    ) -> None:
        folders_path = (
            str(hosts_mk_file_path).removeprefix(str(wato_root_dir())).removesuffix("hosts.mk")
        )
        anon_folders_path = self.anon_interface.get_folder_path(folders_path)
        anon_hosts_mk_file_path = self.anon_interface.relative_to_anon_dir(
            Path(f"{wato_root_dir()}/{anon_folders_path}/hosts.mk")
        )

        super()._write(
            anon_hosts_mk_file_path, _anonymize(self.anon_interface, data), value_formatter
        )

    def _read(self, file_path: Path) -> str:
        raise NotImplementedError()


class AnonFolderAttributesStorage(StandardWATOInfoStorage):
    def __init__(self, anon_interface: AnonInterface) -> None:
        super().__init__()
        self.anon_interface = anon_interface

    def write(self, file_path: Path, data: WATOFolderInfo) -> None:
        folders_path = str(file_path).removeprefix(str(wato_root_dir())).removesuffix(".wato")
        anon_folders_path = self.anon_interface.get_folder_path(folders_path)
        anon_wato_file_path = self.anon_interface.relative_to_anon_dir(
            Path(f"{wato_root_dir()}/{anon_folders_path}/.wato")
        )
        super().write(anon_wato_file_path, _anonymize_folder_attributes(self.anon_interface, data))

    def read(self, file_path: Path) -> WATOFolderInfo:
        raise NotImplementedError()


class HostsSteps(AnonymizeStep):
    def run(
        self, anon_interface: AnonInterface, active_config: Config, logger: logging.Logger
    ) -> None:
        logger.warning("Process hosts")

        for folder_rel_path, folder in folder_tree().all_folders().items():
            folder._save_hosts_file(
                storage_list=[AnonHostsStorage(anon_interface)], pprint_value=False
            )
            folder._save_folder_attributes(
                storage_list=[AnonFolderAttributesStorage(anon_interface)]
            )


anonymize_step_hosts = HostsSteps()
