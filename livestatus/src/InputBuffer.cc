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

#include "InputBuffer.h"
#include <unistd.h>
#include <cctype>
#include <cstring>
#include <ostream>
#include <type_traits>
#include "Logger.h"
#include "Poller.h"

namespace {
constexpr size_t initial_buffer_size = 4096;
// TODO(sp): Make this configurable?
constexpr size_t maximum_buffer_size = 500 * 1024 * 1024;

bool timeout_reached(const std::chrono::system_clock::time_point &start,
                     const std::chrono::milliseconds &timeout) {
    return (timeout != std::chrono::milliseconds(0)) &&
           (std::chrono::system_clock::now() - start >= timeout);
}
}  // namespace

std::ostream &operator<<(std::ostream &os, const InputBuffer::Result &r) {
    switch (r) {
        case InputBuffer::Result::request_read:
            return os << "request read";
        case InputBuffer::Result::data_read:
            return os << "data read";
        case InputBuffer::Result::unexpected_eof:
            return os << "unexpected EOF";
        case InputBuffer::Result::should_terminate:
            return os << "should terminate";
        case InputBuffer::Result::line_too_long:
            return os << "line too long";
        case InputBuffer::Result::eof:
            return os << "EOF";
        case InputBuffer::Result::empty_request:
            return os << "empty request";
        case InputBuffer::Result::timeout:
            return os << "timeout";
    }
    return os;  // never reached
}

InputBuffer::InputBuffer(int fd, const bool &termination_flag, Logger *logger,
                         std::chrono::milliseconds query_timeout,
                         std::chrono::milliseconds idle_timeout)
    : _fd(fd)
    , _termination_flag(termination_flag)
    , _query_timeout(query_timeout)
    , _idle_timeout(idle_timeout)
    , _readahead_buffer(initial_buffer_size)
    , _logger(logger) {
    _read_index = 0;   // points to data not yet processed
    _write_index = 0;  // points to end of data in buffer
}

// read in data enough for one complete request (and maybe more).
InputBuffer::Result InputBuffer::readRequest() {
    // Remember when we started waiting for a request. This is needed for the
    // idle_timeout. A connection may not be idle longer than that value.
    auto start_of_idle = std::chrono::system_clock::now();

    // Remember if we have read some part of the query. During
    // a query the timeout is another (short) than between
    // queries.
    bool query_started = false;

    // _read_index points to the place in the buffer, where the
    // next valid data begins. This data ends at _write_index.
    // That data might have been read while reading the previous
    // request.

    // r is used to find the end of the line
    size_t r = _read_index;

    while (true) {
        // Try to find end of the current line in buffer
        while (r < _write_index && _readahead_buffer[r] != '\n') {
            r++;  // now r is at end of data or at '\n'
        }

        // If we cannot find the end of line in the data
        // already read, then we need to read new data from
        // the client.
        if (r == _write_index) {
            // Is there still space left in the buffer => read in
            // further data into the buffer.
            if (_write_index < _readahead_buffer.capacity()) {
                Result rd =
                    readData();  // tries to read in further data into buffer
                if (rd == Result::timeout) {
                    if (query_started) {
                        Informational(_logger)
                            << "Timeout of " << _query_timeout.count()
                            << " ms exceeded while reading query";
                        return Result::timeout;
                    }
                    // Check if we exceeded the maximum time between two queries
                    if (timeout_reached(start_of_idle, _idle_timeout)) {
                        Informational(_logger)
                            << "Idle timeout of " << _idle_timeout.count()
                            << " ms exceeded. Going to close connection.";
                        return Result::timeout;
                    }
                }

                // Are we at end of file? That is only an error, if we've
                // read an incomplete line. If the last thing we read was
                // a linefeed, then we consider the current request to
                // be valid, if it is not empty.
                else if (
                    rd == Result::eof &&
                    r == _read_index /* currently at beginning of a line */) {
                    if (_request_lines.empty()) {
                        return Result::eof;  // empty request -> no request
                    }
                    // socket has been closed but request is complete
                    return Result::request_read;
                    // the current state is now:
                    // _read_index == r == _write_index => buffer is empty
                    // that way, if the main program tries to read the
                    // next request, it will get an IB_UNEXPECTED_EOF

                }
                // if we are *not* at an end of line while reading
                // a request, we got an invalid request.
                else if (rd == Result::eof) {
                    return Result::unexpected_eof;

                    // Other status codes
                } else if (rd == Result::should_terminate) {
                    return rd;
                }
            }
            // OK. So no space is left in the buffer. But maybe at the
            // *beginning* of the buffer is space left again. This is
            // very probable if _write_index == _readahead_buffer.capacity().
            // Most
            // of the buffer's content is already processed. So we simply
            // shift the yet unprocessed data to the very left of the buffer.
            else if (_read_index > 0) {
                size_t shift_by =
                    _read_index;  // distance to beginning of buffer
                size_t size =
                    _write_index - _read_index;  // amount of data to shift
                memmove(&_readahead_buffer[0], &_readahead_buffer[_read_index],
                        size);
                _read_index = 0;  // unread data is now at the beginning
                _write_index -= shift_by;  // write pointer shifted to the left
                r -= shift_by;  // current scan position also shift left
                // continue -> still no data in buffer, but it will
                // be read, as now is space
            }
            // buffer is full, but still no end of line found
            else {
                size_t new_capacity = _readahead_buffer.capacity() * 2;
                if (new_capacity > maximum_buffer_size) {
                    Informational(_logger)
                        << "Error: maximum length of request line exceeded";
                    return Result::line_too_long;
                }
                _readahead_buffer.resize(new_capacity);
            }
        } else  // end of line found
        {
            if (_read_index == r) {  // empty line found => end of request
                _read_index = r + 1;
                // Was ist, wenn noch keine korrekte Zeile gelesen wurde?
                if (_request_lines.empty()) {
                    return Result::empty_request;
                }
                return Result::request_read;

            }  // non-empty line: belongs to current request
            size_t length = r - _read_index;
            for (size_t end = r; end > _read_index &&
                                 (isspace(_readahead_buffer[--end]) != 0);) {
                length--;
            }
            if (length > 0) {
                _request_lines.emplace_back(&_readahead_buffer[_read_index],
                                            length);
            } else {
                Informational(_logger)
                    << "Warning ignoring line containing only whitespace";
            }
            query_started = true;
            _read_index = r + 1;
            r = _read_index;
        }
    }
}

// read at least *some* data. Return IB_TIMEOUT if that lasts more than
// _query_timeout msecs.
InputBuffer::Result InputBuffer::readData() {
    auto start = std::chrono::system_clock::now();
    while (!_termination_flag) {
        if (timeout_reached(start, _query_timeout)) {
            return Result::timeout;
        }

        Poller poller;
        poller.addFileDescriptor(_fd, PollEvents::in);
        int retval = poller.poll(std::chrono::milliseconds(200));
        if (retval > 0 && poller.isFileDescriptorSet(_fd, PollEvents::in)) {
            ssize_t r = read(_fd, &_readahead_buffer[_write_index],
                             _readahead_buffer.capacity() - _write_index);
            if (r < 0) {
                return Result::eof;
            }
            if (r == 0) {
                return Result::eof;
            }
            _write_index += r;
            return Result::data_read;
        }
    }
    return Result::should_terminate;
}

bool InputBuffer::empty() const { return _request_lines.empty(); }

std::string InputBuffer::nextLine() {
    std::string s = _request_lines.front();
    _request_lines.pop_front();
    return s;
}
