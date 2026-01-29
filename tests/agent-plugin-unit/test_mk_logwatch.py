#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="unreachable"
# ruff: noqa: RUF100
# ruff: noqa: I001

# fmt: off


import locale
import os
import re
import sys
from typing import Iterable, Mapping, Optional, Sequence, Tuple, Union

import agents.plugins.mk_logwatch as lw
import pytest
from _pytest.monkeypatch import MonkeyPatch

unicode = str

_SEP = os.sep.encode()
_SEP_U = _SEP.decode("utf-8")


def _oh_no():
    return "oh-no-П" if os.name == "nt" else b"oh-no-\x89"


def _wat_bad():
    return "watПик" if os.name == "nt" else b"wat\xe2\x80\xbd"


# NOTE: Linux could use bytes and str paths, Windows only str
# we need to have kind of API to provide different types for different OS's
_OH_NO = _oh_no()
_WAT_BAD = _wat_bad()
if os.name == "nt":
    _OH_NO_STR = _OH_NO
    _WAT_BAD_STR = _WAT_BAD
    _OH_NO_BYTES = _OH_NO.encode()
    _WAT_BAD_BYTES = _WAT_BAD.encode()
else:
    _OH_NO_STR = "oh-no-\\x89"  # backslash replace
    _WAT_BAD_STR = "wat\u203D"  # actual interrobang
    _OH_NO_BYTES = _OH_NO
    _WAT_BAD_BYTES = _WAT_BAD

_TEST_CONFIG = """

GLOBAL OPTIONS
 ignore invalid options
 retention_period 42

not a cluster line

CLUSTER duck
 192.168.1.1
 192.168.1.2

CLUSTER empty

/var/log/messages
 C Fail event detected on md device
 I mdadm.*: Rebuild.*event detected
 W mdadm\\[
 W ata.*hard resetting link
 W ata.*soft reset failed (.*FIS failed)
 W device-mapper: thin:.*reached low water mark
 C device-mapper: thin:.*no free space
 C Error: (.*)

/var/log/auth.log
 W sshd.*Corrupted MAC on input

"c:\\a path\\with spaces" "d:\\another path\\with spaces"
 I registered panic notifier
 C panic
 C Oops
 W generic protection rip
 W .*Unrecovered read error - auto reallocate failed

/var/log/äumlaut.log
 W sshd.*Corrupted MAC on input

/var/log/test_append.log
 C .*Error.*
 A .*more information.*
 A .*also important.*
"""


@pytest.fixture(name="parsed_config", scope="module")
def _get_parsed_config():
    # type: () -> tuple[lw.GlobalOptions, Sequence[lw.PatternConfigBlock], Sequence[lw.ClusterConfigBlock]]
    return lw.read_config(_TEST_CONFIG.split("\n"), files=[], debug=False)


def text_type():
    return unicode if sys.version_info[0] == 2 else str


def binary_type():
    return str if sys.version_info[0] == 2 else bytes


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


def test_options_defaults() -> None:
    opt = lw.Options()
    for attribute in (
        'encoding',
        'maxfilesize',
        'maxlines',
        'maxtime',
        'maxlinesize',
        'regex',
        'overflow',
        'nocontext',
        'maxcontextlines',
        'maxoutputsize',
        'skipconsecutiveduplicated',
    ):
        assert getattr(opt, attribute) == lw.Options.DEFAULTS[attribute]


@pytest.mark.parametrize(
    "option_string, key, expected_value",
    [
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
    ],
)
def test_options_setter(option_string: str, key: str, expected_value: object) -> None:
    opt = lw.Options()
    opt.set_opt(option_string)
    actual_value = getattr(opt, key)
    assert isinstance(actual_value, type(expected_value))
    assert actual_value == expected_value


@pytest.mark.parametrize(
    "option_string, expected_pattern, expected_flags",
    [
        ("regex=foobar", 'foobar', re.UNICODE),
        ("iregex=foobar", 'foobar', re.IGNORECASE | re.UNICODE),
    ],
)
def test_options_setter_regex(
    option_string: str, expected_pattern: str, expected_flags: int
) -> None:
    opt = lw.Options()
    opt.set_opt(option_string)
    assert opt.regex.pattern == expected_pattern
    assert opt.regex.flags == expected_flags


