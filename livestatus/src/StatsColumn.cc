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
#include <string>
#include "Column.h"
#include "CountAggregator.h"
#include "DoubleAggregator.h"
#include "DoubleColumn.h"
#include "Filter.h"
#include "IntAggregator.h"
#include "IntColumn.h"
#include "PerfdataAggregator.h"
#include "StringColumn.h"
#include "strutil.h"

StatsColumn::~StatsColumn() {
    if (_filter != nullptr) {
        delete _filter;
    }
}

Aggregator *StatsColumn::createAggregator() {
    if (_operation == StatsOperation::count) {
        return new CountAggregator(_filter);
    }
    if (_column->type() == ColumnType::int_ ||
        _column->type() == ColumnType::time) {
        return new IntAggregator(_operation, static_cast<IntColumn *>(_column));
    }
    if (_column->type() == ColumnType::double_) {
        return new DoubleAggregator(_operation,
                                    static_cast<DoubleColumn *>(_column));
    }
    if (_column->type() == ColumnType::string and
        (ends_with(_column->name().c_str(), "perf_data") != 0)) {
        return new PerfdataAggregator(_operation,
                                      static_cast<StringColumn *>(_column));
    }  // unaggregateble column
    return new CountAggregator(_filter);
}
