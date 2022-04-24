#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# pylint: disable=protected-access,redefined-outer-name
from __future__ import print_function

import locale
import os
import re
import sys

import pytest

import agents.plugins.mk_logwatch as mk_logwatch


def text_type():
    if sys.version_info[0] == 2:
        return unicode  # pylint: disable=undefined-variable
    return str


def binary_type():
    if sys.version_info[0] == 2:
        return str  # pylint: disable=undefined-variable
    return bytes


def ensure_text(s, encoding='utf-8', errors='strict'):
    if isinstance(s, binary_type()):
        return s.decode(encoding, errors)
    if isinstance(s, text_type()):
        return s
    raise TypeError("not expecting type '%s'" % type(s))


def ensure_binary(s, encoding='utf-8', errors='strict'):
    if isinstance(s, text_type()):
        return s.encode(encoding, errors)
    if isinstance(s, binary_type()):
        return s
    raise TypeError("not expecting type '%s'" % type(s))


def test_options_defaults():
    opt = mk_logwatch.Options()
    for attribute in ('encoding', 'maxfilesize', 'maxlines', 'maxtime', 'maxlinesize', 'regex',
                      'overflow', 'nocontext', 'maxcontextlines', 'maxoutputsize',
                      'skipconsecutiveduplicated'):
        assert getattr(opt, attribute) == mk_logwatch.Options.DEFAULTS[attribute]


@pytest.mark.parametrize("option_string, key, expected_value", [
    ("encoding=utf8", 'encoding', 'utf8'),
    ("maxfilesize=42", 'maxfilesize', 42),
    ("maxlines=23", 'maxlines', 23),
    ("maxlinesize=13", 'maxlinesize', 13),
    ("maxtime=0.25", 'maxtime', 0.25),
    ("overflow=I", 'overflow', 'I'),
    ("nocontext=tRuE", 'nocontext', True),
    ("nocontext=FALse", 'nocontext', False),
    ("maxcontextlines=17,23", 'maxcontextlines', (17, 23)),
    ("fromstart=1", 'fromstart', True),
    ("fromstart=yEs", 'fromstart', True),
    ("fromstart=0", 'fromstart', False),
    ("fromstart=no", 'fromstart', False),
    ("maxoutputsize=1024", 'maxoutputsize', 1024),
    ("skipconsecutiveduplicated=False", 'skipconsecutiveduplicated', False),
    ("skipconsecutiveduplicated=True", 'skipconsecutiveduplicated', True),
])
def test_options_setter( option_string, key, expected_value):
    opt = mk_logwatch.Options()
    opt.set_opt(option_string)
    actual_value = getattr(opt, key)
    assert isinstance(actual_value, type(expected_value))
    assert actual_value == expected_value


@pytest.mark.parametrize("option_string, expected_pattern, expected_flags", [
    ("regex=foobar", 'foobar', re.UNICODE),
    ("iregex=foobar", 'foobar', re.IGNORECASE | re.UNICODE),
])
def test_options_setter_regex( option_string, expected_pattern, expected_flags):
    opt = mk_logwatch.Options()
    opt.set_opt(option_string)
    assert opt.regex.pattern == expected_pattern
    assert opt.regex.flags == expected_flags


def test_get_config_files( tmpdir):
    fake_config_dir = os.path.join(str(tmpdir), "test")
    os.mkdir(fake_config_dir)

    logwatch_d_dir = os.path.join(fake_config_dir, "logwatch.d")
    os.mkdir(logwatch_d_dir)

    with open(os.path.join(logwatch_d_dir, "custom.cfg"), mode="w"):

        expected = [
        str(os.path.join(fake_config_dir, "logwatch.cfg")),
        str(os.path.join(fake_config_dir, "logwatch.d/custom.cfg"))
        ]

    assert mk_logwatch.get_config_files(str(fake_config_dir)) == expected


