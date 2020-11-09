// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "OutputBuffer.h"

#include <unistd.h>

#include <cerrno>
#include <chrono>
#include <cstddef>
#include <iomanip>

#include "Logger.h"
#include "Poller.h"

using namespace std::chrono_literals;

OutputBuffer::OutputBuffer(int fd, const bool &termination_flag, Logger *logger)
    : _fd(fd)
    , _termination_flag(termination_flag)
    , _logger(logger)
    // TODO(sp) This is really the wrong default because it hides some early
    // errors, e.g. an unknown command. But we can't change this easily because
    // of legacy reasons... :-/
    , _response_header(ResponseHeader::off)
    , _response_code(ResponseCode::ok) {}

OutputBuffer::~OutputBuffer() { flush(); }

void OutputBuffer::flush() {
    if (_response_header == ResponseHeader::fixed16) {
        if (_response_code != ResponseCode::ok) {
            _os.clear();
            _os.str("");
            _os << _error_message;
        }
        auto code = static_cast<unsigned>(_response_code);
        size_t size = _os.tellp();
        std::ostringstream header;
        header << std::setw(3) << std::setfill('0') << code << " "  //
               << std::setw(11) << std::setfill(' ') << size << "\n";
        writeData(header);
    }
    writeData(_os);
}

void OutputBuffer::writeData(std::ostringstream &os) {
    // TODO(sp) This cruel and slightly non-portable hack avoids copying, which
    // is important. Note that UBSan rightly complains about it. We could do
    // better with C++20 via os.view().data().
    struct Hack : public std::stringbuf {
        [[nodiscard]] const char *base() const { return pbase(); }
    };
    const char *buffer = static_cast<Hack *>(os.rdbuf())->base();
    size_t bytes_to_write = os.tellp();
    while (!shouldTerminate() && bytes_to_write > 0) {
        if (!Poller{}.wait(100ms, _fd, PollEvents::out, _logger)) {
            if (errno == ETIMEDOUT) {
                continue;
            }
            break;
        }
        ssize_t bytes_written = write(_fd, buffer, bytes_to_write);
        if (bytes_written == -1) {
            generic_error ge("could not write " +
                             std::to_string(bytes_to_write) +
                             " bytes to client socket");
            Informational(_logger) << ge;
            break;
        }
        buffer += bytes_written;
        bytes_to_write -= bytes_written;
    }
}

void OutputBuffer::setError(ResponseCode code, const std::string &message) {
    Warning(_logger) << "error: " << message;
    // only the first error is being returned
    if (_error_message.empty()) {
        _error_message = message + "\n";
        _response_code = code;
    }
}

std::string OutputBuffer::getError() const { return _error_message; }
