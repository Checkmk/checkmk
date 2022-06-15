#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# "How to talk to the mkeventd", Python edition :-)

import json
import os
import socket


class EventConsoleConnection(object):
    def __init__(self, path, timeout=3) -> None:
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.settimeout(timeout)
        self._socket.connect(path)
        self._buffer = ""

    def send_request(self, r):
        self._socket.sendall(r)
        self._socket.shutdown(socket.SHUT_WR)

    def read_response(self):
        """Return the whole response as a byte string"""
        buffer = ""
        while True:
            data = self._socket.recv(4096)
            if len(data) == 0:
                return buffer
            buffer += data

    def lines(self):
        return ResponseLines(self._socket)

    def close(self):
        self._socket.close()

    def __iter__(self):
        """Return an iterator for reading the response as Unicode lines"""
        return self

    def __next__(self):
        while True:
            parts = self._buffer.split("\n", 1)
            if len(parts) > 1:
                break
            data = self._socket.recv(4096)
            if len(data) == 0:
                if len(self._buffer) == 0:
                    raise StopIteration()
                parts = [self._buffer, ""]
                break
            self._buffer += data
        line_, self._buffer = parts
        return line_.decode("utf-8").splitlines()

    def __enter__(self):
        return self

    def __exit__(self, ty, value, traceback):
        self.close()


def request(what, path):
    """Submit a request to the event console, returning the reply as a python object"""
    with EventConsoleConnection(path) as c:
        c.send_request(what + "\nOutputFormat: json")
        return json.loads(c.read_response())


################################################################################

status_path = os.getenv("OMD_ROOT") + "/tmp/run/mkeventd/status"

# read the response line by line
with EventConsoleConnection(status_path) as ec:
    ec.send_request("GET status\nOutputFormat: plain")
    for line in ec:
        print(line)

# read the whole response in one go
with EventConsoleConnection(status_path) as ec:
    ec.send_request("GET status\nOutputFormat: python")
    print(ec.read_response())

# use the convenience function
print(request("GET status", status_path))
print(request("COMMAND SYNC", status_path))
print(request("REPLICATE 1488791495", status_path))
