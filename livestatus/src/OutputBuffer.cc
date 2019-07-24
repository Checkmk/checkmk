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

#include "OutputBuffer.h"
#include <unistd.h>
#include <chrono>
#include <cstddef>
#include <iomanip>
#include "Logger.h"
#include "Poller.h"

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
    // TODO(sp) This cruel and slightly non-portable hack avoids copying (which
    // is important). We could do better by e.g. using boost::asio::streambuf.
    struct Hack : public std::stringbuf {
        [[nodiscard]] const char *base() const { return pbase(); }
    };
    const char *buffer = static_cast<Hack *>(os.rdbuf())->base();
    size_t bytes_to_write = os.tellp();
    while (!shouldTerminate() && bytes_to_write > 0) {
        Poller poller;
        poller.addFileDescriptor(_fd, PollEvents::out);
        int retval = poller.poll(std::chrono::milliseconds(100));
        if (retval > 0 && poller.isFileDescriptorSet(_fd, PollEvents::out)) {
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
}

void OutputBuffer::setError(ResponseCode code, const std::string &message) {
    Warning(_logger) << "error: " << message;
    // only the first error is being returned
    if (_error_message.empty()) {
        _error_message = message + "\n";
        _response_code = code;
    }
}
