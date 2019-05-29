# -*- encoding: utf-8
import os
import sys
import pytest
from testlib import cmk_path  # pylint: disable=import-error
from re import compile

# consistent to check_mk/agents/cfg_examples/logwatch.cfg
LOGWATCH_CONFIG_CONTENT = """
/var/log/messages
 C Fail event detected on md device
 I mdadm.*: Rebuild.*event detected
 W mdadm\[
 W ata.*hard resetting link
 W ata.*soft reset failed (.*FIS failed)
 W device-mapper: thin:.*reached low water mark
 C device-mapper: thin:.*no free space
 C Error: (.*)

/var/log/auth.log
 W sshd.*Corrupted MAC on input

/var/log/syslog /var/log/kern.log
 I registered panic notifier
 C panic
 C Oops
 W generic protection rip
 W .*Unrecovered read error - auto reallocate failed
"""


@pytest.fixture(scope="module")
def agent_plugin_as_module(request):
    """
    Fixture to inject source code of agent as module. Removes <source-code-file>c during teardown.
    """
    # - setup - start
    agent_path = os.path.abspath(os.path.join(cmk_path(), 'agents', 'plugins', 'mk_logwatch'))
    # To make this setup fail safe and to prevent from potentially loading the module from a
    # left-over mk_logwtachc file from previous test runs try to remove it.
    try:
        os.remove(agent_path + "c")
    except OSError:
        pass  # it's ok if the file is not there

    # import the agent source file as module
    # (imp.load_source() has the side effect of creating mk_logwatchc)
    import imp
    mk_logwatch = imp.load_source("mk_logwatch", agent_path)
    import mk_logwatch  # pylint: disable=import-error,wrong-import-position

    assert "get_config_files" in mk_logwatch.__dict__
    # - setup - end
    yield mk_logwatch  # inject module
    # - teardown - start
    try:
        os.remove(agent_path + "c")
    except OSError:
        pass  # it's ok if the file is not there
    # - teardown - end


def test_get_config_files(agent_plugin_as_module, tmpdir):
    mk_logwatch = agent_plugin_as_module
    fake_config_dir = tmpdir.mkdir("test")
    fake_custom_config_file = fake_config_dir.mkdir("logwatch.d").join("custom.cfg")
    fake_custom_config_file.write("blub")
    print(fake_config_dir)
    fake_config_dir_path = str(fake_config_dir)
    paths = [
        p.replace(fake_config_dir_path, "")
        for p in mk_logwatch.get_config_files(fake_config_dir_path)
    ]
    assert paths == ['/logwatch.cfg', '/logwatch.d/custom.cfg']


def test_iter_config_lines(agent_plugin_as_module, tmpdir):
    """Fakes a single logwatch config files and checks if the agent plugin reads the configuration appropriately."""
    mk_logwatch = agent_plugin_as_module
    # setup
    fake_config_file = tmpdir.mkdir("test").join("logwatch.cfg")
    fake_config_file.write("# this is a comment\nthis is a line   ")
    files = [str(fake_config_file)]

    read = list(mk_logwatch.iter_config_lines(files))

    assert read == ['this is a line']


@pytest.mark.parametrize("config_lines, cluster_name, cluster_data", [
    (
        [
            'not a cluster line',
            '',
            'CLUSTER duck',
            ' 192.168.1.1',
            ' 192.168.1.2  ',
        ],
        "duck",
        ['192.168.1.1', '192.168.1.2'],
    ),
    (
        [
            'CLUSTER empty',
            '',
        ],
        "empty",
        [],
    ),
])
def test_read_config_cluster(agent_plugin_as_module, config_lines, cluster_name, cluster_data,
                             monkeypatch):
    """checks if the agent plugin parses the configuration appropriately."""
    mk_logwatch = agent_plugin_as_module

    monkeypatch.setattr(mk_logwatch, 'iter_config_lines', lambda _files: iter(config_lines))

    __, c_config = mk_logwatch.read_config(None)
    cluster = c_config[0]

    assert isinstance(cluster, mk_logwatch.ClusterConfig)
    assert cluster.name == cluster_name
    assert cluster.ips_or_subnets == cluster_data


