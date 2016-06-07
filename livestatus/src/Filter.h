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

#ifndef Filter_h
#define Filter_h

#include "config.h"  // IWYU pragma: keep
#include <stdint.h>
#include <string>
#include "OutputBuffer.h"
class Column;
class Query;

class Filter {
public:
    Filter()
        : _query(nullptr)
        , _error_code(OutputBuffer::ResponseCode::ok)
        , _column(nullptr) {}
    virtual ~Filter() {}
    virtual bool isAndingFilter() { return false; }
    virtual bool isNegatingFilter() { return false; }
    std::string errorMessage() { return _error_message; }
    OutputBuffer::ResponseCode errorCode() { return _error_code; }
    bool hasError() { return _error_message != ""; }
    void setQuery(Query *q) { _query = q; }
    void setColumn(Column *c) { _column = c; }
    Column *column() { return _column; }
    virtual bool accepts(void *data) = 0;
    virtual void *indexFilter(const char *) { return 0; }
    virtual void findIntLimits(const char *, int *, int *) {}
    virtual bool optimizeBitmask(const char *, uint32_t *) { return false; }

protected:
    Query *_query;  // needed by TimeOffsetFilter (currently)
    void setError(OutputBuffer::ResponseCode code, const std::string &message);

private:
    std::string _error_message;
    OutputBuffer::ResponseCode _error_code;
    Column *_column;
};

#endif  // Filter_h
