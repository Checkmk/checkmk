#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Preparing the site configuration in distributed setups for synchronization"""

import abc
import enum
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, override, Self
from urllib.parse import quote

from livestatus import (
    AuthenticationConnectionEntry,
    SAMLAuthenticationEntry,
    SiteConfiguration,
    SiteGlobals,
)

import cmk.ccc.version as cmk_version
import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.site import omd_site, SiteId
from cmk.gui.config import active_config
from cmk.gui.log import logger
from cmk.gui.userdb import get_active_saml_connections, user_sync_default_config
from cmk.gui.watolib.config_domain_name import wato_fileheader
from cmk.messaging import rabbitmq

Command = list[str]


class ReplicationPathType(enum.Enum):
    FILE = "file"
    DIR = "dir"


@dataclass(frozen=True, kw_only=True)
class ReplicationPath:
    _PATTERNS_INTERMEDIATE_STORE_FILES = frozenset([re.compile(r"^\..*\.new.*")])

    ty: ReplicationPathType
    ident: str
    site_path: str
    excludes_exact_match: frozenset[str]
    excludes_regex_match: frozenset[re.Pattern[str]]

    @classmethod
    def make(
        cls,
        *,
        ty: ReplicationPathType,
        ident: str,
        site_path: str,
        excludes_exact_match: Iterable[str] = (),
        excludes_regex_match: Iterable[str] = (),
    ) -> Self:
        if site_path.startswith("/"):
            raise Exception("ReplicationPath.site_path must be a path relative to the site root")
        cleaned_path = site_path.rstrip("/")

        return cls(
            ty=ty,
            ident=ident,
            site_path=cleaned_path,
            excludes_exact_match=frozenset(excludes_exact_match),
            excludes_regex_match=frozenset(re.compile(pattern) for pattern in excludes_regex_match)
            | cls._PATTERNS_INTERMEDIATE_STORE_FILES,
        )

    def is_excluded(self, entry: str) -> bool:
        return entry in self.excludes_exact_match or any(
            pattern.match(entry) for pattern in self.excludes_regex_match
        )

    def serialize(self) -> tuple[str, str, str, list[str], list[str]]:
        return (
            self.ty.value,
            self.ident,
            self.site_path,
            list(self.excludes_exact_match),
            [pattern.pattern for pattern in self.excludes_regex_match],
        )

    @classmethod
    def deserialize(cls, serialized: object) -> Self:
        if not isinstance(serialized, tuple):
            raise TypeError(serialized)
        match serialized:
            # Legacy format, drop in 2.6.
            # We need this in 2.5 to stay compatible with 2.4 central sites. A 2.5 remote site must
            # support both formats.
            case (
                str(raw_ty),
                str(ident),
                str(site_path),
                excludes_exact_match,
            ):
                return cls.make(
                    ty=ReplicationPathType(raw_ty),
                    ident=ident,
                    site_path=site_path,
                    excludes_exact_match=excludes_exact_match,
                )
            case (
                str(raw_ty),
                str(ident),
                str(site_path),
                excludes_exact_match,
                excludes_regex_match,
            ):
                return cls.make(
                    ty=ReplicationPathType(raw_ty),
                    ident=ident,
                    site_path=site_path,
                    excludes_exact_match=excludes_exact_match,
                    excludes_regex_match=excludes_regex_match,
                )
            case _:
                raise TypeError(serialized)


class ReplicationPathRegistry(Registry[ReplicationPath]):
    @override
    def plugin_name(self, instance: ReplicationPath) -> str:
        return instance.ident


replication_path_registry = ReplicationPathRegistry()


class SnapshotSettings(NamedTuple):
    # TODO: Refactor to Path
    snapshot_path: str
    # TODO: Refactor to Path
    work_dir: str
    # TODO: Clarify naming (-> replication path or snapshot component?)
    snapshot_components: list[ReplicationPath]
    component_names: set[str]
    site_config: SiteConfiguration
    rabbitmq_definition: rabbitmq.Definitions


class ABCSnapshotDataCollector(abc.ABC):
    """Prepares files to be synchronized to the remote sites"""

    def __init__(self, site_snapshot_settings: dict[SiteId, SnapshotSettings]) -> None:
        super().__init__()
        self._site_snapshot_settings = site_snapshot_settings
        self._logger = logger.getChild(self.__class__.__name__)

    @abc.abstractmethod
    def prepare_snapshot_files(self) -> None:
        """Site independent preparation of files to be used for the sync snapshots
        This will be called once before iterating over all sites.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_generic_components(self) -> list[ReplicationPath]:
        """Return the site independent snapshot components
        These will be collected by the SnapshotManager once when entering the context manager
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_site_components(
        self, snapshot_settings: SnapshotSettings
    ) -> tuple[list[ReplicationPath], list[ReplicationPath]]:
        """Split the snapshot components into generic and site specific components

        The generic components have the advantage that they only need to be created once for all
        sites and can be shared between the sites to optimize processing."""
        raise NotImplementedError()


