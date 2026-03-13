#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from pathlib import Path
from unittest.mock import Mock

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.pre_actions.utils import ConflictMode
from cmk.update_config.plugins.pre_actions.welcome_page_conflict import (
    _scan_file_for_welcome_registration,
    PreUpdateWelcomePageConflict,
)


@pytest.fixture(name="pre_update_action")
def _pre_update_action() -> PreUpdateWelcomePageConflict:
    return PreUpdateWelcomePageConflict(
        name="welcome_page_conflict",
        title="Welcome page conflict detection",
        sort_index=21,
        expiry_version=ExpiryVersion.CMK_260,
    )


class TestScanFileForWelcomeRegistration:
    def test_detects_page_registry_register(self, tmp_path: Path) -> None:
        plugin = tmp_path / "my_welcome.py"
        plugin.write_text(
            "from cmk.gui.pages import page_registry, PageEndpoint\n"
            'page_registry.register(PageEndpoint("welcome", my_handler))\n'
        )
        assert _scan_file_for_welcome_registration(plugin) is True

    def test_detects_single_quoted(self, tmp_path: Path) -> None:
        plugin = tmp_path / "my_welcome.py"
        plugin.write_text("page_registry.register(PageEndpoint('welcome', my_handler))\n")
        assert _scan_file_for_welcome_registration(plugin) is True

    def test_detects_legacy_pagehandlers_dict(self, tmp_path: Path) -> None:
        plugin = tmp_path / "my_welcome.py"
        plugin.write_text('pagehandlers["welcome"] = my_handler\n')
        assert _scan_file_for_welcome_registration(plugin) is True

    def test_detects_legacy_pagehandlers_update(self, tmp_path: Path) -> None:
        plugin = tmp_path / "my_welcome.py"
        plugin.write_text('pagehandlers.update({"welcome": my_handler})\n')
        assert _scan_file_for_welcome_registration(plugin) is True

    def test_ignores_other_idents(self, tmp_path: Path) -> None:
        plugin = tmp_path / "my_page.py"
        plugin.write_text('page_registry.register(PageEndpoint("my_custom_page", my_handler))\n')
        assert _scan_file_for_welcome_registration(plugin) is False

    def test_ignores_nonexistent_file(self, tmp_path: Path) -> None:
        assert _scan_file_for_welcome_registration(tmp_path / "nope.py") is False

    def test_ignores_empty_file(self, tmp_path: Path) -> None:
        plugin = tmp_path / "empty.py"
        plugin.write_text("")
        assert _scan_file_for_welcome_registration(plugin) is False


class TestPreUpdateWelcomePageConflict:
    def test_no_conflict_no_dirs(
        self,
        pre_update_action: PreUpdateWelcomePageConflict,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            "cmk.update_config.plugins.pre_actions.welcome_page_conflict.web_dir",
            tmp_path / "nonexistent",
        )
        monkeypatch.setattr(
            "cmk.update_config.plugins.pre_actions.welcome_page_conflict.local_web_dir",
            tmp_path / "also_nonexistent",
        )
        # Should not raise
        pre_update_action(Mock(spec=Logger), ConflictMode.ABORT)

    def test_no_conflict_no_matching_files(
        self,
        pre_update_action: PreUpdateWelcomePageConflict,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        pages_dir = tmp_path / "local" / "plugins" / "pages"
        pages_dir.mkdir(parents=True)
        (pages_dir / "my_page.py").write_text(
            'page_registry.register(PageEndpoint("my_page", handler))\n'
        )
        monkeypatch.setattr(
            "cmk.update_config.plugins.pre_actions.welcome_page_conflict.web_dir",
            tmp_path / "nonexistent",
        )
        monkeypatch.setattr(
            "cmk.update_config.plugins.pre_actions.welcome_page_conflict.local_web_dir",
            tmp_path / "local",
        )
        # Should not raise
        pre_update_action(Mock(spec=Logger), ConflictMode.ABORT)

    def test_conflict_aborts(
        self,
        pre_update_action: PreUpdateWelcomePageConflict,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        pages_dir = tmp_path / "local" / "plugins" / "pages"
        pages_dir.mkdir(parents=True)
        (pages_dir / "welcome.py").write_text(
            'page_registry.register(PageEndpoint("welcome", my_handler))\n'
        )
        monkeypatch.setattr(
            "cmk.update_config.plugins.pre_actions.welcome_page_conflict.web_dir",
            tmp_path / "nonexistent",
        )
        monkeypatch.setattr(
            "cmk.update_config.plugins.pre_actions.welcome_page_conflict.local_web_dir",
            tmp_path / "local",
        )
        with pytest.raises(MKUserError):
            pre_update_action(Mock(spec=Logger), ConflictMode.ABORT)

    def test_conflict_force_continues(
        self,
        pre_update_action: PreUpdateWelcomePageConflict,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        pages_dir = tmp_path / "local" / "plugins" / "pages"
        pages_dir.mkdir(parents=True)
        (pages_dir / "welcome.py").write_text(
            'page_registry.register(PageEndpoint("welcome", my_handler))\n'
        )
        monkeypatch.setattr(
            "cmk.update_config.plugins.pre_actions.welcome_page_conflict.web_dir",
            tmp_path / "nonexistent",
        )
        monkeypatch.setattr(
            "cmk.update_config.plugins.pre_actions.welcome_page_conflict.local_web_dir",
            tmp_path / "local",
        )
        # Should not raise with FORCE
        pre_update_action(Mock(spec=Logger), ConflictMode.FORCE)

    def test_conflict_logged(
        self,
        pre_update_action: PreUpdateWelcomePageConflict,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        pages_dir = tmp_path / "local" / "plugins" / "pages"
        pages_dir.mkdir(parents=True)
        (pages_dir / "custom_welcome.py").write_text('pagehandlers["welcome"] = my_handler\n')
        monkeypatch.setattr(
            "cmk.update_config.plugins.pre_actions.welcome_page_conflict.web_dir",
            tmp_path / "nonexistent",
        )
        monkeypatch.setattr(
            "cmk.update_config.plugins.pre_actions.welcome_page_conflict.local_web_dir",
            tmp_path / "local",
        )
        logger = Mock(spec=Logger)
        with pytest.raises(MKUserError):
            pre_update_action(logger, ConflictMode.ABORT)
        logger.error.assert_called_once()
        log_message = logger.error.call_args[0][0]
        assert "welcome.py" in log_message
        assert "custom_welcome.py" in log_message
