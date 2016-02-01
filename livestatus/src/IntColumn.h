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

#ifndef IntColumn_h
#define IntColumn_h

#include "config.h"  // IWYU pragma: keep
#include <stdint.h>
#include <string>
#include "Column.h"
class Filter;
class Query;

class IntColumn : public Column {
public:
    IntColumn(std::string name, std::string description, int indirect_offset,
              int extra_offset, int extra_extra_offset = -1)
        : Column(name, description, indirect_offset, extra_offset,
                 extra_extra_offset) {}
    virtual int32_t getValue(void *data, Query *) = 0;
    void output(void *, Query *) override;
    int type() override { return COLTYPE_INT; }
    std::string valueAsString(void *data, Query *) override;
    Filter *createFilter(int operator_id, char *value) override;
};

#endif  // IntColumn_h
