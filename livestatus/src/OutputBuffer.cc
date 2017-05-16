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
#include <sys/select.h>
#include <unistd.h>
#include <chrono>
#include <cstddef>
#include <iomanip>
#include <ratio>
#include "ChronoUtils.h"
#include "Logger.h"

using std::chrono::milliseconds;
using std::ostringstream;
using std::setfill;
using std::setw;
using std::string;
using std::stringbuf;
using std::to_string;

OutputBuffer::OutputBuffer(int fd, const bool &termination_flag, Logger *logger)
    : _fd(fd)
    , _termination_flag(termination_flag)
    , _logger(logger)
    // TODO(sp) This is really the wrong default because it hides some early
    // errors, e.g. an unknown table name. But we can't change this easily
    // because of legacy reasons... :-/
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
        ostringstream header;
        header << setw(3) << setfill('0') << code << " "  //
               << setw(11) << setfill(' ') << size << "\n";
        writeData(header);
    }
    writeData(_os);
}

void OutputBuffer::writeData(ostringstream &os) {
    // TODO(sp) This cruel and slightly non-portable hack avoids copying (which
    // is important). We could do better by e.g. using boost::asio::streambuf.
    struct Hack : public stringbuf {
        const char *base() const { return pbase(); }
    };
    const char *buffer = static_cast<Hack *>(os.rdbuf())->base();
    size_t bytes_to_write = os.tellp();
    while (!_termination_flag && bytes_to_write > 0) {
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(_fd, &fds);

        timeval tv = to_timeval(milliseconds(100));
        int retval = select(_fd + 1, nullptr, &fds, nullptr, &tv);
        if (retval > 0 && FD_ISSET(_fd, &fds)) {
            ssize_t bytes_written = write(_fd, buffer, bytes_to_write);
            if (bytes_written == -1) {
                generic_error ge("could not write " +
                                 to_string(bytes_to_write) +
                                 " bytes to client socket");
                Informational(_logger) << ge;
                break;
            }
            buffer += bytes_written;
            bytes_to_write -= bytes_written;
        }
    }
}

void OutputBuffer::setError(ResponseCode code, const string &message) {
    Warning(_logger) << "error: " << message;
    // only the first error is being returned
    if (_error_message == "") {
        _error_message = message + "\n";
        _response_code = code;
    }
}