def test_iter_config_lines( tmpdir):
    """Fakes a logwatch config file and checks if the agent plugin reads it appropriately"""
    # setup
    fake_config_path = os.path.join(str(tmpdir), "test")
    os.mkdir(fake_config_path)

    fake_config_file = os.path.join(fake_config_path, "logwatch.cfg")
    files = [fake_config_file]

    # No config file at all available, raise in debug mode!
    with pytest.raises(IOError):
        list(mk_logwatch.iter_config_lines(files, debug=True))

    # But it's ok without debug
    list(mk_logwatch.iter_config_lines(files))

    with open(fake_config_file, "wb") as f:
        f.write(u"# this is a comment\nthis is a line   ".encode("utf-8"))

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
def test_read_config_cluster( config_lines, cluster_name, cluster_data, monkeypatch):
    """checks if the agent plugin parses the configuration appropriately."""
    monkeypatch.setattr(mk_logwatch, 'iter_config_lines', lambda _files, **kw: iter(config_lines))

    __, c_config = mk_logwatch.read_config(None)
    cluster = c_config[0]

    assert isinstance(cluster, mk_logwatch.ClusterConfigBlock)
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
            u'"c:\\a path\\with spaces" "d:\\another path\\with spaces"',
            u' I registered panic notifier',
            u' C panic',
            u' C Oops',
            u' W generic protection rip',
            u' W .*Unrecovered read error - auto reallocate failed',
        ],
        [u'c:\\a path\\with spaces', u'd:\\another path\\with spaces'],
        [
            (u'I', u'registered panic notifier', [], []),
            (u'C', u'panic', [], []),
            (u'C', u'Oops', [], []),
            (u'W', u'generic protection rip', [], []),
            (u'W', u'.*Unrecovered read error - auto reallocate failed', [], []),
        ],
    ),
    (
        [
            u'/var/log/äumlaut.log',
            u' W sshd.*Corrupted MAC on input',
        ],
        [u'/var/log/äumlaut.log'],
        [(u'W', u'sshd.*Corrupted MAC on input', [], [])],
    ),
])
def test_read_config_logfiles(config_lines, logfiles_files, logfiles_patterns,
                              monkeypatch):
    """checks if the agent plugin parses the configuration appropriately."""
    monkeypatch.setattr(mk_logwatch, 'iter_config_lines', lambda _files, **kw: iter(config_lines))

    l_config, __ = mk_logwatch.read_config(None)
    logfiles = l_config[0]

    assert isinstance(logfiles, mk_logwatch.PatternConfigBlock)
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
        ("::ffff:192.168.1.2", False,
         "/path/to/config/logwatch.state.my_cluster"),  # tty doesnt matter
    ])
def test_get_status_filename( env_var, istty, statusfile, monkeypatch, mocker):
    """
    May not be executed with pytest option -s set. pytest stdout redirection would colide
    with stdout mock.
    """
    monkeypatch.setenv("REMOTE", env_var)
    monkeypatch.setattr(mk_logwatch, "MK_VARDIR", '/path/to/config')
    stdout_mock = mocker.patch("sys.stdout")
    stdout_mock.isatty.return_value = istty
    fake_config = [
        mk_logwatch.ClusterConfigBlock(
            "my_cluster", ['192.168.1.1', '192.168.1.2', '192.168.1.3', '192.168.1.4']),
        mk_logwatch.ClusterConfigBlock("another_cluster",
                                       ['192.168.1.5', '192.168.1.6', '1762:0:0:0:0:B03:1:AF18'])
    ]

    status_filename = mk_logwatch.get_status_filename(fake_config)
    assert status_filename == statusfile


