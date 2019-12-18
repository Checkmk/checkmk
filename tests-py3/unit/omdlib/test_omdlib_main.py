#!/usr/bin/env python3
# pylint: disable=redefined-outer-name
import os
import re
import pytest  # type: ignore[import]

import omdlib
import omdlib.main
from omdlib.version_info import VersionInfo


def _strip_ansi(s):
    ansi_escape = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", s)


def test_initialize_site_ca(monkeypatch, tmp_path):
    site_id = "tested"
    ca_path = tmp_path / site_id / "etc" / "ssl"
    ca_path.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member

    monkeypatch.setattr(omdlib.certs.CertificateAuthority, "ca_path", property(lambda x: ca_path))

    omdlib.main.initialize_site_ca(omdlib.main.SiteContext(site_id))
    assert (ca_path / "ca.pem").exists()  # pylint: disable=no-member
    assert (ca_path / "sites" / ("%s.pem" % site_id)).exists()  # pylint: disable=no-member


@pytest.fixture()
def version_info():
    return VersionInfo(omdlib.__version__)


@pytest.fixture()
def site_context():
    return omdlib.main.SiteContext("unit")


@pytest.fixture()
def tmp_fstab(tmp_path, monkeypatch):
    fstab_path = tmp_path / "fstab"
    monkeypatch.setattr(omdlib.main, "fstab_path", lambda: str(fstab_path))
    return fstab_path


def test_add_to_fstab_not_existing(tmp_fstab, site_context):
    assert not tmp_fstab.exists()
    omdlib.main.add_to_fstab(site_context)
    assert not tmp_fstab.exists()


def test_add_to_fstab(tmp_fstab, site_context):
    tmp_fstab.open("w", encoding="utf-8").write(u"# system fstab bla\n")
    omdlib.main.add_to_fstab(site_context)
    assert tmp_fstab.open().read() == (
        "# system fstab bla\n"
        "tmpfs  /opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit 0 0\n")


def test_add_to_fstab_with_size(tmp_fstab, site_context):
    tmp_fstab.open("w", encoding="utf-8").write(u"# system fstab bla\n")
    omdlib.main.add_to_fstab(site_context, tmpfs_size="1G")
    assert tmp_fstab.open().read() == (
        "# system fstab bla\n"
        "tmpfs  /opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit,size=1G 0 0\n")


def test_add_to_fstab_no_newline_at_end(tmp_fstab, site_context):
    tmp_fstab.open("w", encoding="utf-8").write(u"# system fstab bla")
    omdlib.main.add_to_fstab(site_context)
    assert tmp_fstab.open().read() == (
        "# system fstab bla\n"
        "tmpfs  /opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit 0 0\n")


def test_add_to_fstab_empty(tmp_fstab, site_context):
    tmp_fstab.open("w", encoding="utf-8").write(u"")
    omdlib.main.add_to_fstab(site_context)
    assert tmp_fstab.open().read() == (
        "tmpfs  /opt/omd/sites/unit/tmp tmpfs noauto,user,mode=755,uid=unit,gid=unit 0 0\n")


def test_hostname():
    assert omdlib.main.hostname() == os.popen("hostname").read().strip()


def test_main_help(site_context, capsys, version_info):
    omdlib.main.main_help(version_info, site_context)
    stdout = capsys.readouterr()[0]
    assert "omd COMMAND -h" in stdout


def test_main_version_of_current_site(site_context, capsys, monkeypatch, version_info):
    monkeypatch.setattr(omdlib, "__version__", "1.2.3p4")
    global_opts = omdlib.main.default_global_options()
    args = []
    options = []
    omdlib.main.main_version(version_info, site_context, global_opts, args, options)

    stdout = capsys.readouterr()[0]
    assert stdout == "OMD - Open Monitoring Distribution Version 1.2.3p4\n"