def test_get_config_files(tmpdir: Union[str, bytes]) -> None:
    fake_config_dir = os.path.join(str(tmpdir), "test")
    os.mkdir(fake_config_dir)

    logwatch_d_dir = os.path.join(fake_config_dir, "logwatch.d")
    os.mkdir(logwatch_d_dir)

    with open(os.path.join(logwatch_d_dir, "custom.cfg"), mode="w"):
        expected = [
            str(os.path.join(fake_config_dir, "logwatch.cfg")),
            str(os.path.join(fake_config_dir, "logwatch.d", "custom.cfg")),
        ]

    assert lw.get_config_files(str(fake_config_dir)) == expected


def test_raise_no_config_lines():
    # type: () -> None

    # No config file at all available, raise in debug mode!
    with pytest.raises(IOError):
        lw.read_config([], files=[], debug=True)

    # But it's ok without debug
    lw.read_config([], files=[], debug=False)


def test_read_global_options(parsed_config):
    # type: (tuple[lw.GlobalOptions, Sequence[lw.PatternConfigBlock], Sequence[lw.ClusterConfigBlock]]) -> None
    global_options, _logfile_config, _cluster_config = parsed_config

    assert isinstance(global_options, lw.GlobalOptions)
    assert global_options.retention_period == 42


def test_read_config_cluster(parsed_config):
    # type: (tuple[lw.GlobalOptions, Sequence[lw.PatternConfigBlock], Sequence[lw.ClusterConfigBlock]]) -> None
    """checks if the agent plugin parses the configuration appropriately."""
    _global_options, _logfile_config, c_config = parsed_config

    assert len(c_config) == 2
    assert isinstance(c_config[0], lw.ClusterConfigBlock)

    assert c_config[0].name == "duck"
    assert c_config[0].ips_or_subnets == ['192.168.1.1', '192.168.1.2']

    assert c_config[1].name == "empty"
    assert not c_config[1].ips_or_subnets


def test_read_config_logfiles(parsed_config):
    # type: (tuple[lw.GlobalOptions, Sequence[lw.PatternConfigBlock], Sequence[lw.ClusterConfigBlock]]) -> None
    """checks if the agent plugin parses the configuration appropriately."""

    _global_options, l_config, _cluster_config = parsed_config

    assert len(l_config) == 6
    assert all(isinstance(lf, lw.PatternConfigBlock) for lf in l_config)

    assert l_config[0].files == ['not', 'a', 'cluster', 'line']
    assert not l_config[0].patterns

    assert l_config[1].files == ['{}'.format(os.path.join(os.sep, "var", "log", "messages"))]
    assert l_config[1].patterns == [
        ('C', 'Fail event detected on md device', [], []),
        ('I', 'mdadm.*: Rebuild.*event detected', [], []),
        ('W', 'mdadm\\[', [], []),
        ('W', 'ata.*hard resetting link', [], []),
        ('W', 'ata.*soft reset failed (.*FIS failed)', [], []),
        ('W', 'device-mapper: thin:.*reached low water mark', [], []),
        ('C', 'device-mapper: thin:.*no free space', [], []),
        ('C', 'Error: (.*)', [], []),
    ]

    assert l_config[2].files == ['{}'.format(os.path.join(os.sep, "var", "log", "auth.log"))]
    assert l_config[2].patterns == [('W', 'sshd.*Corrupted MAC on input', [], [])]

    assert l_config[3].files == ['c:\\a path\\with spaces', 'd:\\another path\\with spaces']
    assert l_config[3].patterns == [
        ('I', 'registered panic notifier', [], []),
        ('C', 'panic', [], []),
        ('C', 'Oops', [], []),
        ('W', 'generic protection rip', [], []),
        ('W', '.*Unrecovered read error - auto reallocate failed', [], []),
    ]

    assert l_config[4].files == ['{}'.format(os.path.join(_SEP_U, "var", "log", "äumlaut.log"))]
    assert l_config[4].patterns == [('W', 'sshd.*Corrupted MAC on input', [], [])]

    assert l_config[5].files == [
        '{}'.format(os.path.join(os.sep, "var", "log", "test_append.log"))
    ]
    assert l_config[5].patterns == [
        ('C', '.*Error.*', ['.*more information.*', '.*also important.*'], [])
    ]