@pytest.mark.parametrize("state_data, state_dict", [
    ((u"/var/log/messages|7767698|32455445\n"
      u"/var/foo|42\n"
      u"/var/test/x12134.log|12345"), {
          '/var/log/messages': {
              "file": "/var/log/messages",
              "offset": 7767698,
              "inode": 32455445,
          },
          '/var/foo': {
              "file": "/var/foo",
              "offset": 42,
              "inode": -1,
          },
          '/var/test/x12134.log': {
              "file": "/var/test/x12134.log",
              "offset": 12345,
              "inode": -1,
          }
      }),
    ((u"{'file': '/var/log/messages', 'offset': 7767698, 'inode': 32455445}\n"
      u"{'file': '/var/foo', 'offset': 42, 'inode': -1}\n"
      u"{'file': '/var/test/x12134.log', 'offset': 12345, 'inode': -1}\n"), {
          '/var/log/messages': {
              "file": "/var/log/messages",
              "offset": 7767698,
              "inode": 32455445,
          },
          '/var/foo': {
              "file": "/var/foo",
              "offset": 42,
              "inode": -1,
          },
          '/var/test/x12134.log': {
              "file": "/var/test/x12134.log",
              "offset": 12345,
              "inode": -1,
          }
      }),
    (u"{'file': 'I/am/a/byte/\\x89', 'offset': 23, 'inode': 42}\n", {
        'I/am/a/byte/\x89': {
            "file": "I/am/a/byte/\x89",
            "offset": 23,
            "inode": 42,
        },
    }),
    (u"{'file': u'I/am/unicode\\u203d', 'offset': 23, 'inode': 42}\n", {
        u'I/am/unicode\u203d': {
            "file": u"I/am/unicode‽",
            "offset": 23,
            "inode": 42,
        },
    }),
])
def test_state_load( tmpdir, state_data, state_dict):
    # setup for reading
    file_path = os.path.join(str(tmpdir), "logwatch.state.testcase")

    # In case the file is not created yet, read should not raise
    state = mk_logwatch.State(file_path).read()
    assert state._data == {}

    with open(file_path, "wb") as f:
        f.write(state_data.encode("utf-8"))

    # loading and __getitem__
    state = mk_logwatch.State(file_path).read()
    assert state._data == state_dict
    for expected_data in state_dict.values():
        key = expected_data['file']
        assert state.get(key) == expected_data


@pytest.mark.parametrize("state_dict", [
    {
        '/var/log/messages': {
            "file": "/var/log/messages",
            "offset": 7767698,
            "inode": 32455445,
        },
        '/var/foo': {
            "file": "/var/foo",
            "offset": 42,
            "inode": -1,
        },
        '/var/test/x12134.log': {
            "file": "/var/test/x12134.log",
            "offset": 12345,
            "inode": -1,
        }
    },
])
def test_state_write( tmpdir, state_dict):
    # setup for writing
    file_path = os.path.join(str(tmpdir), "logwatch.state.testcase")
    state = mk_logwatch.State(file_path)
    assert not state._data

    # writing
    for data in state_dict.values():
        key = data['file']
        filestate = state.get(key)
        # should work w/o setting 'file'
        filestate['offset'] = data['offset']
        filestate['inode'] = data['inode']
    state.write()

    read_state = mk_logwatch.State(file_path).read()
    assert read_state._data == state_dict


STAR_FILES = [
    (b"/file.log", u"/file.log"),
    (b"/hard_link_to_file.log", u"/hard_link_to_file.log"),
    (b"/hard_linked_file.log", u"/hard_linked_file.log"),
    (b"/oh-no-\x89", u"/oh-no-\uFFFD"),  # unicode replace char
    (b"/symlink_to_file.log", u"/symlink_to_file.log"),
    (b"/wat\xe2\x80\xbd", u"/wat\u203D"),  # actual interobang
]


@pytest.mark.parametrize("pattern_suffix, file_suffixes", [
    (u"/*", STAR_FILES),
    (u"/**", STAR_FILES),
    (u"/subdir/*", [(b"/subdir/symlink_to_file.log", u"/subdir/symlink_to_file.log")]),
    (u"/symlink_to_dir/*", [
        (b"/symlink_to_dir/yet_another_file.log", u"/symlink_to_dir/yet_another_file.log")
    ]),
])
def test_find_matching_logfiles( fake_filesystem, pattern_suffix, file_suffixes):
    fake_fs_path_u = ensure_text(fake_filesystem)
    fake_fs_path_b = bytes(fake_filesystem, "utf-8")
    files = mk_logwatch.find_matching_logfiles(fake_fs_path_u + pattern_suffix)
    fake_fs_file_suffixes = [
        (fake_fs_path_b + path[0], fake_fs_path_u + path[1]) for path in file_suffixes
    ]

    for actual, expected in zip(sorted(files), fake_fs_file_suffixes):
        assert isinstance(actual[0], type(expected[0]))
        assert actual[0].endswith(expected[0])

        assert isinstance(actual[1], text_type())
        assert actual[1].startswith(fake_fs_path_u)
        assert actual[1] == expected[1]


