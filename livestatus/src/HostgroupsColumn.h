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

#ifndef HostgroupsColumn_h
#define HostgroupsColumn_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "Column.h"
#include "ListColumn.h"
#include "nagios.h"
class Query;

class HostgroupsColumn : public ListColumn {
    int _offset;

public:
    HostgroupsColumn(std::string name, std::string description, int offset,
                     int indirect_offset, int extra_offset = -1)
        : ListColumn(name, description, indirect_offset, extra_offset)
        , _offset(offset) {}
    int type() override { return COLTYPE_LIST; }
    void output(void *, Query *) override;
    void *getNagiosObject(char *name) override;  // return pointer to host group
    bool isNagiosMember(void *data, void *nagobject) override;
    bool isEmpty(void *data) override;

private:
    objectlist *getData(void *);
};

#endif  // HostgroupsColumn_h
