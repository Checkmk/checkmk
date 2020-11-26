// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "EventConsoleConnection.h"

#include <asio/basic_socket_streambuf.hpp>
#include <asio/error.hpp>
#include <asio/error_code.hpp>
#include <asio/socket_base.hpp>
#include <asio/system_error.hpp>
#include <chrono>
#include <ostream>
#include <system_error>  // IWYU pragma: keep  // CI wants it
#include <thread>
#include <utility>

#include "Logger.h"

using namespace std::chrono_literals;

EventConsoleConnection::EventConsoleConnection(Logger *logger, std::string path)
    : _logger(logger), _path(std::move(path)) {}

EventConsoleConnection::~EventConsoleConnection() {
    Debug(_logger) << prefix("closing connection");
}

void EventConsoleConnection::run() {
    asio::local::stream_protocol::endpoint ep(_path);
    // Attention, tricky timing-dependent stuff ahead: When we connect very
    // rapidly, a no_buffer_space (= ENOBUFS) error can happen. This is probably
    // caused by some internal asio Kung Fu, remapping EGAIN to ENOBUFS, and
    // looks like a bug in asio, but that's a bit unclear. So instead of
    // relying on asio to retry under these circumstances, we do it ourselves.
    asio::local::stream_protocol::iostream stream;
    while (true) {
        stream.connect(ep);
        if (stream.error() != asio::error_code(asio::error::no_buffer_space,
                                               asio::system_category())) {
            break;
        }
        Debug(_logger) << "retrying to connect";
        stream.clear();
        std::this_thread::sleep_for(1ms);
    }

    check(stream, "connect");
    Debug(_logger) << prefix("successfully connected");

    stream << std::nounitbuf;
    sendRequest(stream);
    stream.flush();
    stream.rdbuf()->shutdown(asio::socket_base::shutdown_send);
    check(stream, "send request");

    receiveReply(stream);
    check(stream, "receive reply");
}

std::string EventConsoleConnection::prefix(const std::string &message) const {
    return "[mkeventd at " + _path + "] " + message;
}

void EventConsoleConnection::check(
    asio::local::stream_protocol::iostream &stream,
    const std::string &what) const {
    if (!stream && !stream.eof()) {
        throw asio::system_error(stream.error(), prefix("cannot " + what));
    }
}