def test_read_config_comprehensive(agent_plugin_as_module, monkeypatch):
    """checks if the agent plugin parses the configuration appropriately."""
    mk_logwatch = agent_plugin_as_module
    # setup
    iterlines = iter(LOGWATCH_CONFIG_CONTENT.splitlines())
    monkeypatch.setattr(mk_logwatch, 'iter_config_lines', lambda _files: iterlines)

    # execution
    l_config, __ = mk_logwatch.read_config(None)

    # expected logfiles config
    for lc in l_config:
        assert isinstance(lc, mk_logwatch.LogfilesConfig)

    logfiles_config = l_config[0]
    assert logfiles_config.files == ['/var/log/messages']
    assert [l[0] for l in logfiles_config.patterns] == ['C', 'I', 'W', 'W', 'W', 'W', 'C', 'C']
    patterns_first_logfiles_config = [
        "Fail event detected on md device", "mdadm.*: Rebuild.*event detected", "mdadm\[",
        "ata.*hard resetting link", "ata.*soft reset failed (.*FIS failed)",
        "device-mapper: thin:.*reached low water mark", "device-mapper: thin:.*no free space",
        "Error: (.*)"
    ]

    for compiled, raw in zip([l[1] for l in logfiles_config.patterns],
                             patterns_first_logfiles_config):
        assert compiled.pattern == raw
    assert isinstance(logfiles_config.patterns[0][2],
                      list)  # no "A" pattern levels, empty continuation pattern list ok
    assert isinstance(logfiles_config.patterns[0][3],
                      list)  # no "R" pattern level, empty rewrite pattern list ok


@pytest.mark.parametrize(
    "env_var, istty, statusfile",
    [
        ("192.168.2.1", False, "/path/to/config/logwatch.state.192.168.2.1"),  # tty doesnt matter
        ("::ffff:192.168.2.1", False,
         "/path/to/config/logwatch.state.__ffff_192.168.2.1"),  # tty doesnt matter
        ("192.168.1.4", False, "/path/to/config/logwatch.state.my_cluster"),
        ("1262:0:0:0:0:B03:1:AF18", False,
         "/path/to/config/logwatch.state.1262_0_0_0_0_B03_1_AF18"),
        ("1762:0:0:0:0:B03:1:AF18", False, "/path/to/config/logwatch.state.another_cluster"),
        ("", True, "/path/to/config/logwatch.state.local"),
        ("", False, "/path/to/config/logwatch.state"),
    ])
def test_get_status_filename(agent_plugin_as_module, env_var, istty, statusfile, monkeypatch,
                             mocker):
    """
    May not be executed with pytest option -s set. pytest stdout redirection would colide
    with stdout mock.
    """
    mk_logwatch = agent_plugin_as_module
    monkeypatch.setenv("REMOTE", env_var)
    monkeypatch.setenv("MK_VARDIR", '/path/to/config')
    stdout_mock = mocker.patch("mk_logwatch.sys.stdout")
    stdout_mock.isatty.return_value = istty
    fake_config = [
        mk_logwatch.ClusterConfig("my_cluster",
                                  ['192.168.1.1', '192.168.1.2', '192.168.1.3', '192.168.1.4']),
        mk_logwatch.ClusterConfig("another_cluster",
                                  ['192.168.1.5', '192.168.1.6', '1762:0:0:0:0:B03:1:AF18'])
    ]

    status_filename = mk_logwatch.get_status_filename(fake_config)
    assert status_filename == statusfile


def test_read_status(agent_plugin_as_module, tmpdir):
    # setup
    mk_logwatch = agent_plugin_as_module
    fake_status_file = tmpdir.mkdir("test").join("logwatch.state.another_cluster")
    fake_status_file.write("""/var/log/messages|7767698|32455445
/var/test/x12134.log|12345|32444355""")
    file_path = str(fake_status_file)

    # execution
    actual_status = mk_logwatch.read_status(file_path)
    # comparing dicts (having unordered keys) is ok
    assert actual_status == {
        '/var/log/messages': (7767698, 32455445),
        '/var/test/x12134.log': (12345, 32444355)
    }


def test_save_status(agent_plugin_as_module, tmpdir):
    mk_logwatch = agent_plugin_as_module
    fake_status_file = tmpdir.mkdir("test").join("logwatch.state.another_cluster")
    fake_status_file.write("")
    file_path = str(fake_status_file)
    fake_status = {
        '/var/log/messages': (7767698, 32455445),
        '/var/test/x12134.log': (12345, 32444355)
    }
    mk_logwatch.save_status(fake_status, file_path)
    assert sorted(fake_status_file.read().splitlines()) == [
        '/var/log/messages|7767698|32455445', '/var/test/x12134.log|12345|32444355'
    ]


