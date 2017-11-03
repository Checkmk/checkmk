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

#ifndef TimePointerColumn_h
#define TimePointerColumn_h

#include "config.h"  // IWYU pragma: keep
#include <string>
#include "Column.h"
#include "TimeColumn.h"
#include "opids.h"
class Filter;
class RowRenderer;

class TimePointerColumn : public TimeColumn {
public:
    TimePointerColumn(const std::string &name, const std::string &description,
                      const time_t *number)
        : TimeColumn(name, description, -1, -1, -1, 0), _number(number) {}

    std::chrono::system_clock::time_point getValue(
        Row /* row */, const contact * /* auth_user */) const override {
        return std::chrono::system_clock::from_time_t(*_number);
    }

private:
    const time_t *const _number;
};

#endif  // TimePointerColumn_h