def test_ip_in_subnetwork():
    assert mk_logwatch.ip_in_subnetwork("192.168.1.1", "192.168.1.0/24") is True
    assert mk_logwatch.ip_in_subnetwork("192.160.1.1", "192.168.1.0/24") is False
    assert mk_logwatch.ip_in_subnetwork("1762:0:0:0:0:B03:1:AF18",
                                        "1762:0000:0000:0000:0000:0000:0000:0000/64") is True
    assert mk_logwatch.ip_in_subnetwork("1760:0:0:0:0:B03:1:AF18",
                                        "1762:0000:0000:0000:0000:0000:0000:0000/64") is False


@pytest.mark.parametrize("buff,encoding,position", [
    (b'\xFE\xFF', 'utf_16_be', 2),
    (b'\xFF\xFE', 'utf_16', 2),
    (b'no encoding in this file!', locale.getpreferredencoding(), 0),
])
def test_log_lines_iter_encoding(monkeypatch, buff, encoding, position):
    monkeypatch.setattr(os, 'open', lambda *_args: None)
    monkeypatch.setattr(os, 'close', lambda *_args: None)
    monkeypatch.setattr(os, 'read', lambda *_args: buff)
    monkeypatch.setattr(os, 'lseek', lambda *_args: len(buff))
    with mk_logwatch.LogLinesIter('void', None) as log_iter:
        assert log_iter._enc == encoding
        assert log_iter.get_position() == position


def test_log_lines_iter():
    txt_file = mk_logwatch.__file__.rstrip('c')
    with mk_logwatch.LogLinesIter(txt_file, None) as log_iter:
        log_iter.set_position(122)
        assert log_iter.get_position() == 122

        line = log_iter.next_line()
        assert isinstance(line, text_type())
        assert line == u"# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and\n"
        assert log_iter.get_position() == 207

        log_iter.push_back_line(u'Täke this!')
        assert log_iter.get_position() == 196
        assert log_iter.next_line() == u'Täke this!'

        log_iter.skip_remaining()
        assert log_iter.next_line() is None
        assert log_iter.get_position() == os.stat(txt_file).st_size


@pytest.mark.parametrize(
    "use_specific_encoding,lines,expected_result",
    [
        # UTF-8 encoding works by default
        (None, [
            b"abc1",
            u"äbc2".encode("utf-8"),
            b"abc3",
        ], [
            u"abc1\n",
            u"äbc2\n",
            u"abc3\n",
        ]),
        # Replace characters that can not be decoded
        (None, [
            b"abc1",
            u"äbc2".encode("latin-1"),
            b"abc3",
        ], [
            u"abc1\n",
            u"\ufffdbc2\n",
            u"abc3\n",
        ]),
        # Set custom encoding
        ("latin-1", [
            b"abc1",
            u"äbc2".encode("latin-1"),
            b"abc3",
        ], [
            u"abc1\n",
            u"äbc2\n",
            u"abc3\n",
        ]),
    ])
def test_non_ascii_line_processing(tmpdir, monkeypatch, use_specific_encoding, lines,
        expected_result):
    # Write test logfile first
    log_path = os.path.join(str(tmpdir), "testlog")
    with open(log_path, "wb") as f:
        f.write(b"\n".join(lines) + b"\n")

    # Now test processing
    with mk_logwatch.LogLinesIter(log_path, None) as log_iter:
        if use_specific_encoding:
            log_iter._enc = use_specific_encoding

        result = []
        while True:
            l = log_iter.next_line()
            if l is None:
                break
            result.append(l)

        assert result == expected_result


class MockStdout(object):  # pylint: disable=useless-object-inheritance
    def isatty(self):
        return False


@pytest.mark.parametrize(
    "logfile, patterns, opt_raw, state, expected_output",
    [
        (
            __file__,
            [
                ('W', re.compile(u'^[^u]*W.*I mätch önly mysélf 🧚', re.UNICODE), [], []),
                ('I', re.compile(u'.*', re.UNICODE), [], []),
            ],
            {
                'nocontext': True
            },
            {
                'offset': 0,
            },
            [
                u"[[[%s]]]\n" % __file__,
                u"W                 ('W', re.compile(u'^[^u]*W.*I m\xe4tch \xf6nly mys\xe9lf \U0001f9da', re.UNICODE), [], []),\n"
            ],
        ),
        (
            __file__,
            [
                ('W', re.compile(u'I don\'t match anything at all!', re.UNICODE), [], []),
            ],
            {},
            {
                'offset': 0,
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
                ('C', re.compile(u'🐉', re.UNICODE), [], []),
                ('I', re.compile(u'.*', re.UNICODE), [], []),
            ],
            {
                'nocontext': True
            },
            {
                'offset': 0,
            },
            [
                u"[[[%s]]]\n" % __file__,
                u"C                 ('C', re.compile(u'\U0001f409', re.UNICODE), [], []),\n",
            ],
        ),
        ('locked door', [], {}, {}, [u"[[[locked door:cannotopen]]]\n"]),
    ])
