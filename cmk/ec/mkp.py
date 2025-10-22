#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from pathlib import Path

from cmk.mkp_tool import PackageOperationCallbacks, PackagePart

from .config import MkpRulePackProxy
from .rule_packs import export_rule_pack, load_rule_packs, save_rule_packs
from .settings import create_paths, Paths


def _install_packaged_rule_packs(paths: Paths, file_names: Iterable[Path]) -> None:
    """
    Adds rule pack proxy objects to the list of rule packs given a list
    of file names. The file names without the file extension are used as
    the ID of the rule pack.
    """
    rule_packs = list(load_rule_packs(paths))
    rule_pack_ids = {rp["id"]: i for i, rp in enumerate(rule_packs)}
    ids = [fn.stem for fn in file_names]
    for id_ in ids:
        index = rule_pack_ids.get(id_)
        if index is not None and isinstance(rule_packs[index], MkpRulePackProxy):
            rule_packs[index] = MkpRulePackProxy(id_)
        else:
            rule_packs.append(MkpRulePackProxy(id_))
    save_rule_packs(rule_packs, pretty_print=False, path=paths.rule_pack_dir.value)


def _uninstall_packaged_rule_packs(paths: Paths, file_names: Iterable[Path]) -> None:
    """
    This function synchronizes the rule packs in rules.mk and the packaged rule packs
    of a MKP upon deletion of that MKP. When a modified or an unmodified MKP is
    deleted the exported rule pack and the rule pack in rules.mk are both deleted.
    """
    affected_ids = {fn.stem for fn in file_names}
    save_rule_packs(
        (rp for rp in load_rule_packs(paths) if rp["id"] not in affected_ids),
        pretty_print=False,
        path=paths.rule_pack_dir.value,
    )


def _release_packaged_rule_packs(paths: Paths, file_names: Iterable[Path]) -> None:
    """
    This function synchronizes the rule packs in rules.mk and the rule packs
    packaged in a MKP upon release of that MKP. The following cases have
    to be distinguished:

        1. Upon release of an unmodified MKP package the proxy in rules.mk
           and the exported rule pack are unchanged.
        2. Upon release of a MKP package with locally modified rule packs the
           modified rule pack updates the exported version.
    """
    rule_packs = list(load_rule_packs(paths))
    rule_pack_ids = [rp["id"] for rp in rule_packs]
    affected_ids = [fn.stem for fn in file_names]

    save = False
    for id_ in affected_ids:
        index = rule_pack_ids.index(id_)
        rp = rule_packs[index]
        if not isinstance(rp, MkpRulePackProxy):
            save = True
            export_rule_pack(rp, pretty_print=False, path=paths.mkp_rule_pack_dir.value)
            rule_packs[index] = MkpRulePackProxy(id_)

    if save:
        save_rule_packs(rule_packs, pretty_print=False, path=paths.rule_pack_dir.value)


def mkp_callbacks(omd_root: Path) -> Mapping[PackagePart, PackageOperationCallbacks]:
    paths = create_paths(omd_root)
    return {
        PackagePart.EC_RULE_PACKS: PackageOperationCallbacks(
            install=lambda file_names: _install_packaged_rule_packs(paths, file_names),
            uninstall=lambda file_names: _uninstall_packaged_rule_packs(paths, file_names),
            release=lambda file_names: _release_packaged_rule_packs(paths, file_names),
        ),
    }
