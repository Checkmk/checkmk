// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

#include "config.h"

#define IB_REQUEST_READ               0
#define IB_DATA_READ                  1
#define IB_NO_MORE_REQUEST            2
#define IB_UNEXPECTED_END_OF_FILE     3
#define IB_SHOULD_TERMINATE           4
#define IB_LINE_TOO_LONG              5
#define IB_END_OF_FILE                6
#define IB_EMPTY_REQUEST              7
#define IB_TIMEOUT                    8

#define IB_BUFFER_SIZE            65536

#include <string>
#include <deque>
using namespace std;

class InputBuffer
{
    int _fd;
    int *_termination_flag;
    typedef deque<string> _requestlines_t;
    _requestlines_t _requestlines;
    char _readahead_buffer[IB_BUFFER_SIZE];
    char *_read_pointer;
    char *_write_pointer;
    char *_end_pointer;

    // some buffer
public:
    InputBuffer(int *termination_flag);
    void setFd(int fd);
    int readRequest();
    bool moreLines() { return !_requestlines.empty(); }
    string nextLine();

private:
    void storeRequestLine(char *line, int length);
    int readData();
};


#endif // InputBuffer_h