def test_main_version_root(capsys, monkeypatch, version_info):
    monkeypatch.setattr(omdlib, "__version__", "1.2.3p4")
    global_opts = omdlib.main.default_global_options()
    args = []
    options = []
    omdlib.main.main_version(version_info, omdlib.main.RootContext(), global_opts, args, options)

    stdout = capsys.readouterr()[0]
    assert stdout == "OMD - Open Monitoring Distribution Version 1.2.3p4\n"


def test_main_version_root_not_existing_site(version_info):
    with pytest.raises(SystemExit, match="No such site: testsite"):
        omdlib.main.main_version(version_info, omdlib.main.RootContext(),
                                 omdlib.main.default_global_options(), ["testsite"], [])


def test_main_version_root_specific_site_broken_version(fs, version_info):
    fs.create_dir("/omd/sites/testsite")
    with pytest.raises(SystemExit, match="Failed to determine site version"):
        omdlib.main.main_version(version_info, omdlib.main.RootContext(),
                                 omdlib.main.default_global_options(), ["testsite"], [])


def test_main_version_root_specific_site(fs, capsys, monkeypatch, version_info):
    fs.create_dir("/omd/sites/testsite")
    fs.create_symlink("/omd/sites/testsite/version", "../../versions/1.2.3p4")
    fs.create_dir("/omd/versions/1.2.3p4")
    omdlib.main.main_version(version_info, omdlib.main.RootContext(),
                             omdlib.main.default_global_options(), ["testsite"], [])

    stdout = capsys.readouterr()[0]
    assert stdout == "OMD - Open Monitoring Distribution Version 1.2.3p4\n"


def test_main_version_root_specific_site_bare(fs, capsys, monkeypatch, version_info):
    fs.create_dir("/omd/sites/testsite")
    fs.create_symlink("/omd/sites/testsite/version", "../../versions/1.2.3p4")
    fs.create_dir("/omd/versions/1.2.3p4")
    omdlib.main.main_version(version_info, omdlib.main.RootContext(),
                             omdlib.main.default_global_options(), ["testsite"], ["bare"])

    stdout = capsys.readouterr()[0]
    assert stdout == "1.2.3p4\n"


def test_main_versions(fs, capsys, monkeypatch, version_info):
    fs.create_dir("/omd/versions/1.2.3p4")
    fs.create_dir("/omd/versions/1.6.0p4")
    fs.create_dir("/omd/versions/1.6.0p14")
    fs.create_symlink("/omd/versions/default", "1.6.0p4")
    omdlib.main.main_versions(version_info, omdlib.main.RootContext(),
                              omdlib.main.default_global_options(), [], [])

    stdout = capsys.readouterr()[0]
    assert stdout == "1.2.3p4\n1.6.0p14\n1.6.0p4 (default)\n"


def test_main_versions_bare(fs, capsys, monkeypatch, version_info):
    fs.create_dir("/omd/versions/1.2.3p4")
    fs.create_dir("/omd/versions/1.6.0p4")
    fs.create_dir("/omd/versions/1.6.0p14")
    fs.create_symlink("/omd/versions/default", "1.6.0p4")
    omdlib.main.main_versions(version_info, omdlib.main.RootContext(),
                              omdlib.main.default_global_options(), [], ["bare"])

    stdout = capsys.readouterr()[0]
    assert stdout == "1.2.3p4\n1.6.0p14\n1.6.0p4\n"


def test_default_version(fs):
    fs.create_symlink("/omd/versions/default", "2019.12.11.cee")
    assert omdlib.main.default_version() == "2019.12.11.cee"
    assert isinstance(omdlib.main.default_version(), str)


def test_omd_versions(fs):
    fs.create_dir("/omd/versions/2019.12.11.cee")
    fs.create_dir("/omd/versions/1.6.0p7")
    fs.create_dir("/omd/versions/1.6.0i1")
    fs.create_dir("/omd/versions/1.6.0i10")
    fs.create_dir("/omd/versions/1.2.0p23")
    fs.create_symlink("/omd/versions/default", "2019.12.11.cee")

    assert omdlib.main.omd_versions() == [
        '1.2.0p23', '1.6.0i1', '1.6.0i10', '1.6.0p7', '2019.12.11.cee'
    ]


