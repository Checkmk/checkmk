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

#include "Column.h"
#include "logger.h"


Column::Column(string name, string description, int indirect_offset)
  : _name(name)
  , _description(description)
  , _indirect_offset(indirect_offset)
  , _extra_offset(-1)
{
}

void *Column::shiftPointer(void *data)
{
    if (!data)
        return 0;

    if (_indirect_offset >= 0) {
        // add one indirection level
        // indirect_offset is place in structure, where
        // pointer to real object is
        data = *((void **)((char *)data + _indirect_offset));
        if (!data)
            return 0;
    }

    // one optional extra level of indirection
    if (_extra_offset >= 0)
        data = *((void **)((char *)data + _extra_offset));

    return data;
}

