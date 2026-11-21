#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

import cmk.product_usage.collectors.languages as languages_collector
from cmk.product_usage.collectors.user_store import StoredUser
from cmk.product_usage.schema import LanguageCounts, Languages, UserLanguages

NOW = 1767790000
DAY = 24 * 3600
NO_USERS = LanguageCounts(count_per_language={}, count_with_default_language=0)


def test_site_without_settings_and_users_reports_english_and_no_users(tmp_path: Path) -> None:
    languages = _collect(tmp_path)

    assert languages == Languages(
        default_language="en", users=UserLanguages(active=NO_USERS, inactive=NO_USERS)
    )


@pytest.mark.parametrize(
    "settings_file",
    [
        pytest.param("multisite.mk", id="main file"),
        pytest.param("multisite.d/wato/global.mk", id="global settings"),
        pytest.param("multisite.d/languages.mk", id="file below multisite.d"),
    ],
)
def test_default_language_is_read_from_the_gui_configuration(
    tmp_path: Path, settings_file: str
) -> None:
    _write_default_language(tmp_path / settings_file, "de")

    languages = _collect(tmp_path)

    assert languages.default_language == "de"


def test_default_language_of_a_later_gui_configuration_file_wins(tmp_path: Path) -> None:
    _write_default_language(tmp_path / "multisite.mk", "de")
    _write_default_language(tmp_path / "multisite.d/wato/global.mk", "ja")
    _write_default_language(tmp_path / "multisite.d/wato/sitespecific.mk", "en")

    languages = _collect(tmp_path)

    assert languages.default_language == "en"


def test_gui_configuration_file_that_needs_other_settings_still_sets_the_default_language(
    tmp_path: Path,
) -> None:
    path = tmp_path / "multisite.mk"
    path.write_text("default_language = 'de'\nwato_host_attrs += [{'name': 'x'}]\n")

    languages = _collect(tmp_path)

    assert languages.default_language == "de"


def test_user_is_counted_under_the_language_of_the_profile(tmp_path: Path) -> None:
    languages = _collect(tmp_path, [_user(language="ja"), _user(language="en")])

    assert languages.users.active.count_per_language == {"ja": 1, "en": 1}


def test_user_without_a_language_is_counted_under_the_default_language(tmp_path: Path) -> None:
    _write_default_language(tmp_path / "multisite.mk", "de")

    languages = _collect(tmp_path, [_user(), _user(language="de")])

    assert languages.users.active == LanguageCounts(
        count_per_language={"de": 2}, count_with_default_language=1
    )


@pytest.mark.parametrize(
    "last_seen",
    [
        pytest.param(NOW - 30 * DAY, id="30 days ago"),
        pytest.param(NOW - DAY, id="yesterday"),
    ],
)
def test_user_seen_in_the_last_30_days_is_active(tmp_path: Path, last_seen: int) -> None:
    languages = _collect(tmp_path, [_user(language="de", last_seen=last_seen)])

    assert languages.users == UserLanguages(
        active=LanguageCounts(count_per_language={"de": 1}, count_with_default_language=0),
        inactive=NO_USERS,
    )


@pytest.mark.parametrize(
    "last_seen",
    [
        pytest.param(NOW - 30 * DAY - 1, id="more than 30 days ago"),
        pytest.param(0, id="never"),
    ],
)
def test_user_not_seen_in_the_last_30_days_is_inactive(tmp_path: Path, last_seen: int) -> None:
    languages = _collect(tmp_path, [_user(language="de", last_seen=last_seen)])

    assert languages.users == UserLanguages(
        active=NO_USERS,
        inactive=LanguageCounts(count_per_language={"de": 1}, count_with_default_language=0),
    )


def test_automation_users_are_not_counted(tmp_path: Path) -> None:
    languages = _collect(
        tmp_path, [_user(language="en", is_automation=True), _user(is_automation=True)]
    )

    assert languages.users == UserLanguages(active=NO_USERS, inactive=NO_USERS)


def test_language_that_checkmk_does_not_ship_is_counted_as_custom(tmp_path: Path) -> None:
    languages = _collect(tmp_path, [_user(language="klingon"), _user(language="de")])

    assert languages.users.active.count_per_language == {"custom": 1, "de": 1}


def test_default_language_that_checkmk_does_not_ship_is_reported_as_custom(
    tmp_path: Path,
) -> None:
    _write_default_language(tmp_path / "multisite.mk", "klingon")

    languages = _collect(tmp_path)

    assert languages.default_language == "custom"


def _collect(site_dir: Path, users: Sequence[StoredUser] = ()) -> Languages:
    """Collect from a site with the German and Japanese translations installed"""
    locale_dir = site_dir / "share/check_mk/locale"
    for language in ("de", "ja"):
        (locale_dir / language).mkdir(parents=True, exist_ok=True)
    return languages_collector.collect(
        users, default_config_dir=site_dir, locale_dir=locale_dir, now=NOW
    )


def _user(
    *, language: str | None = None, last_seen: int = NOW - DAY, is_automation: bool = False
) -> StoredUser:
    attributes: Mapping[str, object] = {} if language is None else {"language": language}
    return StoredUser(attributes=attributes, is_automation=is_automation, last_seen=last_seen)


def _write_default_language(path: Path, language: str) -> None:
    """Write the setting in the format of the GUI's configuration files"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"default_language = {language!r}\n")
