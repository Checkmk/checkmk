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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef InputBuffer_h
#define InputBuffer_h

#include "config.h"  // IWYU pragma: keep
#include <stddef.h>
#include <list>
#include <string>
#include <vector>

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

    InputBuffer(int fd, const int *termination_flag);
    Result readRequest();
    bool empty() const;
    std::string nextLine();

private:
    int _fd;
    const int *_termination_flag;
    std::vector<char> _readahead_buffer;
    size_t _read_index;
    size_t _write_index;
    std::list<std::string> _request_lines;

    Result readData();
};

#endif  // InputBuffer_h
