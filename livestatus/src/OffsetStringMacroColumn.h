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

#ifndef OffsetStringMacroColumn_h
#define OffsetStringMacroColumn_h

#include "nagios.h"
#include "OffsetStringColumn.h"

class OffsetStringMacroColumn : public OffsetStringColumn
{
    int _offset;
public:
    OffsetStringMacroColumn(string name, string description, int offset, int indirect_offset = -1) :
        OffsetStringColumn(name, description, offset, indirect_offset) {}
    // reimplement several functions from StringColumn

    string valueAsString(void *data, Query *);
    void output(void *data, Query *);
    Filter *createFilter(int opid, char *value);

    // overriden by host and service macro columns
    virtual host *getHost(void *) = 0;
    virtual service *getService(void *) = 0;
private:
    const char *expandMacro(const char *macroname, host *hst, service *svc);
    const char *expandCustomVariables(const char *varname, customvariablesmember *custvars);
};

#endif // OffsetStringMacroColumn_h

