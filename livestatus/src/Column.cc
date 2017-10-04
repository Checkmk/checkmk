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

#include "Column.h"
#include <stdexcept>
#include <utility>
#include "Logger.h"

using std::move;
using std::runtime_error;
using std::string;
using std::unique_ptr;

Column::Column(string name, string description, int indirect_offset,
               int extra_offset, int extra_extra_offset, int offset)
    : _logger(Logger::getLogger("cmk.livestatus"))
    , _name(move(name))
    , _description(move(description))
    , _indirect_offset(indirect_offset)
    , _extra_offset(extra_offset)
    , _extra_extra_offset(extra_extra_offset)
    , _offset(offset) {}

namespace {
const void *shift(const void *data, int offset) {
    return (data == nullptr || offset < 0)
               ? data
               : *offset_cast<const void *>(data, offset);
}
}  // namespace

const void *Column::shiftPointer(Row row) const {
    return offset_cast<const void *>(
        shift(shift(shift(row.rawData<const void>(), _indirect_offset),
                    _extra_offset),
              _extra_extra_offset),
        _offset);
}

unique_ptr<Filter> Column::createFilter(RelationalOperator /*unused*/,
                                        const std::string & /*unused*/) const {
    throw runtime_error("filtering on column " + _name + " not supported");
}

unique_ptr<Aggregator> Column::createAggregator(
    StatsOperation /*unused*/) const {
    return nullptr;
}
