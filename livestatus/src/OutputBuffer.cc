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
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ostream>
#include <ratio>
#include "ChronoUtils.h"
#include "Logger.h"

using std::chrono::milliseconds;
using std::string;
using std::to_string;
using std::vector;

OutputBuffer::OutputBuffer(Logger *logger) : _max_size(1), _logger(logger) {
    _buffer = static_cast<char *>(malloc(_max_size));
    _end = _buffer + _max_size;
    reset();
}

OutputBuffer::~OutputBuffer() { free(_buffer); }

void OutputBuffer::reset() {
    _writepos = _buffer;
    _response_header = ResponseHeader::off;
    _response_code = ResponseCode::ok;
    _do_keepalive = false;
    _error_message = "";
}

void OutputBuffer::add(const string &str) {
    addBuffer(str.c_str(), str.size());
}

void OutputBuffer::add(const vector<char> &blob) {
    addBuffer(&blob[0], blob.size());
}

void OutputBuffer::addBuffer(const char *buf, size_t len) {
    needSpace(len);
    memcpy(_writepos, buf, len);
    _writepos += len;
}

// TODO(sp): All this code is highly error-prone due to overflow, failed
// allocations
// etc. We should just use vector instead.
void OutputBuffer::needSpace(unsigned len) {
    if (_writepos + len > _end) {
        unsigned s = size();
        unsigned needed = s + len;
        while (_max_size < needed) {  // double, until enough space
            _max_size *= 2;
        }

        char *new_buffer = static_cast<char *>(realloc(_buffer, _max_size));
        // It's better to crash voluntarily than overwriting random memory
        // later.
        if (new_buffer == nullptr) {
            abort();
        }

        _buffer = new_buffer;
        _writepos = _buffer + s;
        _end = _buffer + _max_size;
    }
}

void OutputBuffer::flush(int fd, int *termination_flag) {
    if (_response_header == ResponseHeader::fixed16) {
        const char *buffer = _buffer;
        int s = size();

        // if response code is not OK, output error
        // message instead of data
        if (_response_code != ResponseCode::ok) {
            buffer = _error_message.c_str();
            s = _error_message.size();
        }

        char header[17];
        snprintf(header, sizeof(header), "%03u %11d\n",
                 static_cast<unsigned>(_response_code), s);
        writeData(fd, termination_flag, header, 16);
        writeData(fd, termination_flag, buffer, s);
    } else {
        writeData(fd, termination_flag, _buffer, size());
    }
    reset();
}

void OutputBuffer::writeData(int fd, int *termination_flag, const char *buffer,
                             size_t bytes_to_write) {
    while (*termination_flag == 0 && bytes_to_write > 0) {
        fd_set fds;
        FD_ZERO(&fds);
        FD_SET(fd, &fds);

        timeval tv = to_timeval(milliseconds(100));
        int retval = select(fd + 1, nullptr, &fds, nullptr, &tv);
        if (retval > 0 && FD_ISSET(fd, &fds)) {
            ssize_t bytes_written = write(fd, buffer, bytes_to_write);
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
    // only the first error is being returned
    if (_error_message == "") {
        Informational(_logger) << "error: " << message;
        _error_message = message + "\n";
        _response_code = code;
    }
}
