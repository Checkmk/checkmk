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

#ifndef CustomVarsExplicitColumn_h
#define CustomVarsExplicitColumn_h

#include "StringColumn.h"
#include "nagios.h"

using namespace std;


class CustomVarsExplicitColumn : public StringColumn
{
    int _offset; // within data structure (differs from host/service)
    std::string _varname;

public:
    CustomVarsExplicitColumn(string name, string description, int offset, int indirect_offset, const char *varname)
        : StringColumn(name, description, indirect_offset),  _offset(offset), _varname(varname) {}
    char *getValue(void *data);
private:
    customvariablesmember *getCVM(void *data);
};


#endif // CustomVarsExplicitColumn_h
