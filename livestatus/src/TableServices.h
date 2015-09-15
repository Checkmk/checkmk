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

#ifndef TableServices_h
#define TableServices_h

#include "config.h"

#include <set>
#include "Table.h"
#include "nagios.h"

using namespace std;
class TableHosts;
class TableContacts;
class TableDowntimes;

class TableServices : public Table
{
    bool _by_group;
    bool _by_hostgroup; // alternative to _by_group

public:
    TableServices(bool by_group, bool by_hostgroup);
    const char *name() { return _by_group ? "servicesbygroup" : \
        (_by_hostgroup ? "servicesbyhostgroup" : "services"); }
    const char *prefixname() { return "services"; }
    bool isAuthorized(contact *, void *);
    void *findObject(char *objectspec);
    void add(service *svc);
    void answerQuery(Query *);
    void addColumns(Table *, string prefix, int indirect_offset, bool add_hosts);
};


#endif // TableServices_h
