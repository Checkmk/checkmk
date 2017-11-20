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

#ifndef StatsColumn_h
#define StatsColumn_h

#include "config.h"  // IWYU pragma: keep
#include <memory>
#include "Aggregator.h"
#include "Filter.h"
class Column;
class Logger;

class StatsColumn {
public:
    virtual ~StatsColumn() = default;
    virtual std::unique_ptr<Filter> stealFilter() = 0;
    virtual std::unique_ptr<Aggregator> createAggregator(
        Logger *logger) const = 0;
};

class StatsColumnCount : public StatsColumn {
public:
    explicit StatsColumnCount(std::unique_ptr<Filter> filter);
    std::unique_ptr<Filter> stealFilter() override;
    std::unique_ptr<Aggregator> createAggregator(Logger *logger) const override;

private:
    std::unique_ptr<Filter> _filter;
};

class StatsColumnOp : public StatsColumn {
public:
    StatsColumnOp(StatsOperation operation, Column *column);
    std::unique_ptr<Filter> stealFilter() override;
    std::unique_ptr<Aggregator> createAggregator(Logger *logger) const override;

private:
    StatsOperation _operation;
    Column *_column;
    std::unique_ptr<Filter> _filter;
};

#endif  // StatsColumn_h
