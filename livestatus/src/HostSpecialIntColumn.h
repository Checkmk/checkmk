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

#ifndef HostSpecialIntColumn_h
#define HostSpecialIntColumn_h

#include "config.h"

#include "IntColumn.h"

#define HSIC_REAL_HARD_STATE      0
#define HSIC_PNP_GRAPH_PRESENT    1
#define HSIC_MK_INVENTORY_LAST    2

class HostSpecialIntColumn : public IntColumn
{
    int _type;

public:
    HostSpecialIntColumn(string name, string description, int hsic_type, int indirect)
        : IntColumn(name, description, indirect) , _type(hsic_type) {}
    int32_t getValue(void *data, Query *);
};

#endif // HostSpecialIntColumn_h

