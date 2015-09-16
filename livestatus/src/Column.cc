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

#include "Column.h"
#include "logger.h"


Column::Column(string name, string description, int indirect_offset)
  : _name(name)
  , _description(description)
  , _indirect_offset(indirect_offset)
  , _extra_offset(-1)
{
}

void *Column::shiftPointer(void *data)
{
    if (!data)
        return 0;

    if (_indirect_offset >= 0) {
        // add one indirection level
        // indirect_offset is place in structure, where
        // pointer to real object is
        data = *((void **)((char *)data + _indirect_offset));
        if (!data)
            return 0;
    }

    // one optional extra level of indirection
    if (_extra_offset >= 0)
        data = *((void **)((char *)data + _extra_offset));

    return data;
}

