#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import subprocess
from pathlib import Path

import flask

from cmk.gui.watolib import git


def test_add_message_commit_separation(flask_app: flask.Flask) -> None:
    prev = git._git_messages()
    assert not prev

    with flask_app.test_request_context("/NO_SITE/check_mk/login.py"):
        flask_app.preprocess_request()

        assert not git._git_messages()
        git.add_message("dingdong")
        assert git._git_messages() == ["dingdong"]

        flask_app.process_response(flask.Response())

    assert not git._git_messages()
    assert id(git._git_messages()) != id(prev)


def _touch(config_dir: Path, *rel_paths: str) -> None:
    for rel_path in rel_paths:
        path = config_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()


def test_git_add_files_tracks_setup_managed_configuration(tmp_path: Path) -> None:
    _touch(
        tmp_path,
        # Generated main configuration, never under version control
        "main.mk",
        "multisite.mk",
        # Setup managed
        "conf.d/wato/hosts.mk",
        "conf.d/wato/subfolder/hosts.mk",
        "conf.d/wato/bi_config.bi",
        "conf.d/distributed_wato.mk",
        "multisite.d/sites.mk",
        "multisite.d/wato/global.mk",
        "mkeventd.d/wato/rules.mk",
        "mkeventd.d/mkp/rule_packs/my_pack.mk",
        # Written by "omd config", not by Setup
        "conf.d/microcore.mk",
        "conf.d/mkeventd.mk",
        "conf.d/pnp4nagios.mk",
        "multisite.d/liveproxyd.mk",
        "multisite.d/mkeventd.mk",
        # Same names below a tracked subdirectory are Setup managed and must not be excluded
        "conf.d/wato/microcore.mk",
        "multisite.d/wato/mkeventd.mk",
        # Temporary files and directories nobody declared
        "conf.d/wato/hosts.mk.new",
        "conf.d/wato/hosts.pkl",
        "conf.d/somethingelse/foo.mk",
        "mkeventd.d/mkp/stray.mk",
    )

    git._git_command(["init"], tmp_path)
    git._write_gitignore_files(tmp_path)
    git._git_add_files(tmp_path)

    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        encoding="utf-8",
        check=True,
    ).stdout.split()

    assert set(tracked) == {
        ".gitignore",
        "conf.d/wato/.gitignore",
        "conf.d/wato/bi_config.bi",
        "conf.d/wato/hosts.mk",
        "conf.d/wato/microcore.mk",
        "conf.d/wato/subfolder/hosts.mk",
        "conf.d/distributed_wato.mk",
        "multisite.d/wato/.gitignore",
        "multisite.d/wato/global.mk",
        "multisite.d/wato/mkeventd.mk",
        "multisite.d/sites.mk",
        "mkeventd.d/wato/.gitignore",
        "mkeventd.d/wato/rules.mk",
        "mkeventd.d/mkp/rule_packs/my_pack.mk",
    }
    # The MKP tool reports every file in there as a rule pack file
    assert not (tmp_path / "mkeventd.d/mkp/rule_packs/.gitignore").exists()
    # Nothing may be left over that is neither tracked nor ignored
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        encoding="utf-8",
        check=True,
    ).stdout
    assert not [line for line in status.splitlines() if line.startswith("??")]
