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

#ifndef DynamicColumn_h
#define DynamicColumn_h

#include <string>
using namespace std;

class Column;

class DynamicColumn
{
    string _name;
    string _description;
    int    _indirect_offset;
public:
    DynamicColumn(string name, string description, int indirect_offset) :
        _name(name), _description(description), _indirect_offset(indirect_offset) {}
    virtual ~DynamicColumn() {}
    const char *name() const { return _name.c_str(); }
    const char *description() const { return _description.c_str(); }
    Column *createColumn(const char *arguments);
    virtual Column *createColumn(int indirect_offset, const char *arguments) = 0;
};

#endif // DynamicColumn_h

