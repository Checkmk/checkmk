#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Materialize the GUI-only host relations into the monitoring core.

Host relations (see :mod:`cmk.gui.watolib.host_relations`) are a Setup-only feature: the links
live in the ``relations`` host attribute.

To make the relations available for monitoring (Livestatus, views) they are resolved *once*,
centrally, at activation time and written as the ``_RELATIONS`` custom host variable via a
generated ``explicit_host_conf`` file. This runs on the central site before the configuration
snapshots are built, so the file is replicated to all sites. The central config knows every host
of every site, so cross-site links resolve correctly here; each site's core only emits the macro
for the hosts it actually monitors.

A host attribute normally reaches the core through :meth:`ABCHostAttribute.nagios_name` and lands
in its own folder's ``hosts.mk`` when that folder is saved. Relations cannot use that path: the
derived reverse links belong to hosts in *other* folders, and the counterpart's site can only be
looked up against the whole tree - neither is known while saving a single folder.

:func:`register` declares the generated file for config sync; the write itself is triggered from
the activation (see :func:`export_host_relations`).

The format the value is written in - and hence everything a reader needs to know about it - is
defined in :mod:`cmk.gui.utils.host_relations`, which the monitoring side reads it back with.
"""

from collections.abc import Mapping
from pathlib import Path

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.hostaddress import HostName
from cmk.gui.log import logger
from cmk.gui.utils.host_relations import dump_resolved_relations, RELATIONS_MACRO
from cmk.gui.watolib.config_sync import (
    ReplicationPath,
    ReplicationPathRegistry,
    ReplicationPathType,
)
from cmk.gui.watolib.host_relations import RelatedHost, resolve_all_relations

_LOGGER = logger.getChild("host_relations")


def relations_export_path() -> Path:
    """The generated ``explicit_host_conf`` file, in the directory that is synced to the sites."""
    return cmk.utils.paths.check_mk_config_dir / "relations.mk"


def _write_export_file(path: Path, macro_values: dict[str, str]) -> bool:
    """Write the export file unless it already says exactly this. Returns whether it was written.

    Skipping an unchanged file is not just about saving a write: a file in ``conf.d`` that is
    newer than the last core compilation switches the CMC back to a full recompilation of every
    host (only autochecks, discovered labels and the ``hosts.mk`` of the hosts being updated are
    allowed to be newer, see
    :meth:`cmk.base.nonfree.cmc._create_config.HelperConfig._files_allowed_to_be_newer`). Since
    this runs on every activation, rewriting the file unconditionally would cost every Checkmk
    site its incremental activation. Only relations that really changed may do that.
    """
    lines = [
        "# Created by Checkmk host relations export. Do not edit manually.\n",
        "explicit_host_conf.setdefault(%r, {})\n" % RELATIONS_MACRO,
    ]
    if macro_values:
        lines.append(f"explicit_host_conf[{RELATIONS_MACRO!r}].update({macro_values!r})\n")
    content = "".join(lines)

    if store.load_text_from_file(path) == content:
        return False
    store.save_text_to_file(path, content)
    return True


def export_host_relations(
    all_hosts: Mapping[HostName, RelatedHost], export_file_path: Path
) -> None:
    """Resolve the relations of ``all_hosts`` and persist them as the ``_RELATIONS`` variable.

    Called once per activation on the central site, immediately before the sync snapshots are
    built; the links come from the ``relations`` attribute of every host of the folder tree.
    Counterparts that do not exist are dropped by :func:`resolve_all_relations`.
    """
    resolved = resolve_all_relations(all_hosts)
    macro_values = {
        str(host): dump_resolved_relations(relations) for host, relations in resolved.items()
    }
    written = _write_export_file(export_file_path, macro_values)
    _LOGGER.debug(
        "Host relations export: %(hosts)d host(s) with relations, %(entries)d relation entries, "
        "%(outcome)s %(path)s.",
        {
            "hosts": len(macro_values),
            "entries": sum(len(relations) for relations in resolved.values()),
            "outcome": "written to" if written else "unchanged in",
            "path": export_file_path,
        },
    )


def register(replication_path_registry: ReplicationPathRegistry) -> None:
    replication_path_registry.register(
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="host_relations",
            site_path=str(relations_export_path().relative_to(cmk.utils.paths.omd_root)),
        )
    )
