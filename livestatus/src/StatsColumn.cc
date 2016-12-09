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

#include "StatsColumn.h"
#include <algorithm>
#include "Column.h"
#include "CountAggregator.h"
#include "Filter.h"

using std::make_unique;
using std::unique_ptr;

StatsColumn::StatsColumn(Column *c, unique_ptr<Filter> f, StatsOperation o)
    : _column(c), _filter(move(f)), _operation(o) {}

unique_ptr<Filter> StatsColumn::stealFilter() { return move(_filter); }

unique_ptr<Aggregator> StatsColumn::createAggregator() {
    if (_operation == StatsOperation::count) {
        return make_unique<CountAggregator>(_filter.get());
    }
    if (unique_ptr<Aggregator> aggr = _column->createAggregator(_operation)) {
        return aggr;
    }
    // unaggregateble column
    return make_unique<CountAggregator>(_filter.get());
}
