// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
// Check_MK is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.
//
// Check_MK is  distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY;  without even the implied warranty of
// MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have  received  a copy of the  GNU  General Public
// License along with Check_MK.  If  not, email to mk@mathias-kettner.de
// or write to the postal address provided at www.mathias-kettner.de

#ifndef Filter_h
#define Filter_h

#include "config.h"

#include <vector>
#include <string>
#include <stdint.h>

using namespace std;
class Query;
class Column;

class Filter
{
    string _error_message; // Error in constructor
    unsigned _error_code;
    Column *_column;

protected:
    Query *_query; // needed by TimeOffsetFilter (currently)
    void setError(unsigned code, const char *format, ...);

public:
    Filter() : _query(0), _column(0) {}
    virtual ~Filter() {}
    virtual bool isAndingFilter() { return false; }
    virtual bool isNegatingFilter() { return false; }
    string errorMessage() { return _error_message; }
    unsigned errorCode() { return _error_code; }
    bool hasError() { return _error_message != ""; }
    void setQuery(Query *q) { _query = q; }
    void setColumn(Column *c) { _column = c; }
    Column *column() { return _column; }
    virtual bool accepts(void *data) = 0;
    virtual void *indexFilter(const char *columnname __attribute__ ((__unused__))) { return 0; }
    virtual void findIntLimits(const char *columnname __attribute__ ((__unused__)), int *lower __attribute__ ((__unused__)), int *upper __attribute__ ((__unused__))) {}
    virtual bool optimizeBitmask(const char *columnname __attribute__ ((__unused__)), uint32_t *mask __attribute__ ((__unused__))) { return false; }
};

#endif // Filter_h