def test_version_exists(fs):
    fs.create_dir("/omd/versions/1.6.0p7")
    assert omdlib.main.version_exists("1.6.0p7") is True
    assert omdlib.main.version_exists("1.6.0p6") is False


def test_main_sites(fs, capsys, monkeypatch, version_info):
    fs.create_dir("/omd/versions/1.2.3p4")
    fs.create_dir("/omd/versions/1.6.0p4")
    fs.create_dir("/omd/versions/1.6.0p14")
    fs.create_symlink("/omd/versions/default", "1.6.0p4")

    # Empty site directory
    fs.create_dir("/omd/sites/empty")
    fs.create_file("/omd/apache/empty.conf")

    # Site with version
    fs.create_dir("/omd/sites/xyz")
    fs.create_symlink("/omd/sites/xyz/version", "../../versions/1.2.3p4")
    fs.create_file("/omd/apache/xyz.conf")

    # Site with not existing version
    fs.create_dir("/omd/sites/broken")
    fs.create_symlink("/omd/sites/broken/version", "../../versions/1.0.0")
    fs.create_file("/omd/apache/broken.conf")

    # Site with default version
    fs.create_dir("/omd/sites/default")
    fs.create_symlink("/omd/sites/default/version", "../../versions/1.6.0p4")
    fs.create_file("/omd/apache/default.conf")

    # Disabled site
    fs.create_dir("/omd/sites/disabled")
    fs.create_symlink("/omd/sites/disabled/version", "../../versions/1.6.0p4")

    omdlib.main.main_sites(version_info, omdlib.main.RootContext(),
                           omdlib.main.default_global_options(), [], [])

    stdout = _strip_ansi(capsys.readouterr()[0])
    assert stdout == \
            'broken           1.0.0             \n' \
            'default          1.6.0p4          default version \n' \
            'disabled         1.6.0p4          default version, disabled \n' \
            'empty            (none)           empty site dir \n' \
            'xyz              1.2.3p4           \n'


def test_sitename_must_be_valid_ok(fs):
    fs.create_dir("/omd/sites/lala")
    assert omdlib.main.sitename_must_be_valid(omdlib.main.SiteContext("lulu")) is None


@pytest.mark.parametrize("name,expected_result", [
    ("0asd", False),
    ("asd0", True),
    ("", False),
    ("aaaaaaaaaaaaaaaa", True),
    ("aaaaaaaaaaaaaaaaa", False),
])
def test_sitename_must_be_valid_regex(fs, name, expected_result):
    fs.create_dir("/omd/sites/lala")

    if expected_result:
        assert omdlib.main.sitename_must_be_valid(omdlib.main.SiteContext(name)) is None
    else:
        with pytest.raises(SystemExit, match="Invalid site name"):
            omdlib.main.sitename_must_be_valid(omdlib.main.SiteContext(name))


def test_sitename_must_be_valid_already_exists(fs):
    fs.create_dir("/omd/sites/lala")

    with pytest.raises(SystemExit, match="already existing"):
        omdlib.main.sitename_must_be_valid(omdlib.main.SiteContext("lala"))


def test_get_orig_working_directory(fs):
    try:
        orig_wd = os.getcwd()

        fs.create_dir("/lala")
        os.chdir("/lala")
        assert omdlib.main._get_orig_working_directory() == "/lala"
    finally:
        os.chdir(orig_wd)


def test_get_orig_working_directory_not_existing(tmp_path):
    try:
        orig_wd = os.getcwd()

        test_dir = tmp_path.joinpath("lala")
        test_dir.mkdir()

        os.chdir(str(test_dir))
        assert os.getcwd() == str(test_dir)

        test_dir.rmdir()
        assert not test_dir.exists()

        assert omdlib.main._get_orig_working_directory() == "/"
    finally:
        os.chdir(orig_wd)
