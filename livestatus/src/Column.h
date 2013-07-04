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

#ifndef Column_h
#define Column_h

#include "config.h"

#include <stdio.h>
#include <string>
using namespace std;

#define COLTYPE_INT     0
#define COLTYPE_DOUBLE  1
#define COLTYPE_STRING  2
#define COLTYPE_LIST    3
#define COLTYPE_TIME    4
#define COLTYPE_DICT    5

class Filter;
class Query;
class Table;

class Column
{
    string _name;
    string _description;
public:
    int _indirect_offset;
    int _extra_offset;

public:
    Column(string name, string description, int indirect_offset);
    virtual ~Column() {}
    const char *name() const { return _name.c_str(); }
    const char *description() const { return _description.c_str(); }
    virtual string valueAsString(void *data __attribute__ ((__unused__)), Query *)
        { return "invalid"; }
    virtual int type() = 0;
    virtual void output(void *data, Query *) = 0;
    virtual Filter *createFilter(int opid __attribute__ ((__unused__)), char *value __attribute__ ((__unused__))) { return 0; }
    void *shiftPointer(void *data);
    void setExtraOffset(int o) { _extra_offset = o; }
};

#endif // Column_h

