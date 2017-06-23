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

// IWYU pragma: no_include <boost/asio/local/basic_endpoint.hpp>
// IWYU pragma: no_include <boost/asio/basic_socket_streambuf.hpp>
#include "EventConsoleConnection.h"
#include <boost/asio/socket_base.hpp>
#include <boost/system/error_code.hpp>
#include <boost/system/system_error.hpp>
#include <chrono>
#include <ostream>
#include <ratio>
#include <thread>
#include <utility>
#include "Logger.h"

using boost::system::system_error;
using std::string;

EventConsoleConnection::EventConsoleConnection(Logger *logger, string path)
    : _logger(logger), _path(std::move(path)) {}

EventConsoleConnection::~EventConsoleConnection() {
    Debug(_logger) << prefix("closing connection");
}

void EventConsoleConnection::run() {
    boost::asio::local::stream_protocol::endpoint ep(_path);
    // Attention, tricky timing-dependent stuff ahead: When we connect very
    // rapidly, a no_buffer_space (= ENOBUFS) error can happen. This is probably
    // caused by some internal Boost Kung Fu, remapping EGAIN to ENOBUFS, and
    // looks like a bug in Boost, but that's a bit unclear. So instead of
    // relying on Boost to retry under these circumstances, we do it ourselves.
    boost::asio::local::stream_protocol::iostream stream;
    while (true) {
        stream.connect(ep);
        if (stream.error() !=
            boost::system::error_code(boost::system::errc::no_buffer_space,
                                      boost::system::system_category())) {
            break;
        }
        Debug(_logger) << "retrying to connect";
        stream.clear();
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }

    check(stream, "connect");
    Debug(_logger) << prefix("successfully connected");

    stream << std::nounitbuf;
    sendRequest(stream);
    stream.flush();
    stream.rdbuf()->shutdown(boost::asio::socket_base::shutdown_send);
    check(stream, "send request");

    receiveReply(stream);
    check(stream, "receive reply");
}

std::string EventConsoleConnection::prefix(const string &message) const {
    return "[mkeventd at " + _path + "] " + message;
}

void EventConsoleConnection::check(
    boost::asio::local::stream_protocol::iostream &stream,
    const std::string &what) const {
    if (!stream && !stream.eof()) {
        // NOTE: Boost's system_error has a mutable string member for lazy
        // construction of what(), this screws up cert-err60-cpp. :-P
        throw system_error(stream.error(), prefix("cannot " + what));  // NOLINT
    }
}
