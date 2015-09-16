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

#ifndef CustomVarsColumn_h
#define CustomVarsColumn_h

#include "config.h"

#include "Column.h"
#include <string>
#include "nagios.h"

using namespace std;

#define CVT_VARNAMES 0
#define CVT_VALUES   1
#define CVT_DICT     2

class CustomVarsColumn : public Column
{
    int _offset; // within data structure (differs from host/service)
    int _what;

public:
    CustomVarsColumn(string name, string description, int offset, int indirect_offset, int what)
        : Column(name, description, indirect_offset),  _offset(offset), _what(what) {}
    int type() { return _what == CVT_DICT ? COLTYPE_DICT : COLTYPE_LIST; }
    void output(void *, Query *);
    Filter *createFilter(int opid, char *value);
    bool contains(void *data, const char *value);
    char *getVariable(void *data, const char *varname);
private:
    customvariablesmember *getCVM(void *data);
};


#endif // CustomVarsColumn_h


