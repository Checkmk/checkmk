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
class FilterVisitor;
class Query;

class Filter {
public:
    explicit Filter(Query *query)
        : _query(query), _error_code(OutputBuffer::ResponseCode::ok) {}
    virtual ~Filter() {}
    virtual void accept(FilterVisitor &) = 0;
    std::string errorMessage() const { return _error_message; }
    OutputBuffer::ResponseCode errorCode() const { return _error_code; }
    bool hasError() const { return _error_message != ""; }
    Query *query() const { return _query; }
    virtual bool accepts(void *data) = 0;
    virtual void *indexFilter(const std::string & /* column_name */) {
        return nullptr;
    }
    virtual void findIntLimits(const std::string & /* column_name */,
                               int * /* lower */, int * /* upper */) {}
    virtual bool optimizeBitmask(const std::string & /* column_name */,
                                 uint32_t * /* mask */) {
        return false;
    }

protected:
    void setError(OutputBuffer::ResponseCode code, const std::string &message);

private:
    Query *_query;
    OutputBuffer::ResponseCode _error_code;
    std::string _error_message;
};

#endif  // Filter_h
