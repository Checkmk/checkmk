// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef InputBuffer_h
#define InputBuffer_h

#include "config.h"  // IWYU pragma: keep

#include <chrono>
#include <cstddef>
#include <iosfwd>
#include <list>
#include <string>
#include <vector>
class Logger;

class InputBuffer {
public:
    enum class Result {
        request_read,
        data_read,
        unexpected_eof,
        should_terminate,
        line_too_long,
        eof,
        empty_request,
        timeout
    };

    friend std::ostream &operator<<(std::ostream &os, const Result &r);

    InputBuffer(int fd, const bool &termination_flag, Logger *logger,
                std::chrono::milliseconds query_timeout,
                std::chrono::milliseconds idle_timeout);
    Result readRequest();
    [[nodiscard]] bool empty() const;
    std::string nextLine();

private:
    int _fd;
    const bool &_termination_flag;
    std::chrono::milliseconds _query_timeout;
    std::chrono::milliseconds _idle_timeout;
    std::vector<char> _readahead_buffer;
    size_t _read_index;
    size_t _write_index;
    std::list<std::string> _request_lines;
    Logger *const _logger;

    Result readData();
};

#endif  // InputBuffer_h
