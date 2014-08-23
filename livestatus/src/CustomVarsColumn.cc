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

#include "CustomVarsColumn.h"
#include "nagios.h"
#include "logger.h"
#include "CustomVarsFilter.h"
#include "Query.h"

void CustomVarsColumn::output(void *data, Query *query)
{

    if (_what == CVT_DICT)
        query->outputBeginDict();
    else
        query->outputBeginList();

    customvariablesmember *cvm = getCVM(data);

    bool first = true;
    while (cvm) {
        if (first)
            first = false;
        else if (_what == CVT_DICT)
            query->outputDictSeparator();
        else
            query->outputListSeparator();
        if (_what == CVT_VARNAMES)
            query->outputString(cvm->variable_name);
        else if (_what == CVT_VALUES)
            query->outputString(cvm->variable_value);
        else {
            query->outputString(cvm->variable_name);
            query->outputDictValueSeparator();
            query->outputString(cvm->variable_value);
        }
        cvm = cvm->next;
    }

    if (_what == CVT_DICT)
        query->outputEndDict();
    else
        query->outputEndList();
}

Filter *CustomVarsColumn::createFilter(int opid, char *value)
{
    return new CustomVarsFilter(this, opid, value);
}


customvariablesmember *CustomVarsColumn::getCVM(void *data)
{
    if (!data) return 0;
    data = shiftPointer(data);
    if (!data) return 0;
    return *(customvariablesmember **)((char *)data + _offset);
}


bool CustomVarsColumn::contains(void *data, const char *value)
{
    customvariablesmember *cvm = getCVM(data);
    while (cvm) {
        char *ref = _what == CVT_VARNAMES ? cvm->variable_name : cvm->variable_value;
        if (!strcmp(ref, value))
            return true;
        cvm = cvm->next;
    }
    return false;
}

char *CustomVarsColumn::getVariable(void *data, const char *varname)
{
    customvariablesmember *cvm = getCVM(data);
    while (cvm) {
        if (!strcmp(cvm->variable_name, varname))
            return cvm->variable_value;
        cvm = cvm->next;
    }
    return 0;
}
