# -*- encoding: utf-8
# pylint: disable=protected-access,redefined-outer-name
from __future__ import print_function
import os
import re
import sys
import locale
import pytest  # type: ignore
from testlib import import_module
import six


@pytest.fixture(scope="module")
def mk_logwatch():
    return import_module("agents/plugins/mk_logwatch")


def test_options_defaults(mk_logwatch):
    opt = mk_logwatch.Options()
    for attribute in ('maxfilesize', 'maxlines', 'maxtime', 'maxlinesize', 'regex', 'overflow',
                      'nocontext', 'maxoutputsize'):
        assert getattr(opt, attribute) == mk_logwatch.Options.DEFAULTS[attribute]


@pytest.mark.parametrize("option_string, key, expected_value", [
    ("maxfilesize=42", 'maxfilesize', 42),
    ("maxlines=23", 'maxlines', 23),
    ("maxlinesize=13", 'maxlinesize', 13),
    ("maxtime=0.25", 'maxtime', 0.25),
    ("overflow=I", 'overflow', 'I'),
    ("nocontext=tRuE", 'nocontext', True),
    ("nocontext=FALse", 'nocontext', False),
    ("fromstart=1", 'fromstart', True),
    ("fromstart=yEs", 'fromstart', True),
    ("fromstart=0", 'fromstart', False),
    ("fromstart=no", 'fromstart', False),
    ("maxoutputsize=1024", 'maxoutputsize', 1024),
])
def test_options_setter(mk_logwatch, option_string, key, expected_value):
    opt = mk_logwatch.Options()
    opt.set_opt(option_string)
    actual_value = getattr(opt, key)
    assert isinstance(actual_value, type(expected_value))
    assert actual_value == expected_value


@pytest.mark.parametrize("option_string, expected_pattern, expected_flags", [
    ("regex=foobar", 'foobar', re.UNICODE),
    ("iregex=foobar", 'foobar', re.IGNORECASE | re.UNICODE),
])
def test_options_setter_regex(mk_logwatch, option_string, expected_pattern, expected_flags):
    opt = mk_logwatch.Options()
    opt.set_opt(option_string)
    assert opt.regex.pattern == expected_pattern
    assert opt.regex.flags == expected_flags


def test_get_config_files(mk_logwatch, tmp_path):
    fake_config_dir = tmp_path / "test"
    fake_config_dir.mkdir()
    (fake_config_dir / "logwatch.d").mkdir()
    (fake_config_dir / "logwatch.d").joinpath("custom.cfg").open(mode="w")

    expected = [
        str(fake_config_dir / "logwatch.cfg"),
        str(fake_config_dir / "logwatch.d/custom.cfg")
    ]

    assert mk_logwatch.get_config_files(str(fake_config_dir)) == expected


def test_iter_config_lines(mk_logwatch, tmp_path):
    """Fakes a logwatch config file and checks if the agent plugin reads it appropriately"""
    # setup
    fake_config_path = tmp_path / "test"
    fake_config_path.mkdir()
    fake_config_file = fake_config_path.joinpath("logwatch.cfg")
    fake_config_file.write_text(u"# this is a comment\nthis is a line   ", encoding="utf-8")
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
def test_read_config_cluster(mk_logwatch, config_lines, cluster_name, cluster_data, monkeypatch):
    """checks if the agent plugin parses the configuration appropriately."""
    monkeypatch.setattr(mk_logwatch, 'iter_config_lines', lambda _files: iter(config_lines))

    __, c_config = mk_logwatch.read_config(None)
    cluster = c_config[0]

    assert isinstance(cluster, mk_logwatch.ClusterConfig)
    assert cluster.name == cluster_name
    assert cluster.ips_or_subnets == cluster_data


