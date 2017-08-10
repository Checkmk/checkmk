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
// tails. You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#ifndef OffsetDoubleColumn_h
#define OffsetDoubleColumn_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "DoubleColumn.h"
class Row;

class OffsetDoubleColumn : public DoubleColumn {
public:
    OffsetDoubleColumn(const std::string& name, const std::string& description,
                       int offset, int indirect_offset, int extra_offset,
                       int extra_extra_offset)
        : DoubleColumn(name, description, indirect_offset, extra_offset,
                       extra_extra_offset)
        , _offset(offset) {}
    double getValue(Row row) const override;

protected:
    const int _offset;
};

#endif  // OffsetDoubleColumn_h