@pytest.mark.parametrize(
    "env_var, expected_status_filename",
    [
        ("192.168.2.1", os.path.join("/path/to/config", "logwatch.state.192.168.2.1")),
        (
            "::ffff:192.168.2.1",
            os.path.join("/path/to/config", "logwatch.state.__ffff_192.168.2.1"),
        ),
        ("192.168.1.4", os.path.join("/path/to/config", "logwatch.state.my_cluster")),
        (
            "1262:0:0:0:0:B03:1:AF18",
            os.path.join("/path/to/config", "logwatch.state.1262_0_0_0_0_B03_1_AF18"),
        ),
        (
            "1762:0:0:0:0:B03:1:AF18",
            os.path.join("/path/to/config", "logwatch.state.another_cluster"),
        ),
        ("local", os.path.join("/path/to/config", "logwatch.state.local")),
        ("::ffff:192.168.1.2", os.path.join("/path/to/config", "logwatch.state.my_cluster")),
    ],
)
def test_get_status_filename(
    env_var: str, expected_status_filename: str, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(lw, "MK_VARDIR", '/path/to/config')
    fake_config = [
        lw.ClusterConfigBlock(
            "my_cluster",
            ['192.168.1.1', '192.168.1.2', '192.168.1.3', '192.168.1.4'],
        ),
        lw.ClusterConfigBlock(
            "another_cluster",
            ['192.168.1.5', '192.168.1.6', '1762:0:0:0:0:B03:1:AF18'],
        ),
    ]

    assert lw.get_status_filename(fake_config, env_var) == expected_status_filename


@pytest.mark.parametrize(
    "state_data, state_dict",
    [
        (
            (
                "/var/log/messages|7767698|32455445\n"
                "/var/foo|42\n"
                "/var/test/x12134.log|12345"
            ),
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
                },
            },
        ),
        (
            (
                "{'file': '/var/log/messages', 'offset': 7767698, 'inode': 32455445}\n"
                "{'file': '/var/foo', 'offset': 42, 'inode': -1}\n"
                "{'file': '/var/test/x12134.log', 'offset': 12345, 'inode': -1}\n"
            ),
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
                },
            },
        ),
        (
            "{'file': 'I/am/a/byte/\\x89', 'offset': 23, 'inode': 42}\n",
            {
                'I/am/a/byte/\x89': {
                    "file": "I/am/a/byte/\x89",
                    "offset": 23,
                    "inode": 42,
                },
            },
        ),
        (
            "{'file': u'I/am/unicode\\u203d', 'offset': 23, 'inode': 42}\n",
            {
                'I/am/unicode\u203d': {
                    "file": "I/am/unicode‽",
                    "offset": 23,
                    "inode": 42,
                },
            },
        ),
    ],
)
def test_state_load(
    tmpdir: Union[str, bytes], state_data: str, state_dict: Mapping[str, Mapping[str, object]]
) -> None:
    # setup for reading
    file_path = os.path.join(str(tmpdir), "logwatch.state.testcase")

    # In case the file is not created yet, read should not raise
    state = lw.State(file_path).read()
    assert state._data == {}

    with open(file_path, "wb") as f:
        f.write(state_data.encode("utf-8"))

    # loading and __getitem__
    state = lw.State(file_path).read()
    assert state._data == state_dict
    for expected_data in state_dict.values():
        key = expected_data['file']
        assert isinstance(key, (unicode, str))
        assert state.get(key) == expected_data


@pytest.mark.parametrize(
    "state_dict",
    [
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
            },
        },
    ],
)
def test_state_write(
    tmpdir: Union[str, bytes], state_dict: Mapping[str, Mapping[str, object]]
) -> None:
    # setup for writing
    file_path = os.path.join(str(tmpdir), "logwatch.state.testcase")
    state = lw.State(file_path)
    assert not state._data

    # writing
    for data in state_dict.values():
        key = data['file']
        assert isinstance(key, str)
        filestate = state.get(key)
        # should work w/o setting 'file'
        filestate['offset'] = data['offset']
        filestate['inode'] = data['inode']
    state.write()

    read_state = lw.State(file_path).read()
    assert read_state._data == state_dict


STAR_FILES = [
    (b"file.log", "file.log"),
    (b"hard_link_to_file.log", "hard_link_to_file.log"),
    (b"hard_linked_file.log", "hard_linked_file.log"),
    (_OH_NO_BYTES, _OH_NO_STR),
    (b"symlink_to_file.log", "symlink_to_file.log"),
    (_WAT_BAD_BYTES, _WAT_BAD_STR),
]


