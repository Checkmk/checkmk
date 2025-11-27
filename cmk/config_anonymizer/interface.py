#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import logging
from logging import Logger
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from cmk.ccc.site import omd_site
from cmk.utils.paths import omd_root, var_dir


class ANONTYPE(enum.Enum):
    TAG_ID = "tag_id"
    AUX_TAG_ID = "aux_tag_id"
    SITE = "site"
    SITE_ALIAS = "site_alias"
    HOST = "host"
    HOST_ALIAS = "host_alias"
    SERVICE_DESCRIPTION = "service_description"
    SERVICE_LABEL_KEY = "service_label_key"
    SERVICE_LABEL_VALUE = "service_label_value"
    TAG_GROUP = "tag_group"
    TAG_VALUE = "tag_value"
    LABEL_KEY = "label_key"
    LABEL_VALUE = "label_value"
    USER = "user"
    ITEM = "item"
    IPv4_ADDRESS = "ipv4_address"
    IPv6_ADDRESS = "ipv6_address"
    CONTACT_GROUP = "contact_group"
    FOLDER_NAME = "folder"
    CUSTOM_HOST_ATTR_NAME = "custom_host_attr_name"
    CUSTOM_HOST_ATTR_VALUE = "custom_host_attr_value"
    CUSTOMER = "customer"
    URL = "url"
    PASSWORD = "password"
    PASSWORD_ID = "password_id"
    LDAP_CONNECTION = "ldap_connection"
    UNIX_SOCKET = "unix_socket"
    TAG_TOPIC = "tag_topic"


CustomAnon = str


class AnonInterface:
    def __init__(self, target_dirname: Path, logger: logging.Logger):
        self._site_id = omd_site()
        self._target_dir = var_dir / "anonymized" / target_dirname
        self._logger = logger

    _anon_mapping: dict[str, dict[str, str]] = {}

    @property
    def target_dir(self) -> Path:
        return self._target_dir

    @property
    def logger(self) -> Logger:
        return self._logger

    def relative_to_anon_dir(self, path: Path) -> Path:
        if not str(path).startswith(str(omd_root)):
            raise ValueError(f"Path {path} is not in OMD root {omd_root}")
        relative_path = path.relative_to(f"/omd/sites/{self._site_id}/")
        return self._target_dir / relative_path

    def _get_entry(self, original: str, anon_type: ANONTYPE | CustomAnon) -> str:
        mapping_key = anon_type.value if isinstance(anon_type, ANONTYPE) else anon_type

        self._anon_mapping.setdefault(mapping_key, {})
        try:
            return self._anon_mapping[mapping_key][original]
        except KeyError:
            self._anon_mapping[mapping_key][original] = (
                f"{mapping_key}{len(self._anon_mapping[mapping_key]) + 1}"
            )
            return self._anon_mapping[mapping_key][original]

    def get_site(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.SITE)

    def get_host(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.HOST)

    def get_ipv4_address(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.IPv4_ADDRESS)

    def get_ipv6_address(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.IPv6_ADDRESS)

    def get_host_alias(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.HOST_ALIAS)

    def get_service_description(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.SERVICE_DESCRIPTION)

    def get_service_label_groups(self, key: str, value: str) -> tuple[str, str]:
        return self._get_entry(key, ANONTYPE.SERVICE_LABEL_KEY), self._get_entry(
            value, ANONTYPE.SERVICE_LABEL_VALUE
        )

    def get_tags(self, key: str, value: str) -> tuple[str, str]:
        return self.get_id_of_tag_group(key), self.get_tag_value(value)

    def get_labels(self, key: str, value: str) -> tuple[str, str]:
        return self.get_label_key(key), self.get_label_value(value)

    def get_user(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.USER)

    def get_item(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.ITEM)

    def get_generic_mapping(self, original: str, namespace: CustomAnon) -> str:
        if namespace in ANONTYPE:
            raise ValueError(
                f"Custom namespace must not be one of the predefined namespaces: {[entry.value for entry in ANONTYPE]}"
            )

        return self._get_entry(original, namespace)

    def get_id_of_tag_group(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.TAG_GROUP)

    def get_tag_value(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.TAG_VALUE)

    def get_label_key(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.LABEL_KEY)

    def get_label_value(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.LABEL_VALUE)

    def get_contact_group(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.CONTACT_GROUP)

    def get_folder_path(self, original: str) -> str:
        assert original.startswith("/") and original.endswith("/"), (
            f"Folder '{original}' must start and end with '/'"
        )
        original_cleaned = original.strip("/")
        original_parts = original_cleaned.split("/")

        if original_parts[0] == "wato":
            original_parts = original_parts[1:]
            anon_folder_parts = [
                self._get_entry(folder_part, ANONTYPE.FOLDER_NAME) for folder_part in original_parts
            ]
            anon_folder_parts.insert(0, "wato")
        else:
            anon_folder_parts = [
                self._get_entry(folder_part, ANONTYPE.FOLDER_NAME) for folder_part in original_parts
            ]
        return f"/{'/'.join(anon_folder_parts)}/"

    def get_custom_host_attr_name(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.CUSTOM_HOST_ATTR_NAME)

    def get_custom_host_attr_value(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.CUSTOM_HOST_ATTR_VALUE)

    def get_site_alias(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.SITE_ALIAS)

    def get_customer(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.CUSTOMER)

    def get_url(self, original: str) -> str:
        parsed_url = urlparse(original)
        if not parsed_url.scheme:
            return f"{self._get_entry(parsed_url.netloc, ANONTYPE.URL)}.com"
        return f"{parsed_url.scheme}://{self._get_entry(parsed_url.netloc, ANONTYPE.URL)}.com"

    def get_cmk_postprocessed_password(
        self,
        original: tuple[
            Literal["cmk_postprocessed"],
            Literal["explicit_password", "stored_password"],
            tuple[str, str],
        ],
    ) -> tuple[
        Literal["cmk_postprocessed"],
        Literal["explicit_password", "stored_password"],
        tuple[str, str],
    ]:
        match original:
            case ("cmk_postprocessed", "explicit_password", (password_id, password_value)):
                return (
                    "cmk_postprocessed",
                    "explicit_password",
                    (
                        self._get_entry(password_id, ANONTYPE.PASSWORD_ID),
                        self._get_entry(password_value, ANONTYPE.PASSWORD),
                    ),
                )
            case ("cmk_postprocessed", "stored_password", (password_id, "")):
                return (
                    "cmk_postprocessed",
                    "explicit_password",
                    (self._get_entry(password_id, ANONTYPE.PASSWORD_ID), ""),
                )
            case _:
                raise ValueError(f"Invalid password format: {original}")

    def get_secret(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.PASSWORD)

    def get_ldap_connection(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.LDAP_CONNECTION)

    def get_unix_socket(self, original: str) -> str:
        return "/anon_socket_path/run/" + self._get_entry(original, ANONTYPE.UNIX_SOCKET)

    def get_id_of_aux_tag(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.AUX_TAG_ID)

    def get_tag_topic(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.TAG_TOPIC)

    def get_id_of_tag(self, original: str) -> str:
        return self._get_entry(original, ANONTYPE.TAG_ID)
