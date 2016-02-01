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

#ifndef Column_h
#define Column_h

#include "config.h"  // IWYU pragma: keep
#include <string>
class Filter;
class Query;

#define COLTYPE_INT 0
#define COLTYPE_DOUBLE 1
#define COLTYPE_STRING 2
#define COLTYPE_LIST 3
#define COLTYPE_TIME 4
#define COLTYPE_DICT 5
#define COLTYPE_BLOB 6
#define COLTYPE_NULL 7

class Column {
    std::string _name;
    std::string _description;
    int _indirect_offset;
    int _extra_offset;
    int _extra_extra_offset;

public:
    Column(std::string name, std::string description, int indirect_offset,
           int extra_offset, int extra_extra_offset = -1);
    virtual ~Column() {}

    const char *name() const { return _name.c_str(); }
    const char *description() const { return _description.c_str(); }
    void *shiftPointer(void *data);

    virtual std::string valueAsString(void *, Query *) { return "invalid"; }
    virtual int type() = 0;
    virtual void output(void *data, Query *) = 0;
    virtual bool mustDelete() {
        return false;
    }  // true for dynamic Columns to be deleted after Query
    virtual Filter *createFilter(int, char *) { return 0; }
};

#endif  // Column_h
