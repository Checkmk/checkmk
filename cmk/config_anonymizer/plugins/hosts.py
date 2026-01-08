#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.config_anonymizer.interface import AnonInterface
from cmk.config_anonymizer.step import AnonymizeStep
from cmk.gui.config import Config
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.watolib.attributes import create_ipmi_parameters, SNMPCredentials
from cmk.gui.watolib.host_attributes import host_attribute_registry
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.utils.host_storage import (
    ContactGroupsField,
    FolderAttributesForBase,
    HostsStorageData,
    StandardHostsStorage,
)
from cmk.utils.tags import BuiltinTagConfig, TagGroupID, TagID

KNOWN_EXPLICIT_BUILTIN_ATTRS = ["cmk_agent_connection", "alias", "parents", "metrics_association"]


def _anonymize_attributes(anon_interface: AnonInterface, data: dict[str, Any]) -> dict[str, Any]:
    anon_data: dict[str, Any] = {}

    if (ipaddresses := data.get("ipaddresses")) is not None:
        anon_data["ipaddresses"] = {
            anon_interface.get_host(host): anon_interface.get_ipv4_address(ip)
            for host, ip in ipaddresses.items()
        }

    if (ipv6addresses := data.get("ipv6addresses")) is not None:
        anon_data["ipv6addresses"] = {
            anon_interface.get_host(host): anon_interface.get_ipv6_address(ip)
            for host, ip in ipv6addresses.items()
        }

    if (snmp_community := data.get("explicit_snmp_communities")) is not None:
        # TODO: masking only works on passwords, rest of credentials remain un-anonymized
        snmp_spec = SNMPCredentials()
        anon_data["explicit_snmp_communities"] = {
            anon_interface.get_host(host): snmp_spec.mask(value)
            for host, value in snmp_community.items()
        }

    if (management_snmp_credentials := data.get("management_snmp_credentials")) is not None:
        snmp_spec = SNMPCredentials()
        # TODO: masking only works on passwords, rest of credentials remain un-anonymized
        anon_data["management_snmp_credentials"] = {
            anon_interface.get_host(host): snmp_spec.mask(value)
            for host, value in management_snmp_credentials.items()
        }

    if (management_ipmi_credentials := data.get("management_ipmi_credentials")) is not None:
        # TODO masking only works on passwords, rest of credentials remain un-anonymized
        ipmi_spec_visitor = get_visitor(
            create_ipmi_parameters(), VisitorOptions(migrate_values=False, mask_values=True)
        )

        anon_data["management_ipmi_credentials"] = {
            anon_interface.get_host(host): ipmi_spec_visitor.to_disk(RawDiskData(value))
            for host, value in management_ipmi_credentials.items()
        }

    if (management_protocol := data.get("management_protocol")) is not None:
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


