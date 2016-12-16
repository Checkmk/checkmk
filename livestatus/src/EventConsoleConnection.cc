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
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include "EventConsoleConnection.h"
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <cstring>
#include <sstream>
#include <utility>

using std::move;
using std::ostream;
using std::ostringstream;
using std::string;

EventConsoleConnection::EventConsoleConnection(Logger *logger, string path)
    : _path(move(path))
    , _name("[mkeventd at " + _path + "]")
    , _socket(-1)
    , _logger(logger, [this](ostream &os) { os << _name; }) {}

void EventConsoleConnection::run() {
    _socket = socket(PF_UNIX, SOCK_STREAM, 0);
    if (_socket == -1) {
        throwGenericError("cannot create socket");
    }
    struct sockaddr_un sa;
    sa.sun_family = AF_UNIX;
    strncpy(sa.sun_path, _path.c_str(), sizeof(sa.sun_path));
    if (connect(_socket, reinterpret_cast<const struct sockaddr *>(&sa),
                sizeof(sockaddr_un)) == -1) {
        throwGenericError("cannot connect");
    }
    Debug(&_logger) << "successfully connected";
    if (!writeRequest()) {
        throwGenericError("cannot write");
    }
    if (!receiveReply()) {
        throwGenericError("cannot read");
    }
    close();
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

void EventConsoleConnection::close() {
    if (_socket != -1) {
        Debug(&_logger) << "closing connection";
        ::close(_socket);
    }
}

void EventConsoleConnection::throwGenericError(const string &what_arg) {
    generic_error ge(_name + " " + what_arg);
    Alert(&_logger) << ge;
    close();
    throw move(ge);
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
