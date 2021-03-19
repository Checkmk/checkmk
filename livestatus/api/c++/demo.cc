// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include <stdio.h>

#include "Livestatus.h"

const char *query =
    "GET status\nColumns: livestatus_version program_version\nColumnHeaders: on\n";

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s SOCKETPATH\n", argv[0]);
        return 1;
    }

    const char *socket_path = argv[1];
    Livestatus live;
    live.connectUNIX(socket_path);
    if (live.isConnected()) {
        fprintf(stderr, "Couldn't connect to socket '%s'\n", socket_path);
        return 1;
    }
    live.sendQuery(query);
    std::vector<std::string> *row;
    while (0 != (row = live.nextRow())) {
        printf("Line:\n");
        for (size_t i = 0; i < row->size(); i++)
            printf("%s\n", (*row)[i].c_str());
        delete row;
    }
    live.disconnect();
    return 0;
}
