#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""mk_logwatch
This is the Check_MK Agent plugin. If configured it will be called by the
agent without arguments.

Options:
    -d               Debug mode: Colored output, no saving of status.
    -c CONFIG_FILE   Use this config file
    -h               Show help.
    --no_state       No state
    -v               Verbose output for debugging purposes (no debug mode).

You should find an example configuration file at
'../cfg_examples/logwatch.cfg' relative to this file.
"""

# this file has to work with both Python 2 and 3
# pylint: disable=super-with-arguments

from __future__ import with_statement

__version__ = "2.1.0"

import sys

if sys.version_info < (2, 6):
    sys.stderr.write("ERROR: Python 2.5 is not supported. Please use Python 2.6 or newer.\n")
    sys.exit(1)

import ast
import binascii
import glob
import io
import locale
import logging
import os
import platform
import re
import shlex
import shutil
import socket
import time

# For Python 3 sys.stdout creates \r\n as newline for Windows.
# Checkmk can't handle this therefore we rewrite sys.stdout to a new_stdout function.
# If you want to use the old behaviour just use old_stdout.
if sys.version_info[0] >= 3:
    new_stdout = io.TextIOWrapper(
        sys.stdout.buffer, newline="\n", encoding=sys.stdout.encoding, errors=sys.stdout.errors
    )
    old_stdout, sys.stdout = sys.stdout, new_stdout

DEFAULT_LOG_LEVEL = "."

DUPLICATE_LINE_MESSAGE_FMT = "[the above message was repeated %d times]"

MK_VARDIR = os.getenv("LOGWATCH_DIR") or os.getenv("MK_VARDIR") or os.getenv("MK_STATEDIR") or "."

MK_CONFDIR = os.getenv("LOGWATCH_DIR") or os.getenv("MK_CONFDIR") or "."

LOGGER = logging.getLogger(__name__)

IPV4_REGEX = re.compile(r"^(::ffff:|::ffff:0:|)(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")

IPV6_REGEX = re.compile(r"^(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}$")

ENCODINGS = (
    (b"\xFF\xFE", "utf_16"),
    (b"\xFE\xFF", "utf_16_be"),
)

TTY_COLORS = {
    "C": "\033[1;31m",  # red
    "W": "\033[1;33m",  # yellow
    "O": "\033[1;32m",  # green
    "I": "\033[1;34m",  # blue
    ".": "",  # remain same
    "normal": "\033[0m",
}

CONFIG_ERROR_PREFIX = "CANNOT READ CONFIG FILE: "  # detected by check plugin

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
    binary_type = bytes
else:
    text_type = unicode  # pylint: disable=undefined-variable
    binary_type = str


# Borrowed from six
def ensure_str(s, encoding="utf-8", errors="strict"):
    """Coerce *s* to `str`.

    For Python 2:
      - `unicode` -> encoded to `str`
      - `str` -> `str`

    For Python 3:
      - `str` -> `str`
      - `bytes` -> decoded to `str`
    """
    if not isinstance(s, (text_type, binary_type)):
        raise TypeError("not expecting type '%s'" % type(s))
    if PY2 and isinstance(s, text_type):
        s = s.encode(encoding, errors)
    elif PY3 and isinstance(s, binary_type):
        s = s.decode(encoding, errors)
    return s


def init_logging(verbosity):
    if verbosity == 0:
        LOGGER.propagate = False
        logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")
    elif verbosity == 1:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(lineno)s: %(message)s")


class ArgsParser(object):  # pylint: disable=too-few-public-methods, useless-object-inheritance
    """
    Custom argument parsing.
    (Neither use optparse which is Python 2.3 to 2.7 only.
    Nor use argparse which is Python 2.7 onwards only.)
    """

    def __init__(self, argv):
        super(ArgsParser, self).__init__()

        if "-h" in argv:
            sys.stderr.write(ensure_str(__doc__))
            sys.exit(0)

        self.verbosity = argv.count("-v") + 2 * argv.count("-vv")
        self.config = argv[argv.index("-c") + 1] if "-c" in argv else None
        self.debug = "-d" in argv or "--debug" in argv
        self.no_state = "--no_state" in argv


def get_status_filename(cluster_config):
    """
    Side effect:
    - Depend on ENV var.
    - In case agent plugin is called with debug option set -> depends on global
      LOGGER and stdout.

    Determine the name of the state file dependent on ENV variable and config:
    $REMOTE set, no cluster set or no ip match -> logwatch.state.<formatted-REMOTE>
    $REMOTE set, cluster set and ip match      -> logwatch.state.<cluster-name>
    $REMOTE not set and a tty                  -> logwatch.state.local
    $REMOTE not set and not a tty              -> logwatch.state

    $REMOTE is determined by the check_mk_agent and varies dependent on how the
    check_mk_agent is accessed:
    - telnet ($REMOTE_HOST): $REMOTE is in IPv6 notation. IPv4 is extended to IPv6
                             notation e.g. ::ffff:127.0.0.1
    - ssh ($SSH_CLIENT): $REMOTE is either in IPv4 or IPv6 notation dependent on the
                         IP family of the remote host.

    <formatted-REMOTE> is REMOTE with colons (:) replaced with underscores (_) for
    IPv6 address, is to IPv6 notation extended address with colons (:) replaced with
    underscores (_) for IPv4 address or is plain $REMOTE in case it does not match
    an IPv4 or IPv6 address.
    """
    remote = os.getenv("REMOTE", os.getenv("REMOTE_ADDR"))
    if not remote:
        status_filename = "logwatch.state" + (".local" if sys.stdout.isatty() else "")
        return os.path.join(MK_VARDIR, status_filename)
    remote_hostname = remote.replace(":", "_")

    match = IPV4_REGEX.match(remote) or IPV6_REGEX.match(remote)
    if not match:
        LOGGER.debug("REMOTE %r neither IPv4 nor IPv6 address.", remote)
        return os.path.join(MK_VARDIR, "logwatch.state.%s" % remote_hostname)

    remote_ip = match.group()
    # in case of IPv4 extended to IPv6 get rid of prefix for ip match lookup
    if remote_ip.startswith("::ffff:"):
        remote_ip = remote_ip[7:]

    # In case cluster configured map ip to cluster name if configured.
    # key "name" is mandatory and unique for cluster dicts
    cluster_name = remote_hostname
    for conf in cluster_config:
        for ip_or_subnet in conf.ips_or_subnets:
            if ip_in_subnetwork(remote_ip, ip_or_subnet):
                # Cluster name may not contain whitespaces (must be provided from
                # the WATO config as type ID or hostname).
                cluster_name = conf.name
                LOGGER.info("Matching cluster ip %s", remote_ip)
                LOGGER.info("Matching cluster name %s", cluster_name)
    status_filename = os.path.join(MK_VARDIR, "logwatch.state.%s" % cluster_name)
    LOGGER.info("Status filename: %s", status_filename)
    return status_filename


def is_comment(line):
    return line.lstrip().startswith("#")


def is_empty(line):
    return line.strip() == ""


def is_indented(line):
    return line.startswith(" ")


def parse_filenames(line):
    if platform.system() == "Windows":
        # we can't use pathlib: Python 2.5 has no pathlib
        # to garantie that backslash is escaped
        _processed_line = line.replace("\\", "/")
        _processed_line = os.path.normpath(_processed_line)
        _processed_line = _processed_line.replace("\\", "\\\\")
        return shlex.split(_processed_line)

    if sys.version_info[0] < 3:
        return [x.decode("utf-8") for x in shlex.split(line.encode("utf-8"))]

    return shlex.split(line)


def get_config_files(directory, config_file_arg=None):
    if config_file_arg is not None:
        return [config_file_arg]

    config_file_paths = []
    config_file_paths.append(directory + "/logwatch.cfg")
    # Add config file paths from a logwatch.d folder
    for config_file in glob.glob(directory + "/logwatch.d/*.cfg"):
        config_file_paths.append(config_file)
    LOGGER.info("Configuration file paths: %r", config_file_paths)
    return config_file_paths


def iter_config_lines(files, debug=False):
    no_cfg_content_yielded = True
    for file_ in files:
        try:
            with open(file_, "rb") as fid:
                try:
                    decoded = (line.decode("utf-8") for line in fid)
                    for line in decoded:
                        if not is_comment(line) and not is_empty(line):
                            yield line.rstrip()
                            no_cfg_content_yielded = False
                except UnicodeDecodeError:
                    msg = "Error reading file %r (please use utf-8 encoding!)\n" % file_
                    sys.stdout.write(CONFIG_ERROR_PREFIX + msg)
        except IOError:
            pass

    if debug and no_cfg_content_yielded:
        # We need at least one config file *with* content in one of the places:
        # logwatch.d or MK_CONFDIR
        raise IOError("Did not find any content in config files: %s" % ", ".join(files))


def consume_cluster_definition(config_lines):
    cluster_name = config_lines.pop(0)[8:].strip()  # e.g.: CLUSTER duck
    cluster = ClusterConfigBlock(cluster_name, [])
    LOGGER.debug("new ClusterConfigBlock: %s", cluster_name)

    while config_lines and is_indented(config_lines[0]):
        cluster.ips_or_subnets.append(config_lines.pop(0).strip())

    return cluster


def consume_logfile_definition(config_lines):
    cont_list = []
    rewrite_list = []
    filenames = parse_filenames(config_lines.pop(0))
    logfiles = PatternConfigBlock(filenames, [])
    LOGGER.debug("new PatternConfigBlock: %s", filenames)

    while config_lines and is_indented(config_lines[0]):
        line = config_lines.pop(0)
        level, raw_pattern = line.split(None, 1)

        if level == "A":
            cont_list.append(raw_pattern)

        elif level == "R":
            rewrite_list.append(raw_pattern)

        elif level in ("C", "W", "I", "O"):
            # New pattern for line matching => clear continuation and rewrite patterns
            cont_list = []
            rewrite_list = []
            pattern = (level, raw_pattern, cont_list, rewrite_list)
            logfiles.patterns.append(pattern)
            LOGGER.debug("pattern %s", pattern)

        else:
            raise ValueError("Invalid level in pattern line %r" % line)

    return logfiles


def read_config(files, debug=False):
    """
    Read logwatch.cfg (patterns, cluster mapping, etc.).

    Side effect: Reads filesystem files logwatch.cfg and /logwatch.d/*.cfg

    Returns configuration as list. List elements are namedtuples.
    Namedtuple either describes logile patterns and is PatternConfigBlock(files, patterns).
    Or tuple describes optional cluster mapping and is ClusterConfigBlock(name, ips_or_subnets)
    with ips as list of strings.
    """
    LOGGER.debug("Config files: %r", files)

    logfiles_configs = []
    cluster_configs = []
    config_lines = list(iter_config_lines(files, debug=debug))

    # parsing has to consider the following possible lines:
    # - comment lines (begin with #)
    # - logfiles line (begin not with #, are not empty and do not contain CLUSTER)
    # - cluster lines (begin with CLUSTER)
    # - logfiles patterns (follow logfiles lines, begin with whitespace)
    # - cluster ips or subnets (follow cluster lines, begin with whitespace)
    # Needs to consider end of lines to append ips/subnets to clusters as well.

    while config_lines:
        first_line = config_lines[0]
        if is_indented(first_line):
            raise ValueError("Missing block definition for line %r" % first_line)

        if first_line.startswith("CLUSTER "):
            cluster_configs.append(consume_cluster_definition(config_lines))
        else:
            logfiles_configs.append(consume_logfile_definition(config_lines))

    LOGGER.info("Logfiles configurations: %r", logfiles_configs)
    LOGGER.info("Optional cluster configurations: %r", cluster_configs)
    return logfiles_configs, cluster_configs


class State(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, filename, data=None):
        super(State, self).__init__()
        self.filename = filename
        self._data = data or {}

    @staticmethod
    def _load_line(line):
        try:
            return ast.literal_eval(line)
        except (NameError, SyntaxError, ValueError):
            # Support status files with the following structure:
            # /var/log/messages|7767698|32455445
            # These were used prior to to 1.7.0i1
            parts = line.split("|")
            filename, offset = parts[0], int(parts[1])
            inode = int(parts[2]) if len(parts) >= 3 else -1
            return {"file": filename, "offset": offset, "inode": inode}

    def read(self):
        """Read state from file
        Support state files with the following structure:
        {'file': b'/var/log/messages', 'offset': 7767698, 'inode': 32455445}
        """
        LOGGER.debug("Reading state file: %r", self.filename)

        if not os.path.exists(self.filename):
            return self

        with open(self.filename) as stat_fh:
            for line in stat_fh:
                line_data = self._load_line(line)
                self._data[line_data["file"]] = line_data

        LOGGER.info("Read state: %r", self._data)
        return self

    def write(self):
        LOGGER.debug("Writing state: %r", self._data)
        LOGGER.debug("State filename: %r", self.filename)

        with open(self.filename, "wb") as stat_fh:
            for data in self._data.values():
                stat_fh.write(repr(data).encode("ascii") + b"\n")

    def get(self, key):
        return self._data.setdefault(key, {"file": key})


class LogLinesIter(object):  # pylint: disable=useless-object-inheritance
    # this is supposed to become a proper iterator.
    # for now, we need a persistent buffer to fix things
    BLOCKSIZE = 8192

    def __init__(self, logfile, encoding):
        super(LogLinesIter, self).__init__()
        self._fd = os.open(logfile, os.O_RDONLY)
        self._lines = []  # List[Text]
        self._buffer = b""
        self._reached_end = False  # used for optimization only
        self._enc = encoding or self._get_encoding()
        self._nl = "\n"
        # for Windows we need a bit special processing. It is difficult to fit this processing
        # in current architecture smoothly
        self._utf16 = self._enc == "utf_16"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False  # Do not swallow exceptions

    def close(self):
        os.close(self._fd)

    def _get_encoding(self):
        # In 1.5 this was only used when logwatch is executed on windows.
        # On linux the log lines were not decoded at all.
        #
        # For 1.6 we want to follow the standard approach to decode things read
        # from external sources as soon as possible. We also want to ensure that
        # the output of this script is always UTF-8 encoded later.
        #
        # In case the current approach does not work out, then have a look here
        # for possible more robust solutions:
        # http://python-notes.curiousefficiency.org/en/latest/python3/text_file_processing.html
        enc_bytes_len = max(len(bom) for bom, _enc in ENCODINGS)
        self._buffer = os.read(self._fd, enc_bytes_len)
        for bom, encoding in ENCODINGS:
            if self._buffer.startswith(bom):
                self._buffer = self._buffer[len(bom) :]
                LOGGER.debug("Detected %r encoding by BOM", encoding)
                return encoding

        pref_encoding = locale.getpreferredencoding()
        encoding = (
            "utf_8" if not pref_encoding or pref_encoding == "ANSI_X3.4-1968" else pref_encoding
        )
        LOGGER.debug("Locale Preferred encoding is %s, using %s", pref_encoding, encoding)
        return encoding

    def _update_lines(self):
        """
        Try to read more lines from file.
        """
        binary_nl = self._nl.encode(self._enc)
        while binary_nl not in self._buffer:
            new_bytes = os.read(self._fd, LogLinesIter.BLOCKSIZE)
            if not new_bytes:
                break
            self._buffer += new_bytes

        # in case of decoding error, replace with U+FFFD REPLACEMENT CHARACTER
        raw_lines = self._buffer.decode(self._enc, "replace").split(self._nl)
        self._buffer = raw_lines.pop().encode(self._enc)  # unfinished line
        self._lines.extend(l + self._nl for l in raw_lines)

    def set_position(self, position):
        if position is None:
            return
        self._buffer = b""
        self._lines = []
        os.lseek(self._fd, position, os.SEEK_SET)

    def get_position(self):
        """
        Return the position where we want to continue next time
        """
        pointer_pos = os.lseek(self._fd, 0, os.SEEK_CUR)
        bytes_unused = sum((len(l.encode(self._enc)) for l in self._lines), len(self._buffer))
        return pointer_pos - bytes_unused

    def skip_remaining(self):
        os.lseek(self._fd, 0, os.SEEK_END)
        self._buffer = b""
        self._lines = []

    def push_back_line(self, line):
        self._lines.insert(0, line)

    def next_line(self):
        if self._reached_end:  # optimization only
            return None

        if not self._lines:
            self._update_lines()

        if self._lines:
            return self._lines.pop(0)

        self._reached_end = True
        return None


def is_inode_capable(path):
    system = platform.system()
    if system == "Windows":
        volume_name = "%s:\\\\" % path.split(":", 1)[0]
        import win32api  # type: ignore[import] # pylint: disable=import-error

        volume_info = win32api.GetVolumeInformation(volume_name)
        volume_type = volume_info[-1]
        return "ntfs" in volume_type.lower()
    return system == "Linux"


def get_formatted_line(line, level):
    formatted_line = "%s %s" % (level, line)
    if sys.stdout.isatty():
        formatted_line = "%s%s%s" % (
            TTY_COLORS[level],
            formatted_line.replace("\1", "\nCONT:"),
            TTY_COLORS["normal"],
        )
    return formatted_line


def should_log_line_with_level(level, nocontext):
    return not (nocontext and level == ".")


def process_logfile(section, filestate, debug):
    """
    Returns tuple of (
        logfile lines,
        warning and/or error indicator,
        warning and/or error lines,
    ).
    In case the file has never been seen before returns a list of logfile lines
    and None in case the logfile cannot be opened.
    """
    # TODO: Make use of the ContextManager feature of LogLinesIter
    try:
        log_iter = LogLinesIter(section.name_fs, section.options.encoding)
    except OSError:
        if debug:
            raise
        return "[[[%s:cannotopen]]]\n" % section.name_write, []

    try:
        header = "[[[%s]]]\n" % section.name_write

        stat = os.stat(section.name_fs)
        inode = stat.st_ino if is_inode_capable(section.name_fs) else 1
        # If we have never seen this file before, we set the inode to -1
        prev_inode = filestate.get("inode", -1)
        filestate["inode"] = inode

        # Look at which file offset we have finished scanning the logfile last time.
        offset = filestate.get("offset")
        # Set the current pointer to the file end
        filestate["offset"] = stat.st_size

        # If we have never seen this file before, we do not want
        # to make a fuss about ancient log messages... (unless configured to)
        if offset is None and not (section.options.fromstart or debug):
            return header, []

        # If the inode of the logfile has changed it has appearently
        # been started from new (logfile rotation). At least we must
        # assume that. In some rare cases (restore of a backup, etc)
        # we are wrong and resend old log messages
        if prev_inode >= 0 and inode != prev_inode:
            offset = None

        # Our previously stored offset is the current end ->
        # no new lines in this file
        if offset == stat.st_size:
            return header, []

        # If our offset is beyond the current end, the logfile has been
        # truncated or wrapped while keeping the same inode. We assume
        # that it contains all new data in that case and restart from
        # beginning.
        if offset is not None and offset > stat.st_size:
            offset = None

        # now seek to offset where interesting data begins
        log_iter.set_position(offset)

        worst = -1
        warnings_and_errors = []
        lines_parsed = 0
        start_time = time.time()

        while True:
            line = log_iter.next_line()
            if line is None:
                break  # End of file

            # Handle option maxlinesize
            if section.options.maxlinesize is not None and len(line) > section.options.maxlinesize:
                line = line[: section.options.maxlinesize] + "[TRUNCATED]\n"

            lines_parsed += 1
            # Check if maximum number of new log messages is exceeded
            if section.options.maxlines is not None and lines_parsed > section.options.maxlines:
                warnings_and_errors.append(
                    "%s Maximum number (%d) of new log messages exceeded.\n"
                    % (
                        section.options.overflow,
                        section.options.maxlines,
                    )
                )
                worst = max(worst, section.options.overflow_level)
                log_iter.skip_remaining()
                break

            # Check if maximum processing time (per file) is exceeded. Check only
            # every 100'th line in order to save system calls
            if (
                section.options.maxtime is not None
                and lines_parsed % 100 == 10
                and time.time() - start_time > section.options.maxtime
            ):
                warnings_and_errors.append(
                    "%s Maximum parsing time (%.1f sec) of this log file exceeded.\n"
                    % (
                        section.options.overflow,
                        section.options.maxtime,
                    )
                )
                worst = max(worst, section.options.overflow_level)
                log_iter.skip_remaining()
                break

            level = DEFAULT_LOG_LEVEL
            for lev, pattern, cont_patterns, replacements in section.compiled_patterns:

                matches = pattern.search(line[:-1])
                if matches:
                    level = lev
                    levelint = {"C": 2, "W": 1, "O": 0, "I": -1, ".": -1}[lev]
                    worst = max(levelint, worst)

                    # TODO: the following for block should be a method of the iterator
                    # Check for continuation lines
                    for cont_pattern in cont_patterns:
                        if isinstance(cont_pattern, int):  # add that many lines
                            for _unused_x in range(cont_pattern):
                                cont_line = log_iter.next_line()
                                if cont_line is None:  # end of file
                                    break
                                line = line[:-1] + "\1" + cont_line

                        else:  # pattern is regex
                            while True:
                                cont_line = log_iter.next_line()
                                if cont_line is None:  # end of file
                                    break
                                if cont_pattern.search(cont_line[:-1]):
                                    line = line[:-1] + "\1" + cont_line
                                else:
                                    log_iter.push_back_line(
                                        cont_line
                                    )  # sorry for stealing this line
                                    break

                    # Replacement
                    for replace in replacements:
                        line = replace.replace("\\0", line.rstrip()) + "\n"
                        for num, group in enumerate(matches.groups()):
                            if group is not None:
                                line = line.replace("\\%d" % (num + 1), group)

                    break  # matching rule found and executed

            if level == "I":
                level = "."
            if not should_log_line_with_level(level, section.options.nocontext):
                continue

            out_line = get_formatted_line(line[:-1], level)
            warnings_and_errors.append("%s\n" % out_line)

        new_offset = log_iter.get_position()
    finally:
        log_iter.close()

    filestate["offset"] = new_offset

    # Handle option maxfilesize, regardless of warning or errors that have happened
    if section.options.maxfilesize:
        offset_wrap = new_offset // section.options.maxfilesize
        if ((offset or 0) // section.options.maxfilesize) < offset_wrap:
            warnings_and_errors.append(
                "%sW Maximum allowed logfile size (%d bytes) exceeded for the %dth time.%s\n"
                % (
                    TTY_COLORS["W"] if sys.stdout.isatty() else "",
                    section.options.maxfilesize,
                    offset_wrap,
                    TTY_COLORS["normal"] if sys.stdout.isatty() else "",
                )
            )

    # output all lines if at least one warning, error or ok has been found
    if worst > -1:
        return header, warnings_and_errors
    return header, []


class Options(object):  # pylint: disable=useless-object-inheritance
    """Options w.r.t. logfile patterns (not w.r.t. cluster mapping)."""

    MAP_OVERFLOW = {"C": 2, "W": 1, "I": 0, "O": 0}
    MAP_BOOL = {"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False}
    DEFAULTS = {
        "encoding": None,
        "maxfilesize": None,
        "maxlines": None,
        "maxtime": None,
        "maxlinesize": None,
        "regex": None,
        "overflow": "C",
        "nocontext": None,
        "maxcontextlines": None,
        "maxoutputsize": 500000,  # same as logwatch_max_filesize in check plugin
        "fromstart": False,
        "skipconsecutiveduplicated": False,
    }

    def __init__(self):
        self.values = {}

    @property
    def encoding(self):
        return self._attr_or_default("encoding")

    @property
    def maxfilesize(self):
        return self._attr_or_default("maxfilesize")

    @property
    def maxlines(self):
        return self._attr_or_default("maxlines")

    @property
    def maxtime(self):
        return self._attr_or_default("maxtime")

    @property
    def maxlinesize(self):
        return self._attr_or_default("maxlinesize")

    @property
    def regex(self):
        return self._attr_or_default("regex")

    @property
    def overflow(self):
        return self._attr_or_default("overflow")

    @property
    def nocontext(self):
        return self._attr_or_default("nocontext")

    @property
    def maxcontextlines(self):
        return self._attr_or_default("maxcontextlines")

    @property
    def maxoutputsize(self):
        return self._attr_or_default("maxoutputsize")

    @property
    def fromstart(self):
        return self._attr_or_default("fromstart")

    @property
    def skipconsecutiveduplicated(self):
        return self._attr_or_default("skipconsecutiveduplicated")

    def _attr_or_default(self, key):
        if key in self.values:
            return self.values[key]
        return Options.DEFAULTS[key]

    @property
    def overflow_level(self):
        return self.MAP_OVERFLOW[self.overflow]

    def update(self, other):
        self.values.update(other.values)

    def set_opt(self, opt_str):
        try:
            key, value = opt_str.split("=", 1)
            if key == "encoding":
                "".encode(value)  # make sure it's an encoding
                self.values[key] = value
            elif key in ("maxlines", "maxlinesize", "maxfilesize", "maxoutputsize"):
                self.values[key] = int(value)
            elif key in ("maxtime",):
                self.values[key] = float(value)
            elif key == "overflow":
                if value not in Options.MAP_OVERFLOW:
                    raise ValueError(
                        "Invalid overflow: %r (choose from %r)"
                        % (
                            value,
                            Options.MAP_OVERFLOW.keys(),
                        )
                    )
                self.values["overflow"] = value
            elif key in ("regex", "iregex"):
                flags = (re.IGNORECASE if key.startswith("i") else 0) | re.UNICODE
                self.values["regex"] = re.compile(value, flags)
            elif key in ("nocontext", "fromstart", "skipconsecutiveduplicated"):
                if value.lower() not in Options.MAP_BOOL:
                    raise ValueError(
                        "Invalid %s: %r (choose from %r)"
                        % (
                            key,
                            value,
                            Options.MAP_BOOL.keys(),
                        )
                    )
                self.values[key] = Options.MAP_BOOL[value.lower()]
            elif key == "maxcontextlines":
                before, after = (int(i) for i in value.split(","))
                self.values[key] = (before, after)
            else:
                raise ValueError("Invalid option: %r" % opt_str)
        except (ValueError, LookupError) as exc:
            sys.stdout.write("INVALID CONFIGURATION: %s\n" % exc)
            raise


class PatternConfigBlock(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, files, patterns):
        super(PatternConfigBlock, self).__init__()
        self.files = files
        self.patterns = patterns


class ClusterConfigBlock(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, name, ips_or_subnets):
        super(ClusterConfigBlock, self).__init__()
        self.name = name
        self.ips_or_subnets = ips_or_subnets


def _decode_to_unicode(match):
    # (Union[bytes, unicode, str]) -> unicode
    # we can't use 'surrogatereplace' because that a) is py3 only b) would fail upon re-encoding
    # we can't use 'six': this code may be executed using Python 2.5/2.6
    if sys.version_info[0] == 2:
        # Python 2: str @Windows && @Linux
        return (
            match
            if isinstance(match, unicode)  # pylint: disable=undefined-variable
            else match.decode("utf8", "replace")
        )

    # Python 3: bytes @Linux and unicode @Windows
    return match.decode("utf-8", "replace") if isinstance(match, bytes) else match


def find_matching_logfiles(glob_pattern):
    """
    Evaluate globbing pattern to a list of logfile IDs

    Return a list of Tuples:
     * one identifier for opening the file as used by os.open (byte str or unicode)
     * one unicode str, safe for writing

    Glob matching of hard linked, unbroken soft linked/symlinked files.
    No tilde expansion is done, but *, ?, and character ranges expressed with []
    will be correctly matched.

    No support for recursive globs ** (supported beginning with Python3.5 only).

    Hard linked dublicates of files are not filtered.
    Soft links may not be detected properly dependent on the Python runtime
    [Python Standard Lib, os.path.islink()].
    """
    if platform.system() == "Windows":
        # windows is the easy case:
        # provide unicode, and let python deal with the rest
        # (see https://www.python.org/dev/peps/pep-0277)
        matches = list(glob.glob(glob_pattern))
    else:
        # we can't use glob on unicode, as it would try to re-decode matches with ascii
        matches = glob.glob(glob_pattern.encode("utf8"))

    # skip dirs
    file_refs = []
    for match in matches:
        if os.path.isdir(match):
            continue

        # match is bytes in Linux and unicode/str in Windows
        match_readable = _decode_to_unicode(match)

        file_refs.append((match, match_readable))

    return file_refs


def _search_optimize_raw_pattern(raw_pattern):
    """return potentially stripped pattern for use with *search*

    Stripping leading and trailing '.*' avoids catastrophic backtracking
    when long log lines are being processed
    """
    start_idx = 2 if raw_pattern.startswith(".*") else 0
    end_idx = -2 if raw_pattern.endswith(".*") else None
    return raw_pattern[start_idx:end_idx] or raw_pattern


def _compile_continuation_pattern(raw_pattern):
    try:
        return int(raw_pattern)
    except (ValueError, TypeError):
        return re.compile(_search_optimize_raw_pattern(raw_pattern), re.UNICODE)


class LogfileSection(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, logfile_ref):
        super(LogfileSection, self).__init__()
        self.name_fs = logfile_ref[0]
        self.name_write = logfile_ref[1]
        self.options = Options()
        self.patterns = []
        self._compiled_patterns = None

    @property
    def compiled_patterns(self):
        if self._compiled_patterns is not None:
            return self._compiled_patterns

        compiled_patterns = []
        for level, raw_pattern, cont_list, rewrite_list in self.patterns:
            if not rewrite_list:
                # it does not matter what the matched group is in this case
                raw_pattern = _search_optimize_raw_pattern(raw_pattern)
            compiled = re.compile(raw_pattern, re.UNICODE)
            cont_list = [_compile_continuation_pattern(cp) for cp in cont_list]
            compiled_patterns.append((level, compiled, cont_list, rewrite_list))

        self._compiled_patterns = compiled_patterns
        return self._compiled_patterns


def parse_sections(logfiles_config):
    """
    Returns a list of LogfileSections and and a list of non-matching patterns.
    """
    found_sections = {}  # type: dict
    non_matching_patterns = []

    for cfg in logfiles_config:

        # First read all the options like 'maxlines=100' or 'maxtime=10'
        opt = Options()
        for item in cfg.files:
            if "=" in item:
                opt.set_opt(item)

        # Then handle the file patterns
        # The thing here is that the same file could match different patterns.
        for glob_pattern in (f for f in cfg.files if "=" not in f):
            logfile_refs = find_matching_logfiles(glob_pattern)
            if opt.regex is not None:
                logfile_refs = [ref for ref in logfile_refs if opt.regex.search(ref[1])]
            if not logfile_refs:
                non_matching_patterns.append(glob_pattern)
            for logfile_ref in logfile_refs:
                section = found_sections.setdefault(logfile_ref[0], LogfileSection(logfile_ref))
                section.patterns.extend(cfg.patterns)
                section.options.update(opt)

    logfile_sections = [found_sections[k] for k in sorted(found_sections)]

    return logfile_sections, non_matching_patterns


def ip_in_subnetwork(ip_address, subnetwork):
    """
    Accepts ip address as string e.g. "10.80.1.1" and CIDR notation as string e.g."10.80.1.0/24".
    Returns False in case of incompatible IP versions.

    Implementation depends on Python2 and Python3 standard lib only.
    """
    (ip_integer, version1) = _ip_to_integer(ip_address)
    (ip_lower, ip_upper, version2) = _subnetwork_to_ip_range(subnetwork)
    if version1 != version2:
        return False
    return ip_lower <= ip_integer <= ip_upper


def _ip_to_integer(ip_address):
    """
    Raises ValueError in case of invalid IP address.
    """
    # try parsing the IP address first as IPv4, then as IPv6
    for version in (socket.AF_INET, socket.AF_INET6):
        try:
            ip_hex = socket.inet_pton(version, ip_address)
        except socket.error:
            continue
        ip_integer = int(binascii.hexlify(ip_hex), 16)
        return (ip_integer, 4 if version == socket.AF_INET else 6)
    raise ValueError("invalid IP address: %r" % ip_address)


def _subnetwork_to_ip_range(subnetwork):
    """
    Convert subnetwork to a range of IP addresses

    Raises ValueError in case of invalid subnetwork.
    """
    if "/" not in subnetwork:
        ip_integer, version = _ip_to_integer(subnetwork)
        return ip_integer, ip_integer, version
    network_prefix, netmask_len = subnetwork.split("/", 1)
    # try parsing the subnetwork first as IPv4, then as IPv6
    for version, ip_len in ((socket.AF_INET, 32), (socket.AF_INET6, 128)):
        try:
            ip_hex = socket.inet_pton(version, network_prefix)
        except socket.error:
            continue
        try:
            suffix_mask = (1 << (ip_len - int(netmask_len))) - 1
        except ValueError:  # netmask_len is too large or invalid
            raise ValueError("invalid subnetwork: %r" % subnetwork)
        netmask = ((1 << ip_len) - 1) - suffix_mask
        ip_lower = int(binascii.hexlify(ip_hex), 16) & netmask
        ip_upper = ip_lower + suffix_mask
        return (ip_lower, ip_upper, 4 if version == socket.AF_INET else 6)
    raise ValueError("invalid subnetwork: %r" % subnetwork)


def _filter_maxoutputsize(lines, maxoutputsize):
    """Produce lines right *before* maxoutputsize is exceeded"""
    bytecount = 0
    for line in lines:
        bytecount += len(line.encode("utf-8"))
        if bytecount > maxoutputsize:
            break
        yield line


def _filter_maxcontextlines(lines_list, before, after):
    """Only produce lines from a limited context

    Think of grep's -A and -B options
    """

    n_lines = len(lines_list)
    indices = iter(range(-before, n_lines))
    context_end = -1
    for idx in indices:
        new_in_context_idx = idx + before
        if new_in_context_idx < n_lines and context_end < n_lines:
            new_in_context = lines_list[new_in_context_idx]
            # if the line ahead is relevant, extend the context
            if new_in_context.startswith(("C", "W")):
                context_end = new_in_context_idx + after
        if 0 <= idx <= context_end:
            yield lines_list[idx]


def _filter_consecutive_duplicates(lines, nocontext):
    """
    Filters out consecutive duplicated lines and adds a context line (if nocontext=False) with the
    number of removed lines for every chunk of removed lines
    """

    lines = iter(lines)

    counter = 0
    current_line = next(lines, None)
    next_line = None

    while True:
        if current_line is None:
            return

        next_line = next(lines, None)

        if counter == 0:
            yield current_line

        if current_line == next_line:
            counter += 1
            continue

        if counter > 0 and should_log_line_with_level(DEFAULT_LOG_LEVEL, nocontext):
            unformatted_msg = DUPLICATE_LINE_MESSAGE_FMT % (counter)
            duplicate_line_msg = get_formatted_line(unformatted_msg, DEFAULT_LOG_LEVEL)
            yield "%s\n" % duplicate_line_msg

        counter = 0
        current_line = next_line


def write_output(header, lines, options):

    if options.maxcontextlines:
        lines = _filter_maxcontextlines(lines, *options.maxcontextlines)

    lines = _filter_maxoutputsize(lines, options.maxoutputsize)

    if options.skipconsecutiveduplicated:
        lines = _filter_consecutive_duplicates(lines, options.nocontext)

    sys.stdout.write(header)
    sys.stdout.writelines(map(ensure_str, lines))


def main(argv=None):
    if argv is None:
        argv = sys.argv

    args = ArgsParser(argv)
    init_logging(args.verbosity)

    sys.stdout.write("<<<logwatch>>>\n")

    try:
        files = get_config_files(MK_CONFDIR, config_file_arg=args.config)
        logfiles_config, cluster_config = read_config(files, args.debug)
    except Exception as exc:
        if args.debug:
            raise
        sys.stdout.write(CONFIG_ERROR_PREFIX + "%s\n" % exc)
        sys.exit(1)

    status_filename = get_status_filename(cluster_config)
    # Copy the last known state from the logwatch.state when there is no status_filename yet.
    if not os.path.exists(status_filename) and os.path.exists("%s/logwatch.state" % MK_VARDIR):
        shutil.copy("%s/logwatch.state" % MK_VARDIR, status_filename)

    found_sections, non_matching_patterns = parse_sections(logfiles_config)

    for pattern in non_matching_patterns:
        # Python 2.5/2.6 compatible solution
        if sys.version_info[0] == 3:
            sys.stdout.write("[[[%s:missing]]]\n" % pattern)
        else:
            sys.stdout.write(("[[[%s:missing]]]\n" % pattern).encode("utf-8"))

    state = State(status_filename)
    try:
        state.read()
    except Exception as exc:
        if args.debug:
            raise
        # Simply ignore errors in the status file.  In case of a corrupted status file we simply
        # begin with an empty status. That keeps the monitoring up and running - even if we might
        # lose a message in the extreme case of a corrupted status file.
        LOGGER.warning("Exception reading status file: %s", str(exc))

    for section in found_sections:
        filestate = state.get(section.name_fs)
        try:
            header, output = process_logfile(section, filestate, args.debug)
            write_output(header, output, section.options)
        except Exception as exc:
            if args.debug:
                raise
            LOGGER.debug("Exception when processing %r: %s", section.name_fs, exc)

    if args.debug:
        LOGGER.debug("State file not written (debug mode)")
        return
    if not args.no_state:
        state.write()


if __name__ == "__main__":
    main()
