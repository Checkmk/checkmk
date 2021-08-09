// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "Livestatus.h"

#include <fcntl.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>

void Livestatus::connectUNIX(const char *socket_path) {
    _connection = ::socket(PF_LOCAL, SOCK_STREAM, 0);
    struct sockaddr_un sockaddr;
    sockaddr.sun_family = AF_UNIX;
    strncpy(sockaddr.sun_path, socket_path, sizeof(sockaddr.sun_path) - 1);
    sockaddr.sun_path[sizeof(sockaddr.sun_path) - 1] = '\0';
    if (0 > connect(_connection, (const struct sockaddr *)&sockaddr,
                    sizeof(sockaddr))) {
        ::close(_connection);
        _connection = -1;
    } else
        _file = fdopen(_connection, "r");
}

Livestatus::~Livestatus() { disconnect(); }

void Livestatus::disconnect() {
    if (isConnected()) {
        if (_file)
            fclose(_file);
        else
            ::close(_connection);
    }
    _connection = -1;
    _file = 0;
}

void Livestatus::sendQuery(const char *query) {
    ::write(_connection, query, strlen(query));
    std::string separators = "Separators: 10 1 2 3\n";
    ::write(_connection, separators.c_str(), separators.size());
    shutdown(_connection, SHUT_WR);
}

std::vector<std::string> *Livestatus::nextRow() {
    char line[65536];
    if (0 != fgets(line, sizeof(line), _file)) {
        // strip trailing linefeed
        char *end = strlen(line) + line;
        if (end > line && *(end - 1) == '\n') {
            *(end - 1) = 0;
            --end;
        }
        std::vector<std::string> *row = new std::vector<std::string>;
        char *scan = line;
        while (scan < end) {
            char *zero = scan;
            while (zero < end && *zero != '\001') zero++;
            *zero = 0;
            row->push_back(std::string(scan));
            scan = zero + 1;
        }
        return row;
    } else
        return 0;
}
