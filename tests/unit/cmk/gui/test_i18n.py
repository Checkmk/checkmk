# encoding: utf-8

import subprocess
import gettext
import pytest
from pathlib2 import Path
from testlib import cmk_path

import cmk.utils.paths
import cmk.gui.i18n as i18n


@pytest.fixture(autouse=True)
def locale_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(cmk.utils.paths, "locale_dir", "%s/enterprise/locale" % cmk_path())
    monkeypatch.setattr(cmk.utils.paths, "local_locale_dir", str(tmp_path / "locale"))


@pytest.fixture(autouse=True)
def compile_builtin_po_files(locale_paths):
    builtin_dir = Path(cmk.utils.paths.locale_dir) / "de" / "LC_MESSAGES"
    po_file = builtin_dir / "multisite.po"
    mo_file = builtin_dir / "multisite.mo"
    if po_file.exists() and not mo_file.exists():  # pylint: disable=no-member
        subprocess.call(['msgfmt', str(po_file), '-o', str(mo_file)])


@pytest.fixture()
def local_translation():
    _add_local_translation("de", u"Äxtended German")
    _add_local_translation("xz", "Xz")


def _add_local_translation(lang, alias):
    local_dir = Path(cmk.utils.paths.local_locale_dir) / lang / "LC_MESSAGES"
    local_dir.mkdir(parents=True)  # pylint: disable=no-member
    po_file = local_dir / "multisite.po"
    mo_file = local_dir / "multisite.mo"

    with (local_dir.parent / "alias").open("w", encoding="utf-8") as f:  # pylint: disable=no-member
        f.write(u"%s\n" % alias)

    with po_file.open(mode="w", encoding="utf-8") as f:  # pylint: disable=no-member
        f.write(u'''
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

msgid "bla"
msgstr "blub"
''')

    subprocess.call(['msgfmt', str(po_file), '-o', str(mo_file)])


def test_underscore_without_localization():
    assert i18n.get_current_language() is None
    assert isinstance(i18n._("bla"), unicode)
    assert i18n._("bla") == u"bla"


def test_underscore_localization():
    i18n.localize("de")
    assert i18n.get_current_language() == "de"
    assert i18n._("Age") == "Alter"
    i18n.unlocalize()
    assert i18n._("Age") == "Age"
    assert i18n.get_current_language() is None


def test_get_locale_path():
    assert i18n._get_cmk_locale_path("de") == "%s/enterprise/locale" % cmk_path()
    assert i18n._get_cmk_locale_path("xz") == "%s/enterprise/locale" % cmk_path()


def test_get_locale_path_with_local_modification(local_translation):
    assert i18n._get_cmk_locale_path("de") == cmk.utils.paths.local_locale_dir


def test_init_language_not_existing():
    assert i18n._init_language("xz") is None


def test_init_language_only_builtin():
    trans = i18n._init_language("de")
    assert isinstance(trans, gettext.GNUTranslations)
    assert trans.info()["language"] == "de"
    assert trans.info()["project-id-version"] == "Check_MK Multisite translation 0.1"

    translated = trans.ugettext("bla")
    assert isinstance(translated, unicode)
    assert translated == "bla"


def test_init_language_with_local_modification(local_translation):
    trans = i18n._init_language("de")
    assert isinstance(trans, gettext.GNUTranslations)
    assert trans.info()["language"] == "de"
    assert trans.info()["project-id-version"] == "Locally modified Check_MK translation"

    translated = trans.ugettext("bla")
    assert isinstance(translated, unicode)
    assert translated == "blub"


# Will be enabled soon
#def test_init_language_with_local_modification_fallback(local_translation):
#    trans = i18n._init_language("de")
#    assert isinstance(trans, gettext.GNUTranslations)
#    assert trans.info()["language"] == "de"
#    assert trans.info()["project-id-version"] == "Locally modified Check_MK translation"
#
#    # This string is localized in the standard file, not in the locally
#    # overridden file
#    translated = trans.ugettext("Age")
#    assert isinstance(translated, unicode)
#    assert translated == "Alter"


def test_get_language_alias():
    assert isinstance(i18n.get_language_alias(None), unicode)
    assert i18n.get_language_alias(None) == "English"

    assert isinstance(i18n.get_language_alias("de"), unicode)
    assert i18n.get_language_alias("de") == "German"


def test_get_language_local_alias(local_translation):
    assert isinstance(i18n.get_language_alias("de"), unicode)
    assert i18n.get_language_alias("de") == u"Äxtended German"


def test_get_languages():
    assert i18n.get_languages() == [
        ("", "English"),
        ("de", "German"),
        ("ro", "Romanian"),
    ]


def test_get_languages_new_local_language(local_translation):
    assert i18n.get_languages() == [
        ("", "English"),
        ("ro", "Romanian"),
        ("xz", "Xz"),
        ('de', u'\xc4xtended German'),
    ]
