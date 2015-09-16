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

#include <math.h>
#include "DoubleAggregator.h"
#include "StatsColumn.h"
#include "DoubleColumn.h"
#include "Query.h"

/* SORRY: This file is copy&pasted from IntAggregator.
   I hate copy & paste. But I also dislike complicating
   stuff by using C++ templates and the like.
 */

void DoubleAggregator::consume(void *data, Query *)
{
    _count++;
    double value = _column->getValue(data);
    switch (_operation) {
        case STATS_OP_SUM:
        case STATS_OP_AVG:
            _aggr += value; break;

        case STATS_OP_MIN:
            if (_count == 1)
                _aggr = value;
            else if (value < _aggr)
                _aggr = value;
            break;

        case STATS_OP_MAX:
            if (_count == 1)
                _aggr = value;
            else if (value > _aggr)
                _aggr = value;
            break;

        case STATS_OP_STD:
            _aggr += value;
            _sumq += value * value;
            break;

        case STATS_OP_SUMINV:
        case STATS_OP_AVGINV:
            _aggr += 1.0 / value;
            break;
    }
}


void DoubleAggregator::output(Query *q)
{
    switch (_operation) {
        case STATS_OP_SUM:
        case STATS_OP_MIN:
        case STATS_OP_MAX:
        case STATS_OP_SUMINV:
            q->outputDouble(_aggr);
            break;

        case STATS_OP_AVG:
        case STATS_OP_AVGINV:
            if (_count == 0)
                q->outputDouble(0.0);
            else
                q->outputDouble(_aggr / _count);
            break;

        case STATS_OP_STD:
            if (_count <= 1)
                q->outputDouble(0.0);
            else
                q->outputDouble(sqrt((_sumq - (_aggr * _aggr) / _count)/(_count - 1)));
            break;
    }
}

