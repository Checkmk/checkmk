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
#include "EventConsoleConnection.h"
#include <errno.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <sstream>
#include <utility>
#include "Logger.h"

using std::move;
using std::ostream;
using std::ostringstream;
using std::string;

namespace {
struct MkEventD {
    explicit MkEventD(string path) : _msg(move(path)) {}
    MkEventD(const string &path, int errc)
        : _msg(path + ": " + strerror(errc)) {}
    const string _msg;
    friend ostream &operator<<(ostream &os, const MkEventD &m) {
        return os << "mkeventd at " << m._msg;
    }
};
}  // namespace

EventConsoleConnection::EventConsoleConnection(string path)
    : _path(move(path)), _socket(-1) {}

void EventConsoleConnection::run() {
    _socket = socket(PF_LOCAL, SOCK_STREAM, 0);
    if (_socket == -1) {
        Alert() << "Cannot create socket for " << MkEventD(_path, errno);
        return;
    }

    struct sockaddr_un sa;
    sa.sun_family = AF_LOCAL;
    strncpy(sa.sun_path, _path.c_str(), sizeof(sa.sun_path));
    if (connect(_socket, reinterpret_cast<const struct sockaddr *>(&sa),
                sizeof(sockaddr_un)) == -1) {
        Alert() << "Cannot connect to " << MkEventD(_path, errno);
        close(_socket);
        return;
    }
    Notice() << "Successfully connected to " << MkEventD(_path);

    if (!writeRequest()) {
        Alert() << "Cannot write to " << MkEventD(_path, errno);
    } else if (!receiveReply()) {
        Alert() << "Cannot read from " << MkEventD(_path, errno);
    }

    Notice() << "Closing connection to " << MkEventD(_path);
    close(_socket);
}

// TODO(sp) Horribly inefficient, must be replaced.
bool EventConsoleConnection::getline(string &line) {
    line = "";
    line.reserve(4096);
    do {
        char c;
        ssize_t res = read(_socket, &c, 1);
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

bool EventConsoleConnection::writeRequest() {
    ostringstream os;
    sendRequest(os);
    os.flush();  // probably not needed, but just to be sure...
    string request = os.str();

    const char *buffer = request.c_str();
    size_t bytes_to_write = request.size();
    while (bytes_to_write > 0) {
        ssize_t bytes_written = write(_socket, buffer, bytes_to_write);
        if (bytes_written == -1) {
            return false;
        }
        buffer += bytes_written;
        bytes_to_write -= bytes_written;
    }

    return shutdown(_socket, SHUT_WR) == 0;
}
