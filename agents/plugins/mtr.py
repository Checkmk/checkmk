#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

__version__ = "2.0.0p21"

# This plugin was sponsored by BenV. Thanks!
# https://notes.benv.junerules.com/mtr/

# Concept:
# Read config mtr.cfg
# For every host:
# parse outstanding reports (and delete them)
# If current time > last check + config(time)//300 start new mtr in background
#    MTR results are stored in $VARDIR/mtr_${host}.report
# return previous host data

try:
    import configparser
except ImportError:  # Python 2
    import ConfigParser as configparser  # type: ignore
import glob
import os
import re
import subprocess
import sys
import time

try:
    from typing import Dict, Any
except ImportError:
    pass

mk_confdir = os.getenv("MK_CONFDIR") or "/etc/check_mk"
mk_vardir = os.getenv("MK_VARDIR") or "/var/lib/check_mk_agent"

config_filename = mk_confdir + "/mtr.cfg"
config_dir = mk_confdir + "/mtr.d/*.cfg"
status_filename = mk_vardir + "/mtr.state"
report_filepre = mk_vardir + "/mtr.report."

debug = '-d' in sys.argv[2:] or '--debug' in sys.argv[1:]


def ensure_str(s):
    if sys.version_info[0] >= 3:
        if isinstance(s, bytes):
            return s.decode("utf-8")
    else:
        if isinstance(s, unicode):  # pylint: disable=undefined-variable
            return s.encode("utf-8")
    return s


def read_config():
    default_options = {
        'type': 'icmp',
        'count': "10",
        'force_ipv4': "0",
        'force_ipv6': "0",
        'size': "64",
        'time': "0",
        'dns': "0",
        'port': "",
        'address': "",
        'interval': "",
        'timeout': ""
    }
    if not os.path.exists(config_filename):
        if debug:
            sys.stdout.write("Not configured, %s missing\n" % config_filename)
        sys.exit(0)

    cfg = configparser.SafeConfigParser(default_options)
    # Let ConfigParser figure it out
    for config_file in [config_filename] + glob.glob(config_dir):
        try:
            if not cfg.read(config_file):
                sys.stdout.write("**ERROR** Failed to parse configuration file %s!\n" % config_file)
        except Exception as e:
            sys.stdout.write("**ERROR** Failed to parse config file %s: %s\n" %
                             (config_file, repr(e)))

    if len(cfg.sections()) == 0:
        sys.stdout.write("**ERROR** Configuration defines no hosts!\n")
        sys.exit(0)

    return cfg


# structure of statusfile
# # HOST        |LASTTIME |HOPCOUNT|HOP1|Loss%|Snt|Last|Avg|Best|Wrst|StDev|HOP2|...|HOP8|...|StdDev
# www.google.com|145122481|8|192.168.1.1|0.0%|10|32.6|3.6|0.3|32.6|10.2|192.168.0.1|...|9.8
def read_status():
    current_status = {}  # type: Dict[str, Dict[str, Any]]
    if not os.path.exists(status_filename):
        return current_status

    for line in open(status_filename):
        try:
            parts = line.split('|')
            if len(parts) < 2:
                sys.stdout.write("**ERROR** (BUG) Status has less than 2 parts:\n")
                sys.stdout.write("%s\n" % parts)
                continue
            host = parts[0]
            lasttime = int(parts[1])
            current_status[host] = {'hops': {}, 'lasttime': lasttime}
            hops = int(parts[2])
            for i in range(0, hops):
                current_status[host]["hops"][i + 1] = {
                    'hopname': parts[i * 8 + 3].rstrip(),
                    'loss': parts[i * 8 + 4].rstrip(),
                    'snt': parts[i * 8 + 5].rstrip(),
                    'last': parts[i * 8 + 6].rstrip(),
                    'avg': parts[i * 8 + 7].rstrip(),
                    'best': parts[i * 8 + 8].rstrip(),
                    'wrst': parts[i * 8 + 9].rstrip(),
                    'stddev': parts[i * 8 + 10].rstrip(),
                }
        except Exception as e:
            sys.stdout.write("*ERROR** (BUG) Could not parse status line: %s, reason: %s\n" %
                             (line, repr(e)))
    return current_status


