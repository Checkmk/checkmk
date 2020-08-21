// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef Livestatus_h
#define Livestatus_h

#include <stdio.h>

#include <string>
#include <vector>

// simple C++ API for accessing Livestatus from C++,
// currently supports only UNIX sockets, no TCP. But
// this is only a simple enhancement.

class Livestatus {
    int _connection;
    FILE *_file;

public:
    Livestatus() : _connection(-1), _file(0){};
    ~Livestatus();
    void connectUNIX(const char *socketpath);
    bool isConnected() const { return _connection >= 0; };
    void disconnect();
    void sendQuery(const char *query);
    std::vector<std::string> *nextRow();
};

#endif  // Livestatus_h
