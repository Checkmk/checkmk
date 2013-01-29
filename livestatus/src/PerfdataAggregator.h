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

#ifndef PerfdataAggregator_h
#define PerfdataAggregator_h

#include <map>
#include <string>
#include "Aggregator.h"

class StringColumn;

struct perf_aggr {
    double _aggr;
    double _count;
    double _sumq;
};

class PerfdataAggregator : public Aggregator
{
    StringColumn *_column;
    typedef std::map<std::string, perf_aggr> _aggr_t;
    _aggr_t _aggr;

public:
    PerfdataAggregator(StringColumn *c, int o) : Aggregator(o), _column(c) {}
    void consume(void *data, Query *);
    void output(Query *);

private:
    void consumeVariable(const char *varname, double value);
};

#endif // PerfdataAggregator_h

