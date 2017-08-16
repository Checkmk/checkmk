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

#ifndef IntAggregator_h
#define IntAggregator_h

#include "config.h"  // IWYU pragma: keep
#include <cstdint>
#include "Aggregator.h"
class IntColumn;
class Row;
class RowRenderer;

#ifdef CMC
#include "cmc.h"
#else
#include "nagios.h"
#endif

class IntAggregator : public Aggregator {
public:
    IntAggregator(StatsOperation operation, const IntColumn *column)
        : Aggregator(operation)
        , _column(column)
        , _count(0)
        , _aggr(0)
        , _sumq(0) {}
    void consume(Row row, const contact *auth_user,
                 int timezone_offset) override;
    void output(RowRenderer &r) const override;

private:
    const IntColumn *const _column;
    std::uint32_t _count;
    int64_t _aggr;
    double _sumq;
};

#endif  // IntAggregator_h
