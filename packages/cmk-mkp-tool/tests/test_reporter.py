#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from pytest import MonkeyPatch

from cmk.mkp_tool import PackagePart, PathConfig
from cmk.mkp_tool._reporter import _all_local_files, all_packable_files, categorize_files


def _setup_local_files_structure(path_config: PathConfig) -> None:
    for part in PackagePart:
        part_path = path_config.get_path(part)
        subdir = part_path / "subdir"
        subdir.mkdir(parents=True)
        (part_path / f"regular_file_of_{part.ident}.py").touch()
        (part_path / f".hidden_file_of_{part.ident}.py").touch()
        (part_path / f"editor_file_of_{part.ident}.py~").touch()
        (part_path / f"compiled_file_of_{part.ident}.pyc").touch()
        (subdir / f"subdir_file_of_{part.ident}.py").touch()

    other_file = path_config.local_root / "some" / "other" / "file.sh"
    other_file.parent.mkdir(parents=True)
    other_file.touch()


def test_get_local_files_by_part(path_config: PathConfig) -> None:
    _setup_local_files_structure(path_config)
    expected: dict[PackagePart | None, set[Path]] = {
        **{
            p: {Path(f"regular_file_of_{p.ident}.py"), Path(f"subdir/subdir_file_of_{p.ident}.py")}
            for p in PackagePart
            if p is not PackagePart.EC_RULE_PACKS
        },
        None: {
            path_config.local_root / "some" / "other" / "file.sh",
        },
    }
    assert _all_local_files(path_config) == expected


def test_get_packable_files_by_part(path_config: PathConfig) -> None:
    _setup_local_files_structure(path_config)

    expected: dict[PackagePart, set[Path]] = {
        **{
            p: {Path(f"regular_file_of_{p.ident}.py"), Path(f"subdir/subdir_file_of_{p.ident}.py")}
            for p in PackagePart
            if p is not PackagePart.EC_RULE_PACKS
        },
        PackagePart.EC_RULE_PACKS: {
            Path(".hidden_file_of_ec_rule_packs.py"),
            Path("compiled_file_of_ec_rule_packs.pyc"),
            Path("editor_file_of_ec_rule_packs.py~"),
            Path("regular_file_of_ec_rule_packs.py"),
            Path("subdir"),
        },
    }
    assert all_packable_files(path_config) == expected


_PATH_CONFIG = PathConfig(
    cmk_plugins_dir=Path("/omd/sites/mySite/local/lib/python3/cmk/plugins/"),
    cmk_addons_plugins_dir=Path("/omd/sites/mySite/local/lib/python3/cmk_addons/plugins/"),
    agent_based_plugins_dir=Path(
        "/omd/sites/mySite/local/lib/python3/cmk/base/plugins/agent_based/"
    ),
    agents_dir=Path("/omd/sites/mySite/share/check_mk/agents/"),
    alert_handlers_dir=Path("/omd/sites/mySite/NEVERMIND"),
    bin_dir=Path("/omd/sites/mySite/NEVERMIND"),
    check_manpages_dir=Path("/omd/sites/mySite/NEVERMIND"),
    checks_dir=Path("/omd/sites/mySite/NEVERMIND"),
    doc_dir=Path("/omd/sites/mySite/NEVERMIND"),
    gui_plugins_dir=Path("/omd/sites/mySite/NEVERMIND"),
    inventory_dir=Path("/omd/sites/mySite/NEVERMIND"),
    lib_dir=Path("/omd/sites/mySite/local/lib"),
    locale_dir=Path("/omd/sites/mySite/NEVERMIND"),
    mib_dir=Path("/omd/sites/mySite/NEVERMIND"),
    mkp_rule_pack_dir=Path("/omd/sites/mySite/NEVERMIND"),
    notifications_dir=Path("/omd/sites/mySite/NEVERMIND"),
    pnp_templates_dir=Path("/omd/sites/mySite/NEVERMIND"),
    web_dir=Path("/omd/sites/mySite/NEVERMIND"),
    local_root=Path("/omd/sites/mySite/NEVERMIND"),
)


def test_categorize_files_empty() -> None:
    assert categorize_files({}, _PATH_CONFIG) == {}


def _fake_resolve(self: Path) -> Path:
    str_self = str(self)
    if str_self.startswith("/omd/"):
        str_self = "/opt" + str_self
    return Path(str_self)


def test_categorize_files(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "resolve", _fake_resolve)

    resolved_to_abstracted = {
        Path(
            "/opt/omd/sites/mySite/local/lib/python3/cmk/plugins/family/agent_based/check.py"
        ): Path("/omd/sites/mySite/local/lib/python3/cmk/plugins/family/agent_based/check.py"),
        Path(
            "/opt/omd/sites/mySite/local/lib/python3/cmk_addons/plugins/family/agent_based/check.py"
        ): Path(
            "/omd/sites/mySite/local/lib/python3/cmk_addons/plugins/family/agent_based/check.py"
        ),
        Path(
            "/opt/omd/sites/mySite/local/lib/python3/cmk/base/cee/plugins/bakery/bakelet.py"
        ): Path("/omd/sites/mySite/local/lib/python3/cmk/base/cee/plugins/bakery/bakelet.py"),
    }
    assert categorize_files(resolved_to_abstracted, _PATH_CONFIG) == {
        PackagePart.CMK_PLUGINS: {
            Path("family/agent_based/check.py"),
        },
        PackagePart.CMK_ADDONS_PLUGINS: {
            Path("family/agent_based/check.py"),
        },
        PackagePart.LIB: {
            Path("python3/cmk/base/cee/plugins/bakery/bakelet.py"),
        },
    }
