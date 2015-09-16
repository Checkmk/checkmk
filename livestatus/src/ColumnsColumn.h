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

#ifndef ColumnsColumn_h
#define ColumnsColumn_h

#include "config.h"

#include "StringColumn.h"

#define COLCOL_TABLE 1
#define COLCOL_NAME  2
#define COLCOL_DESCR 3
#define COLCOL_TYPE  4

class TableColumns;

class ColumnsColumn : public StringColumn
{
    int _colcol;
    TableColumns *_table_columns;

public:
    ColumnsColumn(string name, string description, int colcol, TableColumns *tablecols) :
        StringColumn(name, description, -1), _colcol(colcol), _table_columns(tablecols) {}
    char *getValue(void *data);
};


#endif // ColumnsColumn_h

