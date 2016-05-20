// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

// IWYU pragma: no_include <bits/socket_type.h>
#include "TableEventConsole.h"
#include <errno.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <syslog.h>
#include <unistd.h>
#include <memory>
#include <sstream>
#include <vector>
#include "Column.h"
#include "Query.h"
#include "logger.h"

using std::istringstream;
using std::string;
using std::vector;

namespace {
// TODO(sp) Horribly inefficient, must be replaced.
string readLine(int sock) {
    string line;
    line.reserve(4096);
    do {
        char c;
        ssize_t res = read(sock, &c, 1);
        if (res == 1) {
            if (c == '\n') {
                logger(LOG_DEBUG, "mkeventd returned line: [%s]", line.c_str());
                return line;
            }
            line.push_back(c);
        }
        if (res == 0) {
            return line;
        }
        if (res == -1) {
            logger(LOG_ALERT, "Cannot read reply from mkeventd: %s",
                   strerror(errno));
            return line;
        }
    } while (true);
    return line;  // unreachable
}

vector<string> split(string str, char delimiter = '\t') {
    istringstream iss(str);
    vector<string> result;
    string field;
    while (getline(iss, field, delimiter)) {
        result.push_back(field);
    }
    return result;
}

};  // namespace

void TableEventConsole::answerQuery(Query *query) {
    string path = "/omd/sites/heute/tmp/run/mkeventd/status";
    int sock = socket(PF_LOCAL, SOCK_STREAM, 0);
    if (sock == -1) {
        logger(LOG_ALERT, "Cannot create socket for connection to mkeventd: %s",
               strerror(errno));
        return;
    }

    struct sockaddr_un sa;
    sa.sun_family = AF_LOCAL;
    strncpy(sa.sun_path, path.c_str(), sizeof(sa.sun_path));
    if (connect(sock, reinterpret_cast<const struct sockaddr *>(&sa),
                sizeof(sockaddr_un)) == -1) {
        logger(LOG_ALERT, "Cannot connect to mkeventd at %s: %s", path.c_str(),
               strerror(errno));
        close(sock);
        return;
    }

    logger(LOG_NOTICE, "Successfully connected to mkeventd at %s",
           path.c_str());

    // NOTE: The EC ignores Columns: at the moment!
    string table_name = name() + 12;  // skip "eventconsole" prefix;
    string ec_query = "GET " + table_name + "\nOutputFormat: plain\nColumns:";
    for (const auto &c : *query->allColumns()) {
        ec_query += " " + string(c->name());
    }
    logger(LOG_DEBUG, "Sending query to event console: [%s]", ec_query.c_str());

    const char *buffer = ec_query.c_str();
    size_t bytes_to_write = ec_query.size();
    while (bytes_to_write > 0) {
        ssize_t bytes_written = write(sock, buffer, bytes_to_write);
        if (bytes_written == -1) {
            logger(LOG_ALERT, "Cannot write quey to mkeventd: %s",
                   strerror(errno));
            close(sock);
            return;
        }
        buffer += bytes_written;
        bytes_to_write -= bytes_written;
    }

    vector<string> headers = split(readLine(sock));

    do {
        string line = readLine(sock);
        if (line.empty()) {
            break;
        }
        _row_t row;
        int i = 0;
        for (const auto &field : split(line)) {
            logger(LOG_DEBUG, "setting EC column \"%s\" to \"%s\"",
                   headers[i].c_str(), field.c_str());
            row[headers[i++]] = field;
        }
        query->processDataset(&row);
    } while (true);

    close(sock);
    logger(LOG_NOTICE, "Closed connection to mkeventd at %s", path.c_str());
}