def is_user_file(filepath: str) -> bool:
    entry = os.path.basename(filepath)
    return entry.startswith("user_") or entry in ["tableoptions.mk", "treestates.mk", "sidebar.mk"]


def resolve_central_site_inheritance(site_config: SiteConfiguration) -> SiteConfiguration:
    """Resolve absent `authentication_connections` to the central site's value.

    Called on the central site when building a remote site's
    ``sitespecific.mk``: when the remote's per-site key is absent the
    inherited value comes from the central's own
    `authentication_connections`, so the remote sees the concrete list at
    runtime and `populate_saml_site_endpoint_urls()` sees SAML entries
    directly. The central's own missing key collapses to an empty list.
    """
    if "authentication_connections" in site_config:
        return site_config
    central_id = omd_site()
    central_config = active_config.sites.get(central_id)
    inherited: list[AuthenticationConnectionEntry] = (
        list(central_config.get("authentication_connections", []))
        if central_config is not None
        else []
    )
    return {**site_config, "authentication_connections": inherited}


def populate_saml_site_endpoint_urls(site_config: SiteConfiguration) -> SiteConfiguration:
    """Inject SAML SP endpoint URLs into the resolved authentication connections.

    Returns a copy of `site_config` where each SAML entry under
    `authentication_connections` carries `metadata_endpoint` and `acs_endpoint`
    populated from the site's `multisiteurl` and the connection ID. Used by
    `get_site_globals()` so the propagated `sitespecific.mk` carries the
    resolved URLs instead of the placeholder ``-``.

    `multisiteurl` is only set on remote sites — it's the URL the central uses
    to reach them. On the central / single-site setups it's empty; in that
    case the SAML connection's own `checkmk_assertion_consumer_service_endpoint`
    serves as the displayed ACS URL (matching the runtime fallback in
    `_pages._site_interface_config`).

    Entries that don't have enough information yet (e.g. a brand-new entry
    without a connection ID, or a site without a callback URL configured)
    show ``-`` instead.

    Sites that inherit (no per-site key) are returned unchanged; callers
    that want the resolved list should run `resolve_central_site_inheritance`
    first.
    """
    auth_conns = site_config.get("authentication_connections")
    if auth_conns is None:
        return site_config

    callback_url = site_config.get("multisiteurl", "")
    populated = _populate_endpoint_urls(auth_conns, callback_url)
    return {**site_config, "authentication_connections": populated}


def _populate_endpoint_urls(
    entries: list[AuthenticationConnectionEntry], callback_url: str
) -> list[AuthenticationConnectionEntry]:
    populated: list[AuthenticationConnectionEntry] = []
    for entry in entries:
        if entry[0] != "saml":
            populated.append(entry)
            continue
        _kind, saml_entry = entry
        connection_id = saml_entry.get("connection_id", "")
        metadata, acs = _saml_endpoint_urls(callback_url, connection_id)
        new_entry: SAMLAuthenticationEntry = {
            "connection_id": connection_id,
            "metadata_endpoint": metadata,
            "acs_endpoint": acs,
        }
        populated.append(("saml", new_entry))
    return populated


def _saml_endpoint_urls(callback_url: str, connection_id: str) -> tuple[str, str]:
    """Compute the per-site SAML metadata + ACS URLs for a connection.

    On a remote site `callback_url` is the site's `multisiteurl` and the URLs
    are derived from it. On the central / single-site setups `callback_url`
    is empty; we then fall back to the connection's own
    `checkmk_assertion_consumer_service_endpoint` so the editor displays the
    actual URL pysaml2 will use at runtime (mirroring
    `_pages._site_interface_config`).
    """
    if callback_url and connection_id:
        # URL-encode ``connection_id`` for defense-in-depth: ``validate_connection_id``
        # currently only enforces uniqueness, so a future relaxation of the
        # upstream ``ID()`` valuespec could otherwise let characters like ``&``
        # or ``=`` smuggle extra query parameters into the IdP request.
        return (
            f"{callback_url}saml_metadata.py?RelayState={quote(connection_id, safe='')}",
            f"{callback_url}saml_acs.py?acs",
        )

    if not connection_id:
        return "-", "-"

    connection = get_active_saml_connections().get(connection_id)
    if connection is None:
        return "-", "-"

    acs_endpoint = connection["checkmk_assertion_consumer_service_endpoint"]
    if not acs_endpoint:
        return "-", "-"
    # `checkmk_metadata_endpoint` is already stored as
    # `<server>/saml_metadata.py?RelayState=<connection_id>` (see
    # `checkmk_service_provider_metadata` in `_config.py`), so it must not be
    # appended to again.
    return connection["checkmk_metadata_endpoint"], acs_endpoint


