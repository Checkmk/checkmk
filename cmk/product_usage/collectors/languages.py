#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from cmk.product_usage.collectors.user_store import StoredUser
from cmk.product_usage.schema import LanguageCounts, Languages, UserLanguages

# English is built into the GUI, it has no directory in the locale directory
_BUILT_IN_LANGUAGE = "en"

# Reported instead of the code of a language that an admin added to the site
_CUSTOM_LANGUAGE = "custom"

# A user who logged in or used the GUI within this time is active. This is the longest period of
# users.*.active, so that the active users here are the ones counted there for 30 days.
_ACTIVITY_PERIOD = 30 * 86400


def collect(
    users: Iterable[StoredUser],
    *,
    default_config_dir: Path,
    locale_dir: Path,
    now: int,
) -> Languages:
    shipped_languages = _shipped_languages(locale_dir)

    def reported(language: str) -> str:
        return language if language in shipped_languages else _CUSTOM_LANGUAGE

    default_language = _default_language(default_config_dir)

    active, inactive = _Tally(), _Tally()
    for user in users:
        if user.is_automation:
            continue
        tally = active if user.last_seen >= now - _ACTIVITY_PERIOD else inactive
        match user.attributes.get("language"):
            case str(language):
                tally.count_per_language[reported(language)] += 1
            case _:
                tally.count_per_language[reported(default_language)] += 1
                tally.count_with_default_language += 1

    return Languages(
        default_language=reported(default_language),
        users=UserLanguages(active=active.counts(), inactive=inactive.counts()),
    )


@dataclass
class _Tally:
    count_per_language: Counter[str] = field(default_factory=Counter)
    count_with_default_language: int = 0

    def counts(self) -> LanguageCounts:
        return LanguageCounts(
            count_per_language=dict(self.count_per_language),
            count_with_default_language=self.count_with_default_language,
        )


def _shipped_languages(locale_dir: Path) -> frozenset[str]:
    try:
        translations = frozenset(d.name for d in locale_dir.iterdir() if d.is_dir())
    except FileNotFoundError:
        translations = frozenset()
    return translations | {_BUILT_IN_LANGUAGE}


def _default_language(default_config_dir: Path) -> str:
    """The default language of the GUI

    The GUI reads multisite.mk, then all files below multisite.d in the order of their paths, and
    the last assignment wins. The files are parsed rather than executed, so that a file that
    needs the rest of the GUI configuration does not break the collection.
    """
    default_language = _BUILT_IN_LANGUAGE
    for path in _gui_config_files(default_config_dir):
        for value in _assigned_values(path, "default_language"):
            if isinstance(value, str):
                default_language = value
    return default_language


def _gui_config_files(default_config_dir: Path) -> Iterator[Path]:
    yield default_config_dir / "multisite.mk"
    conf_dir = default_config_dir / "multisite.d"
    yield from sorted((p for p in conf_dir.rglob("*.mk") if p.is_file()), key=str)


def _assigned_values(path: Path, name: str) -> Iterator[object]:
    """The literal values assigned to the variable at the top level of the file, in order

    A file that is missing or cannot be parsed has no values. A value that is no literal is skipped.
    """
    try:
        module = ast.parse(path.read_bytes(), filename=str(path))
    except FileNotFoundError, SyntaxError, ValueError:
        return
    for statement in module.body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in statement.targets
        ):
            try:
                yield ast.literal_eval(statement.value)
            except ValueError, TypeError, SyntaxError, RecursionError:
                continue
