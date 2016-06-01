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

// TODO(sp): Find a nicer way to teach IWYU about this part of Boost.
// IWYU pragma: no_include <boost/asio/basic_socket_streambuf.hpp>
// IWYU pragma: no_include <boost/asio/buffer.hpp>
// IWYU pragma: no_include <boost/asio/detail/impl/epoll_reactor.hpp>
// IWYU pragma: no_include <boost/asio/detail/impl/reactive_socket_service_base.ipp>
// IWYU pragma: no_include <boost/asio/detail/impl/service_registry.hpp>
// IWYU pragma: no_include <boost/asio/detail/impl/task_io_service.hpp>
// IWYU pragma: no_include <boost/asio/detail/impl/timer_queue_ptime.ipp>
// IWYU pragma: no_include <boost/asio/error.hpp>
// IWYU pragma: no_include <boost/asio/impl/io_service.hpp>
// IWYU pragma: no_include <boost/asio/impl/io_service.ipp>
// IWYU pragma: no_include <boost/asio/local/detail/impl/endpoint.ipp>
// IWYU pragma: no_include <boost/system/error_code.hpp>

// IWYU pragma: no_include <bits/socket_type.h>
#include "TableEventConsole.h"
#include <errno.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <algorithm>
#include <iostream>
#include <string>
#include <utility>
#include <vector>
#include "Column.h"
#include "Logger.h"
#include "Query.h"
#ifdef CMC
#include "Core.h"
#include "World.h"
#endif

// using boost::asio::local::stream_protocol;
using std::string;
using std::vector;

namespace {
struct MkEventD {
    explicit MkEventD(string path) : _msg(std::move(path)) {}
#if 0
    MkEventD(const string &path, const stream_protocol::iostream &ios)
        : _msg(path + ": " + ios.error().message()) {}
#else
    MkEventD(const string &path, int errc)
        : _msg(path + ": " + strerror(errc)) {}
#endif
    const string _msg;
    friend std::ostream &operator<<(std::ostream &os, const MkEventD &m) {
        return os << "mkeventd at " << m._msg;
    }
};
}  // namespace

#ifdef CMC
TableEventConsole::TableEventConsole(Core *core) : _core(core) {}
TableEventConsole::TableEventConsole() : _core(nullptr) {}
#else
TableEventConsole::TableEventConsole() {}
#endif

void TableEventConsole::answerQuery(Query *query) {
#if 0
    string path = "/omd/sites/heute/tmp/run/mkeventd/status";
    stream_protocol::endpoint ep(path);
    stream_protocol::iostream ios(ep);
    if (!ios) {
        Alert() << "Cannot connect to " << MkEventD(path, ios);
        return;
    }
#else
    string path = "/omd/sites/heute/tmp/run/mkeventd/status";
    int sock = socket(PF_LOCAL, SOCK_STREAM, 0);
    if (sock == -1) {
        Alert() << "Cannot create socket for " << MkEventD(path, errno);
        return;
    }

    struct sockaddr_un sa;
    sa.sun_family = AF_LOCAL;
    strncpy(sa.sun_path, path.c_str(), sizeof(sa.sun_path));
    if (connect(sock, reinterpret_cast<const struct sockaddr *>(&sa),
                sizeof(sockaddr_un)) == -1) {
        Alert() << "Cannot connect to " << MkEventD(path, errno);
        close(sock);
        return;
    }
#endif
    Notice() << "Successfully connected to " << MkEventD(path);
#if 0
    sendRequest(ios, query);
    if (!ios) {
        Alert() << "Cannot write to " << MkEventD(path, ios);
        return;
    }
    receiveReply(ios, query);
    if (ios.bad()) {
        Alert() << "Cannot read from " << MkEventD(path, ios);
    }
#else
    if (!sendRequest(sock, query)) {
        Alert() << "Cannot write to " << MkEventD(path, errno);
        close(sock);
        return;
    }
    if (!receiveReply(sock, query)) {
        Alert() << "Cannot read from " << MkEventD(path, errno);
    }
    close(sock);
#endif
    Notice() << "Closing connection to " << MkEventD(path);
}

