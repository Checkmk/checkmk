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

#ifndef Table_h
#define Table_h

#include "config.h"
#include "nagios.h"

#include <map>
#include <string>

using namespace std;

class Column;
class DynamicColumn;
class Query;

class Table
{
public:
    typedef map<string, Column *> _columns_t;
    typedef map<string, DynamicColumn *> _dynamic_columns_t;

private:
    _columns_t _columns;
    _dynamic_columns_t _dynamic_columns;

public:
    Table() {}
    virtual ~Table();
    virtual Column *column(const char *name);
    Column *dynamicColumn(const char *colname_with_args);
    virtual void answerQuery(Query *) = 0;
    virtual const char *name() = 0;
    virtual const char *prefixname() { return name(); }
    virtual bool isAuthorized(contact *, void *) { return true; }
    virtual void *findObject(char *objectspec __attribute__ ((__unused__))) { return 0; } // objectspec may be modified while parsing
    void addColumn(Column *);
    bool hasColumn(Column *);
    void addDynamicColumn(DynamicColumn *);
    void addAllColumnsToQuery(Query *);
    _columns_t *columns() { return &_columns; }
};


#endif // Table_h

