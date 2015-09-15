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

#include <stdlib.h>
#include "DoubleColumnFilter.h"
#include "DoubleColumn.h"
#include "logger.h"
#include "opids.h"

DoubleColumnFilter::DoubleColumnFilter(DoubleColumn *column, int opid, char *value)
    : _column(column)
    , _ref_value(atof(value))
    , _opid(abs(opid))
    , _negate(opid < 0)
{
}

bool DoubleColumnFilter::accepts(void *data)
{
    bool pass = true;
    double act_value = _column->getValue(data);
    switch (_opid) {
        case OP_EQUAL:
            pass = act_value == _ref_value; break;
        case OP_GREATER:
            pass = act_value > _ref_value; break;
        case OP_LESS:
            pass = act_value < _ref_value; break;
        default:
            logger(LG_INFO, "Sorry. Operator %s for float columns not implemented.", op_names_plus_8[_opid]);
            break;
    }
    return pass != _negate;
}

