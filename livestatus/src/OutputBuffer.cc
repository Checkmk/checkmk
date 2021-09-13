// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#include "OutputBuffer.h"

#include <chrono>
#include <cstddef>
#include <iomanip>
#include <string_view>
#include <utility>

#include "Logger.h"
#include "POSIXUtils.h"

using namespace std::chrono_literals;

OutputBuffer::OutputBuffer(int fd, std::function<bool()> should_terminate,
                           Logger *logger)
    : _fd(fd)
    , should_terminate_{std::move(should_terminate)}
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

namespace {
// TODO(sp) This cruel and slightly non-portable hack avoids copying, which
// is important. Note that UBSan rightly complains about it. We could do
// better with C++20 via os.view().
std::string_view toStringView(std::ostringstream &os) {
    struct Hack : public std::stringbuf {
        [[nodiscard]] const char *base() const { return pbase(); }
    };
    return {static_cast<Hack *>(os.rdbuf())->base(),
            static_cast<size_t>(os.tellp())};
}
}  // namespace

void OutputBuffer::writeData(std::ostringstream &os) {
    if (writeWithTimeoutWhile(_fd, toStringView(os), 100ms,
                              [this]() { return !shouldTerminate(); }) == -1) {
        generic_error ge{"cannot write to client socket"};
        Informational(_logger) << ge;
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
