#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import gettext
import subprocess
from pathlib import Path

import flask
import pytest

from tests.testlib.common.repo import repo_path

import cmk.utils.paths

from cmk.gui import i18n
from cmk.gui.utils.script_helpers import application_and_request_context

LOCAL_DE_TRANSLATIONS = {
    "Age": "Alter",
    "Edit foreign %s": "Fremde(n) %s editieren",
    "bla": "blub",
}


@pytest.fixture(scope="session")
def locale_base_dir() -> Path:
    return repo_path() / "locale"


@pytest.fixture(autouse=True)
def locale_paths(tmp_path, monkeypatch, locale_base_dir):
    monkeypatch.setattr(cmk.utils.paths, "locale_dir", locale_base_dir)
    monkeypatch.setattr(cmk.utils.paths, "local_locale_dir", tmp_path / "locale")


@pytest.fixture(autouse=True, scope="session")
def compile_builtin_po_files(locale_base_dir):
    builtin_dir = locale_base_dir / "de" / "LC_MESSAGES"
    po_file = builtin_dir / "multisite.po"
    mo_file = builtin_dir / "multisite.mo"
    if po_file.exists():
        subprocess.call(["msgfmt", str(po_file), "-o", str(mo_file)])


@pytest.fixture()
def local_translation() -> None:
    _add_local_translation("de", "Äxtended German", texts=LOCAL_DE_TRANSLATIONS)
    _add_local_translation("xz", "Xz", texts={"bla": "blub"})
    # Add one package localization
    _add_local_translation("packages/pkg_name/de", "pkg_name German", texts={"pkg1": "lala"})


def _add_local_translation(lang, alias, texts):
    local_dir = cmk.utils.paths.local_locale_dir / lang / "LC_MESSAGES"
    local_dir.mkdir(parents=True)
    po_file = local_dir / "multisite.po"
    mo_file = local_dir / "multisite.mo"

    with (local_dir.parent / "alias").open("w", encoding="utf-8") as f:
        f.write("%s\n" % alias)

    with po_file.open(mode="w", encoding="utf-8") as f:
        f.write(
            """
msgid ""
msgstr ""
"Project-Id-Version: Locally modified Check_MK translation\\n"
"Report-Msgid-Bugs-To: checkmk-en@lists.mathias-kettner.de\\n"
"Language-Team: none\\n"
"Language: de\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"
"""
        )

        for key, val in texts.items():
            f.write(
                """
msgid "%s"
msgstr "%s"
"""
                % (key, val)
            )

    subprocess.call(["msgfmt", str(po_file), "-o", str(mo_file)])


def test_underscore_without_localization(flask_app: flask.Flask) -> None:
    with flask_app.test_request_context("/"):
        assert i18n.get_current_language() == "en"
        assert isinstance(i18n._("bla"), str)
        assert i18n._("bla") == "bla"
        assert i18n._("") == ""


@pytest.mark.usefixtures("local_translation")
def test_underscore_localization() -> None:
    with application_and_request_context():
        i18n.localize("de")
        assert i18n.get_current_language() == "de"
        assert i18n._("Age") == "Alter"
        assert i18n._("") == ""

    with application_and_request_context():
        i18n._unlocalize()
        assert i18n._("Age") == "Age"
        assert i18n.get_current_language() == "en"


@pytest.mark.usefixtures("local_translation")
def test_lazy_localization() -> None:
    with application_and_request_context():
        lazy_str = i18n._l("Age")
        assert lazy_str == "Age"

    with application_and_request_context():
        i18n.localize("de")
        assert lazy_str == "Alter"

    with application_and_request_context():
        i18n._unlocalize()
        assert lazy_str == "Age"


@pytest.mark.usefixtures("local_translation")
def test_lazy_with_args() -> None:
    with application_and_request_context():
        lazy_str = i18n._l("Edit foreign %s") % "zeugs"
        assert lazy_str == "Edit foreign zeugs"

    with application_and_request_context():
        i18n.localize("de")
        assert lazy_str == "Fremde(n) zeugs editieren"

    with application_and_request_context():
        i18n._unlocalize()
        assert lazy_str == "Edit foreign zeugs"


def test_init_language_not_existing() -> None:
    assert i18n._init_language("xz") is None


@pytest.mark.usefixtures("local_translation", "request_context")
def test_init_language_with_local_modification() -> None:
    trans = i18n._init_language("de")
    assert isinstance(trans, gettext.GNUTranslations)
    assert trans.info()["language"] == "de"
    assert trans.info()["project-id-version"] == "Locally modified Check_MK translation"

    translated = trans.gettext("bla")
    assert isinstance(translated, str)
    assert translated == "blub"


@pytest.mark.usefixtures("local_translation", "request_context")
def test_init_language_with_package_localization() -> None:
    trans = i18n._init_language("de")
    assert trans is not None
    translated = trans.gettext("pkg1")
    assert isinstance(translated, str)
    assert translated == "lala"


@pytest.mark.usefixtures("local_translation")
def test_get_language_local_alias() -> None:
    assert isinstance(i18n.get_language_alias("de"), str)
    assert i18n.get_language_alias("de") == "Äxtended German"


@pytest.mark.usefixtures("local_translation")
def test_local_langs_are_available_in_get_languages() -> None:
    local_langs = [("de", "Äxtended German"), ("xz", "Xz")]
    registered_langs = i18n.get_languages()
    assert all(local_lang in registered_langs for local_lang in local_langs)