@pytest.mark.parametrize("config_lines, logfiles_files, logfiles_patterns", [
    (
        [
            u'/var/log/messages',
            u' C Fail event detected on md device',
            u' I mdadm.*: Rebuild.*event detected',
            u' W mdadm\\[',
            u' W ata.*hard resetting link',
            u' W ata.*soft reset failed (.*FIS failed)',
            u' W device-mapper: thin:.*reached low water mark',
            u' C device-mapper: thin:.*no free space',
            u' C Error: (.*)',
        ],
        [u'/var/log/messages'],
        [
            (u'C', u'Fail event detected on md device', [], []),
            (u'I', u'mdadm.*: Rebuild.*event detected', [], []),
            (u'W', u'mdadm\\[', [], []),
            (u'W', u'ata.*hard resetting link', [], []),
            (u'W', u'ata.*soft reset failed (.*FIS failed)', [], []),
            (u'W', u'device-mapper: thin:.*reached low water mark', [], []),
            (u'C', u'device-mapper: thin:.*no free space', [], []),
            (u'C', u'Error: (.*)', [], []),
        ],
    ),
    (
        [
            u'/var/log/auth.log',
            u' W sshd.*Corrupted MAC on input',
        ],
        [u'/var/log/auth.log'],
        [(u'W', u'sshd.*Corrupted MAC on input', [], [])],
    ),
    (
        [
            u'/var/log/syslog /var/log/kern.log',
            u' I registered panic notifier',
            u' C panic',
            u' C Oops',
            u' W generic protection rip',
            u' W .*Unrecovered read error - auto reallocate failed',
        ],
        [u'/var/log/syslog', u'/var/log/kern.log'],
        [
            (u'I', u'registered panic notifier', [], []),
            (u'C', u'panic', [], []),
            (u'C', u'Oops', [], []),
            (u'W', u'generic protection rip', [], []),
            (u'W', u'.*Unrecovered read error - auto reallocate failed', [], []),
        ],
    ),
])
def test_read_config_logfiles(mk_logwatch, config_lines, logfiles_files, logfiles_patterns,
                              monkeypatch):
    """checks if the agent plugin parses the configuration appropriately."""
    monkeypatch.setattr(mk_logwatch, 'iter_config_lines', lambda _files: iter(config_lines))

    l_config, __ = mk_logwatch.read_config(None)
    logfiles = l_config[0]

    assert isinstance(logfiles, mk_logwatch.LogfilesConfig)
    assert logfiles.files == logfiles_files
    assert len(logfiles.patterns) == len(logfiles_patterns)
    for actual, expected in zip(logfiles.patterns, logfiles_patterns):
        assert isinstance(actual, type(expected))
        assert actual == expected


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
def test_get_status_filename(mk_logwatch, env_var, istty, statusfile, monkeypatch, mocker):
    """
    May not be executed with pytest option -s set. pytest stdout redirection would colide
    with stdout mock.
    """
    monkeypatch.setenv("REMOTE", env_var)
    monkeypatch.setattr(mk_logwatch, "MK_VARDIR", '/path/to/config')
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


def test_read_status(mk_logwatch, tmp_path):
    # setup
    fake_status_path = tmp_path / "test"
    fake_status_path.mkdir()
    fake_status_file = fake_status_path.joinpath("logwatch.state.another_cluster")
    fake_status_file.write_text(u"""/var/log/messages|7767698|32455445
/var/test/x12134.log|12345|32444355""",
                                encoding="utf-8")
    file_path = str(fake_status_file)

    # execution
    actual_status = mk_logwatch.read_status(file_path)
    # comparing dicts (having unordered keys) is ok
    assert actual_status == {
        '/var/log/messages': (7767698, 32455445),
        '/var/test/x12134.log': (12345, 32444355)
    }