def save_status(current_status):
    f = open(status_filename, "w")
    for host, hostdict in current_status.items():
        hopnum = len(hostdict["hops"].keys())
        lastreport = hostdict["lasttime"]
        hoststring = "%s|%s|%s" % (host, lastreport, hopnum)
        for hop in hostdict["hops"].keys():
            hi = hostdict["hops"][hop]
            hoststring += '|%s|%s|%s|%s|%s|%s|%s|%s' % (
                hi['hopname'],
                hi['loss'],
                hi['snt'],
                hi['last'],
                hi['avg'],
                hi['best'],
                hi['wrst'],
                hi['stddev'],
            )
        hoststring = hoststring.rstrip()
        f.write("%s\n" % hoststring)


_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.:]+')


def host_to_filename(host, delim=u'-'):
    # Get rid of gibberish chars, stolen from Django
    """Generates an slightly worse ASCII-only slug."""
    return ensure_str(delim).join(
        word for word in _punct_re.split(ensure_str(host).lower()) if word)


def check_mtr_pid(pid):
    """ Check for the existence of a unix pid and if the process matches. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False  # process does no longer exist
    else:
        pid_cmdline = "/proc/%d/cmdline" % pid
        try:
            return os.path.exists(pid_cmdline) and \
                   "mtr\x00--report\x00--report-wide" in open(pid_cmdline).read()
        except Exception:
            return False  # any error


def parse_report(host, status):
    reportfile = report_filepre + host_to_filename(host)
    if not os.path.exists(reportfile):
        if not host in status.keys():
            # New host
            status[host] = {'hops': {}, 'lasttime': 0}
        return

    # 1451228358
    # Start: Sun Dec 27 14:35:18 2015
    #HOST: purple         Loss%   Snt   Last   Avg  Best  Wrst StDev
    #  1.|-- 80.69.76.120    0.0%    10    0.3   0.4   0.3   0.6   0.0
    #  2.|-- 80.249.209.100  0.0%    10    1.0   1.1   0.8   1.4   0.0
    #  3.|-- 209.85.240.63   0.0%    10    1.3   1.7   1.1   3.6   0.5
    #  4.|-- 209.85.253.242  0.0%    10    1.6   1.8   1.6   2.1   0.0
    #  5.|-- 209.85.253.201  0.0%    10    4.8   5.0   4.8   5.4   0.0
    #  6.|-- 216.239.56.6    0.0%    10    4.7   5.1   4.7   5.5   0.0
    #  7.|-- ???            100.0    10    0.0   0.0   0.0   0.0   0.0
    #  8.|-- 74.125.136.147  0.0%    10    4.5   4.6   4.3   5.2   0.0
    # See if pidfile exists and if mtr is still running
    if os.path.exists(reportfile + ".pid"):
        # See if it's running
        try:
            pid = int(open(reportfile + ".pid", 'r').readline().rstrip())
            if check_mtr_pid(pid):
                # Still running, we're done.
                if not host in status.keys():
                    # New host
                    status[host] = {'hops': {}, 'lasttime': 0}
                status[host]['running'] = True
                return
        except ValueError:
            # Pid file is broken. Process probably crashed..
            pass
        # Done running, get rid of pid file
        os.unlink(reportfile + ".pid")

    # Parse the existing report
    lines = open(reportfile).readlines()
    if len(lines) < 3:
        sys.stdout.write("**ERROR** Report file %s has less than 3 lines, "
                         "expecting at least 1 hop! Throwing away invalid report\n" % reportfile)
        os.unlink(reportfile)
        if not host in status.keys():
            # New host
            status[host] = {'hops': {}, 'lasttime': 0}
        return
    status[host] = {'hops': {}, 'lasttime': 0}

    hopcount = 0
    status[host]["lasttime"] = int(float(lines.pop(0)))
    while len(lines) > 0 and not lines[0].startswith("HOST:"):
        lines.pop(0)
    if len(lines) < 2:  # Not enough lines
        return
    try:
        lines.pop(0)  # Get rid of HOST: header
        hopline = re.compile(
            r'^\s*\d+\.')  #  10.|-- 129.250.2.147   0.0%    10  325.6 315.5 310.3 325.6   5.0
        for line in lines:
            if not hopline.match(line):
                continue  #     |  `|-- 129.250.2.159
            hopcount += 1
            parts = line.split()
            if len(parts) < 8:
                sys.stdout.write("**ERROR** Bug parsing host/hop, "
                                 "line has less than 8 parts: %s\n" % line)
                continue
            status[host]['hops'][hopcount] = {
                'hopname': parts[1],
                'loss': parts[2],
                'snt': parts[3],
                'last': parts[4],
                'avg': parts[5],
                'best': parts[6],
                'wrst': parts[7],
                'stddev': parts[8],
            }
    except Exception as e:
        sys.stdout.write("**ERROR** Could not parse report file %s, "
                         "tossing away invalid data %s\n" % (reportfile, e))
        del status[host]
    os.unlink(reportfile)


def output_report(host, status):
    hostdict = status.get(host)
    if not hostdict:
        return

    hopnum = len(hostdict["hops"].keys())
    lastreport = hostdict["lasttime"]
    hoststring = "%s|%s|%s" % (host, lastreport, hopnum)
    for hop in hostdict["hops"].keys():
        hi = hostdict["hops"][hop]
        hoststring += '|%s|%s|%s|%s|%s|%s|%s|%s' % (
            hi['hopname'],
            hi['loss'],
            hi['snt'],
            hi['last'],
            hi['avg'],
            hi['best'],
            hi['wrst'],
            hi['stddev'],
        )
    sys.stdout.write("%s\n" % hoststring)


def start_mtr(host, mtr_binary, config, status):
    options = [mtr_binary, '--report', '--report-wide']
    pingtype = config.get(host, "type")
    count = config.getint(host, "count")
    ipv4 = config.getboolean(host, "force_ipv4")
    ipv6 = config.getboolean(host, "force_ipv6")
    size = config.getint(host, "size")
    lasttime = config.getint(host, "time")
    dns = config.getboolean(host, "dns")
    port = config.get(host, "port")
    address = config.get(host, "address")
    interval = config.get(host, "interval")
    timeout = config.get(host, "timeout")

    if "running" in status[host].keys():
        if debug:
            sys.stdout.write("MTR for host still running, not restarting MTR!\n")
        return

    if time.time() - status[host]["lasttime"] < lasttime:
        if debug:
            sys.stdout.write("%s - %s = %s is smaller than %s => mtr run not needed yet.\n" %
                             (time.time(), status[host]["lasttime"],
                              time.time() - status[host]["lasttime"], lasttime))
        return

    pid = os.fork()
    if pid > 0:
        # Parent process, return and keep running
        return

    os.chdir("/")
    os.umask(0)
    os.setsid()

    # Close all fd except stdin,out,err
    for fd in range(3, 256):
        try:
            os.close(fd)
        except OSError:
            pass

    if pingtype == 'tcp':
        options.append("--tcp")
    if pingtype == 'udp':
        options.append("--udp")
    if port:
        options.append("--port")
        options.append(str(port))
    if ipv4:
        options.append("-4")
    if ipv6:
        options.append("-6")
    options.append("-s")
    options.append(str(size))
    options.append("-c")
    options.append(str(count))
    if not dns:
        options.append("--no-dns")
    if address:
        options.append("--address")
        options.append(str(address))
    if interval:
        options.append("-i")
        options.append(str(interval))
    if timeout:
        options.append("--timeout")
        options.append(str(timeout))

    options.append(str(host))
    if debug:
        sys.stdout.write("Startin MTR: %s\n" % (" ".join(options)))
    reportfile = report_filepre + host_to_filename(host)
    if os.path.exists(reportfile):
        os.unlink(reportfile)
    report = open(reportfile, 'a+')
    report.write(str(int(time.time())) + "\n")
    report.flush()
    process = subprocess.Popen(options, stdout=report, stderr=report)
    # Write pid to report.pid
    pidfile = open(reportfile + ".pid", 'w')
    pidfile.write("%d\n" % process.pid)
    pidfile.flush()
    pidfile.close()
    os._exit(os.EX_OK)


def _is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)


def _which(program):

    fpath, _fname = os.path.split(program)
    if fpath:
        if _is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if _is_exe(exe_file):
                return exe_file

    return None


if __name__ == "__main__":
    # See if we have mtr
    mtr_bin = _which('mtr')
    if mtr_bin is None:
        if debug:
            sys.stdout.write("Could not find mtr binary\n")
        sys.exit(0)

    # Parse config
    sys.stdout.write("<<<mtr:sep(124)>>>\n")
    conf = read_config()
    stat = read_status()
    for host_name in conf.sections():
        # Parse outstanding report
        parse_report(host_name, stat)
        # Output last known values
        output_report(host_name, stat)
        # Start new if needed
        start_mtr(host_name, mtr_bin, conf, stat)
    save_status(stat)
