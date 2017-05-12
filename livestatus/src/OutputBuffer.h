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
#include <sstream>
#include <string>
class Logger;

class OutputBuffer {
public:
    // TODO(sp) Replace this plus its string message with std::error_code
    enum class ResponseCode {
        ok = 200,
        invalid_header = 400,
        not_found = 404,
        limit_exceeded = 413,
        incomplete_request = 451,
        invalid_request = 452,
    };

    enum class ResponseHeader { off, fixed16 };

    OutputBuffer(int fd, const bool &termination_flag, Logger *logger);
    ~OutputBuffer();

    std::ostream &os() { return _os; }

    void setResponseHeader(ResponseHeader r) { _response_header = r; }

    void setError(ResponseCode code, const std::string &message);

    Logger *getLogger() const { return _logger; }

private:
    const int _fd;
    const bool &_termination_flag;
    Logger *const _logger;
    std::ostringstream _os;
    ResponseHeader _response_header;
    ResponseCode _response_code;
    std::string _error_message;

    void flush();
    void writeData(std::ostringstream &os);
};

#endif  // OutputBuffer_h