def _fix_for_os(pairs):
    # type: (Sequence[tuple[bytes, str]])  -> list[tuple[bytes, str]]
    def symlink_in_windows(s: str) -> bool:
        return os.name == "nt" and "symlink" in s

    return [(os.sep.encode() + b, os.sep + s) for b, s in pairs if not symlink_in_windows(s)]


def _cvt(path):
    return os.path.normpath(path.decode("utf-8", errors="replace")) if os.name == "nt" else path


# NOTE: helper for mypy
def _end_with(actual: Union[str, bytes], *, expected: bytes) -> bool:
    if isinstance(actual, str):
        assert isinstance(expected, str)
        return actual.endswith(expected)
    assert isinstance(expected, bytes)
    return actual.endswith(expected)


@pytest.mark.parametrize(
    "pattern_suffix, file_suffixes",
    [
        ("/*", _fix_for_os(STAR_FILES)),
        ("/**", _fix_for_os(STAR_FILES)),
        ("/subdir/*", [(b"/subdir/symlink_to_file.log", "/subdir/symlink_to_file.log")]),
        (
            "/symlink_to_dir/*",
            [(b"/symlink_to_dir/yet_another_file.log", "/symlink_to_dir/yet_another_file.log")],
        ),
    ],
)
def test_find_matching_logfiles(
    fake_filesystem: str, pattern_suffix: unicode, file_suffixes: Iterable[Tuple[bytes, unicode]]
) -> None:
    fake_fs_path_u = ensure_text(fake_filesystem)
    fake_fs_path_b = bytes(fake_filesystem, "utf-8")
    files = lw.find_matching_logfiles(fake_fs_path_u + pattern_suffix)
    fake_fs_file_suffixes = [
        (fake_fs_path_b + path[0], fake_fs_path_u + path[1]) for path in file_suffixes
    ]

    for actual, expected in zip(sorted(files), fake_fs_file_suffixes):
        assert _end_with(actual[0], expected=_cvt(expected[0]))

        assert isinstance(actual[1], text_type())
        assert actual[1].startswith(fake_fs_path_u)
        assert actual[1] == expected[1]


def test_ip_in_subnetwork() -> None:
    assert lw.ip_in_subnetwork("192.168.1.1", "192.168.1.0/24") is True
    assert lw.ip_in_subnetwork("192.160.1.1", "192.168.1.0/24") is False
    assert (
        lw.ip_in_subnetwork("1762:0:0:0:0:B03:1:AF18", "1762:0000:0000:0000:0000:0000:0000:0000/64")
        is True
    )
    assert (
        lw.ip_in_subnetwork("1760:0:0:0:0:B03:1:AF18", "1762:0000:0000:0000:0000:0000:0000:0000/64")
        is False
    )


@pytest.mark.parametrize(
    "buff,encoding,position",
    [
        (b'\xFE\xFF', 'utf_16_be', 2),
        (b'\xFF\xFE', 'utf_16', 2),
        (b'no encoding in this file!', locale.getpreferredencoding(), 0),
    ],
)
def test_log_lines_iter_encoding(
    monkeypatch: MonkeyPatch, buff: bytes, encoding: str, position: int
) -> None:
    monkeypatch.setattr(os, 'open', lambda *_args: None)
    monkeypatch.setattr(os, 'close', lambda *_args: None)
    monkeypatch.setattr(os, 'read', lambda *_args: buff)
    monkeypatch.setattr(os, 'lseek', lambda *_args: len(buff))
    with lw.LogLinesIter('void', None) as log_iter:
        assert log_iter._enc == encoding
        assert log_iter.get_position() == position


def test_log_lines_iter() -> None:
    txt_file = _path_to_testfile("test_data_for_mk_logwatch.txt")
    with lw.LogLinesIter(txt_file, "utf-8" if os.name == "nt" else None) as log_iter:
        log_iter.set_position(99)
        assert log_iter.get_position() == 99

        line = log_iter.next_line()
        assert isinstance(line, text_type())
        assert (
            line
            == "# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and\n"
        )
        assert log_iter.get_position() == 184

        log_iter.push_back_line('Täke this!')
        assert log_iter.get_position() == 173
        assert log_iter.next_line() == 'Täke this!'

        log_iter.skip_remaining()
        assert log_iter.next_line() is None
        assert log_iter.get_position() == os.stat(txt_file).st_size


def _latin_1_encoding():
    return "cp1252" if os.name == "nt" else "latin-1"