@pytest.mark.parametrize("pattern_suffix, file_suffixes", [
    ("/*",
     ["/file.log", "/hard_linked_file_a.log", "/hard_linked_file_b.log", "/symlinked_file.log"]),
    ("/**",
     ["/file.log", "/hard_linked_file_a.log", "/hard_linked_file_b.log", "/symlinked_file.log"]),
    ("/subdir/*", ["/subdir/another_symlinked_file.log"]),
    ("/symlink_to_dir/*", ["/symlink_to_dir/yet_another_file.log"]),
])
def test_find_matching_logfiles(agent_plugin_as_module, fake_filesystem, pattern_suffix,
                                file_suffixes):
    mk_logwatch = agent_plugin_as_module
    fake_fs_path = str(fake_filesystem)
    files = mk_logwatch.find_matching_logfiles(fake_fs_path + pattern_suffix)
    assert sorted(files) == [fake_fs_path + fs for fs in file_suffixes]


def test_ip_in_subnetwork(agent_plugin_as_module):
    mk_logwatch = agent_plugin_as_module
    assert mk_logwatch.ip_in_subnetwork("192.168.1.1", "192.168.1.0/24") is True
    assert mk_logwatch.ip_in_subnetwork("192.160.1.1", "192.168.1.0/24") is False
    assert mk_logwatch.ip_in_subnetwork("1762:0:0:0:0:B03:1:AF18",
                                        "1762:0000:0000:0000:0000:0000:0000:0000/64") is True
    assert mk_logwatch.ip_in_subnetwork("1760:0:0:0:0:B03:1:AF18",
                                        "1762:0000:0000:0000:0000:0000:0000:0000/64") is False


@pytest.fixture
def fake_filesystem(tmp_path):
    """
    root
      file.log
      symlink_to_file.log -> symlinked_file.log
      /subdir
        symlink_to_file.log -> another_symlinked_file.log
        /subsubdir
          yaf.log
      /symlink_to_dir -> /symlinked_dir
      /symlinked_dir
        yet_another_file.log
      hard_linked_file_a.log = hard_linked_file_b.log
    """
    fake_fs = tmp_path / "root"
    fake_fs.mkdir()

    fake_file = fake_fs / "file.log"
    fake_file.write_text(u"blub")

    fake_fs_subdir = fake_fs / "subdir"
    fake_fs_subdir.mkdir()

    fake_fs_subsubdir = fake_fs / "subdir" / "subsubdir"
    fake_fs_subsubdir.mkdir()
    fake_subsubdir_file = fake_fs_subsubdir / "yaf.log"
    fake_subsubdir_file.write_text(u"bla")

    fake_fs_another_subdir = fake_fs / "another_subdir"
    fake_fs_another_subdir.mkdir()

    fake_symlink_file_root_level = fake_fs / "symlink_to_file.log"
    fake_symlink_file_root_level.symlink_to(fake_fs / "symlinked_file.log")
    assert fake_symlink_file_root_level.is_symlink()

    fake_symlink_file_subdir_level = fake_fs_subdir / "symlink_to_file.log"
    fake_symlink_file_subdir_level.symlink_to(
        fake_fs_subdir / "another_symlinked_file.log", target_is_directory=False)
    assert fake_symlink_file_subdir_level.is_symlink()

    fake_fs_symlink_to_dir = fake_fs / "symlink_to_dir"
    fake_fs_symlinked_dir = fake_fs / "symlinked_dir"
    fake_fs_symlinked_dir.mkdir()
    symlinked_file = fake_fs_symlinked_dir / "yet_another_file.log"
    symlinked_file.write_text(u"bla")
    fake_fs_symlink_to_dir.symlink_to(fake_fs_symlinked_dir, target_is_directory=True)

    hard_linked_file_a = fake_fs / "hard_linked_file_a.log"
    hard_linked_file_a.write_text(u"bla")  # only create src via writing
    hard_linked_file_b = fake_fs / "hard_linked_file_b.log"
    os.link(str(hard_linked_file_a), str(hard_linked_file_b))
    assert os.stat(str(hard_linked_file_a)) == os.stat(str(hard_linked_file_b))

    return fake_fs


def _print_tree(directory, resolve=True):
    """
    Print fake filesystem with optional expansion of symlinks.
    Don't remove this helper function. Used for debugging.
    """
    print('%s' % directory)
    for path in sorted(directory.rglob('*')):
        if resolve:
            try:  # try resolve symlinks
                path = path.resolve()
            except Exception:
                pass
        depth = len(path.relative_to(directory).parts)
        spacer = '    ' * depth
        print('%s%s' % (spacer, path.name))
