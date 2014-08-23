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

#ifndef AttributelistColumn_h
#define AttributelistColumn_h

#include "config.h"

#include "IntColumn.h"
#include "nagios.h"

/* Since this column can be of type COLTYPE_INT, it must
   be a subclass of IntColumn, since StatsColumn assumes
   Columns of the type COLTYPE_INT to be of that type.
 */

class AttributelistColumn : public IntColumn
{
    int _offset;
    bool _show_list;
public:
    AttributelistColumn(string name, string description, int offset, int indirect_offset, bool show_list)
        : IntColumn(name, description, indirect_offset), _offset(offset), _show_list(show_list) {}

    /* API of Column */
    int type() { return _show_list ? COLTYPE_LIST : COLTYPE_INT; }
    virtual string valueAsString(void *data, Query *);
    void output(void *, Query *);
    Filter *createFilter(int opid, char *value);

    /* API of IntColumn */
    virtual int32_t getValue(void *data, Query *) { return getValue(data); }

    unsigned long getValue(void *data);
};



#endif // AttributelistColumn_h

