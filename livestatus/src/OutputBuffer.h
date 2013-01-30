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

#ifndef OutputBuffer_h
#define OutputBuffer_h

#include "config.h"

#include <string>
using namespace std;

#define INITIAL_OUTPUT_BUFFER_SIZE 1

#define RESPONSE_CODE_OK                 200
#define RESPONSE_CODE_INVALID_HEADER     400
#define RESPONSE_CODE_UNAUTHORIZED       403
#define RESPONSE_CODE_NOT_FOUND          404
#define RESPONSE_CODE_INCOMPLETE_REQUEST 451
#define RESPONSE_CODE_INVALID_REQUEST    452
#define RESPONSE_CODE_UNKNOWN_COLUMN     450

class OutputBuffer
{
    char *_buffer;
    char *_writepos;
    char *_end;
    unsigned _max_size;
    int _response_header;
    unsigned _response_code;
    string _error_message;
    bool _do_keepalive;

public:
    OutputBuffer();
    ~OutputBuffer();
    const char *buffer() { return _buffer; }
    unsigned size() { return _writepos - _buffer; }
    void addChar(char c);
    void addString(const char *);
    void addBuffer(const char *, unsigned);
    void reset();
    void flush(int fd, int *termination_flag);
    void setResponseHeader(int r) { _response_header = r; }
    int responseHeader() { return _response_header; }
    void setDoKeepalive(bool d) { _do_keepalive = d; }
    bool doKeepalive() { return _do_keepalive; }
    void setError(unsigned code, const char *format, ...);
    bool hasError() { return _error_message != ""; }

private:
    void needSpace(unsigned);
    void writeData(int fd, int *, const char *, int);
};


#endif // OutputBuffer_h