def central_site_inherited_summary(callback_url: str) -> str:
    """Render a human-readable summary of the central site's authentication connections.

    Used by the site-edit form to show what the remote site would inherit
    when the admin picks "Use the same connections as the central site".
    The form widget is read-only display; the summary is recomputed each
    time the dialog renders.

    Returned format:
        LDAP: <connection_id>
        SAML: <connection_id>
            Metadata endpoint URL: <url>
            Assertion Consumer Service URL: <url>

    For an unset / empty central, returns a placeholder.
    """
    central_id = omd_site()
    central_config = active_config.sites.get(central_id)
    central_auth = (
        central_config.get("authentication_connections") if central_config is not None else None
    )

    if not central_auth:
        return "-"

    lines: list[str] = []
    for entry in central_auth:
        if entry[0] == "ldap":
            lines.append(f"LDAP: {entry[1]}")
            continue
        connection_id = entry[1].get("connection_id", "")
        metadata, acs = _saml_endpoint_urls(callback_url, connection_id)
        lines.append(f"SAML: {connection_id or '-'}")
        lines.append(f"    Metadata endpoint URL: {metadata}")
        lines.append(f"    Assertion Consumer Service URL: {acs}")
    return "\n".join(lines) if lines else "-"


def get_site_globals(site_id: SiteId, site_config: SiteConfiguration) -> SiteGlobals:
    site_globals = site_config.get("globals", {}).copy()
    # Resolve "inherit from central" first so downstream steps (SAML endpoint
    # population) see the concrete connection list.
    site_config = resolve_central_site_inheritance(site_config)
    # Resolve the SAML SP endpoint URLs so the propagated authentication_connections
    # value carries the actual `metadata_endpoint` / `acs_endpoint` URLs rather than
    # the `"-"` placeholder that the site editor stores in `sites.mk`.
    populated_site_config = populate_saml_site_endpoint_urls(site_config)
    site_globals.update(
        {
            "wato_enabled": not site_config.get("disable_wato", True),
            "userdb_automatic_sync": user_sync_default_config(site_config, site_id),
            "user_login": site_config.get("user_login", False),
            # Propagate the per-site connector settings. `sites.mk` is not synced
            # to remotes, so these are passed through the global settings
            # mechanism. The propagated `authentication_connections` carries
            # per-entry SAML `acs_endpoint`/`metadata_endpoint` URLs computed
            # for this site by `populate_saml_site_endpoint_urls()`, so the
            # remote's SAML runtime reads them straight from there. SAML cert
            # files arrive on the remote via the `saml2_certs` `ReplicationPath`
            # (see `cmk/gui/nonfree/pro/saml2_auth/registration.py`).
            "authentication_connections": populated_site_config.get(
                "authentication_connections", []
            ),
        }
    )
    # Propagate `user_attribute_sync_connections` when set per-site; otherwise
    # fall back to the central's own value so the remote inherits it. If
    # neither is set the global keeps its default ("all").
    attr_sync = site_config.get("user_attribute_sync_connections")
    if attr_sync is None:
        central_config = active_config.sites.get(omd_site())
        if central_config is not None:
            attr_sync = central_config.get("user_attribute_sync_connections")
    if attr_sync is not None:
        site_globals["user_attribute_sync_connections"] = attr_sync
    return site_globals


def create_distributed_wato_files(base_dir: Path, site_id: SiteId, is_remote: bool) -> None:
    _create_distributed_wato_file_for_base(
        base_dir.joinpath("etc/check_mk/conf.d/distributed_wato.mk"), site_id, is_remote
    )
    _create_distributed_wato_file_for_dcd(
        base_dir.joinpath("etc/check_mk/dcd.d/wato/distributed.mk"), is_remote
    )
    _create_distributed_wato_file_for_omd(base_dir / "etc/omd/distributed.mk", is_remote)


def _create_distributed_wato_file_for_base(
    output_file_path: Path, site_id: SiteId, is_remote: bool
) -> None:
    output = wato_fileheader()
    output += (
        "# This file has been created by the master site\n"
        "# push the configuration to us. It makes sure that\n"
        "# we only monitor hosts that are assigned to our site.\n\n"
    )
    output += "distributed_wato_site = '%s'\n" % site_id
    output += "is_distributed_setup_remote_site = %r\n" % is_remote

    store.save_text_to_file(output_file_path, output)


def _create_distributed_wato_file_for_dcd(output_file_path: Path, is_remote: bool) -> None:
    if cmk_version.edition(cmk.utils.paths.omd_root) is cmk_version.Edition.COMMUNITY:
        return

    output = wato_fileheader()
    output += "dcd_is_wato_remote_site = %r\n" % is_remote

    store.save_text_to_file(output_file_path, output)


def _create_distributed_wato_file_for_omd(output_file_path: Path, is_remote: bool) -> None:
    output = wato_fileheader()
    output += f"is_wato_remote_site = {is_remote}\n"
    store.save_text_to_file(output_file_path, output)


def create_rabbitmq_new_definitions_file(base_dir: Path, definition: rabbitmq.Definitions) -> None:
    store.save_text_to_file(base_dir / rabbitmq.NEW_DEFINITIONS_FILE_PATH, definition.dumps())
