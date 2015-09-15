// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
//
// Check_MK is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.
//
// Check_MK is  distributed in the hope that it will be useful, but
// WITHOUT ANY WARRANTY;  without even the implied warranty of
// MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have  received  a copy of the  GNU  General Public
// License along with Check_MK.  If  not, email to mk@mathias-kettner.de
// or write to the postal address provided at www.mathias-kettner.de

#include "StatsColumn.h"
#include "Column.h"
#include "Filter.h"
#include "CountAggregator.h"
#include "IntAggregator.h"
#include "DoubleAggregator.h"
#include "PerfdataAggregator.h"
#include "strutil.h"

StatsColumn::~StatsColumn()
{
    if (_filter)
        delete _filter;
}


Aggregator *StatsColumn::createAggregator()
{
    if (_operation == STATS_OP_COUNT)
        return new CountAggregator(_filter);
    else if (_column->type() == COLTYPE_INT || _column->type() == COLTYPE_TIME)
        return new IntAggregator((IntColumn *)_column, _operation);
    else if (_column->type() == COLTYPE_DOUBLE)
        return new DoubleAggregator((DoubleColumn *)_column, _operation);
    else if (_column->type() == COLTYPE_STRING and ends_with(_column->name(), "perf_data"))
        return new PerfdataAggregator((StringColumn *)_column, _operation);
    else  // unaggregateble column
        return new CountAggregator(_filter);
}
