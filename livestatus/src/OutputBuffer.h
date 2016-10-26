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

#ifndef OutputBuffer_h
#define OutputBuffer_h

#include "config.h"  // IWYU pragma: keep
#include <cstddef>
#include <string>
#include <vector>
class Logger;

class OutputBuffer {
public:
    enum class ResponseCode {
        ok = 200,
        invalid_header = 400,
        unauthorized = 403,
        not_found = 404,
        limit_exceeded = 413,
        incomplete_request = 451,
        invalid_request = 452,
        unknown_column = 450,
    };

    enum class ResponseHeader { off, fixed16 };

    explicit OutputBuffer(Logger *logger);
    ~OutputBuffer();

    void add(const std::string &str);
    void add(const std::vector<char> &blob);

    void reset();
    void flush(int fd, int *termination_flag);
    size_t size() { return _writepos - _buffer; }

    void setResponseHeader(ResponseHeader r) { _response_header = r; }

    void setDoKeepalive(bool d) { _do_keepalive = d; }
    bool doKeepalive() { return _do_keepalive; }

    void setError(ResponseCode code, const std::string &message);

    Logger *getLogger() const { return _logger; }

private:
    char *_buffer;
    char *_writepos;
    char *_end;
    unsigned _max_size;
    ResponseHeader _response_header;
    ResponseCode _response_code;
    std::string _error_message;
    bool _do_keepalive;
    Logger *const _logger;

    // We use dynamically allocated memory => disable copy/assignment
    // TODO: Just use vector instead of all this manual fiddling...
    OutputBuffer(const OutputBuffer &) = delete;
    OutputBuffer &operator=(const OutputBuffer &) = delete;

    void addBuffer(const char *, size_t);
    void needSpace(unsigned);
    void writeData(int fd, int *, const char *, size_t);
};

#endif  // OutputBuffer_h
