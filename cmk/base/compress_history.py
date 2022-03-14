#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Helper file for more effectively organizing monitoring log files.
# Rewrites existing logfiles for CMC. You can concatenate several
# logfiles and then compress them. Do *not* compress compressed
# files again.
import io
import logging
from typing import Dict, IO, List, Optional, Set, Tuple

import cmk.utils.debug
from cmk.utils.exceptions import MKBailOut
from cmk.utils.log import VERBOSE

logger = logging.getLogger("cmk.base.compress_history")


def do_compress_history(args: List[str]) -> None:
    if not args:
        raise MKBailOut("Please specify files to compress.")

    for filename in args:
        try:
            logger.log(VERBOSE, "%s...", filename)
            compress_history_file(filename, filename + ".compressed")
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKBailOut("%s" % e)


def compress_history_file(input_path: str, output_path: str) -> None:
    known_services: Dict[str, Set[Optional[str]]] = {}
    machine_state = "START"

    with io.open(output_path, "wt") as output:
        with open(input_path) as opened_file:
            for line in opened_file:
                skip_this_line = False
                timestamp = int(line[1:11])
                line_type, host, service = parse_history_line(line)

                logger.debug("%s  (%s) %s / %s / %s", line, machine_state, line_type, host, service)

                if line_type in ("RESTART", "LOGGING_INITIAL"):
                    if machine_state != "START":
                        machine_state = "AFTER_RESTART"
                        services_after_reload: Dict[str, Set[Optional[str]]] = {}
                    if line_type == "LOGGING_INITIAL":
                        skip_this_line = True

                elif line_type == "CURRENT":
                    if host is None:
                        raise Exception(
                            "Unexpected line %s (while in state %s); Host is None"
                            % (line, machine_state)
                        )
                    if machine_state not in ("START", "CURRENT", "AFTER_RESTART"):
                        raise Exception(
                            "Unexpected line %s (while in state %s)" % (line, machine_state)
                        )
                    machine_state = "CURRENT"
                    known_services.setdefault(host, set([])).add(service)

                elif line_type == "INITIAL":
                    if host is None:
                        raise Exception(
                            "Unexpected line %s (while in state %s); Host is None"
                            % (line, machine_state)
                        )

                    if machine_state == "OPERATION":
                        pass  # happens at CMC. That does not create a log entry on reload
                    elif machine_state == "START":
                        machine_state = "INITIAL"
                        known_services.setdefault(host, set([])).add(service)
                        services_after_reload = {}
                    elif machine_state not in ("AFTER_RESTART", "INITIAL"):
                        raise Exception(
                            "Unexpected line %s (while in state %s)" % (line, machine_state)
                        )
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


def parse_history_line(line: str) -> Tuple[str, Optional[str], Optional[str]]:
    command = get_line_command(line)
    if "INITIAL" in command:
        host, service = get_host_service_from_history_line(command, line)
        return "INITIAL", host, service
    if "CURRENT" in command:
        host, service = get_host_service_from_history_line(command, line)
        return "CURRENT", host, service
    if "logging intitial" in command or "logging initial" in command:
        return "LOGGING_INITIAL", None, None
    if "LOG ROTATION" in command or "LOG VERSION" in command:
        return "RESTART", None, None
    return "OPERATION", None, None


def get_host_service_from_history_line(command: str, line: str) -> Tuple[str, Optional[str]]:
    arguments = line.split(":")[1].strip().split(";")
    if "HOST" in command:
        return arguments[0], None
    return arguments[0], arguments[1]


def get_line_command(line: str) -> str:
    if ":" in line:
        return line.split(":")[0].split("]")[1].strip()
    return line.split("]")[1].strip()


def log_vanished_object(output: IO[str], timestamp: int, host: str, service: Optional[str]) -> None:
    if service:
        output.write("[%s] VANISHED SERVICE: %s;%s\n" % (timestamp, host, service))
    else:
        output.write("[%s] VANISHED HOST: %s\n" % (timestamp, host))