def test_process_logfile(monkeypatch, logfile, patterns, opt_raw, state,
                         expected_output):

    section = mk_logwatch.LogfileSection((logfile, logfile))
    section.options.values.update(opt_raw)
    section._compiled_patterns = patterns

    monkeypatch.setattr(sys, 'stdout', MockStdout())
    header, warning_and_errors = mk_logwatch.process_logfile(section, state, False)
    output = [header] + warning_and_errors
    assert output == expected_output
    if len(output) > 1:
        assert isinstance(state['offset'], int)
        assert state['offset'] >= 15000  # about the size of this file


@pytest.mark.parametrize("input_lines, before, after, expected_output",
                         [([], 2, 3, []),
                          (["0", "1", "2", "C 3", "4", "5", "6", "7", "8", "9", "W 10"
                           ], 2, 3, ["1", "2", "C 3", "4", "5", "6", "8", "9", "W 10"]),
                          (["C 0", "1", "2"], 12, 17, ["C 0", "1", "2"])])
def test_filter_maxcontextlines( input_lines, before, after, expected_output):

    assert expected_output == list(mk_logwatch._filter_maxcontextlines(input_lines, before, after))


@pytest.mark.parametrize("input_lines, nocontext, expected_output",
                         [([], False, []),
                          ([], True, []),
                          (["ln", "ln2", "ln2", "ln2", "ln3", "ln3", "ln"],
                           True,
                           ["ln", "ln2", "ln3", "ln"]),
                          (["ln", "ln2", "ln2", "ln2", "ln3", "ln3", "ln"],
                           False,
                           ["ln", "ln2", ". [the above message was repeated 2 times]\n",
                           "ln3", ". [the above message was repeated 1 times]\n", "ln"]),
                           (["ln", "ln"],
                            False,
                            ["ln", ". [the above message was repeated 1 times]\n"]),
                           ((str(i) for i in range(3)),
                           False,
                           ["0", "1", "2"])])
def test_filter_consecutive_duplicates( input_lines, nocontext, expected_output):
    assert expected_output == list(
        mk_logwatch._filter_consecutive_duplicates(input_lines, nocontext)
    )


@pytest.fixture
def fake_filesystem(tmpdir):
    root = [
        # name     | type  | content/target
        ("file.log", "file", None),
        (b"wat\xe2\x80\xbd", "file", None),
        (b"oh-no-\x89", "file", None),
        ("symlink_to_file.log", "symlink", "symlinked_file.log"),
        ("subdir", "dir", [
            ("symlink_to_file.log", "symlink", "another_symlinked_file.log"),
            ("subsubdir", "dir", [
                ("yaf.log", "file", None),
            ]),
        ]),
        ("symlink_to_dir", "symlink", "symlinked_dir"),
        ("symlinked_dir", "dir", [
            ("yet_another_file.log", "file", None),
        ]),
        ("hard_linked_file.log", "file", None),
        ("hard_link_to_file.log", "hardlink", "hard_linked_file.log"),
    ]

    def create_recursively(dirpath, name, type_, value):
        obj_path = os.path.join(ensure_binary(dirpath), ensure_binary(name))

        if type_ == "file":
            with open(obj_path, 'w'):
                pass
            return

        if type_ == "dir":
            os.mkdir(obj_path)
            for spec in value:
                create_recursively(obj_path, *spec)
            return

        source = os.path.join(ensure_binary(dirpath), ensure_binary(value))
        if type_ == "symlink":
            os.symlink(source, obj_path)
        else:
            os.link(source, obj_path)

    create_recursively(str(tmpdir), "root", "dir", root)

    return os.path.join(str(tmpdir), "root")
