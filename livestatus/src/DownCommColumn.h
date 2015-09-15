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

#ifndef DownCommColumn_h
#define DownCommColumn_h

#include "config.h"

#include "ListColumn.h"
#include "TableContacts.h"

class TableDownComm;

class DownCommColumn : public ListColumn
{
    bool _is_downtime;
    bool _with_info;
    bool _is_service; // and not host
    bool _with_extra_info; // provides date and type
public:
    DownCommColumn(string name, string description, int indirect_offset, bool is_downtime, bool is_service, bool with_info, bool with_extra_info)
        : ListColumn(name, description, indirect_offset), _is_downtime(is_downtime), _is_service(is_service), _with_info(with_info), _with_extra_info(with_extra_info) {}
    int type() { return COLTYPE_LIST; }
    void output(void *, Query *);
    void *getNagiosObject(char *name);
    bool isEmpty(void *data);
    bool isNagiosMember(void *data, void *member);
};


#endif // DownCommColumn_h

