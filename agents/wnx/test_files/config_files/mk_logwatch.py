#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""mk_logwatch
This is the Check_MK Agent plugin. If configured it will be called by the
agent without arguments.

Options:
    -d    Debug mode: Colored output, no saving of status.
    -h    Show help.
    --no_state       No state
    -v    Verbose output for debugging purposes (no debug mode).

You should find an example configuration file at
'../cfg_examples/logwatch.cfg' relative to this file.
"""

from __future__ import with_statement

import glob
import logging
import os
import re
import shutil
import sys
import time
import socket
import binascii
import platform
import locale

MK_VARDIR = os.getenv("LOGWATCH_DIR") or os.getenv("MK_VARDIR") or os.getenv("MK_STATEDIR") or "."

MK_CONFDIR = os.getenv("LOGWATCH_DIR") or os.getenv("MK_CONFDIR") or "."

LOGGER = logging.getLogger(__name__)

IPV4_REGEX = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")

IPV6_REGEX = re.compile(r"^(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}$")

ENCODINGS = (
    ('\xFF\xFE', "utf_16"),
    ('\xFE\xFF', "utf_16_be"),
)

TTY_COLORS = {
    'C': '\033[1;31m',  # red
    'W': '\033[1;33m',  # yellow
    'O': '\033[1;32m',  # green
    'I': '\033[1;34m',  # blue
    '.': '',  # remain same
    'normal': '\033[0m',
}

CONFIG_ERROR_PREFIX = "CANNOT READ CONFIG FILE: "  # detected by check plugin


def parse_arguments(argv=None):
    """
    Custom argument parsing.
    (Neither use optparse which is Python 2.3 to 2.7 only.
    Nor use argparse which is Python 2.7 onwards only.)
    """
    args = {}
    if argv is None:
        argv = sys.argv[1:]
    if "-h" in argv:
        sys.stderr.write(__doc__)
        sys.exit(0)
    if "-v" in argv:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    elif "-vv" in argv:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(lineno)s: %(message)s")
    else:
        LOGGER.propagate = False
    return args


#   .--MEI-Cleanup---------------------------------------------------------.
#   |     __  __ _____ ___       ____ _                                    |
#   |    |  \/  | ____|_ _|     / ___| | ___  __ _ _ __  _   _ _ __        |
#   |    | |\/| |  _|  | |_____| |   | |/ _ \/ _` | '_ \| | | | '_ \       |
#   |    | |  | | |___ | |_____| |___| |  __/ (_| | | | | |_| | |_) |      |
#   |    |_|  |_|_____|___|     \____|_|\___|\__,_|_| |_|\__,_| .__/       |
#   |                                                         |_|          |
#   +----------------------------------------------------------------------+
# In case the program crashes or is killed in a hard way, the frozen binary .exe
# may leave temporary directories named "_MEI..." in the temporary path. Clean them
# up to prevent eating disk space over time.

########################################################################
############## DUPLICATE CODE WARNING ##################################
### This code is also used in the cmk-update-agent frozen binary #######
### Any changes to this class should also be made in cmk-update-agent ##
### In the bright future we will move this code into a library #########
########################################################################


class MEIFolderCleaner(object):
    def pid_running(self, pid):
        import ctypes
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x100000

        process = kernel32.OpenProcess(SYNCHRONIZE, 0, pid)

        if process != 0:
            kernel32.CloseHandle(process)
            return True
        return False

    def find_and_remove_leftover_folders(self, hint_filenames):
        if not hasattr(sys, "frozen"):
            return

        import win32file  # pylint: disable=import-error
        import tempfile
        base_path = tempfile.gettempdir()
        for f in os.listdir(base_path):
            try:
                path = os.path.join(base_path, f)

                if not os.path.isdir(path):
                    continue

                # Only care about directories related to our program
                invalid_dir = False
                for hint_filename in hint_filenames:
                    if not os.path.exists(os.path.join(path, hint_filename)):
                        invalid_dir = True
                        break
                if invalid_dir:
                    continue

                pyinstaller_tmp_path = win32file.GetLongPathName(sys._MEIPASS).lower()  # pylint: disable=no-member
                if pyinstaller_tmp_path == path.lower():
                    continue  # Skip our own directory

                # Extract the process id from the directory and check whether or not it is still
                # running. Don't delete directories of running processes!
                # The name of the temporary directories is "_MEI<PID><NR>". We try to extract the PID
                # by stripping of a single digit from the right. In the hope the NR is a single digit
                # in all relevant cases.
                pid = int(f[4:-1])
                if self.pid_running(pid):
                    continue

                shutil.rmtree(path)
            except Exception, e:
                LOGGER.debug("Finding and removing leftover folders failed: %s", e)


def debug():
    return '-d' in sys.argv[1:] or '--debug' in sys.argv[1:]


def no_state():
    return '--no_state' in sys.argv[1:]


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
    return line.lstrip().startswith('#')


def is_empty(line):
    return line.strip() == ""


def is_indented(line):
    return line.startswith(" ")


def parse_filenames(line):
    return line.split()


def get_config_files(directory):
    config_file_paths = []
    config_file_paths.append(directory + "/logwatch.cfg")
    # Add config file paths from a logwatch.d folder
    for config_file in glob.glob(directory + "/logwatch.d/*.cfg"):
        config_file_paths.append(config_file)
    LOGGER.info("Configuration file paths: %r", config_file_paths)
    return config_file_paths


def iter_config_lines(files):
    for file_ in files:
        try:
            with open(file_) as fid:
                try:
                    decoded = (line.decode('utf-8') for line in fid)
                    for line in decoded:
                        if not is_comment(line) and not is_empty(line):
                            yield line.rstrip()
                except UnicodeDecodeError:
                    msg = "Error reading file %r (please use utf-8 encoding!)\n" % file_
                    sys.stdout.write(CONFIG_ERROR_PREFIX + msg)
        except IOError:
            if debug():
                raise


def consume_cluster_definition(config_lines):
    cluster_name = config_lines.pop(0)[8:].strip()  # e.g.: CLUSTER duck
    cluster = ClusterConfig(cluster_name, [])
    LOGGER.debug("new ClusterConfig: %s", cluster_name)

    while config_lines and is_indented(config_lines[0]):
        cluster.ips_or_subnets.append(config_lines.pop(0).strip())

    return cluster


def consume_logfile_definition(config_lines):
    cont_list = []
    rewrite_list = []
    filenames = parse_filenames(config_lines.pop(0))
    logfiles = LogfilesConfig(filenames, [])
    LOGGER.debug("new LogfilesConfig: %s", filenames)

    while config_lines and is_indented(config_lines[0]):
        line = config_lines.pop(0)
        level, raw_pattern = line.split(None, 1)

        if level == 'A':
            cont_list.append(raw_pattern)

        elif level == 'R':
            rewrite_list.append(raw_pattern)

        elif level in ('C', 'W', 'I', 'O'):
            # New pattern for line matching => clear continuation and rewrite patterns
            cont_list = []
            rewrite_list = []
            pattern = (level, raw_pattern, cont_list, rewrite_list)
            logfiles.patterns.append(pattern)
            LOGGER.debug("pattern %s", pattern)

        else:
            raise ValueError("Invalid level in pattern line %r" % line)

    return logfiles


def read_config(files):
    """
    Read logwatch.cfg (patterns, cluster mapping, etc.).

    Side effect: Reads filesystem files logwatch.cfg and /logwatch.d/*.cfg

    Returns configuration as list. List elements are namedtuples.
    Namedtuple either describes logile patterns and is LogfilesConfig(files, patterns).
    Or tuple describes optional cluster mapping and is ClusterConfig(name, ips_or_subnets)
    with ips as list of strings.
    """
    LOGGER.debug("Config files: %r", files)

    logfiles_configs = []
    cluster_configs = []
    config_lines = list(iter_config_lines(files))

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


def read_status(file_name):
    """
    Support status files with the following structure:

    # LOGFILE         OFFSET    INODE
    /var/log/messages|7767698|32455445
    /var/test/x12134.log|12345|32444355

    Status file lines may not be empty but must contain | separated status meta data.
    """
    LOGGER.debug("Status file: %r", file_name)
    if debug():
        return {}

    status = {}
    with open(file_name) as stat_fh:
        for line in stat_fh:
            parts = line.split('|')
            filename, offset = parts[0], int(parts[1])
            inode = int(parts[2]) if len(parts) >= 3 else -1
            status[filename] = (offset, inode)

    LOGGER.info("Read status: %r", status)
    return status


def save_status(status, file_name):
    LOGGER.debug("Save status:")
    LOGGER.debug("Status: %s", status)
    LOGGER.debug("Filename: %s", file_name)
    with open(file_name, "w") as f:
        for filename, (offset, inode) in status.items():
            f.write("%s|%d|%d\n" % (filename, offset, inode))


class LogLinesIter(object):
    # this is supposed to become a proper iterator.
    # for now, we need a persistent buffer to fix things
    BLOCKSIZE = 8192

    def __init__(self, logfile, encoding):
        super(LogLinesIter, self).__init__()
        self._fd = os.open(logfile, os.O_RDONLY)
        self._lines = []
        self._buffer = ''
        self._reached_end = False  # used for optimization only
        self._enc = encoding or self._get_encoding()
        self._newline = u'\n'.encode(self._enc)
        self._nl = u'\n'  # new line for utf_16, we process data as unicode in this case
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

    # TODO: Add an encoding-Option to the logfile section to enable the
    # user telling us the correct encoding of a file.
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
                self._buffer = self._buffer[len(bom):]
                LOGGER.debug("Detected %r encoding by BOM", encoding)
                return encoding

        pref_encoding = locale.getpreferredencoding()
        encoding = "utf_8" if not pref_encoding or pref_encoding == "ANSI_X3.4-1968" else pref_encoding
        LOGGER.debug("Locale Preferred encoding is %s, using %s", pref_encoding, encoding)
        return encoding

    def _update_lines(self):
        """
        Try to read more lines from file.
        """
        # try to read at least to end of next line
        if self._utf16:
            # unicode processing.
            # we don't bother what can happen and using unicode only mode for all utf_16 files
            while self._nl not in self._buffer:
                new_bytes = os.read(self._fd, LogLinesIter.BLOCKSIZE)
                if not new_bytes:
                    break
                self._buffer += new_bytes.decode("utf-16")  # unicode

            raw_lines = self._buffer.split(self._nl)
            self._buffer = raw_lines.pop()  # unfinished line
            self._lines.extend(l + self._nl for l in raw_lines)
        else:
            while self._newline not in self._buffer:
                new_bytes = os.read(self._fd, LogLinesIter.BLOCKSIZE)
                if not new_bytes:
                    break
                self._buffer += new_bytes

            raw_lines = self._buffer.split(self._newline)
            self._buffer = raw_lines.pop()  # unfinished line
            self._lines.extend(l + self._newline for l in raw_lines)

    def set_position(self, position):
        if position is None:
            return
        self._buffer = ''
        self._lines = []
        os.lseek(self._fd, position, os.SEEK_SET)

    def get_position(self):
        """
        Return the position where we want to continue next time
        """
        pointer_pos = os.lseek(self._fd, 0, os.SEEK_CUR)
        bytes_unused = sum((len(l) for l in self._lines), len(self._buffer))
        return pointer_pos - bytes_unused

    def skip_remaining(self):
        os.lseek(self._fd, 0, os.SEEK_END)
        self._buffer = ''
        self._lines = []

    def push_back_line(self, line):
        self._lines.insert(0, line.encode(self._enc))

    def next_line(self):
        if self._reached_end:  # optimization only
            return None

        if not self._lines:
            self._update_lines()

        if self._lines:
            if self._utf16:
                return self._lines.pop(0)
            # in case of decoding error, replace with U+FFFD REPLACEMENT CHARACTER
            return self._lines.pop(0).decode(self._enc, "replace")

        self._reached_end = True
        return None


def is_inode_capable(path):
    system = platform.system()
    if system == "Windows":
        volume_name = "%s:\\\\" % path.split(":", 1)[0]
        import win32api  # pylint: disable=import-error
        volume_info = win32api.GetVolumeInformation(volume_name)
        volume_type = volume_info[-1]
        return "ntfs" in volume_type.lower()
    return system == "Linux"


def decode_filename(byte_str_filename):
    return byte_str_filename.decode('utf-8')


def process_logfile(logfile, patterns, opt, status):
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
        log_iter = LogLinesIter(logfile, opt.encoding)
    except OSError:
        if debug():
            raise
        return [u"[[[%s:cannotopen]]]\n" % decode_filename(logfile)]

    output = [u"[[[%s]]]\n" % decode_filename(logfile)]

    stat = os.stat(logfile)
    inode = stat.st_ino if is_inode_capable(logfile) else 1

    # Look at which file offset we have finished scanning
    # the logfile last time. If we have never seen this file
    # before, we set the offset to -1
    offset, prev_inode = status.get(logfile, (None, -1))

    # Set the current pointer to the file end
    status[logfile] = stat.st_size, inode

    # If we have never seen this file before, we do not want
    # to make a fuss about ancient log messages... (unless configured to)
    if offset is None and not (opt.fromstart or debug()):
        return output

    # If the inode of the logfile has changed it has appearently
    # been started from new (logfile rotation). At least we must
    # assume that. In some rare cases (restore of a backup, etc)
    # we are wrong and resend old log messages
    if prev_inode >= 0 and inode != prev_inode:
        offset = None

    # Our previously stored offset is the current end ->
    # no new lines in this file
    if offset == stat.st_size:
        return output  # contains logfile name only

    # If our offset is beyond the current end, the logfile has been
    # truncated or wrapped while keeping the same inode. We assume
    # that it contains all new data in that case and restart from
    # beginning.
    if offset > stat.st_size:
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
        if opt.maxlinesize is not None and len(line) > opt.maxlinesize:
            line = line[:opt.maxlinesize] + u"[TRUNCATED]\n"

        lines_parsed += 1
        # Check if maximum number of new log messages is exceeded
        if opt.maxlines is not None and lines_parsed > opt.maxlines:
            warnings_and_errors.append(u"%s Maximum number (%d) of new log messages exceeded.\n" % (
                opt.overflow,
                opt.maxlines,
            ))
            worst = max(worst, opt.overflow_level)
            log_iter.skip_remaining()
            break

        # Check if maximum processing time (per file) is exceeded. Check only
        # every 100'th line in order to save system calls
        if opt.maxtime is not None and lines_parsed % 100 == 10 \
            and time.time() - start_time > opt.maxtime:
            warnings_and_errors.append(
                u"%s Maximum parsing time (%.1f sec) of this log file exceeded.\n" % (
                    opt.overflow,
                    opt.maxtime,
                ))
            worst = max(worst, opt.overflow_level)
            log_iter.skip_remaining()
            break

        level = "."
        for lev, pattern, cont_patterns, replacements in patterns:

            matches = pattern.search(line[:-1])
            if matches:
                level = lev
                levelint = {'C': 2, 'W': 1, 'O': 0, 'I': -1, '.': -1}[lev]
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
                            elif cont_pattern.search(cont_line[:-1]):
                                line = line[:-1] + "\1" + cont_line
                            else:
                                log_iter.push_back_line(cont_line)  # sorry for stealing this line
                                break

                # Replacement
                for replace in replacements:
                    line = replace.replace('\\0', line.rstrip()) + "\n"
                    for num, group in enumerate(matches.groups()):
                        if group is not None:
                            line = line.replace('\\%d' % (num + 1), group)

                break  # matching rule found and executed

        if level == "I":
            level = "."
        if opt.nocontext and level == '.':
            continue

        out_line = "%s %s" % (level, line[:-1])
        if sys.stdout.isatty():
            out_line = "%s%s%s" % (TTY_COLORS[level], out_line.replace(
                "\1", "\nCONT:"), TTY_COLORS['normal'])
        warnings_and_errors.append("%s\n" % out_line)

    new_offset = log_iter.get_position()
    log_iter.close()

    status[logfile] = new_offset, inode

    # Handle option maxfilesize, regardless of warning or errors that have happened
    if opt.maxfilesize and ((offset or 0) // opt.maxfilesize) < (new_offset // opt.maxfilesize):
        warnings_and_errors.append(
            u"%sW Maximum allowed logfile size (%d bytes) exceeded for the %dth time.%s\n" %
            (TTY_COLORS['W'] if sys.stdout.isatty() else '', opt.maxfilesize,
             new_offset // opt.maxfilesize, TTY_COLORS['normal'] if sys.stdout.isatty() else ''))

    # output all lines if at least one warning, error or ok has been found
    if worst > -1:
        output.extend(warnings_and_errors)

    return output


class Options(object):
    """Options w.r.t. logfile patterns (not w.r.t. cluster mapping)."""
    MAP_OVERFLOW = {'C': 2, 'W': 1, 'I': 0, 'O': 0}
    MAP_BOOL = {'true': True, 'false': False, '1': True, '0': False, 'yes': True, 'no': False}
    DEFAULTS = {
        'encoding': None,
        'maxfilesize': None,
        'maxlines': None,
        'maxtime': None,
        'maxlinesize': None,
        'regex': None,
        'overflow': 'C',
        'nocontext': None,
        'maxoutputsize': 500000,  # same as logwatch_max_filesize in check plugin
        'fromstart': False,
    }

    def __init__(self):
        self.values = {}

    @property
    def encoding(self):
        return self._attr_or_default('encoding')

    @property
    def maxfilesize(self):
        return self._attr_or_default('maxfilesize')

    @property
    def maxlines(self):
        return self._attr_or_default('maxlines')

    @property
    def maxtime(self):
        return self._attr_or_default('maxtime')

    @property
    def maxlinesize(self):
        return self._attr_or_default('maxlinesize')

    @property
    def regex(self):
        return self._attr_or_default('regex')

    @property
    def overflow(self):
        return self._attr_or_default('overflow')

    @property
    def nocontext(self):
        return self._attr_or_default('nocontext')

    @property
    def maxoutputsize(self):
        return self._attr_or_default('maxoutputsize')

    @property
    def fromstart(self):
        return self._attr_or_default('fromstart')

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
            key, value = opt_str.split('=', 1)
            if key == 'encoding':
                ''.encode(value)  # make sure it's an encoding
                self.values[key] = value
            elif key in ('maxlines', 'maxlinesize', 'maxfilesize', 'maxoutputsize'):
                self.values[key] = int(value)
            elif key in ('maxtime',):
                self.values[key] = float(value)
            elif key == 'overflow':
                if value not in Options.MAP_OVERFLOW.keys():
                    raise ValueError("Invalid overflow: %r (choose from %r)" % (
                        value,
                        Options.MAP_OVERFLOW.keys(),
                    ))
                self.values['overflow'] = value
            elif key in ('regex', 'iregex'):
                flags = (re.IGNORECASE if key.startswith('i') else 0) | re.UNICODE
                self.values['regex'] = re.compile(value, flags)
            elif key in ('nocontext', 'fromstart'):
                if value.lower() not in Options.MAP_BOOL.keys():
                    raise ValueError("Invalid %s: %r (choose from %r)" % (
                        key,
                        value,
                        Options.MAP_BOOL.keys(),
                    ))
                self.values[key] = Options.MAP_BOOL[value.lower()]
            else:
                raise ValueError("Invalid option: %r" % opt_str)
        except (ValueError, LookupError), exc:
            sys.stdout.write("INVALID CONFIGURATION: %s\n" % exc)
            raise


class LogfilesConfig(object):
    def __init__(self, files, patterns):
        super(LogfilesConfig, self).__init__()
        self.files = files
        self.patterns = patterns


class ClusterConfig(object):
    def __init__(self, name, ips_or_subnets):
        super(ClusterConfig, self).__init__()
        self.name = name
        self.ips_or_subnets = ips_or_subnets


def find_matching_logfiles(glob_pattern):
    """
    Glob matching of hard linked, unbroken soft linked/symlinked files.
    No tilde expansion is done, but *, ?, and character ranges expressed with []
    will be correctly matched. No support for recursive globs ** (supported
    beginning with Python3.5 only). Hard linked dublicates of files are not filtered.
    Soft links may not be detected properly dependent on the Python runtime
    [Python Standard Lib, os.path.islink()].
    """
    files = []
    for match in glob.glob(glob_pattern):
        if os.path.isdir(match):
            continue
        if os.path.islink(match):
            match = os.readlink(match)
        files.append(match)
    return files


def _search_optimize_raw_pattern(raw_pattern):
    """return potentially stripped pattern for use with *search*

    Stripping leading and trailing '.*' avoids catastrophic backtracking
    when long log lines are being processed
    """
    start_idx = 2 if raw_pattern.startswith('.*') else 0
    end_idx = -2 if raw_pattern.endswith('.*') else None
    return raw_pattern[start_idx:end_idx] or raw_pattern


def _compile_continuation_pattern(raw_pattern):
    try:
        return int(raw_pattern)
    except (ValueError, TypeError):
        return re.compile(_search_optimize_raw_pattern(raw_pattern), re.UNICODE)


def _compile_all_expressions(patterns):
    compiled_patterns = []
    for level, raw_pattern, cont_list, rewrite_list in patterns:
        if not rewrite_list:
            # it does not matter what the matched group is in this case
            raw_pattern = _search_optimize_raw_pattern(raw_pattern)
        compiled = re.compile(raw_pattern, re.UNICODE)
        cont_list = [_compile_continuation_pattern(cp) for cp in cont_list]
        compiled_patterns.append((level, compiled, cont_list, rewrite_list))

    return compiled_patterns


def parse_sections(logfiles_config):
    """
    Returns s list of (logfile name, (patterns, options)) tuples and
    and a list of non-matching patterns.
    """
    found_sections = {}
    non_matching_patterns = []

    for cfg in logfiles_config:

        # First read all the options like 'maxlines=100' or 'maxtime=10'
        opt = Options()
        for item in cfg.files:
            if '=' in item:
                opt.set_opt(item)

        # Then handle the file patterns
        for glob_pattern in (f for f in cfg.files if '=' not in f):
            logfiles = find_matching_logfiles(glob_pattern)
            if opt.regex is not None:
                logfiles = [f for f in logfiles if opt.regex.search(f)]
            if not logfiles:
                non_matching_patterns.append(glob_pattern)
            for logfile in logfiles:
                present_patterns, present_options = found_sections.get(logfile, ([], Options()))
                present_patterns.extend(cfg.patterns)
                present_options.update(opt)
                found_sections[logfile] = (present_patterns, present_options)

    matching_patterns = [(logfile, (_compile_all_expressions(patterns), options))
                         for logfile, (patterns, options) in found_sections.iteritems()]

    return matching_patterns, non_matching_patterns


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
    if '/' not in subnetwork:
        ip_integer, version = _ip_to_integer(subnetwork)
        return ip_integer, ip_integer, version
    network_prefix, netmask_len = subnetwork.split('/', 1)
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


def write_output(lines, maxbytes):
    bytecount = 0
    for line in (l.encode('utf-8') for l in lines):
        bytecount += len(line)
        if bytecount > maxbytes:
            break
        sys.stdout.write(line)


def main():

    parse_arguments()

    sys.stdout.write("<<<logwatch>>>\n")

    try:
        # This removes leftover folders which may be generated by crashing frozen binaries
        folder_cleaner = MEIFolderCleaner()
        folder_cleaner.find_and_remove_leftover_folders(hint_filenames=["mk_logwatch.exe.manifest"])
    except Exception, exc:
        sys.stdout.write("ERROR WHILE DOING FOLDER: %s\n" % exc)
        sys.exit(1)

    try:
        files = get_config_files(MK_CONFDIR)
        logfiles_config, cluster_config = read_config(files)
    except Exception, exc:
        if debug():
            raise
        sys.stdout.write(CONFIG_ERROR_PREFIX + "%s\n" % exc)
        sys.exit(1)

    status_filename = get_status_filename(cluster_config)
    # Copy the last known state from the logwatch.state when there is no status_filename yet.
    if not os.path.exists(status_filename) and os.path.exists("%s/logwatch.state" % MK_VARDIR):
        shutil.copy("%s/logwatch.state" % MK_VARDIR, status_filename)

    # Simply ignore errors in the status file.  In case of a corrupted status file we simply begin
    # with an empty status. That keeps the monitoring up and running - even if we might lose a
    # message in the extreme case of a corrupted status file.
    try:
        status = read_status(status_filename)
    except Exception:
        status = {}

    found_sections, non_matching_patterns = parse_sections(logfiles_config)

    for pattern in non_matching_patterns:
        sys.stdout.write((u"[[[%s:missing]]]\n" % decode_filename(pattern)).encode('utf-8'))

    for logfile, (patterns, options) in sorted(found_sections, key=lambda k: k[0]):
        try:
            output = process_logfile(logfile, patterns, options, status)
            write_output(output, options.maxoutputsize)
        except () if debug() else Exception, exc:
            LOGGER.debug("Exception when processing %r: %s", logfile, exc)

    if not debug() and not no_state():
        save_status(status, status_filename)


if __name__ == "__main__":
    main()
