#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Contract tests: the languages collector agrees with the GUI on the languages in use

The collector parses the GUI configuration and the user profiles itself. These tests let the
GUI write the settings and the users and compare the collector's result with the language the
GUI resolves for each user.
"""

import time
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

import pytest

import cmk.product_usage.collectors.languages as languages_collector
from cmk.ccc.user import UserId
from cmk.gui import config as gui_config
from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInUser, UserDefaultConfig
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.global_settings import save_global_settings_raw
from cmk.product_usage.collectors.user_store import load_users_with_profiles
from cmk.product_usage.schema import Languages
from cmk.utils import paths
from tests.testlib.unit.gui.users import create_and_destroy_user


@pytest.fixture(name="user_with_language")
def fixture_user_with_language(load_config: Config) -> Iterator[UserId]:
    with create_and_destroy_user(custom_attrs={"language": "nl"}, config=load_config) as user:
        yield user[0]


@pytest.mark.usefixtures("request_context")
def test_collector_reads_the_default_language_that_the_gui_loads(tmp_path: Path) -> None:
    save_global_settings_raw({"default_language": "de"})

    languages = _collect(_locale_dir(tmp_path, "de"))

    assert (languages.default_language, gui_config.load_config().default_language) == ("de", "de")


@pytest.mark.usefixtures("with_user", "user_with_language")
def test_collector_counts_the_language_that_the_gui_resolves_for_each_user(
    tmp_path: Path,
) -> None:
    save_global_settings_raw({"default_language": "de"})
    config = gui_config.load_config()

    languages = _collect(_locale_dir(tmp_path, "de", "nl"))

    assert _all_users(languages) == Counter(
        _gui_language(UserId(user_id), config)
        for user_id, user in config.multisite_users.items()
        if not user.get("is_automation_user")
    )


def _collect(locale_dir: Path) -> Languages:
    return languages_collector.collect(
        load_users_with_profiles(paths.default_config_dir, paths.profile_dir),
        default_config_dir=paths.default_config_dir,
        locale_dir=locale_dir,
        now=int(time.time()),
    )


def _locale_dir(tmp_path: Path, *languages: str) -> Path:
    """A locale directory that ships the given languages"""
    locale_dir = tmp_path / "locale"
    for language in languages:
        (locale_dir / language).mkdir(parents=True)
    return locale_dir


def _all_users(languages: Languages) -> Counter[str]:
    return Counter(languages.users.active.count_per_language) + Counter(
        languages.users.inactive.count_per_language
    )


def _gui_language(user_id: UserId, config: Config) -> str:
    return LoggedInUser(
        user_id,
        UserPermissions({}, {}, {}, []),
        defaults=UserDefaultConfig(
            users=config.multisite_users,
            default_language=config.default_language,
            default_show_mode=config.show_mode,
        ),
    ).language