@pytest.mark.parametrize(
    "use_specific_encoding,lines,expected_result",
    [
        # UTF-8 encoding works by default in Linux and must be selected in Windows
        (
            "utf-8" if os.name == "nt" else None,
            [
                b"abc1",
                "äbc2".encode(),
                b"abc3",
            ],
            [
                "abc1\n",
                "äbc2\n",
                "abc3\n",
            ],
        ),
        # Replace characters that can not be decoded
        (
            "utf-8" if os.name == "nt" else None,
            [
                b"abc1",
                "äbc2".encode(_latin_1_encoding()),
                b"abc3",
            ],
            [
                "abc1\n",
                "\ufffdbc2\n",
                "abc3\n",
            ],
        ),
        # Set custom encoding
        (
            _latin_1_encoding(),
            [
                b"abc1",
                "äbc2".encode(_latin_1_encoding()),
                b"abc3",
            ],
            [
                "abc1\n",
                "äbc2\n",
                "abc3\n",
            ],
        ),
    ],
)
def test_non_ascii_line_processing(
    tmpdir, monkeypatch, use_specific_encoding, lines, expected_result
):
    # Write test logfile first
    log_path = os.path.join(str(tmpdir), "testlog")
    with open(log_path, "wb") as f:
        f.write(b"\n".join(lines) + b"\n")

    # Now test processing
    with lw.LogLinesIter(log_path, None) as log_iter:
        if use_specific_encoding:
            log_iter._enc = use_specific_encoding

        result = []
        while True:
            l = log_iter.next_line()
            if l is None:
                break
            result.append(l)

        assert result == expected_result


def _linux_dataset_path(filename):
    return os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "datasets",
            "mk_logwatch",
            filename,
        )
    )


def _path_to_testfile(filename):
    return _linux_dataset_path(filename)


class MockStdout:
    def isatty(self):
        return False


@pytest.mark.parametrize(
    "logfile, patterns, opt_raw, state, expected_output",
    [
        (
            __file__,
            [
                ('W', re.compile('^[^u]*W.*I mätch önly mysélf 🧚', re.UNICODE), [], []),
                ('I', re.compile('.*', re.UNICODE), [], []),
            ],
            {'nocontext': True},
            {
                'offset': 0,
            },
            [
                "[[[%s]]]\n" % __file__,
                "W                 ('W', re.compile('^[^u]*W.*I m\xe4tch \xf6nly mys\xe9lf \U0001f9da', re.UNICODE), [], []),\n",
            ],
        ),
        (
            __file__,
            [
                ('W', re.compile('I don\'t match anything at all!', re.UNICODE), [], []),
            ],
            {},
            {
                'offset': 0,
            },
            [
                "[[[%s]]]\n" % __file__,
            ],
        ),
        (
            __file__,
            [
                ('W', re.compile('.*', re.UNICODE), [], []),
            ],
            {},
            {},
            [  # nothing for new files
                "[[[%s]]]\n" % __file__,
            ],
        ),
        (
            __file__,
            [
                ('C', re.compile('🐉', re.UNICODE), [], []),
                ('I', re.compile('.*', re.UNICODE), [], []),
            ],
            {'nocontext': True},
            {
                'offset': 0,
            },
            [
                "[[[%s]]]\n" % __file__,
                "C                 ('C', re.compile('\U0001f409', re.UNICODE), [], []),\n",
            ],
        ),
        ('locked door', [], {}, {}, ["[[[locked door:cannotopen]]]\n"]),
        (
            _path_to_testfile("test_append.log"),
            [
                (
                    'C',
                    re.compile('.*Error.*'),
                    [
                        re.compile('.*more information.*'),
                        re.compile('.*also important.*'),
                    ],
                    [],
                ),
            ],
            {'nocontext': True},
            {
                'offset': 0,
            },
            [
                '[[[%s]]]\n' % _path_to_testfile("test_append.log"),
                'C Error: Everything down!\x01more information: very useful\x01also important: please inform admins\n',
            ],
        ),
    ],
)
def test_process_logfile(monkeypatch, logfile, patterns, opt_raw, state, expected_output):

    section = lw.LogfileSection((logfile, logfile))
    section.options.values.update(opt_raw)
    # in Windows default encoding, i.e., None means cp1252 and we cant change default easy
    # we want to test utf-8 file, so please
    if os.name == "nt":
        section.options.values.update({"encoding": "utf-8"})
    section._compiled_patterns = patterns

    monkeypatch.setattr(sys, 'stdout', MockStdout())
    header, warning_and_errors = lw.process_logfile(section, state, False)
    output = [header] + warning_and_errors
    assert output == expected_output
    if len(output) > 1:
        assert isinstance(state['offset'], int)
        if logfile == __file__:
            assert state['offset'] >= 15000  # about the size of this file


