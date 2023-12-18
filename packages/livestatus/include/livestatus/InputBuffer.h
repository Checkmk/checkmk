// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the
// terms and conditions defined in the file COPYING, which is part of this
// source code package.

#ifndef InputBuffer_h
#define InputBuffer_h

#include <chrono>
#include <cstddef>
#include <functional>
#include <iosfwd>
#include <queue>
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
        timeout,
        invalid_utf8
    };

    friend std::ostream &operator<<(std::ostream &os, const Result &r);

    InputBuffer(int fd, std::function<bool()> should_terminate, Logger *logger,
                std::chrono::milliseconds query_timeout,
                std::chrono::milliseconds idle_timeout);
    Result readRequest();
    std::string nextLine();
    std::vector<std::string> getLines();

private:
    const int _fd;
    const std::function<bool()> should_terminate_;
    const std::chrono::milliseconds _query_timeout;
    const std::chrono::milliseconds _idle_timeout;
    std::vector<char> _readahead_buffer;
    size_t _read_index;
    size_t _write_index;
    std::queue<std::string> _request_lines;
    Logger *const _logger;

    [[nodiscard]] bool shouldTerminate() const { return should_terminate_(); }
    Result readData();
};

#endif  // InputBuffer_h
