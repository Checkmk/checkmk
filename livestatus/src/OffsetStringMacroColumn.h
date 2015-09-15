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

#ifndef OffsetStringMacroColumn_h
#define OffsetStringMacroColumn_h

#include "nagios.h"
#include "OffsetStringColumn.h"

class OffsetStringMacroColumn : public OffsetStringColumn
{
    int _offset;
public:
    OffsetStringMacroColumn(string name, string description, int offset, int indirect_offset = -1) :
        OffsetStringColumn(name, description, offset, indirect_offset) {}
    // reimplement several functions from StringColumn

    string valueAsString(void *data, Query *);
    void output(void *data, Query *);
    Filter *createFilter(int opid, char *value);

    // overriden by host and service macro columns
    virtual host *getHost(void *) = 0;
    virtual service *getService(void *) = 0;
private:
    const char *expandMacro(const char *macroname, host *hst, service *svc);
    const char *expandCustomVariables(const char *varname, customvariablesmember *custvars);
};

#endif // OffsetStringMacroColumn_h