def test_save_status(mk_logwatch, tmp_path):
    fake_status_path = tmp_path / "test"
    fake_status_path.mkdir()
    fake_status_file = fake_status_path.joinpath("logwatch.state.another_cluster")
    fake_status_file.write_text(u"", encoding="utf-8")
    file_path = str(fake_status_file)
    fake_status = {
        '/var/log/messages': (7767698, 32455445),
        '/var/test/x12134.log': (12345, 32444355)
    }
    mk_logwatch.save_status(fake_status, file_path)
    assert sorted(fake_status_file.read_text().splitlines()) == [
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
def test_find_matching_logfiles(mk_logwatch, fake_filesystem, pattern_suffix, file_suffixes):
    fake_fs_path = str(fake_filesystem)
    files = mk_logwatch.find_matching_logfiles(fake_fs_path + pattern_suffix)
    assert sorted(files) == [fake_fs_path + fs for fs in file_suffixes]


def test_ip_in_subnetwork(mk_logwatch):
    assert mk_logwatch.ip_in_subnetwork("192.168.1.1", "192.168.1.0/24") is True
    assert mk_logwatch.ip_in_subnetwork("192.160.1.1", "192.168.1.0/24") is False
    assert mk_logwatch.ip_in_subnetwork("1762:0:0:0:0:B03:1:AF18",
                                        "1762:0000:0000:0000:0000:0000:0000:0000/64") is True
    assert mk_logwatch.ip_in_subnetwork("1760:0:0:0:0:B03:1:AF18",
                                        "1762:0000:0000:0000:0000:0000:0000:0000/64") is False


@pytest.mark.parametrize("buff,encoding,position", [
    ('\xFE\xFF', 'utf_16_be', 2),
    ('\xFF\xFE', 'utf_16', 2),
    ('no encoding in this file!', locale.getpreferredencoding(), 0),
])
def test_log_lines_iter_encoding(mk_logwatch, monkeypatch, buff, encoding, position):
    monkeypatch.setattr(os, 'open', lambda *_args: None)
    monkeypatch.setattr(os, 'read', lambda *_args: buff)
    monkeypatch.setattr(os, 'lseek', lambda *_args: len(buff))
    log_iter = mk_logwatch.LogLinesIter('void')
    assert log_iter._enc == encoding
    assert log_iter.get_position() == position


def test_log_lines_iter(mk_logwatch):
    log_iter = mk_logwatch.LogLinesIter(mk_logwatch.__file__)

    log_iter.set_position(710)
    assert log_iter.get_position() == 710

    line = log_iter.next_line()
    assert isinstance(line, six.text_type)
    assert line == u"# This file is part of Check_MK.\n"
    assert log_iter.get_position() == 743

    log_iter.push_back_line(u'Täke this!')
    assert log_iter.get_position() == 732
    assert log_iter.next_line() == u'Täke this!'

    log_iter.skip_remaining()
    assert log_iter.next_line() is None
    assert log_iter.get_position() == os.stat(mk_logwatch.__file__).st_size


class MockStdout(object):
    def isatty(self):
        return False


@pytest.mark.parametrize(
    "logfile, patterns, opt_raw, status, expected_output",
    [
        (
            __file__,
            [
                ('W', re.compile(u'^[^u]*W.*I match only myself', re.UNICODE), [], []),
                ('I', re.compile(u'.*', re.UNICODE), [], []),
            ],
            {
                'nocontext': True
            },
            {
                __file__: (0, -1)
            },
            [
                u"[[[%s]]]\n" % __file__,
                u"W                 ('W', re.compile(u'^[^u]*W.*I match only myself', re.UNICODE), [], []),\n"
            ],
        ),
        (
            __file__,
            [
                ('W', re.compile(u'I don\'t match anything at all!', re.UNICODE), [], []),
            ],
            {},
            {
                __file__: (0, -1)
            },
            [
                u"[[[%s]]]\n" % __file__,
            ],
        ),
        (
            __file__,
            [
                ('W', re.compile(u'.*', re.UNICODE), [], []),
            ],
            {},
            {},
            [  # nothing for new files
                u"[[[%s]]]\n" % __file__,
            ],
        ),
        (
            __file__,
            [
                ('C', re.compile(u'äöü', re.UNICODE), [], []),
                ('I', re.compile(u'.*', re.UNICODE), [], []),
            ],
            {
                'nocontext': True
            },
            {
                __file__: (0, -1)
            },
            [  # match umlauts
                u"[[[%s]]]\n" % __file__,
                u"C                 ('C', re.compile(u'\xe4\xf6\xfc', re.UNICODE), [], []),\n",
            ],
        ),
        ('locked door', [], {}, {}, [u"[[[locked door:cannotopen]]]\n"]),
    ])
def test_process_logfile(mk_logwatch, monkeypatch, logfile, patterns, opt_raw, status,
                         expected_output):
    opt = mk_logwatch.Options()
    opt.values.update(opt_raw)

    monkeypatch.setattr(sys, 'stdout', MockStdout())
    output = mk_logwatch.process_logfile(logfile, patterns, opt, status)
    assert all(isinstance(item, six.text_type) for item in output)
    assert output == expected_output
    if len(output) > 1:
        assert logfile in status


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
    fake_symlink_file_subdir_level.symlink_to(fake_fs_subdir / "another_symlinked_file.log",
                                              target_is_directory=False)
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