def _anonymize_host_attributes(
    anon_interface: AnonInterface,
    builtin_tag_group_ids: list[TagGroupID],
    data: HostsStorageData,
) -> dict[HostName, Any]:
    anon_host_attributes: dict[HostAddress, dict[str, Any]] = {}
    for host, attributes in list(data.host_attributes.items()):
        anon_attributes: dict[str, Any] = {}

        for attr_name, attr_value in attributes.items():
            match attr_name:
                case "alias":
                    anon_attributes["alias"] = anon_interface.get_host_alias(attr_value)
                case "ipaddress":
                    anon_attributes["ipaddress"] = anon_interface.get_ipv4_address(attr_value)
                case "additional_ipv4addresses":
                    anon_attributes["additional_ipv4addresses"] = [
                        anon_interface.get_ipv4_address(ip) for ip in attr_value
                    ]
                case "ipv6address":
                    anon_attributes["ipv6address"] = anon_interface.get_ipv6_address(attr_value)
                case "additional_ipv6addresses":
                    anon_attributes["additional_ipv6addresses"] = [
                        anon_interface.get_ipv6_address(ip) for ip in attr_value
                    ]
                case "parents":
                    anon_attributes["parents"] = [anon_interface.get_host(h) for h in attr_value]
                case "snmp_community":
                    snmp_spec = SNMPCredentials()
                    anon_attributes["snmp_community"] = snmp_spec.mask(attr_value)
                case "management_address":
                    anon_attributes["management_address"] = anon_interface.get_ipv4_address(
                        attr_value
                    )
                case "management_protocol":
                    anon_attributes["management_protocol"] = attr_value
                case "management_snmp_community":
                    # TODO: masking only works on passwords, rest of credentials remain un-anonymized
                    snmp_spec = SNMPCredentials()
                    anon_attributes["management_snmp_community"] = snmp_spec.mask(attr_value)
                case "management_ipmi_credentials":
                    # TODO: masking only works on passwords, rest of credentials remain un-anonymized
                    ipmi_spec_visitor = get_visitor(
                        create_ipmi_parameters(),
                        VisitorOptions(migrate_values=False, mask_values=True),
                    )
                    anon_attributes["management_ipmi_credentials"] = ipmi_spec_visitor.to_disk(
                        RawDiskData(attr_value)
                    )

                case "site":
                    anon_attributes["site"] = anon_interface.get_site(attr_value)
                case "labels":
                    anon_attributes["labels"] = {
                        k_an: v_an
                        for k, v in attr_value.items()
                        for k_an, v_an in [anon_interface.get_labels(k, v)]
                    }
                case "contactgroups":
                    anon_attributes["contactgroups"] = attr_value.copy()
                    anon_attributes["contactgroups"]["groups"] = {
                        "groups": [
                            anon_interface.get_contact_group(g) for g in attr_value["groups"]
                        ]
                    }
                case "metrics_association":
                    attr_mode, attr_metric_assoc = attr_value
                    if attr_mode == "disabled":
                        anon_attributes["metrics_association"] = attr_value.copy()
                    else:
                        anon_attributes["metrics_association"] = _anonymize_metrics_association(
                            anon_interface,
                            attr_metric_assoc,
                        )

                case "meta_data":
                    anon_attributes["meta_data"] = {
                        "created_at": attr_value.get("created_at"),
                        "created_by": anon_interface.get_user(attr_value.get("created_by", "")),
                        "updated_at": attr_value.get("updated_at"),
                    }
                case str() if attr_name.startswith("tag_"):
                    tag_key = attr_name[len("tag_") :]

                    if tag_key in builtin_tag_group_ids:
                        anon_attributes[attr_name] = anon_interface.get_tag_value(attr_value)
                    else:
                        anon_attributes[f"tag_{anon_interface.get_tag_group(tag_key)}"] = (
                            anon_interface.get_tag_value(attr_value)
                        )

                case _:
                    # custom host attributes
                    anon_attributes[anon_interface.get_custom_host_attr_name(attr_name)] = (
                        anon_interface.get_custom_host_attr_value(attr_value)
                    )

        anon_host_attributes[HostAddress(anon_interface.get_host(host))] = anon_attributes
    return anon_host_attributes


def _anonymize_metrics_association(
    anon_interface: AnonInterface,
    value: Any,
) -> Any:
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
    value: Any,
) -> Any:
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
) -> dict[Any, Any]:
    builtin_attrs_explicit = [
        attr_name for attr_name, attr in host_attribute_registry.items() if attr().is_explicit()
    ]

    unhandled_explicit_attrs = set(builtin_attrs_explicit) - set(KNOWN_EXPLICIT_BUILTIN_ATTRS)
    assert len(unhandled_explicit_attrs) == 0, (
        f"Please handle unhandled explicit host attributes {unhandled_explicit_attrs} "
    )

    anon_explicit_host_conf = {}
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
            anon_key, anon_value = anon_interface.get_labels(label_key, label_value)
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


class AnonStorage(StandardHostsStorage):
    def __init__(self, anon_interface: AnonInterface) -> None:
        super().__init__()
        self.anon_interface = anon_interface

    def _write(
        self,
        hosts_mk_file_path: Path,
        data: HostsStorageData,
        value_formatter: Callable[[Any], str],
    ) -> None:
        anon_hosts_mk_file_path = self.anon_interface.relative_to_anon_dir(hosts_mk_file_path)
        super()._write(
            anon_hosts_mk_file_path, _anonymize(self.anon_interface, data), value_formatter
        )

    def _read(self, file_path: Path) -> str:
        raise NotImplementedError()


class HostsSteps(AnonymizeStep):
    def run(
        self, anon_interface: AnonInterface, active_config: Config, logger: logging.Logger
    ) -> None:
        logger.warning("Process hosts")

        for folder_rel_path, folder in folder_tree().all_folders().items():
            folder._save_hosts_file(storage_list=[AnonStorage(anon_interface)], pprint_value=False)


anonymize_step_hosts = HostsSteps()
