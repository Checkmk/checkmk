#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Materialize the host relations into the monitoring core.

Host relations (see :mod:`cmk.gui.watolib.host_relations`) are configured in Setup: the links
live in the ``relations`` host attribute.

To make the relations available for monitoring (Livestatus, views) they are resolved *once*,
centrally, at activation time and written as the ``_CMK_RELATIONS`` custom host variable via a
generated ``explicit_host_conf`` file. This runs on the central site before the configuration
snapshots are built, so the file reaches every site with the configuration sync (``ultimatemt``
builds a filtered one per site, see ``relations_of_site``). The central config knows every host
of every site, so cross-site links resolve correctly here; each site's core only emits the macro
for the hosts it actually monitors.

A host attribute normally reaches the core through :meth:`ABCHostAttribute.nagios_name` and lands
in its own folder's ``hosts.mk`` when that folder is saved. Relations cannot use that path: the
derived reverse links belong to hosts in *other* folders, and the counterpart's site can only be
looked up against the whole tree - neither is known while saving a single folder.

:func:`register` declares the generated file for config sync; the write itself is triggered from
the activation (see :func:`export_host_relations`).

What the resolution dropped with a warning is written to a file of the central site, which the
activation adds to the result of the sites concerned (see :func:`add_dropped_relations`).

The format the value is written in - and hence everything a reader needs to know about it - is
defined in :mod:`cmk.gui.utils.host_relations`, which the monitoring side reads it back with.
"""

from collections.abc import Callable, Mapping, MutableMapping, Sequence
from pathlib import Path
from typing import cast

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.hostaddress import HostName
from cmk.gui.log import logger
from cmk.gui.utils.host_relations import (
    dump_resolved_relations,
    parse_resolved_relations,
    RELATIONS_MACRO,
)
from cmk.gui.watolib.config_sync import (
    ReplicationPath,
    ReplicationPathRegistry,
    ReplicationPathType,
)
from cmk.gui.watolib.host_relations import (
    dropped_relation_message,
    DroppedRelation,
    parse_dropped_relation,
    RelatedHost,
    resolve_all_relations,
    ResolvedRelations,
)
from cmk.gui.watolib.paths import wato_var_dir

LOGGER = logger.getChild("host_relations")

#: What the activation result prefixes the dropped relations of a site with.
DROPPED_RELATIONS_WARNING_KEY = "host_relations"


def relations_export_path() -> Path:
    """The generated ``explicit_host_conf`` file, in the directory that is synced to the sites."""
    return cmk.utils.paths.check_mk_config_dir / "relations.mk"


def relations_dropped_path() -> Path:
    """What the last export dropped with a warning, outside ``conf.d``: it is no config file, and
    a file there newer than the last core compilation would cost the incremental activation."""
    return wato_var_dir() / "host_relations_dropped.mk"


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


def write_host_relations(path: Path, resolved: ResolvedRelations) -> bool:
    """Write ``resolved`` as the ``_CMK_RELATIONS`` variable of its hosts.

    Returns whether it was written.
    """
    return _write_export_file(
        path,
        {str(host): dump_resolved_relations(relations) for host, relations in resolved.items()},
    )


def read_host_relations(path: Path) -> ResolvedRelations:
    """The relations an export file holds, the way the core reads them."""
    config = store.load_mk_file(path, default={"explicit_host_conf": {}}, lock=False)
    explicit_host_conf = cast(Mapping[str, Mapping[str, str]], config["explicit_host_conf"])
    return {
        HostName(host): list(parse_resolved_relations(value))
        for host, value in explicit_host_conf.get(RELATIONS_MACRO, {}).items()
    }


def write_dropped_relations(path: Path, dropped: Sequence[DroppedRelation]) -> None:
    store.save_object_to_file(path, list(dropped))


def read_dropped_relations(path: Path) -> Sequence[DroppedRelation]:
    """Skips what this version cannot word: a failed export leaves the file of another version."""
    raw = store.load_object_from_file(path, default=[])
    dropped = []
    for entry in raw if isinstance(raw, list) else []:
        if (parsed := parse_dropped_relation(entry)) is None:
            LOGGER.debug(
                "Skipping a dropped relation this version cannot word: %(entry)r", {"entry": entry}
            )
            continue
        dropped.append(parsed)
    return dropped


def export_host_relations(
    all_hosts: Mapping[HostName, RelatedHost],
    export_file_path: Path,
    dropped_file_path: Path,
    customer_of_site: Callable[[str], object] = lambda _site: None,
) -> None:
    """Resolve the relations of ``all_hosts`` and persist them as the ``_CMK_RELATIONS`` variable.

    Called once per activation on the central site, immediately before the sync snapshots are
    built; the links come from the ``relations`` attribute of every host of the folder tree.
    Counterparts that do not exist are dropped by :func:`resolve_all_relations`. What it dropped
    with a warning goes to ``dropped_file_path``, for the activation of the sites concerned -
    unless their hosts belong to different customers: the warning names both hosts, so that one
    stays in the log of the central site.
    """
    dropped: list[DroppedRelation] = []
    resolved = resolve_all_relations(all_hosts, on_dropped=dropped.append)
    written = write_host_relations(export_file_path, resolved)
    write_dropped_relations(
        dropped_file_path,
        [entry for entry in dropped if len({*map(customer_of_site, entry["sites"])}) == 1],
    )
    LOGGER.debug(
        "Host relations export: %(hosts)d host(s) with relations, %(entries)d relation entries, "
        "%(outcome)s %(path)s.",
        {
            "hosts": len(resolved),
            "entries": sum(len(relations) for relations in resolved.values()),
            "outcome": "written to" if written else "unchanged in",
            "path": export_file_path,
        },
    )


def dropped_relations_of_site(path: Path, site_id: str) -> list[str]:
    """What the last export dropped on hosts of ``site_id``, for its activation result.

    Read on every activation of the site, since the file stays until an export without the problem
    replaces it: the warning is meant to nag until someone settles the pair in Setup.
    """
    return [
        dropped_relation_message(dropped)
        for dropped in read_dropped_relations(path)
        if site_id in dropped["sites"]
    ]


def add_dropped_relations(
    warnings: MutableMapping[str, list[str]], site_id: str, path: Path
) -> None:
    """Add to the activation result of ``site_id`` what the last export dropped on its hosts."""
    if dropped := dropped_relations_of_site(path, site_id):
        warnings.setdefault(DROPPED_RELATIONS_WARNING_KEY, []).extend(dropped)


def register(replication_path_registry: ReplicationPathRegistry) -> None:
    replication_path_registry.register(
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="host_relations",
            site_path=str(relations_export_path().relative_to(cmk.utils.paths.omd_root)),
        )
    )