@pytest.mark.parametrize(
    "input_lines, before, after, expected_output",
    [
        ([], 2, 3, []),
        (
            ["0", "1", "2", "C 3", "4", "5", "6", "7", "8", "9", "W 10"],
            2,
            3,
            ["1", "2", "C 3", "4", "5", "6", "8", "9", "W 10"],
        ),
        (["C 0", "1", "2"], 12, 17, ["C 0", "1", "2"]),
    ],
)
def test_filter_maxcontextlines(
    input_lines: Sequence[str], before: int, after: int, expected_output: Sequence[str]
) -> None:
    assert expected_output == list(lw._filter_maxcontextlines(input_lines, before, after))


@pytest.mark.parametrize(
    "input_lines, nocontext, expected_output",
    [
        ([], False, []),
        ([], True, []),
        (["ln", "ln2", "ln2", "ln2", "ln3", "ln3", "ln"], True, ["ln", "ln2", "ln3", "ln"]),
        (
            ["ln", "ln2", "ln2", "ln2", "ln3", "ln3", "ln"],
            False,
            [
                "ln",
                "ln2",
                ". [the above message was repeated 2 times]\n",
                "ln3",
                ". [the above message was repeated 1 times]\n",
                "ln",
            ],
        ),
        (["ln", "ln"], False, ["ln", ". [the above message was repeated 1 times]\n"]),
        ((str(i) for i in range(3)), False, ["0", "1", "2"]),
    ],
)
def test_filter_consecutive_duplicates(
    input_lines: Sequence[str], nocontext: Optional[bool], expected_output: Sequence[str]
) -> None:
    assert expected_output == list(lw._filter_consecutive_duplicates(input_lines, nocontext))


@pytest.fixture
def fake_filesystem(tmpdir):
    root = [
        # name     | type  | content/target
        ("file.log", "file", None),
        (_WAT_BAD, "file", None),
        (_OH_NO, "file", None),
        ("symlink_to_file.log", "symlink", "symlinked_file.log"),
        (
            "subdir",
            "dir",
            [
                ("symlink_to_file.log", "symlink", "another_symlinked_file.log"),
                (
                    "subsubdir",
                    "dir",
                    [
                        ("yaf.log", "file", None),
                    ],
                ),
            ],
        ),
        ("symlink_to_dir", "symlink", "symlinked_dir"),
        (
            "symlinked_dir",
            "dir",
            [
                ("yet_another_file.log", "file", None),
            ],
        ),
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
            if os.name != "nt":
                os.symlink(source, obj_path)
        else:
            os.link(source, obj_path)

    create_recursively(str(tmpdir), "root", "dir", root)

    return os.path.join(str(tmpdir), "root")


def test_process_batches(tmpdir, mocker):
    mocker.patch.object(lw, "MK_VARDIR", str(tmpdir))
    lw.process_batches(
        [lw.ensure_text_type(l) for l in ["line1", "line2"]],
        "batch_id",
        "::remote",
        123,
        456,
    )
    assert os.path.isfile(
        os.path.join(
            str(tmpdir),
            "logwatch-batches",
            "__remote" if os.name == "nt" else "::remote",
            "logwatch-batch-file-batch_id",
        )
    )


def _get_file_info(tmp_path, file_name):
    return lw.get_file_info(os.path.join(str(tmp_path), "root", file_name))


def test_get_uniq_id_one_file(fake_filesystem, tmpdir):
    file_id, sz = _get_file_info(tmpdir, "file.log")
    assert file_id > 1
    assert sz == 0
    assert (file_id, sz) == _get_file_info(tmpdir, "file.log")


def test_get_uniq_id_with_hard_link(fake_filesystem, tmpdir):
    info = [
        _get_file_info(tmpdir, f)
        for f in ("file.log", "hard_linked_file.log", "hard_link_to_file.log")
    ]
    assert {s for (_, s) in info} == {0}
    assert len({i for (i, _) in info}) == 2
    assert info[0][0] != info[1][0]
    assert info[1][0] == info[2][0]


def test_main(tmpdir, mocker):
    mocker.patch.object(lw, "MK_VARDIR", str(tmpdir))
    lw.main()
