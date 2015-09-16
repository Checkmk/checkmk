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
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

#include <string.h>

#include "Table.h"
#include "Column.h"
#include "DynamicColumn.h"
#include "Query.h"
#include "logger.h"

void Table::addColumn(Column *col)
{
    // do not insert column if one with that name
    // already exists. Delete that column in that
    // case. (For example needed for TableLog->TableHosts,
    // which both define host_name.
    if (column(col->name())) {
        delete col;
    }
    else {
        _columns.insert(make_pair(col->name(), col));
    }
}


void Table::addDynamicColumn(DynamicColumn *dyncol)
{
    _dynamic_columns.insert(make_pair(dyncol->name(), dyncol));
}


Table::~Table()
{
    for (_columns_t::iterator it = _columns.begin();
            it != _columns.end();
            ++it)
    {
        delete it->second;
    }

    for (_dynamic_columns_t::iterator it = _dynamic_columns.begin();
            it != _dynamic_columns.end();
            ++it)
    {
        delete it->second;
    }
}


void Table::addAllColumnsToQuery(Query *q)
{
    for (_columns_t::iterator it = _columns.begin();
            it != _columns.end();
            ++it)
    {
        q->addColumn(it->second);
    }
}


Column *Table::column(const char *colname)
{
    // We allow the name of the table to be
    // prefixed to the column name. So if we
    // detect this prefix, we simply remove it.
    int prefix_len = strlen(prefixname()); // replace 's' with '_'

    // Multisite seems to query "service_service_description". We can fix this
    // in newer versions, but need to be compatible. So we need a "while" here,
    // not just an "if".
    while (!strncmp(colname, prefixname(), prefix_len - 1) && colname[prefix_len - 1] == '_')
    {
        colname += prefix_len;
    }

    // If the colum name contains a ':' then we have a dynamic
    // column with column arguments
    if (strchr(colname, ':'))
        return dynamicColumn(colname);


    // First try exact match
    _columns_t::iterator it = _columns.find(string(colname));
    if (it != _columns.end())
        return it->second;

    // Now we try to readd the removed prefix. That way we tackle the
    // problem with the column "service_period". Here the prefix service_
    // is part of the actual name of the column!
    string with_prefix(prefixname(), prefix_len - 1);
    with_prefix += "_";
    with_prefix += colname;

    it = _columns.find(with_prefix);
    if (it != _columns.end())
        return it->second;
    else
        return 0;
}


Column *Table::dynamicColumn(const char *colname_with_args)
{
    const char *sep_pos = strchr(colname_with_args, ':');
    string name(colname_with_args, sep_pos - colname_with_args);

    const char *argstring = sep_pos + 1;

    _dynamic_columns_t::iterator it = _dynamic_columns.find(name);
    if (it != _dynamic_columns.end())
        return it->second->createColumn(argstring);

    else
        return 0;
}


bool Table::hasColumn(Column *col)
{
    // this is not very efficient but seldomly used
    for (_columns_t::iterator it = _columns.begin();
            it != _columns.end();
            ++it)
    {
        if (col == it->second)
            return true;
    }
    return false;
}


