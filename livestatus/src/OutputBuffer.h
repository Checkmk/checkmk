// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

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

    bool shouldTerminate() const { return _termination_flag; }

    std::ostream &os() { return _os; }
    std::string str() const { return _os.str(); }

    void setResponseHeader(ResponseHeader r) { _response_header = r; }

    void setError(ResponseCode code, const std::string &message);
    std::string getError() const;

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
