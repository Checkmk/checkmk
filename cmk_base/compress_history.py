#!/usr/bin/python
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

# Helper file for more effectively organizing monitoring log files.
# Rewrites existing logfiles for CMC. You can concatenate several
# logfiles and then compress them. Do *not* compress compressed
# files again.
import logging

from cmk.utils.exceptions import MKBailOut
import cmk.utils.debug

logger = logging.getLogger("cmk.base.compress_history")


def do_compress_history(args):
    if not args:
        raise MKBailOut("Please specify files to compress.")

    for filename in args:
        try:
            logger.verbose("%s...", filename)
            compress_history_file(filename, filename + ".compressed")
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKBailOut("%s" % e)


def compress_history_file(input_path, output_path):
    known_services = {}
    machine_state = "START"

    output = file(output_path, "w")
    for line in file(input_path):
        skip_this_line = False
        timestamp = int(line[1:11])
        line_type, host, service = parse_history_line(line)

        logger.debug("%s  (%s) %s / %s / %s", line, machine_state, line_type, host, service)

        if line_type == "RESTART" or line_type == "LOGGING_INITIAL":
            if machine_state != "START":
                machine_state = "AFTER_RESTART"
                services_after_reload = {}
            if line_type == "LOGGING_INITIAL":
                skip_this_line = True

        elif line_type == "CURRENT":
            if machine_state not in ("START", "CURRENT", "AFTER_RESTART"):
                raise Exception("Unexpected line %s (while in state %s)" % (line, machine_state))
            machine_state = "CURRENT"
            known_services.setdefault(host, set([])).add(service)

        elif line_type == "INITIAL":
            if machine_state == "OPERATION":
                pass  # happens at CMC. That does not create a log entry on reload
            elif machine_state == "START":
                machine_state = "INITIAL"
                known_services.setdefault(host, set([])).add(service)
                services_after_reload = {}
            elif machine_state not in ("AFTER_RESTART", "INITIAL"):
                raise Exception("Unexpected line %s (while in state %s)" % (line, machine_state))
            else:
                machine_state = "INITIAL"
                services_after_reload.setdefault(host, set([])).add(service)
                if host in known_services and service in known_services[host]:
                    skip_this_line = True

        elif line_type == "OPERATION":
            if machine_state != "START":
                if machine_state == "INITIAL":
                    for host in known_services:
                        if host not in services_after_reload:
                            for service in known_services[host]:
                                log_vanished_object(output, timestamp, host, service)
                            del known_services[host]
                        else:
                            known = known_services[host]
                            after_reload = services_after_reload[host]
                            for service in list(known):
                                if service not in after_reload:
                                    log_vanished_object(output, timestamp, host, service)
                                    known.remove(service)
                machine_state = "OPERATION"
        else:
            pass

        if not skip_this_line:
            output.write(line)


def parse_history_line(line):
    command = get_line_command(line)
    if "INITIAL" in command:
        host, service = get_host_service_from_history_line(command, line)
        return "INITIAL", host, service
    elif "CURRENT" in command:
        host, service = get_host_service_from_history_line(command, line)
        return "CURRENT", host, service
    elif "logging intitial" in command \
        or "logging initial" in command:
        return "LOGGING_INITIAL", None, None
    elif "LOG ROTATION" in command \
        or "LOG VERSION" in command:
        return "RESTART", None, None
    return "OPERATION", None, None


def get_host_service_from_history_line(command, line):
    arguments = line.split(":")[1].strip().split(";")
    if "HOST" in command:
        return arguments[0], None
    return arguments[0], arguments[1]


def get_line_command(line):
    if ":" in line:
        return line.split(":")[0].split("]")[1].strip()
    return line.split("]")[1].strip()


def log_vanished_object(output, timestamp, host, service):
    if service:
        output.write("[%s] VANISHED SERVICE: %s;%s\n" % (timestamp, host, service))
    else:
        output.write("[%s] VANISHED HOST: %s\n" % (timestamp, host))