// static
vector<string> TableEventConsole::split(string str, char delimiter) {
    std::istringstream iss(str);
    vector<string> result;
    string field;
    while (std::getline(iss, field, delimiter)) {
        result.push_back(field);
    }
    return result;
}

string TableEventConsole::internalName() const {
    return name() + 12;  // skip "eventconsole" prefix :-P
}

#if 0
void TableEventConsole::sendRequest(stream_protocol::iostream &ios,
                                    Query *query) {
    // NOTE: The EC ignores Columns: at the moment!
    ios << std::nounitbuf
        << "GET " + internalName() + "\nOutputFormat: plain\nColumns:";
    for (const auto &c : *query->allColumns()) {
        ios << " " << c->name();
    }
    ios << std::endl;
    ios.rdbuf()->shutdown(stream_protocol::socket::shutdown_send);
}
#else
bool TableEventConsole::sendRequest(int sock, Query *query) {
    // NOTE: The EC ignores Columns: at the moment!
    string ec_query =
        "GET " + internalName() + "\nOutputFormat: plain\nColumns:";
    for (const auto &c : *query->allColumns()) {
        ec_query += " " + string(c->name());
    }

    const char *buffer = ec_query.c_str();
    size_t bytes_to_write = ec_query.size();
    while (bytes_to_write > 0) {
        ssize_t bytes_written = write(sock, buffer, bytes_to_write);
        if (bytes_written == -1) {
            return false;
        }
        buffer += bytes_written;
        bytes_to_write -= bytes_written;
    }

    return shutdown(sock, SHUT_WR) == 0;
}
#endif

#if 0
void TableEventConsole::receiveReply(stream_protocol::iostream &ios,
                                     Query *query) {
    bool is_header = true;
    vector<string> headers;
    do {
        string line;
        std::getline(ios, line);
        if (ios.bad() || line.empty()) {
            return;
        }
        vector<string> columns = split(line, '\t');
        if (is_header) {
            headers = std::move(columns);
            is_header = false;
        } else {
            _row_t row;
            int i = 0;
            columns.resize(headers.size());  // just to be sure...
            for (const auto &field : columns) {
                row[headers[i++]] = field;
            }
            query->processDataset(&row);
        }
    } while (true);
}
#else
namespace {
// TODO(sp) Horribly inefficient, must be replaced.
bool getline(int sock, string &line) {
    line = "";
    line.reserve(4096);
    do {
        char c;
        ssize_t res = read(sock, &c, 1);
        if (res == 1) {
            if (c == '\n') {
                return true;
            }
            line.push_back(c);
        }
        if (res == 0) {
            return true;
        }
        if (res == -1) {
            return false;
        }
    } while (true);
    return false;  // unreachable
}
}  // namespace

bool TableEventConsole::receiveReply(int sock, Query *query) {
    bool is_header = true;
    vector<string> headers;
    do {
        string line;
        if (!getline(sock, line)) {
            return false;
        }
        if (line.empty()) {
            return true;
        }
        vector<string> columns = split(line, '\t');
        if (is_header) {
            headers = std::move(columns);
            is_header = false;
        } else {
            Row row;
            int i = 0;
            columns.resize(headers.size());  // just to be sure...
            for (const auto &field : columns) {
                row._map[headers[i++]] = field;
            }

            auto it = row._map.find("event_host");
#ifdef CMC
            row._host = (it == row._map.end() || _core == nullptr)
                            ? nullptr
                            : _core->_world->getHostByDesignation(it->second);
#else
            // Older Nagios headers are not const-correct... :-P
            row._host = it == row._map.end()
                            ? nullptr
                            : find_host(const_cast<char *>(it->second.c_str()));
#endif
            query->processDataset(&row);
        }
    } while (true);
    return true;
}
#endif
