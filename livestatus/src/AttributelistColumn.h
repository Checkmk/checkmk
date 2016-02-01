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

#include "config.h"  // IWYU pragma: keep
#include <stdint.h>
#include <string>
#include "Column.h"
#include "IntColumn.h"
class Filter;
class Query;

/* Since this column can be of type COLTYPE_INT, it must
   be a subclass of IntColumn, since StatsColumn assumes
   Columns of the type COLTYPE_INT to be of that type.
 */

class AttributelistColumn : public IntColumn {
    int _offset;
    bool _show_list;

public:
    AttributelistColumn(std::string name, std::string description, int offset,
                        int indirect_offset, bool show_list,
                        int extra_offset = -1, int extra_extra_offset = -1)
        : IntColumn(name, description, indirect_offset, extra_offset,
                    extra_extra_offset)
        , _offset(offset)
        , _show_list(show_list) {}

    // API of Column
    int type() override { return _show_list ? COLTYPE_LIST : COLTYPE_INT; }
    std::string valueAsString(void *data, Query *) override;
    void output(void *, Query *) override;
    Filter *createFilter(int opid, char *value) override;

    // API of IntColumn
    int32_t getValue(void *data, Query *) override { return getValue(data); }
    unsigned long getValue(void *data);
};

#endif  // AttributelistColumn_h
