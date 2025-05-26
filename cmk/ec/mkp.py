#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping
from pathlib import Path

import cmk.utils.paths

from cmk.mkp_tool import PackageOperationCallbacks, PackagePart

from .config import MkpRulePackProxy
from .rule_packs import export_rule_pack, load_rule_packs, save_rule_packs


def rule_pack_dir() -> Path:
    """Returns the default WATO directory of the Event Console."""
    return cmk.utils.paths.default_config_dir / "mkeventd.d/wato"


def mkp_rule_pack_dir() -> Path:
    """Returns the default directory for rule pack exports of the Event Console."""
    return cmk.utils.paths.default_config_dir / "mkeventd.d/mkp/rule_packs"


def _install_packaged_rule_packs(file_names: Iterable[Path]) -> None:
    """
    Adds rule pack proxy objects to the list of rule packs given a list
    of file names. The file names without the file extension are used as
    the ID of the rule pack.
    """
    rule_packs = list(load_rule_packs())
    rule_pack_ids = {rp["id"]: i for i, rp in enumerate(rule_packs)}
    ids = [fn.stem for fn in file_names]
    for id_ in ids:
        index = rule_pack_ids.get(id_)
        if index is not None and isinstance(rule_packs[index], MkpRulePackProxy):
            rule_packs[index] = MkpRulePackProxy(id_)
        else:
            rule_packs.append(MkpRulePackProxy(id_))
    save_rule_packs(rule_packs, pretty_print=False, path=rule_pack_dir())


def _uninstall_packaged_rule_packs(file_names: Iterable[Path]) -> None:
    """
    This function synchronizes the rule packs in rules.mk and the packaged rule packs
    of a MKP upon deletion of that MKP. When a modified or an unmodified MKP is
    deleted the exported rule pack and the rule pack in rules.mk are both deleted.
    """
    affected_ids = {fn.stem for fn in file_names}
    save_rule_packs(
        (rp for rp in load_rule_packs() if rp["id"] not in affected_ids),
        pretty_print=False,
        path=rule_pack_dir(),
    )


def _release_packaged_rule_packs(file_names: Iterable[Path]) -> None:
    """
    This function synchronizes the rule packs in rules.mk and the rule packs
    packaged in a MKP upon release of that MKP. The following cases have
    to be distinguished:

        1. Upon release of an unmodified MKP package the proxy in rules.mk
           and the exported rule pack are unchanged.
        2. Upon release of a MKP package with locally modified rule packs the
           modified rule pack updates the exported version.
    """
    rule_packs = list(load_rule_packs())
    rule_pack_ids = [rp["id"] for rp in rule_packs]
    affected_ids = [fn.stem for fn in file_names]

    save = False
    for id_ in affected_ids:
        index = rule_pack_ids.index(id_)
        rp = rule_packs[index]
        if not isinstance(rp, MkpRulePackProxy):
            save = True
            export_rule_pack(rp, pretty_print=False, path=mkp_rule_pack_dir())
            rule_packs[index] = MkpRulePackProxy(id_)

    if save:
        save_rule_packs(rule_packs, pretty_print=False, path=rule_pack_dir())


def mkp_callbacks() -> Mapping[PackagePart, PackageOperationCallbacks]:
    return {
        PackagePart.EC_RULE_PACKS: PackageOperationCallbacks(
            install=_install_packaged_rule_packs,
            uninstall=_uninstall_packaged_rule_packs,
            release=_release_packaged_rule_packs,
        ),
    }
